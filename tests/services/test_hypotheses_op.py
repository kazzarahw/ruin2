"""Tests for the triage hypotheses mode and its JSON output."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.services.operations import run_operation, run_operation_json

if TYPE_CHECKING:
    from pathlib import Path


def test_hypotheses_mode_text() -> None:
    text = run_operation(
        "triage",
        {
            "name": "T",
            "mode": "hypotheses",
            "check": ["controlled-delegatecall"],
            "signal": ["oracle"],
        },
    )
    assert "# Hypotheses" in text
    assert "delegatecall" in text.lower()
    assert "Oracle" in text


def test_hypotheses_mode_json() -> None:
    data = run_operation_json(
        "triage", {"name": "T", "mode": "hypotheses", "signal": ["flash-loan"]}
    )
    assert isinstance(data, dict)
    items = data.get("items")
    assert isinstance(items, list)
    first = items[0]
    assert isinstance(first, dict)
    assert first.get("title") == "Flash-loan-amplified imbalance"


def test_hypotheses_mode_from_file(tmp_path: Path) -> None:
    report = tmp_path / "slither.json"
    report.write_text(
        '{"results": {"detectors": [{"check": "weak-prng"}]}}', encoding="utf-8"
    )
    text = run_operation(
        "triage", {"name": "T", "mode": "hypotheses", "file": str(report)}
    )
    assert "randomness" in text.lower()
