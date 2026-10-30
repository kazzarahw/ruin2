"""Thin-collateral operation wiring (markdown + JSON payloads)."""

from __future__ import annotations

from typing import Any

from ruin.core.chains import rpc_for
from ruin.core.thin import ScreenParams, ThinCollateralReport
from ruin.services.files import write_or_render
from ruin.services.operations_ext_thin import thin_collateral_data
from ruin.services.serialize import to_dict


def thin_screen(kwargs: dict[str, Any]) -> ThinCollateralReport:
    """Run the thin-collateral screen for CLI kwargs (shared output)."""
    return thin_collateral_data(
        str(kwargs["token"]),
        str(kwargs["market"]),
        str(kwargs["factory"]),
        rpc_for(kwargs),
        ScreenParams(
            price_usd=float(kwargs["price_usd"]),
            blocks=int(kwargs["blocks"]),
            min_usd=float(kwargs["min_usd"]),
        ),
    )


def _thin_data(kwargs: dict[str, Any]) -> object:
    """Build the thin-collateral JSON payload."""
    return to_dict(thin_screen(kwargs))


def _thin(kwargs: dict[str, Any]) -> str:
    """Render the thin-liquidity collateral screen for one market."""
    text = thin_screen(kwargs).render_markdown()
    return write_or_render(kwargs.get("out"), text)


THIN_OPERATIONS: dict[str, Any] = {"thin-collateral": _thin}
THIN_BUILDERS: dict[str, Any] = {"thin-collateral": _thin_data}
