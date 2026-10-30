"""Agent-facing structured-output builders for ``ruin``.

These builders back the reasoning surfaces (inspect, source, cluster,
replay, proxy, logs, accessmap). Each one reuses the same payload the text
handler builds and serializes it; they are merged into the main ``BUILDERS``
map by :mod:`ruin.services.operations_builders`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from ruin.core.review_templates import get_template
from ruin.services.access_control import build_access_map
from ruin.services.clustering import fetch_cluster_bytecodes
from ruin.services.operations_builders_hunt import _hunt_data
from ruin.services.operations_builders_probe import _probe_data
from ruin.services.operations_ext import (
    _parse_chain,
    cluster_targets,
    inspect_digest,
    logs_scan,
    proxy_resolution,
    replay_timeline,
    source_info,
)
from ruin.services.operations_ext_decode import decode_data
from ruin.services.operations_ext_diff import impl_diff_report
from ruin.services.operations_ext_honeypot import honeypot_report
from ruin.services.operations_ext_honeypot_evm import evm_honeypot_report
from ruin.services.operations_ext_selectors import is_offline, selector_report
from ruin.services.operations_ext_slot import slot_hunt_request
from ruin.services.operations_ext_solvency import solvency_request
from ruin.services.serialize import to_dict


def _unsupported(kwargs: dict[str, Any], note: str) -> dict[str, object]:
    """Return the structured skip payload for a non-EVM chain."""
    return {
        "chain": _parse_chain(kwargs.get("chain", "EVM")).value,
        "supported": False,
        "note": note,
    }


def _proxy_data(kwargs: dict[str, Any]) -> object:
    info = proxy_resolution(kwargs)
    if isinstance(info, str):
        return _unsupported(kwargs, info)
    return to_dict(info)


def _logs_data(kwargs: dict[str, Any]) -> object:
    scan = logs_scan(kwargs)
    if isinstance(scan, str):
        return _unsupported(kwargs, scan)
    return to_dict(scan)


def _replay_data(kwargs: dict[str, Any]) -> object:
    timeline = replay_timeline(kwargs)
    if isinstance(timeline, str):
        return _unsupported(kwargs, timeline)
    return to_dict(timeline)


def _accessmap_data(kwargs: dict[str, Any]) -> object:
    amap = build_access_map(Path(str(kwargs["source"])))
    return to_dict(amap)


def _cluster_data(kwargs: dict[str, Any]) -> object:
    addresses, chain, rpc = cluster_targets(kwargs)
    return to_dict(fetch_cluster_bytecodes(addresses, chain, rpc))


def _source_data(kwargs: dict[str, Any]) -> object:
    return to_dict(source_info(kwargs))


def _inspect_data(kwargs: dict[str, Any]) -> object:
    return to_dict(inspect_digest(kwargs))


def _infra_data(kwargs: dict[str, Any]) -> object:
    return to_dict(get_template(str(kwargs["name"])))


def _selectors_data(kwargs: dict[str, Any]) -> object:
    """Build the selectors payload: on-chain inventory or offline decode."""
    raw = str(kwargs["target"])
    if is_offline(raw):
        return decode_data(raw)
    return to_dict(selector_report(kwargs))


def _honeypot_data(kwargs: dict[str, Any]) -> object:
    """Build the honeypot JSON payload (verdict + signals)."""
    return to_dict(honeypot_report(kwargs))


def _impl_diff_data(kwargs: dict[str, Any]) -> object:
    """Build the impl-diff JSON payload (added/removed selectors)."""
    report = impl_diff_report(kwargs)
    return {
        "new_impl": report.new_impl,
        "old_impl": report.old_impl,
        "added": list(report.added),
        "removed": list(report.removed),
    }


def _honeypot_evm_data(kwargs: dict[str, Any]) -> object:
    """Build the honeypot-evm JSON payload (fork probe results)."""
    return to_dict(evm_honeypot_report(kwargs))


def _slot_hunt_data(kwargs: dict[str, Any]) -> object:
    """Build the slot-hunt JSON payload."""
    return to_dict(slot_hunt_request(kwargs))


def _solvency_data(kwargs: dict[str, Any]) -> object:
    """Build the solvency JSON payload."""
    report = solvency_request(kwargs)
    data = cast("dict[str, object]", to_dict(report))
    return {**data, "delta": report.delta, "flags": report.flags}


AGENT_BUILDERS: dict[str, Any] = {
    "hunt": _hunt_data,
    "honeypot-evm": _honeypot_evm_data,
    "impl-diff": _impl_diff_data,
    "honeypot": _honeypot_data,
    "selectors": _selectors_data,
    "probe": _probe_data,
    "proxy": _proxy_data,
    "logs": _logs_data,
    "replay": _replay_data,
    "accessmap": _accessmap_data,
    "cluster": _cluster_data,
    "source": _source_data,
    "inspect": _inspect_data,
    "infra": _infra_data,
    "slot-hunt": _slot_hunt_data,
    "solvency": _solvency_data,
}
