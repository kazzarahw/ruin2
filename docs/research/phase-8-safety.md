# Phase 8 research: safety and scope enforcement

## Scope

Prevent out-of-scope execution.

## Non-goals

- No legal compliance engine.
- No policy DSL.

## Proposed minimal implementation

1. Add scope allowlists and denylists to `ReconSpec`.
2. Validate target authorization before running.
3. Add RPC budget counters.

## Acceptance tests

- Out-of-scope targets cannot run.

## Open questions

- How should authorization be represented?