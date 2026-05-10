# src

Application code for the rentals data pipeline. Single top-level package — [`app/`](app/) — using the src-layout (`pythonpath = src` in [.code_quality/pytest.ini](../.code_quality/pytest.ini)).

## Layout

```text
app/
├── data/
│   └── scrapers/                  # Real-estate listing scrapers
│       ├── settings.py            # City / UF enums, CITIES_UF map, PropertyTypes
│       └── sites/
│           ├── base.py            # SiteScraper — URL build, fetch+parse, JSON-LD extract
│           ├── viva_real.py       # VivaRealScraper
│           └── zap_imoveis.py     # ZapImoveisScraper
├── entrypoints/
│   └── scraper_data_to_bucket.py  # Scrape every (site, property_type) pair → GCS
└── utils/                         # Shared cross-cutting helpers
    ├── decorators.py              # @task — start/end logging, exit-on-error
    ├── gcs.py                     # Bucket ABC + ScraperBucket descriptor
    └── utils.py                   # Environment, FileExtensions enums
```

## Packages

### [`app/data/scrapers/`](app/data/scrapers/)

Site-agnostic scraping. [`SiteScraper`](app/data/scrapers/sites/base.py) is the abstract base — subclasses bind `_SITE_NAME`, `_URL_TEMPLATE`, and a `_PROPERTY_TYPES: PropertyTypes` ClassVar. The fluent chain is `Scraper(city).set_url(property_type).fetch_and_parse_html().extract_properties()`. Fetches retry up to 3× on `requests.RequestException` with exponential backoff (tenacity); only HTTP 200 is treated as success. `extract_properties()` parses every `<script type="application/ld+json">` block and returns the listings inside the `ItemList` block indexed by `@id`. Adding a new site = a ~10-line subclass alongside [`viva_real.py`](app/data/scrapers/sites/viva_real.py).

### [`app/entrypoints/`](app/entrypoints/)

Runnable scripts. Each module exposes a single `@task(label=...)` function and a `if __name__ == "__main__":` guard. Run with:

```bash
poetry run python -m app.entrypoints.scraper_data_to_bucket
```

[`scraper_data_to_bucket.py`](app/entrypoints/scraper_data_to_bucket.py) iterates every `(site, property_type)` pair, scrapes, and uploads the JSON payload to the `ScraperBucket` location matching `<env>/<site>/<city>/<property_type>/<executed_at>.json`. Runtime parameters (`env`, `city`, `sites`, `property_types`) are module-level constants today — see the `TODO` markers; they'll move to a `RuntimeParameters` class.

### [`app/utils/`](app/utils/)

Cross-cutting helpers re-exported from [`app/utils/__init__.py`](app/utils/__init__.py):

- **`Environment`** (`dev`/`test`/`prod`) and **`FileExtensions`** (`json`) — `StrEnum`s used wherever the env scopes a path or a payload format is named.
- **`@task(label)`** — wraps an entrypoint callable to log start/end and total runtime, and `sys.exit(1)` on any raised exception. Use it on every entrypoint.
- **`Bucket` / `ScraperBucket`** ([`gcs.py`](app/utils/gcs.py)) — frozen dataclasses that own the GCS bucket name and key-prefix layout. `ScraperBucket` is `kw_only` and partitions by `env/site/city/property_type`; `blob_name(filename=..., extension=...)` joins prefix + filename + extension as a POSIX path.

## Conventions

- All imports use the absolute `app.…` path (the src-layout makes `app` the package root). No `from .foo import …`.
- Public enums and dataclasses are re-exported through `__init__.py` (`app.utils`, `app.data.scrapers`); reach for the re-export, not the inner module path, in callers.
- Dataclasses with multiple fields are declared `kw_only=True` — see `Bucket`/`ScraperBucket`.
- Tests live in [`tests/`](../tests/) mirroring this tree; conventions documented in [tests/README.md](../tests/README.md).
