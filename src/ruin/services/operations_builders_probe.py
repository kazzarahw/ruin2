"""JSON builders for probe-style operations."""

from __future__ import annotations

from typing import Any

from ruin.core.chains import rpc_for
from ruin.core.probe import ProbeReport
from ruin.services.probe import probe_drain_selectors
from ruin.services.serialize import to_dict
from ruin.services.subprocesses import cast_code_command, run_command


def probe_report(kwargs: dict[str, Any]) -> ProbeReport:
    """Probe an address live and return the shared drain-probe report."""
    address = str(kwargs["address"])
    rpc = rpc_for(kwargs)
    code = run_command(cast_code_command(rpc, address)).stdout.strip()
    hits = probe_drain_selectors(
        address,
        rpc,
        code,
        probe_from=str(kwargs["probe_from"]),
        extra_selectors=tuple(kwargs.get("extra_selectors") or ()),
    )
    return ProbeReport(address=address, hits=tuple(hits))


def _probe_data(kwargs: dict[str, Any]) -> object:
    """Build the probe JSON payload (per-selector revert status)."""
    return to_dict(probe_report(kwargs))
