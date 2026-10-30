"""Pipeline orchestration for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ruin.core.domain import Poc, Report, Vuln
from ruin.core.enums import CredentialsRef, Severity, TargetMode, VulnClass
from ruin.core.ids import ProtocolName, RpcUrl
from ruin.core.recon import ReconResult, ReconSpec
from ruin.core.runs import RunConfig
from ruin.core.value_objects import Amount
from ruin.services.files import read_recon, read_vulns
from ruin.services.foundry import FoundryRunner


@dataclass
class PipelineOptions:
    """Options for the end-to-end pipeline."""

    recon_file: str
    name: str
    forge_test: str
    method: str
    rpc: str
    mode: str = "research"
    min_tvl: int | None = None
    vulns_file: str | None = None
    out: str | None = None
    fork_block: int | None = None
    private_key: str | None = None


def run_pipeline(options: PipelineOptions) -> str:
    """Run the end-to-end pipeline and return Markdown."""
    mode_map = {
        "research": TargetMode.RESEARCH,
        "fork": TargetMode.RESEARCH,
        "own": TargetMode.OWN,
        "authorized": TargetMode.AUTHORIZED,
    }
    if options.mode not in mode_map:
        raise ValueError(f"unknown mode: {options.mode}")
    target_mode = mode_map[options.mode]

    entries = read_recon(Path(options.recon_file))
    spec = ReconSpec(
        name=ProtocolName.new(options.name),
        mode=target_mode,
        min_tvl=options.min_tvl,
    )
    recon = ReconResult.scope(spec, entries)
    if recon is None:
        raise ValueError("no in-scope contracts")
    target = recon.to_target()
    asset_source = recon.tvl
    asset = (
        asset_source.asset
        if asset_source is not None
        else (target.contracts[0] if target.contracts else None)
    )
    if asset is None:
        raise ValueError("no asset to measure")
    poc = Poc(
        method=options.method,
        calls=[],
        expected_drain=Amount(asset=asset, units=0),
        forge_test=options.forge_test,
    )
    report_target = target
    report_poc = poc
    config = RunConfig(
        target=target,
        poc=poc,
        rpc_url=RpcUrl.new(options.rpc),
        credentials=CredentialsRef.NONE,
        fork_block=options.fork_block,
        private_key=options.private_key,
    )
    run = FoundryRunner().run(config)
    discovered: list[Vuln] = []
    if options.vulns_file is not None:
        discovered = read_vulns(Path(options.vulns_file))
    run_vuln = Vuln(
        klass=VulnClass.LOGIC,
        severity=Severity.HIGH,
        summary=run.summary,
        poc=report_poc,
    )
    proofs = run.all_drains or ([run.drain] if run.drain else [])
    report = Report(
        protocol=report_target,
        vulns=[*discovered, run_vuln],
        proofs=proofs,
    )
    markdown = report.render_markdown()
    if options.out is not None:
        Path(options.out).write_text(markdown, encoding="utf-8")
        return ""
    return markdown
