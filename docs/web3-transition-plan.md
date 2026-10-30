# Plan: Transition ruin2 to a general web3 security research toolkit

This plan moves `ruin2` from an EVM/Solidity/DeFi-focused fork-measurement
toolkit to a general web3 security research platform while preserving its core
ideology: pure core, strict gates, deterministic fork measurement, and
structured research artifacts.

## Current state

`ruin2` is a Python Prime Agent skill with:
- Pure core domain model and renderers
- Services for HTTP, files, subprocesses, Foundry, Slither
- CLI and Prime entry point
- Opt-in integration tests for Foundry and Slither
- Golden and property tests
- `make check` gate with 85%+ coverage

It currently assumes:
- EVM chains
- Solidity contracts
- ERC20-style balances
- DefiLlama target discovery
- Foundry and Slither tooling

## Target state

A general web3 security research toolkit supporting:
- Multiple chains and VMs
- Multiple smart-contract languages
- Off-chain and infrastructure targets
- Broader analyzer and fuzzer integrations
- Forensics and incident response
- Structured, multi-format reporting
- Safe scope enforcement

## Guiding principles

1. Keep the core pure and chain-agnostic.
2. Add chain/language/tool adapters at the service boundary.
3. Preserve deterministic fork measurement where possible.
4. Make every capability testable without network or external tools by default.
5. Prefer composable capabilities over monolithic workflows.

## Research prerequisite

Before each phase, create `docs/research/phase-N-<slug>.md` following
`docs/research-workflow.md`. Implementation starts only after the research note
is complete.

## Phase 1 — Abstract the core model

Goal: remove EVM/Solidity assumptions from core.

Tasks:
1. Introduce `Chain` and `Language` enums.
2. Make `ContractId` a generic address wrapper with chain-specific validators.
3. Add `Target` fields for chain, language, and scope metadata.
4. Replace ERC20-specific `Amount` assumptions with asset descriptors.
5. Add `Analyzer`, `Fuzzer`, and `Forensics` capability interfaces.

Acceptance:
- Core no longer imports EVM-specific concepts.
- Existing tests pass with updated fixtures.

## Phase 2 — Multi-chain and multi-language support

Goal: support non-EVM targets.

Tasks:
1. Add chain adapters for Solana, Cosmos, Move, Cairo, and Bitcoin.
2. Add language adapters for Vyper, Rust, Move, and Cairo.
3. Implement chain-specific address validation and RPC clients.
4. Add tool wrappers for chain-native analyzers and fuzzers.

Acceptance:
- A non-EVM target can be scoped and rendered.
- Integration tests cover at least one non-EVM chain.

## Phase 3 — Target discovery and scope ingestion

Goal: discover targets beyond DeFi.

Tasks:
1. Add Immunefi / Code4rena / Sherlock scope parsers.
2. Add GitHub repository discovery.
3. Add Etherscan / Sourcify verified-contract ingestion.
4. Add audit-report ingestion and prior-finding deduplication.
5. Add target allowlists and denylists.

Acceptance:
- A target can be imported from a bug-bounty scope.
- Duplicate findings are deduplicated across runs.

## Phase 4 — Analyzer and fuzzer expansion

Goal: broaden static and dynamic analysis.

Tasks:
1. Add Mythril, Manticore, and Echidna integrations.
2. Add Semgrep rules for Solidity and Vyper.
3. Add Halmos / Certora hooks.
4. Add fuzzer orchestration beyond Foundry.
5. Add bytecode-only analysis for unverified contracts.

Acceptance:
- At least two analyzers can run on the same target.
- Fuzzer results are recorded and rendered.

## Phase 5 — Off-chain and infrastructure security

Goal: cover web3 systems beyond smart contracts.

Tasks:
1. Add frontend and wallet analysis helpers.
2. Add API and oracle backend review workflows.
3. Add keeper and relayer infrastructure checks.
4. Add key-management and multisig review templates.

Acceptance:
- An off-chain target can be scoped and reported.
- Infrastructure findings use the same report model.

## Phase 6 — Forensics and incident response

Goal: support post-exploit analysis.

Tasks:
1. Add transaction tracing and fund-flow analysis.
2. Add address clustering and attribution helpers.
3. Add exploit replay and post-mortem generation.
4. Add on-chain event decoding.
5. Add evidence bundle generation.

Acceptance:
- A transaction hash can be turned into a timeline.
- Evidence bundles are reproducible.

## Phase 7 — Reporting and collaboration

Goal: make reports usable by teams and clients.

Tasks:
1. Add SARIF, JSON, and PDF export.
2. Add finding lifecycle states.
3. Add severity calibration.
4. Add deduplication across runs.
5. Add reviewer assignments and audit trails.

Acceptance:
- A report can be exported in at least three formats.
- Findings persist across sessions.

## Phase 8 — Safety and scope enforcement

Goal: prevent unsafe or out-of-scope execution.

Tasks:
1. Implement target authorization checks.
2. Add scope allowlists and denylists.
3. Add rate limiting and RPC budget controls.
4. Add secret handling and key isolation.
5. Add safe defaults for live vs fork execution.

Acceptance:
- Out-of-scope targets cannot be run.
- Live execution requires explicit authorization.

## Phase 9 — AI-agent ergonomics

Goal: make the toolkit effective for autonomous agents.

Tasks:
1. Add structured tool outputs for agents.
2. Add reusable research playbooks.
3. Add automated hypothesis generation.
4. Add finding confidence scoring.
5. Add integration with external knowledge bases.

Acceptance:
- An agent can run a full workflow end-to-end.
- Findings include confidence scores.

## Phase 10 — Final validation

Goal: declare the platform complete.

Tasks:
1. Run `make check` locally.
2. Run integration tests with `RUIN_INTEGRATION=1`.
3. Run mutation tests.
4. Verify Prime Agent installation.
5. Tag a release (`v1.0.0`).

Acceptance:
- All gates green.
- Release tagged on `main`.

## Risks

- Multi-chain support increases complexity.
- External tool availability varies.
- Formal verification integrations are heavy.
- Reporting formats require new dependencies.

## Non-goals

- No replacement of existing security tools.
- No centralized SaaS backend.
- No proprietary data collection.


## Progress update (2026-10-18)

Implemented and gated green (`make check`):

- Phase 1 (abstract core): done — Chain/Language enums, generic validators,
  pure on-chain read models (`core/onchain.py`).
- Phase 2 (multi-chain): read layer done — `services/rpc.py` transport and
  adapters for Solana, Move, Cairo/Starknet, CosmWasm, TON; `inspect` builds a
  chain-agnostic digest for any chain. Chain-native analyzers are empty where
  none exist; the researcher reasons from source/bytes.
- Phase 3 (discovery/ingestion): verified-source ingestion (`source` op,
  Sourcify + Etherscan) and `inspect --source`. Immunefi/Code4rena scope ingest
  intentionally dropped (targets are selected dynamically).
- Phase 4 (analyzers/fuzzers): Foundry/Echidna/Medusa fuzzers, Halmos/Mythril/hevm
  symbolic, Slither/Semgrep analyzers, bytecode format sniffing (`decode`).
- Phase 6 (forensics): traces, event-log scans, proxy resolution, exploit replay,
  and bytecode-based address clustering (`cluster` op: minimal-proxy clones and
  identical deployments grouped for attribution).
- Phase 7 (reporting): finding lifecycle, JSON output on every op, SARIF/JSON
  export, dedup and cross-run merge, known-exploit pattern DB (`exploits`).
- Phase 9 (agent ergonomics): structured JSON outputs, executable playbooks,
  confidence scoring, `inspect`/`source`/`exploits` reasoning surfaces, and
  hypothesis generation (`hypotheses` op) from checks plus agent signals.

- Phase 5 (off-chain/infra): review templates for keeper, oracle-backend,
  multisig, and bridge-relayer components (`infra` op).

Intentionally not built: Phase 8 scope/safety enforcement (the toolkit is a power
tool; scope is the agent's job).

Not yet done: broader non-EVM live
integration tests (Move/Cairo/CosmWasm/TON public RPCs), and making
`make mutation` a hard gate. Built-in playbooks now ship inside the package
(`src/ruin/playbooks/`), and the analyzers were refactored to inject their
subprocess runner instead of monkeypatching a module global, yet mutmut's clean
baseline still fails: its trampoline, running from the copied `mutants/` tree,
does not preserve constructor-injected collaborators, so an injected runner is
dropped and a clean test fails. This is a mutmut-sandbox limitation, not a
toolkit defect, so mutation stays an opt-in best-effort tool. Live Solana
integration is covered; `v1.0.0` is tagged.
