"""Tests for the cold discovery fetcher with an injected transport."""

from typing import Any

import pytest

from ruin.core.cold import ColdThresholds
from ruin.core.protocols import ProtocolSummary
from ruin.services import cold as cold_service

ADDR = "0x" + "a" * 40
ADDR_B = "0x" + "b" * 40
NOW = 1_700_000_000


class FakeTransport:
    def __init__(self, urls: dict[str, object]) -> None:
        self.urls = urls

    def post_json(self, _url: str, _payload: dict[str, Any]) -> dict[str, Any]:
        return {"result": None}

    def get_json(self, url: str, /) -> object:
        if url not in self.urls:
            raise RuntimeError(f"missing {url}")
        return self.urls[url]

    def get_text(self, _url: str, /) -> str:
        return ""


def summary(name: str, tvl: int, **fields: int | str) -> ProtocolSummary:
    item = ProtocolSummary.new(name, name.lower(), tvl, ["Ethereum"], "Yield")
    item.address = str(fields.get("address", ADDR))
    item.listed_unix = int(fields.get("listed_unix", 0))
    item.audits = int(fields.get("audits", 0))
    if "chain" in fields:
        item.chains = [str(fields["chain"])]
    return item


def sourcify_hit(chain_id: int, address: str) -> dict[str, object]:
    tail = "?fields=sources,metadata"
    url = f"https://sourcify.dev/server/v2/contract/{chain_id}/{address}{tail}"
    return {url: {"sources": {"Vault.sol": {"content": "pragma solidity;"}}}}


def patch_feed(monkeypatch: pytest.MonkeyPatch, items: list[ProtocolSummary]) -> None:
    monkeypatch.setattr(cold_service, "fetch_protocols", lambda: list(items))
    monkeypatch.setattr(cold_service.time, "time", lambda: float(NOW))


def test_cold_candidates_drops_entries_below_the_floor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_feed(monkeypatch, [summary("Tiny", 10_000)])

    assert cold_service.cold_candidates(transport=FakeTransport({})) == []


def test_cold_candidates_drops_entries_without_an_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_feed(monkeypatch, [summary("NoAddr", 900_000, address="")])

    assert cold_service.cold_candidates(transport=FakeTransport({})) == []


def test_cold_candidates_ranks_the_young_unaudited_entry_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cold = summary("VaultX", 500_000, listed_unix=NOW - 10 * 86_400)
    warm = summary(
        "MegaLend",
        40_000_000,
        address=ADDR_B,
        listed_unix=NOW - 900 * 86_400,
        audits=2,
    )
    patch_feed(monkeypatch, [warm, cold])

    ranked = cold_service.cold_candidates(transport=FakeTransport({}))

    assert ranked[0].name == "VaultX"
    assert ranked[0].signals.age_days == 10
    assert ranked[1].signals.audited is True


def test_cold_candidates_marks_verified_on_a_sourcify_hit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_feed(monkeypatch, [summary("VaultX", 500_000)])

    transport = FakeTransport(sourcify_hit(1, ADDR))
    ranked = cold_service.cold_candidates(transport=transport)

    assert ranked[0].signals.verified is True


def test_cold_candidates_skips_the_probe_for_unmapped_chains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_feed(monkeypatch, [summary("SolVault", 500_000, chain="Solana")])

    transport = FakeTransport(sourcify_hit(1, ADDR))
    ranked = cold_service.cold_candidates(transport=transport)

    assert ranked[0].signals.verified is False


def test_cold_candidates_marks_unknown_age_for_unlisted_protocols(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_feed(monkeypatch, [summary("Old-timer", 500_000)])

    ranked = cold_service.cold_candidates(transport=FakeTransport({}))

    assert ranked[0].signals.age_days == -1


def test_cold_candidates_threads_a_custom_floor_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_feed(monkeypatch, [summary("SmallVault", 30_000)])
    tuned = ColdThresholds(min_tvl_usd=25_000.0)

    assert cold_service.cold_candidates(10, None, tuned, FakeTransport({}))


def test_probe_set_targets_the_cold_band_not_the_giants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_feed(
        monkeypatch,
        [
            summary("Giant", 500_000_000, listed_unix=NOW - 900 * 86_400),
            summary("Small", 60_000, listed_unix=NOW - 400 * 86_400),
            summary("Fresh", 300_000, listed_unix=NOW - 5 * 86_400),
        ],
    )
    names = [
        c.name
        for c in cold_service.cold_candidates(limit=2, transport=FakeTransport({}))
    ]
    assert "Giant" not in names
    assert "Fresh" in names
    assert "Small" in names
