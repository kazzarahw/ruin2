"""Tests for the selectors inventory operation."""

from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from ruin.services import operations_ext_decode as dec
from ruin.services import operations_ext_selectors as sel

IMPL = "0x1111111111111111111111111111111111111111"
ADDR = "0x" + "A" * 40
CLONE = (
    "0x363d3d373d3d3d363d73"
    "1111111111111111111111111111111111111111"
    "5af43d82803e903d91602b57fd5bf3"
)

# PUSH4 pattern embedding two known drain selectors plus one unknown one.
CODE = "0x60806040632e1a7d4d1460016000638814fa27146002600063deadbeef1460036000"


def _fake_run(cmd: list[str], **_kw: Any) -> Any:
    class Result:
        stdout = CODE
        stderr = ""
        returncode = 0

    return Result()


def test_selectors_lists_known_drain_signatures() -> None:
    with patch.object(sel, "run_command", side_effect=_fake_run):
        out = sel.SELECTOR_OPERATIONS["selectors"](
            {"target": ADDR, "rpc": "http://rpc"}
        )
    assert "3 selectors found" in out
    assert "`0x2e1a7d4d` withdraw(uint256)" in out
    assert "0xdeadbeef" in out
    assert "4byte" not in out


def test_selectors_resolve_fills_unknown_signatures() -> None:
    with (
        patch.object(sel, "run_command", side_effect=_fake_run),
        patch.object(sel, "resolve_selectors", return_value={"deadbeef": "mystery()"}),
    ):
        out = sel.SELECTOR_OPERATIONS["selectors"](
            {"target": ADDR, "rpc": "http://rpc", "resolve": True}
        )
    assert "`0xdeadbeef` mystery()" in out


def test_selectors_reports_missing_code() -> None:
    def _empty(_cmd: list[str], **_kw: Any) -> Any:
        class Result:
            stdout = "0x"
            stderr = ""
            returncode = 0

        return Result()

    with patch.object(sel, "run_command", side_effect=_empty):
        out = sel.SELECTOR_OPERATIONS["selectors"](
            {"target": ADDR, "rpc": "http://rpc"}
        )
    assert out == f"no code at {ADDR}"


def test_selectors_registered_in_operations() -> None:
    from ruin.services.operations import _OPERATIONS

    assert "selectors" in cast("dict[str, Any]", _OPERATIONS)


def test_selectors_json_builder_shape() -> None:
    from ruin.services.operations_builders_agent import AGENT_BUILDERS

    with patch.object(sel, "run_command", side_effect=_fake_run):
        data = AGENT_BUILDERS["selectors"]({"target": ADDR, "rpc": "http://rpc"})
    doc = cast("dict[str, Any]", data)
    assert doc["address"] == ADDR
    got = {row["selector"]: row["signature"] for row in doc["selectors"]}
    assert got["0x2e1a7d4d"] == "withdraw(uint256)"
    assert got["0xdeadbeef"] == ""


def test_selectors_follows_minimal_proxy() -> None:
    def _two_step(cmd: list[str], **_kw: Any) -> Any:
        class Result:
            stdout = CODE if IMPL in cmd else CLONE
            stderr = ""
            returncode = 0

        return Result()

    with patch.object(sel, "run_command", side_effect=_two_step):
        out = sel.SELECTOR_OPERATIONS["selectors"](
            {"target": ADDR, "rpc": "http://rpc"}
        )
    assert "minimal proxy -> implementation" in out
    assert "withdraw(uint256)" in out


def test_inventory_prefers_canonical_names_over_4byte_junk() -> None:
    code = "0x6080604063a9059cbb1460016000638da5cb5b1460026000"

    def _run(_cmd: list[str], **_kw: Any) -> Any:
        class Result:
            stdout = code
            stderr = ""
            returncode = 0

        return Result()

    junk = {"a9059cbb": "workMyDirefulOwner(uint256)"}
    with (
        patch.object(sel, "run_command", side_effect=_run),
        patch.object(sel, "resolve_selectors", return_value=junk),
    ):
        pairs = sel.inventory(code, resolve=True)
    labels = dict(pairs)
    assert labels["0xa9059cbb"] == "transfer(address,uint256)"
    assert labels["0x8da5cb5b"] == "owner()"


def test_selectors_follows_eip1967_slot() -> None:
    shell = "0x6080604052600a600c565b005b60186014601a565b6050565b565b"
    slot_word = "0x000000000000000000000000" + IMPL.removeprefix("0x")

    def _dispatch(cmd: list[str], **_kw: Any) -> Any:
        class Result:
            stdout = slot_word if "storage" in cmd else (CODE if IMPL in cmd else shell)
            stderr = ""
            returncode = 0

        return Result()

    with patch.object(sel, "run_command", side_effect=_dispatch):
        out = sel.SELECTOR_OPERATIONS["selectors"](
            {"target": ADDR, "rpc": "http://rpc"}
        )
    assert "eip1967 implementation" in out
    assert "withdraw(uint256)" in out


def test_selectors_offline_decodes_existing_file(tmp_path: Path) -> None:
    code = tmp_path / "code.txt"
    code.write_text("0x60016001636e553f65", encoding="utf-8")
    out = sel.SELECTOR_OPERATIONS["selectors"]({"target": str(code)})
    assert "format: evm" in out
    assert "0x6e553f65" in out


def test_selectors_offline_decodes_bare_selector() -> None:
    with patch.object(dec, "resolve_selectors", lambda _s: {"540e4832": "foo()"}):
        out = sel.SELECTOR_OPERATIONS["selectors"]({"target": "0x540e4832"})
    assert "format: selector" in out
    assert "match: foo()" in out


def test_selectors_offline_json_payload(tmp_path: Path) -> None:
    from ruin.services.operations_builders_agent import AGENT_BUILDERS

    code = tmp_path / "code.hex"
    code.write_text("0x0061736d00000001", encoding="utf-8")
    data = AGENT_BUILDERS["selectors"]({"target": str(code)})
    doc = cast("dict[str, Any]", data)
    assert doc["format"] == "wasm"


def test_is_offline_routing_table(tmp_path: Path) -> None:
    existing = tmp_path / "code.hex"
    existing.write_text("0x6001", encoding="utf-8")
    assert sel.is_offline(str(existing))
    assert sel.is_offline("0xdeadbeef")
    assert not sel.is_offline(ADDR)
    assert not sel.is_offline("nope-missing")


def test_code_at_raises_on_rpc_failure() -> None:
    def _fail(_cmd: list[str], **_kw: Any) -> Any:
        class Result:
            stdout = ""
            stderr = "Error: server returned an error response: 403 Forbidden"
            returncode = 1

        return Result()

    with patch.object(sel, "run_command", side_effect=_fail):
        try:
            sel.code_at("http://rpc", "0xA")
        except RuntimeError as error:
            assert "rpc failure" in str(error)
        else:
            raise AssertionError("expected RuntimeError")
