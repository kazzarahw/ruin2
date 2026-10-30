"""Tests for domain."""

from ruin.core.domain import DrainProof, Poc, Report, Target, Vuln
from ruin.core.enums import Severity, TargetMode, VulnClass
from ruin.core.ids import ContractId


def test_drain_proof_measure() -> None:
    asset = ContractId.new("0x" + "1" * 40)
    proof = DrainProof.measure("m", asset, 10, 4)
    assert proof is not None
    assert proof.amount == 6
    assert DrainProof.measure("m", asset, 5, 5) is None


def test_poc_well_formed() -> None:
    poc = Poc(method="m", forge_test="t")
    assert poc.is_well_formed()


def test_vuln_well_formed() -> None:
    vuln = Vuln(klass=VulnClass.LOGIC, severity=Severity.HIGH, summary="s")
    assert vuln.is_well_formed()


def test_report_render() -> None:
    asset = ContractId.new("0x" + "1" * 40)
    target = Target.new("P", [asset], None, TargetMode.RESEARCH)
    report = Report(protocol=target, vulns=[], proofs=[])
    assert "Security Research Report" in report.render_markdown()
