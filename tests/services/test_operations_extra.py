"""Extra operations tests."""

from pathlib import Path

from ruin.services.operations import run_operation


def test_operations(tmp_path: Path) -> None:
    source = tmp_path / "s.sol"
    source.write_text("contract X {}", encoding="utf-8")
    assert "source" in run_operation("review", {"source": str(source)})

    code = tmp_path / "code.txt"
    code.write_text("0x6001", encoding="utf-8")
    assert "selectors" in run_operation("selectors", {"target": str(code)})

    text = run_operation("research", {"mechanism": "m", "summary": "s"})
    assert "Research Card" in text

    text = run_operation(
        "rng-hack", {"mechanism": "m", "summary": "s", "source": "block.timestamp"}
    )
    assert "RNG-Hack" in text

    text = run_operation("fuzz", {"target": "t"})
    assert "Fuzz" in text

    text = run_operation("trust", {"name": "P"})
    assert "Trust Model" in text

    text = run_operation("screen", {"name": "P", "chain": "Ethereum"})
    assert "Target Screen" in text

    text = run_operation("pipeline-status", {"name": "P"})
    assert "Pipeline" in text

    text = run_operation("bundle", {"name": "P"})
    assert "Report Bundle" in text

    text = run_operation("triage", {"name": "P", "check": ["weak-prng"]})
    assert "Vuln Triage" in text
