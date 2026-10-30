"""Guard that every API function forwards exactly what its CLI route produces.

Each API function must dispatch the registered operation name and a kwargs
dict identical to what the argparse parser would hand the handler for the
equivalent CLI invocation (minus renderer-only keys). This catches drift
between the typed facade and the CLI/handler contract in either direction.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
from typing import Any

import pytest

from ruin.api import (
    bytecode,
    chain,
    classes,
    finding,
    flow,
    protocol,
    source,
    target,
    verify,
)
from ruin.api._requests import (
    BlockWindow,
    FindingDraft,
    FlashloanRequest,
    HuntRequest,
    OracleRequest,
    PocRequest,
    ProtocolRequest,
    RunnerRequest,
    ScreenRequest,
    ThinRequest,
    TriageRequest,
)
from ruin.services.parsing import build_parser

MINARGS: dict[str, list[str]] = json.loads(
    (pathlib.Path(__file__).parents[1] / "fixtures" / "cli_argv.json").read_text()
)

CASES: list[tuple[Any, str, str, dict[str, Any], str, list[str]]] = [
    (target, "rank", "rank", {}, "rank", []),
    (target, "map_", "map", {"slug": "slug", "asset": "0x1"}, "map", []),
    (
        target,
        "screen",
        "screen",
        {"req": ScreenRequest(name="N", chain="ethereum")},
        "screen",
        [],
    ),
    (target, "trust", "trust", {"name": "N"}, "trust", []),
    (target, "hunt", "hunt", {"req": HuntRequest(token="0x1")}, "hunt", []),
    (target, "bundle", "bundle", {"name": "N"}, "bundle", []),
    (source, "fetch", "source", {"address": "0x1"}, "source", []),
    (source, "slither", "slither", {"source_path": "s.sol"}, "slither", []),
    (source, "review", "review", {"source_path": "s.sol"}, "review", []),
    (source, "analyze", "analyze", {"source_path": "s.sol"}, "analyze", []),
    (
        source,
        "triage",
        "triage",
        {"req": TriageRequest(name="N")},
        "triage",
        [],
    ),
    (
        source,
        "triage",
        "triage",
        {"req": TriageRequest(name="N", mode="exploits")},
        "triage",
        ["--mode", "exploits"],
    ),
    (
        source,
        "triage",
        "triage",
        {"req": TriageRequest(name="N", mode="hypotheses", signals=["oracle"])},
        "triage",
        ["--mode", "hypotheses", "--signal", "oracle"],
    ),
    (
        source,
        "research",
        "research",
        {"mechanism": "mech", "summary": ["sum"]},
        "research",
        [],
    ),
    (source, "access_map", "accessmap", {"source_path": "s.sol"}, "accessmap", []),
    (source, "infra", "infra", {"name": "N"}, "infra", []),
    (bytecode, "inspect", "inspect", {"address": "0x1"}, "inspect", []),
    (bytecode, "probe", "probe", {"address": "0x1"}, "probe", []),
    (bytecode, "selectors", "selectors", {"target": "0x1"}, "selectors", []),
    (bytecode, "decompile", "decompile", {"address": "0x1"}, "decompile", []),
    (
        bytecode,
        "cluster",
        "cluster",
        {"addresses": ["0x1"], "rpc": "R"},
        "cluster",
        [],
    ),
    (bytecode, "proxy", "proxy", {"address": "0x1"}, "proxy", []),
    (
        bytecode,
        "impl_diff",
        "impl-diff",
        {"new_impl": "0x1", "old_impl": "0x2"},
        "impl-diff",
        [],
    ),
    (bytecode, "slot_hunt", "slot-hunt", {"token": "0x1"}, "slot-hunt", []),
    (classes, "erc4626_solvency", "solvency", {"vault": "0x1"}, "solvency", []),
    (
        classes,
        "ctoken_inflation",
        "ctoken-inflation",
        {"ctoken": "0x1"},
        "ctoken-inflation",
        [],
    ),
    (classes, "honeypot", "honeypot", {"mint": "M"}, "honeypot", []),
    (classes, "honeypot_evm", "honeypot-evm", {"token": "0x1"}, "honeypot-evm", []),
    (
        classes,
        "thin_collateral",
        "thin-collateral",
        {"req": ThinRequest(token="0x1", market="0x2", factory="0x3", price_usd=1.0)},
        "thin-collateral",
        [],
    ),
    (
        classes,
        "rng_hack",
        "rng-hack",
        {"mechanism": "mech", "summary": ["sum"], "source": ["v"]},
        "rng-hack",
        [],
    ),
    (classes, "mintsig", "mintsig", {"address": "M"}, "mintsig", []),
    (classes, "cosmos_gov", "cosmos-gov", {}, "cosmos-gov", []),
    (chain, "trace", "trace", {"tx": "0xtx"}, "trace", []),
    (
        chain,
        "logs",
        "logs",
        {"address": "0x1", "window": BlockWindow(from_block=1, to_block=2)},
        "logs",
        [],
    ),
    (
        chain,
        "replay",
        "replay",
        {
            "tx": "0xtx",
            "address": "0x1",
            "window": BlockWindow(from_block=1, to_block=2),
            "rpc": "R",
        },
        "replay",
        [],
    ),
    (
        verify,
        "poc",
        "pipeline",
        {
            "req": PocRequest(
                recon_file="x.json", name="N", forge_test="T", method="M", rpc="R"
            )
        },
        "pipeline",
        [],
    ),
    (verify, "fuzz", "fuzz", {"req": RunnerRequest(target="t")}, "fuzz", []),
    (
        verify,
        "fuzz",
        "fuzz",
        {"req": RunnerRequest(target="t", run=True)},
        "fuzz",
        ["--run"],
    ),
    (
        verify,
        "symbolic",
        "symbolic",
        {"req": RunnerRequest(target="t", tool="halmos")},
        "symbolic",
        [],
    ),
    (
        verify,
        "symbolic",
        "symbolic",
        {"req": RunnerRequest(target="t", tool="halmos", run=True)},
        "symbolic",
        ["--run"],
    ),
    (
        verify,
        "oracle",
        "oracle",
        {"req": OracleRequest(target="0x1", rpc="R")},
        "oracle",
        [],
    ),
    (
        verify,
        "flashloan",
        "flashloan",
        {"req": FlashloanRequest(target="0x1", rpc="R")},
        "flashloan",
        [],
    ),
    (flow, "status", "pipeline-status", {"name": "N"}, "pipeline-status", []),
    (flow, "run", "playbook", {"name": "name"}, "playbook", []),
    (
        finding,
        "create",
        "finding-new",
        {"draft": FindingDraft(finding_id="id", title="title", file="f")},
        "finding-new",
        [],
    ),
    (
        finding,
        "update",
        "finding-update",
        {"finding_id": "id", "state": "state", "file": "f"},
        "finding-update",
        [],
    ),
    (finding, "list_findings", "finding-list", {"file": "f"}, "finding-list", []),
    (finding, "dedupe", "finding-dedupe", {"file": "f"}, "finding-dedupe", []),
    (
        finding,
        "merge",
        "finding-merge",
        {"file": "f", "other": "g"},
        "finding-merge",
        [],
    ),
    (
        protocol,
        "resolve",
        "resolve",
        {"req": ProtocolRequest(address="0x1")},
        "resolve",
        [],
    ),
    (
        protocol,
        "enumerate_",
        "enumerate",
        {"req": ProtocolRequest(address="0x1")},
        "enumerate",
        [],
    ),
    (
        protocol,
        "model",
        "model",
        {"req": ProtocolRequest(address="0x1", chain="base")},
        "model",
        ["--chain", "base"],
    ),
    (
        protocol,
        "invariants",
        "invariants",
        {"req": ProtocolRequest(address="0x1"), "scaffold": "d"},
        "invariants",
        ["--scaffold", "d"],
    ),
]


def _expected(operation: str, extra: list[str]) -> dict[str, Any]:
    parser = build_parser()
    ns = parser.parse_args([*MINARGS[operation], *extra])
    return {
        k: v
        for k, v in vars(ns).items()
        if k not in ("command", "action", "format", "operation", "out")
    }


@pytest.mark.parametrize(
    "case", CASES, ids=[f"{c[0].__name__}.{c[1]}-{i}" for i, c in enumerate(CASES)]
)
def test_api_matches_cli_kwargs(
    case: tuple[Any, str, str, dict[str, Any], str, list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module, fn_name, operation, api_kwargs, command, extra = case
    seen: dict[str, Any] = {}

    async def fake_call(op: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        seen["operation"] = op
        seen["kwargs"] = kwargs
        return {}

    monkeypatch.setattr(module, "call", fake_call)
    asyncio.run(getattr(module, fn_name)(**api_kwargs))
    assert seen["operation"] == operation
    assert seen["kwargs"] == _expected(command, extra)
