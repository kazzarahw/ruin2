"""Anvil fork lifecycle shared by the fork-backed operations."""

from __future__ import annotations

import subprocess
import time

import httpx

from ruin.services.subprocesses import anvil_command, run_command

FORK_PORT = 8545


def wait_for_ready(endpoint: str) -> None:
    """Wait until endpoint answers a block-number query."""
    for _ in range(50):
        process = run_command(["cast", "block-number", "--rpc-url", endpoint])
        if process.returncode == 0:
            return
        time.sleep(0.1)
    raise RuntimeError(f"endpoint not ready: {endpoint}")


class _ForkHandle:
    """Owns an anvil fork: boots it on enter, kills it on exit."""

    def __init__(
        self, port: int, rpc: str, fork_block: int | None, retries: int
    ) -> None:
        """Record the boot parameters; nothing spawns until ``__enter__``."""
        self._port = port
        self._rpc = rpc
        self._fork_block = fork_block
        self._retries = retries
        self._proc: subprocess.Popen[bytes] | None = None

    def __enter__(self) -> str:
        """Boot the fork and return its local endpoint.

        Kills the anvil process and retries a fresh boot when the endpoint
        never answers, up to ``retries`` extra attempts.

        Raises:
            RuntimeError: If the endpoint is still not ready after all tries.
        """
        endpoint = f"http://127.0.0.1:{self._port}"
        attempt = 0
        while True:
            proc = subprocess.Popen(
                anvil_command(self._port, self._rpc, fork_block=self._fork_block),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                wait_for_ready(endpoint)
            except (RuntimeError, httpx.HTTPError):
                proc.kill()
                proc.wait()
                if attempt >= self._retries:
                    raise
                attempt += 1
                continue
            self._proc = proc
            return endpoint

    def __exit__(self, *_exc: object) -> None:
        """Kill the fork process if it is still running."""
        if self._proc is not None:
            self._proc.kill()
            self._proc.wait()


def fork(
    port: int,
    rpc: str,
    *,
    fork_block: int | None = None,
    retries: int = 1,
) -> _ForkHandle:
    """Return a context manager that forks ``rpc`` on ``port``.

    Args:
        port: Local port the anvil fork binds to.
        rpc: Upstream RPC the fork follows.
        fork_block: Optional pinned fork block number.
        retries: Extra boot attempts when the endpoint never answers.
    """
    return _ForkHandle(port, rpc, fork_block, retries)
