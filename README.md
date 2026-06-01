# Rentals Data Pipeline

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Poetry](https://img.shields.io/badge/Poetry-60A5FA?style=for-the-badge&logo=poetry&logoColor=white)
![Google Cloud](https://img.shields.io/badge/Google%20Cloud-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![BigQuery](https://img.shields.io/badge/BigQuery-669DF6?style=for-the-badge&logo=googlebigquery&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-FF694B?style=for-the-badge&logo=dbt&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=for-the-badge&logo=terraform&logoColor=white)

## *Motivation*

Brazilian rental-market prices move fast and aren't trivially comparable across listing sites — each platform has its own search URLs, page layouts, and JSON-LD shapes, and none of them expose a public feed for tracking how asking prices for apartments and houses in a given city evolve over time. To answer questions like *"How is rent in a given city trending?"* we need to capture that history ourselves, listing by listing.

## *Main Goal*

Land an append-only history of rental listings for every configured `(site, city, property_type)`, partitioned in a layout that downstream warehouse models can consume directly without further cleanup.

---

## Project

### *Solution*

For each configured combination of `(site, city, property_type)`, the pipeline automatically collects all available rental listings across all pages and stores a per-page timestamped snapshot in cloud storage (data is partitioned by `environment, site, city, property_type, page`). Those snapshots are then loaded into BigQuery as a Bronze layer table — each listing is flattened into a structured row, deduplicated by source blob, and partitioned by scrape date. A dbt Silver layer then reads from Bronze, coalesces nulls, and applies cross-site deduplication via a window function, producing a single clean table (`silver_listings_deduped`). A dbt Gold layer then transforms Silver into an analytical star schema — four incremental dimensions (`dim_listings`, `dim_address`, `dim_amenities`, `dim_images`) tracking listing attributes, addresses, amenities and images, plus a central fact table (`fact_listings_scrapes`) capturing all mutable measures per `(LISTING_ID, SCRAPE_DATE)` — ready for downstream analytics and reporting.

Collection runs automatically on **Google Cloud** through a managed workflow layer. Each pipeline step is containerised and executed on demand, with configuration centrally managed in `cloud/` — one YAML file per task defining how it runs, and one YAML file per workflow defining the execution order. Adding a new listing site or city requires only a small configuration change with no infrastructure work.

### *Code Structure*

```txt
├── .claude/                    # Claude Code files;
├── .code_quality/              # Config files to ensure clean code;
├── .github/                    # GitHub automations;
├── .vscode/                    # VSCode configurations for development;
├── cloud/                      # Cloud execution configuration;
├── dbt/                        # dbt project for Silver and Gold transformation layers;
├── docs/                       # Documentation files;
├── notebooks/                  # Jupyter notebooks for exploration and prototyping;
├── scripts/                    # Operational scripts (setup, Docker entrypoint, deploy);
├── src/                        # Source code;
├── terraform/                  # GCP infrastructure managed by Terraform;
├── tests/                      # Pytests for quality assurance;
├── .dockerignore               # Files excluded from the Docker build context;
├── .gitattributes              # Define attributes for pathnames;
├── .gitignore                  # Files that Git should ignore when committing;
├── AUTHORS.md                  # List of individuals who contributed to the project;
├── CHANGELOG.md                # Annotate notable changes for each version;
├── CLAUDE.md                   # Instructions, standards and context to Claude Code AI agent;
├── CODING_GUIDELINES.md        # Standards and best practices for the codebase;
├── Dockerfile                  # Container definition, one image per task;
├── poetry.lock                 # Ensure reproducible builds across envs;
├── pyproject.toml              # Centralized configurations for Python project;
└── README.md                   # YOU ARE HERE!
```

### *Workflow · etl_rentals_data*

```mermaid
flowchart TD
    Trigger["☁️ Cloud Workflows · etl_rentals_data\n(ENVIRONMENT, CITY, SITES, PROPERTY_TYPES,\nSTART_PAGE, MAX_PAGE, FILE_DATE,\nUPLOAD_TO_GCS, UPLOAD_TO_BQ)"]

    Trigger -->|"step 1"| CR1["📦 Cloud Run Job\nscraper-data-to-bucket"]

    subgraph ScraperJob["scraper_data_to_bucket — fetch listings and store in GCS"]
        CR1 --> Pairs1["for each (site, property_type) pair"]
        Pairs1 --> Fetch["fetch listing page N"]
        Fetch -->|"404 / empty page"| PairDone1(["pair done"])
        Fetch -->|"transient error"| Retry["retry with backoff\n5 fast retries · then long-sleep retry"]
        Retry -->|"retries exhausted"| PairDone1
        Retry --> Fetch
        Fetch -->|"200 OK · listings found"| GCS[("GCS · scraper-rentals-data\nenv / site / city / type / page / timestamp.json")]
        GCS --> NextPage1["next page"]
        NextPage1 -->|"below max_page or unbounded"| Fetch
        NextPage1 -->|"max_page reached"| PairDone1
        PairDone1 --> Pairs1
    end

    ScraperJob -->|"step 2"| CR2["📦 Cloud Run Job\ngcs-to-bigquery-bronze"]

    subgraph BronzeJob["gcs_to_bigquery_bronze — load GCS snapshots into BigQuery"]
        CR2 --> TableCheck{"bronze_listings\ntable exists?"}
        TableCheck -->|no| CreateTable["create table"]
        TableCheck -->|yes| Pairs2
        CreateTable --> Pairs2["for each (site, property_type) pair"]
        Pairs2 --> FindBlob["look up latest GCS blob\nfor target date · page N"]
        FindBlob -->|"no blob found"| PairDone2(["pair done"])
        FindBlob -->|"blob found"| DupCheck{"already loaded\ninto BigQuery?"}
        DupCheck -->|"yes — skip"| NextPage2["next page"]
        DupCheck -->|no| BQ[("BigQuery · env.bronze_listings\npartitioned by scrape date")]
        BQ --> NextPage2
        NextPage2 -->|"below max_page or unbounded"| FindBlob
        NextPage2 -->|"max_page reached"| PairDone2
        PairDone2 --> Pairs2
    end

    BronzeJob -->|"step 3"| CR3["📦 Cloud Run Job\nprocess-silver-layer"]

    subgraph SilverJob["process_silver_layer — dbt incremental merge into Silver"]
        CR3 --> dbtRun["dbt run --select silver\n--target dev|test|prod"]
        dbtRun --> Dedup["flatten structs · coalesce NULLs\ncross-site deduplication\n(QUALIFY ROW_NUMBER OVER ...)"]
        Dedup --> BQSilver[("BigQuery · env.silver_listings_deduped\nincremental merge · unique key\n(LISTING_ID, SCRAPE_DATE)")]
    end

    SilverJob -->|"step 4"| CR4["📦 Cloud Run Job\nmodel-gold-layer"]

    subgraph GoldJob["model_gold_layer — dbt incremental merge into Gold"]
        CR4 --> dbtRunGold["dbt run --select gold\n--target dev|test|prod"]
        dbtRunGold --> GoldModels["build dimensions\n(dim_listings · dim_address\ndim_amenities · dim_images)\n+ fact_listings_scrapes"]
        GoldModels --> BQGold[("BigQuery · env.gold_*\nincremental merge · FILE_DATE-scoped\nunique key per model")]
    end

    GoldJob --> Done(["done"])
```

### *Documentations*

Follow our [CODING_GUIDELINES.md](CODING_GUIDELINES.md) to check our way of code.

## License and Authors

This project is maintained by the **Dark Theme Org**.
