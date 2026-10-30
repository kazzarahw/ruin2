"""Tests for the shared balances-slot hunt."""

from typing import Any
from unittest.mock import patch

from ruin.core.slots import NAMED_BASE_SLOTS
from ruin.services import balances
from ruin.services.subprocesses import ANVIL_DEV_ADDRESS

_PROBE = 10**24


class _Proc:
    """Canned subprocess result."""

    def __init__(self, stdout: str, returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


def _run(found_base: int | None, empty_index: bool = False) -> Any:
    state: dict[str, int | None] = {"written": None}

    def _dispatch(cmd: list[str], **_kw: Any) -> _Proc:
        if cmd[1] == "index":
            if empty_index:
                return _Proc("")
            base = int(cmd[4], 16)
            return _Proc(f"0x{base:064x}")
        if cmd[1] == "call" and "balanceOf" in " ".join(cmd):
            hit = state["written"] is not None and state["written"] == found_base
            return _Proc(str(_PROBE if hit else 0))
        return _Proc("")

    return _dispatch, state


def _fake_jsonrpc(state: dict[str, int | None]) -> Any:
    def _call(_t: object, _u: str, method: str, params: list[Any]) -> object:
        if method == "anvil_setStorageAt":
            state["written"] = int(str(params[1]), 16)
        return "0x1"

    return _call


def test_find_balance_slot_hits_legacy_base() -> None:
    run, state = _run(3)
    with (
        patch.object(balances, "run_command", run),
        patch.object(balances, "jsonrpc", _fake_jsonrpc(state)),
    ):
        base, key = balances.find_balance_slot("http://rpc", "0xT", ANVIL_DEV_ADDRESS)
    assert base == 3
    assert key == f"0x{3:064x}"


def test_find_balance_slot_reports_miss() -> None:
    run, state = _run(None)
    with (
        patch.object(balances, "run_command", run),
        patch.object(balances, "jsonrpc", _fake_jsonrpc(state)),
    ):
        base, key = balances.find_balance_slot("http://rpc", "0xT", ANVIL_DEV_ADDRESS)
    assert base == -1
    assert key == ""


def test_find_balance_slot_skips_unusable_index() -> None:
    run, state = _run(3, empty_index=True)
    with (
        patch.object(balances, "run_command", run),
        patch.object(balances, "jsonrpc", _fake_jsonrpc(state)),
    ):
        base, _key = balances.find_balance_slot("http://rpc", "0xT", ANVIL_DEV_ADDRESS)
    assert base == -1


def test_find_balance_slot_names_erc7201_base() -> None:
    named = NAMED_BASE_SLOTS["ERC20"]
    run, state = _run(named)
    with (
        patch.object(balances, "run_command", run),
        patch.object(balances, "jsonrpc", _fake_jsonrpc(state)),
    ):
        base, _key = balances.find_balance_slot("http://rpc", "0xT", ANVIL_DEV_ADDRESS)
    assert base == named


def test_find_balance_slot_respects_max_base() -> None:
    run, state = _run(30)
    seen: list[int] = []

    def _spy(cmd: list[str], **kw: Any) -> Any:
        if cmd[1] == "index":
            seen.append(int(cmd[4], 16))
        return run(cmd, **kw)

    with (
        patch.object(balances, "run_command", _spy),
        patch.object(balances, "jsonrpc", _fake_jsonrpc(state)),
    ):
        base, _key = balances.find_balance_slot(
            "http://rpc", "0xT", ANVIL_DEV_ADDRESS, max_base=48
        )
    assert base == 30
    assert 30 in seen
    legacy = [b for b in seen if b < 10**6]
    assert legacy == list(range(31))


def test_find_balance_slot_custom_probe_value() -> None:
    run, state = _run(None)

    def _probe_seven(cmd: list[str], **kw: Any) -> Any:
        out = run(cmd, **kw)
        if cmd[1] == "call" and "balanceOf" in " ".join(cmd) and state["written"] == 7:
            return _Proc("7")
        return out

    with (
        patch.object(balances, "run_command", _probe_seven),
        patch.object(balances, "jsonrpc", _fake_jsonrpc(state)),
    ):
        base, _key = balances.find_balance_slot(
            "http://rpc", "0xT", ANVIL_DEV_ADDRESS, probe_value=7
        )
    assert base == 7
