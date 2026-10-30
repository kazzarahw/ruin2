"""Foundry invariant scaffold writer for resolved protocols.

Template strings only: forge-std imports stay commented until the user
confirms remappings, and each stub names the gate/subject it guards. The
synthesis rules live in ``ruin.core.invariants``; this module only turns
specs into files.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.services.protocol import Protocol, invariants

if TYPE_CHECKING:
    from pathlib import Path

    from ruin.core.invariants import InvariantSpec

_TEMPLATE = """// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

// import {{Test}} from "forge-std/Test.sol";           // uncomment after remappings
// import {{StdInvariant}} from "forge-std/StdInvariant.sol";
// import {{Target}} from "<path-to-source>";

/// @notice candidate invariant for {contract}: {rationale}
contract {slug}Invariant is /* StdInvariant */ Test {{
    // TODO: instantiate the protocol under test and register handlers.

    /// @custom:invariant {description}
    function invariant_{slug}() public view {{
        // TODO: assert on `{subject}`{guard_note}; keep all handlers.
    }}
}}
"""


def _guard_note(guard: str) -> str:
    """Suffix describing the gate a spec expects."""
    return f" gated by `{guard}`" if guard else ""


def _description(spec: InvariantSpec) -> str:
    """One-line invariant description for the @custom:invariant tag."""
    verbs = {
        "total_supply_monotonic": "totalSupply only changes through known writers",
        "share_price_non_decreasing": "assets-per-share never decreases on gated paths",
        "owner_settable_param": (
            "parameter changes only through its owner-gated setter"
        ),
        "unauthenticated_value_mover": (
            "ungated value movers never drain unexpected value"
        ),
    }
    return verbs.get(spec.kind, spec.kind.replace("_", " "))


def stub(spec: InvariantSpec) -> str:
    """Render one Foundry invariant stub for a spec."""
    slug = spec.name.lower().replace("-", "_")
    return _TEMPLATE.format(
        contract=spec.contract,
        slug=slug,
        rationale=spec.rationale,
        description=_description(spec),
        subject=spec.subject,
        guard_note=_guard_note(spec.guard),
    )


def scaffold(protocol: Protocol, out_dir: Path) -> str:
    """Write one invariant stub per candidate spec; return a summary line."""
    specs = invariants(protocol)
    out_dir.mkdir(parents=True, exist_ok=True)
    for spec in specs:
        (out_dir / f"{spec.name.lower()}.t.sol").write_text(
            stub(spec), encoding="utf-8"
        )
    return f"wrote {len(specs)} invariant stubs to {out_dir}"
