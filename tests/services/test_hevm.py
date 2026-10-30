"""Tests for the hevm symbolic adapter."""

from __future__ import annotations

from ruin.core.enums import SymbolicOutcome
from ruin.services.hevm import HevmAdapter, parse_hevm_output
from ruin.services.runners import run_symbolic


def test_parse_qed() -> None:
    outcome, detail, cex = parse_hevm_output("Qed", "", 0)
    assert outcome is SymbolicOutcome.PROVEN
    assert cex is None
    assert "proved" in detail


def test_parse_counterexample() -> None:
    outcome, _, cex = parse_hevm_output("counterexample found\nrevert at step 3", "", 0)
    assert outcome is SymbolicOutcome.UNDECIDED
    assert cex is not None


def test_parse_error() -> None:
    outcome, _, _ = parse_hevm_output("", "hevm: error parsing", 0)
    assert outcome is SymbolicOutcome.ERROR


def test_parse_no_verdict() -> None:
    outcome, _, _ = parse_hevm_output("some output", "", 0)
    assert outcome is SymbolicOutcome.UNDECIDED


def test_hevm_command_default() -> None:
    adapter = HevmAdapter()
    assert adapter._build_command("t") == ["hevm", "symbolic", "exec"]


def test_run_symbolic_dispatches_hevm() -> None:
    result = run_symbolic({"target": "T", "tool": "hevm", "outcome": "proven"})
    assert "- **Tool:** hevm" in result
    assert "- **Outcome:** Proven" in result


def test_run_symbolic_unknown_tool_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match="halmos"):
        run_symbolic({"target": "T", "tool": "zorp"})
