"""Target selection scoring for ``ruin``."""

from __future__ import annotations

from ruin.core.protocols import ProtocolSummary, RankedTarget


def score(summary: ProtocolSummary) -> int:
    """Return the selection score for a protocol summary."""
    return summary.tvl_usd


def rank_targets(summaries: list[ProtocolSummary], limit: int) -> list[RankedTarget]:
    """Rank protocols by value-at-stake, breadth, then name."""
    scored: list[tuple[int, int, str, ProtocolSummary]] = []
    for summary in summaries:
        scored.append(
            (score(summary), len(summary.chains), summary.name.as_str(), summary)
        )
    scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
    result: list[RankedTarget] = []
    for sc, _chains, _name, summary in scored[:limit]:
        result.append(RankedTarget(summary=summary, score=sc))
    return result


def filter_cex(summaries: list[ProtocolSummary]) -> list[ProtocolSummary]:
    """Drop centralized-exchange entries."""
    return [s for s in summaries if s.category != "CEX"]


def filter_chains(
    summaries: list[ProtocolSummary], chains: list[str]
) -> list[ProtocolSummary]:
    """Keep only protocols listed on any of the given chains, case-insensitively."""
    wanted = {c.lower() for c in chains}
    return [s for s in summaries if any(c.lower() in wanted for c in s.chains)]


def exclude_chains(
    summaries: list[ProtocolSummary], chains: list[str]
) -> list[ProtocolSummary]:
    """Drop protocols listed on any of the given chains, case-insensitively."""
    dropped = {c.lower() for c in chains}
    return [s for s in summaries if not any(c.lower() in dropped for c in s.chains)]
