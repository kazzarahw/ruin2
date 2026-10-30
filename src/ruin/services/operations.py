"""Operation dispatch for ``ruin``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruin.core.bundle import report_bundle
from ruin.core.domain import Vuln
from ruin.core.enums import (
    FUZZ_KIND_BY_NAME,
    FUZZ_OUTCOME_BY_NAME,
    SOURCE_ACCESS_BY_NAME,
    Severity,
    SourceAccess,
    VulnClass,
)
from ruin.core.fuzz import FuzzResult, fuzz_result
from ruin.core.ids import ContractId
from ruin.core.pipeline import (
    STAGE_BY_NAME,
    STATUS_BY_NAME,
    PipelineStatus,
    pipeline_status,
)
from ruin.core.protocols import parse_protocol
from ruin.core.recon import recon_document
from ruin.core.research import research_card
from ruin.core.rng import RngHackAssessment, rng_hack_assessment
from ruin.core.screen import TargetScreen, target_screen
from ruin.core.slither_io import serialize_review_scaffold, serialize_vulns
from ruin.core.trust import TrustModel, trust_model
from ruin.services.http import fetch_protocol
from ruin.services.operations_builders import BUILDERS
from ruin.services.operations_builders_ctoken import CTOKEN_OPERATIONS
from ruin.services.operations_builders_decompile import DECOMPILE_OPERATIONS
from ruin.services.operations_builders_hunt import HUNT_OPERATIONS
from ruin.services.operations_builders_probe import probe_report
from ruin.services.operations_ext import EXT_OPERATIONS
from ruin.services.operations_ext_diff import DIFF_OPERATIONS
from ruin.services.operations_ext_honeypot import HONEYPOT_OPERATIONS
from ruin.services.operations_ext_honeypot_evm import HONEYPOT_EVM_OPERATIONS
from ruin.services.operations_ext_protocol import PROTOCOL_OPERATIONS
from ruin.services.operations_ext_slot import SLOT_OPERATIONS
from ruin.services.operations_ext_solvency import SOLVENCY_OPERATIONS
from ruin.services.operations_ext_triage import TRIAGE_OPERATIONS
from ruin.services.orchestration import PipelineOptions, run_pipeline
from ruin.services.runners import run_fuzz_operation as _fuzz_run
from ruin.services.runners import run_symbolic as _symbolic
from ruin.services.slither import run_slither


def _pipeline(kwargs: dict[str, Any]) -> str:
    options = PipelineOptions(
        recon_file=str(kwargs["recon_file"]),
        name=str(kwargs["name"]),
        forge_test=str(kwargs["forge_test"]),
        method=str(kwargs["method"]),
        rpc=str(kwargs["rpc"]),
        mode=str(kwargs.get("mode", "research")),
        min_tvl=kwargs.get("min_tvl"),
        vulns_file=kwargs.get("vulns"),
        out=kwargs.get("out"),
        fork_block=kwargs.get("fork_block"),
        private_key=kwargs.get("private_key"),
    )
    return run_pipeline(options)


def _map(kwargs: dict[str, Any]) -> str:
    detail = parse_protocol(fetch_protocol(str(kwargs["slug"])))
    asset = ContractId.new(str(kwargs["asset"]))
    document = recon_document(detail, asset)
    out = kwargs.get("out")
    if out is not None:
        Path(str(out)).write_text(document, encoding="utf-8")
        return ""
    return document


def _slither(kwargs: dict[str, Any]) -> str:
    vulns = run_slither(Path(str(kwargs["source"])))
    lines = [f"slither candidates: {len(vulns)}"]
    lines.extend(f"  [{v.severity.value}] {v.klass}: {v.summary}" for v in vulns)
    out = kwargs.get("out")
    if out is not None:
        Path(str(out)).write_text(serialize_vulns(vulns), encoding="utf-8")
        lines.append(f"wrote {out}")
    return "\n".join(lines)


def _review(kwargs: dict[str, Any]) -> str:
    source = Path(str(kwargs["source"])).read_text(encoding="utf-8")
    scaffold = serialize_review_scaffold(source)
    out = kwargs.get("out")
    if out is not None:
        Path(str(out)).write_text(scaffold, encoding="utf-8")
        return f"wrote {out} (fill `candidates`, then use `--vulns {out}`)"
    return scaffold


def _research(kwargs: dict[str, Any]) -> str:
    summary = kwargs["summary"]
    if isinstance(summary, list):
        summary = " ".join(str(item) for item in summary)
    vuln = Vuln(
        klass=VulnClass.LOGIC,
        severity=Severity.MEDIUM,
        summary=str(summary),
        poc=None,
    )
    card = research_card(vuln, str(kwargs["mechanism"])).with_sources(
        list(kwargs.get("source", []))
    )
    return card.render_markdown()


def _rng_assessment(kwargs: dict[str, Any]) -> RngHackAssessment:
    """Build the RNG-hack assessment shared by text and JSON output."""
    summary = kwargs["summary"]
    if isinstance(summary, list):
        summary = " ".join(str(item) for item in summary)
    source = kwargs["source"]
    if isinstance(source, list):
        source = " ".join(str(item) for item in source)
    vuln = Vuln(
        klass=VulnClass.LOGIC,
        severity=Severity.HIGH,
        summary=str(summary),
        poc=None,
    )
    assessment = rng_hack_assessment(vuln, str(kwargs["mechanism"]), str(source))
    decision = kwargs.get("decision")
    if decision:
        assessment = assessment.with_decision(str(decision))
    if kwargs.get("manipulator") is not None:
        assessment = assessment.with_manipulator(str(kwargs["manipulator"]))
    return assessment


def _rng_hack(kwargs: dict[str, Any]) -> str:
    return _rng_assessment(kwargs).render_markdown()


def _fuzz_result(kwargs: dict[str, Any]) -> FuzzResult:
    """Build the recorded fuzz result shared by text and JSON output."""
    kind_key = str(kwargs.get("kind", "invariant"))
    outcome_key = str(kwargs.get("outcome", "passed"))
    if kind_key not in FUZZ_KIND_BY_NAME:
        raise ValueError("kind must be fuzz|invariant")
    if outcome_key not in FUZZ_OUTCOME_BY_NAME:
        raise ValueError("outcome must be passed|violated|errored")
    return fuzz_result(
        str(kwargs["target"]),
        FUZZ_KIND_BY_NAME[kind_key],
        FUZZ_OUTCOME_BY_NAME[outcome_key],
    ).with_detail(str(kwargs.get("detail", "")))


def _fuzz_op(kwargs: dict[str, Any]) -> str:
    """Record a fuzz result, or execute the fuzzer when ``run`` is set."""
    if kwargs.get("run"):
        return _fuzz_run(kwargs)
    return _fuzz_result(kwargs).render_markdown()


def _symbolic_op(kwargs: dict[str, Any]) -> str:
    """Record when an outcome is given; ``run`` forces the runner path."""
    if kwargs.get("run"):
        return _symbolic({**kwargs, "outcome": None})
    return _symbolic(kwargs)


def _trust_model(kwargs: dict[str, Any]) -> TrustModel:
    """Build the trust model shared by text and JSON output."""
    model = trust_model(str(kwargs["name"])).custodial(
        bool(kwargs.get("custodial", False))
    )
    for assumption in kwargs.get("assume", []):
        role, flow, bound = assumption
        model = model.with_assumption(role, flow, str(bound).lower() != "unbounded")
    return model


def _trust(kwargs: dict[str, Any]) -> str:
    return _trust_model(kwargs).render_markdown()


def _screen_target(kwargs: dict[str, Any]) -> TargetScreen:
    """Build the target screen shared by text and JSON output."""
    screen = target_screen(
        str(kwargs["name"]),
        str(kwargs["chain"]),
        int(kwargs.get("tvl", 0)),
    ).with_source(
        SOURCE_ACCESS_BY_NAME.get(str(kwargs.get("source", "none")), SourceAccess.NONE)
    )
    screen = screen.with_bespoke(bool(kwargs.get("bespoke", False))).with_custodial(
        bool(kwargs.get("custodial", False))
    )
    listed = kwargs.get("listed")
    if listed is not None:
        try:
            screen = screen.with_listed(int(listed))
        except (TypeError, ValueError):
            screen = screen.with_listed(0)
    return screen


def _screen(kwargs: dict[str, Any]) -> str:
    return _screen_target(kwargs).render_markdown()


def _pipeline_state(kwargs: dict[str, Any]) -> PipelineStatus:
    """Build the pipeline status shared by text and JSON output."""
    status = pipeline_status(str(kwargs["name"]))
    for stage_name, state, note in kwargs.get("stage", []):
        stage_key = str(stage_name).lower()
        state_key = str(state).lower()
        if stage_key not in STAGE_BY_NAME:
            raise ValueError("stage must be screen|source|sast|review|report")
        if state_key not in STATUS_BY_NAME:
            raise ValueError("status must be done|inprogress|blocked")
        stage = STAGE_BY_NAME[stage_key]
        mapped = STATUS_BY_NAME[state_key]
        status = status.with_stage(stage, mapped, str(note))
    return status


def _pipeline_status(kwargs: dict[str, Any]) -> str:
    return _pipeline_state(kwargs).render_markdown()


def _bundle(kwargs: dict[str, Any]) -> str:
    bundle = report_bundle(str(kwargs["name"]))
    if kwargs.get("screen"):
        bundle = bundle.with_screen(target_screen(str(kwargs["name"]), "unknown", 0))
    if kwargs.get("pipeline"):
        bundle = bundle.with_pipeline(pipeline_status(str(kwargs["name"])))
    return bundle.render_markdown()


def _probe(kwargs: dict[str, Any]) -> str:
    return probe_report(kwargs).render_markdown()


_OPERATIONS = {
    "pipeline": _pipeline,
    "map": _map,
    "slither": _slither,
    "review": _review,
    "research": _research,
    "rng-hack": _rng_hack,
    "fuzz": _fuzz_op,
    "symbolic": _symbolic_op,
    "trust": _trust,
    "screen": _screen,
    "pipeline-status": _pipeline_status,
    "bundle": _bundle,
    "probe": _probe,
}

_OPERATIONS.update(EXT_OPERATIONS)
_OPERATIONS.update(HONEYPOT_OPERATIONS)
_OPERATIONS.update(HONEYPOT_EVM_OPERATIONS)
_OPERATIONS.update(HUNT_OPERATIONS)
_OPERATIONS.update(DIFF_OPERATIONS)
_OPERATIONS.update(SOLVENCY_OPERATIONS)
_OPERATIONS.update(SLOT_OPERATIONS)
_OPERATIONS.update(CTOKEN_OPERATIONS)
_OPERATIONS.update(DECOMPILE_OPERATIONS)
_OPERATIONS.update(TRIAGE_OPERATIONS)
_OPERATIONS.update(PROTOCOL_OPERATIONS)


def run_operation(operation: str, kwargs: dict[str, Any]) -> str:
    """Dispatch and run one operation."""
    handler = _OPERATIONS.get(operation)
    if handler is None:
        raise ValueError(f"unknown operation: {operation}")
    result = handler(kwargs)
    if not isinstance(result, str):
        raise TypeError(f"{operation} returned non-string")
    return result


def run_operation_json(operation: str, kwargs: dict[str, Any]) -> object:
    """Dispatch and return structured data for one operation."""
    builder = BUILDERS.get(operation)
    if builder is None:
        raise ValueError(f"no structured output for: {operation}")
    return builder(kwargs)
