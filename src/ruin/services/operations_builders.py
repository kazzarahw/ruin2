"""Structured-output builders for ``ruin`` operations.

Each builder reuses the exact payload its text handler builds; the
agent-facing reasoning builders are defined in
:mod:`ruin.services.operations_builders_agent` and merged into ``BUILDERS``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from ruin.core.scoring import rank_targets
from ruin.services.findings import dedupe_registry, load_registry, merge_into
from ruin.services.http import filtered_summaries
from ruin.services.operations_builders_agent import AGENT_BUILDERS
from ruin.services.operations_builders_cosmos import COSMOS_BUILDERS
from ruin.services.operations_builders_ctoken import CTOKEN_BUILDERS
from ruin.services.operations_builders_decompile import DECOMPILE_BUILDERS
from ruin.services.operations_builders_mintsig import MINTSIG_BUILDERS
from ruin.services.operations_builders_protocol import PROTOCOL_BUILDERS
from ruin.services.operations_builders_thin import THIN_BUILDERS
from ruin.services.operations_ext import _chain_list
from ruin.services.operations_ext_scaffold import (
    flashloan_scaffold,
    oracle_scaffold,
)
from ruin.services.operations_ext_triage import triage_data
from ruin.services.serialize import to_dict


def _screen_data(kwargs: dict[str, Any]) -> object:
    from ruin.services.operations import _screen_target

    return to_dict(_screen_target(kwargs))


def _fuzz_data(kwargs: dict[str, Any]) -> object:
    if kwargs.get("run"):
        raise ValueError("fuzz run has no structured output")
    from ruin.services.operations import _fuzz_result

    return to_dict(_fuzz_result(kwargs))


def _trust_data(kwargs: dict[str, Any]) -> object:
    from ruin.services.operations import _trust_model

    return to_dict(_trust_model(kwargs))


def _pipeline_status_data(kwargs: dict[str, Any]) -> object:
    from ruin.services.operations import _pipeline_state

    return to_dict(_pipeline_state(kwargs))


def _oracle_data(kwargs: dict[str, Any]) -> object:
    return to_dict(oracle_scaffold(kwargs))


def _flashloan_data(kwargs: dict[str, Any]) -> object:
    return to_dict(flashloan_scaffold(kwargs))


def _rng_hack_data(kwargs: dict[str, Any]) -> object:
    from ruin.services.operations import _rng_assessment

    return to_dict(_rng_assessment(kwargs))


def _finding_dedupe_data(kwargs: dict[str, Any]) -> object:
    registry, removed = dedupe_registry(Path(str(kwargs["file"])))
    data = to_dict(registry)
    return {**cast("dict[str, object]", data), "removed": removed}


def _rank_data(kwargs: dict[str, Any]) -> object:
    """Return ranked targets as structured rows (screen flag ignored)."""
    summaries = filtered_summaries(
        _chain_list(kwargs.get("chain")),
        _chain_list(kwargs.get("exclude_chain")),
    )
    ranked = rank_targets(summaries, int(kwargs.get("limit", 10)))
    return {
        "targets": [
            {
                "name": item.summary.name.as_str(),
                "tvl_usd": item.score,
                "chains": item.summary.chains,
                "slug": item.summary.slug,
            }
            for item in ranked
        ]
    }


def _finding_merge_data(kwargs: dict[str, Any]) -> object:
    registry, added = merge_into(Path(str(kwargs["file"])), Path(str(kwargs["other"])))
    data = to_dict(registry)
    return {**cast("dict[str, object]", data), "added": added}


BUILDERS: dict[str, Any] = {
    "rank": _rank_data,
    "screen": _screen_data,
    "triage": triage_data,
    "fuzz": _fuzz_data,
    "trust": _trust_data,
    "pipeline-status": _pipeline_status_data,
    "oracle": _oracle_data,
    "flashloan": _flashloan_data,
    "rng-hack": _rng_hack_data,
    "finding-list": lambda kw: to_dict(load_registry(Path(str(kw["file"])))),
    "finding-dedupe": _finding_dedupe_data,
    "finding-merge": _finding_merge_data,
}

BUILDERS.update(AGENT_BUILDERS)
BUILDERS.update(COSMOS_BUILDERS)
BUILDERS.update(MINTSIG_BUILDERS)
BUILDERS.update(CTOKEN_BUILDERS)
BUILDERS.update(DECOMPILE_BUILDERS)
BUILDERS.update(THIN_BUILDERS)
BUILDERS.update(PROTOCOL_BUILDERS)
