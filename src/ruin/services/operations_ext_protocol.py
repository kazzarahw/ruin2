"""Protocol namespace operation handlers.

Merged into ``_OPERATIONS`` by :mod:`ruin.services.operations`; the JSON
builders in :mod:`ruin.services.operations_builders_protocol` reuse these
exact payload helpers.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruin.services.protocol import Protocol, SurfaceRow, resolve, surface
from ruin.services.protocol_scaffold import scaffold

if TYPE_CHECKING:
    from ruin.core.invariants import InvariantSpec


def protocol_of(kwargs: dict[str, Any]) -> Protocol:
    """Resolve the kwargs address into a Protocol (chain/rpc included)."""
    rpc = kwargs.get("rpc")
    return resolve(
        str(kwargs["address"]),
        str(kwargs.get("chain") or "ethereum"),
        str(rpc) if rpc else None,
    )


def surface_rows(kwargs: dict[str, Any]) -> tuple[SurfaceRow, ...]:
    """Ranked surface rows for the kwargs protocol (shared text/JSON)."""
    return surface(protocol_of(kwargs))


def invariant_specs(kwargs: dict[str, Any]) -> tuple[InvariantSpec, ...]:
    """Candidate invariant specs for the kwargs protocol (shared)."""
    from ruin.services.protocol import invariants

    return invariants(protocol_of(kwargs))


def _row_line(row: SurfaceRow) -> str:
    """One text line for a surface row."""
    mods = ",".join(row.modifiers) or "-"
    writes = ",".join(row.writes) or "-"
    tags = ",".join(row.tags) or "-"
    return (
        f"  [{row.rank}] {row.contract}.{row.name} ({row.mutability},"
        f" {row.visibility}) mods={mods} writes={writes} tags={tags}"
    )


def _spec_line(spec: InvariantSpec) -> str:
    """One text line for an invariant spec."""
    guard = f" [guard: {spec.guard}]" if spec.guard else ""
    return f"- [{spec.kind}] {spec.name}{guard}: {spec.rationale}"


def _resolve(kwargs: dict[str, Any]) -> str:
    return protocol_of(kwargs).render_markdown()


def _enumerate(kwargs: dict[str, Any]) -> str:
    rows = surface_rows(kwargs)
    if not rows:
        return "no external surface (unverified source or no AST/facts)"
    return "\n".join(_row_line(row) for row in rows)


def _model(kwargs: dict[str, Any]) -> str:
    protocol = protocol_of(kwargs)
    lines = [protocol.render_markdown(), "", "## Storage layout"]
    lines.extend(
        f"  {contract}.{var}: {type_name}"
        for contract, var, type_name in protocol.graph.storage_layout
    )
    if protocol.graph.events:
        lines.append(f"- events: {', '.join(protocol.graph.events)}")
    if protocol.graph.errors:
        lines.append(f"- errors: {', '.join(protocol.graph.errors)}")
    writes = protocol.graph.writes_by_function()
    if writes:
        lines.extend(["", "## State writes"])
        lines.extend(
            f"  {fn} -> {', '.join(vars_)}" for fn, vars_ in sorted(writes.items())
        )
    return "\n".join(lines)


def _invariants(kwargs: dict[str, Any]) -> str:
    specs = invariant_specs(kwargs)
    lines = [_spec_line(spec) for spec in specs] or ["no candidate invariants"]
    out = kwargs.get("scaffold")
    if out:
        lines.append(scaffold(protocol_of(kwargs), Path(str(out))))
    return "\n".join(lines)


PROTOCOL_OPERATIONS: dict[str, Any] = {
    "resolve": _resolve,
    "enumerate": _enumerate,
    "model": _model,
    "invariants": _invariants,
}
