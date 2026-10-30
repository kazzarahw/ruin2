"""Shared async dispatch for the typed API namespaces."""

from __future__ import annotations

import asyncio
from typing import Any, cast

from ruin.services.operations import BUILDERS, run_operation, run_operation_json

# Payload keys differ per operation; each builder defines its own shape.
JsonPayload = dict[str, Any]


async def call(operation: str, kwargs: dict[str, Any]) -> JsonPayload | str:
    """Return structured data for an operation, rendered text when unstructured.

    Args:
        operation: Registered operation name.
        kwargs: Operation arguments keyed exactly by parser dest names.

    Returns:
        The builder payload when one exists, otherwise the rendered text.
    """
    if operation not in BUILDERS:
        return await asyncio.to_thread(run_operation, operation, kwargs)
    data = await asyncio.to_thread(run_operation_json, operation, kwargs)
    return cast("JsonPayload", data)
