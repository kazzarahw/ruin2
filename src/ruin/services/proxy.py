"""Proxy resolution service for ``ruin``."""

from __future__ import annotations

from ruin.core.proxy import (
    EIP1967_ADMIN_SLOT,
    EIP1967_BEACON_SLOT,
    EIP1967_IMPLEMENTATION_SLOT,
    ProxyInfo,
    detect_delegation,
    resolve_proxy,
)
from ruin.services.subprocesses import (
    cast_code_command,
    cast_storage_command,
    run_command,
)


def resolve_proxy_onchain(address: str, rpc: str) -> ProxyInfo:
    """Read EIP-1967 slots from a live or forked chain and resolve the proxy.

    Args:
        address: The proxy contract address.
        rpc: The RPC endpoint URL.

    Returns:
        A resolved ProxyInfo with the address filled in.
    """
    impl_val = _read_slot(rpc, address, EIP1967_IMPLEMENTATION_SLOT)
    admin_val = _read_slot(rpc, address, EIP1967_ADMIN_SLOT)
    beacon_val = _read_slot(rpc, address, EIP1967_BEACON_SLOT)
    info = resolve_proxy(impl_val, admin_val, beacon_val, address=address)
    if not info.is_proxy:
        delegated = detect_delegation(_read_code(rpc, address))
        if delegated:
            info = ProxyInfo(
                address=address,
                implementation=delegated,
                is_proxy=True,
                delegated_to=delegated,
            )
    return info


def _read_code(rpc: str, address: str) -> str:
    """Read account bytecode via cast."""
    process = run_command(cast_code_command(rpc, address))
    return process.stdout.strip() or "0x"


def _read_slot(rpc: str, address: str, slot: str) -> str:
    """Read a single storage slot via cast."""
    process = run_command(cast_storage_command(rpc, address, slot))
    return process.stdout.strip() or "0x0"
