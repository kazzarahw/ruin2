"""Smoke-test a ruin Prime skill installation."""

from __future__ import annotations

import asyncio

from ruin import run


async def main() -> int:
    """Run a small Prime skill smoke test."""
    print(await run("research", mechanism="m", summary="s"))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
