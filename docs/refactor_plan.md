# ruin2 refactor plan (v2, 2026-10-23) — audit findings folded in, claims verified

Requirements R1-R7 and constraints unchanged from v1. Research inputs: methodology.md
(verified: TRAIL, ConsenSys/surya, tryethernal), api-layout.md (PEP 660/621/695, argparse,
httpx/pytest design), codebase-audit.md (430 lines; top-10 HIGHs independently re-verified
against source + real clone bytecode).

## Architecture decisions (v2 changes marked *)
D1. CLI namespaces: target | source | bytecode | classes | chain | *verify | flow |
    protocol | finding. `verify` replaces v1's `exec` (reserved word; CLI verb reads
    better: `ruin verify poc|fuzz|symbolic`). Clean break, no hyphen aliases.
D2. Library surface = services modules re-exported through ruin/__init__ facade with
    __all__; ruin.source.fetch(...) etc. Phased: P1 wrappers return JSON-safe dicts
    (existing *_data payloads), P3/P4 migrate to frozen dataclasses with one shared
    serialize.to_dict (reporting.py deleted, F1).
D3. One implementation path per op: facade fn -> (typed dataclass|dict) + renderer +
    builder. This deletes the handler/builder copy-paste class (A2/E3/E4) by design,
    not by patching both copies.
D4. cli.py alone renders/prints/exits (0 ok, 1 domain, 2 usage); services raise typed
    exceptions (ValueError/TypeError subclasses already used).
D5. async facade for network-bound fns (kernel is async-first); core stays pure sync;
    cli uses asyncio.run at the single boundary.
D6. Playbook schema v2: operations keyed "ns.action"; executor passes STRUCTURED
    (text, written_path) between steps instead of regexing prose "wrote <path>" (D2 audit).
D7. Single chain registry (slug/id/rpc/lcd/aliases) in core consumed by parser defaults,
    hunt, solvency, honeypot, chains adapters (A10/E5: five sources today).
D8. Shared primitives replace 3-4x copies: follow_delegation (A6), find_balance_slot
    (A7), parse_cast_int (A8), one retry helper (A9), fork(port, rpc) context manager
    (A11), ANVIL_DEV constants (A12), write_or_render (A4), rpc_for (A5), checks_from (A3).
D9. memoization: @lru_cache(maxsize=256) on extract_selectors returning TUPLE (G1),
    then template_family/minimal_proxy_implementation/stale_lock_present/decode_bytecode
    (G2); per-call dict literals -> module constants (G3).
D10. quick correctness fixes land first: clustering clone suffix via probe
    (F3 + real-bytecode fixture), SymbolicOutcome ERRORED member deleted (B2),
    cli json single-dispatch (A1), known-set derived from parser (E6), core/solc
    tree_preference I/O -> services (B1).
D11. dead code deleted with its tests: reporting.py, ~15 core symbols, duplicate
    PipelineStage/StageStatus, alias sets propped only by tests (F1/F2/H3).
D12. tests: keep one golden per renderer; move behavior assertions to JSON payloads;
    fix disjunctive asserts (H1/H2/H4).
D13. human-approval proposals stay proposals: ruff target-version py312->py311 (H1),
    README updated in P2. New file docs/refactor_plan.md committed now (additive).
    docs/architecture.md api-layer update was claimed here earlier but only landed
    in P7c; it is now applied and FLAGGED for human review.
D14. deviation from D2: the facade returns a JsonPayload|str envelope, not
    per-operation dataclasses. Typed *inputs* (request dataclasses) shipped;
    typed domain dataclasses live in core/services and are serialized per
    operation. Per-operation typed returns are a deferred follow-up.
D15. P7 integration review (0 BLOCKER / 5 MAJOR / 15 MINOR): MAJORs fixed in
    P7c (pipeline-status hint + completeness test, symbolic default parity,
    architecture.md, skill README, this note). MINORs deferred; list lives in
    /tmp/ruin-plan/p7_review.md.

## Phases (commit + adversarial review per phase)
P0 branch + baseline commits                                    [DONE]
P1a cli quick fixes: A1 single-dispatch, E6 derived known set   [THIS COMMIT]
P1b facade: 9 namespace modules wrapping existing ops; import
    ruin + ruin.source.fetch verified in kernel; api tests w/ fakes
P2  CLI nested subparsers (distinct dests, set_defaults),
    playbook schema v2 + built-in playbooks rewritten, wiring/consistency
    tests updated in same commit; README updated
P3  merges: triage+hypotheses+exploits -> source triage modes;
    fuzz/symbolic record+run -> verify fuzz|symbolic --record;
    decode+selectors -> bytecode selectors (path OR address);
    research/rng asymmetry normalized (E2/E4/E8)
P4  purity+SRP+memoization+dedup per audit: B1-B4, C2-C7, D1-D5,
    A3-A12 shared primitives, G1-G3, F2/F3/B2 fixes, H1-H4 tests
P5  protocol subsystem: core/sol_parse (pure, documented limits) ->
    core/callgraph (edges, ftrace, inheritance, cycles, state-var map) ->
    services/protocol resolver (1967/1167/clone + logs helpers) ->
    invariant specs + foundry scaffold; ruin protocol|ruin.protocol
P6  skill rewrite: SKILL.md kernel-first (import ruin, namespaces, protocol
    enumerate examples), sync symlink-src, sync --check + installed smoke tests
P7  verification: make check; RUIN_INTEGRATION=1 pinned-fork spot checks;
    dogfood strata/strUSD triage through new API (acceptance gate applies);
    memory/ledger updates; final report with green make check

## Verification log (what was checked, not assumed)
- cli.py read: double-dispatch + missing ctoken-inflation + CLI-side rng join: CONFIRMED.
- core/solc.py rglob/read_text: CONFIRMED layer violation.
- clustering suffix vs real clone bytecode (/tmp/ruin-hunt/clone_code.txt ends
  5af43d82803e903d91602b57fd5bf3): CONFIRMED unreachable clone path.
- enums SymbolicOutcome __eq__/__hash__ = object.__hash__: CONFIRMED.
- grep functools src/ -> 0; extract_selectors call sites -> 14: CONFIRMED.
- pyproject: hatchling src-layout, scripts->prime_entry:main, target-version py312
  vs requires-python >=3.11: CONFIRMED.
- skill import path: kernel resolves ruin via .prime skill symlink src -> repo:
  CONFIRMED (import ruin printed skill path).
