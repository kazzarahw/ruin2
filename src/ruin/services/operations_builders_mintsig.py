"""mintsig operation wiring (markdown + JSON payloads)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ruin.core.chains import rpc_for
from ruin.services.operations_ext_mintsig import mintsig_data

if TYPE_CHECKING:
    from ruin.core.screens import MintSigReport
from ruin.services.serialize import to_dict


def mintsig_screen(kwargs: dict[str, Any]) -> MintSigReport:
    """Run the sig-mint screen for CLI kwargs (shared by text and JSON)."""
    return mintsig_data(str(kwargs["address"]), rpc_for(kwargs))


def _mintsig(kwargs: dict[str, Any]) -> str:
    """Run the sig-mint screen and render markdown."""
    return mintsig_screen(kwargs).render_markdown()


def _mintsig_json(kwargs: dict[str, Any]) -> object:
    """Run the sig-mint screen and return the JSON payload."""
    return to_dict(mintsig_screen(kwargs))


MINTSIG_OPERATIONS = {"mintsig": _mintsig}
MINTSIG_BUILDERS = {"mintsig": _mintsig_json}
