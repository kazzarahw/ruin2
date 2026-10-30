"""Implementation-diff operation for proxy upgrades."""

from __future__ import annotations

from typing import Any

from ruin.core.chains import rpc_for
from ruin.core.probe import (
    ImplDiffReport,
    SelectorRow,
    drain_selectors_in,
    selector_delta,
)
from ruin.services.operations_ext_selectors import code_at, follow_delegation, inventory


def impl_diff_report(kwargs: dict[str, Any]) -> ImplDiffReport:
    """Build the selector-surface diff shared by text and JSON output."""
    rpc = rpc_for(kwargs)
    old_rpc = str(kwargs.get("old_rpc") or rpc)
    new_addr = str(kwargs["new_impl"])
    old_addr = str(kwargs["old_impl"])
    new_code, _ = follow_delegation(
        rpc, new_addr, code_at(rpc, new_addr), follow_slot=False
    )
    old_code, _ = follow_delegation(
        old_rpc, old_addr, code_at(old_rpc, old_addr), follow_slot=False
    )
    added, removed = selector_delta(new_code, old_code)
    rows = tuple(
        SelectorRow(selector=selector, signature=signature)
        for selector, signature in inventory(new_code, resolve=False)
    )
    drain_new = {s for s, _ in drain_selectors_in(new_code)}
    return ImplDiffReport(
        new_impl=new_addr,
        old_impl=old_addr,
        added=tuple(added),
        removed=tuple(removed),
        new_names=rows,
        drain_added=tuple(s for s in added if s in drain_new),
        old_missing=not bool(old_code) or old_code == "0x",
    )


def _impl_diff(kwargs: dict[str, Any]) -> str:
    """Compare the selector surface of two implementations."""
    return impl_diff_report(kwargs).render_markdown()


DIFF_OPERATIONS: dict[str, Any] = {"impl-diff": _impl_diff}
