"""Tests for Immunefi scope parsing."""

import json

from ruin.core.recon import parse_immunefi_scope


def test_parse_immunefi_scope() -> None:
    doc = {
        "assets": [
            {
                "type": "smart_contract",
                "name": "Vault",
                "url": "https://etherscan.io/address/0x" + "1" * 40,
                "chain": "ETH",
            },
            {"type": "websites_and_applications", "url": "https://example.com"},
        ]
    }
    entries = parse_immunefi_scope(json.dumps(doc))
    assert len(entries) == 1
    assert entries[0].label == "Vault"
