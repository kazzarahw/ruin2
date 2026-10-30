"""Tests for candidate invariant synthesis from call-graph facts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ruin.core.callgraph import build, build_from_facts
from ruin.core.invariants import synthesize
from ruin.core.sol_parse import parse_source

if TYPE_CHECKING:
    from ruin.core.invariants import InvariantSpec


def _fn(
    name: str,
    mut: str,
    mods: tuple[str, ...],
    writes: tuple[str, ...] = (),
    calls: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Build one external AST function node with writes/calls in its body."""
    body = {
        "nodeType": "Block",
        "statements": [
            *(
                {
                    "nodeType": "Assignment",
                    "leftHandSide": {"nodeType": "Identifier", "name": v},
                }
                for v in writes
            ),
            *(
                {
                    "nodeType": "FunctionCall",
                    "kind": "functionCall",
                    "expression": {"nodeType": "MemberAccess", "memberName": c},
                }
                for c in calls
            ),
        ],
    }
    return {
        "nodeType": "FunctionDefinition",
        "name": name,
        "visibility": "external",
        "stateMutability": mut,
        "modifiers": [
            {"nodeType": "ModifierInvocation", "modifierName": {"name": m}}
            for m in mods
        ],
        "body": body,
    }


def _var(name: str) -> dict[str, Any]:
    """Build one uint256 state-variable AST node."""
    return {
        "nodeType": "VariableDefinition",
        "name": name,
        "typeDescriptions": {"typeString": "uint256"},
    }


VAULT_AST = {
    "nodeType": "SourceUnit",
    "nodes": [
        {
            "nodeType": "ContractDefinition",
            "name": "Vault",
            "contractKind": "contract",
            "nodes": [
                _var("totalSupply"),
                _var("fee"),
                _fn(
                    "deposit",
                    "payable",
                    ("nonReentrant",),
                    writes=("totalSupply",),
                ),
                _fn("setFee", "nonpayable", ("onlyOwner",), writes=("fee",)),
                _fn("claim", "payable", (), calls=("transfer",)),
                _fn("receive", "payable", ()),
            ],
        }
    ],
}


def _specs() -> tuple[InvariantSpec, ...]:
    return synthesize(build({"a.sol": VAULT_AST}))


def test_kinds_synthesized_from_minimal_ast() -> None:
    kinds = sorted(s.kind for s in _specs())
    assert kinds == [
        "owner_settable_param",
        "share_price_non_decreasing",
        "total_supply_monotonic",
        "unauthenticated_value_mover",
    ]


def test_supply_spec_names_writers() -> None:
    spec = next(s for s in _specs() if s.kind == "total_supply_monotonic")
    assert spec.contract == "Vault"
    assert spec.subject == "totalSupply"
    assert "deposit" in spec.rationale


def test_share_price_spec_carries_gate() -> None:
    spec = next(s for s in _specs() if s.kind == "share_price_non_decreasing")
    assert spec.guard == "nonReentrant"


def test_setter_spec_uses_owner_guard_and_written_var() -> None:
    spec = next(s for s in _specs() if s.kind == "owner_settable_param")
    assert spec.subject == "fee"
    assert spec.guard == "onlyOwner"


def test_value_mover_lists_ungated_payables() -> None:
    spec = next(s for s in _specs() if s.kind == "unauthenticated_value_mover")
    assert set(spec.subject.split(",")) == {"claim", "receive"}


def test_no_share_price_spec_without_gated_mint() -> None:
    ast = {
        "nodeType": "SourceUnit",
        "nodes": [
            {
                "nodeType": "ContractDefinition",
                "name": "T",
                "contractKind": "contract",
                "nodes": [
                    {
                        "nodeType": "VariableDefinition",
                        "name": "totalSupply",
                        "typeDescriptions": {"typeString": "uint256"},
                    },
                    {
                        "nodeType": "FunctionDefinition",
                        "name": "mint",
                        "visibility": "external",
                        "stateMutability": "nonpayable",
                        "body": {"nodeType": "Block", "statements": []},
                    },
                ],
            }
        ],
    }
    kinds = [s.kind for s in synthesize(build({"t.sol": ast}))]
    assert "share_price_non_decreasing" not in kinds
    assert "unauthenticated_value_mover" not in kinds


def test_non_owner_setter_is_ignored() -> None:
    ast = {
        "nodeType": "SourceUnit",
        "nodes": [
            {
                "nodeType": "ContractDefinition",
                "name": "T",
                "contractKind": "contract",
                "nodes": [
                    {
                        "nodeType": "FunctionDefinition",
                        "name": "setAnything",
                        "visibility": "external",
                        "stateMutability": "nonpayable",
                        "modifiers": [
                            {
                                "nodeType": "ModifierInvocation",
                                "modifierName": {"name": "pausable"},
                            }
                        ],
                        "body": {"nodeType": "Block", "statements": []},
                    }
                ],
            }
        ],
    }
    assert synthesize(build({"t.sol": ast})) == ()


def test_fallback_facts_still_yield_supply_spec() -> None:
    text = (
        "pragma solidity ^0.8.0;\n"
        "contract V {\n"
        "  uint256 public totalSupply;\n"
        "  uint24 public cooldownDuration;\n"
        "  function setCooldownDuration(uint24 d) external onlyRole(0) {}\n"
        "}"
    )
    graph = build_from_facts((parse_source("v", text),))
    specs = synthesize(graph)
    supply = next(s for s in specs if s.kind == "total_supply_monotonic")
    assert supply.rationale.endswith("unknown")
    setter = next(s for s in specs if s.kind == "owner_settable_param")
    assert setter.subject == "setCooldownDuration"
    assert setter.guard == "onlyRole"


def test_synthesis_is_deterministic() -> None:
    assert _specs() == _specs()
