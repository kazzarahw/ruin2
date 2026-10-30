"""Tests for the cToken donation-inflation fork screen."""

from typing import Any

import pytest

from ruin.services import balances
from ruin.services import fork as forkmod
from ruin.services import operations_builders_ctoken as ct_bh
from ruin.services import operations_ext_ctoken as ct

_DEV = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"


class _Proc:
    """Canned subprocess result."""

    def __init__(self, stdout: str, returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = ""
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


def _dispatch(bump: bool, underlying_ok: bool = True) -> Any:
    state = {"donations": 0, "dev_balance": 10**9}

    def _run(cmd: list[str], **_kw: Any) -> _Proc:
        joined = " ".join(cmd)
        out, rc = "0", 0
        if cmd[1] == "index":
            out = "0xabc"
        elif cmd[1] == "call" and "underlying" in joined:
            out, rc = ("", 1) if not underlying_ok else ("0x" + "ab" * 20, 0)
        elif cmd[1] == "call" and "getCash" in joined:
            out = "100000000 [1e8]"
        elif cmd[1] == "call" and "exchangeRateStored" in joined:
            out = "1010" if state["donations"] and bump else "1000"
        elif cmd[1] == "call" and "balanceOf" in joined and _DEV in joined:
            out = str(state["dev_balance"])
        elif cmd[1] == "send" and "transfer(" in joined:
            state["donations"] += 1
            state["dev_balance"] -= 10**7
            out = "0xreceipt"
        elif cmd[1] == "send":
            out = "0xreceipt"
        return _Proc(out, rc)

    return _run


@pytest.fixture
def fork_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralize fork lifecycle and RPC for the cToken screen."""
    monkeypatch.setattr(forkmod.subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(forkmod, "wait_for_ready", lambda *_a: None)
    monkeypatch.setattr(ct, "jsonrpc", lambda *_a, **_k: None)
    monkeypatch.setattr(balances, "jsonrpc", lambda *_a, **_k: None)


def test_not_ctoken_when_underlying_missing(
    fork_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkey = _dispatch(True, underlying_ok=False)
    monkeypatch.setattr(ct, "run_command", monkey)
    monkeypatch.setattr(balances, "run_command", monkey)
    data = ct.ctoken_inflation_data("0xCT", "http://rpc")
    assert data.verdict == "not-ctoken"


def test_exposed_market_flags_negative_cycle(
    fork_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkey = _dispatch(True)
    monkeypatch.setattr(ct, "run_command", monkey)
    monkeypatch.setattr(balances, "run_command", monkey)
    data = ct.ctoken_inflation_data("0xCT", "http://rpc")
    assert data.verdict == "exposed"
    assert any(s.startswith("ctoken-rate-exposed") for s in data.signals)
    assert "ctoken-cycle-negative" in data.signals


def test_flat_rate_market_is_clean(
    fork_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkey = _dispatch(False)
    monkeypatch.setattr(ct, "run_command", monkey)
    monkeypatch.setattr(balances, "run_command", monkey)
    data = ct.ctoken_inflation_data("0xCT", "http://rpc")
    assert data.verdict == "clean"
    assert data.signals == ()


def test_markdown_and_json_wiring(
    fork_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkey = _dispatch(True)
    monkeypatch.setattr(ct, "run_command", monkey)
    monkeypatch.setattr(balances, "run_command", monkey)
    kwargs = {"ctoken": "0xCT", "rpc": "http://rpc"}
    out = ct_bh.CTOKEN_OPERATIONS["ctoken-inflation"](kwargs)
    assert "# cToken inflation" in out
    assert "verdict: exposed" in out
    payload = ct_bh.CTOKEN_BUILDERS["ctoken-inflation"](kwargs)
    assert isinstance(payload, dict)
    assert payload["address"] == "0xCT"


def test_rate_read_failure_is_inconclusive(
    fork_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A rate call that errors must not be graded clean."""

    def _run(cmd: list[str], **_kw: Any) -> _Proc:
        joined = " ".join(cmd)
        out, rc = "0xreceipt", 0
        if cmd[1] == "call" and "exchangeRateStored" in joined:
            out, rc = "", 1
        elif cmd[1] == "call" and "underlying" in joined:
            out = "0x" + "ab" * 20
        elif cmd[1] == "call" and "getCash" in joined:
            out = "100000000 [1e8]"
        elif cmd[1] == "index":
            out = "0xabc"
        elif cmd[1] == "call" and "balanceOf" in joined:
            out = "1000000000"
        return _Proc(out, rc)

    monkeypatch.setattr(ct, "run_command", _run)
    monkeypatch.setattr(balances, "run_command", _run)
    data = ct.ctoken_inflation_data("0xCT", "http://rpc")
    assert data.verdict == "probe-inconclusive"
    assert data.signals == ("rate-read-failed",)


def test_getcash_read_failure_is_inconclusive(
    fork_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed getCash with live underlying must not read as not-ctoken."""

    def _run(cmd: list[str], **_kw: Any) -> _Proc:
        joined = " ".join(cmd)
        out, rc = "0xreceipt", 0
        if cmd[1] == "call" and "getCash" in joined:
            out, rc = "", 1
        elif cmd[1] == "call" and "underlying" in joined:
            out = "0x" + "ab" * 20
        return _Proc(out, rc)

    monkeypatch.setattr(ct, "run_command", _run)
    monkeypatch.setattr(balances, "run_command", _run)
    monkeypatch.setattr(ct, "_code_missing", lambda *_a: False)
    data = ct.ctoken_inflation_data("0xCT", "http://rpc")
    assert data.verdict == "probe-inconclusive"
    assert data.signals == ("getCash-read-failed",)


def test_zero_cash_market_reports_no_cash(
    fork_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fully utilized market (cash 0) is a cToken with nothing to donate."""

    def _run(cmd: list[str], **_kw: Any) -> _Proc:
        joined = " ".join(cmd)
        out, rc = "0xreceipt", 0
        if cmd[1] == "call" and "getCash" in joined:
            out = "0"
        elif cmd[1] == "call" and "underlying" in joined:
            out = "0x" + "ab" * 20
        return _Proc(out, rc)

    monkeypatch.setattr(ct, "run_command", _run)
    monkeypatch.setattr(balances, "run_command", _run)
    data = ct.ctoken_inflation_data("0xCT", "http://rpc")
    assert data.verdict == "no-cash"
