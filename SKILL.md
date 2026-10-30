---
name: ruin
description: Kernel-first multi-chain DeFi security-research toolkit. `import ruin` and await typed calls across nine namespaces (target, source, bytecode, classes, chain, verify, flow, finding, protocol): rank and screen targets, fetch and triage verified sources, probe bytecode and proxies, screen bug classes (ERC-4626, cToken inflation, honeypot), read logs and replay, run fork PoC/fuzz/symbolic, enumerate and model a deployed protocol surface, run playbooks, and scaffold Foundry invariants. The namespaced CLI (`ruin <ns> <leaf>`) mirrors the API one-to-one. Use when researching a DeFi protocol, enumerating a deployed contract's surface, triaging findings, or packaging a report bundle.
---

# ruin

## Kernel first

`import ruin` in the persistent kernel. Every namespace function is `async` —
`await` it. Network-bound work runs off-thread; core logic is pure sync. Calls
return a JSON-safe `dict` (`JsonPayload`) when the operation has a structured
builder, otherwise rendered markdown `str`. Library users get exceptions
(`ValueError`, `TypeError`, `RuntimeError`, `OSError`, `KeyError`) — exit codes
are CLI-only.

```python
import ruin

data = await ruin.source.fetch("0x...")  # verified source (dict)
await ruin.bytecode.probe("0x...")  # outsider drain-selector smoke test
await ruin.chain.logs("0x...", ruin.BlockWindow(22_000_000, 22_001_000))
await ruin.protocol.model(ruin.ProtocolRequest(address="0x..."))
```

Wide operations take frozen request dataclasses, all re-exported at the top
level: `ScreenRequest`, `PocRequest`, `RunnerRequest`, `TriageRequest`,
`ProtocolRequest`, `BlockWindow`, `FindingDraft`, `ThinRequest`,
`OracleRequest`, `FlashloanRequest`. Narrow operations take plain arguments.

Generic escape hatch, sparingly — prefer the namespaces:
`await ruin.run(op, **kwargs)` / `await ruin.run_json(op, **kwargs)` dispatch
registered operation names (`"pipeline"`, `"hunt"`, `"triage"`,
`"ctoken-inflation"`, ...). Do not mix styles per operation mid-task.

## Namespaces

| Namespace | Purpose | Example leaf |
|---|---|---|
| `target` | pick and size hunt targets | `await ruin.target.rank(limit=10)`; `screen(ScreenRequest(name="Example", chain="ethereum"))` |
| `source` | verified sources: fetch, slither, triage, research | `await ruin.source.fetch("0x...", tree="src-dir")`; `triage(TriageRequest(name="Example", mode="exploits"))` |
| `bytecode` | live bytecode, proxies, offline decode | `await ruin.bytecode.probe("0x...")`; `selectors("0x...")` — address reads the on-chain dispatcher, a path or bare `0x` literal decodes offline |
| `classes` | screens for known bug classes | `await ruin.classes.erc4626_solvency("0x...")`; `ctoken_inflation("0x...")`; `honeypot_evm("0x...")` |
| `chain` | live reads, traces, exploit replay | `await ruin.chain.trace("0x...")`; `logs("0x...", BlockWindow(a, b))` |
| `verify` | PoC pipeline, fuzz/symbolic, scaffolds | `await ruin.verify.poc(PocRequest(recon_file="recon.json", name="Example", forge_test="test_drain", method="drain", rpc="https://..."))` |
| `flow` | pipeline status and playbooks | `await ruin.flow.status("Example")`; `run("standard-recon", params=["slug=yearn"])` |
| `finding` | local finding registry | `await ruin.finding.create(FindingDraft(finding_id="F1", title="Share inflation", file="f.json"))`; `list_findings("f.json")` |
| `protocol` | enumerate and model deployed protocols | `await ruin.protocol.enumerate_(ruin.ProtocolRequest(address="0x..."))` — `enumerate_` sidesteps the builtin |

`target hunt` JSON carries `scan_errors`/`scan_windows` so RPC-rejected
windows never masquerade as an empty chain; the recent-window cap is 10000
blocks, and `from_block`/`to_block` (CLI `--from-block`/`--to-block`, 0 =
latest) widen a sweep.

## CLI

Namespaced form mirrors the API: `ruin <ns> <leaf> [args]`, e.g.
`ruin verify poc recon.json --name Example --forge-test test_drain --method drain --rpc https://...`.
Bare `ruin` or `ruin <ns>` prints help.

- `--format json` is accepted before or after the leaf; operations without a
  structured builder print `{"operation": ..., "output": ...}` wrapping the
  rendered text. Many leaves write markdown to a file with `--out FILE`.
- Old flat names fail with a moved-name hint (`error: 'hunt' moved to
  'ruin target hunt'`) and exit 2.
- A first token that is not a namespace is parsed as `verify poc` arguments,
  so `ruin recon.json --name Example ...` still runs a PoC.
- Success exits 0; domain and usage errors print `error: ...` to stderr,
  exit 2.

Playbooks are named multi-step plans (`ruin flow playbook` /
`ruin.flow.run`): `--param key=value` overrides step inputs and `{last_file}`
chains artifacts between steps. `verify fuzz` records a result by default
(`--run` executes foundry/echidna/medusa); `verify symbolic` runs
halmos/mythril/hevm unless `--outcome` records instead.

## protocol

`ruin protocol resolve|enumerate|model|invariants ADDRESS [--chain SLUG]
[--rpc URL]`; kernel `ruin.protocol.*` takes `ProtocolRequest(address,
chain="ethereum", rpc=None)`.

- `resolve`: fetch verified sources, follow EIP-1967/EIP-1167/EIP-7702 to the
  implementation (verified implementation source preferred), compile
  pragma-pinned solc standard-json ASTs.
- `enumerate`: rank entrypoints by modifiers x state writes x risk tags
  (`initializer`, `owner-settable`, `ungated-value`).
- `model`: contracts, entrypoints, inheritance cycles, storage layout,
  events/errors, per-function state writes.
- `invariants`: candidate specs (supply monotonic, share-price
  non-decreasing, owner-settable params, unauthenticated value movers);
  `--scaffold DIR` writes Foundry invariant stubs with forge-std imports
  commented until remappings are confirmed.

Honest limits: one address resolves to one source bundle — the proxy shell or
its verified implementation, not every engine contract reached via external
calls. With no solc available the graph falls back to line-scanner facts
(textual modifier matching, no structs/enums/events, multi-line signatures
truncated; see `core/sol_parse.py`).

## Chains

`--chain SLUG` picks the chain's default RPC when `--rpc` is omitted; an
explicit `--rpc` always wins. An unknown slug with no `--rpc` raises
`ValueError` listing the known slugs. Single registry (`core/chains.py`):
ethereum, base, arbitrum, optimism, polygon, bsc, avalanche, sonic, linea,
scroll, berachain, cronos, hyperliquid, unichain, ink, megaeth, robinhood,
hemi, tempo, soneium, gnosis, celo, tac, fraxtal, coredao, kava, injective,
hedera, bouncebit. `classes cosmos-gov` reads Cosmos LCDs instead (default
neutron; osmosis, injective, cosmoshub, persistence, kava, celestia, stride,
dydx, akash; `--lcd` wins). Solana/TON leaves (`classes honeypot`,
`bytecode inspect`) use family-default RPCs. On `source fetch` and
`bytecode inspect`, `--chain`/`--chain-id` select the provider family, not an
EVM slug.

## Prerequisites

Foundry (`anvil`, `cast`, `forge`) and `slither` must be on PATH for the
operations that execute them (fork probes, `verify --run`, `source slither`).
Network access is needed for `target rank`/`map`/`hunt`, `source fetch`,
`chain` reads, and `protocol`. The toolkit boots its own anvil forks on local
port 8545. The kernel imports `ruin` through this skill's symlinked `src`, so
current repo code is importable without reinstalling.
