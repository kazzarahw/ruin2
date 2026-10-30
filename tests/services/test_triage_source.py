"""Tests for triage with a source file and for the merged mode dispatch."""

from pathlib import Path

import pytest

from ruin.services.operations import run_operation

_VAULT = """
function convertToShares(uint256 assets) public view returns (uint256) {
    return (assets * totalSupply) / totalAssets();
}
function totalAssets() public view returns (uint256) {
    return asset.balanceOf(address(this));
}
"""

_SLITHER_NEW_FORMAT = (
    '[{"klass": "Reentrancy", "severity": "Medium", "summary": "re-entrancy"}]'
)


def test_triage_source_lists_smell_lead(tmp_path: Path) -> None:
    src = tmp_path / "Vault.sol"
    src.write_text(_VAULT, encoding="utf-8")
    out = run_operation("triage", {"name": "P", "source": str(src)})
    assert "erc4626-inflation-exposed" in out
    assert "## Leads" in out


def test_triage_merges_slither_and_source(tmp_path: Path) -> None:
    src = tmp_path / "Vault.sol"
    src.write_text(_VAULT, encoding="utf-8")
    doc = tmp_path / "slither.json"
    doc.write_text(_SLITHER_NEW_FORMAT, encoding="utf-8")
    out = run_operation(
        "triage",
        {"name": "P", "source": str(src), "file": str(doc)},
    )
    assert "reentrancy" in out
    assert "erc4626-inflation-exposed" in out


def test_triage_source_mode_uses_only_source(tmp_path: Path) -> None:
    src = tmp_path / "Vault.sol"
    src.write_text(_VAULT, encoding="utf-8")
    out = run_operation("triage", {"name": "P", "mode": "source", "source": str(src)})
    assert "erc4626-inflation-exposed" in out


def test_triage_source_mode_requires_source(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source file"):
        run_operation("triage", {"name": "P", "mode": "source"})


def test_triage_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="mode must be"):
        run_operation("triage", {"name": "P", "mode": "vibes"})


def test_triage_checks_mode_writes_out(tmp_path: Path) -> None:
    report = tmp_path / "triage.md"
    out = run_operation(
        "triage", {"name": "P", "check": ["weak-prng"], "out": str(report)}
    )
    assert out == f"wrote {report}"
    assert "weak-prng" in report.read_text(encoding="utf-8")
