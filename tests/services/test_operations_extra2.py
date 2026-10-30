"""More operations tests."""

from pathlib import Path
from typing import Any, cast

import pytest

from ruin.core.forensics import TransactionTrace
from ruin.services import analyzers as analyzer_service
from ruin.services import operations as ops


def test_map_with_out(tmp_path: Path) -> None:
    cast("Any", ops).fetch_protocol = lambda _slug: (
        '{"name": "A", "address": "0x' + "1" * 40 + '"}'
    )
    out = tmp_path / "out.json"
    result = ops.run_operation(
        "map", {"slug": "a", "asset": "0x" + "2" * 40, "out": str(out)}
    )
    assert result == ""
    assert out.exists()


def test_review_with_out(tmp_path: Path) -> None:
    source = tmp_path / "s.sol"
    source.write_text("contract X {}", encoding="utf-8")
    out = tmp_path / "review.json"
    result = ops.run_operation("review", {"source": str(source), "out": str(out)})
    assert "wrote" in result
    assert out.exists()


def test_rng_hack_list_summary() -> None:
    result = ops.run_operation(
        "rng-hack",
        {"mechanism": "m", "summary": ["a", "b"], "source": "block.timestamp"},
    )
    assert "a b" in result


def test_research_list_summary() -> None:
    result = ops.run_operation("research", {"mechanism": "m", "summary": ["a", "b"]})
    assert "a b" in result


def test_fuzz_invalid() -> None:
    with pytest.raises(ValueError, match=r".*"):
        ops.run_operation("fuzz", {"target": "t", "kind": "bad"})


def test_pipeline_status_invalid() -> None:
    with pytest.raises(ValueError, match=r".*"):
        ops.run_operation(
            "pipeline-status", {"name": "P", "stage": [["bad", "done", "n"]]}
        )


def test_analyze_operation() -> None:
    cast("Any", analyzer_service.SlitherAnalyzer).analyze = lambda _self, _target: []
    cast("Any", analyzer_service.SemgrepAnalyzer).analyze = lambda _self, _target: []
    result = ops.run_operation("analyze", {"source": "x.sol"})
    assert result == ""


def test_trace_operation(monkeypatch: pytest.MonkeyPatch) -> None:
    from ruin.services import operations_ext as ext

    monkeypatch.setattr(
        ext.forensics_svc,
        "trace_transaction",
        lambda _tx, _rpc: TransactionTrace(tx_hash="0xabc", steps=["step"]),
    )
    result = ops.run_operation("trace", {"tx": "0xabc", "rpc": "http://x"})
    assert "Trace" in result
