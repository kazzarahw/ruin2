# Ruin

Security-research tooling for EVM chains: contract discovery, verification, and analysis pipelines aimed at finding real, on-chain vulnerabilities — with a bias toward *cold* (under-researched) contracts rather than the well-picked-over TVL top-60.

## What it does

- **Multi-chain core** — chain registry (EVM + Cosmos), explorer/chain-id resolution by slug (`--chain robinhood`, `--chain core`, …)
- **Target discovery** — cold-band selection: probe under-verified, low-attention deployments instead of only the usual DeFi blue chips
- **Verification pipeline** — Sourcify metadata-pinned `solc` versions, remappings-aware compilation, full source-bundle staging, verified-implementation preference
- **Analysis modules** — callgraph, decompile, bytecode/decode, honeypot, oracle, flash-loan, invariants, clustering, fuzzing hooks, forensics, exploit scaffolding
- **Findings & flow** — first-class finding/hypothesis domain model for structured reporting
- **Agent-friendly** — ships with an agent skill (`SKILL.md`) so AI coding agents can drive it mechanically

## Status

Active research WIP. APIs will move; correctness gates will not. One `make check` gate runs every static check — nothing is "done" until it passes. CI, CodeQL, integration, and mutation-testing workflows included.

## Quickstart

```bash
pip install -e .
python -m ruin --help
make check
```

## Layout

- `src/ruin/api/` — public surface (targets, chains, verification, findings)
- `src/ruin/core/` — analysis modules and chain logic
- `docs/` — architecture, research phase plans, playbooks
- `.prime/agent/skills/ruin/` — packaged agent skill

## License

See LICENSE.
