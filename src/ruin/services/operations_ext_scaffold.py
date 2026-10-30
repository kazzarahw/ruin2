"""Scaffold and infra operation handlers for ``ruin``.

Holds the oracle/flash-loan scaffold builders and the off-chain infra review
template op. Merged into ``EXT_OPERATIONS`` by operations_ext.
"""

from __future__ import annotations

from typing import Any

from ruin.core.flashloan import (
    DEFAULT_FLASHLOAN_AMOUNT,
    FlashLoanScaffold,
    flashloan_defaults,
)
from ruin.core.oracle import (
    DEFAULT_SWAP_AMOUNT,
    OracleScaffold,
    amm_defaults,
)
from ruin.core.review_templates import get_template
from ruin.services.files import write_or_render


def _opt(kwargs: dict[str, Any], key: str, fallback: str) -> str:
    """Return a CLI flag value, falling back when absent or empty."""
    value = kwargs.get(key)
    return str(value) if value else fallback


def oracle_scaffold(kwargs: dict[str, Any]) -> OracleScaffold:
    """Build the oracle scaffold from CLI kwargs (chain defaults included)."""
    chain = _opt(kwargs, "chain", "ethereum")
    fallback_router, fallback_a, fallback_b, known = amm_defaults(chain)
    return OracleScaffold(
        target=str(kwargs["target"]),
        rpc=str(kwargs["rpc"]),
        router=_opt(kwargs, "router", fallback_router),
        reserve_a=_opt(kwargs, "reserve_a", fallback_a),
        reserve_b=_opt(kwargs, "reserve_b", fallback_b),
        oracle=_opt(kwargs, "oracle", ""),
        swap_amount=_opt(kwargs, "swap_amount", DEFAULT_SWAP_AMOUNT),
        min_deviation=_opt(kwargs, "min_deviation", "1 ether"),
        chain=chain.strip().lower(),
        chain_known=known,
    )


def flashloan_scaffold(kwargs: dict[str, Any]) -> FlashLoanScaffold:
    """Build the flash-loan scaffold from CLI kwargs (chain defaults included)."""
    chain = _opt(kwargs, "chain", "ethereum")
    fallback_pool, fallback_asset, known = flashloan_defaults(chain)
    return FlashLoanScaffold(
        target=str(kwargs["target"]),
        rpc=str(kwargs["rpc"]),
        asset=_opt(kwargs, "asset", fallback_asset),
        amount=_opt(kwargs, "amount", DEFAULT_FLASHLOAN_AMOUNT),
        pool=_opt(kwargs, "pool", fallback_pool),
        chain=chain.strip().lower(),
        chain_known=known,
    )


def _oracle(kwargs: dict[str, Any]) -> str:
    return write_or_render(kwargs.get("out"), oracle_scaffold(kwargs).render())


def _flashloan(kwargs: dict[str, Any]) -> str:
    return write_or_render(kwargs.get("out"), flashloan_scaffold(kwargs).render())


def _infra(kwargs: dict[str, Any]) -> str:
    text = get_template(str(kwargs["name"])).render_markdown()
    return write_or_render(kwargs.get("out"), text)


SCAFFOLD_OPERATIONS: dict[str, Any] = {
    "oracle": _oracle,
    "flashloan": _flashloan,
    "infra": _infra,
}
