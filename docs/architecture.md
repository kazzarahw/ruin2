# Architecture

## The four layers

```
cli        src/ruin/cli.py       argument parsing, printing, exit codes
api        src/ruin/api/         awaitable kernel facade: typed requests, JSON/text results
services   src/ruin/services/    policy, orchestration, I/O
core       src/ruin/core/        pure logic: no I/O, no side effects
```

`core` sits at the bottom and may import only the standard library. Higher
layers may import lower ones -- never the reverse:

```
cli  --->  api  --->  services  --->  core
```

`cli` may also call `services` directly (it always has); `api` is the
kernel-first door: every namespace function is `await`-able from a Python
session (`import ruin; await ruin.source.fetch(...)`) and dispatches the
same operations the CLI exposes.

This is not a convention; it is enforced. `make arch` (import-linter) fails
if a lower layer imports a higher one, including indirectly.

## Where does new code go?

Ask these questions in order:

1. Does it parse command-line input, print output, or set an exit code?
   -> `cli`
2. Is it an awaitable kernel entry point wrapping an existing operation with
   a typed request object? -> `api`
3. Does it orchestrate multiple steps, talk to the outside world, or apply
   user-facing policy (defaults, formatting for display, retries)?
   -> `services`
4. Everything else: validation rules, calculations, decisions, data shapes.
   -> `core`

When in doubt, put logic in `core`. It is the easiest layer to test, and
moving code up is cheap; untangling it later is not.

## Adding a feature (the recipe)

1. In `core`, add the pure logic and its tests (`tests/test_<module>.py`).
2. In `services`, orchestrate it and add tests.
3. In `cli`, expose it and add tests.
4. In `api`, expose the awaitable namespace function (request dataclass in
   `api/_requests.py` when it would exceed five arguments) and add the
   consistency test case.
5. Run `make check`.

If a change does not fit the layers, stop and ask -- do not import across
layers to make it fit.

## Why layers at all?

A small model reads a handful of files per step. Layer rules make "where does
this belong?" a decision with exactly one right answer, keep files small, and
stop circular dependencies before they start. The import check runs in
milliseconds, so the feedback is free.
