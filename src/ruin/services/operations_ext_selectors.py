"""Selector surface operation: on-chain inventory plus offline decode.

A positional is an address when it is ``0x`` plus exactly 40 hex digits; a
file path or any other ``0x`` literal decodes offline (the former ``decode``
operation) instead of hitting an RPC.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, cast

from ruin.core.chains import rpc_for
from ruin.core.decompile import scan_opcodes
from ruin.core.probe import (
    COMMON_SELECTORS,
    SelectorReport,
    SelectorRow,
    drain_selectors_in,
    extract_selectors,
    minimal_proxy_implementation,
)
from ruin.core.proxy import (
    EIP1967_IMPLEMENTATION_SLOT,
    implementation_from_slot,
)
from ruin.core.templates import template_family
from ruin.services.http import resolve_selectors
from ruin.services.operations_ext_decode import decode_text
from ruin.services.subprocesses import (
    cast_code_command,
    cast_storage_command,
    run_command,
)

_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
_HEX_LITERAL_RE = re.compile(r"^0x[0-9a-fA-F]+$")


def is_offline(raw: str) -> bool:
    """True when a selectors positional is a file path or bare 0x literal.

    Only ``0x`` plus exactly 40 hex digits counts as an on-chain address;
    anything else that is an existing file or a hex literal decodes offline.
    """
    if _ADDRESS_RE.match(raw):
        return False
    if Path(raw).exists():
        return True
    return bool(_HEX_LITERAL_RE.match(raw))


def code_at(rpc: str, address: str) -> str:
    """Fetch runtime bytecode for an address over a configured RPC.

    Raises when the RPC itself fails (403s, archive caps, timeouts) so an
    empty stdout is never mistaken for "no code at this address".
    """
    result = run_command(cast_code_command(rpc, address), timeout=20.0)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        first = detail[0] if detail else "unknown error"
        raise RuntimeError(f"rpc failure fetching code at {address}: {first}")
    return result.stdout.strip()


def inventory(code: str, *, resolve: bool) -> list[tuple[str, str]]:
    """Return (selector, signature) pairs, consulting 4byte when asked."""
    selectors = extract_selectors(code)
    drain = dict(drain_selectors_in(code))
    names = (
        resolve_selectors([s.removeprefix("0x") for s in selectors]) if resolve else {}
    )
    return [
        (
            selector,
            drain.get(selector)
            or COMMON_SELECTORS.get(selector)
            or names.get(selector.removeprefix("0x"), ""),
        )
        for selector in selectors
    ]


_PROXY_MAX_SSTORE = 2


def _proxy_shaped(code: str) -> bool:
    """True when the dispatcher delegatecalls with almost no storage writes."""
    shape = scan_opcodes(code)
    counts = cast("dict[str, int]", shape["counts"])
    return counts["delegatecall"] > 0 and counts["sstore"] <= _PROXY_MAX_SSTORE


def follow_delegation(
    rpc: str,
    address: str,
    code: str,
    *,
    follow_slot: bool = True,
    opcode_shape: bool = False,
) -> tuple[str, str]:
    """Follow EIP-1167 clone or EIP-1967 slot delegation; return (code, note).

    ``follow_slot=False`` restricts the walk to minimal-proxy clones.
    ``opcode_shape`` reads the implementation slot only when the dispatcher
    looks proxy-shaped (delegatecalls with few storage writes).
    """
    implementation = minimal_proxy_implementation(code)
    via_clone = bool(implementation)
    if not implementation and follow_slot and (not opcode_shape or _proxy_shaped(code)):
        raw = run_command(
            cast_storage_command(rpc, address, EIP1967_IMPLEMENTATION_SLOT),
            timeout=20.0,
        ).stdout.strip()
        implementation = implementation_from_slot(raw)
        if implementation.lower() == address.lower():
            implementation = ""
    if not implementation:
        return code, ""
    impl_code = code_at(rpc, implementation)
    if not impl_code or impl_code == "0x":
        dead = (
            f"clone of {implementation}"
            if via_clone
            else f"eip1967 -> {implementation}"
        )
        return code, f"{dead} (implementation has no code)"
    tail = (
        f"minimal proxy -> implementation {implementation}"
        if via_clone
        else f"eip1967 implementation {implementation}"
    )
    return impl_code, tail


def selector_report(kwargs: dict[str, Any]) -> SelectorReport:
    """Build the on-chain selector inventory shared by text and JSON output."""
    address = str(kwargs["target"])
    rpc = rpc_for(kwargs)
    code = code_at(rpc, address)
    if not code or code == "0x":
        return SelectorReport(address=address, exists=False)
    code, note = follow_delegation(rpc, address, code)
    pairs = inventory(code, resolve=bool(kwargs.get("resolve")))
    rows = tuple(
        SelectorRow(selector=selector, signature=signature)
        for selector, signature in pairs
    )
    return SelectorReport(
        address=address, clone_note=note, family=template_family(code), selectors=rows
    )


def _selectors(kwargs: dict[str, Any]) -> str:
    """List an address's dispatched selectors, or decode an offline input."""
    raw = str(kwargs["target"])
    if is_offline(raw):
        return decode_text(raw, bool(kwargs.get("resolve")))
    return selector_report(kwargs).render_markdown()


SELECTOR_OPERATIONS: dict[str, Any] = {"selectors": _selectors}
