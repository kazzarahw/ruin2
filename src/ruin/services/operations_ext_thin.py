"""Thin-liquidity collateral screen (DEX exit depth vs market holdings).

Compound-style markets accept collateral whose DEX liquidity is thin: a
whale pumps the spot price on a spot AMM, borrows against the inflated
valuation, dumps, and the market is left holding underwater collateral.
This screen scans UniV2-style PairCreated logs from a factory over a
recent block window, measures the combined buy-depth that moves each pool
holding TOKEN by ten percent (core constant-product model), converts it
with an operator-supplied USD price, and flags markets whose TOKEN
holdings exceed five times that depth.
"""

from __future__ import annotations

import json
import re

from ruin.core.thin import (
    MAX_DECIMALS,
    PoolDepth,
    ScreenParams,
    ThinCollateralReport,
    depth_model,
)
from ruin.services.rpc import SHARED_TRANSPORT, jsonrpc
from ruin.services.subprocesses import (
    cast_call_command,
    cast_logs_command,
    parse_cast_int,
    run_command,
)

_PAIR_CREATED = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"
_ADDRESS_RE = re.compile(r"0x[0-9a-fA-F]{40}")
_MAX_PAIRS = 24
_DEFAULT_DECIMALS = 18
_EXPOSURE_RATIO = 5.0
_JSON_FLAG = "--json"
_ERROR_EXCERPT = 200
_MIN_TOPICS = 4
_RESERVE_LINES = 2


def _checked_address(value: str, label: str) -> str:
    """Lowercase ``value`` after enforcing the 0x + 40-hex address shape."""
    if not _ADDRESS_RE.fullmatch(value):
        raise ValueError(f"{label} must be a 0x-prefixed 40-hex address, got {value!r}")
    return value.lower()


def _first_word(text: str) -> str:
    """First whitespace-delimited token of cast output (strips annotations)."""
    words = text.strip().split()
    return words[0] if words else ""


def _address_from(word: str) -> str:
    """Read the trailing 20 bytes of a padded hex word as a lowercase address."""
    return f"0x{word.removeprefix('0x')[-40:]}"


def _latest_block(rpc: str) -> int:
    """Read the chain head so the scan window can be clamped to it."""
    raw = jsonrpc(SHARED_TRANSPORT, rpc, "eth_blockNumber", [])
    return int(str(raw), 16)


def _pair_created_logs(
    rpc: str, factory: str, start: int, end: int
) -> list[dict[str, object]]:
    """Fetch factory logs as JSON dicts over ``[start, end]``.

    Raises:
        RuntimeError: If cast rejects the query or the output is not a JSON list.
    """
    argv = [*cast_logs_command(rpc, factory, start, end), _JSON_FLAG]
    out = run_command(argv, timeout=30.0)
    if out.returncode != 0:
        raise RuntimeError(
            f"PairCreated log scan failed: {out.stdout[:_ERROR_EXCERPT].strip()}"
        )
    try:
        doc = json.loads(out.stdout or "[]")
    except json.JSONDecodeError as error:
        raise RuntimeError("PairCreated log output was not JSON") from error
    entries = doc if isinstance(doc, list) else None
    if entries is None:
        raise RuntimeError("PairCreated log output was not a JSON list")
    return [entry for entry in entries if isinstance(entry, dict)]


def _candidate_pairs(logs: list[dict[str, object]], token: str) -> list[str]:
    """Pair addresses from PairCreated logs whose sides include ``token``."""
    pairs: list[str] = []
    for entry in logs:
        topics = entry.get("topics")
        if not isinstance(topics, list) or len(topics) < _MIN_TOPICS:
            continue
        if str(topics[0]).lower() != _PAIR_CREATED:
            continue
        if token in (_address_from(str(topics[1])), _address_from(str(topics[2]))):
            pairs.append(_address_from(str(topics[3])))
    return pairs[:_MAX_PAIRS]


def _pair_sides(rpc: str, pair: str) -> tuple[str, str] | None:
    """Read token0()/token1() of a pair; None when either read fails."""
    zero = run_command(cast_call_command(rpc, pair, "token0()", []), timeout=20.0)
    one = run_command(cast_call_command(rpc, pair, "token1()", []), timeout=20.0)
    if zero.returncode != 0 or one.returncode != 0:
        return None
    return _address_from(_first_word(zero.stdout)), _address_from(
        _first_word(one.stdout)
    )


def _reserves(rpc: str, pair: str) -> tuple[int, int] | None:
    """Read getReserves(); None when the call fails or returns too few lines."""
    out = run_command(cast_call_command(rpc, pair, "getReserves()", []), timeout=20.0)
    if out.returncode != 0:
        return None
    lines = [line for line in out.stdout.splitlines() if line.strip()]
    if len(lines) < _RESERVE_LINES:
        return None
    return parse_cast_int(lines[0]), parse_cast_int(lines[1])


def _decimals(rpc: str, token: str) -> int:
    """Read ERC20 decimals over cast; fall back to 18 on any bad read."""
    out = run_command(cast_call_command(rpc, token, "decimals()", []), timeout=20.0)
    if out.returncode != 0:
        return _DEFAULT_DECIMALS
    value = parse_cast_int(out.stdout)
    return value if 0 <= value <= MAX_DECIMALS else _DEFAULT_DECIMALS


def _balance(rpc: str, token: str, market: str) -> int | None:
    """Read the market's TOKEN balance; None when the read fails."""
    out = run_command(
        cast_call_command(rpc, token, "balanceOf(address)", [market]), timeout=20.0
    )
    if out.returncode != 0:
        return None
    return parse_cast_int(out.stdout)


def _pool_row(
    rpc: str, pair: str, token: str, params: ScreenParams
) -> PoolDepth | None:
    """One usable pool as a depth row, or None when it is stale or dust."""
    sides = _pair_sides(rpc, pair)
    if sides is None:
        return None
    reserves = _reserves(rpc, pair)
    if reserves is None:
        return None
    if sides[0] == token:
        quote, token_res, quote_res = sides[1], reserves[0], reserves[1]
    elif sides[1] == token:
        quote, token_res, quote_res = sides[0], reserves[1], reserves[0]
    else:
        return None
    token_dec = _decimals(rpc, token)
    quote_dec = _decimals(rpc, quote)
    raw = depth_model(quote_res, token_res, quote_dec, token_dec)
    usd = raw / 10**token_dec * params.price_usd
    if usd < params.min_usd:
        return None
    return PoolDepth(pair=pair, depth_raw=raw, depth_usd=round(usd, 2))


def _decide(
    balance: int | None, pairs: list[str], market_usd: float, depth_usd: float
) -> tuple[str, list[str]]:
    """Map readings to (verdict, signals) for the final report."""
    if balance is None:
        return "probe-inconclusive", ["balance-read-failed"]
    if not pairs:
        return "no-pools", ["no-pair-created-logs"]
    if market_usd > _EXPOSURE_RATIO * depth_usd:
        if depth_usd > 0:
            ratio = market_usd / depth_usd
            return "thin-collateral-exposed", [f"market-usd-over-depth:{ratio:.1f}x"]
        return "thin-collateral-exposed", ["no-usable-pool-depth"]
    return "clean", []


def thin_collateral_data(
    token: str, market: str, factory: str, rpc: str, params: ScreenParams
) -> ThinCollateralReport:
    """Screen one market's collateral against its combined DEX exit depth.

    Args:
        token: Collateral ERC20 address.
        market: Market contract whose collateral holdings are measured.
        factory: UniV2-style pair factory whose PairCreated logs are scanned.
        rpc: JSON-RPC endpoint.
        params: Price, block window, and dust-pool floor chosen by the operator.

    Returns:
        Screen report with per-pool depth rows, combined depth, market USD,
        verdict, and signals.

    Raises:
        ValueError: If any address is malformed.
        RuntimeError: If the PairCreated log scan fails.
    """
    token = _checked_address(token, "token")
    market = _checked_address(market, "market")
    factory = _checked_address(factory, "factory")
    latest = _latest_block(rpc)
    start = max(latest - max(params.blocks, 1) + 1, 0)
    logs = _pair_created_logs(rpc, factory, start, latest)
    pairs = _candidate_pairs(logs, token)
    pools = [
        row
        for pair in pairs
        if (row := _pool_row(rpc, pair, token, params)) is not None
    ]
    balance = _balance(rpc, token, market)
    token_dec = _decimals(rpc, token)
    depth_raw = sum(row.depth_raw for row in pools)
    depth_usd = sum(row.depth_usd for row in pools)
    market_usd = 0.0 if balance is None else balance / 10**token_dec * params.price_usd
    verdict, signals = _decide(balance, pairs, market_usd, depth_usd)
    return ThinCollateralReport(
        token=token,
        market=market,
        factory=factory,
        price_usd=params.price_usd,
        min_usd=params.min_usd,
        decimals=token_dec,
        from_block=start,
        to_block=latest,
        blocks=latest - start + 1,
        pairs_found=len(pairs),
        pools=tuple(pools),
        depth_raw=depth_raw,
        depth_usd=round(depth_usd, 2),
        market_raw=0 if balance is None else balance,
        market_usd=round(market_usd, 2),
        verdict=verdict,
        signals=tuple(signals),
    )
