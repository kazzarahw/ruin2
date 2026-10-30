# Phase 2 research: multi-chain and multi-language support

## Scope

Add the first non-EVM address and language abstractions without replacing the
working EVM workflow. This phase establishes adapters, not full tool support.

## Non-goals

- No Solana/Move/Cairo analyzers yet.
- No RPC clients for non-EVM chains.
- No Foundry replacement.

## Ecosystem coverage

Address formats:
- EVM: `0x` + 40 hex digits
- Solana: base58, 32 bytes
- Aptos/Sui: `0x` + 64 hex digits
- Cairo: `0x` + up to 64 hex digits
- CosmWasm: bech32

Language families:
- Solidity / Vyper
- Rust / Anchor
- Move
- Cairo
- CosmWasm Rust

## Relevant codebase touchpoints

- `src/ruin/core/enums.py`: `Chain`, `Language`
- `src/ruin/core/ids.py`: `ContractId`
- `src/ruin/core/domain.py`: `Target`
- `src/ruin/core/recon.py`: `ReconSpec`, `ReconResult`
- `src/ruin/services/`: new chain adapter module

## External standards and tools

- Base58 (Solana)
- Bech32 (CosmWasm)
- Hex (EVM, Move, Cairo)

## Compatibility risks

- Existing EVM tests expect `ContractId` behavior.
- Adding fields to `Target` must preserve defaults.
- Golden tests must not change.

## Proposed minimal implementation

1. Add address validators for Solana, Move, Cairo, and CosmWasm.
2. Add a `ChainAdapter` protocol with `validate_address`.
3. Add a service registry mapping `Chain` to validators.
4. Add `chain` and `language` to `ReconSpec` and `ReconResult`.
5. Keep EVM as the default.

## Acceptance tests

- Validators accept valid addresses for each chain.
- Invalid addresses raise `ValueError`.
- Existing EVM tests pass.

## Open questions

- Should address validation be in core or services?
- Should non-EVM chains support fork measurement?