"""Tests for protocols."""

import json

from ruin.core.protocols import parse_protocol, parse_protocols


def test_parse_protocols() -> None:
    data = [
        {"name": "A", "slug": "a", "tvl": 1.0, "chain": "Ethereum", "category": "Defi"}
    ]
    result = parse_protocols(json.dumps(data))
    assert len(result) == 1


def test_parse_protocol() -> None:
    data = {
        "name": "A",
        "category": "Defi",
        "chains": ["Ethereum"],
        "address": "0x" + "1" * 40,
    }
    detail = parse_protocol(json.dumps(data))
    assert detail.name == "A"
