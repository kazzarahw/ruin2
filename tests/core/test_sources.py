"""Tests for the pure verified-source parsers."""

from __future__ import annotations

import json

from ruin.core.sources import (
    etherscan_source,
    explorer_url,
    language_for,
    sourcify_source,
    split_bundle,
)


def test_language_for_suffixes() -> None:
    assert language_for("Vault.sol") == "Solidity"
    assert language_for("token.vy") == "Vyper"
    assert language_for("lib.rs") == "Rust"
    assert language_for("notes.txt") == "unknown"


def test_sourcify_v2_picks_largest_contract() -> None:
    doc = {
        "sources": {
            "Small.sol": {"content": "pragma solidity ^0.8;"},
            "Big.sol": {"content": "pragma solidity ^0.8;" + "x" * 200},
        },
        "metadata": {
            "compiler": "solc",
            "settings": {"remappings": [":@oz/=lib/oz/", "broken", 7]},
        },
    }
    name, text, language, remappings, _version = sourcify_source(doc)
    assert name == "Big.sol"
    assert language == "Solidity"
    assert len(text) > 100
    assert remappings == ("@oz/=lib/oz/",)


def test_sourcify_v2_keeps_every_contract_file() -> None:
    doc = {
        "sources": {
            "Small.sol": {"content": "library Small {}"},
            "Big.sol": {"content": "contract Big {}" + "x" * 200},
            "notes.txt": {"content": "ignore me"},
        }
    }
    _, text, _, _, _ = sourcify_source(doc)
    assert "// ==== Big.sol ====" in text
    assert "// ==== Small.sol ====" in text
    assert "library Small {}" in text
    assert "ignore me" not in text
    assert text.index("Big.sol") < text.index("Small.sol")


def test_sourcify_v2_skips_non_contract_entries() -> None:
    doc = {"sources": {"notes.txt": {"content": "hello"}}}
    assert sourcify_source(doc) == ("", "", "", (), "")


def test_sourcify_no_sources() -> None:
    assert sourcify_source({"sources": {}}) == ("", "", "", (), "")
    assert sourcify_source({"match": None}) == ("", "", "", (), "")


def test_sourcify_bad_input() -> None:
    assert sourcify_source("nope") == ("", "", "", (), "")


def test_sourcify_remappings_missing_or_malformed() -> None:
    no_meta = {"sources": {"A.sol": {"content": "contract A {}"}}}
    assert sourcify_source(no_meta)[3] == ()
    bad = {
        "sources": {"A.sol": {"content": "contract A {}"}},
        "metadata": {"settings": {"remappings": "=empty"}},
    }
    assert sourcify_source(bad)[3] == ()


def test_etherscan_plain_source() -> None:
    doc = {
        "result": [
            {
                "ContractName": "Token",
                "SourceCode": "pragma solidity;",
                "Compiler": "solc",
            }
        ]
    }
    name, text, language, url = etherscan_source(doc, "0xabc", 1)
    assert name == "Token"
    assert text == "pragma solidity;"
    assert language == "Solidity"
    assert url == "https://etherscan.io/address/0xabc"


def test_etherscan_standard_json_wrapped() -> None:
    inner = json.dumps(
        {
            "sources": {
                "A.sol": {"content": "contract A {}"},
                "B.sol": {"content": "contract B {}" + "y" * 100},
            }
        }
    )
    doc = {
        "result": [
            {
                "ContractName": "Wrap",
                "SourceCode": "{{" + inner + "}}",
                "Compiler": "solc",
            }
        ]
    }
    name, text, language, _ = etherscan_source(doc, "0xabc", 1)
    assert name == "Wrap"
    assert "contract B" in text
    assert language == "Solidity"


def test_etherscan_vyper_compiler() -> None:
    doc = {
        "result": [
            {"ContractName": "V", "SourceCode": "# @dev", "Compiler": "vyper 0.3"}
        ]
    }
    _, _, language, _ = etherscan_source(doc, "0xabc", 1)
    assert language == "Vyper"


def test_etherscan_empty() -> None:
    assert etherscan_source({}, "0xabc", 1) == ("", "", "", "")


def test_split_bundle_roundtrip() -> None:
    doc = {
        "sources": {
            "src/A.sol": {"content": "contract A {}"},
            "src/B.sol": {"content": "contract B {}" + "y" * 200},
        }
    }
    _, text, _, _, _ = sourcify_source(doc)
    pairs = split_bundle(text)
    paths = [path for path, _ in pairs]
    assert "src/B.sol" in paths
    assert "src/A.sol" in paths
    bodies = dict(pairs)
    assert bodies["src/A.sol"] == "contract A {}"


def test_split_bundle_drops_unsafe_paths() -> None:
    text = "// ==== ../evil.sol ====\ncontract E {}\n\n// ==== /abs.sol ====\nX"
    assert split_bundle(text) == []


def test_explorer_url_known_and_unknown() -> None:
    assert explorer_url("0xabc", 1) == "https://etherscan.io/address/0xabc"
    assert explorer_url("0xabc", 8453) == "https://basescan.org/address/0xabc"
    assert explorer_url("0xabc", 999999) == ""


def test_sourcify_compiler_version_extracted() -> None:
    doc = {
        "metadata": {"compiler": {"version": "0.8.28"}},
        "sources": {"A.sol": {"content": "contract A {}"}},
    }
    assert sourcify_source(doc)[4] == "0.8.28"


def test_sourcify_compiler_version_absent_is_empty() -> None:
    doc = {
        "metadata": {"compiler": "solc"},
        "sources": {"A.sol": {"content": "contract A {}"}},
    }
    assert sourcify_source(doc)[4] == ""
