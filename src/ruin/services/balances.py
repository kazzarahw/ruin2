"""Shared balances-slot hunt: fund candidates until balanceOf reads back."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.core.slots import NAMED_BASE_SLOTS
from ruin.services.rpc import SHARED_TRANSPORT, jsonrpc
from ruin.services.subprocesses import (
    cast_balance_command,
    cast_index_command,
    parse_cast_int,
    run_command,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

_DEFAULT_PROBE = 10**24


def _candidate_bases(max_base: int) -> Iterator[int]:
    """Yield legacy bases 0..max_base, then the ERC-7201 named bases."""
    yield from range(max_base + 1)
    yield from NAMED_BASE_SLOTS.values()


def find_balance_slot(
    endpoint: str,
    token: str,
    wallet: str,
    *,
    max_base: int = 23,
    probe_value: int = _DEFAULT_PROBE,
) -> tuple[int, str]:
    """Credit (wallet, base) candidates until balanceOf(wallet) reads back.

    Args:
        endpoint: Fork RPC endpoint accepting anvil_setStorageAt.
        token: ERC20 token whose balances mapping is being hunted.
        wallet: Account credited while hunting.
        max_base: Highest legacy base slot to try.
        probe_value: Raw amount credited to each candidate slot.

    Returns:
        (base, value-slot key) for the first hit, else (-1, "").
    """
    for base in _candidate_bases(max_base):
        key = run_command(
            cast_index_command("address", wallet, base), timeout=20.0
        ).stdout.strip()
        if not key:
            continue
        jsonrpc(
            SHARED_TRANSPORT,
            endpoint,
            "anvil_setStorageAt",
            [token, key, f"0x{probe_value:064x}"],
        )
        balance = run_command(
            cast_balance_command(endpoint, token, wallet), timeout=20.0
        )
        if parse_cast_int(balance.stdout) == probe_value:
            return base, key
    return -1, ""
