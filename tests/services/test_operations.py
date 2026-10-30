"""Tests for operations."""

from contextlib import suppress

import pytest

from ruin.services.operations import run_operation


def test_unknown_operation() -> None:
    with suppress(ValueError):
        run_operation("nope", {})


def test_rank_coerces_string_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    from ruin.services import operations as ops

    captured: dict[str, list[str]] = {}

    def fake_ranked(
        _limit: int, chains: list[str], exclude: list[str], _screen: object
    ) -> str:
        captured["chains"] = chains
        captured["exclude"] = exclude
        return "ok"

    from ruin.services import operations_ext as ext

    monkeypatch.setattr(ext, "ranked_text", fake_ranked)
    out = ops.run_operation(
        "rank", {"limit": 5, "chain": "ethereum", "exclude_chain": "polygon"}
    )
    assert out == "ok"
    assert captured["chains"] == ["ethereum"]
    assert captured["exclude"] == ["polygon"]
    out = ops.run_operation("rank", {"limit": 5, "chain": ["a", "b"]})
    assert captured["chains"] == ["a", "b"]
