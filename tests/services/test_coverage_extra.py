"""Extra coverage tests."""

from pathlib import Path
from typing import Any, cast

import pytest

from ruin.services import slither as slither_service


def test_run_slither_empty_output() -> None:
    def fake_run(_argv: list[str], *, timeout: float = 30.0) -> Any:
        class P:
            stdout = ""
            stderr = "solc version mismatch"
            returncode = 1

        return P()

    cast("Any", slither_service).run_command = fake_run
    try:
        slither_service.run_slither(Path("x.sol"))
        assert False, "should have raised"
    except RuntimeError as e:
        assert "no JSON" in str(e)


def test_run_slither_timeout_passed() -> None:
    captured: dict[str, float] = {}

    def fake_run(_argv: list[str], *, timeout: float = 30.0) -> Any:
        captured["timeout"] = timeout

        class P:
            stdout = '{"results": {"detectors": []}}'
            returncode = 0

        return P()

    cast("Any", slither_service).run_command = fake_run
    slither_service.run_slither(Path("x.sol"))
    assert captured["timeout"] == 120.0


def test_access_map_service_empty() -> None:
    from ruin.services import access_control as ac_svc

    def fake_run(_argv: list[str], *, timeout: float = 30.0) -> Any:
        class P:
            stdout = "not json"
            returncode = 0

        return P()

    cast("Any", ac_svc).run_command = fake_run
    amap = ac_svc.build_access_map(Path("x.sol"))
    assert amap.contract == "x.sol"
    assert amap.functions == []


def test_access_map_service_with_data() -> None:
    import json

    from ruin.services import access_control as ac_svc

    doc = {
        "results": {
            "printers": [
                {
                    "elements": [
                        {
                            "type": "pretty_table",
                            "name": {
                                "name": "Vault",
                                "content": {
                                    "fields_names": [
                                        "Function",
                                        "State variables written",
                                        "Conditions on msg.sender",
                                    ],
                                    "rows": [
                                        ["withdraw", "['balance']", "['onlyOwner']"]
                                    ],
                                },
                            },
                        }
                    ]
                }
            ]
        }
    }

    def fake_run(_argv: list[str], *, timeout: float = 30.0) -> Any:
        class P:
            stdout = json.dumps(doc)
            returncode = 0

        return P()

    cast("Any", ac_svc).run_command = fake_run
    amap = ac_svc.build_access_map(Path("Vault.sol"))
    assert amap.contract == "Vault"
    assert len(amap.functions) == 1
    assert amap.functions[0].is_guarded


def test_forensics_trace_transaction() -> None:
    from ruin.services import forensics as fs

    def fake_run(*args: Any, **kwargs: Any) -> Any:
        class P:
            stdout = "Step 1: call\nStep 2: delegatecall"
            returncode = 0

        return P()

    cast("Any", fs).run_command = fake_run
    trace = fs.trace_transaction("0xdead", "http://rpc")
    assert trace.tx_hash == "0xdead"
    assert len(trace.steps) == 2


def test_scan_logs_raises_when_rpc_lacks_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ruin.services import forensics as fs

    def fake_run(*_args: Any, **_kwargs: Any) -> Any:
        class P:
            stdout = ""
            stderr = "method eth_getLogs is not supported"
            returncode = 1

        return P()

    monkeypatch.setattr(fs, "run_command", fake_run)
    with pytest.raises(RuntimeError, match="cast logs failed"):
        fs.scan_logs("0xabc", "http://rpc", 1, 2)


def test_trace_raises_when_cast_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    from ruin.services import forensics as fs

    def fake_run(*_args: Any, **_kwargs: Any) -> Any:
        class P:
            stdout = ""
            stderr = "connection reset"
            returncode = 1

        return P()

    monkeypatch.setattr(fs, "run_command", fake_run)
    with pytest.raises(RuntimeError, match="cast tx failed"):
        fs.trace_transaction("0xdead", "http://rpc")


def test_access_map_raises_on_empty_stdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ruin.services import access_control as ac_svc

    def fake_run(*_args: Any, **_kwargs: Any) -> Any:
        class P:
            stdout = ""
            stderr = "pragma version unsupported"
            returncode = 1

        return P()

    monkeypatch.setattr(ac_svc, "run_command", fake_run)
    with pytest.raises(RuntimeError, match="access map"):
        ac_svc.build_access_map(Path("Vault.sol"))
