"""Tests for exploit replay timeline."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

from ruin.core.forensics import TransactionTrace
from ruin.core.replay import Timeline

if TYPE_CHECKING:
    from typing import Any

    import pytest

from ruin.core.forensics import LogEntry, LogScan
from ruin.services.forensics import replay_transaction
from ruin.services.operations import run_operation


def test_timeline_render() -> None:
    timeline = Timeline(
        tx_hash="0xabc",
        address="0xdef",
        from_block=1,
        to_block=5,
        steps=["CALL 0xdef", "REVERT"],
        events=[(2, "0xabc", "Transfer(address,address,uint256)")],
    )
    text = timeline.render_markdown()
    assert "# Replay" in text
    assert "REVERT" in text
    assert "Transfer" in text


def test_timeline_empty() -> None:
    text = Timeline(tx_hash="0x1").render_markdown()
    assert "Trace steps (0)" in text


def test_replay_transaction_composes(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_trace(tx_hash: str, rpc: str) -> TransactionTrace:
        _ = rpc
        return TransactionTrace(tx_hash=tx_hash, steps=["CALL A"])

    def fake_logs(address: str, rpc: str, frm: int, to: int) -> LogScan:
        _ = rpc
        return LogScan(
            address=address,
            from_block=frm,
            to_block=to,
            entries=[
                LogEntry(
                    address=address, block=3, tx_hash="0xabc", event_signature="Mint"
                )
            ],
        )

    monkeypatch.setattr("ruin.services.forensics.trace_transaction", fake_trace)
    monkeypatch.setattr("ruin.services.forensics.scan_logs", fake_logs)
    timeline = replay_transaction("0xabc", "0xdef", "http://x", 1, 5)
    assert timeline.steps == ["CALL A"]
    assert timeline.events == [(3, "0xabc", "Mint")]


def test_replay_non_evm_degrades() -> None:
    text = run_operation(
        "replay",
        {
            "tx": "0xabc",
            "address": "0xdef",
            "rpc": "http://x",
            "from_block": 1,
            "to_block": 2,
            "chain": "Solana",
        },
    )
    assert "not supported" in text


def test_replay_carries_trace_caveat_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ruin.core.forensics import TransactionTrace

    def fake_trace(tx_hash: str, rpc: str) -> TransactionTrace:
        return TransactionTrace(
            tx_hash=tx_hash,
            steps=["raw field line"],
            note="callTracer unavailable on this RPC; showing raw transaction fields",
        )

    def fake_logs(address: str, rpc: str, start: int, end: int) -> Any:
        return SimpleNamespace(entries=[])

    monkeypatch.setattr("ruin.services.forensics.trace_transaction", fake_trace)
    monkeypatch.setattr("ruin.services.forensics.scan_logs", fake_logs)
    timeline = replay_transaction("0xabc", "0xdef", "http://x", 1, 5)
    assert timeline.note.startswith("callTracer unavailable")
    assert "note:" in timeline.render_markdown()
