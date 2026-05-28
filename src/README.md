# src

Application code for the rentals data pipeline. Single top-level package — [`app/`](app/) — using the src-layout (`pythonpath = src` in [.code_quality/pytest.ini](../.code_quality/pytest.ini)).

## Layout

```text
app/
├── data/
│   ├── bigquery/                  # BigQuery table descriptors and SQL files
│   │   ├── settings.py            # AuditMetadata dataclass and SQL_PATH constant
│   │   ├── sql/                   # DDL and query files with {{ key }} placeholders
│   │   │   ├── create_bronze_listings_table.sql
│   │   │   ├── check_table_exists.sql
│   │   │   └── check_bronze_listings_exists.sql
│   │   └── tables/
│   │       ├── base.py            # Table abstract base class
│   │       └── bronze_listings.py # BronzeListingsTable and SourceMetadata
│   ├── gcs/                       # GCS bucket descriptors
│   │   └── buckets/
│   │       ├── base.py            # Bucket abstract base class
│   │       └── scraper.py         # ScraperBucket for scraped listings
│   └── scrapers/                  # Real-estate listing scrapers
│       ├── settings.py            # City, UF, PropertyTypes definitions
│       └── sites/
│           ├── base.py            # SiteScraper abstract base class
│           ├── viva_real.py       # VivaRealScraper
│           └── zap_imoveis.py     # ZapImoveisScraper
├── entrypoints/
│   ├── scraper_data_to_bucket.py  # Scrape listings and upload to GCS
│   └── gcs_to_bigquery_bronze.py  # Load GCS snapshots into BigQuery Bronze
└── utils/                         # Shared cross-cutting helpers
    ├── decorators.py              # @task decorator
    ├── utils.py                   # Enums, logging setup, credentials, datetime helpers
    └── validations.py             # Pydantic input parameter models
```

## Packages

### [`app/data/scrapers/`](app/data/scrapers/)

Site-agnostic scraping. [`SiteScraper`](app/data/scrapers/sites/base.py) is the abstract base — subclasses bind `_SITE_NAME`, `_URL_TEMPLATE`, and a `_PROPERTY_TYPES: PropertyTypes` ClassVar. The fluent chain is `Scraper(city).set_url(property_type).fetch_and_parse_html(page=N).extract_properties()`. Fetches retry up to 5× on `requests.RequestException` with randomised exponential backoff (tenacity, 2–30 s); HTTP 200 is success, HTTP 404 returns `None` to signal end-of-pagination, any other status raises. `extract_properties()` parses every `<script type="application/ld+json">` block and returns the listings inside the `ItemList` block indexed by `@id`. Adding a new site = a ~10-line subclass alongside [`viva_real.py`](app/data/scrapers/sites/viva_real.py).

### [`app/data/gcs/`](app/data/gcs/)

GCS bucket descriptors structured as a package mirroring the `scrapers/` pattern. `Bucket` (in [`buckets/base.py`](app/data/gcs/buckets/base.py)) is the abstract base; `ScraperBucket` (in [`buckets/scraper.py`](app/data/gcs/buckets/scraper.py)) partitions blobs by `env/site/city/property_type/page`. Key methods: `blob_name(filename, extension)` joins prefix + filename + extension; `glob_pattern` returns a template string used for server-side filtering (prefix is passed separately to `list_blobs`); `latest_blob(gcs_client, **kwargs)` formats the pattern with the caller-supplied kwargs and returns the most recently updated matching blob, or `None`.

### [`app/data/bigquery/`](app/data/bigquery/)

BigQuery table descriptors and metadata, structured as a package mirroring the `scrapers/` pattern. [`settings.py`](app/data/bigquery/settings.py) holds the `AuditMetadata` dataclass and `SQL_PATH` (an absolute `Path` pointing to [`bigquery/sql/`](app/data/bigquery/sql/)). `Table` (in [`tables/base.py`](app/data/bigquery/tables/base.py)) is the abstract base providing `exists`, `create`, `read_and_replace_params`, and `destination`. `BronzeListingsTable` (in [`tables/bronze_listings.py`](app/data/bigquery/tables/bronze_listings.py)) adds `blob_already_loaded`, `load_job_config`, `row_schema`, and the inner `SourceMetadata` dataclass. SQL files live in [`bigquery/sql/`](app/data/bigquery/sql/) and are resolved via `SQL_PATH` from `settings.py`.

### [`app/entrypoints/`](app/entrypoints/)

Runnable scripts. Each module exposes a single `@task(label=...)` function and a `if __name__ == "__main__":` guard.

[`scraper_data_to_bucket.py`](app/entrypoints/scraper_data_to_bucket.py) iterates every `(site, property_type)` pair and paginates through all pages from `START_PAGE` to `MAX_PAGE` (or until the site returns a 404 / empty page). Each page is uploaded individually to `<env>/<site>/<city>/<property_type>/<page>/<executed_at>.json`. When fast retries (tenacity) are exhausted, a two-level long-retry kicks in: sleep 30–90 s and retry the same page up to `MAX_LONG_RETRIES` times. Upload can be skipped via `UPLOAD_TO_GCS=false`.

[`gcs_to_bigquery_bronze.py`](app/entrypoints/gcs_to_bigquery_bronze.py) loads the latest scraped snapshot for a given `FILE_DATE` into `{env}.bronze_listings` in BigQuery. For each `(site, property_type)` pair it paginates through GCS pages, skips already-loaded blobs, transforms each listing via `BronzeListingsTable.row_schema`, and batch-loads via `load_table_from_json`. Creates the table on first run using the DDL in `app/data/sql/`. Upload can be skipped via `UPLOAD_TO_BQ=false`.

### [`app/utils/`](app/utils/)

Cross-cutting helpers re-exported from [`app/utils/__init__.py`](app/utils/__init__.py):

- **`Environment`** (`dev`/`test`/`prod`), **`FileExtensions`** (`json`) — `StrEnum`s loaded from `cloud/settings.yml` at import time; used wherever an env scope or a payload format is named.
- **`configure_logging(level=INFO)`** — attaches a `StreamHandler` to the root logger with a uniform format; idempotent (`basicConfig` is a no-op if a handler is already attached). Called once per entrypoint at module level.
- **`datetime_now_utc(date_trunc=False)`** — returns the current UTC time as an ISO-8601 string; `date_trunc=True` returns only the `YYYY-MM-DD` portion.
- **`@task(label)`** — wraps an entrypoint callable to log start/end and total runtime, and `sys.exit(1)` on any raised exception.
- **`get_credentials()`** — resolves Application Default Credentials via `google.auth.default()`; in Cloud Run resolves to the runtime SA, locally resolves to whatever `gcloud auth application-default login` configured.
- **`ScraperParameters` / `BronzeParameters`** ([`validations.py`](app/utils/validations.py)) — Pydantic models sharing a common `InputParameters` base (`project_id`, `location`, `environment`, `city`, `sites`, `property_types`, `version`, `start_page`, `max_page`, `file_extension`, `executed_at`). `ScraperParameters` adds `upload_to_gcs` and `max_long_retries` (controls the two-level retry in the scraper loop); `BronzeParameters` adds `upload_to_bq` and `file_date`.

## Conventions

- All imports use the absolute `app.…` path (the src-layout makes `app` the package root). No `from .foo import …`.
- Public enums, dataclasses, and Pydantic models are re-exported through `__init__.py` (`app.utils`, `app.data.scrapers`, `app.data.gcs`, `app.data.bigquery`); reach for the re-export, not the inner module path, in callers.
- Dataclasses with multiple fields are declared `kw_only=True` — see `Bucket`/`ScraperBucket`, `Table`/`BronzeListingsTable`.
- Tests live in [`tests/`](../tests/) mirroring this tree; conventions documented in [tests/README.md](../tests/README.md).
