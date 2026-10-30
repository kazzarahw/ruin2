"""Tests for the offline decode helpers behind ``bytecode selectors``."""

from pathlib import Path
from unittest.mock import patch

from ruin.services import operations_ext_decode as dec


def test_bare_selector_resolves_without_file() -> None:
    matches = {"540e4832": "transfer(address,uint256)"}
    with patch.object(dec, "resolve_selectors", lambda _s: matches):
        out = dec.decode_text("0x540e4832", True)
    assert "format: selector" in out
    assert "match: transfer(address,uint256)" in out


def test_bare_selector_unknown_when_no_match() -> None:
    with patch.object(dec, "resolve_selectors", lambda _s: {}):
        out = dec.decode_text("0xdeadbeef", True)
    assert "match: unknown" in out


def test_existing_file_is_read_as_code(tmp_path: Path) -> None:
    code = tmp_path / "code.txt"
    code.write_text("hello world this is not hex at all", encoding="utf-8")
    out = dec.decode_text(str(code), False)
    assert "format:" in out


def test_read_code_falls_back_to_literal(tmp_path: Path) -> None:
    missing = tmp_path / "absent.hex"
    assert dec.read_code("0x6001") == "0x6001"
    assert dec.read_code(str(missing)) == str(missing)


def test_decode_data_from_file(tmp_path: Path) -> None:
    code = tmp_path / "code.hex"
    code.write_text("0x0061736d00000001", encoding="utf-8")
    data = dec.decode_data(str(code))
    assert isinstance(data, dict)
    assert data.get("format") == "wasm"


def test_decode_data_bare_selector() -> None:
    data = dec.decode_data("0x540e4832")
    assert isinstance(data, dict)
    assert data.get("format") == "selector"
    assert data.get("selectors") == ["540e4832"]
