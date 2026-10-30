"""Source-code smell heuristics for ``ruin``.

Each heuristic names a bug class drawn from public exploit postmortems
(ERC-4626 inflation attacks, Yul calldata-dispatch corruptions such as
the 1inch resolver incident, wide-shift fixed-point overflow, spot-price
oracle reliance, unprotected external-exec wrappers, caller-supplied
executors, unverified V3 flash callbacks, optimistic-oracle payout
consumers). Flags are coarse
regex signals meant for triage, not verdicts: a flag means "read this
code path", never "this is exploitable".
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

_ERC4626_API = re.compile(
    r"function\s+(?:convertToShares|previewDeposit|totalAssets)\b"
)
_TOTAL_ASSETS_IMPL = re.compile(
    r"function\s+totalAssets\s*\([^)]*\)[^{;]*\{[^}]*balanceOf\(\s*address\(this\)",
    re.DOTALL,
)
_INFLATION_HARDENING = re.compile(
    r"virtual[_-]?(?:Shares|Assets|Amount)|OFFERLE|dead[_-]?shares?|"
    r"MIN(?:IMUM)?[_-]?TOTAL_SUPPLY|initial[_-]?shares|MULTIPLIER_DECIMALS|"
    r"decimalsOffset",
    re.IGNORECASE,
)
_ASSEMBLY = re.compile(r"\bassembly\s*\{")
_CALLDATA_LOAD = re.compile(r"calldataload\s*\(")
_SHR = re.compile(r"\bshr\s*\(")
_LOW_LEVEL_CALL = re.compile(r"\.call\s*[{(]")
_WIDE_SHIFT = re.compile(r"<<\s*(?:64|96|112|128)\b")
_SAFE_MATH = re.compile(
    r"checked_sh|SafeCast|assertEq|mulDiv|2\*\*\s*(?:64|96|112|128)",
    re.IGNORECASE,
)
_SPOT_PRICE = re.compile(r"getReserves\s*\(")
_TRUSTED_ORACLE = re.compile(
    r"chainlink|AggregatorV3|observation|TWAP|twap\b|oracle",
    re.IGNORECASE,
)
_EXEC_FN = re.compile(
    r"function\s+(?:execute|exec|callContract|multiAction|multicall)\b[^{]*\bexternal\b",
)
_SENDER_GUARD = re.compile(
    r"msg\.sender\s*==|only[A-Z]\w*|onlyOwner|_checkOwner|"
    r"hasRole\(|_recover\(|recover\w*\(|ecrecover|\bsig[VS]\b"
)

INFLATION_EXPOSED = "erc4626-inflation-exposed"
YUL_DISPATCH = "yul-calldata-dispatch"
WIDE_SHIFT_MATH = "wide-shift-math"
SPOT_PRICE_ORACLE = "spot-price-oracle"
UNPROTECTED_EXEC = "unprotected-exec"
AUTHORITY_UNGUARDED = "rust-authority-unguarded"
CALLER_EXECUTOR = "caller-supplied-executor"
UNVERIFIED_POOL_CALLBACK = "unverified-pool-callback"
OM_ORACLE_CONSUMER = "optimistic-oracle-consumer"

SMELL_NAMES: tuple[str, ...] = (
    INFLATION_EXPOSED,
    YUL_DISPATCH,
    WIDE_SHIFT_MATH,
    SPOT_PRICE_ORACLE,
    UNPROTECTED_EXEC,
    AUTHORITY_UNGUARDED,
    CALLER_EXECUTOR,
    UNVERIFIED_POOL_CALLBACK,
    OM_ORACLE_CONSUMER,
)


_VY_4626_API = re.compile(
    r"def\s+(?:convert_to_shares|preview_deposit|_?total_?assets)\b",
    re.IGNORECASE,
)
_VY_TOTAL_ASSETS = re.compile(r"def\s+_?total_?assets\s*\(", re.IGNORECASE)
_VY_BALANCE_SELF = re.compile(r"balance_?of\(\s*(?:self|vault\b)", re.IGNORECASE)


def _vy_total_assets_body(text: str, start: int) -> str:
    """Return a Vyper function body: from the signature to the next def."""
    header = text.find(":", start)
    if header == -1:
        return ""
    nxt = text.find("\ndef ", header)
    end = nxt if nxt != -1 else min(len(text), header + 600)
    return text[header:end]


def _vy_inflation_exposed(text: str) -> bool:
    """Flag Vyper vaults whose total-assets reads the raw balance."""
    if not _VY_4626_API.search(text):
        return False
    for match in _VY_TOTAL_ASSETS.finditer(text):
        body = _vy_total_assets_body(text, match.start())
        if _VY_BALANCE_SELF.search(body):
            return True
    return False


def _inflation_exposed(text: str) -> bool:
    """Flag share-price accounting off the raw contract balance."""
    vyper_hit = _vy_inflation_exposed(text)
    if not vyper_hit and (
        not _ERC4626_API.search(text) or not _TOTAL_ASSETS_IMPL.search(text)
    ):
        return False
    return _INFLATION_HARDENING.search(text) is None


def _yul_dispatch(text: str) -> bool:
    """Flag hand-written calldata parsing in assembly.

    Raw loads plus shifts or copies are the fingerprint of manual argument
    decoding (the 1inch resolver class); revert-bubble-only assembly does
    not qualify.
    """
    return bool(
        _ASSEMBLY.search(text) and _CALLDATA_LOAD.search(text) and _SHR.search(text)
    )


def _wide_shift_math(text: str) -> bool:
    """Flag wide left-shift fixed-point math without checked helpers."""
    if not _WIDE_SHIFT.search(text):
        return False
    return _SAFE_MATH.search(text) is None


def _spot_price_oracle(text: str) -> bool:
    """Flag reserve-based pricing with no observation/oracle reference."""
    if not _SPOT_PRICE.search(text):
        return False
    return _TRUSTED_ORACLE.search(text) is None


def _exec_body(text: str, start: int) -> str:
    """Return the function body slice beginning at a match start."""
    brace = text.find("{", start)
    if brace == -1:
        return ""
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[brace : index + 1]
    return text[brace:]


def _unprotected_exec(text: str) -> bool:
    """Flag external exec wrappers that call out without a sender guard."""
    for match in _EXEC_FN.finditer(text):
        body = _exec_body(text, match.start())
        header = text[match.start() : text.find("{", match.start())]
        guarded = _SENDER_GUARD.search(body) or _SENDER_GUARD.search(header)
        if _LOW_LEVEL_CALL.search(body) and not guarded:
            return True
    return False


_RUST_FN = re.compile(r"\bfn\s+(\w+)\s*\(")
_RUST_AUTH = re.compile(r"\bauthority\b")
_RUST_GUARD = re.compile(
    r"require_keys_eq!|require!\(|ensure!\(|assert_\w+\(|check_owner|"
    r"is_authorized|validate|CheckedFrom",
)
_RUST_FRAME = re.compile(r"Ctx\s*<|\bPod\b|Pod[A-Z]\w*|get_checked|load_account_type")
_RUST_MARK = re.compile(r"AccountInfo")


def _braced_body(text: str, brace: int) -> str:
    """Return the balanced text after an opening brace."""
    depth = 0
    for index in range(brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1 : index]
    return text[brace + 1 :]


def _rust_authority_unguarded(text: str) -> bool:
    """Flag Rust processors that use an authority without a runtime guard.

    Framework-validated modules (token-2022's Pod/Ctx typing) are exempt:
    accounts are proven at the type level there.
    """
    if not _RUST_MARK.search(text) or _RUST_FRAME.search(text):
        return False
    for match in _RUST_FN.finditer(text):
        if match.group(1).startswith("test"):
            continue
        brace = text.find("{", match.end())
        if brace == -1:
            continue
        body = _braced_body(text, brace)
        if _RUST_AUTH.search(body) and not _RUST_GUARD.search(body):
            return True
    return False


_EXECUTOR_PARAM = re.compile(
    r"function\s+\w+\s*\(([^)]*)\)\s*(?:public|external)", re.DOTALL
)
_EXECUTOR_NAME = re.compile(
    r"address\s+(?:calldata\s+|memory\s+)?(solver|executor|worker|relayer|handler)\b"
)
_EXECUTOR_GUARD = re.compile(
    r"allowed|whitelist|isExecutor|hasRole|onlyRole|msg\.sender\s*==", re.IGNORECASE
)
_V3_CALLBACK = re.compile(r"uniswapV3FlashCallback|UniswapV3FlashCallback")
_V3_FACTORY_REF = re.compile(r"[Ff]actory")
_OM_REF = re.compile(r"OptimisticOracle|receiveProposal|IOptimisticOracle")
_OM_PAYOUT = re.compile(r"function\s+\w*(claim|payout|resolveAndClaim)\w*\s*\(")


def _caller_supplied_executor(text: str) -> bool:
    """Flag functions that low-level-call an address chosen by the caller.

    Postmortem class: ether.fi AtomicQueue (2026-09) — a caller-supplied
    ``solver`` handled user funds with no membership check.
    """
    for match in _EXECUTOR_PARAM.finditer(text):
        name = _EXECUTOR_NAME.search(match.group(1))
        if name is None:
            continue
        param = name.group(1)
        body = _exec_body(text, match.start())
        if (
            f"{param}.call(" in body or f"{param}.functionCall(" in body
        ) and not _EXECUTOR_GUARD.search(body):
            return True
    return False


def _unverified_pool_callback(text: str) -> bool:
    """Flag V3 flash callbacks paying a caller-chosen payer with no factory check.

    Postmortem class: BNB DEX-router drain (2026-09) — fake pool re-entered the
    router callback and ``transferFrom(payer, ...)`` drained victims.
    """
    return bool(
        _V3_CALLBACK.search(text)
        and "transferFrom(" in text
        and not _V3_FACTORY_REF.search(text)
    )


def _om_oracle_consumer(text: str) -> bool:
    """Flag consumers of the Optimistic Oracle that pay out on proposals.

    Postmortem class: Cozy Finance (Optimism, 2026-09) — a fraudulent UMA
    answer survived the liveness window and drained the protection reserve.
    """
    return bool(_OM_REF.search(text) and _OM_PAYOUT.search(text))


_CHECKS: tuple[tuple[str, Callable[[str], bool]], ...] = (
    (INFLATION_EXPOSED, _inflation_exposed),
    (YUL_DISPATCH, _yul_dispatch),
    (WIDE_SHIFT_MATH, _wide_shift_math),
    (SPOT_PRICE_ORACLE, _spot_price_oracle),
    (UNPROTECTED_EXEC, _unprotected_exec),
    (AUTHORITY_UNGUARDED, _rust_authority_unguarded),
    (CALLER_EXECUTOR, _caller_supplied_executor),
    (UNVERIFIED_POOL_CALLBACK, _unverified_pool_callback),
    (OM_ORACLE_CONSUMER, _om_oracle_consumer),
)


def source_smells(text: str) -> list[str]:
    """Return the smell flags present in a source text, sorted."""
    flags = [name for name, check in _CHECKS if check(text)]
    return sorted(flags)
