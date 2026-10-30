"""More http tests."""

import httpx
import pytest

from ruin.services import http as http_service
from ruin.services import rpc as rpc_service


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("bad")


def test_request_with_retry_success(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def fake_get(_url: str, **_kwargs: object) -> FakeResponse:
        calls["count"] += 1
        if calls["count"] == 1:
            raise httpx.ConnectError("boom")
        return FakeResponse("[]")

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(rpc_service.time, "sleep", lambda *_args, **_kwargs: None)
    assert rpc_service.request_with_retry("GET", "https://example.com").text == "[]"


def test_request_with_retry_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(_url: str, **_kwargs: object) -> FakeResponse:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(rpc_service.time, "sleep", lambda *_args, **_kwargs: None)
    try:
        rpc_service.request_with_retry("GET", "https://example.com", attempts=2)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")


def test_fetch_protocol_invalid_slug() -> None:
    try:
        http_service.fetch_protocol(" ")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")
