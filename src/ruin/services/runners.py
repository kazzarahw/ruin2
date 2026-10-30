"""Operation runner helpers for ``ruin``."""

from __future__ import annotations

from typing import Any

from ruin.core.enums import FUZZ_KIND_BY_NAME
from ruin.core.symbolic import symbolic_result
from ruin.services.fuzzing import (
    EchidnaAdapter,
    FoundryFuzzer,
    MedusaAdapter,
)
from ruin.services.hevm import HevmAdapter
from ruin.services.symbolic import (
    HalmosAdapter,
    MythrilAdapter,
    SymbolicOutcome,
)


def run_fuzz_operation(kwargs: dict[str, Any]) -> str:
    """Run the fuzz-run operation from CLI kwargs."""
    kind_key = str(kwargs.get("kind", "invariant"))
    if kind_key not in FUZZ_KIND_BY_NAME:
        raise ValueError("kind must be fuzz|invariant")
    kind = FUZZ_KIND_BY_NAME[kind_key]
    target = str(kwargs["target"])
    tool = str(kwargs.get("tool", "foundry")).lower()
    match_test = kwargs.get("match_test")
    command = kwargs.get("tool_command")
    if isinstance(command, str):
        command = command.split()
    if tool in {"foundry", "forge"}:
        fuzzer = FoundryFuzzer(command=command, match_test=match_test, kind=kind)
    elif tool == "echidna":
        fuzzer = EchidnaAdapter(command=command, kind=kind)
    elif tool == "medusa":
        fuzzer = MedusaAdapter(command=command, kind=kind)
    else:
        raise ValueError("tool must be foundry|echidna|medusa")
    result = fuzzer.fuzz(
        target,
        match_test=match_test,
        command=command,
        kind=kind,
        finding=kwargs.get("finding") or kwargs.get("linked_finding"),
    )
    return str(result.render_markdown())


def run_symbolic(kwargs: dict[str, Any]) -> str:
    """Run the symbolic operation from CLI kwargs."""
    target = str(kwargs["target"])
    tool = str(kwargs.get("tool", "halmos")).lower()
    if kwargs.get("outcome") is not None:
        outcome_map = {
            "proven": SymbolicOutcome.PROVEN,
            "undecided": SymbolicOutcome.UNDECIDED,
            "unsupported": SymbolicOutcome.UNSUPPORTED,
            "error": SymbolicOutcome.ERROR,
            "errored": SymbolicOutcome.ERROR,
        }
        outcome_key = str(kwargs.get("outcome")).lower()
        if outcome_key not in outcome_map:
            raise ValueError("outcome must be proven|undecided|unsupported|error")
        result = symbolic_result(
            target,
            tool,
            outcome_map[outcome_key],
        ).with_detail(str(kwargs.get("detail", "")))
        resolved_finding = (
            kwargs.get("finding")
            or kwargs.get("linked_finding")
            or kwargs.get("linked-finding")
        )
        if resolved_finding is not None:
            result = result.with_finding(str(resolved_finding))
        return str(result.render_markdown())

    if tool == "halmos":
        adapter = HalmosAdapter(command=kwargs.get("tool_command"))
    elif tool in ("mythril", "myth"):
        adapter = MythrilAdapter(command=kwargs.get("tool_command"))
    elif tool == "hevm":
        adapter = HevmAdapter(command=kwargs.get("tool_command"))
    else:
        raise ValueError("tool must be halmos|mythril|hevm")
    command = kwargs.get("tool_command")
    if isinstance(command, str):
        command = command.split()
    result = adapter.run(
        target,
        command=command,
        finding=kwargs.get("finding"),
        linked_finding=kwargs.get("linked_finding"),
    )
    return str(result.render_markdown())
