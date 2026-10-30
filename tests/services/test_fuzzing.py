"""Tests for fuzzing service."""

from typing import cast

import pytest

from ruin.core.domain import Target
from ruin.core.enums import FuzzOutcome, TargetMode
from ruin.services import fuzzing as fuzzing_service


class FakeProcess:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _patch(monkeypatch: pytest.MonkeyPatch, fake_run: object) -> None:
    monkeypatch.setattr(fuzzing_service, "run_command", fake_run)


def test_foundry_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv: list[str]) -> FakeProcess:
        assert argv == ["forge", "test", "--match-test", "testFoo"]
        return FakeProcess(stdout="test result: ok", returncode=0)

    _patch(monkeypatch, fake_run)
    fuzzer = fuzzing_service.FoundryFuzzer(match_test="testFoo")
    result = fuzzer.fuzz("Target")
    assert result.outcome == FuzzOutcome.PASSED
    assert result.skipped is False
    assert result.counterexample is None


def test_foundry_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess(
            stdout="FAIL: invariant broken\nCounterexample: x = 1", returncode=1
        )

    _patch(monkeypatch, fake_run)
    fuzzer = fuzzing_service.FoundryFuzzer()
    result = fuzzer.fuzz("Target", match_test="testFoo")
    assert result.outcome == FuzzOutcome.VIOLATED
    assert result.counterexample is not None
    assert "Counterexample" in result.render_markdown()


def test_foundry_missing_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        raise FileNotFoundError("forge")

    _patch(monkeypatch, fake_run)
    fuzzer = fuzzing_service.FoundryFuzzer()
    result = fuzzer.fuzz("Target")
    assert result.skipped is True
    assert result.outcome == FuzzOutcome.ERRORED


def test_foundry_command_override(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, list[str]] = {}

    def fake_run(argv: list[str]) -> FakeProcess:
        captured["argv"] = list(argv)
        return FakeProcess(stdout="ok", returncode=0)

    _patch(monkeypatch, fake_run)
    fuzzer = fuzzing_service.FoundryFuzzer(
        command=["forge", "test", "--fuzz-runs", "10"]
    )
    result = fuzzer.fuzz("Target")
    assert captured["argv"] == ["forge", "test", "--fuzz-runs", "10"]
    assert result.outcome == FuzzOutcome.PASSED


def test_echidna(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv: list[str]) -> FakeProcess:
        assert argv[0] == "echidna"
        return FakeProcess(stdout="failed! counterexample found", returncode=1)

    _patch(monkeypatch, fake_run)
    fuzzer = fuzzing_service.EchidnaAdapter()
    result = fuzzer.fuzz("Target")
    assert result.outcome == FuzzOutcome.VIOLATED

    def fake_pass(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="passed", returncode=0)

    _patch(monkeypatch, fake_pass)
    result2 = fuzzing_service.EchidnaAdapter().fuzz("Target")
    assert result2.outcome == FuzzOutcome.PASSED


def test_medusa(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(argv: list[str]) -> FakeProcess:
        assert argv[0] == "medusa"
        return FakeProcess(stdout="no failures", returncode=0)

    _patch(monkeypatch, fake_run)
    fuzzer = fuzzing_service.MedusaAdapter()
    result = fuzzer.fuzz("Target")
    assert result.outcome == FuzzOutcome.PASSED

    def fake_fail(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="failed: broken invariant", returncode=1)

    _patch(monkeypatch, fake_fail)
    result2 = fuzzing_service.MedusaAdapter().fuzz("Target")
    assert result2.outcome == FuzzOutcome.VIOLATED


def test_linked_finding(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="FAIL", returncode=1)

    _patch(monkeypatch, fake_run)
    fuzzer = fuzzing_service.FoundryFuzzer()
    result = fuzzer.fuzz("Target", finding="reentrancy")
    assert result.linked_finding == "reentrancy"
    assert result.finding == "reentrancy"


def test_parse_functions() -> None:
    outcome, _detail, ce = fuzzing_service.parse_foundry_output(
        "FAIL\nCounterexample: y", "", 1
    )
    assert outcome == FuzzOutcome.VIOLATED
    assert ce is not None

    outcome2, _, _ = fuzzing_service.parse_echidna_output("all passed", "", 0)
    assert outcome2 == FuzzOutcome.PASSED

    outcome3, _, _ = fuzzing_service.parse_medusa_output("error", "", 2)
    assert outcome3 == FuzzOutcome.ERRORED


def test_target_name_and_string_kind(monkeypatch: pytest.MonkeyPatch) -> None:

    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="ok", returncode=0)

    _patch(monkeypatch, fake_run)
    target = Target.new("P", [], None, TargetMode.RESEARCH)
    fuzzer = fuzzing_service.FoundryFuzzer(kind="fuzz")
    result = fuzzer.fuzz(target)
    assert result.kind.value == "Fuzz"
    assert result.target == "P"


def test_parse_errored() -> None:
    outcome, _, _ = fuzzing_service.parse_foundry_output("", "", 2)
    assert outcome == FuzzOutcome.ERRORED
    outcome2, _, _ = fuzzing_service.parse_echidna_output("", "", 2)
    assert outcome2 == FuzzOutcome.ERRORED
    outcome3, _, _ = fuzzing_service.parse_medusa_output("", "", 2)
    assert outcome3 == FuzzOutcome.ERRORED


def test_command_list_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="ok", returncode=0)

    _patch(monkeypatch, fake_run)
    # str command
    fuzzer = fuzzing_service.FoundryFuzzer(command="forge test")
    assert fuzzer.fuzz("Target").outcome == FuzzOutcome.PASSED
    # unsupported command type falls back? returns None -> forge test default
    fuzzer2 = fuzzing_service.FoundryFuzzer(command=cast("str | None", 123))
    assert fuzzer2.fuzz("Target").outcome == FuzzOutcome.PASSED

    # echidna/medusa command override
    ech = fuzzing_service.EchidnaAdapter(command=["echidna", "x"])
    assert ech.fuzz("Target").outcome == FuzzOutcome.PASSED
    med = fuzzing_service.MedusaAdapter(command=["medusa", "fuzz"])
    assert med.fuzz("Target").outcome == FuzzOutcome.PASSED


def test_run_method_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="FAIL", returncode=1)

    _patch(monkeypatch, fake_run)
    fuzzer = fuzzing_service.FoundryFuzzer()
    # positional match_test
    result = fuzzer.fuzz("Target", "testFoo")
    assert result.outcome == FuzzOutcome.VIOLATED
    # linked finding
    result2 = fuzzer.fuzz("Target", finding="g")
    assert result2.linked_finding == "g"
    result3 = fuzzer.fuzz("Target")
    assert result3.skipped is False


def test_missing_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        raise FileNotFoundError("missing")

    _patch(monkeypatch, fake_run)
    assert fuzzing_service.EchidnaAdapter().fuzz("Target").skipped is True
    assert fuzzing_service.MedusaAdapter().fuzz("Target").skipped is True
