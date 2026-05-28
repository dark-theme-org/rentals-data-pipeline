# tests

Pytest suite for `src/`. Layout mirrors the source tree one-to-one: `src/X/Y/foo.py` is covered by `tests/X/Y/test_foo.py`.

## Running

```bash
poetry run pytest -c .code_quality/pytest.ini
```

A single file or test:

```bash
poetry run pytest -c .code_quality/pytest.ini tests/app/utils/test_utils.py
poetry run pytest -c .code_quality/pytest.ini tests/app/utils/test_utils.py::test_environment_members
```

Config lives in [.code_quality/pytest.ini](../.code_quality/pytest.ini) — sets `pythonpath = src` for
the src-layout, scopes discovery to `tests/`, and enables `--strict-markers --strict-config`.
Pytest also runs as the final pre-commit hook (see [.pre-commit-config.yaml](../.pre-commit-config.yaml)).

## Environment variables

`pytest.ini` pre-sets the GCP runtime variables via `pytest-env`:

```ini
env =
    USER=local
    PROJECT_ID=rentals-data-pipeline
    LOCATION=southamerica-east1
    ENVIRONMENT=dev
    CITY=macae
    SITES=vivareal,zapimoveis
    PROPERTY_TYPES=apartment,house
    UPLOAD_TO_GCS=true
    UPLOAD_TO_BQ=true
    FILE_DATE=2026-01-01
    START_PAGE=1
    MAX_PAGE=-1
    VERSION=0-0-1-test-pytest
```

These allow `ScraperParameters.from_env()` and `BronzeParameters.from_env()` — called at module
level in the entrypoints — to succeed during test collection without real GCP credentials.
Individual tests that need to override or remove a variable use `monkeypatch.setenv` /
`monkeypatch.delenv`.

## Shared fixtures (`tests/conftest.py`)

Only fixtures used by **2 or more** test files live here. Single-consumer fixtures stay in the
test file that owns them.

| Fixture | Type | Description |
| --- | --- | --- |
| `project_id` | `str` | `"rentals-data-pipeline"` — GCP project ID from `PROJECT_ID` |
| `location` | `str` | `"southamerica-east1"` — GCP location from `LOCATION` |
| `env` | `str` | `"dev"` — deployment environment from `ENVIRONMENT` |
| `expected_city` | `str` | `"macae"` — city slug from `CITY` |
| `expected_uf` | `str` | `"rj"` — canonical UF code for `UF.RJ` |
| `file_date` | `str` | `"2026-01-01"` — scrape date from `FILE_DATE` |
| `property_apartment` | `str` | `"ap"` — stub apartment slug for `PropertyTypes` |
| `property_house` | `str` | `"ho"` — stub house slug for `PropertyTypes` |
| `item_list_payload` | `dict` | JSON-LD `ItemList` with two listings |
| `scraper_bucket` | `ScraperBucket` | Bound to `(dev, vivareal, macae, apartment, page=1)` |
| `audit_metadata` | `AuditMetadata` | Fixed timestamps derived from `file_date` |
| `bronze_table` | `BronzeListingsTable` | Descriptor bound to dev env and `project_id` fixture |
| `raw_listing` | `dict` | Minimal raw listing dict as scraped from the source site |

## Conventions

- **Fixture placement**: fixtures used by ≥ 2 test files go in [tests/conftest.py](conftest.py); fixtures used by exactly one test file are defined locally in that file.
- **Fixture naming**: `@pytest.fixture(name="x") def x_(...)`. Public name + underscored function dodges `pylint W0621` without per-line disables.
- **Side-effect-only fixtures** (e.g. `fast_retry`) are applied via `@pytest.mark.usefixtures("name")` on the test, not as a parameter.
- **`mocker` is typed as `MockerFixture`** from `pytest_mock`, not `# type: ignore`.
- **Patch at the import site** — `app.data.scrapers.sites.base.requests.get`, not `requests.get`. Once the SUT has bound the name at import time, patching the source does nothing.
- **Abstract base classes** with unset `ClassVar`s are tested via `monkeypatch.setattr(BaseCls, "_VAR", ..., raising=False)` inside a fixture — never via a `_StubX` subclass in the test file.
- **Scope is narrow by design** — one success-path test per public method, plus one test per documented `Raises:` clause. Skip trivial Python builtins (`KeyError` on dict miss, plain `AttributeError`, dataclass default checks).

## Adding tests

Use the `/pytest` skill — it mirrors `src/` into `tests/`, reuses or extends `tests/conftest.py`, and runs the suite end-to-end. If you write tests by hand, follow the conventions above.
