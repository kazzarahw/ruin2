"""Cosmos governance-capture operation wiring (markdown + JSON payloads)."""

from __future__ import annotations

from typing import Any

from ruin.core.cosmos import CosmosGovReport, resolve_lcd
from ruin.services.operations_ext_cosmos import cosmos_gov_data
from ruin.services.serialize import to_dict


def _resolve(kwargs: dict[str, Any]) -> str:
    """Pick the LCD: explicit --lcd wins, else the --chain table."""
    lcd = str(kwargs.get("lcd") or "")
    if lcd:
        return lcd
    return resolve_lcd(str(kwargs.get("chain") or "neutron"))


def cosmos_screen(kwargs: dict[str, Any]) -> CosmosGovReport:
    """Run the governance screen for CLI kwargs (shared by both outputs)."""
    return cosmos_gov_data(_resolve(kwargs))


def _cosmos_gov(kwargs: dict[str, Any]) -> str:
    """Render the governance-capture screen for a Cosmos chain LCD."""
    return cosmos_screen(kwargs).render_markdown()


def _cosmos_gov_data(kwargs: dict[str, Any]) -> object:
    """Build the governance-capture JSON payload."""
    return to_dict(cosmos_screen(kwargs))


COSMOS_OPERATIONS: dict[str, Any] = {"cosmos-gov": _cosmos_gov}
COSMOS_BUILDERS: dict[str, Any] = {"cosmos-gov": _cosmos_gov_data}
