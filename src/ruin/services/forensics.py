"""Forensics services for ``ruin``."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from ruin.core.forensics import (
    LogEntry,
    LogScan,
    TransactionTrace,
    flatten_call_trace,
)
from ruin.core.replay import Timeline
from ruin.services.http import resolve_selectors
from ruin.services.rpc import SHARED_TRANSPORT, jsonrpc

if TYPE_CHECKING:
    from subprocess import CompletedProcess

from ruin.services.subprocesses import cast_logs_command, run_command


def _require_output(name: str, process: CompletedProcess[str]) -> None:
    """Raise when a cast command fails without producing stdout."""
    if process.returncode != 0 and not process.stdout.strip():
        tail = process.stderr.strip()[-200:]
        raise RuntimeError(f"{name} failed (exit {process.returncode}): {tail}")


_MIN_PARTS = 4
_MIN_FIELDS = 2
_MIN_INDEXED = 3
_LOG_CHUNK_BLOCKS = 100


_SELECTOR_TAIL = re.compile(r" 0x([0-9a-fA-F]{8})(?: \[reverted\])?$")


def _annotate_selectors(steps: list[str]) -> list[str]:
    """Append resolved function signatures after trailing selector tokens."""
    found = {
        match.group(1).lower()
        for line in steps
        if (match := _SELECTOR_TAIL.search(line))
    }
    if not found:
        return steps
    resolved = resolve_selectors(sorted(found)[:40])
    annotated: list[str] = []
    for line in steps:
        match = _SELECTOR_TAIL.search(line)
        sig = resolved.get(match.group(1).lower(), "") if match else ""
        if match is not None and sig:
            end = match.end(1)
            annotated.append(f"{line[:end]} {sig}{line[end:]}")
        else:
            annotated.append(line)
    return annotated


def trace_transaction(tx_hash: str, rpc: str) -> TransactionTrace:
    """Trace a transaction: callTracer when the RPC offers it, else tx fields.

    Public RPCs frequently lack debug_traceTransaction; in that case the raw
    transaction fields are returned with a note saying why.
    """
    try:
        result = jsonrpc(
            SHARED_TRANSPORT,
            rpc,
            "debug_traceTransaction",
            [tx_hash, {"tracer": "callTracer"}],
        )
    except RuntimeError:
        result = None
    if isinstance(result, dict) and result.get("from"):
        steps = _annotate_selectors(
            flatten_call_trace(cast("dict[str, object]", result))
        )
        return TransactionTrace(tx_hash=tx_hash, steps=steps)
    process = run_command(["cast", "tx", tx_hash, "--rpc-url", rpc])
    _require_output("cast tx", process)
    steps = [line.strip() for line in process.stdout.splitlines() if line.strip()]
    return TransactionTrace(
        tx_hash=tx_hash,
        steps=steps,
        note="callTracer unavailable on this RPC; showing raw transaction fields",
    )


def scan_logs(address: str, rpc: str, from_block: int, to_block: int) -> LogScan:
    """Scan event logs for a contract over a block range.

    Args:
        address: Contract address to scan.
        rpc: RPC endpoint URL.
        from_block: Start block number.
        to_block: End block number.

    Returns:
        A LogScan with parsed entries.
    """
    entries: list[LogEntry] = []
    for lo, hi in _chunk_range(from_block, to_block):
        process = run_command(cast_logs_command(rpc, address, lo, hi), timeout=60.0)
        _require_output("cast logs", process)
        entries.extend(_parse_log_lines(address, process.stdout))
    return LogScan(
        address=address,
        from_block=from_block,
        to_block=to_block,
        entries=entries,
    )


def _chunk_range(from_block: int, to_block: int) -> list[tuple[int, int]]:
    """Split a block range into windows public RPCs accept for old blocks."""
    windows: list[tuple[int, int]] = []
    lo = from_block
    while lo <= to_block:
        hi = min(lo + _LOG_CHUNK_BLOCKS - 1, to_block)
        windows.append((lo, hi))
        lo = hi + 1
    return windows


def _parse_log_lines(address: str, stdout: str) -> list[LogEntry]:
    """Parse cast logs stdout rows into log entries."""
    entries: list[LogEntry] = []
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("block"):
            continue
        parts = stripped.split()
        if len(parts) >= _MIN_PARTS:
            entries.append(
                LogEntry(
                    address=address,
                    block=int(parts[0]) if parts[0].isdigit() else 0,
                    tx_hash=parts[1] if len(parts) > 1 else "",
                    event_signature=parts[2] if len(parts) > _MIN_FIELDS else "",
                    indexed=parts[3:] if len(parts) > _MIN_INDEXED else [],
                )
            )
    return entries


def replay_transaction(
    tx_hash: str,
    address: str,
    rpc: str,
    from_block: int,
    to_block: int,
) -> Timeline:
    """Replay a transaction into a fund-flow timeline.

    Combines the call trace for the transaction with the contract's event logs
    over the block range, so a post-mortem can read as one ordered story.

    Args:
        tx_hash: The transaction to trace.
        address: The contract whose events to scan.
        rpc: The RPC endpoint URL.
        from_block: Start block number.
        to_block: End block number.

    Returns:
        A Timeline combining trace steps and event rows.
    """
    trace = trace_transaction(tx_hash, rpc)
    scan = scan_logs(address, rpc, from_block, to_block)
    events = [
        (entry.block, entry.tx_hash, entry.event_signature) for entry in scan.entries
    ]
    return Timeline(
        tx_hash=tx_hash,
        address=address,
        from_block=from_block,
        to_block=to_block,
        steps=trace.steps,
        events=events,
        note=trace.note,
    )
