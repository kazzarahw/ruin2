"""Tests for callTracer tree flattening."""

from ruin.core.forensics import flatten_call_trace


def test_flatten_nested_call_tree() -> None:
    tree: dict[str, object] = {
        "type": "CALL",
        "from": "0xA",
        "to": "0xB",
        "input": "0xa9059cbb00000000",
        "calls": [
            {
                "type": "DELEGATECALL",
                "from": "0xB",
                "to": "0xC",
                "input": "0x095ea7b3ffff",
                "error": "execution reverted",
            }
        ],
    }
    lines = flatten_call_trace(tree)
    assert lines[0] == "CALL 0xA -> 0xB 0xa9059cbb"
    assert lines[1] == "  DELEGATECALL 0xB -> 0xC 0x095ea7b3 [reverted]"


def test_flatten_empty_input_shows_bare_transfer() -> None:
    lines = flatten_call_trace(
        {"type": "CALL", "from": "0xA", "to": "0xB", "input": ""}
    )
    assert lines == ["CALL 0xA -> 0xB 0x"]
