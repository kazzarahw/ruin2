"""ERC-4626 donation-dilution fork probe (shared by the EVM honeypot flow)."""

from __future__ import annotations

from ruin.core.probe import (
    extract_selectors,
    stale_lock_present,
)
from ruin.core.solvency import stale_rate_flag
from ruin.services.balances import find_balance_slot
from ruin.services.operations_ext_selectors import follow_delegation
from ruin.services.rpc import SHARED_TRANSPORT, jsonrpc
from ruin.services.subprocesses import (
    ANVIL_DEV_ADDRESS,
    DEFAULT_PRIVATE_KEY,
    cast_call_command,
    cast_code_command,
    cast_index_command,
    cast_send_command,
    parse_cast_int,
    run_command,
)

_TOTAL_ASSETS_SELECTOR = "0x01e1d114"
_DILUTION_PCT = 0.5


def _preview_deposit(endpoint: str, token: str, assets: int) -> int:
    """Preview the shares a deposit of ``assets`` would mint."""
    result = run_command(
        cast_call_command(endpoint, token, "previewDeposit(uint256)", [str(assets)]),
        timeout=20.0,
    )
    return parse_cast_int(result.stdout) if result.returncode == 0 else 0


def _probe_code(endpoint: str, token: str) -> str:
    """Fetch the token code, following clone or EIP-1967 delegation if present."""
    code = run_command(cast_code_command(endpoint, token), timeout=20.0).stdout
    if _TOTAL_ASSETS_SELECTOR in extract_selectors(code):
        return code
    code_after, _note = follow_delegation(endpoint, token, code)
    return code_after


def _nav_jump_pct(endpoint: str, token: str, assets: int, supply: int) -> float:
    """Percentage NAV-per-share jump caused by the donation (ERC-7540 mode)."""
    assets_after = parse_cast_int(
        run_command(
            cast_call_command(endpoint, token, "totalAssets()", []), timeout=20.0
        ).stdout
    )
    price_before = assets * 10**18 // supply
    price_after = assets_after * 10**18 // supply
    return (price_after - price_before) * 100.0 / price_before


def _zero_balance_quote(
    endpoint: str,
    token: str,
    asset: str,
    base: int,
    probe_amount: int,
) -> tuple[int, int] | None:
    """Zero the vault balance slot and re-read totalAssets and the quote.

    Returns:
        (totalAssets, previewDeposit) measured with the slot zeroed, or None
        when the balance slot key cannot be resolved.
    """
    key = run_command(
        cast_index_command("address", token, base), timeout=20.0
    ).stdout.strip()
    if not key:
        return None
    original = jsonrpc(
        SHARED_TRANSPORT, endpoint, "eth_getStorageAt", [token, key, "latest"]
    )
    jsonrpc(
        SHARED_TRANSPORT, endpoint, "anvil_setStorageAt", [asset, key, f"0x{0:064x}"]
    )
    ta_after = parse_cast_int(
        run_command(
            cast_call_command(endpoint, token, "totalAssets()", []), timeout=20.0
        ).stdout
    )
    quote = _preview_deposit(endpoint, token, probe_amount)
    jsonrpc(
        SHARED_TRANSPORT,
        endpoint,
        "anvil_setStorageAt",
        [asset, key, str(original or "0x")],
    )
    return ta_after, quote


def _drain_stale_rate(
    endpoint: str,
    token: str,
    asset: str,
    base: int,
    quote_ctx: tuple[int, int, int],
) -> str | None:
    """Zero the vault balance slot and re-quote; flag cached-rate drift.

    ``quote_ctx`` carries (assets, probe_amount, before) from the caller.
    """
    assets, probe_amount, before = quote_ctx
    measured = _zero_balance_quote(endpoint, token, asset, base, probe_amount)
    if measured is None:
        return None
    ta_after, quote = measured
    return stale_rate_flag(assets, before, ta_after, quote)


def probe_donation(endpoint: str, token: str) -> list[str]:
    """Donate 1% of the vault ASSET and measure the deposit dilution caused.

    Vaults without a virtual-share offset mint post-donation deposits at an
    inflated price (the ERC-4626 donation class); stale-rate exit queues turn
    that into a live loss vector (flagged via ``donation-stale-lock-combo``).
    Returns [] for non-ERC4626 tokens.
    """
    code = _probe_code(endpoint, token)
    signals: list[str] = []
    assets_result = run_command(
        cast_call_command(endpoint, token, "totalAssets()", []), timeout=20.0
    )
    if (
        _TOTAL_ASSETS_SELECTOR not in extract_selectors(code)
        and assets_result.returncode != 0
    ):
        return signals
    asset_result = run_command(
        cast_call_command(endpoint, token, "asset()", []), timeout=20.0
    )
    if asset_result.returncode != 0 or assets_result.returncode != 0:
        return signals
    asset_word = asset_result.stdout.strip().split(" [")[0]
    asset = f"0x{asset_word.removeprefix('0x')[-40:]}"
    assets = parse_cast_int(assets_result.stdout)
    probe_amount = max(assets // 1000, 1)
    before = _preview_deposit(endpoint, token, probe_amount)
    donation = max(assets // 100, 1)
    donor_slot, donor_key = find_balance_slot(endpoint, asset, ANVIL_DEV_ADDRESS)
    supply_result = run_command(
        cast_call_command(endpoint, token, "totalSupply()", []), timeout=20.0
    )
    supply_before = (
        parse_cast_int(supply_result.stdout) if supply_result.returncode == 0 else 0
    )
    if donor_slot < 0 or (before <= 0 and supply_before <= 0):
        return ["donation-probe-skipped"]
    stale = _drain_stale_rate(
        endpoint, token, asset, donor_slot, (assets, probe_amount, before)
    )
    jsonrpc(
        SHARED_TRANSPORT,
        endpoint,
        "anvil_setStorageAt",
        [asset, donor_key, f"0x{donation + probe_amount:064x}"],
    )
    donated = run_command(
        cast_send_command(
            endpoint,
            asset,
            "transfer(address,uint256)",
            [token, str(donation)],
            DEFAULT_PRIVATE_KEY,
        ),
        timeout=30.0,
    )
    if donated.returncode != 0:
        return ["donation-probe-skipped"]
    if before > 0:
        after = _preview_deposit(endpoint, token, probe_amount)
        pct = (before - after) * 100.0 / before
    else:
        pct = _nav_jump_pct(endpoint, token, assets, supply_before)
    if pct >= _DILUTION_PCT:
        signals.append(f"donation-dilution-exposed:{round(pct, 2)}%")
        if stale_lock_present(code):
            signals.append("donation-stale-lock-combo")
    else:
        signals.append("donation-probe-clean")
    if stale:
        signals.append(stale)
    return signals
