"""Tests for the honeypot verdict operation."""

from typing import Any, cast
from unittest.mock import patch

import pytest

from ruin.core.enums import Chain
from ruin.core.onchain import AccountInfo
from ruin.services import operations_ext_honeypot as hp


class _FakeAdapter:
    """Adapter stub returning a canned jsonParsed mint record."""

    def __init__(self, raw: dict[str, object]) -> None:
        self.raw = raw

    def fetch_account(self, address: str, _rpc: str) -> AccountInfo:
        return AccountInfo(
            chain=Chain.SOLANA, address=address, exists=True, raw=self.raw, note=""
        )


def test_honeypot_flags_active_authorities() -> None:
    raw: dict[str, object] = {
        "data": {
            "parsed": {
                "type": "mint",
                "info": {"mintAuthority": "A", "freezeAuthority": "F"},
            }
        }
    }
    with patch.object(hp, "get_adapter", return_value=_FakeAdapter(raw)):
        out = hp.HONEYPOT_OPERATIONS["honeypot"]({"mint": "MINTxyz"})
    assert "verdict: medium" in out
    assert "mint-authority-active" in out


def test_honeypot_clean_when_renounced() -> None:
    raw: dict[str, object] = {
        "data": {
            "parsed": {
                "type": "mint",
                "info": {"mintAuthority": None, "freezeAuthority": None},
            }
        }
    }
    with patch.object(hp, "get_adapter", return_value=_FakeAdapter(raw)):
        data = hp.honeypot_data("MINTxyz", "http://rpc")
    assert data.verdict == "clean"
    assert data.is_mint is True


def test_honeypot_registered_in_operations() -> None:
    from ruin.services.operations import _OPERATIONS

    assert "honeypot" in cast("dict[str, Any]", _OPERATIONS)


def test_honeypot_data_defaults_rpc_when_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    class FakeAdapter:
        def fetch_account(self, _address: str, rpc: str) -> object:
            seen.append(rpc)

            class Acct:
                def __init__(self) -> None:
                    self.raw: dict[str, object] = {"type": "mint", "parsed": {}}

            return Acct()

    monkeypatch.setattr(hp, "get_adapter", lambda _chain: FakeAdapter())
    data = hp.honeypot_data("MINT", None)
    assert seen == [hp.DEFAULT_RPC]
    assert data.address == "MINT"
