"""Foundry runner service for ``ruin``."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from ruin.core.decode import decode_uint
from ruin.core.domain import DrainProof
from ruin.core.enums import TargetMode
from ruin.core.ids import ContractId, RpcUrl
from ruin.core.runs import RunConfig, RunOutput, SlotDiff
from ruin.services.fork import FORK_PORT, fork, wait_for_ready
from ruin.services.subprocesses import (
    DEFAULT_PRIVATE_KEY,
    cast_balance_command,
    cast_native_balance_command,
    cast_storage_command,
    forge_script_command,
    run_command,
)


class FoundryRunner:
    """A runner that executes a PoC using the Foundry toolchain."""

    def run(self, config: RunConfig) -> RunOutput:
        """Run the configured PoC against its endpoint."""
        if not config.target.contracts:
            raise ValueError("target has no in-scope contract to measure")
        if not config.poc.is_well_formed():
            raise ValueError("poc is not well-formed")
        key = config.private_key or DEFAULT_PRIVATE_KEY
        if config.target.mode == TargetMode.RESEARCH:
            with fork(
                FORK_PORT,
                config.rpc_url.as_str(),
                fork_block=config.fork_block,
            ) as endpoint:
                return self._measure(config, key, endpoint)
        return self._measure(config, key, config.rpc_url.as_str())

    def _measure(self, config: RunConfig, key: str, endpoint: str) -> RunOutput:
        """Measure a run against ``endpoint`` in a fresh broadcast dir."""
        broadcast_dir = tempfile.mkdtemp(prefix="ruin-broadcast-")
        try:
            return _measure_run(
                endpoint=endpoint, config=config, key=key, broadcast_dir=broadcast_dir
            )
        finally:
            shutil.rmtree(broadcast_dir, ignore_errors=True)


def _measure_run(
    endpoint: str, config: RunConfig, key: str, *, broadcast_dir: str
) -> RunOutput:
    """Measure a run and return a RunOutput."""
    wait_for_ready(endpoint)
    wallet = config.target.contracts[0]
    asset = (
        config.poc.expected_drain.asset
        if config.poc.expected_drain is not None
        else wallet
    )
    wallet_str = wallet.as_str()
    asset_id = asset if isinstance(asset, ContractId) else ContractId.new(str(asset))

    before = _read_state(endpoint, wallet_str, config)
    process = subprocess.run(
        forge_script_command(endpoint, config.poc.forge_test, private_key=key),
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "FOUNDRY_RPC_URL": endpoint,
            "ETH_RPC_URL": endpoint,
            "FOUNDRY_BROADCAST": broadcast_dir,
        },
    )
    succeeded = process.returncode == 0
    after = _read_state(endpoint, wallet_str, config)

    drain = DrainProof.measure(config.poc.method, asset_id, before.erc20, after.erc20)
    all_drains = _build_drains(config, asset_id, drain, before, after)
    slot_diffs = _build_slot_diffs(before.slots, after.slots)
    summary = _build_summary(all_drains) if succeeded else _failure_summary(process)

    return RunOutput(
        rpc_url=RpcUrl.new(endpoint),
        succeeded=succeeded,
        drain=drain,
        summary=summary,
        all_drains=all_drains,
        slot_diffs=slot_diffs,
    )


class _State:
    """Measured state snapshot."""

    __slots__ = ("erc20", "native", "slots", "tokens")

    def __init__(
        self,
        erc20: int,
        native: int,
        tokens: dict[str, int],
        slots: dict[str, str],
    ) -> None:
        """Initialize the state snapshot."""
        self.erc20 = erc20
        self.native = native
        self.tokens = tokens
        self.slots = slots


def _read_state(endpoint: str, wallet: str, config: RunConfig) -> _State:
    """Read all measured state before or after a run."""
    asset = (
        config.poc.expected_drain.asset
        if config.poc.expected_drain is not None
        else config.target.contracts[0]
    )
    asset_str = asset.as_str() if isinstance(asset, ContractId) else str(asset)
    return _State(
        erc20=_read_balance(endpoint, asset_str, wallet),
        native=_read_native(endpoint, wallet) if config.measure_native else 0,
        tokens=_measure_tokens(endpoint, wallet, config.measure_tokens),
        slots=_measure_slots(endpoint, wallet, config.measure_slots),
    )


def _build_drains(
    config: RunConfig,
    asset_id: ContractId,
    primary: DrainProof | None,
    before: _State,
    after: _State,
) -> list[DrainProof]:
    """Collect all drain proofs from before/after state."""
    method = config.poc.method
    drains: list[DrainProof] = []
    if primary is not None:
        drains.append(primary)
    if config.measure_native and before.native > after.native:
        drains.append(
            DrainProof(
                method=method, asset=asset_id, amount=before.native - after.native
            )
        )
    for tok_addr, bv in before.tokens.items():
        av = after.tokens.get(tok_addr, bv)
        if bv > av:
            drains.append(
                DrainProof(
                    method=method,
                    asset=ContractId.new(tok_addr),
                    amount=bv - av,
                )
            )
    return drains


def _build_slot_diffs(before: dict[str, str], after: dict[str, str]) -> list[SlotDiff]:
    """Build SlotDiff list from before/after slot readings."""
    diffs: list[SlotDiff] = []
    for slot, bv in before.items():
        av = after.get(slot, bv)
        if bv != av:
            diffs.append(SlotDiff(slot=slot, before=bv, after=av))
    return diffs


def _failure_summary(process: subprocess.CompletedProcess[str]) -> str:
    """Build a summary naming the forge failure and its stderr tail."""
    tail = process.stderr.strip()[-200:]
    return f"forge script failed (exit {process.returncode}): {tail}"


def _build_summary(drains: list[DrainProof]) -> str:
    """Build a human-readable summary from drain proofs."""
    if not drains:
        return "no measurable drain on this run"
    parts = [f"drained {d.amount} units of {d.asset.as_str()}" for d in drains]
    return "; ".join(parts)


def _measure_tokens(
    endpoint: str, wallet: str, tokens: list[ContractId]
) -> dict[str, int]:
    """Read ERC20 balances for a list of tokens."""
    result: dict[str, int] = {}
    for tok in tokens:
        result[tok.as_str()] = _read_balance(endpoint, tok.as_str(), wallet)
    return result


def _measure_slots(endpoint: str, wallet: str, slots: list[str]) -> dict[str, str]:
    """Read storage slots for a wallet address."""
    result: dict[str, str] = {}
    for slot in slots:
        result[slot] = _read_storage(endpoint, wallet, slot)
    return result


def _read_balance(endpoint: str, asset: str, wallet: str) -> int:
    """Read a wallet's ERC20 balance of an asset."""
    process = run_command(cast_balance_command(endpoint, asset, wallet))
    stdout = process.stdout.strip()
    if stdout.startswith("0x"):
        return decode_uint(stdout.split()[0])
    try:
        return int(stdout)
    except ValueError as error:
        raise RuntimeError(f"cast bad number: {stdout}") from error


def _read_native(endpoint: str, wallet: str) -> int:
    """Read a wallet's native ETH balance in wei."""
    process = run_command(cast_native_balance_command(endpoint, wallet))
    stdout = process.stdout.strip()
    try:
        return int(stdout)
    except ValueError as error:
        raise RuntimeError(f"cast bad balance: {stdout}") from error


def _read_storage(endpoint: str, address: str, slot: str) -> str:
    """Read a single storage slot."""
    process = run_command(cast_storage_command(endpoint, address, slot))
    return process.stdout.strip() or "0x0"


# Runner is a Protocol; FoundryRunner satisfies it structurally.
