"""Tests for files."""

from pathlib import Path

from ruin.services.files import read_recon, read_vulns, write_text


def test_files(tmp_path: Path) -> None:
    recon = tmp_path / "recon.json"
    recon.write_text(
        '{"tvl_asset": "0x' + "1" * 40 + '", "contracts": []}', encoding="utf-8"
    )
    assert read_recon(recon) == []

    vulns = tmp_path / "vulns.json"
    vulns.write_text("[]", encoding="utf-8")
    assert read_vulns(vulns) == []

    out = tmp_path / "out.txt"
    write_text(out, "hi")
    assert out.read_text() == "hi"
