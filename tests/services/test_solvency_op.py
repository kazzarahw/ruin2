"""Tests for the solvency operation wiring."""

import subprocess
from typing import Any

import pytest

from ruin.services import operations_ext_solvency as sol


def _completed(stdout: str) -> Any:
    return subprocess.CompletedProcess(["cast"], 0, stdout, "")


def test_solvency_probes_underlying_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def _fake_run(cmd: list[str], timeout: float = 60.0) -> Any:
        calls.append(cmd)
        sig = cmd[3]
        out = {
            "underlying()(address)": "0xTOKEN",
            "totalAssets()(uint256)": "100 [100e2]",
            "balanceOf(address)(uint256)": "150",
            "totalSupply()(uint256)": "10",
        }[sig]
        return _completed(out)

    monkeypatch.setattr(sol, "run_command", _fake_run)
    out = sol._solvency({"vault": "0xVAULT", "rpc": "http://rpc"})
    assert "underlying: 0xTOKEN" in out
    assert "delta: 50" in out
    assert "inflation-exposed" in out
    assert len(calls) == 4


def test_solvency_skips_probe_when_underlying_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def _fake_run(cmd: list[str], timeout: float = 60.0) -> Any:
        calls.append(cmd)
        sig = cmd[3]
        out = {
            "totalAssets()(uint256)": "100",
            "balanceOf(address)(uint256)": "0",
            "totalSupply()(uint256)": "10",
        }[sig]
        return _completed(out)

    monkeypatch.setattr(sol, "run_command", _fake_run)
    out = sol._solvency(
        {"vault": "0xVAULT", "rpc": "http://rpc", "underlying": "0xTOK"}
    )
    assert "assets-not-custodied" in out
    assert len(calls) == 3


def test_solvency_falls_back_to_asset_accessor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def _fake_run(cmd: list[str], timeout: float = 60.0) -> Any:
        calls.append(cmd)
        sig = cmd[3]
        if sig in ("underlying()(address)", "want()(address)"):
            return subprocess.CompletedProcess(cmd, 1, "", "reverted")
        out = {
            "asset()(address)": "0xASSET",
            "totalAssets()(uint256)": "100",
            "balanceOf(address)(uint256)": "150",
            "totalSupply()(uint256)": "10",
        }[sig]
        return _completed(out)

    monkeypatch.setattr(sol, "run_command", _fake_run)
    out = sol._solvency({"vault": "0xVAULT", "rpc": "http://rpc"})
    assert "underlying: 0xASSET" in out
    assert "inflation-exposed" in out
    assert len(calls) == 6
