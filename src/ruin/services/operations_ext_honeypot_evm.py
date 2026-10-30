"""EVM honeypot probe operation (fork-based transfer/fee/mint checks)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import httpx

from ruin.core.chains import rpc_for
from ruin.core.honeypot import (
    EvmHoneypotReport,
    evm_verdict,
    tax_gate_flags,
)
from ruin.core.probe import (
    extract_selectors,
)
from ruin.services.balances import find_balance_slot
from ruin.services.fork import FORK_PORT, fork
from ruin.services.operations_ext_donation import probe_donation
from ruin.services.rpc import SHARED_TRANSPORT, jsonrpc
from ruin.services.subprocesses import (
    ANVIL_DEV_ADDRESS,
    DEFAULT_PRIVATE_KEY,
    DEV_FUND_WEI,
    cast_balance_command,
    cast_call_command,
    cast_send_command,
    parse_cast_int,
    run_command,
)

if TYPE_CHECKING:
    import subprocess

_RECV = "0x70997970C51812dc3a010C7d01b50e0d24c8f778"
_PROBE = 10**18
_REVERT_RE = re.compile(r'execution reverted: ([^\n,"]+)')


def _revert_reason(result: subprocess.CompletedProcess[str]) -> str:
    """Extract the revert string from a failed cast send, if any."""
    match = _REVERT_RE.search(result.stderr or "") or _REVERT_RE.search(
        result.stdout or ""
    )
    if match is None:
        return ""
    return str(match.group(1)).strip()


def probe_transfer(endpoint: str, token: str) -> tuple[list[str], float]:
    """Send a real transfer on the fork; return (signals, fee percent)."""
    before = run_command(cast_balance_command(endpoint, token, _RECV))
    result = run_command(
        cast_send_command(
            endpoint,
            token,
            "transfer(address,uint256)",
            [_RECV, str(_PROBE)],
            DEFAULT_PRIVATE_KEY,
        ),
        timeout=60.0,
    )
    if result.returncode != 0:
        blob = f"{result.stderr or ''}{result.stdout or ''}"
        if "Fork Error" in blob or "Archive request" in blob:
            return (["fork-unavailable"], 0.0)
        signals = ["transfer-reverts"]
        reason = _revert_reason(result)
        if reason:
            signals.append(f"revert-reason:{reason}")
        return (signals, 0.0)
    got = run_command(cast_balance_command(endpoint, token, _RECV))
    try:
        delta = parse_cast_int(got.stdout) - parse_cast_int(before.stdout)
    except ValueError:
        return (["unparsable-balance"], 0.0)
    fee = max(0.0, (_PROBE - delta) / _PROBE * 100.0)
    return ([], fee)


def probe_mint(endpoint: str, token: str) -> list[str]:
    """Eth_call an open mint from a stranger; success means mintable."""
    stranger = "0x0000000000000000000000000000000000000042"
    result = run_command(
        cast_call_command(
            endpoint,
            token,
            "mint(address,uint256)",
            [ANVIL_DEV_ADDRESS, "1"],
            sender=stranger,
        )
    )
    return ["unlimited-mint-possible"] if result.returncode == 0 else []


def static_shape_signals(rpc: str, address: str) -> list[str]:
    """Selector-shape evidence when the fork cannot boot (free archive caps)."""
    try:
        code = jsonrpc(SHARED_TRANSPORT, rpc, "eth_getCode", [address, "latest"])
    except RuntimeError:
        return []
    if not isinstance(code, str):
        return []
    return tax_gate_flags(set(extract_selectors(code)))


def evm_honeypot_data(address: str, rpc: str) -> EvmHoneypotReport:
    """Fork mainnet state and probe transfer/fee/mint behaviour empirically."""
    cm = fork(FORK_PORT, rpc)
    try:
        endpoint = cm.__enter__()
    except (RuntimeError, httpx.HTTPError):
        signals = ["fork-unavailable", *static_shape_signals(rpc, address)]
        return EvmHoneypotReport(
            address=address,
            verdict=evm_verdict(signals, 0.0),
            signals=tuple(signals),
        )
    slot = -1
    try:
        jsonrpc(
            SHARED_TRANSPORT,
            endpoint,
            "anvil_setBalance",
            [ANVIL_DEV_ADDRESS, DEV_FUND_WEI],
        )
        slot, _key = find_balance_slot(endpoint, address, ANVIL_DEV_ADDRESS)
        if slot < 0:
            signals = [
                "balance-slot-not-found",
                *probe_mint(endpoint, address),
                *probe_donation(endpoint, address),
            ]
            fee = 0.0
        else:
            transfer_signals, fee = probe_transfer(endpoint, address)
            signals = [
                *transfer_signals,
                *probe_mint(endpoint, address),
                *probe_donation(endpoint, address),
            ]
            if "fork-unavailable" in signals:
                signals += static_shape_signals(rpc, address)
    except (RuntimeError, httpx.HTTPError):
        signals = ["fork-unavailable", *static_shape_signals(rpc, address)]
        fee = 0.0
    finally:
        cm.__exit__(None, None, None)
    return EvmHoneypotReport(
        address=address,
        verdict=evm_verdict(signals, fee),
        signals=tuple(signals),
        fee_pct=round(fee, 4),
        balances_slot=slot,
    )


def evm_honeypot_report(kwargs: dict[str, Any]) -> EvmHoneypotReport:
    """Build the fork-probe report from CLI kwargs (shared by text and JSON)."""
    rpc = rpc_for(kwargs)
    if not rpc:
        raise ValueError("EVM honeypot needs --rpc (fork source)")
    return evm_honeypot_data(str(kwargs["token"]), rpc)


def _honeypot_evm(kwargs: dict[str, Any]) -> str:
    """Render the EVM honeypot probe verdict for a token."""
    return evm_honeypot_report(kwargs).render_markdown()


HONEYPOT_EVM_OPERATIONS: dict[str, Any] = {"honeypot-evm": _honeypot_evm}
