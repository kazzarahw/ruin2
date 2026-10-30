"""Live Slither integration test."""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.integration

FIXTURE = "tests/fixtures/foundry/src/Vault.sol"


def test_slither_live() -> None:
    if os.getenv("RUIN_INTEGRATION") != "1":
        pytest.skip("RUIN_INTEGRATION not set")
    if shutil.which("slither") is None:
        pytest.skip("slither not installed")
    result = subprocess.run(
        ["slither", FIXTURE, "--json", "-"],
        check=False,
        capture_output=True,
        text=True,
    )
    # Slither may return non-zero for findings; output should be JSON.
    assert "{" in result.stdout
