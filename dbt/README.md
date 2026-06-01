# dbt/

dbt project (`rentals_dbt`) for the transformation layer of the Rentals Data Pipeline. Reads
from the BigQuery Bronze table and produces cleaned, deduplicated Silver models and a Gold
analytical layer — all landing in the same environment dataset (`dev` / `test` / `prod`) with a
layer prefix on the table name.

## Structure

```txt
dbt/
├── dbt_project.yml       # Project config — name, profile, model paths, layer materializations
├── profiles.yml          # Connection profiles; reads PROJECT_ID, LOCATION from env vars
├── models/
│   ├── silver/
│   │   ├── _schema.yml          # Column docs and dbt tests for Silver models
│   │   ├── _sources.yml         # Declares bronze_listings as the Bronze source
│   │   └── listings_deduped.sql
│   └── gold/
│       ├── _schema.yml          # Column docs and dbt tests for Gold models
│       ├── dimensions/
│       │   ├── dim_listings.sql       # SCD-1 listing catalogue with soft-delete
│       │   ├── dim_address.sql        # Per-listing address (STREET_ADDRESS + LISTING_ID)
│       │   ├── dim_amenities.sql      # Unnested amenity features per listing
│       │   └── dim_images.sql         # Unnested image URLs per listing
│       └── facts/
│           └── fact_listings_scrapes.sql  # One row per (LISTING_ID, SCRAPE_DATE)
└── macros/
    ├── generate_schema_name.sql   # All models land in the bare target dataset (no layer suffix)
    ├── generate_alias_name.sql    # +schema value becomes a table name prefix (silver_*, gold_*)
    └── generate_surrogate_key.sql # MD5 surrogate key over a list of columns
```

> **SQLFluff stubs** live in `.sqlfluff_macros/` (separate from `macros/` so dbt never picks them
> up at runtime). They mirror the project macros — `env_var.sql` and `generate_surrogate_key.sql`
> — so the jinja templater can lint models without a live dbt environment.

---

## Running locally

From the **project root**:

```bash
export PROJECT_ID=rentals-data-pipeline
export LOCATION=southamerica-east1

# Silver — parameterised per run
export CITY=macae
export SITES=vivareal,zapimoveis
export PROPERTY_TYPES=apartment,house
export FILE_DATE=2026-01-01   # omit or set empty to use CURRENT_DATE

# Gold — only FILE_DATE controls which scrape date to load
export FILE_DATE=2026-01-01   # omit to load CURRENT_DATE

# Run Silver
dbt run --profiles-dir dbt --project-dir dbt --select silver
dbt run --profiles-dir dbt --project-dir dbt --select silver --target dev

# Run Gold (dimensions then fact, or all at once — dbt resolves order via ref())
dbt run --profiles-dir dbt --project-dir dbt --select gold
dbt run --profiles-dir dbt --project-dir dbt --select gold --target prod

# Run a specific model
dbt run --profiles-dir dbt --project-dir dbt --select fact_listings_scrapes

# Tests only (same --target pattern applies)
dbt test --profiles-dir dbt --project-dir dbt --select silver
dbt test --profiles-dir dbt --project-dir dbt --select gold
```

Or from the `dbt/` directory directly (`profiles.yml` is auto-discovered):

```bash
cd dbt && dbt run --select gold --target prod
```

> **In Cloud Run** the task definitions under `cloud/tasks/` handle execution.
> `scripts/setup_docker.py` injects all env vars before launching dbt,
> so no manual export is needed.

---

## Configuration

### `profiles.yml`

Three targets (`dev`, `test`, `prod`) — each uses OAuth ADC, points at the same
`PROJECT_ID` and `LOCATION`, and lands in the dataset named after the target.
The default target is `dev`. Fallback defaults are set so SQLFluff can lint without
requiring the env vars to be exported first.

| Env var | Source | Purpose |
| --- | --- | --- |
| `PROJECT_ID` | `cloud/settings.yml :: project_id` | GCP project for BigQuery |
| `LOCATION` | `cloud/settings.yml :: location` | BigQuery dataset location |

The target dataset (`dev` / `test` / `prod`) is selected via the `--target` CLI flag, not an env var.
Defaults to `dev` when `--target` is omitted.

### `dbt_project.yml`

| Layer | Materialization | Strategy |
| --- | --- | --- |
| `silver` | incremental | merge |
| `gold` | incremental | merge |

All Gold models (dimensions and facts alike) use `incremental + merge`. Each model
declares its own `unique_key` and optionally `partition_by` / `cluster_by`.

---

## Models

### Silver — `models/silver/`

**Source:** `bronze_listings` in the target dataset (declared in `_sources.yml`).

| Model | Table name | Description |
| --- | --- | --- |
| `listings_deduped` | `{env}.silver_listings_deduped` | Flattened, NULL-coalesced, cross-site deduplicated listings. One row per `(LISTING_ID, SCRAPE_DATE)`. Rows without a URL are excluded. |

### Gold — `models/gold/`

**Source:** `silver_listings_deduped` via `{{ ref('listings_deduped') }}`.

All dimensions use an `IN_LAST_SCRAPE_FLAG` column (TRUE while the entity appears in the
latest scrape, FALSE once it disappears) and standard audit columns (`AUD_INS_TS`, `AUD_UPD_TS`).

#### Dimensions

| Model | Table name | Grain | unique_key |
| --- | --- | --- | --- |
| `dim_listings` | `{env}.gold_dim_listings` | One row per `LISTING_ID` | `LISTING_ID` |
| `dim_address` | `{env}.gold_dim_address` | One row per `(LISTING_ID, STREET_ADDRESS)` | `ADDRESS_SK` |
| `dim_amenities` | `{env}.gold_dim_amenities` | One row per `(listing, amenity)` | `['AMENITIES_SK', 'AMENITY_NAME', 'AMENITY_VALUE']` |
| `dim_images` | `{env}.gold_dim_images` | One row per `(listing, image URL)` | `['IMAGES_SK', 'IMAGE_URL']` |

**Surrogate keys** are MD5 hashes computed by `generate_surrogate_key()`:

| Key | Input columns | Used in |
| --- | --- | --- |
| `ADDRESS_SK` | `LISTING_ID`, `STREET_ADDRESS` | `dim_address`, `fact_listings_scrapes` |
| `IMAGES_SK` | `LISTING_ID`, `IMAGES` (full array) | `dim_images`, `fact_listings_scrapes` |
| `AMENITIES_SK` | `LISTING_ID`, `AMENITY_FEATURES` (full array) | `dim_amenities`, `fact_listings_scrapes` |

#### Facts

| Model | Table name | Grain | unique_key |
| --- | --- | --- | --- |
| `fact_listings_scrapes` | `{env}.gold_fact_listings_scrapes` | One row per `(LISTING_ID, SCRAPE_DATE)` | `['LISTING_ID', 'SCRAPE_DATE']` |

The fact stores all mutable measures (`PRICE_BRL`, `CONDO_FEE_BRL`, `FLOOR_SIZE_M2`,
`ROOMS`, `BEDROOMS`, `BATHROOMS`, `PETS_ALLOWED`) plus the surrogate keys for joining to
dimensions and degenerate dimensions (`SITE`, `CITY`, `PROPERTY_TYPE`, `PAGE`).

The `FILE_DATE` env var controls which scrape date is loaded per run:

```sql
WHERE SCRAPE_DATE = DATE('{{ file_date }}')  -- or CURRENT_DATE when not set
```

---

## Macros

| Macro | Override behaviour |
| --- | --- |
| `generate_schema_name` | Always returns the bare target schema (`dev` / `test` / `prod`); suppresses the `dev_silver` / `dev_gold` suffix dbt would otherwise append. |
| `generate_alias_name` | Prepends the `+schema` value from `dbt_project.yml` to the model name as a table prefix — e.g. `silver_listings_deduped`, `gold_dim_listings`. |
| `generate_surrogate_key(field_list)` | Returns an MD5 hex digest over the pipe-separated, null-coalesced string values of the given columns. Used by all Gold dimension and fact models. |

The result is a flat dataset layout:

```txt
dev.silver_listings_deduped
dev.gold_dim_listings
dev.gold_dim_address
dev.gold_dim_amenities
dev.gold_dim_images
dev.gold_fact_listings_scrapes
```

---

## Adding a new model

1. Place the `.sql` file under `models/<layer>/`.
2. Add `+schema: <layer>` in `dbt_project.yml` under `models.rentals_dbt.<layer>` if the layer is new.
3. Register columns and tests in `models/<layer>/_schema.yml`.
4. If the model reads from a new source table, declare it in `models/<layer>/_sources.yml`.
5. If the model uses a new project macro, add a matching stub in `.sqlfluff_macros/` so SQLFluff can lint without a live dbt environment.
