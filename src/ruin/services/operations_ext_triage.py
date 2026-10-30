"""Merged triage operation: checks, exploits, hypotheses, and source modes.

One CLI leaf (``source triage``) and one operation dispatch on ``mode``:
``checks`` classifies detector/check names (leads vs noise), ``exploits``
matches checks to the known-exploit DB, ``hypotheses`` ranks investigation
leads from checks plus structural signals, and ``source`` triages raw
source-code smells. The former ``triage``/``exploits``/``hypotheses``
operations are these modes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruin.core.exploits import ExploitReport, exploit_report
from ruin.core.hypotheses import HypothesisSet, build_hypotheses
from ruin.core.smells import source_smells
from ruin.core.triage import (
    VulnTriage,
    slither_checks,
    triage_from_source,
    triage_vulns,
)
from ruin.services.files import write_or_render
from ruin.services.serialize import to_dict

TRIAGE_MODES: tuple[str, ...] = ("checks", "exploits", "hypotheses", "source")


def _mode(kwargs: dict[str, Any]) -> str:
    mode = str(kwargs.get("mode", "checks"))
    if mode not in TRIAGE_MODES:
        raise ValueError("mode must be checks|exploits|hypotheses|source")
    return mode


def _read(path: object) -> str:
    return Path(str(path)).read_text(encoding="utf-8")


def _checks_from(kwargs: dict[str, Any]) -> list[str]:
    """Detector check names from a Slither JSON file, else from check flags."""
    if kwargs.get("file"):
        return slither_checks(_read(kwargs["file"]))
    return list(kwargs.get("check", []))


def _triage_object(
    kwargs: dict[str, Any],
) -> VulnTriage | ExploitReport | HypothesisSet:
    """Build the per-mode domain object (triage, exploit, or hypothesis set)."""
    name = str(kwargs["name"])
    mode = _mode(kwargs)
    if mode == "exploits":
        return exploit_report(name, _checks_from(kwargs))
    if mode == "hypotheses":
        return build_hypotheses(
            name, _checks_from(kwargs), list(kwargs.get("signal", []))
        )
    if mode == "source":
        source = kwargs.get("source")
        if source is None:
            raise ValueError("triage mode source needs a source file")
        return triage_from_source(name, _read(source))
    checks: list[str] = []
    if kwargs.get("file"):
        checks.extend(slither_checks(_read(kwargs["file"])))
    if kwargs.get("source"):
        checks.extend(source_smells(_read(kwargs["source"])))
    checks.extend(list(kwargs.get("check", [])))
    return triage_vulns(name, checks)


def _write_or_text(markdown: str, kwargs: dict[str, Any]) -> str:
    return write_or_render(kwargs.get("out"), markdown)


def triage_text(kwargs: dict[str, Any]) -> str:
    """Render the merged triage report for the requested mode."""
    report = _triage_object(kwargs)
    return _write_or_text(report.render_markdown(), kwargs)


def triage_data(kwargs: dict[str, Any]) -> object:
    """Build the per-mode structured payload (same fields as the old ops)."""
    return to_dict(_triage_object(kwargs))


TRIAGE_OPERATIONS: dict[str, Any] = {"triage": triage_text}
