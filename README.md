# python-llm-template

A Python project template tuned for AI coding agents -- especially small,
locally-hosted models (9B-35B) -- that enforces code **cleanliness**,
**stability**, and **consistency** with fast, deterministic checks.

<!-- After pushing, replace <owner>/<repo> and uncomment:
[![CI](https://github.com/<owner>/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<owner>/<repo>/actions/workflows/ci.yml)
-->

## Why this exists

Small models write plausible code; plausible is not correct. Their signature
failure modes are well documented: drive-by refactors, abstractions for
single-use code, happy-path-only implementations, and reporting "done"
without verification. Instructions alone do not stop this -- agents forget
them mid-task. So this template makes correctness mechanical:

- **One gate, one answer.** `make check` runs every check. Nothing is "done"
  until it is green; CI runs the same gate after verifying the lockfile.
- **Rules the tools enforce**, not rules the prompt politely suggests:
  complexity ceilings, full type annotations, docstrings, import layers,
  coverage floor, warnings-as-errors.
- **No suppression vocabulary.** `# noqa`, `# type: ignore`, and
  `# pragma: no cover` fail the gate: the code gets fixed, not silenced.
- **A short instruction file for agents** (`AGENTS.md`) plus `docs/` for
  progressive disclosure, so small context windows are used well.
- **Small units everywhere** -- small functions, small files, small rules --
  because a 9B model does not have room for anything larger.

## What's inside

| Concern | Tool | Enforces |
|---|---|---|
| Environment | uv + committed lockfile | Reproducible installs |
| Style & lint | ruff (curated strict set) | Formatting, imports, bug patterns, complexity ceilings |
| Types | ty | Annotations everywhere; honest types |
| Architecture | import-linter | `cli` -> `services` -> `core`; no reverse imports |
| Tests | pytest + pytest-cov (85% gate) | Behavior of every layer |
| Flakiness | pytest-timeout, warnings-as-errors | No hangs, no hidden warnings |
| Edge cases | Hypothesis | Property-based tests for pure logic |
| Dependencies | deptry | No unused or missing runtime dependencies |
| Repo policy | `tests/test_repo_policy.py` | No suppressions; small source files |
| File hygiene | prek + pre-commit hooks | YAML/TOML, merge conflicts, secrets, large files |
| Workflows | actionlint | Valid actions, inputs, and shell in `.github/workflows` |
| CI | GitHub Actions | `make check` as the single required check |
| Security | CodeQL, pip-audit, detect-private-key | Vulnerable deps, unsafe patterns, leaks |
| Test quality | mutmut (weekly CI job) | Tests that actually catch bugs for review |

## Quickstart

1. On GitHub, click **Use this template**, then clone your new repository.
2. Rename the project (once):
   ```bash
   python3 scripts/bootstrap.py my-project-name
   ```
3. Install and verify:
   ```bash
   make setup
   make check      # must pass before you write any code
   ```
4. (Optional) install the git hooks: `make hooks`.

After bootstrapping, delete `scripts/bootstrap.py` (one-time tool) and set
`[project].authors` in `pyproject.toml`.

## Daily workflow

| Command | What it does |
|---|---|
| `make fix` | Auto-format and apply safe fixes |
| `make check` | The full gate: hygiene, workflows, lint, types, architecture, deps, tests, coverage |
| `make test` | Tests with coverage only |
| `make hygiene` | YAML/TOML, merge conflicts, secrets, large files (part of `make check`) |
| `make workflows` | Lint `.github/workflows` (part of `make check`) |
| `uv run pytest tests/test_cli.py -q` | One test file while iterating |
| `uv run python-llm-template Ada` | Run the program |

## Customization

- **Coverage floor:** `[tool.coverage.report] fail_under` in `pyproject.toml`.
- **Python version:** `.python-version` and `requires-python`.
- **Complexity ceilings:** `[tool.ruff.lint.mccabe]` / `[tool.ruff.lint.pylint]`.
- **Authors:** `[project].authors` in `pyproject.toml` (template placeholder).
- **Optional extras:** delete `hypothesis` tests, `.github/workflows/mutation.yml`
  (mutation testing), or `.github/workflows/codeql.yml` if you do not want them.
- **More CI platforms:** follow the comment in `.github/workflows/ci.yml` (it
  replaces the `runs-on` line).

## How the pieces fit

- `make check` is the definition of done; CI runs the same gate after
  verifying the lockfile is current.
- `AGENTS.md` is the single source of agent instructions (Codex, opencode,
  Copilot, and Claude Code read it natively; other tools can be pointed at it).
- `pyproject.toml` is the single home for tool configuration.
- `docs/` holds the detail that should not live in a prompt: architecture,
  conventions, and testing practice.

## License

MIT
