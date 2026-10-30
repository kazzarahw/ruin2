"""Tests for subprocesses."""

from ruin.services.subprocesses import (
    anvil_command,
    cast_balance_command,
    forge_script_command,
    parse_cast_int,
    slither_command,
)


def test_commands() -> None:
    assert anvil_command(1, "u")[0] == "anvil"
    assert cast_balance_command("e", "a", "w")[0] == "cast"
    assert forge_script_command("e", "t")[0] == "forge"
    assert slither_command("s")[0] == "slither"


def test_parse_cast_int_formats() -> None:
    assert parse_cast_int("123.456000") == 123456
    assert parse_cast_int("123 [123e3]") == 123
    assert parse_cast_int("0xff") == 255
    assert parse_cast_int("1,000_000") == 1000000
    assert parse_cast_int("") == 0
