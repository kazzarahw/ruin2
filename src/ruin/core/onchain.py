"""Chain-agnostic on-chain read models for ``ruin``.

These are pure data holders. Chain adapters in the service layer fill them in;
they carry the raw facts an agent needs to reason about a non-EVM target.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruin.core.decode import DecodedBytecode
    from ruin.core.enums import Chain

_MAX_SELECTORS = 20
_MAX_STRINGS = 10


@dataclass
class AccountInfo:
    """A chain-agnostic account or program record."""

    chain: Chain
    address: str
    exists: bool = False
    balance_native: str = ""
    raw: dict[str, object] = field(default_factory=dict)
    note: str = ""


@dataclass
class BytecodeInfo:
    """A chain-agnostic program / deployed-code record."""

    chain: Chain
    address: str
    kind: str = "bytecode"
    hexcode: str = ""
    size_bytes: int = 0
    decoded: DecodedBytecode | None = None
    note: str = ""


@dataclass
class SourceInfo:
    """A verified source or interface-definition record."""

    chain: Chain
    address: str
    name: str = ""
    language: str = ""
    source_text: str = ""
    url: str = ""
    verified: bool = False
    remappings: tuple[str, ...] = ()
    compiler_version: str = ""

    def render_markdown(self, *, full: bool = False) -> str:
        """Render the source record as Markdown.

        ``full`` keeps the complete source text; otherwise it is capped
        for terminal display.
        """
        state = "verified" if self.verified else "unverified"
        lines: list[str] = [f"# Source — {self.chain.value} {self.address}", ""]
        lines.append(f"- contract: {self.name or 'unknown'}")
        lines.append(f"- language: {self.language or 'unknown'} ({state})")
        if self.url:
            lines.append(f"- url: {self.url}")
        if self.source_text:
            lines.append("")
            lines.append("```solidity")
            lines.append(self.source_text if full else self.source_text[:4000])
            lines.append("```")
        return "\n".join(lines)


@dataclass
class ChainDigest:
    """Everything an agent needs to reason about one target."""

    chain: Chain
    address: str
    account: AccountInfo | None = None
    bytecode: BytecodeInfo | None = None
    source: SourceInfo | None = None
    analyzers: list[str] = field(default_factory=list)

    def render_markdown(self) -> str:
        """Render the digest as Markdown for agent reasoning."""
        lines: list[str] = [f"# Digest — {self.chain.value} {self.address}", ""]
        lines.extend(self._account_lines())
        lines.extend(self._bytecode_lines())
        lines.extend(self._source_lines())
        lines.extend(self._analyzer_lines())
        return "\n".join(lines)

    def _account_lines(self) -> list[str]:
        if self.account is None:
            return []
        exists = "exists" if self.account.exists else "not found"
        lines = [f"## Account ({exists})"]
        if self.account.balance_native:
            lines.append(f"- native balance: {self.account.balance_native}")
        if self.account.note:
            lines.append(f"- note: {self.account.note}")
        lines.append("")
        return lines

    def _bytecode_lines(self) -> list[str]:
        if self.bytecode is None:
            return []
        info = self.bytecode
        lines = [f"## Program ({info.kind}, {info.size_bytes} bytes)"]
        if info.decoded is not None:
            sels = ", ".join(info.decoded.selectors[:_MAX_SELECTORS])
            strs = ", ".join(info.decoded.strings[:_MAX_STRINGS])
            if sels:
                lines.append(f"- selectors: {sels}")
            if strs:
                lines.append(f"- strings: {strs}")
        if info.note:
            lines.append(f"- note: {info.note}")
        lines.append("")
        return lines

    def _source_lines(self) -> list[str]:
        if self.source is None:
            return []
        state = "verified" if self.source.verified else "unverified"
        lines = [f"## Source ({state}, {self.source.language})"]
        if self.source.name:
            lines.append(f"- name: {self.source.name}")
        if self.source.url:
            lines.append(f"- url: {self.source.url}")
        lines.append("")
        return lines

    def _analyzer_lines(self) -> list[str]:
        if self.analyzers:
            return [f"Analyzers available: {', '.join(self.analyzers)}"]
        return ["No chain-native analyzer; reason from source and bytecode."]
