"""Line-based Solidity source parsing: source text to structural facts.

Pure: no I/O, no package imports. This is a deliberately incomplete
scanner used as the fallback when a solc AST is unavailable, and as a
cheap way to read pragma/import lines out of source files.

Documented limits (by design -- a full Solidity grammar is out of scope):

* Contract/library/interface/abstract matching is textual: any line
  whose first identifier after the keyword is the declared name.
  Comments and strings are stripped per line, so a contract keyword
  inside a multi-line block comment on one line still matches.
* Modifier detection is "name appears in the signature before the
  opening brace"; custom modifiers must therefore be named there
  (inheritance-provided modifiers are not resolved).
* Visibility/mutability default to external/nonpayable per the
  Solidity 0.x rules when the pragma is ^0.5 or newer, else public.
* Parameter parsing splits on commas and takes the first token as the
  type; mapped or multi-word types keep only their leading word.
* Structs, enums, using/using-for directives, events, errors, and
  inheritance arguments are not modelled.
* Multi-line signatures are truncated at the first newline, and only the
  first declaration on a single line is parsed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_KIND_RE = re.compile(
    r"^(?P<kind>abstract\s+contract|contract|interface|library)\s+"
    r"(?P<name>[A-Za-z_$][\w$]*)",
)
_FUNC_RE = re.compile(
    r"^(?:function|receive|fallback)\s+(?P<name>[A-Za-z_$][\w$]*)?\s*"
    r"(?P<sig>\([^)]*\)[^;{]*)",
)
_VISIBILITY_RE = re.compile(r"\b(external|public|internal|private)\b")
_MUTABILITY_RE = re.compile(r"\b(payable|view|pure)\b")
_VAR_RE = re.compile(
    r"^(?P<qual>public|internal|private|external)?\s*"
    r"(?P<type>[A-Za-z_$][\w$]*(?:\s*\[[^\]]*\])*)\s+"
    r"(?P<name>[A-Za-z_$][\w$]*)\s*(?:=|;|$)",
)
_IMPORT_RE = re.compile(r"""^import\s+(?:[^;"]*from\s*)?["'](?P<path>[^"']+)["']""")
_PRE_05_MINOR = 5
_PRAGMA_RE = re.compile(r"^pragma\s+solidity\s+(?P<range>[^;]+);")


@dataclass(frozen=True, slots=True)
class ParsedFunction:
    """A function signature recovered from source text."""

    name: str
    visibility: str
    mutability: str
    modifiers: tuple[str, ...]
    params: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ParsedStateVar:
    """A state variable declaration recovered from source text."""

    name: str
    type: str
    visibility: str


@dataclass(frozen=True, slots=True)
class ParsedContract:
    """A contract-like declaration and its members."""

    name: str
    kind: str
    inherits: tuple[str, ...]
    functions: tuple[ParsedFunction, ...]
    state_vars: tuple[ParsedStateVar, ...]


@dataclass(frozen=True, slots=True)
class Facts:
    """Everything the line scanner can say about one source unit."""

    path: str
    pragma: str
    imports: tuple[str, ...]
    contracts: tuple[ParsedContract, ...]


def _strip_line(line: str) -> str:
    """Remove line comments and string literals from one source line."""
    no_comment = re.sub(r"//.*$", "", line)
    return re.sub(r"\"[^\"]*\"|'[^\']*'", " ", no_comment)


def _pre_05(pragma: str) -> bool:
    """True when the pragma range tops out below 0.5."""
    match = re.search(r"0\.(?P<minor>\d+)", pragma)
    return bool(match and int(match.group("minor")) < _PRE_05_MINOR)


def _default_visibility(pragma: str) -> str:
    """Default function visibility: public pre-0.5, else external."""
    return "public" if _pre_05(pragma) else "external"


def _default_var_visibility(pragma: str) -> str:
    """Default state-variable visibility: public pre-0.5, else internal."""
    return "public" if _pre_05(pragma) else "internal"


def _params(sig: str) -> tuple[str, ...]:
    """Extract parameter type words from a signature tail."""
    match = re.search(r"\((?P<args>[^)]*)\)", sig)
    if not match:
        return ()
    args = str(match.group("args") or "").strip()
    if not args:
        return ()
    out: list[str] = []
    for part in args.split(","):
        tokens = part.strip().split()
        if tokens:
            out.append(tokens[0])
    return tuple(out)


def _modifiers(sig: str) -> tuple[str, ...]:
    """Names listed between the parameter list and the opening brace."""
    after = sig[sig.index(")") + 1 :] if ")" in sig else sig
    after = re.sub(r"returns\s*\([^)]*\)", " ", after)
    after = re.sub(
        r"\b(external|public|internal|private|view|pure|payable|virtual|override)\b",
        " ",
        after,
    )
    after = re.sub(r"\([^)]*\)", " ", after)
    names: list[str] = []
    for token in re.findall(r"[A-Za-z_$][\w$]*", after):
        if token not in names:
            names.append(token)
    return tuple(names)


def _split_contracts(lines: list[str]) -> list[tuple[str, str, list[str]]]:
    """Group lines into (name, kind, body) blocks per contract keyword."""
    blocks: list[tuple[str, str, list[str]]] = []
    current: tuple[str, str, list[str]] | None = None
    depth = 0
    for raw in lines:
        line = _strip_line(raw)
        match = _KIND_RE.match(line)
        if match and depth == 0:
            kind = match.group("kind").replace("abstract ", "")
            current = (match.group("name"), kind, [])
            blocks.append(current)
        if current is not None:
            current[2].append(line)
        depth = max(depth + line.count("{") - line.count("}"), 0)
    return blocks


def _inherits(header: str, name: str) -> tuple[str, ...]:
    """Parent names from an is-clause of this contract header."""
    match = re.search(r"\bis\s+(?P<parents>[^{]*)", header)
    if not match or not match.group("parents").strip():
        return ()
    parents: list[str] = []
    for part in match.group("parents").split(","):
        token = part.strip().split("(")[0].strip()
        if token and token != name:
            parents.append(token)
    return tuple(parents)


def _function(line: str, pragma: str) -> ParsedFunction | None:
    """Parse one function/receive/fallback declaration line."""
    match = _FUNC_RE.match(line)
    if not match:
        return None
    name = match.group("name") or (
        "receive" if line.startswith("receive") else "fallback"
    )
    sig = match.group("sig")
    vis_match = _VISIBILITY_RE.search(sig)
    mut_match = _MUTABILITY_RE.search(sig)
    return ParsedFunction(
        name=name,
        visibility=vis_match.group(1) if vis_match else _default_visibility(pragma),
        mutability=mut_match.group(1) if mut_match else "nonpayable",
        modifiers=_modifiers(sig),
        params=_params(sig),
    )


def _state_var(line: str, pragma: str) -> ParsedStateVar | None:
    """State variable declared at contract-body depth (name/type/visibility)."""
    line = re.sub(r"\bconstant\b.*$", "", line)
    line = re.sub(r"\bimmutable\b", " ", line)
    vis = _VISIBILITY_RE.search(line)
    visibility = vis.group(1) if vis else _default_var_visibility(pragma)
    if line.startswith("mapping"):
        match = re.search(
            r"\)\s*(?:public|internal|private|external)?\s*(?P<name>[A-Za-z_$][\w$]*)\s*(?:=|;|$)",
            line,
        )
        if not match:
            return None
        return ParsedStateVar(
            name=match.group("name"), type="mapping", visibility=visibility
        )
    body = _VISIBILITY_RE.sub(" ", line)
    match = _VAR_RE.match(body)
    if not match or match.group("type") in ("function", "event", "error"):
        return None
    return ParsedStateVar(
        name=match.group("name"),
        type=match.group("type"),
        visibility=visibility,
    )


def _contract(name: str, kind: str, body: list[str], pragma: str) -> ParsedContract:
    """Build one contract fact from its body lines."""
    functions = []
    state_vars = []
    depth = body[0].count("{") - body[0].count("}")
    for line in body[1:]:
        fn = _function(line, pragma) if depth == 1 else None
        if fn:
            functions.append(fn)
        elif depth == 1:
            var = _state_var(line, pragma)
            if var:
                state_vars.append(var)
        depth = max(depth + line.count("{") - line.count("}"), 0)
    return ParsedContract(
        name=name,
        kind=kind,
        inherits=_inherits(body[0], name),
        functions=tuple(functions),
        state_vars=tuple(state_vars),
    )


def parse_source(path: str, source: str) -> Facts:
    """Parse one Solidity source unit into structural facts."""
    lines = [ln.strip() for ln in source.splitlines()]
    stripped = [_strip_line(ln) for ln in lines]
    pragma_match = next((m for ln in stripped if (m := _PRAGMA_RE.match(ln))), None)
    pragma = pragma_match.group("range").strip() if pragma_match else ""
    imports = tuple(m.group("path") for ln in lines if (m := _IMPORT_RE.match(ln)))
    contracts = tuple(
        _contract(name, kind, body, pragma)
        for name, kind, body in _split_contracts(lines)
    )
    return Facts(path=path, pragma=pragma, imports=imports, contracts=contracts)
