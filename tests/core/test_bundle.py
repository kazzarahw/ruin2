"""Tests for bundle."""

from ruin.core.bundle import report_bundle


def test_bundle() -> None:
    bundle = report_bundle("P")
    assert "Report Bundle" in bundle.render_markdown()
