"""Tests for the thin-liquidity collateral screen."""

import json
from pathlib import Path
from typing import Any

import pytest

from ruin.core.thin import ScreenParams, ThinCollateralReport, depth_model
from ruin.services import operations_builders_thin as th_bh
from ruin.services import operations_ext_thin as th

_TOK = "0x" + "a1" * 20
_MKT = "0x" + "b2" * 20
_FAC = "0x" + "c3" * 20
_P1 = "0x" + "d4" * 20
_P2 = "0x" + "e5" * 20
_P3 = "0x" + "33" * 20
_STALE = "0x" + "44" * 20
_Q1 = "0x" + "11" * 20
_Q2 = "0x" + "22" * 20
_HEAD = "0x3e8"


class _Proc:
    """Canned subprocess result."""

    def __init__(self, stdout: str, returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


def _pad(addr: str) -> str:
    return "0x" + "0" * 24 + addr[2:]


def _log(pair: str, token0: str, token1: str) -> dict[str, object]:
    return {
        "address": _FAC,
        "topics": [th._PAIR_CREATED, _pad(token0), _pad(token1), _pad(pair)],
        "data": "0x0",
    }


def _logs_json() -> str:
    return json.dumps(
        [
            _log(_P1, _TOK, _Q1),
            _log(_P2, _Q2, _TOK),
            _log(_P3, _Q1, _Q2),
            _log(_STALE, _TOK, _Q2),
        ]
    )


_SIDES = {
    _P1: (_TOK, _Q1),
    _P2: (_Q2, _TOK),
    _P3: (_Q1, _Q2),
    _STALE: (_Q2, _Q1),
}


def _dispatch(reserves: dict[str, tuple[int, int]], **flags: Any) -> Any:
    def _run(cmd: list[str], **_kw: Any) -> _Proc:
        joined = " ".join(cmd)
        out, rc = "", 1
        if cmd[1] == "logs":
            rc = int(flags.get("logs_rc", 0))
            out = "" if rc else str(flags.get("logs_text", _logs_json()))
        elif cmd[1] == "call" and "getReserves" in joined:
            r0, r1 = reserves.get(cmd[2], (0, 0))
            out, rc = f"{r0} [1e18]\n{r1} [1e18]\n1700000000 [1.7e9]", 0
        elif cmd[1] == "call" and "token0()" in joined:
            out, rc = _SIDES[cmd[2]][0], 0
        elif cmd[1] == "call" and "token1()" in joined:
            out, rc = _SIDES[cmd[2]][1], 0
        elif cmd[1] == "call" and "decimals()" in joined:
            ok = not flags.get("decimals_fail")
            out, rc = ("18 [uint256]" if ok else "", 0 if ok else 1)
        elif cmd[1] == "call" and "balanceOf" in joined:
            ok = not flags.get("balance_fail")
            text = f"{flags.get('balance', 100 * 10**18)} [1e18]"
            out, rc = (text if ok else "", 0 if ok else 1)
        return _Proc(out, rc)

    return _run


@pytest.fixture
def chain_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the chain head so the scan window is deterministic."""
    monkeypatch.setattr(th, "jsonrpc", lambda *_a, **_k: _HEAD)


def _params(**overrides: Any) -> ScreenParams:
    knobs: dict[str, Any] = {"price_usd": 1.0, "blocks": 1000, "min_usd": 0.01}
    knobs.update(overrides)
    return ScreenParams(**knobs)


def _screen(
    monkeypatch: pytest.MonkeyPatch, reserves: dict[str, tuple[int, int]], **flags: Any
) -> ThinCollateralReport:
    monkeypatch.setattr(th, "run_command", _dispatch(reserves, **flags))
    return th.thin_collateral_data(_TOK, _MKT, _FAC, "http://rpc", _params())


def test_exposed_when_market_usd_dwarfs_depth(
    chain_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = _screen(
        monkeypatch,
        {_P1: (30 * 10**18, 60 * 10**18), _P2: (60 * 10**18, 10 * 10**18)},
    )
    assert data.verdict == "thin-collateral-exposed"


def test_clean_when_depth_covers_market(
    chain_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = _screen(
        monkeypatch,
        {_P1: (2000 * 10**18, 60 * 10**18), _P2: (60 * 10**18, 1000 * 10**18)},
    )
    assert data.verdict == "clean"
    assert data.signals == ()


def test_token_reserves_are_read_from_either_side(
    chain_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    reserves = {_P1: (30 * 10**18, 60 * 10**18), _P2: (60 * 10**18, 10 * 10**18)}
    data = _screen(monkeypatch, reserves)
    by_pair = {row.pair: row for row in data.pools}
    assert by_pair[_P1].depth_raw == depth_model(60 * 10**18, 30 * 10**18, 18, 18)
    assert by_pair[_P2].depth_raw == depth_model(60 * 10**18, 10 * 10**18, 18, 18)


def test_signal_reports_the_exposure_ratio(
    chain_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = _screen(
        monkeypatch,
        {_P1: (30 * 10**18, 60 * 10**18), _P2: (60 * 10**18, 10 * 10**18)},
    )
    depth = round(depth_model(60 * 10**18, 30 * 10**18, 18, 18) / 10**18, 2) + round(
        depth_model(60 * 10**18, 10 * 10**18, 18, 18) / 10**18, 2
    )
    assert data.signals == (f"market-usd-over-depth:{100.0 / depth:.1f}x",)


def test_stale_pair_log_is_skipped(
    chain_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = _screen(
        monkeypatch,
        {_P1: (30 * 10**18, 60 * 10**18), _P2: (60 * 10**18, 10 * 10**18)},
    )
    pairs = {row.pair for row in data.pools}
    assert data.pairs_found == 3
    assert _STALE not in pairs
    assert pairs == {_P1, _P2}


def test_dust_pools_are_dropped_below_min_usd(
    chain_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        th,
        "run_command",
        _dispatch({_P1: (10 * 10**18, 60 * 10**18), _P2: (60 * 10**18, 10 * 10**18)}),
    )
    data = th.thin_collateral_data(
        _TOK, _MKT, _FAC, "http://rpc", _params(min_usd=50000.0)
    )
    assert data.verdict == "thin-collateral-exposed"
    assert data.pools == ()
    assert data.signals == ("no-usable-pool-depth",)


def test_no_pools_when_scan_finds_no_token_pairs(
    chain_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        th, "run_command", _dispatch({}, logs_text=json.dumps([_log(_P3, _Q1, _Q2)]))
    )
    data = th.thin_collateral_data(_TOK, _MKT, _FAC, "http://rpc", _params())
    assert data.verdict == "no-pools"
    assert data.signals == ("no-pair-created-logs",)


def test_balance_read_failure_is_inconclusive(
    chain_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = _screen(
        monkeypatch,
        {_P1: (30 * 10**18, 60 * 10**18)},
        balance_fail=True,
    )
    assert data.verdict == "probe-inconclusive"
    assert data.signals == ("balance-read-failed",)
    assert data.market_usd == 0.0


def test_log_scan_failure_raises(
    chain_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(th, "run_command", _dispatch({}, logs_rc=1))
    with pytest.raises(RuntimeError, match="PairCreated log scan failed"):
        th.thin_collateral_data(_TOK, _MKT, _FAC, "http://rpc", _params())


def test_non_json_log_output_raises(
    chain_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(th, "run_command", _dispatch({}, logs_text="not json"))
    with pytest.raises(RuntimeError, match="was not JSON"):
        th.thin_collateral_data(_TOK, _MKT, _FAC, "http://rpc", _params())


def test_log_output_that_is_not_a_list_raises(
    chain_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(th, "run_command", _dispatch({}, logs_text='{"a": 1}'))
    with pytest.raises(RuntimeError, match="was not a JSON list"):
        th.thin_collateral_data(_TOK, _MKT, _FAC, "http://rpc", _params())


@pytest.mark.parametrize(
    ("bad", "label"),
    [("nonsense", "token"), ("0xdeadbeef", "market"), ("factory-face", "factory")],
)
def test_malformed_addresses_raise(
    chain_env: None, monkeypatch: pytest.MonkeyPatch, bad: str, label: str
) -> None:
    monkeypatch.setattr(th, "run_command", _dispatch({}))
    token, market, factory = _TOK, _MKT, _FAC
    if label == "token":
        token = bad
    elif label == "market":
        market = bad
    else:
        factory = bad
    with pytest.raises(ValueError, match=f"{label} must be a 0x-prefixed"):
        th.thin_collateral_data(token, market, factory, "http://rpc", _params())


def test_decimals_fallback_assumes_eighteen(
    chain_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = _screen(
        monkeypatch,
        {_P1: (30 * 10**18, 60 * 10**18)},
        decimals_fail=True,
    )
    assert data.decimals == 18
    assert data.market_usd == 100.0


def test_scan_window_is_clamped_to_the_chain_head(
    chain_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(th, "run_command", _dispatch({}))
    data = th.thin_collateral_data(_TOK, _MKT, _FAC, "http://rpc", _params(blocks=5000))
    assert data.from_block == 0
    assert data.to_block == 1000
    assert data.blocks == 1001


def test_markdown_and_json_wiring(
    chain_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        th,
        "run_command",
        _dispatch({_P1: (30 * 10**18, 60 * 10**18), _P2: (60 * 10**18, 10 * 10**18)}),
    )
    kwargs = {
        "token": _TOK,
        "market": _MKT,
        "factory": _FAC,
        "rpc": "http://rpc",
        "chain": "ethereum",
        "price_usd": 1.0,
        "blocks": 1000,
        "min_usd": 0.01,
    }
    out = th_bh.THIN_OPERATIONS["thin-collateral"](kwargs)
    assert "# Thin collateral" in out
    assert "verdict: thin-collateral-exposed" in out
    payload = th_bh.THIN_BUILDERS["thin-collateral"](kwargs)
    assert isinstance(payload, dict)
    assert payload["token"] == _TOK


def test_out_writes_the_markdown_report(
    chain_env: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(th, "run_command", _dispatch({_P1: (30 * 10**18, 60 * 10**18)}))
    report = tmp_path / "thin.md"
    kwargs = {
        "token": _TOK,
        "market": _MKT,
        "factory": _FAC,
        "rpc": "http://rpc",
        "chain": "ethereum",
        "price_usd": 1.0,
        "blocks": 1000,
        "min_usd": 0.01,
        "out": str(report),
    }
    result = th_bh.THIN_OPERATIONS["thin-collateral"](kwargs)
    assert result == f"wrote {report}"
    assert "verdict: thin-collateral-exposed" in report.read_text(encoding="utf-8")
