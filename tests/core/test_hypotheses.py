"""Tests for hypothesis generation."""

from __future__ import annotations

from ruin.core.enums import Severity
from ruin.core.hypotheses import build_hypotheses


def test_hypotheses_from_checks() -> None:
    result = build_hypotheses("T", ["reentrancy-no-eth", "weak-prng"])
    titles = [h.title for h in result.items]
    assert any("Reentrancy" in t for t in titles)
    assert any("randomness" in t.lower() for t in titles)
    # ranked: HIGH before MEDIUM
    severities = [h.severity for h in result.items]
    assert severities[0] is Severity.HIGH


def test_hypotheses_from_signals() -> None:
    result = build_hypotheses("T", [], ["oracle", "upgradeable", "nonsense"])
    titles = [h.title for h in result.items]
    assert any("Oracle" in t for t in titles)
    assert any("Upgrade" in t for t in titles)
    assert len(result.items) == 2


def test_hypotheses_dedup_by_title() -> None:
    # block-timestamp check and oracle signal both mention price; titles differ,
    # but passing the same check twice must not duplicate.
    result = build_hypotheses("T", ["reentrancy-no-eth", "reentrancy-no-eth"])
    titles = [h.title for h in result.items]
    assert titles.count(titles[0]) == 1


def test_hypotheses_empty() -> None:
    result = build_hypotheses("T", [], [])
    assert result.items == []
    assert "No hypotheses" in result.render_markdown()


def test_hypotheses_render() -> None:
    result = build_hypotheses("T", ["controlled-delegatecall"])
    text = result.render_markdown()
    assert "# Hypotheses" in text
    assert "delegatecall" in text.lower()
    assert "test:" in text
