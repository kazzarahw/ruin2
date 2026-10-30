"""Tests for forensics service."""

import pytest

from ruin.core.forensics import LogEntry, LogScan


def test_log_scan_render() -> None:
    scan = LogScan(
        address="0xabc",
        from_block=100,
        to_block=200,
        entries=[
            LogEntry(
                address="0xabc",
                block=150,
                tx_hash="0xdeadbeef1234567890",
                event_signature="Transfer(address,address,uint256)",
            )
        ],
    )
    md = scan.render_markdown()
    assert "0xabc" in md
    assert "100" in md
    assert "Transfer" in md


def test_log_scan_empty() -> None:
    scan = LogScan(address="0xabc", from_block=1, to_block=10, entries=[])
    md = scan.render_markdown()
    assert "Events found: 0" in md


def test_trace_prefers_call_tracer(monkeypatch: pytest.MonkeyPatch) -> None:
    from ruin.services import forensics as svc

    monkeypatch.setattr(
        svc,
        "jsonrpc",
        lambda _t, _u, _m, _p: {
            "type": "CALL",
            "from": "0xA",
            "to": "0xB",
            "input": "0xa9059cbb00",
        },
    )
    monkeypatch.setattr(svc, "resolve_selectors", lambda _sels: {})
    trace = svc.trace_transaction("0xabc", "http://rpc")
    assert trace.steps == ["CALL 0xA -> 0xB 0xa9059cbb"]


def test_trace_annotates_selectors(monkeypatch: pytest.MonkeyPatch) -> None:
    from ruin.services import forensics as svc

    monkeypatch.setattr(
        svc,
        "jsonrpc",
        lambda _t, _u, _m, _p: {
            "type": "CALL",
            "from": "0xA",
            "to": "0xB",
            "input": "0xa9059cbb00",
        },
    )
    monkeypatch.setattr(
        svc,
        "resolve_selectors",
        lambda _sels: {"a9059cbb": "transfer(address,uint256)"},
    )
    trace = svc.trace_transaction("0xabc", "http://rpc")
    assert trace.steps == ["CALL 0xA -> 0xB 0xa9059cbb transfer(address,uint256)"]
    assert trace.note == ""


def test_trace_falls_back_to_tx_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    from ruin.services import forensics as svc

    def _boom(*_args: object, **_kw: object) -> None:
        raise RuntimeError("method not found")

    monkeypatch.setattr(svc, "jsonrpc", _boom)

    class _Proc:
        stdout = "type:       LEGACY\nnonce:      5\n"
        stderr = ""
        returncode = 0

    monkeypatch.setattr(svc, "run_command", lambda *_a, **_k: _Proc())
    trace = svc.trace_transaction("0xabc", "http://rpc")
    assert trace.note.startswith("callTracer unavailable")
    assert any("nonce" in step for step in trace.steps)


def test_scan_logs_chunks_large_ranges(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    from ruin.services import forensics as svc

    calls: list[tuple[int, int]] = []

    def _fake_run(
        cmd: list[str], timeout: float = 60.0
    ) -> subprocess.CompletedProcess[str]:
        lo = int(cmd[cmd.index("--from-block") + 1])
        hi = int(cmd[cmd.index("--to-block") + 1])
        calls.append((lo, hi))
        return subprocess.CompletedProcess(cmd, 0, "block number\n", "")

    monkeypatch.setattr(svc, "run_command", _fake_run)
    scan = svc.scan_logs("0xA", "http://rpc", 1000, 1250)
    assert calls == [(1000, 1099), (1100, 1199), (1200, 1250)]
    assert scan.entries == []
