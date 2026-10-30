"""Pure constant-product depth model for the thin-collateral screen."""

from __future__ import annotations

import math
from dataclasses import dataclass

_TARGET_NUM = 11
_TARGET_DEN = 10
MAX_DECIMALS = 36


def depth_model(reserves0: int, reserves1: int, decimals0: int, decimals1: int) -> int:
    """Smallest raw token1 buy that lifts the pool spot price by ten percent.

    On a constant-product pool (``x*y=k``) the spot price of token1 quoted
    in token0 is ``reserves0 / reserves1``. Buying ``q`` raw units of token1
    moves that price by the factor ``(reserves1 / (reserves1 - q)) ** 2``,
    so the ten-percent bar is cleared exactly when
    ``10 * reserves1**2 >= 11 * (reserves1 - q) ** 2``.
    Solving with an integer square root yields the closed form below: the
    returned amount always clears the bar and one unit less never does.
    The buy side is the cheaper direction (selling needs ~16% more), so
    this figure doubles as the tightest "moves price 10% either way" depth.
    Decimals cancel out of the price ratio; they are validated so garbage
    from a misread ``decimals()`` never flows downstream.

    Args:
        reserves0: Raw reserve of token0 (the quote side).
        reserves1: Raw reserve of token1 (the side being bought).
        decimals0: Decimals of token0, used for input validation only.
        decimals1: Decimals of token1, used for input validation only.

    Returns:
        Raw units of token1 whose purchase lifts the spot price >= 10%.

    Raises:
        ValueError: If a reserve is negative or decimals fall outside 0..36.
    """
    if reserves0 < 0 or reserves1 < 0:
        raise ValueError("reserves must be non-negative")
    if not 0 <= decimals0 <= MAX_DECIMALS or not 0 <= decimals1 <= MAX_DECIMALS:
        raise ValueError("decimals must be within 0..36")
    cap = reserves1 * reserves1 * _TARGET_DEN // _TARGET_NUM
    return reserves1 - math.isqrt(cap)


@dataclass(frozen=True)
class ScreenParams:
    """Operator-chosen knobs for one thin-collateral screen.

    Attributes:
        price_usd: USD price of one whole TOKEN (required input; the screen
            deliberately avoids price-oracle plumbing).
        blocks: PairCreated scan window in blocks, clamped to the chain head.
        min_usd: pools whose whole-token depth is worth less than this are
            dropped from the combined depth (dust pools are not exit liquidity).
    """

    price_usd: float
    blocks: int
    min_usd: float


@dataclass(frozen=True)
class PoolDepth:
    """One usable pool with its measured buy-depth."""

    pair: str
    depth_raw: int
    depth_usd: float


@dataclass(frozen=True)
class ThinCollateralReport:
    """Thin-collateral screen: market exposure versus combined DEX depth."""

    token: str
    market: str
    factory: str
    price_usd: float
    min_usd: float
    decimals: int
    from_block: int
    to_block: int
    blocks: int
    pairs_found: int
    pools: tuple[PoolDepth, ...] = ()
    depth_raw: int = 0
    depth_usd: float = 0.0
    market_raw: int = 0
    market_usd: float = 0.0
    verdict: str = "clean"
    signals: tuple[str, ...] = ()

    def render_markdown(self) -> str:
        """Render the screen verdict exactly as the CLI text output does."""
        lines: list[str] = [
            f"# Thin collateral — {self.token} at market {self.market}",
            "",
            f"- verdict: {self.verdict}",
            f"- exit depth usd: {self.depth_usd}",
            f"- market usd: {self.market_usd}",
            f"- pools counted: {len(self.pools)}",
        ]
        if self.signals:
            lines.append("- signals: " + ", ".join(self.signals))
        return "\n".join(lines)
