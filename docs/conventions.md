# Conventions

Golden rule: **match the closest existing code.** These rules describe what
that code looks like. `make check` enforces most of them mechanically.

## Formatting

- ruff owns formatting. Never hand-format -- run `make fix`.
- Line length: 88 characters. Long strings/comments are flags to simplify.
- Double quotes, trailing commas, one import per line (ruff enforces all of
  this; do not fight it).

## Typing

- Every function: annotations on all parameters and the return type.
- Modern syntax only: `list[str]`, `X | None`, `int | str` (Python 3.12).
- Use `collections.abc` for abstract types (`Sequence`, `Iterable`, `Callable`).
- `Any` is a last resort; if you need it, say why in a comment.
- Public functions in `core` should be easy to type; if they are not, that is
  a design smell.

## Naming

- `snake_case` for modules, functions, variables; `PascalCase` for classes;
  `UPPER_CASE` for constants.
- Names say what a thing is: `build_greeting`, not `do_stuff` or `helper`.
- Boolean names read as questions: `is_valid`, `has_owner`.
- Test names state the behavior: `test_greet_rejects_blank_names`.

## Docstrings

- Every module gets a one-line summary. Ruff's `D` rules (Google convention)
  fail `make check` when a docstring is missing in `src/` or `scripts/`;
  tests are exempt.
- Classes: what an instance represents.
- Public functions: a one-line summary, plus `Args:`, `Returns:`, and
  `Raises:` sections when they add information. Example:

```python
def build_greeting(name: str) -> str:
    """Build a greeting for ``name``.

    Args:
        name: The name to greet. Surrounding whitespace is ignored.

    Returns:
        A greeting message such as ``"Hello, Ada!"``.

    Raises:
        ValueError: If ``name`` is blank or too long.
    """
```

- Do not restate the signature ("Args: name: the name"). Add meaning.

## Errors

- Validate inputs at the boundary and raise early.
- Raise specific built-in exceptions (`ValueError`, `TypeError`) for
  programming errors; define exception classes only when callers must
  distinguish failure modes from each other.
- Exception messages are lowercase, factual, and actionable:
  `"name must not be blank"`.
- Never swallow errors: no bare `except:`, no `except Exception: pass`.
  If you catch, either handle it fully or re-raise.

## Comments and output

- Comments explain *why*; the code explains *what*.
- `print()` is allowed only in `cli.py` (and in developer scripts under
  `scripts/`). Libraries and services return values or raise; the CLI decides
  how failures look to the user.

## Suppressions

There are none. `# noqa`, `# type: ignore`, `# ty: ignore`, and
`# pragma: no cover` fail `make check` (`tests/test_repo_policy.py`), ty is
configured not to honor `type: ignore` at all, and ruff flags unused `noqa`.
A suppression is never the fix: change the code, or ask the human to change
the contract.

## Constants and configuration

- No magic values: name constants at module level
  (`MAX_NAME_LENGTH = 50`).
- Configuration comes from arguments or environment variables -- never from
  editing code at import time.

## Dependencies

- Standard library first. Do not add dependencies without asking; every
  dependency is permanent surface area. When you `uv add` one, say why.
