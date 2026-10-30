"""Tests for drain probing."""

import subprocess
from collections.abc import Sequence

import pytest

from ruin.core.probe import (
    DRAIN_SELECTORS,
    ProbeHit,
    ProbeReport,
    drain_selectors_in,
    extract_selectors,
    minimal_proxy_implementation,
)
from ruin.services.probe import probe_drain_selectors

_WITHDRAW_PUSH4 = "638814fa271457600055"


def test_extract_selectors_finds_dispatcher_jumps() -> None:
    code = "0x608060" + _WITHDRAW_PUSH4 + "63a9059cbb14"
    assert extract_selectors(code) == ("0x8814fa27", "0xa9059cbb")


def test_drain_selectors_in_filters_known_names() -> None:
    code = "0x" + _WITHDRAW_PUSH4
    pairs = drain_selectors_in(code)
    assert pairs == [("0x8814fa27", "withdraw()")]
    assert "0xa9059cbb" not in DRAIN_SELECTORS


def test_minimal_proxy_implementation_extraction() -> None:
    clone = (
        "0x363d3d373d3d3d363d73"
        "0d424072d658e6abd92c36f8fc16fd6479ae15a0"
        "5af43d82803e903d91602b57fd5bf3"
    )
    assert minimal_proxy_implementation(clone) == (
        "0x0d424072d658e6abd92c36f8fc16fd6479ae15a0"
    )
    assert minimal_proxy_implementation("0x6001600101") == ""


def test_probe_follows_minimal_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    clone = (
        "0x363d3d373d3d3d363d73"
        "0d424072d658e6abd92c36f8fc16fd6479ae15a0"
        "5af43d82803e903d91602b57fd5bf3"
    )

    def fake_run(
        argv: Sequence[str], *, timeout: float = 30.0
    ) -> subprocess.CompletedProcess[str]:
        del timeout
        if argv[1] == "code":
            return subprocess.CompletedProcess(
                args=list(argv), returncode=0, stdout="0x" + _WITHDRAW_PUSH4, stderr=""
            )
        return subprocess.CompletedProcess(
            args=list(argv), returncode=0, stdout="0x", stderr=""
        )

    monkeypatch.setattr("ruin.services.probe.run_command", fake_run)
    hits = probe_drain_selectors("0xA", "http://x", clone, probe_from="0xB")
    assert [h.selector for h in hits] == ["0x8814fa27"]
    assert not hits[0].reverted


def test_probe_marks_reverts(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"0x8814fa27": 0, "0xed4fffe0": 1}

    def fake_run(
        argv: Sequence[str], *, timeout: float = 30.0
    ) -> subprocess.CompletedProcess[str]:
        del timeout
        return subprocess.CompletedProcess(
            args=list(argv), returncode=calls.get(argv[5], 1), stdout="", stderr=""
        )

    monkeypatch.setattr("ruin.services.probe.run_command", fake_run)
    code = "0x" + _WITHDRAW_PUSH4 + "63ed4fffe014"
    hits = probe_drain_selectors("0xA", "http://x", code, probe_from="0xB")
    by_sel = {h.selector: h.reverted for h in hits}
    assert by_sel == {"0x8814fa27": False, "0xed4fffe0": True}


def test_probe_report_markdown_sections() -> None:
    hits = [ProbeHit("0x8814fa27", "withdraw()", reverted=False)]
    text = ProbeReport(address="0xA", hits=tuple(hits)).render_markdown()
    assert "withdraw()" in text
    assert "[ok]" in text
    assert "smoke signal" in text
    empty = ProbeReport(address="0xA").render_markdown()
    assert "No drain-shaped selectors" in empty


def test_probe_json_lists_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        argv: Sequence[str], *, timeout: float = 30.0
    ) -> subprocess.CompletedProcess[str]:
        del timeout
        return subprocess.CompletedProcess(
            args=list(argv), returncode=0, stdout="0x60" + _WITHDRAW_PUSH4, stderr=""
        )

    monkeypatch.setattr("ruin.services.operations_builders_probe.run_command", fake_run)
    monkeypatch.setattr("ruin.services.probe.run_command", fake_run)
    from ruin.services import operations_builders_probe as ob_probe

    data = ob_probe._probe_data(
        {"address": "0xA", "rpc": "http://x", "probe_from": "0xB"}
    )
    assert isinstance(data, dict)
    hits = data.get("hits")
    assert isinstance(hits, list)
    assert hits == [
        {"selector": "0x8814fa27", "signature": "withdraw()", "reverted": False}
    ]


def test_probe_follows_eip7702_delegation(monkeypatch: pytest.MonkeyPatch) -> None:
    delegated = "0xef01000d424072d658e6abd92c36f8fc16fd6479ae15a0"
    seen: list[str] = []

    def fake_run(
        argv: Sequence[str], *, timeout: float = 30.0
    ) -> subprocess.CompletedProcess[str]:
        del timeout
        if argv[1] == "code":
            seen.append(argv[2])
            return subprocess.CompletedProcess(
                args=list(argv), returncode=0, stdout="0x" + _WITHDRAW_PUSH4, stderr=""
            )
        return subprocess.CompletedProcess(
            args=list(argv), returncode=0, stdout="0x", stderr=""
        )

    monkeypatch.setattr("ruin.services.probe.run_command", fake_run)
    hits = probe_drain_selectors("0xA", "http://x", delegated, probe_from="0xB")
    assert "0x0d424072d658e6abd92c36f8fc16fd6479ae15a0" in seen
    assert [h.selector for h in hits] == ["0x8814fa27"]


def test_probe_follows_eip1967_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    impl = "0x2222222222222222222222222222222222222222"
    slot_word = "0x000000000000000000000000" + impl.removeprefix("0x")
    shell = "0x6080604052600a600c565b005b60186014601a565b6050565b565b"
    seen: list[str] = []

    def fake_run(
        argv: Sequence[str], *, timeout: float = 30.0
    ) -> subprocess.CompletedProcess[str]:
        del timeout
        if argv[1] == "storage":
            return subprocess.CompletedProcess(
                args=list(argv), returncode=0, stdout=slot_word, stderr=""
            )
        if argv[1] == "code":
            seen.append(argv[2])
            return subprocess.CompletedProcess(
                args=list(argv), returncode=0, stdout="0x" + _WITHDRAW_PUSH4, stderr=""
            )
        return subprocess.CompletedProcess(
            args=list(argv), returncode=0, stdout="0x", stderr=""
        )

    monkeypatch.setattr("ruin.services.probe.run_command", fake_run)
    hits = probe_drain_selectors("0xA", "http://x", shell, probe_from="0xB")
    assert impl in seen
    assert [h.selector for h in hits] == ["0x8814fa27"]


def test_probe_skips_on_transport_error(monkeypatch: pytest.MonkeyPatch) -> None:
    code = "0x608060" + _WITHDRAW_PUSH4

    def fake_run(
        argv: Sequence[str], *, timeout: float = 30.0
    ) -> subprocess.CompletedProcess[str]:
        del timeout, argv
        return subprocess.CompletedProcess(
            args=["cast"],
            returncode=1,
            stdout="",
            stderr="error code -32603: 403 Forbidden",
        )

    monkeypatch.setattr("ruin.services.probe.run_command", fake_run)
    hits = probe_drain_selectors("0xA", "http://x", code, probe_from="0xB")
    assert [h.signature for h in hits] == ["1 selector(s) skipped: RPC transport error"]


def test_extract_selectors_falls_back_for_assembly_dispatch() -> None:
    code = "0x60016000" + "63a9059cbb600f55" + "6370a0823180" + "611234"
    sels = extract_selectors(code)
    assert "0xa9059cbb" in sels
    assert "0x70a08231" in sels


def test_probe_extra_selectors_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"0xdeadbeef": 0, "0x11111111": 1}

    def fake_run(
        argv: Sequence[str], *, timeout: float = 30.0
    ) -> subprocess.CompletedProcess[str]:
        del timeout
        return subprocess.CompletedProcess(
            args=list(argv), returncode=calls.get(argv[5], 1), stdout="", stderr=""
        )

    monkeypatch.setattr("ruin.services.probe.run_command", fake_run)
    hits = probe_drain_selectors(
        "0xA",
        "http://x",
        "0x6001600101",
        probe_from="0xB",
        extra_selectors=("0xdeadbeef", "0x11111111"),
    )
    by_sel = {h.selector: h.reverted for h in hits}
    assert by_sel == {"0xdeadbeef": False, "0x11111111": True}
    for hit in hits:
        assert hit.signature == "custom selector probe"


def test_probe_extra_selector_requires_hex(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        argv: Sequence[str], *, timeout: float = 30.0
    ) -> subprocess.CompletedProcess[str]:
        del timeout
        return subprocess.CompletedProcess(
            args=list(argv), returncode=0, stdout="", stderr=""
        )

    monkeypatch.setattr("ruin.services.probe.run_command", fake_run)
    with pytest.raises(ValueError, match="invalid selector"):
        probe_drain_selectors(
            "0xA",
            "http://x",
            "0x6001600101",
            probe_from="0xB",
            extra_selectors=("deadbeef",),
        )


def test_extract_selectors_keeps_adjacency_first() -> None:
    code = "0x63095ea7b31463deadbeef60"
    sels = extract_selectors(code)
    assert "0x095ea7b3" in sels
