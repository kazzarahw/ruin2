"""Tests for the EVM honeypot fork probe."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, cast
from unittest.mock import patch

import pytest

from ruin.core.honeypot import evm_verdict
from ruin.services import balances
from ruin.services import fork as forkmod
from ruin.services import operations_ext_donation as don
from ruin.services import operations_ext_honeypot_evm as hev
from ruin.services import operations_ext_selectors as sel
from ruin.services.subprocesses import ANVIL_DEV_ADDRESS as _DEV
from ruin.services.subprocesses import parse_cast_int


class _Proc:
    """Canned subprocess result."""

    def __init__(self, stdout: str, returncode: int = 0, stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class _FakePopen:
    """No-op anvil stand-in."""

    def __init__(self, *_a: object, **_k: object) -> None:
        pass

    @staticmethod
    def kill() -> None:
        return None

    @staticmethod
    def wait() -> int:
        return 0


def _dispatch(found_slot: bool) -> Any:
    state = {"sent": 0}

    def _run(cmd: list[str], **_kw: Any) -> _Proc:
        joined = " ".join(cmd)
        out, rc = "", 0
        if cmd[1] == "index":
            out = "0xabc" if found_slot else "0xdead"
        elif cmd[1] == "call" and "balanceOf" in joined:
            if _DEV in joined:
                out = "1000000000000000000000000" if found_slot else "0"
            else:
                out = str(10**18) if state["sent"] else "0"
        elif cmd[1] == "send":
            state["sent"] += 1
            out = "0xreceipt"
        elif cmd[1] == "call" and "mint" in joined:
            rc = 1
        return _Proc(out, rc)

    return _run


@contextmanager
def _env(runner: Any) -> Generator[None, None, None]:
    with (
        patch.object(hev, "run_command", side_effect=runner),
        patch.object(hev, "jsonrpc", return_value=None),
        patch.object(forkmod.subprocess, "Popen", _FakePopen),
        patch.object(forkmod, "wait_for_ready", return_value=None),
        patch.object(don, "run_command", side_effect=runner),
        patch.object(don, "jsonrpc", return_value=None),
        patch.object(balances, "run_command", side_effect=runner),
        patch.object(balances, "jsonrpc", return_value=None),
        patch.object(sel, "run_command", side_effect=runner),
    ):
        yield


def test_parse_cast_int_treats_empty_hex_as_zero() -> None:
    """RPC-flap empty words ('0x') must not crash the probe."""
    assert parse_cast_int("0x") == 0
    assert parse_cast_int("") == 0
    assert parse_cast_int("0x0") == 0


def test_evm_verdict_grading() -> None:
    assert evm_verdict(["transfer-reverts"], 0.0) == "high"
    assert evm_verdict([], 3.5) == "high"
    assert evm_verdict(["unlimited-mint-possible"], 0.0) == "medium"
    assert evm_verdict([], 0.5) == "medium"
    assert evm_verdict([], 0.0) == "clean"
    assert evm_verdict(["balance-slot-not-found"], 0.0) == "unknown"


def test_honeypot_evm_clean_token() -> None:
    with _env(_dispatch(True)):
        out = hev.HONEYPOT_EVM_OPERATIONS["honeypot-evm"](
            {"token": "0xT", "rpc": "http://rpc"}
        )
    assert "verdict: low" in out
    assert "fee_pct: 0.0" in out
    assert "balances slot: 0" in out
    assert "donation-probe-skipped" in out


def test_honeypot_evm_slot_hunt_failure() -> None:
    with _env(_dispatch(False)):
        data = hev.evm_honeypot_data("0xT", "http://rpc")
    assert data.verdict == "unknown"
    assert data.balances_slot == -1


def test_honeypot_evm_rejects_unknown_chain() -> None:
    import pytest

    with pytest.raises(ValueError, match="unknown chain"):
        hev.HONEYPOT_EVM_OPERATIONS["honeypot-evm"](
            {"token": "0xT", "rpc": "", "chain": "platypus"}
        )


def test_honeypot_evm_surfaces_revert_reason() -> None:
    def _run(cmd: list[str], **_kw: Any) -> _Proc:
        joined = " ".join(cmd)
        if cmd[1] == "balance":
            return _Proc("0")
        if cmd[1] == "send":
            return _Proc("", 1, stderr="Error: execution reverted: BNE")
        if cmd[1] == "call" and "mint" in joined:
            return _Proc("", 1)
        if cmd[1] == "call":
            return _Proc("1000000000000000000000000")
        return _Proc("0x")

    with _env(_run):
        data = hev.evm_honeypot_data("0xT", "http://rpc")
    signals = data.signals
    assert isinstance(signals, tuple)
    assert "transfer-reverts" in signals
    assert "revert-reason:BNE" in signals


def test_honeypot_evm_fork_startup_timeout_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(_endpoint: str) -> None:
        raise RuntimeError("command timed out")

    monkeypatch.setattr(forkmod, "wait_for_ready", _boom)
    with patch.object(forkmod.subprocess, "Popen", _FakePopen):
        data = hev.evm_honeypot_data("0xT", "http://rpc")
    assert data.verdict == "unknown"
    assert data.signals == ("fork-unavailable",)


_DONATION_STATE: dict[str, int] = {"previews": 0, "recv": 0}


def _donation_dispatch(cmd: list[str], **_kw: Any) -> _Proc:
    joined = " ".join(cmd)
    out = ""
    rc = 0
    if cmd[1] == "index":
        out = "0xabc"
    elif cmd[1] == "code":
        out = "0x60806301e1d1141463a9059cbb14"
    elif cmd[1] == "call" and "balanceOf" in joined:
        if _DEV in joined:
            out = "1000000000000000000000000"
        else:
            out = "0" if _DONATION_STATE["recv"] == 0 else "1000000000000000000"
    elif cmd[1] == "call" and "asset()" in joined:
        out = "0x00000000000000000000000000000000000000aa"
    elif cmd[1] == "call" and "totalAssets" in joined:
        out = "1000000"
    elif cmd[1] == "call" and "previewDeposit" in joined:
        _DONATION_STATE["previews"] += 1
        out = "1000" if _DONATION_STATE["previews"] == 1 else "900"
    elif cmd[1] == "send":
        _DONATION_STATE["recv"] += 1
        out = "0xreceipt"
    else:
        rc = 1
    return _Proc(out, rc)


@contextmanager
def _patched_donation_probe() -> Generator[None, None, None]:
    _DONATION_STATE.update({"previews": 0, "recv": 0})
    with (
        patch.object(forkmod.subprocess, "Popen", _FakePopen),
        patch.object(hev, "run_command", _donation_dispatch),
        patch.object(forkmod, "wait_for_ready", lambda *_a: None),
        patch.object(hev, "jsonrpc", lambda *_a: "0x1"),
        patch.object(don, "run_command", _donation_dispatch),
        patch.object(don, "jsonrpc", lambda *_a: "0x1"),
        patch.object(balances, "run_command", _donation_dispatch),
        patch.object(balances, "jsonrpc", lambda *_a: "0x1"),
    ):
        yield


def test_donation_probe_flags_dilution() -> None:
    with _patched_donation_probe():
        data = hev.evm_honeypot_data("0xV", "http://rpc")
    signals = cast("list[str]", data.signals)
    assert any("donation-dilution-exposed" in s for s in signals)
    assert data.verdict == "medium"


def test_donation_probe_runs_for_custom_slot_proxy() -> None:
    """A proxy answering totalAssets() is probed even with no visible selectors."""

    def _proxy_dispatch(cmd: list[str], **_kw: Any) -> _Proc:
        out, rc = "", 0
        if cmd[1] == "index":
            out = "0xabc"
        elif cmd[1] == "code":
            out = "0x608060405234801561001057600080fd5b5060"
        elif cmd[1] == "call" and "balanceOf" in " ".join(cmd):
            out = "1000000000000000000000000" if _DEV in " ".join(cmd) else "0"
        elif cmd[1] == "call" and "asset()" in " ".join(cmd):
            out = "0x00000000000000000000000000000000000000aa"
        elif cmd[1] == "call" and "totalAssets" in " ".join(cmd):
            out = "1000000"
        elif cmd[1] == "call" and "previewDeposit" in " ".join(cmd):
            _DONATION_STATE["previews"] += 1
            out = "1000" if _DONATION_STATE["previews"] == 1 else "900"
        elif cmd[1] == "send":
            _DONATION_STATE["recv"] += 1
            out = "0xreceipt"
        else:
            rc = 1
        return _Proc(out, rc)

    _DONATION_STATE.update({"previews": 0, "recv": 0})
    with (
        patch.object(forkmod.subprocess, "Popen", _FakePopen),
        patch.object(forkmod, "wait_for_ready", lambda *_a: None),
        patch.object(hev, "jsonrpc", lambda *_a: "0x1"),
        patch.object(hev, "run_command", _proxy_dispatch),
        patch.object(don, "jsonrpc", lambda *_a: "0x1"),
        patch.object(don, "run_command", _proxy_dispatch),
        patch.object(balances, "run_command", _proxy_dispatch),
        patch.object(balances, "jsonrpc", lambda *_a: "0x1"),
        patch.object(sel, "run_command", _proxy_dispatch),
    ):
        data = hev.evm_honeypot_data("0xP", "http://rpc")
    signals = cast("list[str]", data.signals)
    assert any("donation-dilution-exposed" in s for s in signals)


def test_donation_probe_ratio_mode_for_erc7540() -> None:
    """ERC-7540 vaults without previewDeposit are judged on NAV-per-share."""

    def _rc7540(cmd: list[str], **_kw: Any) -> _Proc:
        joined = " ".join(cmd)
        out, rc = "", 0
        if cmd[1] == "index":
            out = "0xabc"
        elif cmd[1] == "code":
            out = "0x60806301e1d1141463a9059cbb14"
        elif cmd[1] == "call" and "balanceOf" in joined:
            out = "1000000000000000000000000" if _DEV in joined else "0"
        elif cmd[1] == "call" and "asset()" in joined:
            out = "0x00000000000000000000000000000000000000aa"
        elif cmd[1] == "call" and "totalAssets" in joined:
            _DONATION_STATE["recv"] += 1
            out = "1000000" if _DONATION_STATE["recv"] == 1 else "1010000"
        elif cmd[1] == "call" and "totalSupply" in joined:
            out = "1000000"
        elif cmd[1] == "call" and "previewDeposit" in joined:
            rc = 1
        elif cmd[1] == "send":
            out = "0xreceipt"
        else:
            rc = 1
        return _Proc(out, rc)

    _DONATION_STATE.update({"previews": 0, "recv": 0})
    with (
        patch.object(forkmod.subprocess, "Popen", _FakePopen),
        patch.object(forkmod, "wait_for_ready", lambda *_a: None),
        patch.object(hev, "jsonrpc", lambda *_a: "0x1"),
        patch.object(hev, "run_command", _rc7540),
        patch.object(don, "jsonrpc", lambda *_a: "0x1"),
        patch.object(don, "run_command", _rc7540),
        patch.object(balances, "run_command", _rc7540),
        patch.object(balances, "jsonrpc", lambda *_a: "0x1"),
    ):
        data = hev.evm_honeypot_data("0xR", "http://rpc")
    signals = cast("list[str]", data.signals)
    assert any("donation-dilution-exposed:1.0%" in s for s in signals)


def test_fork_retries_once_before_giving_up() -> None:
    """A flaky fork backend gets a second spawn before fork-unavailable."""
    attempts: list[int] = []

    def _flaky_ready(_endpoint: str) -> None:
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("endpoint not ready")

    def _neutral(cmd: list[str], **_kw: Any) -> _Proc:
        if cmd[1] == "index":
            return _Proc("0xabc")
        return _Proc("", 1)

    with (
        patch.object(forkmod.subprocess, "Popen", _FakePopen),
        patch.object(forkmod, "wait_for_ready", _flaky_ready),
        patch.object(hev, "jsonrpc", lambda *_a: "0x1"),
        patch.object(hev, "run_command", _neutral),
        patch.object(don, "jsonrpc", lambda *_a: "0x1"),
        patch.object(don, "run_command", _neutral),
        patch.object(balances, "run_command", _neutral),
        patch.object(balances, "jsonrpc", lambda *_a: "0x1"),
        patch.object(sel, "run_command", _neutral),
    ):
        data = hev.evm_honeypot_data("0xF", "http://rpc")
    assert len(attempts) == 2
    assert "fork-unavailable" not in cast("list[str]", data.signals)


def test_fork_unavailable_falls_back_to_static_shape() -> None:
    def _forked(cmd: list[str], **_kw: Any) -> _Proc:
        if cmd[1] == "index":
            return _Proc("0xabc")
        if cmd[1] == "call" and "balanceOf" in " ".join(cmd):
            return _Proc("1000000000000000000000000")
        return _Proc("", 1, "Fork Error: missing trie node")

    def _code(_transport: object, _url: str, method: str, _params: list[Any]) -> object:
        if method == "eth_getCode":
            return "0x6080638a8c523c1463751039fc14637d1db4a514"
        return "0x1"

    with (
        patch.object(forkmod.subprocess, "Popen", _FakePopen),
        patch.object(forkmod, "wait_for_ready", lambda *_a: None),
        patch.object(hev, "jsonrpc", _code),
        patch.object(hev, "run_command", _forked),
        patch.object(don, "jsonrpc", _code),
        patch.object(don, "run_command", _forked),
        patch.object(balances, "run_command", _forked),
        patch.object(balances, "jsonrpc", _code),
        patch.object(sel, "run_command", _forked),
    ):
        data = hev.evm_honeypot_data("0xT", "http://rpc")
    assert data.verdict == "high"
    assert "tax-gate-shape-detected" in cast("list[str]", data.signals)


def _stale_env(monkey: Any) -> tuple[Any, Any]:
    """Fork env where setStorage(0) flips the vault balance to empty."""
    state = {"drained": False}

    def _storage(_t: Any, _u: str, method: str, params: Any) -> Any:
        if method == "anvil_setStorageAt":
            value = str(params[2]) if isinstance(params, list) else ""
            state["drained"] = value == "0x" + "0" * 64
        return None

    def _run(cmd: list[str], **_kw: Any) -> _Proc:
        joined = " ".join(cmd)
        out, rc = "0xreceipt", 0
        if cmd[1] == "index":
            out = "0xabc"
        elif cmd[1] == "call" and "totalAssets" in joined:
            out = "100" if state["drained"] else "1000000000000000000"
        elif cmd[1] == "call" and "previewDeposit" in joined:
            out = "1000000000000000000"
        elif cmd[1] == "call" and "asset()" in joined:
            out = "0x" + "0" * 63 + "1"
        elif cmd[1] == "call" and "totalSupply" in joined:
            out = "1000000000000000000"
        elif cmd[1] == "call" and "balanceOf" in joined:
            out = "1000000000000000000000000"
        return _Proc(out, rc)

    return _run, _storage


def test_donation_probe_flags_stale_rate_cache() -> None:
    """Balance-driven totalAssets + frozen quote = drain-first stale cache."""
    runner, storage = _stale_env(None)
    with (
        patch.object(don, "run_command", side_effect=runner),
        patch.object(don, "jsonrpc", side_effect=storage),
        patch.object(balances, "run_command", side_effect=runner),
        patch.object(balances, "jsonrpc", side_effect=storage),
    ):
        signals = don.probe_donation("http://rpc", "0x" + "ab" * 20)
    assert "stale-rate-cache-drain-first" in signals
    assert "donation-probe-clean" in signals


def test_fresh_quote_vault_has_no_stale_flag() -> None:
    """A vault whose quote collapses with its balance is not flagged."""
    state = {"drained": False}

    def _storage(_t: Any, _u: str, method: str, params: Any) -> Any:
        if method == "anvil_setStorageAt":
            value = str(params[2]) if isinstance(params, list) else ""
            state["drained"] = value == "0x" + "0" * 64
        return None

    def _run(cmd: list[str], **_kw: Any) -> _Proc:
        joined = " ".join(cmd)
        out, rc = "0xreceipt", 0
        if cmd[1] == "index":
            out = "0xabc"
        elif cmd[1] == "call" and "totalAssets" in joined:
            out = "100" if state["drained"] else "1000000000000000000"
        elif cmd[1] == "call" and "previewDeposit" in joined:
            out = (
                "1000000000000000000000000"
                if state["drained"]
                else "1000000000000000000"
            )
        elif cmd[1] == "call" and "asset()" in joined:
            out = "0x" + "0" * 63 + "1"
        elif cmd[1] == "call" and "totalSupply" in joined:
            out = "1000000000000000000"
        elif cmd[1] == "call" and "balanceOf" in joined:
            out = "1000000000000000000000000"
        return _Proc(out, rc)

    with (
        patch.object(don, "run_command", side_effect=_run),
        patch.object(don, "jsonrpc", side_effect=_storage),
        patch.object(balances, "run_command", side_effect=_run),
        patch.object(balances, "jsonrpc", side_effect=_storage),
    ):
        signals = don.probe_donation("http://rpc", "0x" + "ab" * 20)
    assert "stale-rate-cache-drain-first" not in signals
