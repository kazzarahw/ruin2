"""Tests for symbolic service."""

from typing import cast

import pytest

from ruin.core.domain import Target
from ruin.core.enums import SymbolicOutcome, TargetMode
from ruin.services import symbolic as symbolic_service


class FakeProcess:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _patch(monkeypatch: pytest.MonkeyPatch, fake_run: object) -> None:
    monkeypatch.setattr(symbolic_service, "run_command", fake_run)


def test_halmos_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv: list[str]) -> FakeProcess:
        assert argv == ["halmos"]
        return FakeProcess(stdout="proven", returncode=0)

    _patch(monkeypatch, fake_run)
    adapter = symbolic_service.HalmosAdapter()
    result = adapter.run("Target")
    assert result.outcome == SymbolicOutcome.PROVEN
    assert result.skipped is False
    assert result.tool == "halmos"


def test_halmos_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="counterexample found", returncode=1)

    _patch(monkeypatch, fake_run)
    adapter = symbolic_service.HalmosAdapter()
    result = adapter.run("Target")
    assert result.outcome == SymbolicOutcome.UNDECIDED
    assert result.counterexample is not None


def test_halmos_missing_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        raise FileNotFoundError("halmos")

    _patch(monkeypatch, fake_run)
    result = symbolic_service.HalmosAdapter().run("Target")
    assert result.skipped is True
    assert result.outcome == SymbolicOutcome.ERROR


def test_halmos_command_override(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, list[str]] = {}

    def fake_run(argv: list[str]) -> FakeProcess:
        captured["argv"] = list(argv)
        return FakeProcess(stdout="ok", returncode=0)

    _patch(monkeypatch, fake_run)
    adapter = symbolic_service.HalmosAdapter(command=["halmos", "--loop"])
    result = adapter.run("Target")
    assert captured["argv"] == ["halmos", "--loop"]
    assert result.outcome == SymbolicOutcome.PROVEN


def test_mythril(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv: list[str]) -> FakeProcess:
        assert argv[0] == "myth"
        return FakeProcess(stdout="no issues found", returncode=0)

    _patch(monkeypatch, fake_run)
    adapter = symbolic_service.MythrilAdapter()
    result = adapter.run("Target")
    assert result.outcome == SymbolicOutcome.PROVEN

    def fake_fail(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="issue found", returncode=1)

    _patch(monkeypatch, fake_fail)
    result2 = symbolic_service.MythrilAdapter().run("Target")
    assert result2.outcome == SymbolicOutcome.UNDECIDED


def test_mythril_missing_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        raise FileNotFoundError("myth")

    _patch(monkeypatch, fake_run)
    assert symbolic_service.MythrilAdapter().run("Target").skipped is True


def test_linked_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="proven", returncode=0)

    _patch(monkeypatch, fake_run)
    result = symbolic_service.HalmosAdapter().run("Target", finding="reentrancy")
    assert result.linked_finding == "reentrancy"


def test_parse_functions() -> None:
    outcome, _detail, ce = symbolic_service.parse_halmos_output(
        "counterexample found", "", 1
    )
    assert outcome == SymbolicOutcome.UNDECIDED
    assert ce is not None

    outcome2, _, _ = symbolic_service.parse_halmos_output("proven", "", 0)
    assert outcome2 == SymbolicOutcome.PROVEN

    outcome3, _, _ = symbolic_service.parse_mythril_output("error", "", 2)
    assert outcome3 == SymbolicOutcome.ERROR

    outcome4, _, _ = symbolic_service.parse_mythril_output("no issues", "", 0)
    assert outcome4 == SymbolicOutcome.PROVEN


def test_target_name(monkeypatch: pytest.MonkeyPatch) -> None:

    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="proven", returncode=0)

    _patch(monkeypatch, fake_run)
    target = Target.new("P", [], None, TargetMode.RESEARCH)
    result = symbolic_service.HalmosAdapter().run(target)
    assert result.target == "P"


def test_command_list_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="proven", returncode=0)

    _patch(monkeypatch, fake_run)
    adapter = symbolic_service.HalmosAdapter(command="halmos --foo")
    assert adapter.run("Target").outcome == SymbolicOutcome.PROVEN

    adapter2 = symbolic_service.HalmosAdapter(command=cast("str | None", 123))
    assert adapter2.run("Target").outcome == SymbolicOutcome.PROVEN

    med = symbolic_service.MythrilAdapter(command=["myth", "analyze"])
    assert med.run("Target").outcome == SymbolicOutcome.PROVEN


def test_run_method_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="proven", returncode=0)

    _patch(monkeypatch, fake_run)
    adapter = symbolic_service.HalmosAdapter()
    result = adapter.run("Target")
    assert result.skipped is False
    result2 = adapter.run("Target")
    assert result2.outcome == SymbolicOutcome.PROVEN


def test_parse_unsupported() -> None:
    outcome, _, _ = symbolic_service.parse_halmos_output("unsupported feature", "", 0)
    assert outcome == SymbolicOutcome.UNSUPPORTED
    outcome2, _, _ = symbolic_service.parse_mythril_output("unsupported", "", 0)
    assert outcome2 == SymbolicOutcome.UNSUPPORTED


def test_target_name_string(monkeypatch: pytest.MonkeyPatch) -> None:
    class Obj:
        name = "foo"

    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="proven", returncode=0)

    _patch(monkeypatch, fake_run)
    result = symbolic_service.HalmosAdapter().run(Obj())
    assert result.target == "foo"


def test_parse_empty_errors() -> None:
    outcome, _, _ = symbolic_service.parse_halmos_output("", "", 2)
    assert outcome == SymbolicOutcome.ERROR
    outcome2, _, _ = symbolic_service.parse_mythril_output("", "", 2)
    assert outcome2 == SymbolicOutcome.ERROR


def test_wrapper_methods(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="proven", returncode=0)

    _patch(monkeypatch, fake_run)
    adapter = symbolic_service.HalmosAdapter()
    assert adapter.run("Target").outcome == SymbolicOutcome.PROVEN
