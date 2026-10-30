"""Pure runtime-bytecode scanners for the unverified-contract review report."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast

from ruin.core.probe import SelectorRow

_PUSH_LOW = 0x60
_PUSH_HIGH = 0x7F
_PUSH32 = 0x7F
_PUSH32_HEX_LEN = 64
_SSTORE = 0x55
_SSTORE_WINDOW = 32
_MAX_PUSH32_WORDS = 8
_MIN_REVERT_RUN = 6
_MAX_REVERT_STRINGS = 40
_VALUE_CALL_PATTERN = re.compile("345a")
_PRINTABLE_RUN = re.compile(rf"[\x20-\x7e]{{{_MIN_REVERT_RUN},}}".encode())
_THIN_DISPATCH_MAX = 4

_WATCHED: dict[int, str] = {
    0xF1: "call",
    0xF4: "delegatecall",
    0xFA: "staticcall",
    _SSTORE: "sstore",
    0xFF: "selfdestruct",
    0xF0: "create",
    0xF5: "create2",
}


def _decode_hex(code: str) -> bytes:
    """Decode runtime bytecode hex (with or without 0x) into raw bytes."""
    body = code.removeprefix("0x").strip().lower()
    try:
        return bytes.fromhex(body)
    except ValueError as error:
        raise ValueError("bytecode must be a hex string") from error


def _walk_stream(
    data: bytes,
) -> tuple[dict[str, int], list[tuple[int, str]], list[int]]:
    """Walk the opcode stream, skipping PUSH immediates, and record landmarks.

    Returns (opcode counts, (offset, word) for each PUSH32, sstore offsets).
    """
    counts: dict[str, int] = dict.fromkeys(_WATCHED.values(), 0)
    pushes: list[tuple[int, str]] = []
    sstores: list[int] = []
    offset = 0
    while offset < len(data):
        op = data[offset]
        name = _WATCHED.get(op)
        if name is not None:
            counts[name] += 1
        width = 1
        if _PUSH_LOW <= op <= _PUSH_HIGH:
            width = op - _PUSH_LOW + 2
            if op == _PUSH32:
                pushes.append((offset, data[offset + 1 : offset + 33].hex()))
        if op == _SSTORE:
            sstores.append(offset)
        offset += width
    return counts, pushes, sstores


def _words_near_sstore(pushes: list[tuple[int, str]], sstores: list[int]) -> list[str]:
    """Return up to 8 distinct PUSH32 words followed closely by an SSTORE.

    A base-slot constant pushed just before a store is the ERC-7201-style
    shape reviewers want listed; this is a stream-distance heuristic, not a
    dataflow proof.
    """
    words: list[str] = []
    seen: set[str] = set()
    for push_offset, word in pushes:
        end = push_offset + 1 + _PUSH32_HEX_LEN // 2
        near = any(0 <= store - end < _SSTORE_WINDOW for store in sstores)
        if near and word not in seen:
            seen.add(word)
            words.append(f"0x{word}")
            if len(words) == _MAX_PUSH32_WORDS:
                break
    return words


def scan_opcodes(code: str) -> dict[str, object]:
    """Count external-call and side-effect opcodes in runtime bytecode.

    Args:
        code: Runtime bytecode hex (with or without the 0x prefix).

    Returns:
        Dict with opcode ``counts``, a ``value_call`` flag (the
        callvalue+gas preamble before a CALL), and ``push32_near_sstore``
        words (up to 8 distinct constants pushed shortly before a store).

    Raises:
        ValueError: If ``code`` is not valid hex.
    """
    data = _decode_hex(code)
    counts, pushes, sstores = _walk_stream(data)
    return {
        "counts": counts,
        "value_call": _VALUE_CALL_PATTERN.search(data.hex()) is not None,
        "push32_near_sstore": _words_near_sstore(pushes, sstores),
    }


def extract_revert_strings(code: str) -> list[str]:
    """Pull printable ASCII runs out of the bytecode (revert-string aid).

    Revert strings live in PUSH data of unverified contracts; CBOR metadata
    strings ride along, so the list is a review aid, not a clean inventory.
    Runs shorter than six characters are dropped, duplicates removed, and
    the list capped at forty entries.
    """
    runs = _PRINTABLE_RUN.findall(_decode_hex(code))
    unique: dict[str, None] = dict.fromkeys(run.decode("ascii") for run in runs)
    return list(unique)[:_MAX_REVERT_STRINGS]


def _risk_flags(counts: dict[str, int], value_call: bool) -> list[str]:
    """Name the dangerous-capability flags implied by the opcode counts."""
    flags: list[str] = []
    if counts["delegatecall"]:
        flags.append("has-delegatecall")
    if counts["selfdestruct"]:
        flags.append("has-selfdestruct")
    if value_call:
        flags.append("has-value-call")
    if counts["create"] or counts["create2"]:
        flags.append("has-create")
    return flags


@dataclass(frozen=True)
class DispatcherShape:
    """Selector-count and thin-dispatch flags for a dispatcher."""

    selector_count: int
    thin_dispatch: bool


@dataclass(frozen=True)
class CallShape:
    """Counts of external-call opcodes plus the value-call preamble flag."""

    call: int
    delegatecall: int
    staticcall: int
    value_call: bool


@dataclass(frozen=True)
class StorageShape:
    """Storage-write sites and base-slot constants pushed near them."""

    sstore_sites: int
    push32_near_sstore: tuple[str, ...] = ()


@dataclass(frozen=True)
class DecompileReport:
    """Reviewable bytecode report shared by markdown and JSON output.

    ``oracle_base_vault``/``oracle_linked`` stay ``None`` when the contract
    exposes no Morpho-style ``BASE_VAULT()`` selector.
    """

    address: str
    rpc: str = ""
    codesize: int = 0
    family: str = ""
    selectors: tuple[SelectorRow, ...] = ()
    dispatcher: DispatcherShape = DispatcherShape(0, True)
    calls: CallShape = CallShape(0, 0, 0, False)
    storage: StorageShape = StorageShape(0)
    revert_strings: tuple[str, ...] = ()
    risk_flags: tuple[str, ...] = ()
    payable_count: str = "unknown"
    oracle_base_vault: str | None = None
    oracle_linked: bool | None = None

    def render_markdown(self) -> str:
        """Render the review report exactly as the CLI text output does."""
        lines: list[str] = [
            f"# Decompile — {self.address}",
            "",
            f"- rpc: {self.rpc}",
            f"- codesize: {self.codesize} bytes",
            f"- template family: {self.family or 'none'}",
            f"- dispatcher: {self.dispatcher.selector_count} selectors "
            f"(thin dispatch: {self.dispatcher.thin_dispatch})",
            f"- calls: {self.calls.call} call / {self.calls.delegatecall} "
            f"delegatecall / {self.calls.staticcall} staticcall "
            f"(value-transfer calls: {self.calls.value_call})",
            f"- storage: {self.storage.sstore_sites} sstore sites",
            "- payable functions: unknown (needs ABI)",
        ]
        if self.storage.push32_near_sstore:
            words = ", ".join(self.storage.push32_near_sstore)
            lines.append(f"- push32 words near sstore: {words}")
        if self.oracle_base_vault is not None:
            lines.append(
                f"- oracle BASE_VAULT: {self.oracle_base_vault} "
                f"(linked: {self.oracle_linked})"
            )
        lines += ["", "## Risk flags", ""]
        lines += [f"- {flag}" for flag in self.risk_flags] or ["- (none)"]
        lines += ["", "## Selectors", ""]
        lines += [
            f"- `{row.selector}` {row.signature}".rstrip() for row in self.selectors
        ] or ["- (none)"]
        lines += ["", "## Revert strings", ""]
        lines += [f"- {item!r}" for item in self.revert_strings] or ["- (none)"]
        return "\n".join(lines)


def bytecode_report(
    address: str,
    code: str,
    names: list[tuple[str, str]],
    family: str,
    rpc: str = "",
) -> DecompileReport:
    """Assemble the bytecode report from the scanners and selector names.

    Selector names come from the shared inventory (drain table, canonical
    names, 4byte lookup); the template family tags known dispatcher shapes.
    """
    scan = scan_opcodes(code)
    counts = cast("dict[str, int]", scan["counts"])
    return DecompileReport(
        address=address,
        rpc=rpc,
        codesize=len(_decode_hex(code)),
        family=family,
        selectors=tuple(
            SelectorRow(selector=selector, signature=signature)
            for selector, signature in names
        ),
        dispatcher=DispatcherShape(
            selector_count=len(names), thin_dispatch=len(names) < _THIN_DISPATCH_MAX
        ),
        calls=CallShape(
            call=counts["call"],
            delegatecall=counts["delegatecall"],
            staticcall=counts["staticcall"],
            value_call=bool(scan["value_call"]),
        ),
        storage=StorageShape(
            sstore_sites=counts["sstore"],
            push32_near_sstore=tuple(cast("list[str]", scan["push32_near_sstore"])),
        ),
        revert_strings=tuple(extract_revert_strings(code)),
        risk_flags=tuple(_risk_flags(counts, bool(scan["value_call"]))),
    )
