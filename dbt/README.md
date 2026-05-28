# dbt/

dbt project (`rentals_dbt`) for the transformation layer of the Rentals Data Pipeline. Reads
from the BigQuery Bronze table and produces cleaned, deduplicated Silver models — all landing in
the same environment dataset (`dev` / `test` / `prod`) with a layer prefix on the table name.

## Structure

```txt
dbt/
├── dbt_project.yml       # Project config — name, profile, model paths, layer materializations
├── profiles.yml          # Connection profiles; reads PROJECT_ID, LOCATION from env vars
├── models/
│   └── silver/
│       ├── _schema.yml   # Column docs and dbt tests for Silver models
│       ├── _sources.yml  # Declares bronze_listings as the Bronze source
│       └── listings_deduped.sql
└── macros/
    ├── generate_schema_name.sql  # All models land in the bare target dataset (no _silver suffix)
    └── generate_alias_name.sql   # +schema value becomes a table name prefix (silver_*, gold_*)
```

---

## Running locally

From the **project root**:

```bash
export PROJECT_ID=rentals-data-pipeline
export LOCATION=southamerica-east1
export CITY=macae
export SITES=vivareal,zapimoveis
export PROPERTY_TYPES=apartment,house
export FILE_DATE=2026-01-01   # omit or set empty to use CURRENT_DATE

# dev (default — omit --target or pass it explicitly)
dbt run --profiles-dir dbt --project-dir dbt --select silver
dbt run --profiles-dir dbt --project-dir dbt --select silver --target dev

# test
dbt run --profiles-dir dbt --project-dir dbt --select silver --target test

# prod
dbt run --profiles-dir dbt --project-dir dbt --select silver --target prod

# Tests only (same --target pattern applies)
dbt test --profiles-dir dbt --project-dir dbt --select silver
```

Or from the `dbt/` directory directly (`profiles.yml` is auto-discovered):

```bash
cd dbt && dbt run --select silver --target prod
```

> **In Cloud Run** the `process_silver_layer` task handles execution. `scripts/setup_docker.py`
> injects all env vars from `cloud/tasks/process_silver_layer.yml` before launching dbt,
> so no manual export is needed.

---

## Configuration

### `profiles.yml`

Three targets (`dev`, `test`, `prod`) — each uses OAuth ADC, points at the same
`PROJECT_ID` and `LOCATION`, and lands in the dataset named after the target.
The default target is `dev`.

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
| `gold/dimensions` | table | — |
| `gold/facts` | incremental | merge |

---

## Models

### Silver — `models/silver/`

**Source:** `bronze_listings` in the target dataset (declared in `_sources.yml`).

| Model | Table name | Description |
| --- | --- | --- |
| `listings_deduped` | `{env}.silver_listings_deduped` | Flattened, NULL-coalesced, cross-site deduplicated listings. One row per `(LISTING_ID, SCRAPE_DATE)`. Rows without a URL are excluded. |

---

## Macros

Two macros override dbt's default naming logic so all models land in a **single flat dataset**
instead of per-layer datasets:

| Macro | Override behaviour |
| --- | --- |
| `generate_schema_name` | Always returns the bare target schema (`dev` / `test` / `prod`); suppresses the `dev_silver` / `dev_gold` suffix dbt would otherwise append. |
| `generate_alias_name` | Prepends the `+schema` value from `dbt_project.yml` to the model name as a table prefix — e.g. `silver_listings_deduped`, `gold_fact_listing_snapshots`. |

The result is a flat dataset layout:

```txt
dev.silver_listings_deduped
dev.gold_fact_listing_snapshots   (future)
dev.gold_dim_*                    (future)
```

---

## Adding a new model

1. Place the `.sql` file under `models/<layer>/`.
2. Add `+schema: <layer>` in `dbt_project.yml` under `models.rentals_dbt.<layer>` if the layer is new.
3. Register columns and tests in `models/<layer>/_schema.yml`.
4. If the model reads from a new source table, declare it in `models/<layer>/_sources.yml`.
