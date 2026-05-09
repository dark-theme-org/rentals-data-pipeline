---
name: pytest
description: Generate clean pytest tests for a Python module under `src/`. Mirrors the source layout into `tests/`, reuses or extends `tests/conftest.py`, and follows the project's test conventions. Runs end-to-end without asking the contributor clarifying questions.
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, AskUserQuestion
---

# /pytest skill

Your task is to create or extend pytest tests for a given source folder.

There is **exactly one moment** when you ask the contributor anything: at the very start, via `AskUserQuestion`, to pick the target folder under `src/`. After that, run end-to-end — no follow-up questions, no confirmation gates. Resolve every other ambiguity from the source code itself.

## Step 0 — Ask which target (the only question allowed)

Before reading or writing anything, scan `src/` for candidate packages and surface them via `AskUserQuestion`:

1. Run `find src -type d -not -path '*/__pycache__*'` (or equivalent) to list every package directory under `src/`.
2. Cross-reference each with `tests/` to find packages whose modules are **missing** or have **incomplete** test coverage.
3. **Roll up siblings into their common parent.** If two or more sibling folders both need new or expanded tests, present the **parent** as a single option — never list the children separately. Walk the tree from `src/` downward and stop at the deepest common ancestor that still covers every candidate. Example: if both `src/app/data/scrapers/` and `src/app/data/scrapers/sites/` need tests, offer `src/app/data/scrapers` (one option, recurses into both); if only `sites/` needs tests, offer `src/app/data/scrapers/sites` directly.
4. Pick up to 3 such parent paths as concrete options (skip empty `__init__`-only dirs).
5. Present them with `AskUserQuestion`:

   - **question**: `"Which folder under src/ should the new pytest tests cover?"`
   - **header**: `"Test target"`
   - **options**: each option's `label` is a path like `src/app/data/scrapers`; `description` is a one-line summary of what lives there (derived from the `__init__.py` docstring or the filenames). The auto-provided **Other** lets the contributor type a custom path or a single file.
   - **multiSelect**: `false`

6. Treat the answer as the **target scope**: every `.py` module **recursively** under that folder (excluding `__init__.py`) gets tested. If the contributor provided a single file path, scope is just that file.

After this answer, do not ask the contributor anything during development. The **only** other allowed question is the final rollback gate (last step of the Process) — nothing in between.

## Tracking changes (required for the rollback gate)

Before writing or editing any file in the Process, capture enough state to undo every change:

- **`created_paths`** — list of paths the skill creates (test files, new `__init__.py`, new conftest if it didn't exist). Check existence with `ls`/`Read` first; if the path is absent, mark it as created the moment you write it.
- **`modified_paths`** — dict of `path → original content`. For any pre-existing file you intend to edit (typically `tests/conftest.py`), `Read` it first and stash the full content in memory before the first `Edit`.

Never restore files outside this tracked set — unrelated uncommitted work must remain untouched even on rollback.

## Process (after Step 0)

1. **Read every source file in scope** end-to-end. Identify:
   - Every public class/function/method.
   - Each method's documented `Raises:` clauses.
   - Class hierarchy: concrete subclasses are tested directly; abstract bases with unset `ClassVar`s use `monkeypatch.setattr(BaseCls, "_VAR", ..., raising=False)` in a fixture (do **not** create a `_StubX` subclass).
   - External calls (`requests`, `time`, third-party SDKs) — mock them at the *import site* (the SUT's module path), not the source.

2. **Resolve the test path** by mirroring the source layout: `src/X/Y/foo.py` → `tests/X/Y/test_foo.py`. Create any missing intermediate test subpackages with empty `__init__.py` files.

3. **Update `tests/conftest.py` first**:
   - Spot canonical input values, sample payloads, and side-effect patches that other tests will reuse.
   - Add fixtures using the **`@pytest.fixture(name="public_name") + def public_name_(...)`** pattern.
   - Reuse existing fixtures rather than duplicating.

4. **Write the test file** following the conventions below.

5. **Run pytest** to verify:

   ```bash
   poetry run pytest -c .code_quality/pytest.ini tests/X/Y/test_foo.py -v
   ```

   Fix any failures before moving on. If a failure exposes a real bug in `src/`, surface it to the contributor — do **not** modify `src/` to make a test pass unless that's clearly the intent.

6. **Confirm or rollback gate.** Before reporting, present the contributor with the only second `AskUserQuestion` of the run:

   - **question**: `"Keep the new tests, or roll back every change from this run?"`
   - **header**: `"Final check"`
   - **options**:
     - `"Keep"` — finalize and proceed to the report.
     - `"Rollback"` — revert every file the skill created or modified during this invocation.
   - **multiSelect**: `false`

   If the contributor picks **Rollback**:
   - For every path in `created_paths`: delete it (`rm`).
   - For every `path → original_content` in `modified_paths`: rewrite the file to its pre-run content.
   - Verify the working tree is back to its prior state (e.g. `git status` shows the same delta as before Step 0).
   - Report what was reverted (paths deleted + paths restored), and stop.

7. **Report** (only on Keep): test file paths (markdown links), number of tests added, any new conftest fixtures, and the pytest summary (`X passed in Ys`).

## Conventions

### Layout & naming
- Tests mirror `src/`: every source path has a corresponding test path.
- Filename prefix: `test_<module>.py` (matches the source filename).
- Every test subpackage has an `__init__.py`.
- Project pytest config is at `.code_quality/pytest.ini` — never duplicate it.

### Conftest (`tests/conftest.py`)
- All shared fixtures live in the root `tests/conftest.py`. Even fixtures used by only one test file go here — reuse beats local-only.
- **Fixture pattern**: register the public name via `name="..."` and suffix the function with an underscore. Avoids `pylint W0621` (`redefined-outer-name`) without per-line disables.

  ```python
  @pytest.fixture(name="expected_uf")
  def expected_uf_() -> str:
      """Canonical two-letter UF code expected for `UF.RJ`."""
      return "rj"
  ```

- **Type the `mocker` parameter**: `from pytest_mock import MockerFixture`, then `mocker: MockerFixture`. No `# type: ignore`.
- **Side-effect-only fixtures** (patches that return `None`) are applied via `@pytest.mark.usefixtures("name")` on the test, not as a parameter — avoids "unused parameter" hints.

  ```python
  @pytest.mark.usefixtures("fast_retry")
  def test_fetch_retries_then_raises(...): ...
  ```

### Docstrings
- **One-line docstrings everywhere** — modules, fixtures, tests. The code in `src/` is the source of truth for behavior; test docstrings only need to name the unit and the outcome (e.g. `"""Test set_url raises AttributeError when the property type is not declared."""`). Don't restate what the source docstring already explains.

### Test scope — only the necessary tests
- **One success-path test** per public method.
- **One test per documented `Raises:`** — exercise the contract, not Python builtins.
- Skip `KeyError` on dict miss, plain `AttributeError`, and other pure-Python behavior.
- Skip trivial dataclass init defaults — verifying `field(default=None)` returns `None` is not a unit test.
- Don't duplicate retry tests: one *transient → recovers* + one *persistent → exhausts* covers tenacity wiring and the project-specific exception path.
- Group tests by method — all `set_url` tests adjacent, all `extract_properties` tests adjacent.

### Test isolation
- **Don't subclass abstract bases in tests.** If a base class has unset `ClassVar`s expected to be bound by a subclass, patch them on the class via a `monkeypatch`-using fixture:

  ```python
  @pytest.fixture(name="stub_scraper")
  def stub_scraper_(monkeypatch: pytest.MonkeyPatch, ...) -> SiteScraper:
      """A `SiteScraper` instance with stub class-level templates patched in."""
      monkeypatch.setattr(SiteScraper, "_PROPERTY_TYPES", ..., raising=False)
      monkeypatch.setattr(SiteScraper, "_URL_TEMPLATE", ..., raising=False)
      return SiteScraper(city=City.MACAE)
  ```

- **Single source of truth via fixtures.** Pull canonical values from conftest; derive expected strings via `template.format(...)` rather than hardcoding `"https://.../rj/macae/ap/"`. Conftest changes propagate to assertions.
- **Module-level constants for repeated `mocker.patch` targets**:

  ```python
  _REQUESTS_GET = "app.data.scrapers.sites.base.requests.get"
  ```

### Network & retry
- Mock at the **import site** (the SUT's module path), not the source: `mocker.patch("app.data.scrapers.sites.base.requests.get", ...)`. Patching `requests.get` directly does nothing once the SUT has bound the name at import time.
- The `fast_retry` fixture patches `tenacity.nap.time.sleep` only — `time.sleep` is redundant since tenacity routes through `nap.time.sleep`.
- Verify retry count via `mock.call_count` (matches `stop_after_attempt(N)`); use `side_effect=[err, ok]` to test recovery in two calls.

## Templates

Minimal test file:

```python
"""<one-line summary of the module under test>."""

import pytest
from pytest_mock import MockerFixture

from app.X.Y.foo import SomeClass


def test_method_success(some_fixture, expected_value) -> None:
    """Test method returns the expected value on the success path."""
    ...


def test_method_raises_on_invalid_input(some_fixture) -> None:
    """Test method raises ValueError when the input is invalid."""
    with pytest.raises(ValueError, match="..."):
        ...
```

Fixture stub for conftest:

```python
@pytest.fixture(name="my_fixture")
def my_fixture_(other_fixture: SomeType) -> ReturnType:
    """One-line description of what this fixture returns."""
    ...
```
