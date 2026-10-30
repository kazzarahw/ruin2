"""Tests for the bytecode decompile review operation."""

from pathlib import Path
from typing import Any, cast

import pytest

from ruin.core import decompile as dc_core
from ruin.services import operations_builders_decompile as dc_bh
from ruin.services import operations_ext_decompile as dc
from ruin.services import operations_ext_selectors as sel

# callvalue+gas+address(CALL) then STATICCALL, DELEGATECALL, two SSTOREs.
CALLS_CODE = "0x345a3073" + "aa" * 20 + "f15afa5af4600155600255"
# PUSH32 base-slot constant followed by an SSTORE, then one far from any store.
PUSH_CODE = "0x7f" + "ab" * 32 + "600055" + "7f" + "cd" * 32
_REVERT_TEXT = "Ownable: caller is not the owner"
REVERT_CODE = (
    "0x" + _REVERT_TEXT.encode().hex() + "00" + _REVERT_TEXT.encode().hex() + "00abcd"
)


def test_scan_opcodes_counts_call_delegatecall_staticcall() -> None:
    scan = cast("dict[str, Any]", dc_core.scan_opcodes(CALLS_CODE))
    counts = cast("dict[str, int]", scan["counts"])
    assert counts["call"] == 1
    assert counts["delegatecall"] == 1
    assert counts["staticcall"] == 1
    assert counts["sstore"] == 2


def test_scan_opcodes_skips_push_immediates() -> None:
    scan = cast("dict[str, Any]", dc_core.scan_opcodes("0x60f15af4"))
    counts = cast("dict[str, int]", scan["counts"])
    assert counts["call"] == 0
    assert counts["delegatecall"] == 1
    assert not scan["value_call"]


def test_scan_opcodes_flags_value_call_preamble() -> None:
    scan = cast("dict[str, Any]", dc_core.scan_opcodes(CALLS_CODE))
    assert scan["value_call"]


def test_scan_opcodes_lists_push32_near_sstore() -> None:
    scan = cast("dict[str, Any]", dc_core.scan_opcodes(PUSH_CODE))
    assert scan["push32_near_sstore"] == ["0x" + "ab" * 32]


def test_extract_revert_strings_dedups_and_drops_short_runs() -> None:
    assert dc_core.extract_revert_strings(REVERT_CODE) == [_REVERT_TEXT]


def test_extract_revert_strings_caps_at_forty() -> None:
    code = "0x" + "00".join(f"run{i:03d}".encode().hex() for i in range(41))
    assert len(dc_core.extract_revert_strings(code)) == 40


def test_scan_opcodes_rejects_non_hex() -> None:
    with pytest.raises(ValueError, match="hex string"):
        dc_core.scan_opcodes("0xzz")


def test_report_shape_and_thin_dispatch() -> None:
    report = dc_core.bytecode_report(
        "0xA", CALLS_CODE, [("0x2e1a7d4d", "withdraw(uint256)")], "", rpc="http://rpc"
    )
    assert report.address == "0xA"
    assert report.rpc == "http://rpc"
    assert report.codesize == 35
    assert report.payable_count == "unknown"
    assert report.dispatcher.selector_count == 1
    assert report.dispatcher.thin_dispatch


def test_report_risk_flags_delegatecall_and_destruct() -> None:
    report = dc_core.bytecode_report("0xA", CALLS_CODE + "f4", [], "")
    assert "has-delegatecall" in report.risk_flags
    assert "has-value-call" in report.risk_flags
    assert "has-selfdestruct" not in report.risk_flags
    created = dc_core.bytecode_report("0xA", "0xf0f5ff", [], "").risk_flags
    assert "has-create" in created
    assert "has-selfdestruct" in created


def test_decompile_data_raises_when_no_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dc, "code_at", lambda _rpc, _addr: "0x")
    with pytest.raises(ValueError, match="no code at"):
        dc.decompile_data("0xA", "http://rpc")


def test_rpc_failure_surfaces_as_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fail(_cmd: list[str], **_kw: Any) -> Any:
        class Result:
            stdout = ""
            stderr = "Error: server returned an error response: 403 Forbidden"
            returncode = 1

        return Result()

    monkeypatch.setattr(sel, "run_command", _fail)
    with pytest.raises(RuntimeError, match="rpc failure"):
        dc_bh.DECOMPILE_OPERATIONS["decompile"]({"address": "0xA", "rpc": "http://rpc"})


def _fake_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        dc, "code_at", lambda _rpc, _addr: CALLS_CODE + PUSH_CODE.removeprefix("0x")
    )
    monkeypatch.setattr(
        dc,
        "inventory",
        lambda _code, **_kw: [("0x2e1a7d4d", "withdraw(uint256)")],
    )


def test_markdown_and_json_wiring(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_service(monkeypatch)
    kwargs = {"address": "0xA", "rpc": "http://rpc"}
    out = dc_bh.DECOMPILE_OPERATIONS["decompile"](kwargs)
    assert "# Decompile" in out
    assert "`0x2e1a7d4d` withdraw(uint256)" in out
    assert "thin dispatch: True" in out
    assert "has-delegatecall" in out
    assert "push32 words near sstore: 0x" + "ab" * 32 in out
    payload = cast("dict[str, Any]", dc_bh.DECOMPILE_BUILDERS["decompile"](kwargs))
    assert payload["address"] == "0xA"
    assert payload["selectors"][0]["selector"] == "0x2e1a7d4d"
    assert payload["calls"]["staticcall"] == 1


def test_out_writes_report_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fake_service(monkeypatch)
    target = tmp_path / "report.md"
    out = dc_bh.DECOMPILE_OPERATIONS["decompile"](
        {"address": "0xA", "rpc": "http://rpc", "out": str(target)}
    )
    assert out == f"wrote {target}"
    assert "# Decompile" in target.read_text(encoding="utf-8")


def test_decompile_registered_in_operations_and_builders() -> None:
    from ruin.services.operations import _OPERATIONS
    from ruin.services.operations_builders import BUILDERS

    assert "decompile" in cast("dict[str, Any]", _OPERATIONS)
    assert "decompile" in BUILDERS


def test_decompile_follows_eip1967_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A short proxy code body must be resolved to its implementation."""
    proxy_code = "0x" + "3660006000376000526000f4" * 10
    impl_code = "0x" + "600055" * 6

    monkeypatch.setattr(
        dc,
        "code_at",
        lambda _rpc, addr: proxy_code if addr.endswith("A") else impl_code,
    )

    def _run(cmd: list[str], **_kw: Any) -> Any:
        out = "0x" + "0" * 63 + "B" if cmd[1] == "storage" else impl_code

        class Result:
            stdout = out
            stderr = ""
            returncode = 0

        return Result()

    monkeypatch.setattr(sel, "run_command", _run)
    monkeypatch.setattr(
        dc, "inventory", lambda _code, **_kw: [("0x01e1d114", "totalAssets()")]
    )
    data = dc.decompile_data("0xA", "http://rpc")
    assert data.codesize == (len(impl_code) - 2) // 2


def _oracle_service(
    monkeypatch: pytest.MonkeyPatch, base_vault_out: str, _rc: int = 0
) -> None:
    """Fake decompile service whose oracle answers BASE_VAULT() on demand."""
    monkeypatch.setattr(
        dc, "code_at", lambda _rpc, _addr: CALLS_CODE + PUSH_CODE.removeprefix("0x")
    )
    monkeypatch.setattr(
        dc,
        "inventory",
        lambda _code, **_kw: [
            ("0xeaa2d7b4", "BASE_VAULT()"),
            ("0x2e1a7d4d", "withdraw(uint256)"),
        ],
    )

    def _run(_cmd: list[str], **_kw: Any) -> Any:
        class Result:
            stdout = base_vault_out
            stderr = ""
            returncode = _rc

        return Result()

    monkeypatch.setattr(dc, "run_command", _run)


def test_oracle_link_zero_word_is_unlinked(monkeypatch: pytest.MonkeyPatch) -> None:
    _oracle_service(monkeypatch, "0x" + "0" * 64)
    payload = dc.decompile_data("0xA", "http://rpc")
    assert payload.oracle_base_vault == ""
    assert payload.oracle_linked is False


def test_oracle_link_nonzero_word_is_linked(monkeypatch: pytest.MonkeyPatch) -> None:
    linked_word = "0x" + "0" * 24 + "16931dcc888754ae780b153598376a6474de4440"
    _oracle_service(monkeypatch, linked_word)
    payload = dc.decompile_data("0xA", "http://rpc")
    assert payload.oracle_base_vault == "0x16931dcc888754ae780b153598376a6474de4440"
    assert payload.oracle_linked is True
    text = dc_bh.DECOMPILE_OPERATIONS["decompile"](
        {"address": "0xA", "rpc": "http://rpc"}
    )
    assert "oracle BASE_VAULT: 0x16931dcc" in text
    assert "(linked: True)" in text


def test_oracle_selector_absent_yields_no_oracle_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_service(monkeypatch)
    payload = dc.decompile_data("0xA", "http://rpc")
    assert payload.oracle_base_vault is None
    assert payload.oracle_linked is None


def test_oracle_call_failure_marks_unreadable(monkeypatch: pytest.MonkeyPatch) -> None:
    _oracle_service(monkeypatch, "", 1)
    payload = dc.decompile_data("0xA", "http://rpc")
    assert payload.oracle_base_vault == "unreadable"
    assert payload.oracle_linked is False
