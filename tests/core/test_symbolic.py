"""Tests for symbolic core."""

from ruin.core.enums import SymbolicOutcome
from ruin.core.fuzz import Counterexample
from ruin.core.symbolic import SymbolicResult, symbolic_result


def test_symbolic_result_render() -> None:
    result = symbolic_result("t", "halmos", SymbolicOutcome.PROVEN).with_detail("d")
    assert "Symbolic" in result.render_markdown()
    assert result.tool == "halmos"


def test_symbolic_counterexample_and_links() -> None:
    ce = Counterexample(summary="x", raw="raw", trace=["a"])
    result = SymbolicResult(
        target="t",
        tool="mythril",
        outcome=SymbolicOutcome.UNDECIDED,
        counterexample=ce,
        finding="f1",
    )
    assert result.counter_example is ce
    assert result.counterexamples == [ce]
    assert result.linked_finding == "f1"
    md = result.render_markdown()
    assert "- **Counterexample:** x" in md
    assert "- **Linked finding:** f1" in md


def test_symbolic_with_methods() -> None:
    result = symbolic_result("t", "halmos", SymbolicOutcome.PROVEN).with_detail("d")
    ce = Counterexample(summary="c")
    result.with_counterexample(ce).with_finding("finding")
    assert result.counterexample is ce
    assert result.finding == "finding"
    assert result.skipped is False
