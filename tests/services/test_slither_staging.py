"""Tests for pragma-compatible staging of mixed trees before slither."""

import subprocess
from pathlib import Path
from typing import Any

import pytest

from ruin.services import slither as svc


def test_mixed_tree_is_staged_to_compatible_subset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "Vault.sol").write_text("pragma solidity ^0.8.20;", encoding="utf-8")
    (tmp_path / "Old.sol").write_text("pragma solidity =0.7.6;", encoding="utf-8")
    nested = tmp_path / "lib" / "dep"
    nested.mkdir(parents=True)
    (nested / "Vault.sol").write_text("pragma solidity ^0.8.28;", encoding="utf-8")
    staged: list[str] = []

    def _fake_run(cmd: list[str], timeout: float = 60.0) -> Any:
        staged.append(cmd[1])
        return subprocess.CompletedProcess(cmd, 0, "[]", "")

    monkeypatch.setattr(svc, "pick_solc", lambda _src: "/x/.svm/0.8.37/solc-0.8.37")
    monkeypatch.setattr(svc, "run_command", _fake_run)
    svc.run_slither(tmp_path)
    root = Path(staged[0])
    names = sorted(p.name for p in root.rglob("*.sol"))
    assert names == ["Vault.sol", "Vault.sol"]
    assert not list(root.rglob("Old.sol"))
