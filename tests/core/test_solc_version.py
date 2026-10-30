"""Tests for solc pragma version detection."""

from ruin.core.solc import version_preference


def test_exact_pinned_pragma() -> None:
    text = "pragma solidity =0.5.16;"
    assert version_preference(text) == ("exact", "0.5.16")


def test_caret_pragma_yields_family() -> None:
    text = "pragma solidity ^0.8.19;"
    assert version_preference(text) == ("family", "0.8")


def test_no_pragma() -> None:
    assert version_preference("contract A {}") == ("none", "")
