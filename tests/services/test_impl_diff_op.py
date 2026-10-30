"""Tests for the implementation-diff operation."""

from typing import Any, cast
from unittest.mock import patch

from ruin.services import operations_ext_diff as dif

OLD_CODE = "0x60806040632e1a7d4d1460016000638814fa271460026000"
NEW_CODE = "0x60806040632e1a7d4d146001600063deadbeef1460026000"


def _codes(_rpc: str, address: str) -> str:
    return NEW_CODE if address == "0xNEW" else OLD_CODE


def test_impl_diff_reports_added_and_removed() -> None:
    with patch.object(dif, "code_at", side_effect=_codes):
        out = dif.DIFF_OPERATIONS["impl-diff"](
            {"new_impl": "0xNEW", "old_impl": "0xOLD", "rpc": "http://rpc"}
        )
    assert "1 added, 1 removed" in out
    assert "0xdeadbeef" in out
    assert "0x8814fa27" in out


def test_impl_diff_flags_new_drain_selectors() -> None:
    flipped = "0x60806040632e1a7d4d1460016000638814fa271460026000"  # new has withdraw()
    plain = "0x60806040632e1a7d4d1460016000"

    def _swap(_rpc: str, address: str) -> str:
        return flipped if address == "0xNEW" else plain

    with patch.object(dif, "code_at", side_effect=_swap):
        out = dif.DIFF_OPERATIONS["impl-diff"](
            {"new_impl": "0xNEW", "old_impl": "0xOLD", "rpc": "http://rpc"}
        )
    assert "DRAIN-SHAPED NEW SELECTORS: 0x8814fa27" in out


def test_impl_diff_json_builder() -> None:
    from ruin.services import operations_builders_agent as builders

    with patch("ruin.services.operations_ext_diff.code_at", side_effect=_codes):
        data = builders.AGENT_BUILDERS["impl-diff"](
            {"new_impl": "0xNEW", "old_impl": "0xOLD", "rpc": "http://rpc"}
        )
    doc = cast("dict[str, Any]", data)
    assert doc["added"] == ["0xdeadbeef"]
    assert doc["removed"] == ["0x8814fa27"]


def test_impl_diff_registered() -> None:
    from ruin.services.operations import _OPERATIONS

    assert "impl-diff" in cast("dict[str, Any]", _OPERATIONS)


def test_impl_diff_uses_old_rpc_for_old_side() -> None:
    seen: list[list[str]] = []

    def _run(cmd: list[str], **_kw: Any) -> Any:
        seen.append(cmd)

        class Result:
            stdout = "0x6001"
            stderr = ""
            returncode = 0

        return Result()

    from ruin.services import operations_ext_selectors as sel_mod

    with patch.object(sel_mod, "run_command", side_effect=_run):
        out = dif.DIFF_OPERATIONS["impl-diff"](
            {
                "new_impl": "0xNEW",
                "old_impl": "0xOLD",
                "rpc": "http://new-rpc",
                "old_rpc": "http://old-rpc",
            }
        )
    rpcs = [cmd[-1] for cmd in seen if cmd[0] == "cast"]
    assert "http://old-rpc" in rpcs
    assert "WARNING" not in out
