"""Honeypot risk assessment for SPL mints from jsonParsed account records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast

_HIGH = ("accounts-start-frozen", "non-transferable")
_MEDIUM = ("transfer-hook-callback", "permanent-delegate-set", "transfer-fee-set")


def is_mint(raw: dict[str, object]) -> bool:
    """Return whether a jsonParsed record describes an SPL mint."""
    return bool(_mint_info(raw))


def mint_signals(raw: dict[str, object]) -> list[str]:
    """Extract honeypot-relevant signals from a jsonParsed mint record.

    Args:
        raw: The ``value`` object of a getAccountInfo jsonParsed response.

    Returns:
        Signal names (possibly empty when the record is not a mint).
    """
    info = _mint_info(raw)
    if not info:
        return []
    signals = []
    if info.get("mintAuthority"):
        signals.append("mint-authority-active")
    if info.get("freezeAuthority"):
        signals.append("freeze-authority-set")
    extensions = info.get("extensions")
    if isinstance(extensions, list):
        for ext in extensions:
            if isinstance(ext, dict):
                signals.extend(_extension_signals(cast("dict[str, object]", ext)))
    return signals


def verdict(signals: list[str]) -> str:
    """Grade the signal set as clean/low/medium/high risk."""
    if any(sig in signals for sig in _HIGH):
        return "high"
    if "mint-authority-active" in signals and "freeze-authority-set" in signals:
        return "medium"
    if any(sig in signals for sig in _MEDIUM):
        return "medium"
    if signals:
        return "low"
    return "clean"


def _mint_info(raw: dict[str, object]) -> dict[str, object]:
    """Drill into data.parsed.info when the record is an SPL mint."""
    data = raw.get("data")
    if not isinstance(data, dict):
        return {}
    parsed = data.get("parsed")
    if not isinstance(parsed, dict) or parsed.get("type") != "mint":
        return {}
    info = parsed.get("info")
    return cast("dict[str, object]", info) if isinstance(info, dict) else {}


def _extension_signals(ext: dict[str, object]) -> list[str]:
    """Map one Token-2022 extension entry to honeypot signals."""
    name = str(ext.get("extension", ""))
    signals: list[str] = []
    if name == "nonTransferable":
        signals.append("non-transferable")
    elif name == "defaultAccountState":
        state = str(ext.get("state", ext.get("defaultAccountState", "")))
        if "frozen" in state.lower():
            signals.append("accounts-start-frozen")
    elif name == "transferFeeConfig":
        config = ext.get("transferFeeConfig")
        text = str(config if config is not None else ext)
        if _has_nonzero_fee(text):
            signals.append("transfer-fee-set")
    elif name == "transferHook":
        signals.append("transfer-hook-callback")
    elif name == "permanentDelegate":
        delegate = ext.get("permanentDelegate")
        if isinstance(delegate, dict):
            delegate = delegate.get("address")
        if delegate:
            signals.append("permanent-delegate-set")
    return signals


def _has_nonzero_fee(text: str) -> bool:
    """Return whether a fee-config dump mentions a nonzero basis point fee."""
    return bool(re.search(r'"(?:newerFee|olderFee|basisPoints)"\s*:\s*"[1-9]', text))


_HIGH_FEE_PCT = 2.0
_TAX_GATE_SELECTORS = frozenset(
    {
        "0x8a8c523c",  # enableTrading()
        "0x751039fc",  # removeLimits()
        "0x7d1db4a5",  # _maxTxAmount()
        "0x8f9a55c0",  # _maxWalletSize()
        "0x0faee56f",  # _maxTaxSwap()
    }
)
_TAX_GATE_MIN = 3


def tax_gate_flags(selectors: set[str]) -> list[str]:
    """Flag the launchpad tax-gate selector shape (static honeypot evidence)."""
    if len(selectors & _TAX_GATE_SELECTORS) >= _TAX_GATE_MIN:
        return ["tax-gate-shape-detected"]
    return []


def evm_verdict(signals: list[str], fee_pct: float) -> str:
    """Grade EVM honeypot probe signals (transfer outcome + fee + mint)."""
    grade = "clean"
    if "tax-gate-shape-detected" in signals:
        grade = "high"
    elif "fork-unavailable" in signals:
        grade = "unknown"
    elif "transfer-reverts" in signals or fee_pct >= _HIGH_FEE_PCT:
        grade = "high"
    elif "balance-slot-not-found" in signals:
        grade = "unknown"
    elif (
        "unlimited-mint-possible" in signals
        or fee_pct > 0.0
        or any(s.startswith("donation-dilution-exposed") for s in signals)
    ):
        grade = "medium"
    elif signals:
        grade = "low"
    return grade


@dataclass(frozen=True)
class HoneypotReport:
    """SPL mint honeypot verdict with its raw signals."""

    address: str
    is_mint: bool
    verdict: str
    signals: tuple[str, ...] = ()

    def render_markdown(self) -> str:
        """Render the verdict and signals as Markdown."""
        lines: list[str] = [
            f"# Honeypot — {self.address}",
            "",
            f"- verdict: {self.verdict}",
        ]
        if self.signals:
            lines.append("- signals: " + ", ".join(self.signals))
        else:
            lines.append("- signals: none (renounced authorities, no risky extensions)")
        return "\n".join(lines)


@dataclass(frozen=True)
class EvmHoneypotReport:
    """EVM fork honeypot probe verdict with fee and slot evidence."""

    address: str
    verdict: str
    signals: tuple[str, ...] = ()
    fee_pct: float = 0.0
    balances_slot: int = -1

    def render_markdown(self) -> str:
        """Render the fork probe verdict as Markdown."""
        lines: list[str] = [
            f"# Honeypot (EVM) — {self.address}",
            "",
            f"- verdict: {self.verdict}",
            f"- fee_pct: {self.fee_pct}",
            f"- balances slot: {self.balances_slot}",
        ]
        if self.signals:
            lines.append("- signals: " + ", ".join(self.signals))
        return "\n".join(lines)
