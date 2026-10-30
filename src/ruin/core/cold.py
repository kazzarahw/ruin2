"""Cold-target selection: low scrutiny times funds at risk (pure).

The bug-bounty crowd and the SAST swarm concentrate on famous, verified
protocols. Cold selection inverts that bias: it ranks by the ABSENCE of
scrutiny (unverified source, no audit trail, young age) scaled by
meaningful funds at risk. Every threshold is a parameter so selection
policy can be tuned without touching code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

MIN_TVL_USD = 50_000.0
MID_TVL_USD = 200_000.0
SWEET_MAX_TVL_USD = 5_000_000.0
LARGE_TVL_USD = 50_000_000.0
NEW_DAYS = 180
SETTLED_DAYS = 730

UNVERIFIED_WEIGHT = 5
NO_AUDIT_WEIGHT = 3
NEW_AGE_WEIGHT = 2
MIDDLE_AGE_WEIGHT = 1
SWEET_FUNDS_WEIGHT = 3
MID_FUNDS_WEIGHT = 2
LARGE_FUNDS_WEIGHT = 1

UNKNOWN_AGE_DAYS = -1
FAME_SCRUTINY_CAP = 3


@dataclass(frozen=True)
class ColdThresholds:
    """Tunable dollar/day boundaries for cold scoring."""

    min_tvl_usd: float = MIN_TVL_USD
    fame_tvl_usd: float = 100_000_000.0
    mid_tvl_usd: float = MID_TVL_USD
    sweet_max_tvl_usd: float = SWEET_MAX_TVL_USD
    large_tvl_usd: float = LARGE_TVL_USD
    new_days: int = NEW_DAYS
    settled_days: int = SETTLED_DAYS


DEFAULT_THRESHOLDS = ColdThresholds()


@dataclass(frozen=True)
class ColdSignals:
    """Low-scrutiny evidence observed for one protocol or contract.

    ``age_days`` is ``UNKNOWN_AGE_DAYS`` when the listing date is unknown;
    unknown age scores neutral, never as a brand-new launch.
    ``chain_supported`` is False when the verification probe cannot see the
    chain (multichain listings, non-Sourcify chains): unverified then means
    nothing and scores neutral, not cold.
    """

    verified: bool = False
    chain_supported: bool = True
    audited: bool = False
    live_contest: bool = False
    age_days: int = UNKNOWN_AGE_DAYS


@dataclass(frozen=True)
class ColdCandidate:
    """One cold-selection candidate with its observed signals."""

    name: str
    chain: str
    tvl_usd: int
    address: str
    signals: ColdSignals = field(default_factory=ColdSignals)


def funds_weight(tvl_usd: int, thresholds: ColdThresholds = DEFAULT_THRESHOLDS) -> int:
    """Scale funds at risk: below the floor scores zero, battlestars fade."""
    if tvl_usd < thresholds.min_tvl_usd:
        return 0
    if tvl_usd < thresholds.sweet_max_tvl_usd:
        return SWEET_FUNDS_WEIGHT
    if tvl_usd < thresholds.large_tvl_usd:
        return MID_FUNDS_WEIGHT
    return LARGE_FUNDS_WEIGHT


def scrutiny_weight(
    signals: ColdSignals,
    tvl_usd: float = 0.0,
    thresholds: ColdThresholds = DEFAULT_THRESHOLDS,
) -> int:
    """Score the absence of scrutiny; a live paid contest is disqualifying.

    Protocols at or above ``fame_tvl_usd`` keep only a capped weight: money
    that size has been audited and SAST-swarmed regardless of what a
    keyless verification probe says.
    """
    if signals.live_contest:
        return 0
    weight = 0
    if not signals.verified and signals.chain_supported:
        weight += UNVERIFIED_WEIGHT
    if not signals.audited:
        weight += NO_AUDIT_WEIGHT
    if signals.age_days >= 0:
        if signals.age_days < thresholds.new_days:
            weight += NEW_AGE_WEIGHT
        elif signals.age_days < thresholds.settled_days:
            weight += MIDDLE_AGE_WEIGHT
    if tvl_usd >= thresholds.fame_tvl_usd:
        weight = min(weight, FAME_SCRUTINY_CAP)
    return weight


def cold_score(
    candidate: ColdCandidate, thresholds: ColdThresholds = DEFAULT_THRESHOLDS
) -> int:
    """Return the cold-selection score: scrutiny absence times funds weight."""
    return scrutiny_weight(
        candidate.signals, candidate.tvl_usd, thresholds
    ) * funds_weight(candidate.tvl_usd, thresholds)


def tier_for(tvl_usd: int, thresholds: ColdThresholds = DEFAULT_THRESHOLDS) -> str:
    """Name the funds tier: below floor, mid (under-covered), or high."""
    if tvl_usd < thresholds.min_tvl_usd:
        return "below"
    if tvl_usd < thresholds.mid_tvl_usd:
        return "mid"
    return "high"


def rank_cold(
    candidates: Sequence[ColdCandidate],
    limit: int,
    thresholds: ColdThresholds = DEFAULT_THRESHOLDS,
) -> list[ColdCandidate]:
    """Rank cold candidates by score, then TVL, then name; drop zero scores."""
    scored = [(cold_score(c, thresholds), c) for c in candidates]
    kept = [pair for pair in scored if pair[0] > 0]
    kept.sort(key=lambda pair: (-pair[0], -pair[1].tvl_usd, pair[1].name.lower()))
    return [candidate for _score, candidate in kept[:limit]]


def render_cold_markdown(
    candidates: Sequence[ColdCandidate],
    thresholds: ColdThresholds = DEFAULT_THRESHOLDS,
) -> str:
    """Render ranked cold candidates as a markdown table."""
    lines = [
        "# Cold targets — low scrutiny x funds at risk",
        "",
        "| name | chain | tvl | tier | score | verified | audited | contest | age |",
        "|---|---|---:|---|---:|---|---|---|---:|",
    ]
    for candidate in candidates:
        lines.append(
            f"| {candidate.name} | {candidate.chain} | {candidate.tvl_usd:,} "
            f"| {tier_for(candidate.tvl_usd, thresholds)} "
            f"| {cold_score(candidate, thresholds)} "
            f"| {candidate.signals.verified} | {candidate.signals.audited} "
            f"| {candidate.signals.live_contest} | {candidate.signals.age_days} |"
        )
    if not candidates:
        lines.append("| (none) |  | 0 | below | 0 | false | false | false | -1 |")
    return "\n".join(lines)


__all__: list[str] = [
    "DEFAULT_THRESHOLDS",
    "UNKNOWN_AGE_DAYS",
    "ColdCandidate",
    "ColdSignals",
    "ColdThresholds",
    "cold_score",
    "rank_cold",
    "render_cold_markdown",
    "scrutiny_weight",
    "tier_for",
]
