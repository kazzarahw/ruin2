# Phase 3 research: target discovery and scope ingestion

## Scope

Ingest bug-bounty and audit scopes into recon entries.

## Non-goals

- No full multi-platform automation yet.
- No off-chain target support yet.

## Ecosystem coverage

Immunefi publishes machine-readable bounty JSON. Scope assets include
`smart_contract`, `websites_and_applications`, and other types. Chains are
reported as strings such as `ETH`, `Solana`, `Aptos`, `StarkNet`, and `Cosmos`.

## Relevant codebase touchpoints

- `src/ruin/core/recon.py`
- `src/ruin/services/http.py`
- `src/ruin/core/ids.py` (chain-aware validation)
- `src/ruin/core/enums.py` (`Chain`)

## External standards and tools

- Immunefi public API (`/public-api/bounties.json`)
- Immunefi scope JSON

## Compatibility risks

- `ReconEntry.address` is currently EVM-oriented.
- Non-EVM addresses cannot be represented as `ContractId`.
- Scope ingestion must not break existing recon tests.

## Proposed minimal implementation

1. Add `parse_immunefi_scope(json)` returning EVM `ReconEntry` items.
2. Extract smart-contract assets whose URLs contain an EVM address.
3. Map chain strings to `Chain`.
4. Defer non-EVM addresses until a generic `Address` type exists.

## Acceptance tests

- EVM smart-contract assets become recon entries.
- Non-EVM assets are skipped with a documented limitation.
- Malformed JSON raises a clear error.

## Open questions

- Should `ReconEntry.address` become a generic `Address`?
- Should scope ingestion be a service or core parser?