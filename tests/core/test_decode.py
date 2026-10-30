"""Tests for decode."""

from ruin.core.decode import decode_bytecode, decode_uint, sniff_format
from ruin.services.operations import run_operation_json


def test_decode_uint() -> None:
    assert decode_uint("0x0") == 0
    assert decode_uint("0x10") == 16


def test_decode_bytecode() -> None:
    code = "0x60016001 60016001636e553f656001600163a9059cbb".replace(" ", "")
    decoded = decode_bytecode(code)
    assert "6e553f65" in decoded.selectors


def test_sniff_formats() -> None:
    assert sniff_format("0x0061736d01000000") == "wasm"
    assert sniff_format("0x7f454c46020101") == "elf"
    assert sniff_format("0xa55c0002") == "move"
    assert sniff_format("0x60016001") == "evm"
    assert sniff_format('{"abc": 1}') == "cairo"
    assert sniff_format("") == "unknown"


def test_decode_bytecode_tags_format() -> None:
    wasm = decode_bytecode("0x0061736d00000001")
    assert wasm.format == "wasm"
    assert wasm.selectors == []


def test_sniff_calldata() -> None:
    transfer = "0xa9059cbb" + "0" * 64 + "0" * 64
    assert sniff_format(transfer) == "calldata"
    assert sniff_format("0x60016001") == "evm"


def test_decode_calldata() -> None:
    calldata = (
        "0xa9059cbb"
        + "0" * 24
        + "f39fd6e51aad88f6f4ce6ab8827279cfffb92266"
        + "0" * 58
        + "989680"
    )
    decoded = decode_bytecode(calldata)
    assert decoded.format == "calldata"
    assert decoded.selectors == ["a9059cbb"]
    assert len(decoded.args) == 2
    assert decoded.args[0].endswith("f39fd6e51aad88f6f4ce6ab8827279cfffb92266")
    assert decoded.strings == []


def test_decode_bytecode_skips_raw_code_string() -> None:
    code = "0x6001600160016001636e553f656001600163a9059cbb"
    decoded = decode_bytecode(code)
    assert code.removeprefix("0x") not in decoded.strings


def test_decode_json_output_via_selectors() -> None:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "code.hex"
        path.write_text("0x0061736d00000001", encoding="utf-8")
        data = run_operation_json("selectors", {"target": str(path)})
    assert isinstance(data, dict)
    assert data.get("format") == "wasm"
