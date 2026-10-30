"""Chain-agnostic RPC transport for ``ruin``.

The default transport uses ``httpx`` with bounded retry. Tests inject a fake
transport so adapter behavior is verified without any network access.
"""

from __future__ import annotations

import time
from typing import Any, Protocol, cast

import httpx

_RETRY_BASE_SECONDS = 0.1
_MAX_ATTEMPTS = 3
_TIMEOUT_SECONDS = 30.0


class RpcTransport(Protocol):
    """A minimal request transport used by chain adapters."""

    def post_json(self, url: str, payload: dict[str, Any], /) -> dict[str, Any]:
        """POST a JSON body and return the decoded JSON object."""

    def get_json(self, url: str, /) -> object:
        """GET a URL and return the decoded JSON body."""

    def get_text(self, url: str, /) -> str:
        """GET a URL and return the raw text body."""


class HttpxTransport:
    """Transport backed by ``httpx`` with bounded retry and backoff."""

    def __init__(self, *, attempts: int = _MAX_ATTEMPTS) -> None:
        """Initialize the transport with a retry budget."""
        self.attempts = max(1, attempts)

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST a JSON body and return the decoded JSON object."""
        doc = self._request("POST", url, payload)
        return cast("dict[str, Any]", doc)

    def get_json(self, url: str) -> object:
        """GET a URL and return the decoded JSON body."""
        return self._request("GET", url, None)

    def get_text(self, url: str) -> str:
        """GET a URL and return the raw text body."""
        return request_with_retry("GET", url, attempts=self.attempts).text

    def _request(self, method: str, url: str, payload: dict[str, Any] | None) -> object:
        response = request_with_retry(method, url, payload, attempts=self.attempts)
        try:
            return response.json()
        except ValueError as error:
            raise RuntimeError(f"failed to {method} {url}: {error}") from error


def request_with_retry(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    *,
    attempts: int = _MAX_ATTEMPTS,
    timeout: float = _TIMEOUT_SECONDS,
) -> httpx.Response:
    """Send one HTTP request with bounded retry, backoff, and status check.

    GET requests go through ``httpx.get``; any other method posts ``payload``
    as JSON. Sleeps geometric backoff between attempts.

    Raises:
        RuntimeError: If every attempt fails.
    """
    last_error: Exception | None = None
    for attempt in range(max(1, attempts)):
        try:
            response = (
                httpx.get(url, timeout=timeout)
                if payload is None
                else httpx.request(method, url, json=payload, timeout=timeout)
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            last_error = error
            if attempt < attempts - 1:
                time.sleep(_RETRY_BASE_SECONDS * (2**attempt))
            continue
        return response
    raise RuntimeError(f"failed to {method} {url}: {last_error}") from last_error


SHARED_TRANSPORT = HttpxTransport()


def jsonrpc(
    transport: RpcTransport, url: str, method: str, params: list[Any] | dict[str, Any]
) -> object:
    """Send a JSON-RPC 2.0 request and return the ``result`` field.

    Args:
        transport: The transport used to send the request.
        url: The RPC endpoint URL.
        method: The JSON-RPC method name.
        params: Positional or named parameters for the method.

    Returns:
        The ``result`` value from the JSON-RPC response.

    Raises:
        RuntimeError: If the response carries an ``error`` object.
    """
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }
    doc = transport.post_json(url, payload)
    error = doc.get("error")
    if error:
        raise RuntimeError(f"rpc error for {method}: {error}")
    return doc.get("result")
