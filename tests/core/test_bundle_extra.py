"""Extra bundle tests."""

from ruin.core.bundle import report_bundle
from ruin.core.domain import DrainProof, Report, Target, Vuln
from ruin.core.enums import Severity, TargetMode, VulnClass
from ruin.core.ids import ContractId
from ruin.core.pipeline import pipeline_status
from ruin.core.research import research_card
from ruin.core.screen import target_screen
from ruin.core.trust import trust_model


def test_bundle_full() -> None:
    asset = ContractId.new("0x" + "1" * 40)
    target = Target.new("P", [asset], None, TargetMode.RESEARCH)

    report = Report(
        protocol=target,
        vulns=[Vuln(klass=VulnClass.LOGIC, severity=Severity.HIGH, summary="s")],
        proofs=[],
    )
    bundle = (
        report_bundle("P")
        .with_report(report)
        .with_poc(
            __import__("ruin.core.domain", fromlist=["Poc"]).Poc(
                method="m", forge_test="t"
            )
        )
        .with_drain(DrainProof(method="m", asset=asset, amount=1))
        .with_research(
            research_card(
                Vuln(klass=VulnClass.LOGIC, severity=Severity.HIGH, summary="s"), "m"
            )
        )
        .with_trust(trust_model("P"))
        .with_screen(target_screen("P", "Ethereum", 1))
        .with_pipeline(pipeline_status("P"))
    )
    text = bundle.render_markdown()
    assert "Report Bundle" in text
