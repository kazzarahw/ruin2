"""Proxy analysis helpers for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass

_SLOT_WORD_HEX_LEN = 64

EIP1967_IMPLEMENTATION_SLOT = (
    "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
)
EIP1967_ADMIN_SLOT = (
    "0xb53127684a568b3173ae4ea00d355d13724b9923e098f63c5230a8e330732f2c"
)
EIP1967_BEACON_SLOT = (
    "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"
)
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
_ADDRESS_HEX_LEN = 40


@dataclass
class ProxyInfo:
    """Resolved proxy information for a contract."""

    address: str
    implementation: str = ""
    admin: str = ""
    beacon: str = ""
    is_proxy: bool = False
    uninitialized_impl: bool = False
    delegated_to: str = ""

    def render_markdown(self) -> str:
        """Render proxy info as Markdown."""
        lines: list[str] = [f"# Proxy — {self.address}", ""]
        if not self.is_proxy:
            lines.append("Not a proxy (implementation slot is zero or unreadable).")
            return "\n".join(lines)
        lines.append(f"- **Implementation:** `{self.implementation}`")
        lines.append(f"- **Admin:** `{self.admin}`")
        if self.beacon:
            lines.append(f"- **Beacon:** `{self.beacon}`")
        if self.delegated_to:
            lines.append(
                f"- **EIP-7702 delegation:** `{self.delegated_to}` "
                "(delegated code marker)"
            )
        if self.uninitialized_impl:
            lines.append("- **WARNING:** Implementation appears uninitialized.")
        return "\n".join(lines)


def is_zero(hexval: str) -> bool:
    """Return whether a hex storage value is all zeros."""
    stripped = hexval.removeprefix("0x").lstrip("0")
    return stripped in ("", "0")


def resolve_proxy(
    impl_slot_value: str,
    admin_slot_value: str,
    beacon_slot_value: str = "",
    address: str = "",
) -> ProxyInfo:
    """Build a ProxyInfo from raw slot values.

    Args:
        impl_slot_value: Hex value read from the EIP-1967 implementation slot.
        admin_slot_value: Hex value read from the EIP-1967 admin slot.
        beacon_slot_value: Hex value read from the EIP-1967 beacon slot.
        address: Proxy address to attach to the returned info.

    Returns:
        A resolved ProxyInfo.
    """
    if is_zero(impl_slot_value):
        return ProxyInfo(address=address, is_proxy=False)
    impl = _extract_address(impl_slot_value)
    admin = "" if is_zero(admin_slot_value) else _extract_address(admin_slot_value)
    beacon = "" if is_zero(beacon_slot_value) else _extract_address(beacon_slot_value)
    uninitialized = impl.lower() == ZERO_ADDRESS
    return ProxyInfo(
        address=address,
        implementation=impl,
        admin=admin,
        beacon=beacon,
        is_proxy=True,
        uninitialized_impl=uninitialized,
    )


def implementation_from_slot(raw: str) -> str:
    """Return the address encoded in a 32-byte EIP-1967 implementation slot.

    Args:
        raw: Storage word as hex (with or without the 0x prefix).

    Returns:
        Lowercase address with 0x prefix, or empty string for empty words.
    """
    body = raw.removeprefix("0x").lower()
    if len(body) != _SLOT_WORD_HEX_LEN:
        return ""
    addr = body[-40:]
    if addr == "0" * 40:
        return ""
    return f"0x{addr}"


def detect_delegation(bytecode: str) -> str:
    """Return the EIP-7702 delegate address if bytecode is a designation.

    Args:
        bytecode: Hex bytecode (with or without the 0x prefix).

    Returns:
        Lowercase delegate address with 0x prefix, or empty string.
    """
    body = bytecode.removeprefix("0x").lower()
    if not body.startswith("ef0100") or len(body) < 6 + _ADDRESS_HEX_LEN:
        return ""
    return "0x" + body[6 : 6 + _ADDRESS_HEX_LEN]


def _extract_address(hexval: str) -> str:
    """Extract the last 20 bytes from a 32-byte storage word."""
    raw = hexval.removeprefix("0x")
    if len(raw) < _ADDRESS_HEX_LEN:
        return "0x" + raw.lower().zfill(_ADDRESS_HEX_LEN)
    return "0x" + raw[-_ADDRESS_HEX_LEN:].lower()
