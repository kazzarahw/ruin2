"""Protocol service tests with monkeypatched I/O seams (no network)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import ruin.services.protocol as protocol_module
from ruin.cli import main
from ruin.core.enums import Chain
from ruin.core.onchain import SourceInfo
from ruin.core.proxy import ProxyInfo
from ruin.services import protocol_compile
from ruin.services.operations import run_operation, run_operation_json
from ruin.services.protocol import Protocol, SurfaceRow, resolve

FIXTURES = Path(__file__).parents[1] / "fixtures" / "protocol_src"

VAULT_TEXT = (FIXTURES / "contracts_StakedAvantCoinV2.sol").read_text()

MINIMAL_AST: dict[str, Any] = {
    "nodeType": "SourceUnit",
    "nodes": [
        {
            "nodeType": "ContractDefinition",
            "name": "StakedAvantCoinV2",
            "contractKind": "contract",
            "nodes": [
                {
                    "nodeType": "VariableDefinition",
                    "name": "totalSupply",
                    "typeDescriptions": {"typeString": "uint256"},
                },
                {
                    "nodeType": "FunctionDefinition",
                    "name": "setFee",
                    "visibility": "external",
                    "stateMutability": "nonpayable",
                    "modifiers": [
                        {
                            "nodeType": "ModifierInvocation",
                            "modifierName": {"name": "onlyOwner"},
                        }
                    ],
                    "body": {
                        "nodeType": "Block",
                        "statements": [
                            {
                                "nodeType": "Assignment",
                                "leftHandSide": {
                                    "nodeType": "Identifier",
                                    "name": "totalSupply",
                                },
                            }
                        ],
                    },
                },
            ],
        }
    ],
}


def _fake_fetch(requested: str, **kwargs: object) -> SourceInfo:
    verified = requested == "0xIMPL"
    return SourceInfo(
        chain=Chain.EVM,
        address=requested,
        name="StakedAvantCoinV2",
        source_text=VAULT_TEXT if verified else "",
        verified=verified,
    )


def _fake_proxy(address: str, rpc: str) -> ProxyInfo:
    return ProxyInfo(
        address=address, implementation="0xIMPL", is_proxy=True, delegated_to=""
    )


def _fake_run(argv: list[str], **kwargs: object) -> SimpleNamespace:
    out = {"sources": {"StakedAvantCoinV2.sol": {"ast": MINIMAL_AST}}}
    return SimpleNamespace(stdout=json.dumps(out), stderr="", returncode=0)


def _verified_fetch(requested: str, **kwargs: object) -> SourceInfo:
    return SourceInfo(
        chain=Chain.EVM,
        address=requested,
        name="StakedAvantCoinV2",
        source_text=VAULT_TEXT,
        verified=True,
    )


def _seams(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(protocol_module, "fetch_source", _fake_fetch)
    monkeypatch.setattr(protocol_module, "resolve_proxy_onchain", _fake_proxy)
    monkeypatch.setattr(protocol_compile, "pick_solc", lambda _source: "/usr/bin/solc")
    monkeypatch.setattr(protocol_compile, "run_command", _fake_run)


def test_resolve_follows_proxy_and_prefers_verified_impl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seams(monkeypatch)
    protocol = resolve("0xPROXY", chain="ethereum", rpc="http://x")
    assert protocol.implementation == "0xIMPL"
    assert protocol.verified
    assert "EIP-1967" in protocol.delegation
    assert protocol.graph.entrypoints == ("setFee",)


def test_resolve_without_solc_falls_back_to_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seams(monkeypatch)
    monkeypatch.setattr(protocol_compile, "pick_solc", lambda _source: "")
    protocol = resolve("0xPROXY", chain="ethereum", rpc="http://x")
    assert "cooldownAssets" in protocol.graph.entrypoints
    assert protocol.pragma == "0.8.20"


def test_resolve_non_proxy_keeps_own_source(monkeypatch: pytest.MonkeyPatch) -> None:
    _seams(monkeypatch)
    monkeypatch.setattr(
        protocol_module,
        "resolve_proxy_onchain",
        lambda _address, _rpc: ProxyInfo(address="0xPROXY"),
    )
    monkeypatch.setattr(protocol_module, "fetch_source", _verified_fetch)
    protocol = resolve("0xPROXY", chain="ethereum", rpc="http://x")
    assert protocol.implementation == ""
    assert protocol.verified


def test_resolve_unknown_chain_without_rpc_raises() -> None:
    with pytest.raises(ValueError, match="unknown chain"):
        resolve("0x1", chain="dogecoin")


def test_surface_ranks_owner_setters_first(monkeypatch: pytest.MonkeyPatch) -> None:
    _seams(monkeypatch)
    monkeypatch.setattr(protocol_compile, "pick_solc", lambda _source: "")
    protocol = resolve("0xPROXY", chain="ethereum", rpc="http://x")
    rows = protocol_module.surface(protocol)
    assert rows[0].name == "setCooldownDuration"
    assert rows[0].rank == 3
    assert rows[0].tags == ("owner-settable",)


def test_invariants_and_scaffold(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _seams(monkeypatch)
    monkeypatch.setattr(protocol_compile, "pick_solc", lambda _source: "")
    protocol = resolve("0xPROXY", chain="ethereum", rpc="http://x")
    specs = protocol_module.invariants(protocol)
    assert any(
        s.kind == "owner_settable_param" and s.guard == "onlyRole" for s in specs
    )
    note = protocol_module_scaffold(protocol, tmp_path / "inv")
    assert "invariant stubs" in note
    files = sorted((tmp_path / "inv").glob("*.t.sol"))
    assert files
    text = files[0].read_text()
    assert '// import {Test} from "forge-std/Test.sol";' in text
    assert "function invariant_" in text


def protocol_module_scaffold(protocol: Protocol, out_dir: Path) -> str:
    from ruin.services.protocol_scaffold import scaffold

    return scaffold(protocol, out_dir)


def test_run_operation_text_and_json_share_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seams(monkeypatch)
    kwargs = {
        "address": "0xPROXY",
        "chain": "ethereum",
        "rpc": "http://x",
        "scaffold": None,
    }
    text = run_operation("resolve", dict(kwargs))
    assert "# Protocol model: 0xPROXY" in text
    data = run_operation_json("resolve", dict(kwargs))
    assert isinstance(data, dict)
    assert data.get("address") == "0xPROXY"
    assert data.get("implementation") == "0xIMPL"
    enum_data = run_operation_json("enumerate", dict(kwargs))
    assert isinstance(enum_data, dict)
    rows = enum_data.get("rows")
    assert isinstance(rows, list)
    first = rows[0]
    assert isinstance(first, dict)
    assert first.get("name") == "setFee"
    inv_data = run_operation_json("invariants", dict(kwargs))
    assert isinstance(inv_data, dict)
    specs = inv_data.get("specs")
    assert isinstance(specs, dict)
    assert specs.get("items")


def test_cli_json_protocol_resolve(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _seams(monkeypatch)
    monkeypatch.setattr(protocol_compile, "pick_solc", lambda _source: "")
    code = main(
        ["--format", "json", "protocol", "resolve", "0xPROXY", "--rpc", "http://x"]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["name"] == "StakedAvantCoinV2"


BUNDLE_TEXT = (
    "// ==== contracts/X.sol ====\n"
    "// SPDX-License-Identifier: MIT\n"
    "pragma solidity ^0.8.20;\n"
    "contract X {}\n"
)

TWIN_TEXT = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IThing {
    function deposit(uint256 v) external;
}

contract Thing is IThing {
    function deposit(uint256 v) public override onlyOwner {}
}
"""


def _bundle_fetch(requested: str, **kwargs: object) -> SourceInfo:
    return SourceInfo(
        chain=Chain.EVM,
        address=requested,
        name="contracts/X.sol",
        source_text=BUNDLE_TEXT,
        verified=True,
        remappings=("@oz/contracts=contracts",),
    )


def _twin_fetch(requested: str, **kwargs: object) -> SourceInfo:
    return SourceInfo(
        chain=Chain.EVM,
        address=requested,
        name="Twin",
        source_text=TWIN_TEXT,
        verified=True,
    )


def _non_proxy(_address: str, _rpc: str) -> ProxyInfo:
    return ProxyInfo(address="0xPROXY")


def test_compile_aliases_bundle_keys_via_remappings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def capture_run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        captured.update(json.loads(Path(argv[-1]).read_text(encoding="utf-8")))
        return _fake_run(argv, **kwargs)

    _seams(monkeypatch)
    monkeypatch.setattr(protocol_module, "fetch_source", _bundle_fetch)
    monkeypatch.setattr(protocol_module, "resolve_proxy_onchain", _non_proxy)
    monkeypatch.setattr(protocol_compile, "run_command", capture_run)
    protocol = resolve("0xPROXY", chain="ethereum", rpc="http://x")
    sources = captured["sources"]
    original = sources["contracts/X.sol"]["content"]
    alias = sources["@oz/contracts/X.sol"]["content"]
    assert alias == original
    assert protocol.mode == "ast"


def test_ast_mode_reported_in_markdown_and_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seams(monkeypatch)
    protocol = resolve("0xPROXY", chain="ethereum", rpc="http://x")
    assert protocol.mode == "ast"
    assert "- graph: `ast`" in protocol.render_markdown()
    kwargs = {
        "address": "0xPROXY",
        "chain": "ethereum",
        "rpc": "http://x",
        "scaffold": None,
    }
    data = run_operation_json("resolve", dict(kwargs))
    assert isinstance(data, dict)
    assert data.get("mode") == "ast"


def test_line_facts_mode_reported_when_not_compiled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seams(monkeypatch)
    monkeypatch.setattr(protocol_compile, "pick_solc", lambda _source: "")
    protocol = resolve("0xPROXY", chain="ethereum", rpc="http://x")
    assert protocol.mode == "line-facts"
    assert "- graph: `line-facts` (source not compiled)" in protocol.render_markdown()
    kwargs = {
        "address": "0xPROXY",
        "chain": "ethereum",
        "rpc": "http://x",
        "scaffold": None,
    }
    data = run_operation_json("resolve", dict(kwargs))
    assert isinstance(data, dict)
    assert data.get("mode") == "line-facts"


def test_surface_collapses_public_external_twins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seams(monkeypatch)
    monkeypatch.setattr(protocol_compile, "pick_solc", lambda _source: "")
    monkeypatch.setattr(protocol_module, "fetch_source", _twin_fetch)
    monkeypatch.setattr(protocol_module, "resolve_proxy_onchain", _non_proxy)
    protocol = resolve("0xPROXY", chain="ethereum", rpc="http://x")
    rows = protocol_module.surface(protocol)
    deposits = [row for row in rows if row.name == "deposit"]
    assert len(deposits) == 1
    assert deposits[0].visibility == "public"
    assert deposits[0].modifiers == ("onlyOwner",)


def test_dedupe_keeps_first_row_on_ties() -> None:
    first = SurfaceRow(
        name="f",
        contract="C",
        visibility="public",
        mutability="view",
        modifiers=(),
        writes=(),
        rank=1,
        tags=(),
    )
    twin = SurfaceRow(
        name="f",
        contract="C",
        visibility="external",
        mutability="view",
        modifiers=(),
        writes=(),
        rank=1,
        tags=(),
    )
    assert protocol_module._dedupe((first, twin)) == (first,)


def test_metadata_pinned_version_prefers_exact_solc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested_versions: list[str] = []

    def _fetch_with_version(requested: str, **kwargs: object) -> SourceInfo:
        return SourceInfo(
            chain=Chain.EVM,
            address=requested,
            name="StakedAvantCoinV2",
            source_text=VAULT_TEXT,
            verified=True,
            compiler_version="0.8.28",
        )

    def _ensure(version: str, **kwargs: object) -> str:
        requested_versions.append(version)
        return "/usr/bin/solc-0.8.28"

    _seams(monkeypatch)
    monkeypatch.setattr(protocol_module, "fetch_source", _fetch_with_version)
    monkeypatch.setattr(
        protocol_module,
        "resolve_proxy_onchain",
        lambda _address, _rpc: ProxyInfo(address="0xPROXY"),
    )
    monkeypatch.setattr(protocol_compile, "ensure_solc", _ensure)
    protocol = resolve("0xPROXY", chain="ethereum", rpc="http://x")
    assert requested_versions == ["0.8.28"]
    assert protocol.mode == "ast"


def test_no_metadata_version_falls_back_to_pragma_pick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested_versions: list[str] = []

    def _ensure(version: str, **kwargs: object) -> str:
        requested_versions.append(version)
        return ""

    _seams(monkeypatch)
    monkeypatch.setattr(
        protocol_module,
        "resolve_proxy_onchain",
        lambda _address, _rpc: ProxyInfo(address="0xPROXY"),
    )
    monkeypatch.setattr(protocol_module, "fetch_source", _verified_fetch)
    monkeypatch.setattr(protocol_compile, "ensure_solc", _ensure)
    protocol = resolve("0xPROXY", chain="ethereum", rpc="http://x")
    assert requested_versions == []
    assert protocol.mode == "ast"
