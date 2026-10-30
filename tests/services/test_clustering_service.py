"""Tests for the address-clustering service and ops."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.core.enums import Chain
from ruin.core.onchain import BytecodeInfo
from ruin.services.clustering import cluster_addresses, fetch_cluster_bytecodes
from ruin.services.operations import run_operation, run_operation_json

if TYPE_CHECKING:
    import pytest

_CLONE = (
    "0x363d3d373d3d3d363d73"
    + "2222222222222222222222222222222222222222"
    + "5af43d82803e903d91602b57fd5bf3"
)


class _FakeAdapter:
    chain = Chain.EVM

    def fetch_bytecode(self, address: str, rpc: str) -> BytecodeInfo:
        _ = rpc
        code = _CLONE if address in {"0xA", "0xB"} else f"0x{address[2:].lower()}"
        return BytecodeInfo(chain=Chain.EVM, address=address, hexcode=code)


def _patch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "ruin.services.clustering.get_adapter", lambda _chain: _FakeAdapter()
    )


def test_fetch_cluster_bytecodes_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    clusters = fetch_cluster_bytecodes(["0xA", "0xB", "0xC"], Chain.EVM, "http://x")
    clones = [c for c in clusters if c.kind == "clone"]
    assert len(clones) == 1
    assert set(clones[0].addresses) == {"0xA", "0xB"}


def test_cluster_addresses_renders(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    text = cluster_addresses(["0xA", "0xB"], Chain.EVM, "http://x")
    assert "shared-code groups: 1" in text


def test_run_operation_cluster(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    text = run_operation(
        "cluster", {"addresses": ["0xA", "0xB"], "rpc": "http://x", "chain": "EVM"}
    )
    assert "clones of" in text


def test_run_operation_json_cluster(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    data = run_operation_json(
        "cluster", {"addresses": ["0xA", "0xB"], "rpc": "http://x", "chain": "EVM"}
    )
    assert isinstance(data, list)
    first = data[0]
    assert isinstance(first, dict)
    assert first.get("kind") == "clone"
