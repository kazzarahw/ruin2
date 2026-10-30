"""Tests for the fuzz operation's runner mode (``run``)."""

import pytest

from ruin.services import fuzzing as fuzzing_service
from ruin.services import operations as ops
from ruin.services.operations import run_operation_json


class FakeProcess:
    def __init__(self, stdout: str = "ok", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


RUN = {"run": True}


def test_fuzz_run_operation(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="FAIL", returncode=1)

    monkeypatch.setattr(fuzzing_service, "run_command", fake_run)
    text = ops.run_operation("fuzz", {"target": "t", "match_test": "testFoo", **RUN})
    assert "Fuzz" in text


def test_fuzz_record_is_default(monkeypatch: pytest.MonkeyPatch) -> None:
    text = ops.run_operation("fuzz", {"target": "t"})
    assert "# Fuzz" in text


def test_fuzz_run_invalid_tool() -> None:
    try:
        ops.run_operation("fuzz", {"target": "t", "tool": "nope", **RUN})
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_fuzz_run_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess(stdout="FAIL", returncode=1)

    monkeypatch.setattr(fuzzing_service, "run_command", fake_run)
    text = ops.run_operation(
        "fuzz",
        {
            "target": "t",
            "tool": "echidna",
            "tool_command": "echidna t",
            "kind": "fuzz",
            **RUN,
        },
    )
    assert "Fuzz" in text
    text2 = ops.run_operation(
        "fuzz",
        {"target": "t", "tool": "medusa", "kind": "invariant", **RUN},
    )
    assert "Fuzz" in text2


def test_fuzz_run_invalid_kind() -> None:
    try:
        ops.run_operation("fuzz", {"target": "t", "kind": "bad", **RUN})
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_fuzz_run_has_no_json_payload() -> None:
    with pytest.raises(ValueError, match="no structured output"):
        run_operation_json("fuzz", {"target": "t", "run": True})
