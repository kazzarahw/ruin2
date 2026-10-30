"""Extra slither_io tests."""

from ruin.core.slither_io import (
    parse_slither,
    parse_vulns,
    serialize_review_scaffold,
    serialize_vulns,
)


def test_slither_io() -> None:
    assert parse_slither("{}") == []
    text = serialize_review_scaffold("src")
    assert "source" in text
    vulns = parse_vulns('{"candidates": []}')
    assert vulns == []
    assert serialize_vulns([]) == "[]"
