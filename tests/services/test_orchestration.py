"""Tests for orchestration."""

from pathlib import Path
from typing import Any, cast

from ruin.core.domain import DrainProof
from ruin.core.ids import ContractId, RpcUrl
from ruin.core.runs import RunOutput
from ruin.services import orchestration as orch


class FakeRunner:
    def run(self, _config: object) -> RunOutput:
        asset = ContractId.new("0x" + "1" * 40)
        return RunOutput(
            rpc_url=RpcUrl.new("http://x"),
            succeeded=True,
            drain=DrainProof(method="m", asset=asset, amount=1),
            summary="drained",
        )


def test_run_pipeline(tmp_path: Path) -> None:
    recon = tmp_path / "recon.json"
    asset = "0x" + "1" * 40
    contract = "0x" + "2" * 40
    recon.write_text(
        '{"tvl_asset": "'
        + asset
        + '", "contracts": [{"address": "'
        + contract
        + '", "tvl": 5}]}',
        encoding="utf-8",
    )
    cast("Any", orch).FoundryRunner = FakeRunner
    options = orch.PipelineOptions(
        recon_file=str(recon),
        name="P",
        forge_test="t",
        method="m",
        rpc="http://example.com",
    )
    text = orch.run_pipeline(options)
    assert "Security Research Report" in text
