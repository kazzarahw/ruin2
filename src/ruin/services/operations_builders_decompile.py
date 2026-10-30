"""decompile operation wiring (markdown + JSON payloads)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ruin.core.chains import rpc_for
from ruin.services.files import write_or_render
from ruin.services.operations_ext_decompile import decompile_data

if TYPE_CHECKING:
    from ruin.core.decompile import DecompileReport
from ruin.services.serialize import to_dict


def decompile_report(kwargs: dict[str, Any]) -> DecompileReport:
    """Build the bytecode review report for CLI kwargs (shared output)."""
    return decompile_data(str(kwargs["address"]), rpc_for(kwargs))


def _decompile(kwargs: dict[str, Any]) -> str:
    """Render the bytecode review report for one deployed contract."""
    text = decompile_report(kwargs).render_markdown()
    return write_or_render(kwargs.get("out"), text)


def _decompile_data(kwargs: dict[str, Any]) -> object:
    """Build the decompile JSON payload."""
    return to_dict(decompile_report(kwargs), drop_none=True)


DECOMPILE_OPERATIONS: dict[str, Any] = {"decompile": _decompile}
DECOMPILE_BUILDERS: dict[str, Any] = {"decompile": _decompile_data}
