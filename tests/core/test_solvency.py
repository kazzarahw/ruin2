"""Tests for ERC-4626 solvency flag derivation."""

from ruin.core.solvency import SolvencyReport


def _report(balance: int, assets: int, shares: int) -> SolvencyReport:
    return SolvencyReport(
        vault="0xA",
        underlying="0xB",
        total_assets=assets,
        vault_balance=balance,
        total_shares=shares,
    )


def test_positive_delta_flags_inflation() -> None:
    report = _report(balance=150, assets=100, shares=10)
    assert report.delta == 50
    assert report.flags == ["inflation-exposed (vault balance exceeds totalAssets)"]


def test_empty_vault_with_assets_flags_genesis_window() -> None:
    report = _report(balance=100, assets=0, shares=0)
    assert report.flags == ["genesis-window (no shares issued yet, assets present)"]


def test_zero_balance_with_assets_flags_custody_elsewhere() -> None:
    report = _report(balance=0, assets=100, shares=10)
    assert report.flags == [
        "assets-not-custodied (reported assets, zero vault balance)"
    ]


def test_balanced_vault_has_no_flags() -> None:
    report = _report(balance=100, assets=100, shares=10)
    assert report.flags == []
