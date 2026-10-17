# Testing

Tests are the only proof that code works. The suite must pass locally
(`make check`) and in CI for anything to be considered done.

## Layout and naming

- One test file per source module: `src/.../foo/bar.py` -> `tests/test_bar.py`.
  When a file outgrows that, mirror the source tree (`tests/core/test_bar.py`).
- Test names state the behavior being verified:
  `test_greet_rejects_blank_names`, not `test_greet_2`.
- One behavior per test. If the name needs the word "and", split it.

## Structure

Follow arrange -- act -- assert, separated by blank lines:

```python
def test_greet_title_cases_the_name() -> None:
    service = GreetingService()

    greeting = service.greet("ada lovelace")

    assert greeting == "Hello, Ada Lovelace!"
```

Use `pytest.raises(..., match="...")` for errors so the message is pinned too.

## Fixtures and parametrization

- Prefer plain helper functions over fixtures; use fixtures for shared setup,
  `conftest.py` when shared across files.
- Keep fixtures small and obvious. A fixture that hides logic is a bug.
- Use `@pytest.mark.parametrize` for the same behavior across many inputs.

## Property tests (Hypothesis)

Example-based tests cover the cases you thought of. Property tests catch the
rest. Use them for pure logic in `core`:

- Assert invariants ("the greeting always starts with 'Hello, '"), not
  specific outputs.
- Keep strategies close to the test; filter only what the function rejects.

```python
@given(st.text(min_size=1, max_size=MAX_NAME_LENGTH).filter(lambda text: text.strip()))
def test_build_greeting_property_echoes_the_cleaned_name(name: str) -> None:
    assert build_greeting(name) == f"Hello, {name.strip()}!"
```

## Warnings are errors

`filterwarnings = ["error"]` turns any warning into a failure. When a
*dependency* starts emitting one (usually a deprecation), the remedy is a
targeted filter in `pyproject.toml` that names the dependency:

```toml
filterwarnings = [
    "error",
    "ignore:.*:DeprecationWarning:some_dependency",
]
```

Never relax the policy globally; a warning is either handled or pinned to a
specific dependency with a comment saying why.

## Policy tests

`tests/test_repo_policy.py` makes two AGENTS.md rules mechanical: the suite
fails on suppression comments anywhere in `src`, `tests`, or `scripts`, and
on source files longer than 300 lines. Treat its messages as design feedback,
not obstacles.

## What to never do

- No network access, no sleeping, no dependence on wall-clock time or test
  order. The suite must pass in any order, offline.
- Do not mock what you can construct: real objects and simple fakes first.
  Mock only at true I/O boundaries.
- Do not delete or weaken a test to make the suite pass; fix the code.
- Do not chase coverage numbers with trivial tests. 85% is a floor, not a goal.

## Running tests

| Command | Purpose |
|---|---|
| `uv run pytest tests/test_x.py -q` | One file while iterating |
| `uv run pytest -k pattern -q` | Tests matching a name |
| `make test` | Full suite with the coverage gate |
| `make check` | The complete gate; run before saying "done" |

## Mutation testing

Coverage says a line ran; mutation testing says a test would catch it being
wrong. Weekly CI runs `mutmut` (everything except `cli.py`, whose argparse
wiring only produces noisy survivors) and prints surviving mutants for
review.

Run it locally when touching either layer:

```bash
uv run mutmut run    # mutates the code, runs the tests, records survivors
uv run mutmut results
```

A survivor means no test noticed that behavior change. Each one is a real
gap: add a test that kills it (or delete genuinely redundant code). Typical
fixes are pinning exact error messages (`match="^...$"`) and testing exact
boundaries (`MAX`, `MAX + 1`).
