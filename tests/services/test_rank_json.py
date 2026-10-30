"""Tests for the rank JSON builder."""

import pytest

from ruin.core.protocols import ProtocolSummary
from ruin.services.operations import run_operation_json


def _summaries() -> list[ProtocolSummary]:
    return [
        ProtocolSummary.new("Alpha", "alpha", 500, ["Ethereum"], "Dex"),
        ProtocolSummary.new("Beta", "beta", 900, ["Ethereum"], "Dex"),
        ProtocolSummary.new("Gamma", "gamma", 100, ["Solana"], "CEX"),
    ]


def test_rank_json_returns_structured_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ruin.services.http.fetch_protocols", _summaries)
    data = run_operation_json("rank", {"limit": 5})
    assert isinstance(data, dict)
    rows = data.get("targets")
    assert isinstance(rows, list)
    first = rows[0]
    assert isinstance(first, dict)
    assert first.get("name") == "Beta"
    assert first.get("tvl_usd") == 900
    assert first.get("slug") == "beta"
    assert first.get("chains") == ["Ethereum"]


def test_rank_json_honours_chain_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ruin.services.http.fetch_protocols", _summaries)
    data = run_operation_json("rank", {"limit": 5, "chain": "solana"})
    assert isinstance(data, dict)
    rows = data.get("targets")
    assert isinstance(rows, list)
    for row in rows:
        assert isinstance(row, dict)
        chains = row.get("chains")
        assert isinstance(chains, list)
        assert "Solana" in chains
