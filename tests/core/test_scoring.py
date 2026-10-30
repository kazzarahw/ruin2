"""Tests for scoring."""

from ruin.core.protocols import ProtocolSummary
from ruin.core.scoring import exclude_chains, filter_cex, filter_chains, rank_targets


def test_rank_targets() -> None:
    summary = ProtocolSummary.new("A", "a", 10, ["Ethereum"], "Defi")
    ranked = rank_targets([summary], 1)
    assert len(ranked) == 1


def test_filters() -> None:
    summary = ProtocolSummary.new("A", "a", 10, ["Ethereum"], "CEX")
    assert filter_cex([summary]) == []
    assert filter_chains([summary], ["Ethereum"]) == [summary]
    assert exclude_chains([summary], ["Ethereum"]) == []


def test_chain_filters_ignore_case() -> None:
    summary = ProtocolSummary.new("A", "a", 10, ["Ethereum"], "Defi")
    assert filter_chains([summary], ["ethereum"]) == [summary]
    assert exclude_chains([summary], ["ETHEREUM"]) == []
