"""Tests for the source op and inspect --source wiring."""

from pathlib import Path
from unittest.mock import patch

from ruin.core.enums import Chain
from ruin.core.onchain import SourceInfo
from ruin.services.operations import run_operation, run_operation_json

_ADDR = "0x" + "c" * 40


def _fake_source() -> SourceInfo:
    return SourceInfo(
        chain=Chain.EVM,
        address=_ADDR,
        name="Vault.sol",
        language="Solidity",
        source_text="pragma solidity ^0.8.0;",
        url="https://etherscan.io/address/" + _ADDR,
        verified=True,
    )


def test_source_op_renders_verified() -> None:
    with patch(
        "ruin.services.operations_ext.fetch_source", return_value=_fake_source()
    ):
        text = run_operation("source", {"address": _ADDR, "chain": "EVM"})
    assert "verified" in text
    assert "Vault.sol" in text
    assert "pragma solidity" in text


def test_source_op_json() -> None:
    with patch(
        "ruin.services.operations_ext.fetch_source", return_value=_fake_source()
    ):
        data = run_operation_json("source", {"address": _ADDR, "chain": "EVM"})
    assert isinstance(data, dict)
    assert data.get("verified") is True


def test_source_out_dump_keeps_full_source(tmp_path: Path) -> None:
    info = SourceInfo(
        chain=Chain.EVM,
        address=_ADDR,
        name="Vault.sol",
        language="Solidity",
        source_text="x" * 5000,
        verified=True,
    )
    out = tmp_path / "src.md"
    with patch("ruin.services.operations_ext.fetch_source", return_value=info):
        run_operation("source", {"address": _ADDR, "chain": "EVM", "out": str(out)})
    assert "x" * 5000 in out.read_text(encoding="utf-8")


def test_source_tree_writes_each_file(tmp_path: Path) -> None:
    info = SourceInfo(
        chain=Chain.EVM,
        address=_ADDR,
        name="Big.sol",
        language="Solidity",
        source_text=(
            "// ==== src/Big.sol ====\ncontract Big {}\n\n"
            "// ==== src/Small.sol ====\nlibrary Small {}"
        ),
        verified=True,
    )
    tree = tmp_path / "tree"
    with patch("ruin.services.operations_ext.fetch_source", return_value=info):
        text = run_operation(
            "source", {"address": _ADDR, "chain": "EVM", "tree": str(tree)}
        )
    assert "2 files" in text
    assert (tree / "src" / "Big.sol").read_text(encoding="utf-8") == "contract Big {}"
    assert (tree / "src" / "Small.sol").read_text(encoding="utf-8") == (
        "library Small {}"
    )


def test_inspect_source_flag_uses_ingestion() -> None:
    with patch(
        "ruin.services.operations_ext.fetch_source", return_value=_fake_source()
    ):
        text = run_operation(
            "inspect", {"address": _ADDR, "chain": "EVM", "source": True}
        )
    assert "Source (verified" in text
