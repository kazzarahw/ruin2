"""ruin: fork-first DeFi security-research pipeline."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from ruin.api import (
    bytecode,
    chain,
    classes,
    finding,
    flow,
    protocol,
    source,
    target,
    verify,
)
from ruin.api._requests import (
    BlockWindow,
    FindingDraft,
    FlashloanRequest,
    HuntRequest,
    OracleRequest,
    PocRequest,
    ProtocolRequest,
    RunnerRequest,
    ScreenRequest,
    ThinRequest,
    TriageRequest,
)
from ruin.services.operations import run_operation, run_operation_json

if TYPE_CHECKING:
    from ruin.api._call import JsonPayload

__all__: list[str] = [
    "BlockWindow",
    "FindingDraft",
    "FlashloanRequest",
    "HuntRequest",
    "OracleRequest",
    "PocRequest",
    "ProtocolRequest",
    "RunnerRequest",
    "ScreenRequest",
    "ThinRequest",
    "TriageRequest",
    "bytecode",
    "chain",
    "classes",
    "finding",
    "flow",
    "protocol",
    "run",
    "run_json",
    "run_operation",
    "run_operation_json",
    "source",
    "target",
    "verify",
]


async def run(operation: str = "pipeline", **kwargs: object) -> str:
    """Dispatch a ruin operation and return its rendered output.

    Args:
        operation: The operation name.
        **kwargs: Operation-specific arguments.

    Returns:
        The rendered Markdown or text for the operation.
    """
    return await asyncio.to_thread(run_operation, operation, dict(kwargs))


async def run_json(operation: str = "pipeline", **kwargs: object) -> JsonPayload:
    """Dispatch a ruin operation and return structured data.

    Args:
        operation: The operation name.
        **kwargs: Operation-specific arguments.

    Returns:
        A JSON-safe structured output for the operation.
    """
    data = await asyncio.to_thread(run_operation_json, operation, dict(kwargs))
    return cast("JsonPayload", data)
