# Phase 4 research: analyzer and fuzzer expansion

## Scope

Add analyzer and fuzzer capability interfaces and at least one non-Slither
backend.

## Non-goals

- No full Mythril/Manticore integration yet.
- No symbolic execution.

## Ecosystem coverage

Tools: Slither, Mythril, Echidna, Medusa, Foundry, Halmos, Semgrep.

## Relevant codebase touchpoints

- `src/ruin/core/runs.py`: `Analyzer`, `Fuzzer`
- `src/ruin/services/slither.py`
- `src/ruin/services/subprocesses.py`

## Proposed minimal implementation

1. Define analyzer result normalization.
2. Add a second analyzer wrapper (e.g. Semgrep) behind the `Analyzer` protocol.
3. Add fuzzer result ingestion for Foundry fuzz output.

## Acceptance tests

- Two analyzers can run on the same fixture.
- Fuzzer results parse into `FuzzResult`.

## Open questions

- Should analyzers return `Vuln` directly or raw findings?