"""ERC-4626 share/asset accounting checks from on-chain numbers."""

from __future__ import annotations

from dataclasses import dataclass

_STALE_KEEP_RATIO = 1.1
_DRAIN_DROP_RATIO = 0.5
_STALE_RATE_FLAG = "stale-rate-cache-drain-first"

_INFLATION_FLAG = "inflation-exposed (vault balance exceeds totalAssets)"
_GENESIS_FLAG = "genesis-window (no shares issued yet, assets present)"
_CUSTODY_FLAG = "assets-not-custodied (reported assets, zero vault balance)"


@dataclass(frozen=True)
class SolvencyReport:
    """Snapshot of a vault's on-chain asset and share accounting."""

    vault: str
    underlying: str
    total_assets: int
    vault_balance: int
    total_shares: int

    @property
    def delta(self) -> int:
        """Underlying held by the vault minus the assets it reports."""
        return self.vault_balance - self.total_assets

    @property
    def flags(self) -> list[str]:
        """Bug-class flags derived from the accounting snapshot."""
        out: list[str] = []
        if self.total_shares == 0 and self.vault_balance > 0:
            out.append(_GENESIS_FLAG)
        elif self.delta > 0:
            out.append(_INFLATION_FLAG)
        if self.total_assets > 0 and self.vault_balance == 0:
            out.append(_CUSTODY_FLAG)
        return out

    def render_markdown(self) -> str:
        """Render the report as markdown for CLI output."""
        lines = [
            f"# Solvency — {self.vault}",
            "",
            f"- underlying: {self.underlying}",
            f"- totalAssets: {self.total_assets}",
            f"- vault balance: {self.vault_balance}",
            f"- totalSupply(shares): {self.total_shares}",
            f"- delta: {self.delta}",
            f"- flags: {', '.join(self.flags) if self.flags else 'none'}",
        ]
        return "\n".join(lines)


def stale_rate_flag(assets: int, before: int, ta_after: int, quote: int) -> str | None:
    """Flag cached-rate drift after a first-deposit-style drain.

    A drain that empties the vault's asset balance must move both totalAssets
    and the deposit quote. When totalAssets follows the balance but
    previewDeposit keeps quoting the old rate, shares are still mintable at
    pre-drain prices -- the yETH-shaped stale-rate-cache bug.

    Args:
        assets: totalAssets before the drain.
        before: previewDeposit quote before the drain.
        ta_after: totalAssets after zeroing the vault balance slot.
        quote: previewDeposit quote after the drain.

    Returns:
        The flag string, or None when the quote followed the drain.
    """
    balance_driven = ta_after < assets * _DRAIN_DROP_RATIO
    if balance_driven and before > 0 and quote <= before * _STALE_KEEP_RATIO:
        return _STALE_RATE_FLAG
    return None
