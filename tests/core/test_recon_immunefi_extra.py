"""Extra Immunefi scope tests."""

import json

import pytest

from ruin.core.recon import parse_immunefi_scope


def test_immunefi_non_evm_skipped() -> None:
    doc = {
        "assets": [
            {
                "type": "smart_contract",
                "name": "X",
                "url": "https://example.com",
                "chain": "Solana",
            }
        ]
    }
    assert parse_immunefi_scope(json.dumps(doc)) == []


def test_immunefi_invalid() -> None:
    with pytest.raises(ValueError, match=r".*"):
        parse_immunefi_scope("not json")
    with pytest.raises(TypeError, match=r".*"):
        parse_immunefi_scope(json.dumps([]))
