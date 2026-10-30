"""Empirical drain-probe service for ``ruin``."""

from __future__ import annotations

import re

from ruin.core.probe import (
    ProbeHit,
    drain_selectors_in,
    minimal_proxy_implementation,
)
from ruin.core.proxy import (
    EIP1967_IMPLEMENTATION_SLOT,
    detect_delegation,
    implementation_from_slot,
)
from ruin.services.subprocesses import (
    cast_code_command,
    cast_storage_command,
    run_command,
)

_TRANSPORT_MARKERS = (
    "Fork Error",
    "Archive request",
    "403 Forbidden",
    "timed out",
)


_SELECTOR_RE = re.compile(r"^0x[0-9a-fA-F]{8}$")


def probe_drain_selectors(
    address: str,
    rpc: str,
    code: str,
    *,
    probe_from: str,
    extra_selectors: tuple[str, ...] = (),
) -> list[ProbeHit]:
    """eth_call each drain selector from an outsider; keep non-reverts.

    Args:
        address: Contract to probe.
        rpc: RPC endpoint URL.
        code: Bytecode of the contract (hex string).
        probe_from: Address the calls are sent from.
        extra_selectors: Additional raw selectors to smoke-test.

    Returns:
        ProbeHits for every drain selector found in the bytecode.
    """
    implementation = minimal_proxy_implementation(code)
    if implementation:
        code_result = run_command(cast_code_command(rpc, implementation), timeout=20.0)
        code = code_result.stdout.strip() or code
    delegate = detect_delegation(code)
    if delegate:
        code_result = run_command(cast_code_command(rpc, delegate), timeout=20.0)
        code = code_result.stdout.strip() or code
    if not implementation and not delegate:
        slot = run_command(
            cast_storage_command(rpc, address, EIP1967_IMPLEMENTATION_SLOT),
            timeout=20.0,
        ).stdout.strip()
        impl = implementation_from_slot(slot)
        if impl and impl.lower() != address.lower():
            code_result = run_command(cast_code_command(rpc, impl), timeout=20.0)
            code = code_result.stdout.strip() or code
    hits: list[ProbeHit] = []
    skipped = 0
    for selector, signature in drain_selectors_in(code):
        cmd = [
            "cast",
            "call",
            "--from",
            probe_from,
            address,
            selector,
            "--rpc-url",
            rpc,
        ]
        result = run_command(cmd, timeout=20.0)
        blob = f"{result.stderr or ''}{result.stdout or ''}"
        if result.returncode != 0 and any(
            marker in blob for marker in _TRANSPORT_MARKERS
        ):
            skipped += 1
            continue
        hits.append(
            ProbeHit(
                selector=selector,
                signature=signature,
                reverted=result.returncode != 0,
            )
        )
    if skipped:
        hits.append(
            ProbeHit(
                selector="0x????????",
                signature=f"{skipped} selector(s) skipped: RPC transport error",
                reverted=False,
            )
        )
    hits.extend(_probe_extras(address, rpc, probe_from, extra_selectors))
    return hits


def _probe_extras(
    address: str, rpc: str, probe_from: str, extra_selectors: tuple[str, ...]
) -> list[ProbeHit]:
    """eth_call caller-supplied selectors from an outsider."""
    hits: list[ProbeHit] = []
    for selector in extra_selectors:
        if not _SELECTOR_RE.match(selector):
            raise ValueError(f"invalid selector {selector!r}, want 0x + 8 hex digits")
        cmd = [
            "cast",
            "call",
            "--from",
            probe_from,
            address,
            selector,
            "--rpc-url",
            rpc,
        ]
        result = run_command(cmd, timeout=20.0)
        blob = f"{result.stderr or ''}{result.stdout or ''}"
        if result.returncode != 0 and any(
            marker in blob for marker in _TRANSPORT_MARKERS
        ):
            continue
        hits.append(
            ProbeHit(
                selector=selector.lower(),
                signature="custom selector probe",
                reverted=result.returncode != 0,
            )
        )
    return hits
