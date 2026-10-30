"""Signature-gated mint surface screen (no fork needed)."""

from __future__ import annotations

from ruin.core.probe import SelectorRow
from ruin.core.screens import MintSigReport
from ruin.services.operations_ext_selectors import code_at, follow_delegation, inventory
from ruin.services.subprocesses import (
    cast_call_command,
    cast_code_command,
    run_command,
)

_SIG_MINT_PATTERNS = (
    "withsig",
    "withauthorization",
    "bysig",
    "permintmint",
    "sweepunclaimed",
    "depositwith",
    "mintwith",
)
_CAP_GETTERS = (
    "getMaxMint(address)",
    "maxMint()",
    "remainingMintable()",
    "getMintLimit(address)",
    "publicMintLimit()",
)
_UINT256_MAX = 2**256 - 1
_OWNER_SIG = "owner()"
_ADDRESS_HEX_LEN = 42


def _matches_sig_mint(signature: str) -> bool:
    """True when a resolved signature looks sig-gated or unclaimed-sweep."""
    lowered = signature.lower()
    return any(pattern in lowered for pattern in _SIG_MINT_PATTERNS)


def _owner_state(endpoint: str, address: str) -> tuple[str, bool]:
    """Return (owner text, owner-is-EOA) for an address via owner()."""
    owner = run_command(
        cast_call_command(endpoint, address, _OWNER_SIG, []), timeout=20.0
    )
    if owner.returncode != 0:
        return "", False
    text = owner.stdout.strip().split(" [")[0]
    if not text.startswith("0x") or len(text) != _ADDRESS_HEX_LEN:
        return text, False
    size = run_command(cast_code_command(endpoint, text), timeout=20.0)
    return text, size.stdout.strip() in ("", "0x")


def _cap_state(endpoint: str, address: str) -> tuple[bool, bool]:
    """Return (any-cap-getter-present, saturated) from getter probes."""
    present = False
    saturated = False
    for sig in _CAP_GETTERS:
        args = (
            ["0x0000000000000000000000000000000000000000"] if "(address)" in sig else []
        )
        result = run_command(
            cast_call_command(endpoint, address, sig, args), timeout=20.0
        )
        if result.returncode != 0:
            continue
        present = True
        body = result.stdout.strip().split(" [")[0].replace(",", "")
        value = int(body, 16) if body.startswith("0x") else int(body or "0")
        saturated = saturated or value >= _UINT256_MAX // 2
    return present, saturated


def mintsig_data(address: str, rpc: str) -> MintSigReport:
    """Screen an ERC20-ish contract for signature-gated unbounded minting."""
    code = code_at(rpc, address)
    if not code or code == "0x":
        raise ValueError(f"no code at {address}")
    code, _note = follow_delegation(rpc, address, code, opcode_shape=True)
    pairs = inventory(code, resolve=True)
    sig_mint = tuple(
        SelectorRow(selector=sel, signature=sig)
        for sel, sig in pairs
        if _matches_sig_mint(sig)
    )
    owner, owner_eoa = _owner_state(rpc, address)
    cap_present, cap_saturated = _cap_state(rpc, address)
    flags: list[str] = []
    if sig_mint:
        flags.append("sig-mint-surface")
    if owner_eoa:
        flags.append("owner-is-EOA")
    if not cap_present:
        flags.append("cap-getter-missing")
    if cap_saturated:
        flags.append("cap-saturated")
    unbounded = bool(sig_mint) and (owner_eoa or not cap_present or cap_saturated)
    if unbounded:
        flags.append("sig-gated-unbounded-mint")
    return MintSigReport(
        address=address,
        rpc=rpc,
        sig_mint=sig_mint,
        owner=owner,
        owner_eoa=owner_eoa,
        cap_getter_present=cap_present,
        cap_saturated=cap_saturated,
        verdict="review" if unbounded else "clean",
        flags=tuple(flags),
    )
