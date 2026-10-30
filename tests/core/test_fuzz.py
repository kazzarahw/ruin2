"""Tests for fuzz."""

from ruin.core.enums import FuzzKind, FuzzOutcome
from ruin.core.fuzz import Counterexample, FuzzResult, fuzz_result


def test_fuzz() -> None:
    result = fuzz_result("t", FuzzKind.INVARIANT, FuzzOutcome.VIOLATED).with_detail("d")
    assert "Fuzz" in result.render_markdown()


def test_fuzz_counterexample() -> None:
    ce = Counterexample(summary="x", raw="raw", trace=["a"])
    result = FuzzResult(
        target="t",
        kind=FuzzKind.FUZZ,
        outcome=FuzzOutcome.VIOLATED,
        counterexample=ce,
        finding="f1",
    )
    assert result.counter_example is ce
    assert result.counterexamples == [ce]
    assert result.linked_finding == "f1"
    md = result.render_markdown()
    assert "- **Counterexample:** x" in md
    assert "- **Linked finding:** f1" in md


def test_fuzz_with_methods() -> None:
    result = fuzz_result("t", FuzzKind.INVARIANT, FuzzOutcome.PASSED).with_detail("d")
    ce = Counterexample(summary="c")
    result.with_counterexample(ce).with_finding("finding")
    assert result.counterexample is ce
    assert result.finding == "finding"
    assert result.skipped is False
