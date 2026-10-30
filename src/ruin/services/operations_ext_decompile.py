"""Runtime-bytecode review operation for unverified contracts."""

from __future__ import annotations

from dataclasses import replace

from ruin.core.decompile import DecompileReport, bytecode_report
from ruin.core.templates import template_family
from ruin.services.operations_ext_selectors import code_at, follow_delegation, inventory
from ruin.services.subprocesses import cast_call_command, run_command

_BASE_VAULT_SELECTOR = "0xeaa2d7b4"
_ADDR_HEX_LEN = 40


def decompile_data(address: str, rpc: str) -> DecompileReport:
    """Fetch runtime code and build the bytecode review payload for an address.

    Selector names come from the shared inventory (drain table, canonical
    names, 4byte lookup); the template family tags known dispatcher shapes.

    Args:
        address: Contract address to review.
        rpc: JSON-RPC endpoint to read the code from.

    Returns:
        The report object shared by the markdown and JSON output.

    Raises:
        RuntimeError: If the RPC fails while fetching the code.
        ValueError: If the address has no deployed code.
    """
    code = code_at(rpc, address)
    if not code or code == "0x":
        raise ValueError(f"no code at {address}")
    code, _note = follow_delegation(rpc, address, code, opcode_shape=True)
    pairs = inventory(code, resolve=True)
    report = bytecode_report(address, code, pairs, template_family(code), rpc)
    selectors = {selector for selector, _signature in pairs}
    return replace(report, **_oracle_link(rpc, address, selectors))


def _oracle_link(rpc: str, address: str, selectors: set[str]) -> dict[str, object]:
    """Probe Morpho-style oracle contracts for a live vault link.

    The oracle template exposes ``BASE_VAULT()`` even when the link is
    zeroed (feed-driven pricing); only the live call distinguishes the two,
    and only a nonzero link lets on-chain state move the market price.
    """
    if _BASE_VAULT_SELECTOR not in selectors:
        return {}
    result = run_command(cast_call_command(rpc, address, _BASE_VAULT_SELECTOR, []))
    raw = result.stdout.strip()
    if result.returncode != 0 or not raw.startswith("0x"):
        return {"oracle_base_vault": "unreadable", "oracle_linked": False}
    body = raw[2:].lower()
    addr = body[-_ADDR_HEX_LEN:] if len(body) >= _ADDR_HEX_LEN else ""
    if addr and not any(c != "0" for c in addr):
        addr = ""
    return {
        "oracle_base_vault": f"0x{addr}" if addr else "",
        "oracle_linked": bool(addr),
    }
