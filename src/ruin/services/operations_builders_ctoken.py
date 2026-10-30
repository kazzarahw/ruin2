"""cToken inflation operation wiring (markdown + JSON payloads)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ruin.core.chains import rpc_for
from ruin.services.operations_ext_ctoken import ctoken_inflation_data

if TYPE_CHECKING:
    from ruin.core.screens import CtokenScreen
from ruin.services.serialize import to_dict


def ctoken_screen(kwargs: dict[str, Any]) -> CtokenScreen:
    """Run the cToken screen for CLI kwargs (shared by text and JSON)."""
    return ctoken_inflation_data(str(kwargs["ctoken"]), rpc_for(kwargs))


def _ctoken(kwargs: dict[str, Any]) -> str:
    """Render the cToken donation-inflation screen for a market."""
    return ctoken_screen(kwargs).render_markdown()


def _ctoken_data(kwargs: dict[str, Any]) -> object:
    """Build the cToken inflation JSON payload."""
    return to_dict(ctoken_screen(kwargs))


CTOKEN_OPERATIONS: dict[str, Any] = {"ctoken-inflation": _ctoken}
CTOKEN_BUILDERS: dict[str, Any] = {"ctoken-inflation": _ctoken_data}
