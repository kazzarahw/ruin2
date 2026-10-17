# AGENTS.md

Instructions for AI coding agents working in this repository. **Read this
file fully before making any change.** If the user's request conflicts with
this file, follow the user and mention the conflict. Humans: see `README.md`.

## What this project is

A Python 3.12 package managed with `uv`. All quality gates are configured in
`pyproject.toml` and run through the `Makefile`. The greeting example
(`cli` -> `services` -> `core`) demonstrates the required conventions;
replace it with real code as the project grows.

## Setup (once per clone)

```bash
make setup        # installs/refreshes the environment
```

Never install with `pip` directly. Dependencies change only through `uv add`.

## Commands

| Command | Purpose |
|---|---|
| `make check` | **The gate.** Hygiene, workflows, lint, types, architecture, deps, tests, coverage. |
| `make fix` | Auto-format and auto-fix. Run after every edit. |
| `uv run pytest tests/test_cli.py -q` | Run one test file while iterating. |
| `make typecheck` | Type-check the whole project. Never use `ty check <file>`: file mode can report a false green. |
| `uv run python-llm-template Ada` | Run the program. |

## Workflow -- follow these steps in order

1. **Read.** Open every file you plan to change, including its tests. Never
   edit a file you have not read in this session.
2. **Plan.** Write one short paragraph: what you will change, in which files.
   If the request is ambiguous, ask instead of guessing.
3. **Copy the pattern.** Find the closest existing code and match it (typing,
   error style, naming, tests). Do not invent new patterns.
4. **Change the minimum.** Touch only what the task requires. Do not refactor
   or reformat unrelated code.
5. **Test.** Add or update tests for every behavior change
   (see `docs/testing.md`).
6. **Fix.** Run `make fix` to auto-format and apply safe automatic fixes.
7. **Verify.** Run `make check`, then fix the first reported error and re-run.
   Repeat until it passes. Do not batch guesses across failures.
8. **Report.** Say what changed, list the files, and paste the final
   `make check` result. "Should work" is not done.

## Hard rules

1. Never weaken a check: no `# noqa`, `# type: ignore`, `# ty: ignore`, or
   `# pragma: no cover` comments; no edited thresholds. `make check` rejects
   suppression comments mechanically -- fix the code instead. If you believe
   a suppression is genuinely required, stop and ask the user.
2. Every function has full type annotations: parameters and return.
3. Every module, class, and public function has a docstring (ruff's `D` rules
   enforce this in `src/` and `scripts/`; tests are exempt). Comments explain
   *why*, never *what*.
4. Keep functions small. Enforced ceilings: 10 branches, 40 statements,
   5 returns, 5 arguments, complexity 10. Split the function; never raise
   the limits.
5. Keep files small. Source files over 300 lines fail `make check`
   (`tests/test_repo_policy.py`); keep tests and scripts in the same
   ballpark. A small model must be able to hold a whole file in context.
6. No `print()` in `src/` outside `src/python_llm_template/cli.py`.
   (Developer scripts under `scripts/` may print progress.)
7. Raise specific exceptions (`ValueError`, `TypeError`, ...) with clear
   messages. Never a bare `except:`; never `except Exception: pass`.
8. Tests: one behavior per test; no network, no sleeping, no dependence on
   order or wall-clock time. If something is hard to test, that is a design
   problem to fix, not to work around.
9. Do not add dependencies without asking the user first. The standard
   library comes first.
10. Never commit or push unless explicitly asked. Never touch `.env` files or
    anything inside `.git/`.
11. Respect the layers (enforced by import-linter):
    `cli` -> `services` -> `core`; `core` imports nothing from the package.

## Boundaries

Do not edit these to make a task pass; fix the code, or stop and ask:

- Tool configuration and thresholds in `pyproject.toml` -- the checks are
  the contract (rule 1).
- `Makefile`, `.github/workflows/`, and `docs/` -- process and CI files need
  human review.
- `scripts/bootstrap.py` -- the one-time rename tool, deleted right after
  bootstrap.

## Definition of done

- `make check` passes completely (hygiene, workflows, lint, format, types,
  architecture, deps, tests, coverage >= 85%), with no new suppression comments.
- New or changed behavior is covered by tests.
- Documentation is updated if behavior, structure, or commands changed.
- The final report lists what changed and shows the green `make check` output.

## Stop and reconsider if you catch yourself in one of these patterns

- **Kitchen sink** -- adding features or refactors nobody asked for.
- **Wrong abstraction** -- abstracting something that is used once.
- **Happy path only** -- handling the normal case while ignoring errors.
- **Runaway refactor** -- a small fix that cascades across many files.
- **Claiming done** -- reporting success without a green `make check`.

## Read before larger changes

- `docs/architecture.md` -- the layers and where new code belongs.
- `docs/conventions.md` -- style, typing, docstrings, error handling.
- `docs/testing.md` -- test structure, fixtures, property tests, coverage.
- `pyproject.toml` -- every tool configuration, with comments.
