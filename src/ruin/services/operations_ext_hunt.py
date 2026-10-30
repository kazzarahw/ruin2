"""Discovery hunt operation (recipient sweep -> token-class candidates)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

import httpx

from ruin.core.chains import CHAIN_SLUG_BY_ID, rpc_for
from ruin.core.hunt import (
    Candidate,
    HuntReport,
    TokenMeta,
    absorb_transfers,
    candidate,
    rank,
)
from ruin.services.http import coin_meta
from ruin.services.rpc import SHARED_TRANSPORT, jsonrpc

_LOG_CHUNK = 25
_MAX_BLOCKS = 10000
_CODE_CAP = 600
_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
_SOURCIFY = "https://sourcify.dev/server/v2/contract/"
_DECIMALS_SELECTOR = "0x313ce567"
_DEFAULT_DECIMALS = 18
_MAX_DECIMALS = 36
_HEX_WORD_LEN = 66
_HTTP_OK = 200


def scan_recipients(
    rpc: str, token: str, start: int, end: int, min_raw: int
) -> tuple[dict[str, int], int, int]:
    """Sum inbound ERC20 transfers per recipient; report window failures.

    Returns (totals, failed_windows, total_windows). A failed window is an
    RPC rejection (cap, 4xx, malformed reply), not an empty chain.
    """
    totals: dict[str, int] = {}
    windows = 0
    failed = 0
    for base in range(start, end + 1, _LOG_CHUNK):
        top = min(base + _LOG_CHUNK - 1, end)
        windows += 1
        query = {
            "fromBlock": hex(base),
            "toBlock": hex(top),
            "address": token,
            "topics": [_TRANSFER_TOPIC],
        }
        logs = jsonrpc(SHARED_TRANSPORT, rpc, "eth_getLogs", [query])
        if not isinstance(logs, list):
            logs = jsonrpc(SHARED_TRANSPORT, rpc, "eth_getLogs", query)
        if not isinstance(logs, list):
            failed += 1
            continue
        absorb_transfers(logs, totals, min_raw)
    return totals, failed, windows


def code_map(rpc: str, addrs: list[str]) -> dict[str, str]:
    """Fetch bytecode for candidate addresses (bounded, sequential)."""
    codes: dict[str, str] = {}
    for addr in addrs[:_CODE_CAP]:
        code = jsonrpc(SHARED_TRANSPORT, rpc, "eth_getCode", [addr, "latest"])
        if isinstance(code, str) and code != "0x":
            codes[addr] = code
    return codes


def is_verified(address: str, chain: int = 1) -> bool:
    """True when Sourcify v2 reports a matching verification."""
    try:
        base = f"{_SOURCIFY}{chain}/"
        response = httpx.get(base + f"{address}?fields=metadata", timeout=10.0)
        if response.status_code != _HTTP_OK:
            return False
        payload = response.json()
        return bool(
            isinstance(payload, dict)
            and (payload.get("match") or payload.get("creationMatch"))
        )
    except httpx.HTTPError:
        return False


def chain_id(rpc: str) -> int:
    """Read the chain id so Sourcify lookups target the right chain."""
    try:
        raw = jsonrpc(SHARED_TRANSPORT, rpc, "eth_chainId", [])
        return int(str(raw), 16) if isinstance(raw, str) else 1
    except (httpx.HTTPError, ValueError, TypeError):
        return 1


def decimals_of(rpc: str, token: str) -> int:
    """Read ERC20 decimals over eth_call; assume 18 when not exposed."""
    try:
        raw = jsonrpc(
            SHARED_TRANSPORT,
            rpc,
            "eth_call",
            [{"to": token, "data": _DECIMALS_SELECTOR}, "latest"],
        )
        text = str(raw or "")
        if len(text) >= _HEX_WORD_LEN:
            value = int(text, 16)
            if value <= _MAX_DECIMALS:
                return value
    except (ValueError, RuntimeError):
        pass
    return _DEFAULT_DECIMALS


def price_and_decimals(rpc: str, token: str) -> tuple[float, int]:
    """Live USD price + decimals from DefiLlama coins, else safe defaults."""
    try:
        chain_id = int(str(jsonrpc(SHARED_TRANSPORT, rpc, "eth_chainId", [])), 16)
    except (ValueError, RuntimeError):
        chain_id = 0
    slug = CHAIN_SLUG_BY_ID.get(chain_id, "")
    meta = coin_meta(slug, token) if slug else {}
    raw_price = meta.get("price")
    price = float(raw_price) if isinstance(raw_price, (int, float, str)) else 0.0
    decimals = meta.get("decimals")
    if not isinstance(decimals, int):
        decimals = decimals_of(rpc, token)
    if price <= 0:
        price = 1.0
    return price, decimals


_ADDRESS_RE = re.compile(r"0x[0-9a-fA-F]{40}")


def _scan_one(
    rpc: str, token: str, span: tuple[int, int], min_usd: float
) -> tuple[dict[str, float], int, int, float, int]:
    """Sum per-recipient USD for one (already validated) token."""
    code = jsonrpc(SHARED_TRANSPORT, rpc, "eth_getCode", [token, "latest"])
    if not isinstance(code, str) or code == "0x":
        # public endpoints intermittently serve empty code for live tokens
        code = jsonrpc(SHARED_TRANSPORT, rpc, "eth_getCode", [token, "latest"])
    if not isinstance(code, str) or code == "0x":
        raise ValueError(
            f"no code at {token} on this RPC (wrong chain, or endpoint "
            f"code-flap: retry against a second endpoint)"
        )
    price, decimals = price_and_decimals(rpc, token)
    min_raw = int(min_usd / max(price, 0.01) * 10**decimals)
    raw, failed, windows = scan_recipients(rpc, token, span[0], span[1], min_raw)
    usd: dict[str, float] = {
        addr: amt / 10**decimals * price for addr, amt in raw.items()
    }
    return usd, failed, windows, price, decimals


def _resolve_span(latest: int, window: int | tuple[int, int]) -> tuple[int, int]:
    """Clamp a recent-block count or explicit (start, end) range to the chain."""
    if isinstance(window, tuple):
        if window[1] <= 0 or window[1] > latest:
            return (window[0], latest)
        return window
    return (max(latest - min(window, _MAX_BLOCKS), 0), latest)


def _validate_tokens(tokens: Sequence[str]) -> None:
    """Reject positional arguments that are not 0x-prefixed addresses."""
    for tok in tokens:
        if not _ADDRESS_RE.fullmatch(tok):
            raise ValueError(
                f"token must be a 0x-prefixed contract address, got {tok!r}"
            )


def _scan_tokens(
    rpc: str,
    tokens: Sequence[str],
    span: tuple[int, int],
    min_usd: float,
) -> tuple[dict[str, float], int, int, list[TokenMeta]]:
    """Sweep every token over the span, merging recipient USD totals."""
    usd: dict[str, float] = {}
    failed = 0
    windows = 0
    metas: list[TokenMeta] = []
    for tok in tokens:
        t_usd, f, w, price, decimals = _scan_one(rpc, tok, span, min_usd)
        failed += f
        windows += w
        for addr, value in t_usd.items():
            usd[addr] = usd.get(addr, 0.0) + value
        metas.append(TokenMeta(token=tok, price=price, decimals=decimals))
    return usd, failed, windows, metas


def _build_candidates(rpc: str, usd: dict[str, float], limit: int) -> list[Candidate]:
    """Classify funded recipients by bytecode and keep the top ``limit``."""
    ranked = sorted(usd.items(), key=lambda kv: -kv[1])
    codes = code_map(rpc, [addr for addr, _ in ranked])
    cands: list[Candidate] = []
    for addr, value in ranked:
        code = codes.get(addr)
        if code is None:
            continue
        built = candidate(addr, value, code)
        if built is not None:
            cands.append(built)
    return rank(cands, limit)


def _flag_verified(rpc: str, cands: list[Candidate]) -> list[Candidate]:
    """Mark each candidate with its Sourcify verification status."""
    chain = chain_id(rpc)
    return [
        Candidate(
            c.address,
            c.usd,
            c.mintable,
            c.ownered,
            is_verified(c.address, chain),
        )
        for c in cands
    ]


def hunt_data(
    tokens: Sequence[str],
    rpc: str,
    window: int | tuple[int, int],
    min_usd: float,
    limit: int,
) -> HuntReport:
    """Run the recipient->code->class->verification pipeline over 1+ tokens."""
    _validate_tokens(tokens)
    latest = int(str(jsonrpc(SHARED_TRANSPORT, rpc, "eth_blockNumber", [])), 16)
    resolved = _resolve_span(latest, window)
    usd, failed, windows, metas = _scan_tokens(rpc, tokens, resolved, min_usd)
    if windows and failed == windows:
        raise RuntimeError(
            f"all {windows} log windows failed - RPC rejected the scan, "
            f"not an empty chain"
        )
    flagged = _flag_verified(rpc, _build_candidates(rpc, usd, limit))
    primary = metas[0]
    return HuntReport(
        token=tokens[0],
        tokens=tuple(metas),
        blocks=resolved[1] - resolved[0] + 1,
        from_block=resolved[0],
        to_block=resolved[1],
        decimals=primary.decimals,
        price=primary.price,
        recipients=len(usd),
        scan_errors=failed,
        scan_windows=windows,
        candidates=tuple(flagged),
    )


def hunt_payload(kwargs: dict[str, Any]) -> HuntReport:
    """Build the hunt report from CLI kwargs (shared by text and JSON)."""
    rpc = rpc_for(kwargs)
    also = tuple(str(t) for t in (kwargs.get("also") or ()))
    window: int | tuple[int, int] = int(kwargs.get("blocks") or 1500)
    if kwargs.get("from_block") is not None:
        window = (int(kwargs["from_block"]), int(kwargs.get("to_block") or 0))
    return hunt_data(
        (str(kwargs["token"]), *also),
        rpc,
        window,
        float(kwargs.get("min_usd") or 2000),
        int(kwargs.get("limit") or 40),
    )
