"""Extra scoring tests."""

from ruin.core.protocols import ProtocolSummary
from ruin.core.scoring import score


def test_score() -> None:
    summary = ProtocolSummary.new("A", "a", 10, ["Ethereum"], "Defi")
    assert score(summary) == 10
