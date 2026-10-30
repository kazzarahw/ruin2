"""Pure parsers for verified-source documents (Sourcify / Etherscan).

These turn raw JSON documents into ``(name, source_text, language)`` tuples
without any network access, so ingestion logic stays testable in isolation.
"""

from __future__ import annotations

import json
import re

_BUNDLE_HEADER = re.compile(r"^// ==== (.+) ====$", re.MULTILINE)

_LANGUAGE_BY_SUFFIX = {
    ".sol": "Solidity",
    ".vy": "Vyper",
    ".rs": "Rust",
    ".move": "Move",
    ".cairo": "Cairo",
}
_EXPLORER_HOSTS = {
    1: "etherscan.io",
    10: "optimistic.etherscan.io",
    56: "bscscan.com",
    137: "polygonscan.com",
    42161: "arbiscan.io",
    8453: "basescan.org",
    43114: "snowtrace.io",
}


def split_bundle(text: str) -> list[tuple[str, str]]:
    """Split a concatenated source bundle back into ``(path, content)`` pairs.

    Paths pointing outside the bundle (absolute or containing ``..``) are
    dropped so the text can be written to disk safely.
    """
    matches = list(_BUNDLE_HEADER.finditer(text))
    pairs: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end() + 1
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        path = match.group(1).strip()
        body = text[start:end].strip()
        if not path or not body or path.startswith("/") or ".." in path:
            continue
        pairs.append((path, body))
    return pairs


def explorer_url(address: str, chain_id: int) -> str:
    """Build an explorer URL for an address on a known chain."""
    host = _EXPLORER_HOSTS.get(chain_id)
    if host is None:
        return ""
    return f"https://{host}/address/{address}"


def language_for(name: str) -> str:
    """Infer a contract language from a file name."""
    lowered = name.lower()
    for suffix, language in _LANGUAGE_BY_SUFFIX.items():
        if lowered.endswith(suffix):
            return language
    return "unknown"


def _files_from(doc: object) -> list[tuple[str, str]]:
    """Collect ``(name, content)`` pairs from a Sourcify v2 document."""
    if not isinstance(doc, dict):
        return []
    sources = doc.get("sources")
    collected: list[tuple[str, str]] = []
    if isinstance(sources, dict):
        for name, entry in sources.items():
            if isinstance(entry, dict):
                content = str(entry.get("content", ""))
                if name and content:
                    collected.append((str(name), content))
    return collected


def _sourcify_compiler(doc: object) -> str:
    """Compiler version from a Sourcify metadata block (solc that built it)."""
    if not isinstance(doc, dict):
        return ""
    metadata = doc.get("metadata")
    compiler = metadata.get("compiler") if isinstance(metadata, dict) else None
    version = compiler.get("version") if isinstance(compiler, dict) else None
    if not isinstance(version, str) or not version:
        return ""
    return version.split("+", 1)[0]


def _sourcify_remappings(doc: object) -> tuple[str, ...]:
    """Remapping entries (``ctx=path``) from a Sourcify metadata settings block.

    Sourcify stores the solc CLI form ``:ctx=path``; the leading colon is
    stripped so downstream aliasing sees plain ``ctx=path`` entries.
    """
    if not isinstance(doc, dict):
        return ()
    metadata = doc.get("metadata")
    settings = metadata.get("settings") if isinstance(metadata, dict) else None
    entries = settings.get("remappings") if isinstance(settings, dict) else None
    if not isinstance(entries, list):
        return ()
    out: list[str] = []
    for entry in entries:
        if not isinstance(entry, str):
            continue
        normalized = entry.lstrip(":")
        ctx, sep, path = normalized.partition("=")
        if sep and ctx and path:
            out.append(normalized)
    return tuple(out)


def sourcify_source(doc: object) -> tuple[str, str, str, tuple[str, ...], str]:
    """Concatenate every contract file in a Sourcify document.

    The largest file (the primary contract) comes first; each file is
    preceded by a ``// ==== <path> ====`` header so downstream readers can
    tell files apart.

    Args:
        doc: A decoded Sourcify JSON document.

    Returns:
        A ``(name, source_text, language, remappings, compiler_version)``
        tuple; empty fields and empty collection when absent.
    """
    files = _files_from(doc)
    contracts = [
        (name, content) for name, content in files if language_for(name) != "unknown"
    ]
    if not contracts:
        return ("", "", "", (), "")
    contracts.sort(key=lambda pair: -len(pair[1]))
    name = contracts[0][0]
    parts = [f"// ==== {path} ====\n{content}" for path, content in contracts]
    return (
        name,
        "\n\n".join(parts),
        language_for(name),
        _sourcify_remappings(doc),
        _sourcify_compiler(doc),
    )


def _unwrap_etherscan(source: object) -> str:
    """Normalize an Etherscan ``SourceCode`` field into plain source text."""
    if not isinstance(source, str) or not source:
        return ""
    raw = source
    if raw.startswith("{{") and raw.endswith("}}"):
        raw = raw[1:-1]
    try:
        doc = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw
    if isinstance(doc, dict):
        sources = doc.get("sources")
        if isinstance(sources, dict):
            texts = [
                str(entry.get("content", ""))
                for entry in sources.values()
                if isinstance(entry, dict)
            ]
            texts = [text for text in texts if text]
            if texts:
                texts.sort(key=len, reverse=True)
                return "\n\n".join(texts)
    return raw


def etherscan_source(
    doc: object, address: str, chain_id: int
) -> tuple[str, str, str, str]:
    """Pick the primary contract source from an Etherscan document.

    Args:
        doc: A decoded Etherscan ``getsourcecode`` JSON document.
        address: The contract address, used to build the explorer URL.
        chain_id: The EIP-155 chain id, used to build the explorer URL.

    Returns:
        A ``(name, source_text, language, url)`` tuple; empty fields when absent.
    """
    if not isinstance(doc, dict):
        return ("", "", "", "")
    result = doc.get("result")
    first: object = result[0] if isinstance(result, list) and result else None
    if not isinstance(first, dict):
        return ("", "", "", "")
    name = str(first.get("ContractName", ""))
    text = _unwrap_etherscan(first.get("SourceCode"))
    compiler = str(first.get("Compiler", ""))
    language = "Vyper" if "vyper" in compiler.lower() else "Solidity"
    if not text:
        language = "unknown"
    return (name, text, language, explorer_url(address, chain_id))
