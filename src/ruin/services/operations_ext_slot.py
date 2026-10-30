"""Balances-slot hunt operation (fork-based storage layout probe)."""

from __future__ import annotations

from typing import Any

from ruin.core.chains import rpc_for
from ruin.core.slots import NAMED_BASE_SLOTS, SlotHuntReport
from ruin.services.balances import find_balance_slot
from ruin.services.fork import fork
from ruin.services.rpc import SHARED_TRANSPORT, jsonrpc
from ruin.services.subprocesses import ANVIL_DEV_ADDRESS, DEV_FUND_WEI

SLOT_PORT = 19670
_LEGACY_MAX = 48
_PROBE_VALUE = 123456789


def hunt_slot(rpc: str, token: str, account: str) -> SlotHuntReport:
    """Fork the chain and find the balances base slot for a token."""
    cm = fork(SLOT_PORT, rpc)
    try:
        endpoint = cm.__enter__()
    except RuntimeError:
        return SlotHuntReport(token=token, found=False, signals=("fork-unavailable",))
    try:
        jsonrpc(
            SHARED_TRANSPORT,
            endpoint,
            "anvil_setBalance",
            [ANVIL_DEV_ADDRESS, DEV_FUND_WEI],
        )
        base, _key = find_balance_slot(
            endpoint,
            token,
            account,
            max_base=_LEGACY_MAX,
            probe_value=_PROBE_VALUE,
        )
    finally:
        cm.__exit__(None, None, None)
    if base < 0:
        return SlotHuntReport(token=token, found=False, signals=("slot-not-found",))
    name = next(
        (n for n, v in NAMED_BASE_SLOTS.items() if v == base),
        "",
    )
    return SlotHuntReport(
        token=token,
        found=True,
        account=account,
        base_slot=hex(base),
        family=name,
        formula="keccak256(account32 || base32)",
    )


def slot_hunt_request(kwargs: dict[str, Any]) -> SlotHuntReport:
    """Run the slot hunt for CLI kwargs (shared by text and JSON output)."""
    rpc = rpc_for(kwargs)
    if not rpc:
        raise ValueError("slot-hunt needs --rpc (fork source)")
    account = str(kwargs.get("account") or ANVIL_DEV_ADDRESS)
    return hunt_slot(rpc, str(kwargs["token"]), account)


def _slot_hunt(kwargs: dict[str, Any]) -> str:
    """Run the balances-slot hunt for an ERC20 token."""
    return slot_hunt_request(kwargs).render_markdown()


SLOT_OPERATIONS: dict[str, Any] = {"slot-hunt": _slot_hunt}
