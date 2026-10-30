"""Tests for the chain-aware inspect operation."""

from __future__ import annotations

from ruin.services.operations import run_operation, run_operation_json


def test_inspect_evm_without_rpc() -> None:
    text = run_operation("inspect", {"address": "0x" + "a" * 40, "chain": "EVM"})
    assert "# Digest" in text
    assert "EVM" in text
    assert "Analyzers available: slither, semgrep" in text


def test_inspect_solana_without_rpc() -> None:
    text = run_operation(
        "inspect",
        {"address": "So11111111111111111111111111111111111111112", "chain": "SOLANA"},
    )
    assert "Solana" in text
    assert "anchor-check" in text


def test_inspect_unknown_chain_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="unknown chain"):
        run_operation("inspect", {"address": "0x1", "chain": "ZORP"})


def test_inspect_json_shape() -> None:
    data = run_operation_json("inspect", {"address": "0x" + "b" * 40, "chain": "EVM"})
    assert isinstance(data, dict)
    assert data.get("chain") == "EVM"
    assert data.get("address") == "0x" + "b" * 40


def test_logs_non_evm_degrades() -> None:
    text = run_operation(
        "logs",
        {
            "address": "So11111111111111111111111111111111111111112",
            "rpc": "http://x",
            "from_block": 1,
            "to_block": 2,
            "chain": "Solana",
        },
    )
    assert "not supported" in text
    assert "inspect" in text


def test_logs_non_evm_json() -> None:
    data = run_operation_json(
        "logs",
        {
            "address": "EQCh2LI3pKp4B5PPNWB0bS9tQYbB4d2bD0dD0dD0dD0d",
            "rpc": "http://x",
            "from_block": 1,
            "to_block": 2,
            "chain": "TON",
        },
    )
    assert isinstance(data, dict)
    assert data.get("supported") is False
