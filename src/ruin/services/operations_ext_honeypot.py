"""Honeypot verdict operation for SPL mints."""

from __future__ import annotations

from typing import Any

from ruin.core.enums import Chain
from ruin.core.honeypot import (
    HoneypotReport,
    is_mint,
    mint_signals,
    verdict,
)
from ruin.services.chains import get_adapter, rpc_for_family

DEFAULT_RPC = rpc_for_family(Chain.SOLANA)


def honeypot_data(address: str, rpc: str | None = None) -> HoneypotReport:
    """Fetch the mint record and grade its honeypot signals."""
    adapter = get_adapter(Chain.SOLANA)
    account = adapter.fetch_account(address, rpc or DEFAULT_RPC)
    raw = account.raw
    signals = mint_signals(raw)
    return HoneypotReport(
        address=address,
        is_mint=is_mint(raw),
        verdict=verdict(signals),
        signals=tuple(signals),
    )


def honeypot_report(kwargs: dict[str, Any]) -> HoneypotReport:
    """Build the honeypot report from CLI kwargs (shared by text and JSON)."""
    return honeypot_data(str(kwargs["mint"]), str(kwargs.get("rpc") or DEFAULT_RPC))


def _honeypot(kwargs: dict[str, Any]) -> str:
    """Render the honeypot verdict for an SPL mint."""
    return honeypot_report(kwargs).render_markdown()


HONEYPOT_OPERATIONS: dict[str, Any] = {"honeypot": _honeypot}
