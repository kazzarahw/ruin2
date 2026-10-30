"""Subprocess helpers for ``ruin``."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_PRIVATE_KEY = (
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
)
ANVIL_DEV_ADDRESS = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
DEV_FUND_WEI = "0x8ac7230489e80000"


def parse_cast_int(text: str) -> int:
    """Parse cast integer output (``123.456000`` or ``123 [123e3]`` forms)."""
    cleaned = text.strip().split(" [")[0].replace(",", "").replace("_", "")
    if cleaned in ("", "0x"):
        return 0
    if cleaned.startswith("0x"):
        return int(cleaned, 16)
    if "." not in cleaned:
        return int(cleaned or "0")
    whole, frac = cleaned.split(".", 1)
    return int(whole + frac.rstrip("0") if frac.rstrip("0") else whole or "0")


def run_command(
    argv: Sequence[str], *, timeout: float = 30.0
) -> subprocess.CompletedProcess[str]:
    """Run a command and return its completed process."""
    try:
        return subprocess.run(
            list(argv),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"command timed out: {argv}") from error


def anvil_command(
    port: int, source: str, *, fork_block: int | None = None
) -> list[str]:
    """Build an anvil fork command."""
    cmd = ["anvil", "--port", str(port), "--fork-url", source]
    if fork_block is not None:
        cmd.extend(["--fork-block-number", str(fork_block)])
    return cmd


def cast_balance_command(endpoint: str, asset: str, wallet: str) -> list[str]:
    """Build a cast balance command."""
    return ["cast", "call", asset, "balanceOf(address)", wallet, "--rpc-url", endpoint]


def cast_native_balance_command(endpoint: str, wallet: str) -> list[str]:
    """Build a cast native-ETH balance command."""
    return ["cast", "balance", wallet, "--rpc-url", endpoint]


def cast_storage_command(endpoint: str, address: str, slot: str) -> list[str]:
    """Build a cast storage-slot read command."""
    return ["cast", "storage", address, slot, "--rpc-url", endpoint]


def cast_logs_command(
    endpoint: str, address: str, from_block: int, to_block: int
) -> list[str]:
    """Build a cast logs command for a contract over a block range."""
    return [
        "cast",
        "logs",
        "--address",
        address,
        "--from-block",
        str(from_block),
        "--to-block",
        str(to_block),
        "--rpc-url",
        endpoint,
    ]


def forge_script_command(
    endpoint: str, script: str, *, private_key: str = DEFAULT_PRIVATE_KEY
) -> list[str]:
    """Build a forge script command."""
    return [
        "forge",
        "script",
        script,
        "--broadcast",
        "--private-key",
        private_key,
        "--rpc-url",
        endpoint,
    ]


def cast_code_command(endpoint: str, address: str) -> list[str]:
    """Build a cast deployed-bytecode read command."""
    return ["cast", "code", address, "--rpc-url", endpoint]


def slither_command(source: str, solc: str = "") -> list[str]:
    """Build a slither command, optionally pinning the compiler binary."""
    cmd = ["slither", source, "--json", "-"]
    if solc:
        cmd += ["--solc", solc]
    return cmd


def cast_call_command(
    endpoint: str,
    target: str,
    signature: str,
    args: list[str],
    *,
    sender: str = "",
) -> list[str]:
    """Build a cast call command with an optional sender override."""
    cmd = ["cast", "call", target, signature, *args, "--rpc-url", endpoint]
    if sender:
        cmd += ["--from", sender]
    return cmd


def cast_send_command(
    endpoint: str,
    target: str,
    signature: str,
    args: list[str],
    private_key: str,
) -> list[str]:
    """Build a broadcast cast send command signed with a private key."""
    return [
        "cast",
        "send",
        target,
        signature,
        *args,
        "--private-key",
        private_key,
        "--rpc-url",
        endpoint,
    ]


def cast_index_command(key_type: str, key: str, base_slot: int) -> list[str]:
    """Build a cast index command (mapping slot derivation)."""
    return ["cast", "index", key_type, key, f"0x{base_slot:x}"]
