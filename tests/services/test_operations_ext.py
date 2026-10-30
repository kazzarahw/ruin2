"""Tests for extended operations."""

from pathlib import Path
from typing import Any, cast

from ruin.services import operations_ext as ext


def test_oracle_operation() -> None:
    result = ext.EXT_OPERATIONS["oracle"](
        {
            "target": "0xTarget",
            "rpc": "http://localhost:8545",
        }
    )
    assert "0xTarget" in result
    assert "test_oracle_manipulation" in result


def test_flashloan_operation() -> None:
    result = ext.EXT_OPERATIONS["flashloan"](
        {
            "target": "0xTarget",
            "rpc": "http://localhost:8545",
        }
    )
    assert "0xTarget" in result
    assert "flashLoanSimple" in result


def test_oracle_none_flags_use_defaults() -> None:
    result = ext.EXT_OPERATIONS["oracle"](
        {
            "target": "0xTarget",
            "rpc": "http://localhost:8545",
            "reserve_a": None,
            "reserve_b": None,
            "oracle": None,
            "swap_amount": None,
            "min_deviation": None,
        }
    )
    assert "None" not in result
    assert "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48" in result


def test_flashloan_none_flags_use_defaults() -> None:
    result = ext.EXT_OPERATIONS["flashloan"](
        {
            "target": "0xA",
            "rpc": "http://localhost:8545",
            "asset": None,
            "amount": None,
            "pool": None,
        }
    )
    assert "None" not in result


def test_oracle_with_out(tmp_path: Path) -> None:
    out = tmp_path / "Oracle.t.sol"
    result = ext.EXT_OPERATIONS["oracle"](
        {
            "target": "0xA",
            "rpc": "http://rpc",
            "out": str(out),
        }
    )
    assert "wrote" in result
    assert out.exists()


def test_flashloan_with_out(tmp_path: Path) -> None:
    out = tmp_path / "Flash.t.sol"
    result = ext.EXT_OPERATIONS["flashloan"](
        {
            "target": "0xA",
            "rpc": "http://rpc",
            "out": str(out),
        }
    )
    assert "wrote" in result
    assert out.exists()


def test_proxy_operation() -> None:
    def fake_run(*args: Any, **kwargs: Any) -> Any:
        class P:
            stdout = "0x000000000000000000000000abcdef1234567890abcd"
            returncode = 0

        return P()

    from ruin.services import proxy as proxy_svc

    cast("Any", proxy_svc).run_command = fake_run
    result = ext.EXT_OPERATIONS["proxy"](
        {
            "address": "0xProxy",
            "rpc": "http://localhost:8545",
        }
    )
    assert "0xProxy" in result


def test_logs_operation() -> None:
    def fake_run(*args: Any, **kwargs: Any) -> Any:
        class P:
            stdout = ""
            returncode = 0

        return P()

    from ruin.services import forensics as fs

    cast("Any", fs).run_command = fake_run
    result = ext.EXT_OPERATIONS["logs"](
        {
            "address": "0xabc",
            "rpc": "http://localhost:8545",
            "from_block": 1,
            "to_block": 10,
        }
    )
    assert "Log Scan" in result


def test_parse_chain_aliases_popular_names_to_evm() -> None:
    from ruin.core.enums import Chain

    assert ext._parse_chain("ethereum") is Chain.EVM
    assert ext._parse_chain("Polygon") is Chain.EVM
    assert ext._parse_chain("arbitrum") is Chain.EVM
    assert ext._parse_chain("solana") is Chain.SOLANA


def test_oracle_router_override_flows_into_scaffold() -> None:
    result = ext.EXT_OPERATIONS["oracle"](
        {
            "target": "0xA",
            "rpc": "http://rpc",
            "router": "0x1111111111111111111111111111111111111111",
        }
    )
    assert "0x1111111111111111111111111111111111111111" in result
    assert "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D" not in result


def test_oracle_json_builder_honors_params() -> None:
    from ruin.services.operations_builders import _oracle_data

    data = _oracle_data(
        {
            "target": "0xA",
            "rpc": "http://rpc",
            "router": "0x2222222222222222222222222222222222222222",
            "reserve_a": None,
            "reserve_b": None,
            "oracle": None,
            "swap_amount": None,
            "min_deviation": None,
        }
    )
    doc = cast("dict[str, Any]", data)
    assert doc["router"] == "0x2222222222222222222222222222222222222222"
    assert doc["reserve_a"] == "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"


def test_flashloan_json_builder_honors_params() -> None:
    from ruin.services.operations_builders import _flashloan_data

    data = _flashloan_data(
        {
            "target": "0xA",
            "rpc": "http://rpc",
            "asset": "0x3333333333333333333333333333333333333333",
            "pool": None,
            "amount": None,
        }
    )
    doc = cast("dict[str, Any]", data)
    assert doc["asset"] == "0x3333333333333333333333333333333333333333"
    assert doc["pool"] == "0x87870Bca3F3fD6335C3F4Ce8392D69350B4fA4E2"


def test_oracle_json_builder_is_chain_aware() -> None:
    from ruin.services.operations_builders import _oracle_data

    data = _oracle_data(
        {
            "target": "0xT",
            "rpc": "http://r",
            "chain": "base",
        }
    )
    doc = cast("dict[str, Any]", data)
    assert doc["chain"] == "base"
    assert doc["chain_known"] is True
    assert doc["reserve_a"] == "0x4200000000000000000000000000000000000006"
    assert doc["reserve_b"] == "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


def test_oracle_scaffold_warns_on_unknown_chain() -> None:
    from ruin.core.oracle import OracleScaffold

    scaffold = OracleScaffold(
        target="0xT",
        rpc="http://r",
        chain="cronos",
        chain_known=False,
    )
    text = scaffold.render()
    assert "WARNING: mainnet AMM defaults" in text
    assert "// chain: cronos" in text


def test_flashloan_json_builder_is_chain_aware() -> None:
    from ruin.services.operations_builders import _flashloan_data

    data = _flashloan_data({"target": "0xT", "rpc": "http://r", "chain": "arb"})
    doc = cast("dict[str, Any]", data)
    assert doc["chain"] == "arb"
    assert doc["chain_known"] is True
    assert doc["pool"] == "0x794a61358D6845594F94dc1DB02A252b5b4814aD"
    assert doc["asset"] == "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"


def test_flashloan_scaffold_warns_on_unknown_chain() -> None:
    from ruin.core.flashloan import FlashLoanScaffold

    scaffold = FlashLoanScaffold(
        target="0xT", rpc="http://r", chain="scroll", chain_known=False
    )
    text = scaffold.render()
    assert "WARNING: mainnet Aave defaults" in text
    assert "// chain: scroll" in text


def test_chain_id_prefers_explicit_pin() -> None:
    assert ext._chain_id_for({"chain": "polygon", "chain_id": 137}) == 137
    assert ext._chain_id_for({"chain": "ethereum", "chain_id": 8453}) == 8453


def test_chain_id_derives_from_slug_when_default() -> None:
    assert ext._chain_id_for({"chain": "polygon"}) == 137
    assert ext._chain_id_for({"chain": "Polygon"}) == 137
    assert ext._chain_id_for({"chain": "etherlink"}) == 42793
    assert ext._chain_id_for({"chain": "EVM"}) == 1
    assert ext._chain_id_for({}) == 1
