"""End-to-end integration test using a live anvil instance."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "foundry"
ANVIL_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


def _require_tools() -> None:
    if os.getenv("RUIN_INTEGRATION") != "1":
        pytest.skip("RUIN_INTEGRATION not set")
    for tool in ("anvil", "cast", "forge"):
        if shutil.which(tool) is None:
            pytest.skip(f"{tool} not installed")


def _wait_for_anvil(rpc: str) -> None:
    for _ in range(50):
        result = subprocess.run(
            ["cast", "block-number", "--rpc-url", rpc],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return
        time.sleep(0.1)
    raise RuntimeError("anvil did not start")


def _deploy(contract: str, rpc: str, *constructor_args: str) -> str:
    command = [
        "forge",
        "create",
        contract,
        "--broadcast",
        "--private-key",
        ANVIL_KEY,
        "--rpc-url",
        rpc,
    ]
    if constructor_args:
        args_file = FIXTURE / ".constructor-args.txt"
        args_file.write_text("\n".join(constructor_args) + "\n", encoding="utf-8")
        command += ["--constructor-args-path", str(args_file)]
    result = subprocess.run(
        command,
        cwd=FIXTURE,
        check=True,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.splitlines():
        if "Deployed to:" in line:
            return line.split("Deployed to:")[1].strip()
    raise RuntimeError(f"deploy failed: {result.stdout}\n{result.stderr}")


def test_end_to_end_drain(tmp_path: Path) -> None:
    _require_tools()
    rpc = "http://127.0.0.1:8545"
    anvil = subprocess.Popen(
        ["anvil", "--port", "8545"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_anvil(rpc)
        token = _deploy("src/Token.sol:Token", rpc)
        vault = _deploy("src/Vault.sol:Vault", rpc, token)

        # Fund the vault with 1000 tokens.
        subprocess.run(
            [
                "cast",
                "send",
                token,
                "transfer(address,uint256)",
                vault,
                "1000",
                "--private-key",
                ANVIL_KEY,
                "--rpc-url",
                rpc,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        recon = tmp_path / "recon.json"
        recon.write_text(
            json.dumps(
                {"tvl_asset": token, "contracts": [{"address": vault, "tvl": 1000}]}
            ),
            encoding="utf-8",
        )

        env = dict(os.environ)
        env["TOKEN"] = token
        env["VAULT"] = vault
        env["FOUNDRY_RPC_URL"] = rpc
        env["ETH_RPC_URL"] = rpc

        result = subprocess.run(
            [
                "uv",
                "run",
                "ruin",
                "run",
                str(recon),
                "--name",
                "Vault",
                "--forge-test",
                "script/Drain.s.sol",
                "--method",
                "drain",
                "--rpc",
                rpc,
                "--mode",
                "own",
            ],
            cwd=FIXTURE,
            check=True,
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )
        assert "Proof of Drain" in result.stdout
        assert "units of" in result.stdout
    finally:
        anvil.kill()
        anvil.wait()
