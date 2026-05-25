# Rentals Data Pipeline

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Poetry](https://img.shields.io/badge/Poetry-60A5FA?style=for-the-badge&logo=poetry&logoColor=white)
![Google Cloud](https://img.shields.io/badge/Google%20Cloud-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![BigQuery](https://img.shields.io/badge/BigQuery-669DF6?style=for-the-badge&logo=googlebigquery&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-FF694B?style=for-the-badge&logo=dbt&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=for-the-badge&logo=terraform&logoColor=white)

## *Motivation*

Brazilian rental-market prices move fast and aren't trivially comparable across listing sites — each platform has its own search URLs, page layouts, and JSON-LD shapes, and none of them expose a public feed for tracking how asking prices for apartments and houses in a given city evolve over time. To answer questions like *"how is rent in Macaé trending vs. last quarter?"* we need to capture that history ourselves, listing by listing, day by day.

## *Main Goal*

Land an append-only history of rental listings for every configured `(site, city, property_type)` tuple in a single GCS bucket, partitioned in a layout that downstream warehouse models (dbt-bigquery is on the dependency list for this) can consume directly without further cleanup.

---

## Project

### *Solution*

For each configured combination of listing site, city, and property type, the pipeline automatically collects all available rental listings across all pages and stores a per-page timestamped snapshot in cloud storage. Data is partitioned by environment, site, city, property type, and page so that downstream models can consume it directly without further cleanup.

Collection runs automatically on Google Cloud through a managed workflow layer. Each pipeline step is containerised and executed on demand, with configuration centrally managed in `cloud/` — one YAML file per task defining how it runs, and one YAML file per workflow defining the execution order. Adding a new listing site or city requires only a small configuration change with no infrastructure work.

### *Code Structure*

```txt
├── .claude/                    # Claude Code files;
├── .code_quality/              # Config files to ensure clean code;
├── .github/                    # GitHub automations;
├── .vscode/                    # VSCode configurations for development;
├── cloud/                      # Cloud execution configuration;
│   ├── settings.yml            # Single source of truth for GCP project config (project_id, region);
│   ├── tasks/                  # One YAML per task — operator type, machine config, parameters;
│   └── workflows/              # One YAML per workflow — Cloud Workflows native execution graph;
├── docs/                       # Documentation files;
├── notebooks/                  # Jupyter notebooks for exploration and prototyping;
├── scripts/                    # Operational scripts (setup, Docker entrypoint, deploy);
├── src/                        # Source code;
│   └── app/                    # Main application code;
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
    Trigger["☁️ Cloud Workflows · etl_rentals_data\n(VERSION, ENVIRONMENT, CITY, SITES,\nPROPERTY_TYPES, UPLOAD_TO_GCS,\nFILE_DATE, UPLOAD_TO_BQ,\nSTART_PAGE, MAX_PAGE)"]

    Trigger -->|"step 1 · googleapis.run.v2\n.jobs.run"| CR1["📦 Cloud Run Job\nscraper-data-to-bucket"]

    subgraph ScraperEntrypoint["scraper_data_to_bucket entrypoint"]
        CR1 --> Pairs1["for each (site, property_type)"]
        Pairs1 --> Init["set_url · page = start_page\nlong_retry_count = 0"]
        Init --> MaxCheck1{"page > max_page?"}
        MaxCheck1 -->|yes| PairDone1(["pair done"])
        MaxCheck1 -->|no| Fetch["fetch_and_parse_html\npage=N · Accept-Language · Referer"]
        Fetch -->|"RequestException\n(5 fast retries exhausted)"| LongCheck{"long_retry_count\n≥ max_long_retries?"}
        LongCheck -->|yes| PairDone1
        LongCheck -->|"no · sleep 30–90 s"| Fetch
        Fetch -->|"None — HTTP 404"| PairDone1
        Fetch -->|"200 OK"| Extract["extract_properties\nJSON-LD ItemList"]
        Extract -->|"ValueError — empty page"| PairDone1
        Extract -->|success| UpFlag1{"upload_to_gcs?"}
        UpFlag1 -->|false| Inc1["page++"]
        UpFlag1 -->|true| GCS[("GCS scraper-rentals-data\nenv/site/city/type/page/\nexecuted_at.json")]
        GCS --> Inc1
        Inc1 --> MaxCheck1
        PairDone1 --> Pairs1
    end

    ScraperEntrypoint -->|"scraper_operation\nstep 2 · googleapis.run.v2\n.jobs.run"| CR2["📦 Cloud Run Job\ngcs-to-bigquery-bronze"]

    subgraph BronzeEntrypoint["gcs_to_bigquery_bronze entrypoint"]
        CR2 --> DDL{"table\nexists?"}
        DDL -->|no| Create["CREATE TABLE\nenv.bronze_listings"]
        DDL -->|yes| Pairs2
        Create --> Pairs2["for each (site, property_type)"]
        Pairs2 --> PageLoop["page = start_page"]
        PageLoop --> MaxCheck2{"page > max_page?"}
        MaxCheck2 -->|yes| PairDone2(["pair done"])
        MaxCheck2 -->|no| Glob["ScraperBucket.latest_blob\nmatch_glob · most recently updated"]
        Glob -->|"None — no blob for date/page"| PairDone2
        Glob -->|blob found| DupCheck{"blob already\nloaded?"}
        DupCheck -->|yes · skip| Inc2["page++"]
        DupCheck -->|no| Download["blob.download_as_text\njson.loads"]
        Download --> Transform["row_schema\nLISTING_* · SRC_* · AUD_*"]
        Transform --> UpFlag2{"upload_to_bq?"}
        UpFlag2 -->|false| Inc2
        UpFlag2 -->|true| BQ[("BigQuery\nenv.bronze_listings\nPARTITION BY DATE(SRC_EXECUTED_AT_TS)")]
        BQ --> Inc2
        Inc2 --> MaxCheck2
        PairDone2 --> Pairs2
    end

    BronzeEntrypoint -->|"bronze_operation"| Done(["done"])
```

### *Documentations*

Follow our [CODING_GUIDELINES.md](CODING_GUIDELINES.md) to check our way of code.

## License and Authors

This project is maintained by the **Dark Theme Org**.
