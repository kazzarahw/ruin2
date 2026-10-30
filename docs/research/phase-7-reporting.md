# Phase 7 research: reporting and collaboration

## Scope

Add multi-format export and finding lifecycle.

## Non-goals

- No hosted backend.
- No user accounts.

## Proposed minimal implementation

1. Add `to_dict()` methods to core models.
2. Add JSON and SARIF exporters.
3. Add finding status fields.

## Acceptance tests

- A report exports to JSON and SARIF.

## Open questions

- Should finding lifecycle be in core or services?