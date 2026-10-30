"""Golden rendering tests."""

from ruin.core.bundle import report_bundle
from ruin.core.domain import Report, Target, Vuln
from ruin.core.enums import FuzzKind, FuzzOutcome, Severity, TargetMode, VulnClass
from ruin.core.fuzz import fuzz_result
from ruin.core.ids import ContractId
from ruin.core.pipeline import PipelineStage, pipeline_status
from ruin.core.rng import rng_hack_assessment
from ruin.core.screen import target_screen
from ruin.core.triage import triage_vulns
from ruin.core.trust import trust_model


def test_report_golden() -> None:

    asset = ContractId.new("0x" + "1" * 40)
    target = Target.new("P", [asset], None, TargetMode.RESEARCH)
    vuln = Vuln(klass=VulnClass.LOGIC, severity=Severity.HIGH, summary="s")
    report = Report(protocol=target, vulns=[vuln], proofs=[])
    expected = """# Security Research Report — P

## Scope

- 0x1111111111111111111111111111111111111111

Mode: Research

## Findings

### 0. Logic — High

s

Status: open
"""
    assert report.render_markdown() == expected


def test_screen_golden() -> None:

    expected = """# Target Screen — P

- **Chain:** Ethereum
- **TVL:** $1
- **Source:** None
- **Bespoke layer (real-bug surface):** False
- **Custodial / trusted:** False

## Screen axes

- [ ] smaller TVL (the smaller-protocol preference)
- [ ] new / live (recently listed)
- [ ] public source (the SAST path)
- [ ] bespoke layer (not a canonical, audited core)
- [ ] trustless (not an explicitly custodial / trusted role)

> Verdict: a candidate scores highest when it is small + new + public-source + bespoke-layer + trustless. A canonical / audited core, a private / no source, a non-Solidity routing, or an explicitly custodial / trusted role each pull the screen down — the realistic exposure then is the trust assumption, a RUG vector, a self-inflicted fund-loss flaw, or a documented not-exploitable."""
    assert target_screen("P", "Ethereum", 1).render_markdown() == expected


def test_pipeline_golden() -> None:

    expected = """# Pipeline — P

- [x] Screen — note
- [ ] Source — (not started)
- [ ] SAST — (not started)
- [ ] Review — (not started)
- [ ] Report — (not started)

> The pipeline is: screen → source → SAST → review → report. The `x`/`…`/`!` marks are done / in-flight / blocked. A blocked stage is a reason, not a door-close — the researcher discriminates (a canonical / audited core ships here; a bespoke / public-source / new / small / trustless target is a full-audit target)."""
    assert (
        pipeline_status("P")
        .with_stage(PipelineStage.SCREEN, "Done", "note")
        .render_markdown()
        == expected
    )


def test_bundle_golden() -> None:

    expected = """# Report Bundle — P
"""
    assert report_bundle("P").render_markdown() == expected


def test_trust_golden() -> None:

    expected = """# Trust Model — P

- **Custodial / trusted:** True

## Trust assumptions

- **`operator`** — flow (UNBOUNDED)

## Roles to expose

- [ ] operator
- [ ] owner
- [ ] governor
- [ ] admin
- [ ] keeper
- [ ] pauser
- [ ] multisig

> Verdict: an explicitly custodial protocol (a trusted operator / owner) has a custodial surface, not a contract-bug surface. A working PoC on a trusted-operator flow is a trust violation (the operator acts), not a code defect. Distinguish the bounded delta (a `revert` cap) from an unbounded flow (a drain)."""
    assert (
        trust_model("P")
        .custodial(True)
        .with_assumption("operator", "flow", False)
        .render_markdown()
        == expected
    )


def test_rng_golden() -> None:

    vuln = Vuln(klass=VulnClass.LOGIC, severity=Severity.HIGH, summary="s")
    expected = """# RNG-Hack Assessment — s

- **Mechanism:** `m`
- **Source value:** `block.timestamp`
- **Feeds decision:** d
- **Manipulable by:** 

## Is it a TWAP / time-accumulator (usually NOT a hack)?

- [ ] cumulative price/time accumulator

## Is it a manipulable decision path?

- [ ] derives from `block.timestamp`
- [ ] derives from `blockhash`
- [ ] derives from `difficulty`
- [ ] derives from `gasleft`
- [ ] derives from `prevrandao`

- [ ] attacker (flash loan / front-running)
- [ ] sequencer (L2 order/timestamp control)
- [ ] miner/proposer (timestamp ±15s, prevrandao)
- [ ] none (embedded entropy / off-chain)

> Verdict: if the value feeds a *winner/order/expiry* decision an actor can influence, it is a genuine RNG-hack — not the `weak-prng` false-positive. Document the source value, the decision, and who can manipulate it."""
    assert (
        rng_hack_assessment(vuln, "m", "block.timestamp")
        .with_decision("d")
        .render_markdown()
        == expected
    )


def test_fuzz_golden() -> None:

    expected = """# Fuzz — t

- **Kind:** Invariant
- **Outcome:** Violated
- **Counter-example / detail:** d

## Invariants to conserve

- [ ] total minted + total burned == total supply (vault)
- [ ] total collateral >= total debt * minCollateralRatio (CDP)
- [ ] reserve * price is conserved up to fees (AMM)
- [ ] after a deposit/withdraw round-trip, balance is unchanged
- [ ] no negative user balances
- [ ] the invariant solvers agree with the on-chain state

> A `Violated` footprint is a lead: it is the counter-example that pinpoints the invariant-guarantee / the fund-routing decision the bespoke math deserves manual review for."""
    assert (
        fuzz_result("t", FuzzKind.INVARIANT, FuzzOutcome.VIOLATED)
        .with_detail("d")
        .render_markdown()
        == expected
    )


def test_triage_golden() -> None:

    expected = """# Vuln Triage — P

## Leads (usually real signals)

- [ ] `weak-prng` x1

## Noise (usually false-positives)

- [ ] `timestamp` x1

> The triage is the first pass: it surfaces the leads (weak-prng, unprotected-init, arbitrary-send-eth, reentrancy, controlled-delegatecall) and flags the noise (invMod Newton-Raphson, safeTransferFrom into address(this), block.timestamp rate-limits, attached-protocol reentrancies) for cross-check. A noise flag is NOT a dismiss — it is the researcher's job to confirm the specific mechanism before shipping a finding."""
    assert triage_vulns("P", ["weak-prng", "timestamp"]).render_markdown() == expected
