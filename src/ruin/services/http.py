"""HTTP helpers for ``ruin``."""

from __future__ import annotations

from typing import cast
from urllib.parse import quote

import httpx

from ruin.core.probe import COMMON_SELECTORS
from ruin.core.protocols import ProtocolSummary, parse_protocols
from ruin.core.scoring import exclude_chains, filter_cex, filter_chains, rank_targets
from ruin.core.screen import screen_from_protocol
from ruin.services.rpc import request_with_retry

_HTTP_OK = 200


def fetch_protocols() -> list[ProtocolSummary]:
    """Fetch the DefiLlama protocols list."""
    response = request_with_retry("GET", "https://api.llama.fi/protocols")
    return parse_protocols(response.text)


def fetch_protocol(slug: str) -> str:
    """Fetch a DefiLlama protocol document as raw JSON."""
    if not slug or any(c.isspace() for c in slug):
        raise ValueError("slug must not be blank or contain whitespace")
    response = request_with_retry(
        "GET", f"https://api.llama.fi/protocol/{quote(slug, safe='')}"
    )
    return response.text


def filtered_summaries(include: list[str], exclude: list[str]) -> list[ProtocolSummary]:
    """Fetch DefiLlama protocols, drop CEX entries, apply the chain filters."""
    summaries = filter_cex(fetch_protocols())
    if include:
        summaries = filter_chains(summaries, include)
    if exclude:
        summaries = exclude_chains(summaries, exclude)
    return summaries


def ranked_text(
    limit: int, include: list[str], exclude: list[str], screen_slug: str | None
) -> str:
    """Build ranked target text, optionally screening a slug."""
    summaries = filtered_summaries(include, exclude)
    ranked = rank_targets(summaries, limit)
    lines: list[str] = [f"top {len(ranked)} targets by value-at-stake:"]
    for item in ranked:
        lines.append(
            f"  {item.summary.name.as_str():<24} ${item.score:>13}  "
            f"{len(item.summary.chains)} chain(s)  slug={item.summary.slug}"
        )
    if screen_slug is not None:
        for proto in summaries:
            if proto.slug == screen_slug:
                return screen_from_protocol(proto).render_markdown()
        return f"screen: slug `{screen_slug}` not in DefiLlama feed"
    return "\n".join(lines)


def coin_meta(chain_slug: str, token: str) -> dict[str, object]:
    """Fetch {price, decimals} for a token from DefiLlama coins, best effort."""
    url = f"https://coins.llama.fi/prices/current/{chain_slug}:{token}"
    try:
        response = request_with_retry("GET", url)
        doc = response.json()
    except (httpx.HTTPError, ValueError):
        return {}
    coins = doc.get("coins") if isinstance(doc, dict) else None
    if not isinstance(coins, dict):
        return {}
    key = f"{chain_slug}:{token.lower()}"
    entry = coins.get(key) or coins.get(f"{chain_slug}:{token}")
    if isinstance(entry, dict):
        return cast("dict[str, object]", entry)
    return {}


def resolve_selectors(selectors: list[str]) -> dict[str, str]:
    """Resolve 4-byte selectors via 4byte.directory.

    Args:
        selectors: List of hex selector strings (without 0x prefix).

    Returns:
        Mapping of selector to resolved signature (or empty string if unknown).
    """
    resolved: dict[str, str] = {}
    for sel in selectors:
        url = f"https://www.4byte.directory/api/v1/signatures/?hex_signature=0x{sel}"
        try:
            response = httpx.get(url, timeout=10.0)
            if response.status_code == _HTTP_OK:
                data = response.json()
                results = data.get("results", [])
                if results:
                    resolved[sel] = results[0].get("text_signature", "")
                else:
                    resolved[sel] = ""
            else:
                resolved[sel] = ""
        except (httpx.HTTPError, ValueError, KeyError):
            resolved[sel] = ""
    _apply_canonical(resolved)
    return resolved


def _apply_canonical(resolved: dict[str, str]) -> None:
    """Override 4byte first-match junk with canonical names we ship."""
    for selector, signature in COMMON_SELECTORS.items():
        key = selector.removeprefix("0x")
        if key in resolved:
            resolved[key] = signature
