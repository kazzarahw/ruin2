"""Candidate invariant specs synthesized from call-graph facts.

Pure: takes a CallGraph and proposes invariant shapes worth testing
(supply monotonicity, share-price ordering, owner-settable parameters,
unauthenticated value movers). This is synthesis only: no Foundry
scaffold strings here, and no I/O or package imports beyond core.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .callgraph import CallGraph, ContractGraph

_OWNER_HINTS = (
    "owner",
    "admin",
    "governance",
    "role",
    "guardian",
    "multisig",
    "timelock",
)
_VALUE_CALLEES = frozenset(
    {"transfer", "transferFrom", "send", "safeTransfer", "safeTransferFrom"}
)
_MINT_LIKE = frozenset(
    {"mint", "deposit", "transfer", "transferFrom", "burn", "withdraw"}
)


@dataclass(frozen=True, slots=True)
class InvariantSpec:
    """One candidate invariant with the facts that motivate it."""

    name: str
    kind: str  # total_supply_monotonic | share_price_non_decreasing |
    # owner_settable_param | unauthenticated_value_mover
    contract: str
    subject: str
    guard: str
    rationale: str


def _owner_guard(modifiers: tuple[str, ...]) -> str:
    """First modifier whose name hints at an owner/role gate."""
    for mod in modifiers:
        low = mod.lower()
        if any(hint in low for hint in _OWNER_HINTS):
            return mod
    return ""


def _writes(graph: CallGraph, contract: str, var: str) -> tuple[str, ...]:
    """Functions of one contract that write a given state variable."""
    for cg in graph.contracts:
        if cg.name == contract:
            return tuple(sorted(fn for fn, w in cg.state_var_writes if w == var))
    return ()


def _has_supply_var(graph: CallGraph, contract: str) -> bool:
    """True when the contract declares a totalSupply state variable."""
    return any(c == contract and v == "totalSupply" for c, v, _ in graph.storage_layout)


def _supply_specs(graph: CallGraph) -> list[InvariantSpec]:
    """TotalSupply only moves through functions that write it."""
    specs = []
    seen = {c for c, v, _ in graph.storage_layout if v == "totalSupply"}
    for contract in sorted(seen):
        writers = _writes(graph, contract, "totalSupply")
        specs.append(
            InvariantSpec(
                name=f"{contract}_totalSupply_monotonic",
                kind="total_supply_monotonic",
                contract=contract,
                subject="totalSupply",
                guard="",
                rationale=(
                    f"totalSupply changes only in: {', '.join(writers) or 'unknown'}"
                ),
            )
        )
    return specs


def _share_price_specs(graph: CallGraph) -> list[InvariantSpec]:
    """Share price never decreases when mint/transfer paths are gated."""
    specs = []
    for cg in sorted(graph.contracts, key=lambda c: c.name):
        if not _has_supply_var(graph, cg.name):
            continue
        for fact in cg.fn_facts:
            if fact.name in _MINT_LIKE and fact.modifiers:
                specs.append(
                    InvariantSpec(
                        name=f"{cg.name}_share_price_non_decreasing",
                        kind="share_price_non_decreasing",
                        contract=cg.name,
                        subject="totalSupply",
                        guard=fact.modifiers[0],
                        rationale=(
                            f"{fact.name} writes supply behind {fact.modifiers[0]}; "
                            "assets-per-share must not drop on gated paths"
                        ),
                    )
                )
                break
    return specs


def _setter_specs(graph: CallGraph) -> list[InvariantSpec]:
    """Parameters writable only through owner-gated setters."""
    specs = []
    for cg in sorted(graph.contracts, key=lambda c: c.name):
        for fact in cg.fn_facts:
            guard = _owner_guard(fact.modifiers)
            if not fact.name.startswith("set") or not guard:
                continue
            var = _written_var(cg, fact.name)
            writers = _writes(graph, cg.name, var) if var else ()
            specs.append(
                InvariantSpec(
                    name=f"{cg.name}_{fact.name}_owner_only",
                    kind="owner_settable_param",
                    contract=cg.name,
                    subject=var or fact.name,
                    guard=guard,
                    rationale=(
                        f"{fact.name} gated by {guard} changes "
                        f"{', '.join(writers) or fact.name}"
                    ),
                )
            )
    return specs


def _written_var(cg: ContractGraph, fn: str) -> str:
    """First state variable written by a function, if any."""
    for name, var in cg.state_var_writes:
        if name == fn:
            return var
    return ""


def _value_mover_specs(graph: CallGraph) -> list[InvariantSpec]:
    """Value-moving functions reachable without any gate."""
    specs = []
    for cg in sorted(graph.contracts, key=lambda c: c.name):
        movers = _movers(cg)
        if movers:
            specs.append(
                InvariantSpec(
                    name=f"{cg.name}_unauthenticated_value_movers",
                    kind="unauthenticated_value_mover",
                    contract=cg.name,
                    subject=",".join(movers),
                    guard="",
                    rationale="payable or value-moving entrypoints with no modifier",
                )
            )
    return specs


def _movers(cg: ContractGraph) -> tuple[str, ...]:
    """Entrypoint names that move value and carry no modifier."""
    gated = {f.name for f in cg.fn_facts if f.modifiers}
    movers = set()
    for fact in cg.fn_facts:
        if fact.name in gated or fact.visibility not in ("public", "external"):
            continue
        if fact.mutability == "payable" or any(
            e.kind == "external" and e.callee in _VALUE_CALLEES for e in cg.edges
        ):
            movers.add(fact.name)
    return tuple(sorted(movers))


def synthesize(graph: CallGraph) -> tuple[InvariantSpec, ...]:
    """All candidate invariant specs for one compiled protocol."""
    specs = (
        _supply_specs(graph)
        + _share_price_specs(graph)
        + _setter_specs(graph)
        + _value_mover_specs(graph)
    )
    return tuple(sorted(specs, key=lambda s: (s.contract, s.kind, s.name)))
