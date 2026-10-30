"""Tests for subprocess helpers and new service paths."""

from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from ruin.services import subprocesses as sp


def test_anvil_command_with_fork_block() -> None:
    cmd = sp.anvil_command(8545, "http://rpc", fork_block=12345)
    assert "--fork-block-number" in cmd
    assert "12345" in cmd


def test_anvil_command_without_fork_block() -> None:
    cmd = sp.anvil_command(8545, "http://rpc")
    assert "--fork-block-number" not in cmd


def test_cast_native_balance_command() -> None:
    cmd = sp.cast_native_balance_command("http://rpc", "0xwallet")
    assert "balance" in cmd
    assert "0xwallet" in cmd


def test_cast_storage_command() -> None:
    cmd = sp.cast_storage_command("http://rpc", "0xaddr", "0xslot")
    assert "storage" in cmd
    assert "0xaddr" in cmd


def test_cast_logs_command() -> None:
    cmd = sp.cast_logs_command("http://rpc", "0xaddr", 100, 200)
    assert "logs" in cmd
    idx = cmd.index("--address")
    assert cmd[idx + 1] == "0xaddr"
    assert "--from-block" in cmd
    assert "100" in cmd
    assert "--to-block" in cmd
    assert "200" in cmd


def test_forge_script_custom_key() -> None:
    cmd = sp.forge_script_command("http://rpc", "MyTest", private_key="0xMYKEY")
    assert "0xMYKEY" in cmd


def test_run_command_timeout() -> None:
    import subprocess

    with patch.object(subprocess, "run") as mock_run:
        mock_run.return_value = cast("Any", None)
        try:
            sp.run_command(["true"], timeout=99.0)
        except Exception:
            pass
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 99.0


def test_scan_logs_parses_output() -> None:
    from ruin.services import forensics as fs

    def fake_run(cmd: list[str], timeout: float = 60.0) -> Any:
        lo = int(cmd[cmd.index("--from-block") + 1])
        out = (
            "150 0xdeadbeef Transfer addr1 addr2\n151 0xcafe Swap amount"
            if lo == 100
            else ""
        )

        class P:
            stdout = out
            returncode = 0

        return P()

    cast("Any", fs).run_command = fake_run
    scan = fs.scan_logs("0xabc", "http://rpc", 100, 200)
    assert len(scan.entries) == 2
    assert scan.entries[0].block == 150


def test_proxy_service_resolve() -> None:
    from ruin.services import proxy as proxy_svc

    call_count = [0]
    responses = [
        "0x00000000000000000000000000000000000000000000000000000000abcdef1234567890ab",
        "0x000000000000000000000000000000000000000000000000000000001234567890abcdef12",
        "0x0",
    ]

    def fake_run(*args: Any, **kwargs: Any) -> Any:
        class P:
            stdout = responses[call_count[0] % 3]
            returncode = 0

        call_count[0] += 1
        return P()

    cast("Any", proxy_svc).run_command = fake_run
    info = proxy_svc.resolve_proxy_onchain("0xProxy", "http://rpc")
    assert info.is_proxy
    assert info.address == "0xProxy"


def test_resolve_selectors_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    from ruin.services import http as http_svc

    class FakeResp:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {"results": [{"text_signature": "transfer(address,uint256)"}]}

    def fake_get(url: str, **kw: Any) -> FakeResp:
        return FakeResp()

    monkeypatch.setattr(httpx, "get", fake_get)
    result = http_svc.resolve_selectors(["a9059cbb"])
    assert result["a9059cbb"] == "transfer(address,uint256)"


def test_proxy_service_detects_eip7702_delegation() -> None:
    from ruin.services import proxy as proxy_svc

    def fake_run(cmd: Any, *args: Any, **kwargs: Any) -> Any:
        class P:
            returncode = 0
            stdout = (
                "0xef01001ab62413e0cf2ebeb73da7d40c70e7202ae14467"
                if "code" in cmd
                else "0x0"
            )

        return P()

    cast("Any", proxy_svc).run_command = fake_run
    info = proxy_svc.resolve_proxy_onchain("0xDelegated", "http://rpc")
    assert info.is_proxy
    assert info.delegated_to == "0x1ab62413e0cf2ebeb73da7d40c70e7202ae14467"


def test_ensure_solc_uses_existing_binary(tmp_path: Path) -> None:
    from ruin.services.solc import ensure_solc

    binary = tmp_path / "0.5.16" / "solc-0.5.16"
    binary.parent.mkdir()
    binary.write_bytes(b"\x7fELF" + b"\x00" * 2_000_000)
    assert ensure_solc("0.5.16", svm_dir=tmp_path) == str(binary)


def test_ensure_solc_downloads_missing_binary(tmp_path: Path) -> None:
    from ruin.services.solc import ensure_solc

    doc: dict[str, object] = {
        "builds": [{"longVersion": "0.5.16+commit.9c3226ce", "path": "solc-0.5.16.bin"}]
    }
    blob = b"\x7fELF" + b"\x00" * 2_000_000
    got = ensure_solc(
        "0.5.16",
        svm_dir=tmp_path,
        fetch_json=lambda _url: doc,
        fetch_bytes=lambda _url: blob,
    )
    assert got == str(tmp_path / "0.5.16" / "solc-0.5.16")
    assert (tmp_path / "0.5.16" / "solc-0.5.16").exists()


def test_pick_solc_pins_exact_pragma_file(tmp_path: Path) -> None:
    from ruin.services.solc import pick_solc

    src = tmp_path / "Pair.sol"
    src.write_text("pragma solidity =0.5.16;", encoding="utf-8")
    svm = tmp_path / "svm" / "0.5.16"
    svm.mkdir(parents=True)
    (svm / "solc-0.5.16").write_bytes(b"\x7fELF" + b"\x00" * 2_000_000)
    assert pick_solc(src, svm_dir=tmp_path / "svm") == str(svm / "solc-0.5.16")


def test_slither_command_appends_solc_flag() -> None:
    from ruin.services.subprocesses import slither_command

    assert slither_command("x.sol") == ["slither", "x.sol", "--json", "-"]
    assert slither_command("x.sol", "/opt/solc")[-2:] == ["--solc", "/opt/solc"]


def test_family_pick_prefers_highest_numeric_patch(tmp_path: Path) -> None:
    from ruin.services.solc import pick_solc

    src = tmp_path / "a.sol"
    src.write_text(
        "// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\n", encoding="utf-8"
    )
    svm = tmp_path / "svm"
    for v in ("0.8.4", "0.8.37", "0.8.9"):
        d = svm / v
        d.mkdir(parents=True)
        (d / f"solc-{v}").write_bytes(b"\x7fELF")
    assert pick_solc(src, svm_dir=svm) == str(svm / "0.8.37" / "solc-0.8.37")


def test_latest_family_patch_is_numeric_not_lexicographic() -> None:
    from ruin.services.solc import _latest_family_patch

    doc: dict[str, object] = {
        "builds": [
            {"longVersion": "0.8.4+abc"},
            {"longVersion": "0.8.9+xyz"},
            {"longVersion": "0.8.37+def"},
            {"longVersion": "0.7.6+q"},
        ]
    }
    assert _latest_family_patch("0.8", lambda _u: doc) == "0.8.37"


def test_resolve_selectors_canonical_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    from ruin.services import http as http_svc

    class JunkResp:
        status_code = 200

        def json(self) -> dict[str, object]:
            return {"results": [{"text_signature": "workMyDirefulOwner(uint256)"}]}

    def junk_get(url: str, **kw: Any) -> JunkResp:
        return JunkResp()

    monkeypatch.setattr(httpx, "get", junk_get)
    result = http_svc.resolve_selectors(["a9059cbb", "deadbeef"])
    assert result["a9059cbb"] == "transfer(address,uint256)"
    assert result["deadbeef"] == "workMyDirefulOwner(uint256)"
