# Phase 5 research: off-chain and infrastructure security

## Scope

Extend the report model to off-chain and infrastructure targets.

## Non-goals

- No automated frontend scanning.
- No cloud provider integrations.

## Proposed minimal implementation

1. Add an `OffChainTarget` variant or metadata to `Target`.
2. Add templates for API, keeper, and wallet review.
3. Reuse existing report rendering.

## Acceptance tests

- An off-chain target renders a report.

## Open questions

- Should off-chain targets use the same `Target` model?