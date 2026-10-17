# Architecture

## The three layers

```
cli        src/python_llm_template/cli.py       argument parsing, printing, exit codes
services   src/python_llm_template/services/    policy, orchestration, I/O
core       src/python_llm_template/core/        pure logic: no I/O, no side effects
```

`core` sits at the bottom and may import only the standard library. Higher
layers may import lower ones -- never the reverse:

```
cli  --->  services  --->  core
```

This is not a convention; it is enforced. `make arch` (import-linter) fails
if a lower layer imports a higher one, including indirectly.

## Where does new code go?

Ask these questions in order:

1. Does it parse command-line input, print output, or set an exit code?
   -> `cli`
2. Does it orchestrate multiple steps, talk to the outside world, or apply
   user-facing policy (defaults, formatting for display, retries)?
   -> `services`
3. Everything else: validation rules, calculations, decisions, data shapes.
   -> `core`

When in doubt, put logic in `core`. It is the easiest layer to test, and
moving code up is cheap; untangling it later is not.

## Adding a feature (the recipe)

1. In `core`, add the pure logic and its tests (`tests/test_<module>.py`).
2. In `services`, orchestrate it and add tests.
3. In `cli`, expose it and add tests.
4. Run `make check`.

If a change does not fit the layers, stop and ask -- do not import across
layers to make it fit.

## Why layers at all?

A small model reads a handful of files per step. Layer rules make "where does
this belong?" a decision with exactly one right answer, keep files small, and
stop circular dependencies before they start. The import check runs in
milliseconds, so the feedback is free.
