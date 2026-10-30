"""Tests for the hunt operation with mocked RPC and Sourcify."""

from typing import Any
from unittest.mock import patch

import pytest

import ruin.services.operations_ext_hunt as hunt_op
from ruin.core.chains import resolve_rpc

_CODE = "0x6001600163a9059cbb146370a08231146323b872dd1463095ea7b3146340c10f1914"
_TOK = "0x" + "a1" * 20
_TOK_BAD = "0x" + "b2" * 20
_TOK_C = "0x" + "c3" * 20
_TOK_D = "0x" + "d4" * 20


def _fake_jsonrpc(_t: Any, _url: str, method: str, params: list[Any]) -> Any:
    if method == "eth_blockNumber":
        return hex(3000)
    if method == "eth_getLogs":
        return [
            {
                "topics": ["0xt0", "0xfrom", "0x000000000000000000000000" + "ab" * 20],
                "data": "0x" + "0" * 53 + "470de45ba00",
            }
        ]
    if method == "eth_getCode":
        return _CODE if params and params[0] != _TOK_BAD else "0x"
    if method == "eth_call":
        return "0x" + "0" * 63 + "6"
    return None


class _Resp:
    status_code = 200

    @staticmethod
    def json() -> dict[str, object]:
        return {"match": True}


def test_hunt_finds_mintable_recipient() -> None:
    with (
        patch.object(hunt_op, "jsonrpc", side_effect=_fake_jsonrpc),
        patch.object(hunt_op.httpx, "get", return_value=_Resp()),
    ):
        data = hunt_op.hunt_data((_TOK,), "http://rpc", 60, 2000.0, 10)
    rows = data.candidates
    assert rows
    assert rows[0].mintable
    assert rows[0].verified
    assert data.recipients >= 1


def test_hunt_renders_table() -> None:
    import ruin.services.operations_builders_hunt as hunt_bh

    with (
        patch.object(hunt_op, "jsonrpc", side_effect=_fake_jsonrpc),
        patch.object(hunt_op.httpx, "get", return_value=_Resp()),
    ):
        out = hunt_bh.HUNT_OPERATIONS["hunt"](
            {"token": _TOK, "rpc": "http://rpc", "blocks": 60}
        )
    assert "# Hunt" in out
    assert "ab" * 20 in out


def test_hunt_multi_token_tracks_both_flows() -> None:
    """--also tokens merge into one recipient/USD table."""

    def _two(_t: Any, _u: str, method: str, params: list[Any]) -> Any:
        if method == "eth_blockNumber":
            out: Any = hex(200)
        elif method == "eth_getLogs":
            who = "ab" * 20 if params[0]["address"] == _TOK else "cd" * 20
            out = [
                {
                    "topics": [
                        "0xt0",
                        "0xfrom",
                        "0x000000000000000000000000" + who,
                    ],
                    "data": "0x" + "0" * 53 + "470de45ba00",
                }
            ]
        elif method == "eth_getCode":
            out = _CODE
        elif method == "eth_call":
            out = "0x" + "0" * 63 + "6"
        else:
            out = None
        return out

    with (
        patch.object(hunt_op, "jsonrpc", side_effect=_two),
        patch.object(hunt_op.httpx, "get", return_value=_Resp()),
    ):
        data = hunt_op.hunt_data((_TOK, _TOK_C), "http://rpc", 100, 500.0, 10)
    assert data.recipients == 2
    addrs = {r.address for r in data.candidates}
    assert "0x" + "ab" * 20 in addrs
    assert "0x" + "cd" * 20 in addrs
    assert len(data.tokens) == 2


def test_decimals_of_defaults_to_18_on_junk() -> None:
    def _junk(_t: Any, _u: str, method: str, _p: list[Any]) -> Any:
        return "0x" if method == "eth_call" else None

    with patch.object(hunt_op, "jsonrpc", side_effect=_junk):
        assert hunt_op.decimals_of("http://rpc", _TOK_D) == 18


def test_decimals_of_clamps_absurd_values() -> None:
    def _huge(_t: Any, _u: str, method: str, _p: list[Any]) -> Any:
        return "0x" + "f" * 64 if method == "eth_call" else None

    with patch.object(hunt_op, "jsonrpc", side_effect=_huge):
        assert hunt_op.decimals_of("http://rpc", _TOK_D) == 18


def test_hunt_rejects_token_without_code() -> None:
    import pytest

    def _nocode(_t: Any, _u: str, method: str, params: list[Any]) -> Any:
        if method == "eth_blockNumber":
            return hex(3000)
        if method == "eth_getCode":
            return "0x"
        return None

    with (
        patch.object(hunt_op, "jsonrpc", side_effect=_nocode),
        pytest.raises(ValueError, match="no code"),
    ):
        hunt_op.hunt_data((_TOK_BAD,), "http://rpc", 60, 2000.0, 10)


def test_hunt_scales_usd_by_live_price(monkeypatch: pytest.MonkeyPatch) -> None:
    from ruin.services import operations_ext_hunt as hunt_op

    monkeypatch.setattr(
        hunt_op, "coin_meta", lambda _slug, _token: {"price": 2000.0, "decimals": 8}
    )
    monkeypatch.setattr(hunt_op, "jsonrpc", lambda _t, _u, _m, _p=None: "0x2105")
    calls: list[int] = []
    real_scan = hunt_op.scan_recipients

    def _spy_scan(
        _rpc: str, _token: str, _latest: int, _blocks: int, min_raw: int
    ) -> tuple[dict[str, int], int, int]:
        calls.append(min_raw)
        return {}, 0, 1

    monkeypatch.setattr(hunt_op, "scan_recipients", _spy_scan)
    data = hunt_op.hunt_data((_TOK_C,), "http://rpc", 100, 4000.0, 10)
    assert calls == [int(4000 / 2000.0 * 10**8)]
    assert data.price == 2000.0
    assert data.decimals == 8
    assert data.recipients == 0
    assert real_scan is not None


def test_resolve_rpc_prefers_explicit_endpoint() -> None:
    assert resolve_rpc("http://mine", "base") == "http://mine"


def test_resolve_rpc_uses_chain_table() -> None:
    assert resolve_rpc(None, "Arbitrum") == "https://arb1.arbitrum.io/rpc"


def test_resolve_rpc_knows_new_chain_endpoints() -> None:
    assert resolve_rpc(None, "megaeth") == "https://mainnet.megaeth.com/rpc"
    assert resolve_rpc(None, "robinhood") == ("https://rpc.mainnet.chain.robinhood.com")
    assert resolve_rpc(None, "hemi") == "https://rpc.hemi.network/rpc"
    assert resolve_rpc(None, "tempo") == "https://rpc.tempo.xyz"
    assert resolve_rpc(None, "soneium") == "https://rpc.soneium.org"
    assert resolve_rpc(None, "gnosis") == "https://rpc.gnosischain.com"
    assert resolve_rpc(None, "celo") == "https://forno.celo.org"
    assert resolve_rpc(None, "tac") == "https://rpc.tac.build"
    assert resolve_rpc(None, "fraxtal") == "https://rpc.frax.com"


def test_resolve_rpc_rejects_unknown_chain() -> None:
    with pytest.raises(ValueError, match="unknown chain"):
        resolve_rpc(None, "platypus")


def test_hunt_caps_scan_at_max_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[Any]] = []

    def _fake(
        _transport: object, _url: str, method: str, params: list[object]
    ) -> object:
        calls.append([method, params])
        if method == "eth_blockNumber":
            return hex(20000)
        if method == "eth_getCode":
            return "0x6000"
        if method == "eth_getLogs":
            return []
        return "0x"

    monkeypatch.setattr(hunt_op, "jsonrpc", _fake)
    monkeypatch.setattr(hunt_op, "price_and_decimals", lambda *_a: (1.0, 18))
    hunt_op.hunt_data((_TOK_D,), "http://rpc", 12000, 500.0, 10)
    logs = [c for c in calls if c[0] == "eth_getLogs"]
    first = int(str(logs[0][1][0]["fromBlock"]), 16)
    last = int(str(logs[-1][1][0]["toBlock"]), 16)
    assert last - first == hunt_op._MAX_BLOCKS


def test_hunt_span_overrides_recent_window_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[Any]] = []

    def _fake(
        _transport: object, _url: str, method: str, params: list[object]
    ) -> object:
        calls.append([method, params])
        if method == "eth_blockNumber":
            return hex(20000)
        if method == "eth_getCode":
            return "0x6000"
        if method == "eth_getLogs":
            return []
        return "0x"

    monkeypatch.setattr(hunt_op, "jsonrpc", _fake)
    monkeypatch.setattr(hunt_op, "price_and_decimals", lambda *_a: (1.0, 18))
    data = hunt_op.hunt_data((_TOK_D,), "http://rpc", (5000, 25000), 500.0, 10)
    logs = [c for c in calls if c[0] == "eth_getLogs"]
    first = int(str(logs[0][1][0]["fromBlock"]), 16)
    assert first == 5000
    assert data.from_block == 5000
    assert data.to_block == 20000


def test_hunt_json_builder_honors_from_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ruin.services.operations_builders_agent as agent_bh

    calls: list[list[Any]] = []

    def _fake(
        _transport: object, _url: str, method: str, params: list[object]
    ) -> object:
        calls.append([method, params])
        if method == "eth_blockNumber":
            return hex(20000)
        if method == "eth_getCode":
            return "0x6000"
        if method == "eth_getLogs":
            return []
        return "0x"

    monkeypatch.setattr(hunt_op, "jsonrpc", _fake)
    monkeypatch.setattr(hunt_op, "price_and_decimals", lambda *_a: (1.0, 18))
    agent_bh.AGENT_BUILDERS["hunt"](
        {"token": _TOK, "rpc": "http://rpc", "from_block": 5000, "to_block": 9000}
    )
    logs = [c for c in calls if c[0] == "eth_getLogs"]
    first = int(str(logs[0][1][0]["fromBlock"]), 16)
    assert first == 5000


def test_chain_id_parses_hex_and_falls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hunt_op, "jsonrpc", lambda _t, _u, _m, _p=None: "0x3e7")
    assert hunt_op.chain_id("http://rpc") == 999
    monkeypatch.setattr(hunt_op, "jsonrpc", lambda _t, _u, _m, _p=None: "junk")
    assert hunt_op.chain_id("http://rpc") == 1


def test_is_verified_targets_the_requested_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    class _Resp:
        status_code = 200

        @staticmethod
        def json() -> dict[str, object]:
            return {"match": True}

    def _get(url: str, timeout: float) -> _Resp:
        seen.append(url)
        return _Resp()

    monkeypatch.setattr(hunt_op.httpx, "get", _get)
    assert hunt_op.is_verified("0xabc", 999)
    assert "/v2/contract/999/0xabc" in seen[0]


def test_hunt_data_rejects_token_symbols() -> None:
    with pytest.raises(ValueError, match="0x-prefixed contract address"):
        hunt_op.hunt_data(("USDC",), "https://example.invalid/rpc", 100, 100.0, 10)


def test_hunt_raises_when_all_windows_fail() -> None:
    """A fully RPC-rejected scan is an error, not a silent empty chain."""

    def _flaky(_t: Any, _u: str, method: str, _params: list[Any]) -> Any:
        if method == "eth_blockNumber":
            return hex(200)
        if method == "eth_getLogs":
            return {"code": -32005, "message": "window too large"}
        if method == "eth_getCode":
            return _CODE
        if method == "eth_call":
            return "0x" + "0" * 63 + "12"
        return None

    with (
        patch.object(hunt_op, "jsonrpc", side_effect=_flaky),
        patch.object(hunt_op.httpx, "get", return_value=_Resp()),
        pytest.raises(RuntimeError, match="log windows failed"),
    ):
        hunt_op.hunt_data((_TOK,), "http://rpc", 100, 500.0, 10)


def test_hunt_counts_partial_window_failures() -> None:
    """Partial RPC failures are reported while surviving data is kept."""

    def _half(_t: Any, _u: str, method: str, params: list[Any] | dict[str, Any]) -> Any:
        out: Any = None
        if method == "eth_blockNumber":
            out = hex(200)
        elif method == "eth_getLogs":
            query = params[0] if isinstance(params, list) else params
            if int(str(query["fromBlock"]), 16) >= 150:
                out = {"code": -32005, "message": "burst limit"}
            else:
                out = [
                    {
                        "topics": [
                            "0xt0",
                            "0xfrom",
                            "0x000000000000000000000000" + "ab" * 20,
                        ],
                        "data": "0x" + "0" * 53 + "470de45ba00",
                    }
                ]
        elif method == "eth_getCode":
            out = _CODE
        elif method == "eth_call":
            out = "0x" + "0" * 63 + "6"
        return out

    with (
        patch.object(hunt_op, "jsonrpc", side_effect=_half),
        patch.object(hunt_op.httpx, "get", return_value=_Resp()),
    ):
        data = hunt_op.hunt_data((_TOK,), "http://rpc", 100, 500.0, 10)
    assert data.recipients >= 1
    assert 0 < data.scan_errors < data.scan_windows
