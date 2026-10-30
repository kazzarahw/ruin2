"""Tests for the filesystem half of the solc compiler-preference lookup."""

from pathlib import Path

from ruin.services.solc import tree_preference


def test_tree_preference_picks_majority_family(tmp_path: Path) -> None:
    (tmp_path / "a.sol").write_text("pragma solidity ^0.8.20;", encoding="utf-8")
    (tmp_path / "b.sol").write_text("pragma solidity ^0.8.28;", encoding="utf-8")
    (tmp_path / "c.sol").write_text("pragma solidity =0.7.6;", encoding="utf-8")
    assert tree_preference(tmp_path) == ("family", "0.8")


def test_tree_preference_exact_when_majority_pinned(tmp_path: Path) -> None:
    (tmp_path / "a.sol").write_text("pragma solidity =0.8.28;", encoding="utf-8")
    (tmp_path / "b.sol").write_text("pragma solidity =0.8.28;", encoding="utf-8")
    (tmp_path / "c.sol").write_text("pragma solidity ^0.8.10;", encoding="utf-8")
    assert tree_preference(tmp_path) == ("exact", "0.8.28")


def test_tree_preference_empty_tree_is_none(tmp_path: Path) -> None:
    assert tree_preference(tmp_path) == ("none", "")
