# Phase 6 research: forensics and incident response

## Scope

Add transaction tracing and evidence bundle generation.

## Non-goals

- No full chain indexer.
- No attribution databases.

## Proposed minimal implementation

1. Add a `TransactionTrace` value object.
2. Add a service that calls RPC trace methods.
3. Render timelines in Markdown.

## Acceptance tests

- A transaction hash produces a timeline.

## Open questions

- Which RPC providers support tracing?