"""Pure discovery-hunt helpers: token-class filtering and candidate ranking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from ruin.core.probe import extract_selectors
from ruin.core.templates import template_family

ERC20_CORE = frozenset(
    {
        "0xa9059cbb",  # transfer(address,uint256)
        "0x70a08231",  # balanceOf(address)
        "0x23b872dd",  # transferFrom(address,address,uint256)
        "0x095ea7b3",  # approve(address,uint256)
    }
)
OWNER_SELECTOR = "0x8da5cb5b"
MINT_SELECTORS = frozenset({"0x40c10f19", "0xa0712d68", "0x1249c58b", "0x0f4e1890"})


@dataclass(frozen=True)
class Candidate:
    """A funded contract that looks like an owner-controlled ERC20 token."""

    address: str
    usd: float
    mintable: bool
    ownered: bool
    verified: bool = False
    family: str = ""


def candidate(address: str, usd: float, code: str) -> Candidate | None:
    """Build a token-class candidate, or None when the code is not one."""
    selectors = set(extract_selectors(code))
    if not selectors >= ERC20_CORE:
        return None
    mintable = bool(selectors & MINT_SELECTORS)
    ownered = OWNER_SELECTOR in selectors
    if not (mintable or ownered):
        return None
    return Candidate(
        address=address,
        usd=usd,
        mintable=mintable,
        ownered=ownered,
        family=template_family(code),
    )


def rank(cands: list[Candidate], limit: int) -> list[Candidate]:
    """Rank candidates: mintable first, then by received USD."""
    ordered = sorted(cands, key=lambda c: (not c.mintable, -c.usd))
    return ordered[:limit]


def render_hunt_markdown(
    token: str,
    cands: list[Candidate],
    blocks: int,
    failed: int = 0,
    total: int = 0,
) -> str:
    """Render hunt results as a markdown candidate table.

    ``failed``/``total`` report how many log windows the RPC rejected so a
    thin result set is not mistaken for a clean chain.
    """
    lines = [
        f"# Hunt — recipients of {token} over {blocks} blocks",
        "",
        "| address | usd | mintable | ownered | verified | family |",
        "|---|---:|---|---|---|---|",
    ]
    for c in cands:
        lines.append(
            f"| {c.address} | {c.usd:,.0f} | {c.mintable} "
            f"| {c.ownered} | {c.verified} | {c.family} |"
        )
    if not cands:
        lines.append("| (none) | 0 | false | false | false |")
    lines.append("")
    if failed:
        lines.append("")
        lines.append(
            f"> WARNING: {failed} of {total} log windows failed "
            "(RPC caps/errors) — recipient counts below are floors."
        )
    lines.append(
        "> Probe leads with `ruin honeypot-evm ADDRESS --rpc URL` "
        "and `ruin selectors ADDRESS --rpc URL --resolve`."
    )
    return "\n".join(lines)


_MIN_TOPICS = 3
_AMOUNT_HEX_LEN = 66


def absorb_transfers(
    logs: Sequence[object], totals: dict[str, int], min_raw: int
) -> None:
    """Add qualifying transfer recipients to the running raw totals."""
    for entry in logs:
        if not isinstance(entry, dict):
            continue
        topics = entry.get("topics")
        data = str(entry.get("data") or "0x")
        if not isinstance(topics, list) or len(topics) < _MIN_TOPICS:
            continue
        if len(data) < _AMOUNT_HEX_LEN:
            continue
        amount = int(data, 16)
        if amount < min_raw:
            continue
        to = f"0x{str(topics[2])[-40:]}"
        totals[to] = totals.get(to, 0) + amount


@dataclass(frozen=True)
class TokenMeta:
    """One scanned token with the pricing context used for its sweep."""

    token: str
    price: float
    decimals: int


@dataclass(frozen=True)
class HuntReport:
    """Recipient-sweep run: ranked candidates plus the scan context.

    ``scan_errors``/``scan_windows`` report how many log windows the RPC
    rejected, so a thin result set is not mistaken for a clean chain.
    """

    token: str
    tokens: tuple[TokenMeta, ...] = ()
    blocks: int = 0
    from_block: int = 0
    to_block: int = 0
    decimals: int = 18
    price: float = 0.0
    recipients: int = 0
    scan_errors: int = 0
    scan_windows: int = 0
    candidates: tuple[Candidate, ...] = ()
