"""Tests for ids."""

from __future__ import annotations

import pytest

from ruin.core.ids import ContractId, ProtocolName, RpcUrl


def test_contract_id_valid() -> None:
    value = ContractId.new("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
    assert str(value) == "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"


def test_contract_id_invalid() -> None:
    with pytest.raises(ValueError, match=r"invalid contract address"):
        ContractId.new("bad")


def test_rpc_url_valid() -> None:
    value = RpcUrl.new("https://example.com")
    assert str(value) == "https://example.com"


def test_rpc_url_invalid() -> None:
    with pytest.raises(ValueError, match=r"invalid rpc url"):
        RpcUrl.new("   ")


def test_protocol_name_valid() -> None:
    value = ProtocolName.new("ZAMM")
    assert str(value) == "ZAMM"


def test_protocol_name_invalid() -> None:
    with pytest.raises(ValueError, match=r"invalid protocol name"):
        ProtocolName.new("")
