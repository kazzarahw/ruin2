# Phase 1 research: abstract the core model

## Scope

Make the `ruin` core model chain- and language-aware without breaking the
existing EVM/Solidity workflow. This phase does not add new analyzers or chains;
it creates extension points.

## Non-goals

- No Solana/Move/Cairo support yet.
- No replacement of `ContractId` with a fully generic address in one step.
- No changes to the Prime skill packaging.

## Ecosystem coverage

The research shows web3 security spans multiple VM families:
- EVM: Solidity, Vyper
- Solana: Rust/Anchor
- Move: Sui and Aptos
- Cairo: Starknet
- CosmWasm: Rust-to-WASM
- TON: FunC/Tact

Each family has distinct address formats, asset models, and vulnerability
classes. A general toolkit must model chain and language explicitly.

## Relevant codebase touchpoints

- `src/ruin/core/ids.py`: `ContractId`, `ProtocolName`, `RpcUrl`
- `src/ruin/core/enums.py`: `TargetMode`, `Severity`, `VulnClass`
- `src/ruin/core/domain.py`: `Target`, `Vuln`, `Poc`, `DrainProof`, `Report`
- `src/ruin/core/recon.py`: `ReconEntry`, `ReconSpec`, `ReconResult`
- `src/ruin/core/protocols.py`: `ProtocolSummary`, `ProtocolDetail`
- `src/ruin/core/screen.py`: `TargetScreen`, `SourceAccess`
- `src/ruin/core/runs.py`: `RunConfig`, `RunOutput`, `Runner`

## External standards and tools

- EVM addresses: `0x` + 40 hex digits
- Solana: base58, 32-byte
- Move: 32-byte hex (Aptos/Sui)
- Cairo: felt / hex
- CosmWasm: bech32

## Compatibility risks

- Existing tests and golden files depend on `ContractId` and `Target`.
- Prime skill packaging expects stable public API.
- Changing `Target` fields could break CLI and operations.

## Proposed minimal implementation

1. Add `Chain` and `Language` enums.
2. Add `chain` and `language` fields to `Target` with defaults for EVM/Solidity.
3. Introduce `Asset` descriptor alongside `Amount`.
4. Add `Analyzer` and `Fuzzer` capability protocols in `core/runs.py`.
5. Keep `ContractId` as the EVM validator; add a generic `Address` alias later.

## Acceptance tests

- Existing tests pass unchanged.
- A target can be constructed with `chain=Chain.EVM`, `language=Language.SOLIDITY`.
- Golden tests still pass.

## Open questions

- Should `Chain` include testnets or only mainnets?
- Should `Language` be a string or enum for extensibility?
- How much of the EVM-specific `Amount` should move to `Asset`?