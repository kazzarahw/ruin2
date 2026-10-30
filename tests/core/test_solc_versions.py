"""Tests for pragma range checking and tree-wide compiler preference."""

from ruin.core.solc import preference_from_texts, version_satisfied


def test_version_satisfied_honours_exact_and_caret() -> None:
    text = "pragma solidity =0.7.6;\npragma solidity ^0.8.10;"
    assert version_satisfied("pragma solidity ^0.8.10;", "0.8.37")
    assert not version_satisfied(text, "0.8.37")
    assert version_satisfied("pragma solidity =0.7.6;", "0.7.6")


def test_version_satisfied_handles_ranges_and_or_clauses() -> None:
    assert version_satisfied("pragma solidity >=0.8.0 <0.9.0;", "0.8.28")
    assert not version_satisfied("pragma solidity >=0.8.0 <0.9.0;", "0.9.1")
    assert version_satisfied("pragma solidity ^0.7.6 || ^0.8.0;", "0.8.37")


def test_caret_zero_major_allows_minor_bump() -> None:
    assert version_satisfied("pragma solidity ^0.8.10;", "0.8.11")
    assert not version_satisfied("pragma solidity ^0.8.10;", "0.8.9")


def test_preference_from_texts_picks_majority_family() -> None:
    texts = [
        "pragma solidity ^0.8.20;",
        "pragma solidity ^0.8.28;",
        "pragma solidity =0.7.6;",
    ]
    assert preference_from_texts(texts) == ("family", "0.8")


def test_preference_from_texts_exact_when_majority_pinned() -> None:
    texts = [
        "pragma solidity =0.8.28;",
        "pragma solidity =0.8.28;",
        "pragma solidity ^0.8.10;",
    ]
    assert preference_from_texts(texts) == ("exact", "0.8.28")


def test_preference_from_texts_empty_tree_is_none() -> None:
    assert preference_from_texts([]) == ("none", "")
