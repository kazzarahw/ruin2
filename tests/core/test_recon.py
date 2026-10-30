"""Tests for recon."""

import json

from ruin.core.enums import TargetMode
from ruin.core.ids import ContractId, ProtocolName
from ruin.core.protocols import ProtocolDetail
from ruin.core.recon import (
    ReconEntry,
    ReconResult,
    ReconSpec,
    parse_recon,
    recon_document,
)
from ruin.core.value_objects import Amount


def test_parse_recon() -> None:
    doc = {
        "tvl_asset": "0x" + "1" * 40,
        "contracts": [{"address": "0x" + "2" * 40, "tvl": 5}],
    }
    entries = parse_recon(json.dumps(doc))
    assert len(entries) == 1


def test_parse_recon_null_tvl_binds_tvl_asset() -> None:
    asset = "0x" + "1" * 40
    doc = {
        "tvl_asset": asset,
        "contracts": [{"address": "0x" + "2" * 40, "tvl": None}],
    }
    entries = parse_recon(json.dumps(doc))
    assert entries[0].tvl is not None
    assert entries[0].tvl.asset.as_str() == asset
    assert entries[0].tvl.units == 0


def test_scope() -> None:
    asset = ContractId.new("0x" + "1" * 40)
    addr = ContractId.new("0x" + "2" * 40)
    entry = ReconEntry(address=addr, tvl=Amount(asset=asset, units=5))
    spec = ReconSpec(name=ProtocolName.new("P"), mode=TargetMode.RESEARCH, min_tvl=1)
    result = ReconResult.scope(spec, [entry])
    assert result is not None
    assert result.is_well_formed()


def test_recon_document() -> None:
    detail = ProtocolDetail(name="P", primary=ContractId.new("0x" + "2" * 40))
    asset = ContractId.new("0x" + "1" * 40)
    doc = recon_document(detail, asset)
    assert "tvl_asset" in doc
