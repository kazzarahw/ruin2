"""Tests for the signature-gated mint screen."""

from typing import Any

import pytest

from ruin.services import operations_ext_mintsig as ms


class _Proc:
    """Canned subprocess result."""

    def __init__(self, stdout: str, returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


CODE = "0x60016002"


def _dispatch(mint_name: str, owner_code: str, cap_value: str) -> Any:
    def _run(cmd: list[str], **_kw: Any) -> _Proc:
        joined = " ".join(cmd)
        out, rc = "0x", 0
        if cmd[1] == "code":
            out = CODE if cmd[2] == "0xA" else owner_code
        elif cmd[1] == "call" and "owner()" in joined:
            out, rc = "0x" + "11" * 20, 0
        elif cmd[1] == "call" and "getMaxMint" in joined:
            out, rc = cap_value, 0 if cap_value else 1
        elif cmd[1] == "call":
            rc = 1
        return _Proc(out, rc)

    return _run


def _wire(monkeypatch: pytest.MonkeyPatch, runner: Any, mint_name: str) -> None:
    monkeypatch.setattr(ms, "run_command", runner)
    monkeypatch.setattr(ms, "code_at", lambda _rpc, _addr: CODE)
    monkeypatch.setattr(
        ms,
        "inventory",
        lambda _code, **_kw: [("0x12345678", mint_name)],
    )


def test_unbounded_when_owner_eoa_and_no_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sig-mint + EOA owner + missing cap getter => review verdict."""
    _wire(
        monkeypatch,
        _dispatch("mintWithSig(address,bytes)", "0x", ""),
        "mintWithSig(address,bytes)",
    )
    data = ms.mintsig_data("0xA", "http://rpc")
    assert data.verdict == "review"
    flags = data.flags
    assert isinstance(flags, tuple)
    assert "sig-gated-unbounded-mint" in flags
    assert "owner-is-EOA" in flags
    assert "cap-getter-missing" in flags


def test_clean_when_plain_mint_and_contract_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No sig-mint surface and a contract owner keeps the verdict clean."""
    _wire(
        monkeypatch,
        _dispatch("mint(address,uint256)", "0x60fe", ""),
        "mint(address,uint256)",
    )
    data = ms.mintsig_data("0xA", "http://rpc")
    assert data.verdict == "clean"
    assert data.sig_mint == ()


def test_saturated_cap_flags_review(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A maxed-out cap getter is treated as unbounded for review."""
    _wire(
        monkeypatch,
        _dispatch(
            "sweepUnclaimed(address)",
            "0x60fe",
            "115792089237316195423570985008687907832963993957753904306800000000000000000000",
        ),
        "sweepUnclaimed(address)",
    )
    data = ms.mintsig_data("0xA", "http://rpc")
    assert data.cap_saturated is True
    assert data.verdict == "review"


def test_no_code_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty code must raise, not render an empty report."""
    monkeypatch.setattr(ms, "code_at", lambda _rpc, _addr: "0x")
    with pytest.raises(ValueError, match="no code"):
        ms.mintsig_data("0xB", "http://rpc")
