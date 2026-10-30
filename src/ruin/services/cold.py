"""Cold-target discovery fetcher: DefiLlama feed plus keyless Sourcify status.

``verified`` here means "Sourcify found the source"; without an Etherscan
key, explorer-only verification stays invisible, so treat misses as a
strong-but-not-proof signal. The audit signal is the DefiLlama audit count,
which is a trail hint, not a verdict; contest status comes from research.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from ruin.core.chains import LLAMA_CHAIN_IDS
from ruin.core.cold import (
    DEFAULT_THRESHOLDS,
    UNKNOWN_AGE_DAYS,
    ColdCandidate,
    ColdSignals,
    rank_cold,
)
from ruin.core.scoring import filter_cex, filter_chains
from ruin.services.http import fetch_protocols
from ruin.services.rpc import SHARED_TRANSPORT
from ruin.services.sources import fetch_source

if TYPE_CHECKING:
    from ruin.core.cold import ColdThresholds
    from ruin.core.protocols import ProtocolSummary
    from ruin.services.rpc import RpcTransport

_SECONDS_PER_DAY = 86_400


def _age_days(listed_unix: int, now: int) -> int:
    """Listing age in whole days, or ``UNKNOWN_AGE_DAYS`` when unlisted."""
    if listed_unix <= 0:
        return UNKNOWN_AGE_DAYS
    return max(0, (now - listed_unix) // _SECONDS_PER_DAY)


def _signals(summary: ProtocolSummary, transport: RpcTransport) -> ColdSignals:
    """Probe one summary: Sourcify status, audit-trail count, listing age."""
    chain_id = LLAMA_CHAIN_IDS.get(summary.chain_of_interest().lower(), 0)
    verified = False
    if chain_id and summary.address:
        verified = fetch_source(
            summary.address, chain_id=chain_id, transport=transport
        ).verified
    return ColdSignals(
        chain_supported=chain_id != 0,
        verified=verified,
        audited=summary.audits > 0,
        live_contest=False,
        age_days=_age_days(summary.listed_unix, int(time.time())),
    )


def _probe_set(pool: list[ProtocolSummary], limit: int) -> list[ProtocolSummary]:
    """Probe the cold band: youngest listings plus smallest above floor.

    Probing the biggest TVL would just re-discover the famous protocols
    that ``rank`` already covers.
    """
    youngest = sorted(
        (s for s in pool if s.listed_unix > 0),
        key=lambda s: -s.listed_unix,
    )[: max(1, limit // 2)]
    seen = {s.name.as_str() for s in youngest}
    rest = [s for s in pool if s.name.as_str() not in seen]
    smallest = sorted(rest, key=lambda s: s.tvl_usd)[: max(0, limit - len(youngest))]
    return youngest + smallest


def _candidate(summary: ProtocolSummary, transport: RpcTransport) -> ColdCandidate:
    """Turn one protocol summary into a cold candidate with probed signals."""
    return ColdCandidate(
        name=summary.name.as_str(),
        chain=summary.chain_of_interest(),
        tvl_usd=summary.tvl_usd,
        address=summary.address,
        signals=_signals(summary, transport),
    )


def cold_candidates(
    limit: int = 10,
    chains: list[str] | None = None,
    thresholds: ColdThresholds = DEFAULT_THRESHOLDS,
    transport: RpcTransport | None = None,
) -> list[ColdCandidate]:
    """Fetch the feed, probe the coldest-looking pool, and rank it cold.

    Args:
        limit: Maximum candidates to probe and return.
        chains: Optional chain names to keep (case-insensitive).
        thresholds: Scoring thresholds; ``min_tvl_usd`` is the funds floor.
        transport: Optional transport, injectable for tests.

    Returns:
        Cold-ranked candidates above the funds floor, best first.
    """
    summaries = filter_cex(fetch_protocols())
    if chains:
        summaries = filter_chains(summaries, chains)
    pool = [
        summary
        for summary in summaries
        if summary.tvl_usd >= thresholds.min_tvl_usd and summary.address
    ]
    active = transport or SHARED_TRANSPORT
    built = [_candidate(summary, active) for summary in _probe_set(pool, limit)]
    return rank_cold(built, limit, thresholds)
