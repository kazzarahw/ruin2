"""Tests for the balances-slot hunt operation."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

from ruin.core.slots import NAMED_BASE_SLOTS
from ruin.services import balances
from ruin.services import fork as forkmod
from ruin.services import operations_ext_slot as slot
from ruin.services.subprocesses import ANVIL_DEV_ADDRESS


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


def _slot_marker(slot_hex: str) -> int:
    """Recover the base slot from the mocked index digest tail."""
    tail = int(slot_hex[-8:], 16)
    return (tail >> 8) & 0xFFFFFF if tail & 0xFF == 0x5F else -1


def _layout_run(found_base: int | None) -> Any:
    state: dict[str, int | None] = {"written": None}

    def _run(cmd: list[str], **_kw: Any) -> _Proc:
        if cmd[1] == "index":
            base = int(cmd[4], 16) & 0xFFFFFF
            return _Proc(f"0x{(base << 8) | 0x5F:064x}")
        if cmd[1] == "call" and "balanceOf" in " ".join(cmd):
            return _Proc(str(_PROBE if state["written"] == found_base else 0))
        return _Proc("")

    return _run, state


_PROBE = slot._PROBE_VALUE


def _fake_jsonrpc(found_base: int | None, state: dict[str, int | None]) -> Any:
    def _call(_t: object, _u: str, method: str, params: list[Any]) -> object:
        if method == "anvil_setStorageAt":
            state["written"] = _slot_marker(str(params[1]))
            return "0x1"
        return "0x1"

    return _call


@contextmanager
def _patched(found_base: int | None) -> Generator[None, None, None]:
    run, state = _layout_run(found_base)
    with (
        patch.object(forkmod.subprocess, "Popen", _FakePopen),
        patch.object(forkmod, "wait_for_ready", lambda *_a: None),
        patch.object(balances, "jsonrpc", _fake_jsonrpc(found_base, state)),
        patch.object(balances, "run_command", run),
        patch.object(slot, "jsonrpc", lambda *_a: "0x1"),
    ):
        yield


def test_slot_hunt_finds_legacy_base() -> None:
    digest = 0x7
    with _patched(digest):
        data = slot.hunt_slot("http://rpc", "0xT", ANVIL_DEV_ADDRESS)
    assert data.found is True
    assert data.base_slot == hex(digest)


def test_slot_hunt_names_erc7201_base() -> None:
    masked = NAMED_BASE_SLOTS["ERC20"] & 0xFFFFFF
    with _patched(masked):
        data = slot.hunt_slot("http://rpc", "0xT", ANVIL_DEV_ADDRESS)
    assert data.found is True
    assert data.family == "ERC20"


def test_slot_hunt_reports_not_found() -> None:
    with _patched(None):
        data = slot.hunt_slot("http://rpc", "0xT", ANVIL_DEV_ADDRESS)
    assert data.found is False
    assert "slot-not-found" in data.signals


def test_slot_hunt_survives_fork_failure() -> None:
    def _boom(_endpoint: str) -> None:
        raise RuntimeError("fork did not boot")

    with (
        patch.object(forkmod.subprocess, "Popen", _FakePopen),
        patch.object(forkmod, "wait_for_ready", _boom),
    ):
        data = slot.hunt_slot("http://rpc", "0xT", ANVIL_DEV_ADDRESS)
    assert data.found is False
    assert "fork-unavailable" in data.signals
