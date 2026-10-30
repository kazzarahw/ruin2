"""Tests for the shared API dispatch helper."""

from __future__ import annotations

import asyncio

import pytest

from ruin.api import _call


def test_call_prefers_the_structured_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_json(operation: str, kwargs: dict[str, object]) -> dict[str, bool]:
        seen.append(operation)
        return {"ok": True}

    def fake_markdown(operation: str, kwargs: dict[str, object]) -> str:
        seen.append(f"markdown:{operation}")
        return "text"

    monkeypatch.setattr(_call, "run_operation_json", fake_json)
    monkeypatch.setattr(_call, "run_operation", fake_markdown)
    result = asyncio.run(_call.call("rank", {}))
    assert result == {"ok": True}
    assert seen == ["rank"]


def test_call_falls_back_to_text_without_a_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_json(operation: str, kwargs: dict[str, object]) -> dict[str, bool]:
        raise ValueError(f"no structured output for: {operation}")

    def fake_markdown(operation: str, kwargs: dict[str, object]) -> str:
        return f"text:{operation}"

    monkeypatch.setattr(_call, "run_operation_json", fake_json)
    monkeypatch.setattr(_call, "run_operation", fake_markdown)
    result = asyncio.run(_call.call("trace", {}))
    assert result == "text:trace"


def test_domain_value_error_propagates_without_text_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    def fake_json(operation: str, kwargs: dict[str, object]) -> dict[str, bool]:
        raise ValueError("kind must be fuzz|invariant")

    def fake_markdown(operation: str, kwargs: dict[str, object]) -> str:
        seen.append(operation)
        return "text"

    monkeypatch.setattr(_call, "run_operation_json", fake_json)
    monkeypatch.setattr(_call, "run_operation", fake_markdown)
    with pytest.raises(ValueError, match="kind must be"):
        asyncio.run(_call.call("rank", {}))
    assert seen == []
