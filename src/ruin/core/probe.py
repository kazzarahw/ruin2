"""Selector extraction and drain-probe helpers for ``ruin``."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

_SELECTOR_PATTERN = re.compile(r"63([0-9a-fA-F]{8})14")
_LOOSE_PATTERN = re.compile(r"63([0-9a-fA-F]{8})")
_FALLBACK_MIN = 4

DRAIN_SELECTORS: dict[str, str] = {
    "0x8814fa27": "withdraw()",
    "0x2e1a7d4d": "withdraw(uint256)",
    "0x9492825a": "withdrawAll()",
    "0xed4fffe0": "emergencyWithdraw()",
    "0x123acb78": "claim()",
    "0x00779d52": "rescue()",
    "0xb827274a": "sweep()",
    "0x25f1eb9d": "rescueTokens(address)",
    "0x084d3512": "execute()",
    "0xa22e8dc7": "flush()",
}


_MINIMAL_PROXY = re.compile(
    r"363d3d373d3d3d363d73([0-9a-fA-F]{40})5af43d82803e903d91602b57fd5bf3"
)


@lru_cache(maxsize=256)
def minimal_proxy_implementation(bytecode: str) -> str:
    """Return the implementation address if bytecode is an EIP-1167 clone.

    Args:
        bytecode: Hex bytecode (with or without the 0x prefix).

    Returns:
        Lowercase implementation address with 0x prefix, or empty string.
    """
    body = bytecode.removeprefix("0x")
    match = _MINIMAL_PROXY.search(body)
    return f"0x{match.group(1).lower()}" if match else ""


@lru_cache(maxsize=256)
def extract_selectors(bytecode: str) -> tuple[str, ...]:
    """Return the 4-byte selectors referenced by an EVM dispatcher.

    Args:
        bytecode: Hex bytecode (with or without the 0x prefix).

    Returns:
        Sorted lowercase selectors, each with a 0x prefix.
    """
    body = bytecode.removeprefix("0x")
    found = {f"0x{m.lower()}" for m in _SELECTOR_PATTERN.findall(body)}
    if len(found) < _FALLBACK_MIN:
        found |= {f"0x{m.lower()}" for m in _LOOSE_PATTERN.findall(body)}
    return tuple(sorted(found))


def drain_selectors_in(bytecode: str) -> list[tuple[str, str]]:
    """Return (selector, signature) pairs for drain-shaped selectors present."""
    found = set(extract_selectors(bytecode))
    return [
        (selector, signature)
        for selector, signature in DRAIN_SELECTORS.items()
        if selector in found
    ]


def selector_delta(new_code: str, old_code: str) -> tuple[list[str], list[str]]:
    """Return (added, removed) selectors between two contract bytecodes.

    Args:
        new_code: Bytecode of the new implementation (hex).
        old_code: Bytecode of the old implementation (hex).

    Returns:
        Sorted selectors present only in new, then only in old.
    """
    new = set(extract_selectors(new_code))
    old = set(extract_selectors(old_code))
    return (sorted(new - old), sorted(old - new))


COMMON_SELECTORS: dict[str, str] = {
    "0xa9059cbb": "transfer(address,uint256)",
    "0x23b872dd": "transferFrom(address,address,uint256)",
    "0x095ea7b3": "approve(address,uint256)",
    "0x70a08231": "balanceOf(address)",
    "0x18160ddd": "totalSupply()",
    "0x06fdde03": "name()",
    "0x95d89b41": "symbol()",
    "0x313ce567": "decimals()",
    "0xdd62ed3e": "allowance(address,address)",
    "0x8da5cb5b": "owner()",
    "0x715018a6": "renounceOwnership()",
    "0xf2fde38b": "transferOwnership(address)",
    "0xd505accf": "permit(address,address,uint256,uint256,uint8,bytes32,bytes32)",
    "0x3644e515": "safeTransferFrom(address,address,uint256)",
    "0x42842e0e": "safeTransferFrom(address,address,uint256,bytes)",
    "0x150b7a02": "onERC721Received(address,address,uint256,bytes)",
    "0xac9650d8": "multicall(bytes[])",
    "0x6a761202": (
        "execTransaction(address,uint256,bytes,uint8,uint256,uint256,"
        "uint256,address,address,bytes)"
    ),
    "0x38ed1739": "swapExactTokensForTokens(uint256,uint256,address[],address,uint256)",
    "0x8803dbee": "swapTokensForExactTokens(uint256,uint256,address[],address,uint256)",
    "0x791ac947": "swapExactTokensForETH(uint256,uint256,address[],address,uint256)",
    "0x78e890ba": "domainSeparatorV4()",
    "0xc4d252f5": "cancel(bytes32)",
    "0x40c10f19": "mint(address,uint256)",
}


STALE_LOCK_SELECTORS = frozenset(
    {
        "0x9343d9e1",  # cooldownShares(uint256)
        "0xf2888dbb",  # unstake(address)
        "0xe7a6bc44",  # cooldown(address,uint256)
        "0x710ba631",  # requestUnstake(address,uint256)
        "0x6482a22f",  # lockShares(uint256)
        "0x6b174f35",  # queueWithdrawal(uint256)
    }
)


@lru_cache(maxsize=256)
def stale_lock_present(bytecode: str) -> bool:
    """Return True when the dispatcher exposes a stale-rate exit-queue entry point.

    Vaults that record assets-per-share at cooldown time pay locked users at
    the pre-donation rate, giving an ERC-4626 donation a real loss vector
    beyond preview dilution.
    """
    return bool(set(extract_selectors(bytecode)) & STALE_LOCK_SELECTORS)


@dataclass(frozen=True)
class SelectorRow:
    """One (selector, signature) pair in a dispatcher inventory."""

    selector: str
    signature: str


@dataclass(frozen=True)
class SelectorReport:
    """On-chain selector inventory for one address.

    ``exists`` is False when the address had no deployed code; the optional
    context fields describe a proxy clone note and a template family.
    """

    address: str
    exists: bool = True
    clone_note: str = ""
    family: str = ""
    selectors: tuple[SelectorRow, ...] = ()

    def render_markdown(self) -> str:
        """Render the inventory exactly as the CLI text output does."""
        if not self.exists:
            return f"no code at {self.address}"
        lines: list[str] = [f"# Selectors at {self.address}", ""]
        if self.clone_note:
            lines.append(self.clone_note)
            lines.append("")
        lines.append(f"{len(self.selectors)} selectors found")
        lines.append("")
        if self.family:
            lines.append(f"template family: {self.family}")
            lines.append("")
        lines.extend(
            f"- `{row.selector}` {row.signature}".rstrip() for row in self.selectors
        )
        return "\n".join(lines)


@dataclass(frozen=True)
class ProbeHit:
    """A drain selector that was probed live, with its revert status."""

    selector: str
    signature: str
    reverted: bool

    def label(self) -> str:
        """Render the hit as ``selector signature [ok|reverted]``."""
        state = "reverted" if self.reverted else "ok"
        return f"`{self.selector}` {self.signature} [{state}]"


@dataclass(frozen=True)
class ProbeReport:
    """Drain-probe results for one address."""

    address: str
    hits: tuple[ProbeHit, ...] = ()

    def render_markdown(self) -> str:
        """Render the probe results as Markdown."""
        lines: list[str] = [f"# Drain Probe — {self.address}", ""]
        if not self.hits:
            lines.append("No drain-shaped selectors found in bytecode.")
            return "\n".join(lines)
        for hit in self.hits:
            lines.append(f"- [ ] {hit.label()}")
        lines.append("")
        lines.append(
            "> Non-reverting calls are a smoke signal only: empty-calldata "
            "calls to argument-taking functions revert regardless of guards. "
            "Confirm on a fork with a real transaction before believing "
            "anything."
        )
        return "\n".join(lines)


@dataclass(frozen=True)
class ImplDiffReport:
    """Selector-surface diff between two contract implementations.

    ``new_names`` carries signatures for the added selectors,
    ``drain_added`` lists added selectors with a drain shape, and
    ``old_missing`` records that the old side had no code on its RPC.
    """

    new_impl: str
    old_impl: str
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    new_names: tuple[SelectorRow, ...] = ()
    drain_added: tuple[str, ...] = ()
    old_missing: bool = False

    def render_markdown(self) -> str:
        """Render the diff exactly as the CLI text output does."""
        names = {row.selector: row.signature for row in self.new_names}
        lines: list[str] = [f"# Impl diff — {self.old_impl} -> {self.new_impl}", ""]
        if self.old_missing:
            lines.append("WARNING: old side has no code on its RPC (wrong chain?)")
        lines.append(f"{len(self.added)} added, {len(self.removed)} removed")
        lines.append("")
        lines.append("## Added")
        lines.extend(
            [f"- `{sel}` {names.get(sel, '')}".rstrip() for sel in self.added]
            or ["- none"]
        )
        lines.append("")
        lines.append("## Removed")
        lines.extend([f"- `{sel}`" for sel in self.removed] or ["- none"])
        if self.drain_added:
            lines.append("")
            joined = ", ".join(self.drain_added)
            lines.append(f"DRAIN-SHAPED NEW SELECTORS: {joined}")
        return "\n".join(lines)
