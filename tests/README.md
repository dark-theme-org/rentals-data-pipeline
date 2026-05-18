# tests

Pytest suite for `src/`. Layout mirrors the source tree one-to-one: `src/X/Y/foo.py` is covered by `tests/X/Y/test_foo.py`.

## Running

```bash
poetry run pytest -c .code_quality/pytest.ini
```

A single file or test:

```bash
poetry run pytest -c .code_quality/pytest.ini tests/app/utils/test_gcs.py
poetry run pytest -c .code_quality/pytest.ini tests/app/utils/test_gcs.py::test_scraper_bucket_name
```

Config lives in [.code_quality/pytest.ini](../.code_quality/pytest.ini) — sets `pythonpath = src` for
the src-layout, scopes discovery to `tests/`, enables `--strict-markers --strict-config`, and requires
**90 % coverage** as a hard gate. Pytest also runs as the final pre-commit hook (see [.pre-commit-config.yaml](../.pre-commit-config.yaml)).

## Environment variables

`pytest.ini` pre-sets the GCP runtime variables via `pytest-env`:

```ini
env =
    ENVIRONMENT=dev
    CITY=macae
    SITES=vivareal,zapimoveis
    PROPERTY_TYPES=apartment,house
    UPLOAD_TO_GCS=true
    START_PAGE=1
    MAX_PAGE=-1
```

These allow `ScraperParameters.from_env()` — called at module level in
`scraper_data_to_bucket.py` — to succeed during test collection without real
GCP credentials. Individual tests that need to override or remove a variable
use `monkeypatch.setenv` / `monkeypatch.delenv`.

## Shared fixtures (`tests/conftest.py`)

| Fixture | Type | Description |
| --- | --- | --- |
| `env` | `Environment` | `Environment.DEV` |
| `file_extension` | `FileExtensions` | `FileExtensions.JSON` |
| `expected_city` | `str` | `"macae"` |
| `expected_uf` | `str` | `"rj"` |
| `sa_email` | `str` | Throwaway SA email for credential tests |
| `scraper_bucket` | `ScraperBucket` | Bound to `(dev, vivareal, macae, apartment)` |
| `valid_scraper_env` | `dict` | Raw env-var dict for `ScraperParameters.model_validate(...)` |
| `scraper_params` | `ScraperParameters` | Single-site/type instance for entrypoint tests |
| `scraper_params_no_upload` | `ScraperParameters` | Same but `upload_to_gcs=False` |
| `scraper_params_with_max_page` | `ScraperParameters` | Same but `max_page=1` for loop-termination tests |
| `item_list_payload` | `dict` | JSON-LD `ItemList` with two listings |
| `html_with_item_list` | `str` | HTML page embedding `item_list_payload` |
| `html_without_item_list` | `str` | HTML page with no `ItemList` block |
| `html_with_bad_json` | `str` | HTML page with malformed JSON-LD |
| `fast_retry` | `None` (side-effect) | Patches `tenacity.nap.time.sleep` — apply with `@pytest.mark.usefixtures` |
| `fast_long_sleep` | `None` (side-effect) | Patches `time.sleep` in the entrypoint — apply with `@pytest.mark.usefixtures` |

## Conventions

- **Shared fixtures live in [tests/conftest.py](conftest.py)** — even when only one test file uses them. No per-package `conftest.py`.
- **Fixture naming**: `@pytest.fixture(name="x") def x_(...)`. Public name + underscored function dodges `pylint W0621` without per-line disables.
- **Side-effect-only fixtures** (e.g. `fast_retry`) are applied via `@pytest.mark.usefixtures("name")` on the test, not as a parameter.
- **`mocker` is typed as `MockerFixture`** from `pytest_mock`, not `# type: ignore`.
- **Patch at the import site** — `app.data.scrapers.sites.base.requests.get`, not `requests.get`. Once the SUT has bound the name at import time, patching the source does nothing.
- **Abstract base classes** with unset `ClassVar`s are tested via `monkeypatch.setattr(BaseCls, "_VAR", ..., raising=False)` inside a fixture — never via a `_StubX` subclass in the test file.
- **Scope is narrow by design** — one success-path test per public method, plus one test per documented `Raises:` clause. Skip trivial Python builtins (`KeyError` on dict miss, plain `AttributeError`, dataclass default checks).

## Adding tests

Use the `/pytest` skill — it mirrors `src/` into `tests/`, reuses or extends `tests/conftest.py`, and runs the suite end-to-end. If you write tests by hand, follow the conventions above and keep new fixtures in the root `conftest.py`.
