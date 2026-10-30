"""Tests for verified-source ingestion with an injected transport."""

from __future__ import annotations

from ruin.core.enums import Chain
from ruin.services.sources import fetch_source


class FakeTransport:
    """A transport that returns canned JSON keyed by URL."""

    def __init__(self, urls: dict[str, object]) -> None:
        """Store canned responses keyed by exact URL."""
        self.urls = urls

    def post_json(self, _url: str, _payload: dict[str, object]) -> dict[str, object]:
        """Return an empty JSON-RPC envelope."""
        return {"result": None}

    def get_json(self, url: str, /) -> object:
        """Return the canned JSON body for a URL."""
        if url not in self.urls:
            raise RuntimeError(f"missing {url}")
        return self.urls[url]

    def get_text(self, _url: str, /) -> str:
        """Return empty text."""
        return ""


ADDR = "0x" + "a" * 40
FULL = f"https://sourcify.dev/server/v2/contract/1/{ADDR}?fields=sources,metadata"


def test_sourcify_full_match() -> None:
    doc = {
        "sources": {"Vault.sol": {"content": "pragma solidity;"}},
        "metadata": {"settings": {"remappings": [":@oz/=lib/oz/"]}},
    }
    transport = FakeTransport({FULL: doc})
    info = fetch_source(ADDR, transport=transport)
    assert info.verified is True
    assert info.name == "Vault.sol"
    assert info.language == "Solidity"
    assert info.remappings == ("@oz/=lib/oz/",)


def test_sourcify_miss_falls_back_to_etherscan() -> None:
    api = (
        "https://api.etherscan.io/v2/api?chainid=1&module=contract"
        f"&action=getsourcecode&address={ADDR}&apikey=KEY"
    )
    doc = {
        "result": [
            {"ContractName": "T", "SourceCode": "pragma solidity;", "Compiler": "solc"}
        ]
    }
    transport = FakeTransport({api: doc})
    info = fetch_source(ADDR, api_key="KEY", transport=transport)
    assert info.verified is True
    assert info.name == "T"


def test_all_miss_returns_unverified() -> None:
    transport = FakeTransport({})
    info = fetch_source(ADDR, transport=transport)
    assert info.verified is False


def test_non_evm_delegates_to_adapter() -> None:
    sol = "So11111111111111111111111111111111111111112"
    status = "https://verify.osec.io/status/" + sol
    info = fetch_source(
        sol,
        chain=Chain.SOLANA,
        transport=FakeTransport({status: {"is_verified": False}}),
    )
    assert info.chain is Chain.SOLANA
    assert info.verified is False
