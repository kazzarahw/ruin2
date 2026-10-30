"""Tests for http service."""

from typing import Any, cast

import httpx
import pytest

from ruin.services import http as http_service


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_fetch_protocols(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(_url: str, **_kwargs: object) -> FakeResponse:
        return FakeResponse("[]")

    monkeypatch.setattr(httpx, "get", fake_get)
    assert http_service.fetch_protocols() == []


def test_ranked_text() -> None:
    def empty_protocols() -> list[object]:
        return []

    cast("Any", http_service).fetch_protocols = empty_protocols
    text = http_service.ranked_text(1, [], [], None)
    assert "top 0" in text


def test_fetch_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(_url: str, **_kwargs: object) -> FakeResponse:
        return FakeResponse("{}")

    monkeypatch.setattr(httpx, "get", fake_get)
    assert http_service.fetch_protocol("slug") == "{}"
