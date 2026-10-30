"""On-chain ERC-4626 solvency probe (assets vs reported accounting)."""

from __future__ import annotations

from typing import Any

from ruin.core.chains import DEFAULT_EVM_RPC
from ruin.core.solvency import SolvencyReport
from ruin.services.subprocesses import cast_call_command, parse_cast_int, run_command

_TOTAL_ASSETS = "totalAssets()(uint256)"
_UNDERLYING = "underlying()(address)"
_WANT = "want()(address)"
_ASSET = "asset()(address)"
_BALANCE_OF = "balanceOf(address)(uint256)"
_TOTAL_SUPPLY = "totalSupply()(uint256)"


def _call(rpc: str, target: str, signature: str, args: list[str]) -> str:
    """Run one cast call and return its stdout."""
    process = run_command(cast_call_command(rpc, target, signature, args))
    if process.returncode != 0 or not process.stdout.strip():
        tail = process.stderr.strip()[-160:]
        raise RuntimeError(f"cast call {signature} failed: {tail}")
    return process.stdout.strip().strip('"')


def _probe_asset_token(vault: str, rpc: str) -> str:
    """Read the vault's asset token via underlying(), falling back to want()."""
    for signature in (_UNDERLYING, _WANT, _ASSET):
        try:
            return _call(rpc, vault, signature, [])
        except RuntimeError:
            continue
    raise RuntimeError("no underlying()/want()/asset() accessor on vault")


def solvency_data(vault: str, rpc: str, underlying: str = "") -> SolvencyReport:
    """Read the vault's asset/share accounting and the underlying balance."""
    token = underlying or _probe_asset_token(vault, rpc)
    total_assets = parse_cast_int(_call(rpc, vault, _TOTAL_ASSETS, []))
    balance = parse_cast_int(_call(rpc, token, _BALANCE_OF, [vault]))
    shares = parse_cast_int(_call(rpc, vault, _TOTAL_SUPPLY, []))
    return SolvencyReport(
        vault=vault,
        underlying=token,
        total_assets=total_assets,
        vault_balance=balance,
        total_shares=shares,
    )


def solvency_request(kwargs: dict[str, Any]) -> SolvencyReport:
    """Read the vault accounting for CLI kwargs (shared by text and JSON)."""
    return solvency_data(
        str(kwargs["vault"]),
        str(kwargs.get("rpc") or DEFAULT_EVM_RPC),
        str(kwargs.get("underlying") or ""),
    )


def _solvency(kwargs: dict[str, Any]) -> str:
    """Render the solvency report for an ERC-4626 vault."""
    return solvency_request(kwargs).render_markdown()


SOLVENCY_OPERATIONS: dict[str, Any] = {"solvency": _solvency}
