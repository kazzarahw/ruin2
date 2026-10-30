# ruin

Web3 security-research toolkit: namespaced CLI plus an awaitable kernel API, packaged as a Prime Agent skill.

## Features

- Scope recon and rank targets.
- Run Slither and triage findings.
- Build research, RNG-hack, fuzz, trust, screen, and flow artifacts.
- Measure PoC drain on a fork with Foundry.

## Usage

Kernel (preferred): `import ruin` then await a namespace function, e.g.

```python
data = await ruin.source.fetch("0x...")
await ruin.bytecode.probe("0x...")
await ruin.protocol.model(ruin.ProtocolRequest(address="0x..."))
```

CLI: `ruin <namespace> <action> ...` over nine namespaces
(target source bytecode classes chain verify flow finding protocol).
Run `ruin --help` or `ruin <namespace>` for the action list.

See `SKILL.md` for the full namespace/API table and worked examples.

## Requirements
Foundry (`anvil`, `cast`, `forge`) and `slither` are required for execution-heavy
operations. Network access is required for target ranking and protocol mapping.