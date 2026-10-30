"""Hunt markdown rendering and CLI operation wiring."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ruin.core.hunt import render_hunt_markdown
from ruin.services.operations_ext_hunt import hunt_payload
from ruin.services.serialize import to_dict


def _hunt(kwargs: dict[str, Any]) -> str:
    """Render the hunt candidate table for the requested tokens."""
    report = hunt_payload(kwargs)
    blocks = int(kwargs.get("blocks") or 1500)
    return render_hunt_markdown(
        str(kwargs["token"]),
        list(report.candidates),
        blocks,
        report.scan_errors,
        report.scan_windows,
    )


def _hunt_data(kwargs: dict[str, Any]) -> object:
    """Build the hunt JSON payload (recipient/class sweep results)."""
    report = hunt_payload(kwargs)
    rounded = replace(
        report,
        candidates=tuple(replace(c, usd=round(c.usd, 2)) for c in report.candidates),
    )
    return to_dict(rounded)


HUNT_OPERATIONS: dict[str, Any] = {"hunt": _hunt}
