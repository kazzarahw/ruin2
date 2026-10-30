# Plan: Security-research feature improvements for ruin2

This plan focuses on research capabilities, not CLI polish. It assumes the
current EVM/Solidity/DeFi core is stable and `make check` is green.

## Current security-research capabilities

- Recon scoping and target construction
- DefiLlama target ranking and chain filtering
- Protocol mapping into recon documents
- Slither SAST to `Vuln` candidates
- LLM-assisted review scaffolds
- Foundry fork measurement and drain proofs
- Research cards
- Raw bytecode decoding
- RNG-hack assessment
- Fuzz result recording
- Trust-model assessment
- Target screening
- Pipeline orchestration
- Report bundles
- Vuln triage
- Immunefi scope ingestion (EVM only)
- Chain-aware address validation and adapters

## Missing security-research capabilities

### 1. Real fuzzing orchestration

Current `fuzz` only records results. The toolkit should actually run fuzzers.

Tasks:
- Add `forge fuzz` / invariant execution orchestration.
- Add Echidna and Medusa adapters.
- Store counterexamples as structured artifacts.
- Link fuzz results to findings.

Acceptance:
- A fuzz campaign can be launched from the CLI.
- Counterexamples are preserved and rendered.

### 2. Symbolic execution and formal verification

Tasks:
- Add Halmos / Mythril / Certora hooks.
- Normalize solver output into `Vuln` candidates.
- Distinguish proven, undecided, and unsupported results.

Acceptance:
- Symbolic results appear in the report.
- Missing solvers fail clearly.

### 3. Multi-chain target discovery

Tasks:
- Add adapters for Solana, Move, Cairo, and CosmWasm.
- Add chain-specific address validation and RPC clients.
- Add target discovery from Immunefi, Code4rena, and Sherlock.

Acceptance:
- A non-EVM target can be scoped and reported.
- Chain-specific analyzers run.

### 4. Forensics and incident response

Tasks:
- Add transaction tracing and fund-flow analysis.
- Add address clustering and attribution.
- Add exploit replay and post-mortem generation.
- Add evidence bundle generation.

Acceptance:
- A transaction hash produces a timeline.
- Evidence bundles are reproducible.

### 5. Finding lifecycle and evidence gating

Tasks:
- Add finding states: open, confirmed, fixed, accepted risk.
- Require evidence before a finding is marked confirmed.
- Add confidence scores.
- Add deduplication across runs.

Acceptance:
- Findings persist across sessions.
- Unconfirmed findings cannot be reported as confirmed.

### 6. Advanced SAST and pattern detection

Tasks:
- Add Semgrep rules for Solidity and Vyper.
- Add custom invariant detectors.
- Add proxy/upgradeability analysis.
- Add access-control graph analysis.

Acceptance:
- At least two analyzers run on the same target.
- Findings include detector source.

### 7. Reporting and collaboration

Tasks:
- Add SARIF, JSON, and PDF export.
- Add severity calibration.
- Add reviewer assignments and audit trails.
- Add client-ready report templates.

Acceptance:
- A report exports in at least three formats.
- Findings persist across sessions.

### 8. AI-agent research ergonomics

Tasks:
- Add structured tool outputs for agents.
- Add reusable research playbooks.
- Add automated hypothesis generation.
- Add finding confidence scoring.

Acceptance:
- An agent can run a full workflow end-to-end.
- Findings include confidence scores.

## Priority order

1. Real fuzzing orchestration
2. Symbolic execution and formal verification
3. Multi-chain target discovery
4. Forensics and incident response
5. Finding lifecycle and evidence gating
6. Advanced SAST and pattern detection
7. Reporting and collaboration
8. AI-agent research ergonomics

## Non-goals

- No GUI or web interface.
- No replacement of existing security tools.
- No centralized SaaS backend.