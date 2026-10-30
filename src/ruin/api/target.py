"""Target-selection namespace: value at stake, exposure, and trust posture."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.api._call import JsonPayload, call

if TYPE_CHECKING:
    from ruin.api._requests import HuntRequest, ScreenRequest


async def rank(
    limit: int = 10,
    chains: list[str] | None = None,
    exclude: list[str] | None = None,
    screen: str | None = None,
) -> JsonPayload | str:
    """Rank protocols by value at stake (CLI ``ruin target rank``)."""
    return await call(
        "rank",
        {
            "limit": limit,
            "chain": chains or [],
            "exclude_chain": exclude or [],
            "screen": screen,
        },
    )


async def map_(slug: str, asset: str) -> JsonPayload | str:
    """Map a protocol slug to its deployed asset (CLI ``ruin target map``)."""
    return await call("map", {"slug": slug, "asset": asset})


async def screen(req: ScreenRequest) -> JsonPayload | str:
    """Screen one target for bespoke/custodial risk (CLI ``ruin target screen``)."""
    return await call(
        "screen",
        {
            "name": req.name,
            "chain": req.chain,
            "tvl": req.tvl,
            "source": req.source,
            "bespoke": req.bespoke,
            "custodial": req.custodial,
            "listed": req.listed,
        },
    )


async def trust(
    name: str, assume: list[tuple[str, str, str]] | None = None, custodial: bool = False
) -> JsonPayload | str:
    """Record the trust model for a target (CLI ``ruin target trust``)."""
    return await call(
        "trust",
        {
            "name": name,
            "custodial": custodial,
            "assume": [list(item) for item in assume or []],
        },
    )


async def hunt(req: HuntRequest) -> JsonPayload | str:
    """Hunt funded holders for contract candidates (CLI ``target hunt``)."""
    return await call(
        "hunt",
        {
            "token": req.token,
            "rpc": req.rpc,
            "chain": req.chain,
            "also": list(req.also),
            "blocks": req.blocks,
            "from_block": req.from_block,
            "to_block": req.to_block,
            "min_usd": req.min_usd,
            "limit": req.limit,
        },
    )


async def bundle(
    name: str, with_screen: bool = False, with_pipeline: bool = False
) -> JsonPayload | str:
    """Assemble the report bundle for a target (CLI ``ruin target bundle``)."""
    return await call(
        "bundle",
        {"name": name, "screen": with_screen, "pipeline": with_pipeline},
    )


__all__: list[str] = ["bundle", "hunt", "map_", "rank", "screen", "trust"]
