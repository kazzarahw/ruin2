"""Flow namespace: pipeline status and playbook execution."""

from __future__ import annotations

from ruin.api._call import JsonPayload, call


async def status(
    name: str, stages: list[tuple[str, str, str]] | None = None
) -> JsonPayload | str:
    """Report pipeline stage progress (CLI ``ruin flow status``)."""
    return await call(
        "pipeline-status",
        {"name": name, "stage": [list(item) for item in stages or []]},
    )


async def run(name: str, params: list[str] | None = None) -> JsonPayload | str:
    """Execute a playbook by name (CLI ``ruin flow playbook``)."""
    return await call("playbook", {"name": name, "param": params or []})


__all__: list[str] = ["run", "status"]
