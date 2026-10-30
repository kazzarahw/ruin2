"""Tests for the infra review op and its JSON output."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ruin.services.operations import run_operation, run_operation_json

if TYPE_CHECKING:
    from pathlib import Path


def test_infra_op_text() -> None:
    text = run_operation("infra", {"name": "keeper"})
    assert "# Infra Review" in text
    assert "keeper" in text.lower()


def test_infra_op_json() -> None:
    data = run_operation_json("infra", {"name": "oracle-backend"})
    assert isinstance(data, dict)
    assert data.get("name") == "oracle-backend"
    checks = data.get("checks")
    assert isinstance(checks, list)
    assert checks


def test_infra_op_unknown_raises() -> None:
    with pytest.raises(ValueError, match="unknown infra template"):
        run_operation("infra", {"name": "zorp"})


def test_infra_op_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "keeper.md"
    result = run_operation("infra", {"name": "multisig", "out": str(out)})
    assert result.startswith("wrote")
    assert "multisig" in out.read_text(encoding="utf-8").lower()
