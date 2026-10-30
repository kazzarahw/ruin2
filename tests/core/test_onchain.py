"""Tests for chain-agnostic on-chain read models."""

from __future__ import annotations

from ruin.core.decode import DecodedBytecode
from ruin.core.enums import Chain
from ruin.core.onchain import AccountInfo, BytecodeInfo, ChainDigest, SourceInfo


def test_source_render_caps_display_and_keeps_full_when_dumped() -> None:
    info = SourceInfo(chain=Chain.EVM, address="0x1", source_text="x" * 5000)
    assert "x" * 4000 in info.render_markdown()
    assert "x" * 4001 not in info.render_markdown()
    assert "x" * 5000 in info.render_markdown(full=True)


def test_digest_renders_all_sections() -> None:
    digest = ChainDigest(
        chain=Chain.SOLANA,
        address="So1111",
        account=AccountInfo(
            chain=Chain.SOLANA, address="So1111", exists=True, balance_native="5"
        ),
        bytecode=BytecodeInfo(
            chain=Chain.SOLANA,
            address="So1111",
            kind="bpf",
            size_bytes=100,
            decoded=DecodedBytecode(selectors=["aabbccdd"], strings=["Token"]),
        ),
        source=SourceInfo(
            chain=Chain.SOLANA,
            address="So1111",
            language="Rust",
            verified=True,
            url="http://x",
        ),
        analyzers=["anchor-check"],
    )
    text = digest.render_markdown()
    assert "Account (exists)" in text
    assert "native balance: 5" in text
    assert "Program (bpf, 100 bytes)" in text
    assert "selectors: aabbccdd" in text
    assert "Source (verified, Rust)" in text
    assert "Analyzers available: anchor-check" in text


def test_digest_no_analyzer_note() -> None:
    digest = ChainDigest(chain=Chain.TON, address="EQabc")
    text = digest.render_markdown()
    assert "No chain-native analyzer" in text


def test_digest_missing_account_shows_not_found() -> None:
    digest = ChainDigest(
        chain=Chain.CAIRO,
        address="0x1",
        account=AccountInfo(chain=Chain.CAIRO, address="0x1", exists=False),
    )
    text = digest.render_markdown()
    assert "Account (not found)" in text
