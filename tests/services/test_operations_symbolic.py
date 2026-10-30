"""Tests for the merged symbolic operation (record and run)."""

import pytest

from ruin.services import operations as ops
from ruin.services import symbolic as symbolic_service


class FakeProcess:
    def __init__(self, stdout: str = "proven", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


def test_symbolic_operation(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="proven", returncode=0)

    monkeypatch.setattr(symbolic_service, "run_command", fake_run)
    text = ops.run_operation("symbolic", {"target": "t"})
    assert "Symbolic" in text


def test_symbolic_run_flag_forces_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str]) -> FakeProcess:
        calls.append(argv)
        return FakeProcess(stdout="proven", returncode=0)

    monkeypatch.setattr(symbolic_service, "run_command", fake_run)
    text = ops.run_operation(
        "symbolic", {"target": "t", "tool": "mythril", "outcome": "proven", "run": True}
    )
    assert calls, "run flag did not execute the tool"
    assert "Symbolic" in text


def test_symbolic_invalid_tool() -> None:
    try:
        ops.run_operation("symbolic", {"target": "t", "tool": "nope"})
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_symbolic_record_style() -> None:
    text = ops.run_operation(
        "symbolic", {"target": "t", "outcome": "proven", "detail": "d"}
    )
    assert "Symbolic" in text


def test_symbolic_invalid_outcome() -> None:
    try:
        ops.run_operation("symbolic", {"target": "t", "outcome": "bad"})
    except ValueError:
        return
    raise AssertionError("expected ValueError")
