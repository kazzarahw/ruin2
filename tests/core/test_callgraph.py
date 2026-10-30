"""Tests for AST-driven call graph, inheritance, and fallback facts."""

from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING, Any

from ruin.core.callgraph import build, build_from_facts
from ruin.core.sol_parse import parse_source

if TYPE_CHECKING:
    from ruin.core.callgraph import CallGraph

FIXTURES = pathlib.Path(__file__).parents[1] / "fixtures" / "protocol_src"

MINIMAL_AST: dict[str, Any] = {
    "nodeType": "SourceUnit",
    "nodes": [
        {
            "nodeType": "ContractDefinition",
            "name": "Vault",
            "contractKind": "contract",
            "nodes": [
                {"nodeType": "InheritanceSpecifier", "baseName": {"name": "Base"}},
                {
                    "nodeType": "VariableDefinition",
                    "name": "totalSupply",
                    "typeDescriptions": {"typeString": "uint256"},
                },
                {"nodeType": "EventDefinition", "name": "Transfer"},
                {"nodeType": "ErrorDefinition", "name": "Slippage"},
                {
                    "nodeType": "FunctionDefinition",
                    "name": "deposit",
                    "visibility": "external",
                    "stateMutability": "payable",
                    "modifiers": [
                        {
                            "nodeType": "ModifierInvocation",
                            "modifierName": {"name": "nonReentrant"},
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
                            },
                            {
                                "nodeType": "FunctionCall",
                                "kind": "functionCall",
                                "expression": {
                                    "nodeType": "Identifier",
                                    "name": "_mint",
                                },
                            },
                            {
                                "nodeType": "FunctionCall",
                                "kind": "functionCall",
                                "expression": {
                                    "nodeType": "MemberAccess",
                                    "memberName": "transfer",
                                },
                            },
                            {
                                "nodeType": "FunctionCall",
                                "kind": "delegateCall",
                                "expression": {
                                    "nodeType": "MemberAccess",
                                    "memberName": "doWork",
                                },
                            },
                            {
                                "nodeType": "FunctionCall",
                                "kind": "staticCall",
                                "expression": {
                                    "nodeType": "MemberAccess",
                                    "memberName": "balanceOf",
                                },
                            },
                        ],
                    },
                },
                {
                    "nodeType": "FunctionDefinition",
                    "name": "_mint",
                    "visibility": "internal",
                    "stateMutability": "nonpayable",
                    "body": {"nodeType": "Block", "statements": []},
                },
                {
                    "nodeType": "FunctionDefinition",
                    "name": "receive",
                    "kind": "receive",
                    "visibility": "external",
                    "stateMutability": "payable",
                    "body": {"nodeType": "Block", "statements": []},
                },
            ],
        },
        {
            "nodeType": "ContractDefinition",
            "name": "Base",
            "contractKind": "abstract contract",
            "nodes": [
                {"nodeType": "InheritanceSpecifier", "baseName": {"name": "Vault"}}
            ],
        },
    ],
}


def _graph() -> CallGraph:
    return build({"a.sol": MINIMAL_AST})


def test_contract_kinds_and_names() -> None:
    graph = _graph()
    by_name = {c.name: c for c in graph.contracts}
    assert by_name["Vault"].kind == "contract"
    assert by_name["Base"].kind == "abstract contract"
    assert by_name["Vault"].functions == ("_mint", "deposit", "receive")


def test_call_edge_kinds() -> None:
    graph = _graph()
    vault = next(c for c in graph.contracts if c.name == "Vault")
    edges = {(e.callee, e.kind) for e in vault.edges}
    assert edges == {
        ("_mint", "internal"),
        ("transfer", "external"),
        ("doWork", "delegatecall"),
        ("balanceOf", "staticcall"),
    }


def test_state_writes_and_lookup() -> None:
    graph = _graph()
    vault = next(c for c in graph.contracts if c.name == "Vault")
    assert vault.state_var_writes == (("deposit", "totalSupply"),)
    assert graph.writes_by_function() == {"Vault.deposit": ("totalSupply",)}


def test_inheritance_edges_and_cycle_detection() -> None:
    graph = _graph()
    assert graph.inheritance == (("Base", "Vault"), ("Vault", "Base"))
    assert graph.cycles == (("Base", "Vault"),)


def test_entrypoints_events_errors_layout() -> None:
    graph = _graph()
    assert graph.entrypoints == ("deposit", "receive")
    assert graph.events == ("Transfer",)
    assert graph.errors == ("Slippage",)
    assert graph.storage_layout == (("Vault", "totalSupply", "uint256"),)


def test_fn_facts_carry_visibility_and_modifiers() -> None:
    graph = _graph()
    vault = next(c for c in graph.contracts if c.name == "Vault")
    deposit = next(f for f in vault.fn_facts if f.name == "deposit")
    assert deposit.visibility == "external"
    assert deposit.mutability == "payable"
    assert deposit.modifiers == ("nonReentrant",)


def test_graph_is_hashable_for_lru_cache() -> None:
    graph = _graph()
    assert hash(graph) == hash(_graph())


def test_fallback_from_facts() -> None:
    text = (
        "pragma solidity ^0.8.0;\n"
        "contract V is B {\n"
        "  uint256 public totalSupply;\n"
        "  function mint() external onlyOwner {}\n"
        "}"
    )
    facts = parse_source("x", text)
    graph = build_from_facts((facts,))
    assert graph.inheritance == (("V", "B"),)
    assert graph.entrypoints == ("mint",)
    assert graph.storage_layout == (("V", "totalSupply", "uint256"),)
    vault = graph.contracts[0]
    assert vault.fn_facts[0].modifiers == ("onlyOwner",)


def test_fallback_on_real_fixture_source() -> None:
    text = (FIXTURES / "contracts_StakedAvantCoinV2.sol").read_text()
    facts = parse_source("vault", text)
    graph = build_from_facts((facts,))
    assert graph.entrypoints == (
        "cooldownAssets",
        "cooldownShares",
        "redeem",
        "setCooldownDuration",
        "unstake",
        "withdraw",
    )
    assert graph.storage_layout[0][0] == "StakedAvantCoinV2"
