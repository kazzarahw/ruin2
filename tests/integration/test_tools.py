"""Opt-in integration tests for external tools."""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.integration


def _require(env: str, tool: str) -> None:
    if os.getenv(env) != "1":
        pytest.skip(f"{env} not set")
    if shutil.which(tool) is None:
        pytest.skip(f"{tool} not installed")


@pytest.mark.skipif(os.getenv("RUIN_INTEGRATION") != "1", reason="opt-in")
def test_anvil_version() -> None:
    _require("RUIN_INTEGRATION", "anvil")
    result = subprocess.run(
        ["anvil", "--version"], check=False, capture_output=True, text=True
    )
    assert result.returncode == 0


@pytest.mark.skipif(os.getenv("RUIN_INTEGRATION") != "1", reason="opt-in")
def test_cast_version() -> None:
    _require("RUIN_INTEGRATION", "cast")
    result = subprocess.run(
        ["cast", "--version"], check=False, capture_output=True, text=True
    )
    assert result.returncode == 0


@pytest.mark.skipif(os.getenv("RUIN_INTEGRATION") != "1", reason="opt-in")
def test_forge_version() -> None:
    _require("RUIN_INTEGRATION", "forge")
    result = subprocess.run(
        ["forge", "--version"], check=False, capture_output=True, text=True
    )
    assert result.returncode == 0


@pytest.mark.skipif(os.getenv("RUIN_INTEGRATION") != "1", reason="opt-in")
def test_slither_version() -> None:
    _require("RUIN_INTEGRATION", "slither")
    result = subprocess.run(
        ["slither", "--version"], check=False, capture_output=True, text=True
    )
    assert result.returncode == 0
