"""Call graph, inheritance, storage layout, and entrypoints from solc ASTs.

Pure: consumes solc >= 0.8 standard-json AST dicts (or line-parser
``Facts`` as fallback) and returns hashable tuples, so results can be
memoized with lru_cache. No I/O, no package imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .sol_parse import ParsedFunction

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .sol_parse import Facts


@dataclass(frozen=True, slots=True)
class CallEdge:
    """One directed call edge (internal/external/delegatecall/staticcall)."""

    caller: str
    callee: str
    kind: str


@dataclass(frozen=True, slots=True)
class ContractGraph:
    """Functions, edges, writes, events for one contract."""

    name: str
    kind: str
    functions: tuple[str, ...]
    edges: tuple[CallEdge, ...]
    state_var_writes: tuple[tuple[str, str], ...]  # (function, variable)
    events: tuple[str, ...]
    errors: tuple[str, ...]
    fn_facts: tuple[ParsedFunction, ...] = ()


@dataclass(frozen=True, slots=True)
class CallGraph:
    """Whole-compilation graph facts."""

    contracts: tuple[ContractGraph, ...]
    inheritance: tuple[tuple[str, str], ...]
    cycles: tuple[tuple[str, ...], ...]
    entrypoints: tuple[str, ...]
    events: tuple[str, ...]
    errors: tuple[str, ...]
    storage_layout: tuple[tuple[str, str, str], ...]

    def writes_by_function(self) -> dict[str, tuple[str, ...]]:
        """Map qualified ``Contract.fn`` to written state variables."""
        out: dict[str, tuple[str, ...]] = {}
        for contract in self.contracts:
            for fn, var in contract.state_var_writes:
                key = f"{contract.name}.{fn}"
                out[key] = tuple(sorted(set(out.get(key, ())) | {var}))
        return out


def _child_dicts(node: dict[str, Any]) -> list[dict[str, Any]]:
    """Direct dict children of an AST node."""
    out = []
    for value in node.values():
        if isinstance(value, dict) and "nodeType" in value:
            out.append(value)
        elif isinstance(value, list):
            out.extend(v for v in value if isinstance(v, dict) and "nodeType" in v)
    return out


def _walk(node: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield every AST node under ``node`` depth-first."""
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(_child_dicts(current))


def _function_name(node: dict[str, Any]) -> str:
    """Declared name, or receive/fallback for the special functions."""
    name = node.get("name")
    if isinstance(name, str) and name:
        return name
    return "receive" if node.get("kind") == "receive" else "fallback"


def _call_edges(fn: dict[str, Any], local: set[str], contract: str) -> list[CallEdge]:
    """Edges inside one function definition."""
    edges: list[CallEdge] = []
    for node in _walk(fn):
        if node.get("nodeType") != "FunctionCall":
            continue
        expr = node.get("expression", {})
        kind = node.get("kind", "functionCall")
        callee = expr.get("memberName") or expr.get("name") or ""
        if not callee:
            continue
        if kind == "functionCall" and callee in local:
            edges.append(CallEdge(contract, callee, "internal"))
        elif kind == "functionCall":
            edges.append(CallEdge(contract, callee, "external"))
        elif kind == "delegateCall":
            edges.append(CallEdge(contract, callee, "delegatecall"))
        elif kind == "staticCall":
            edges.append(CallEdge(contract, callee, "staticcall"))
    return edges


def _fn_facts(fn: dict[str, Any]) -> ParsedFunction:
    """Visibility, mutability, and modifier names of one AST function."""
    mods = tuple(
        m.get("modifierName", {}).get("name", "")
        for m in _child_dicts(fn)
        if m.get("nodeType") == "ModifierInvocation"
    )
    return ParsedFunction(
        _function_name(fn),
        fn.get("visibility", ""),
        fn.get("stateMutability", "nonpayable"),
        mods,
        (),
    )


def _contract_graph(cd: dict[str, Any]) -> ContractGraph:
    """Graph facts for one ContractDefinition node."""
    name = cd.get("name", "")
    children = _child_dicts(cd)
    fns = [c for c in children if c.get("nodeType") == "FunctionDefinition"]
    state_vars = {
        c.get("name", "") for c in children if c.get("nodeType") == "VariableDefinition"
    }
    local = {_function_name(f) for f in fns}
    edges: list[CallEdge] = []
    writes: list[tuple[str, str]] = []
    for fn in fns:
        edges.extend(_call_edges(fn, local, name))
        for node in _walk(fn):
            if node.get("nodeType") != "Assignment":
                continue
            target = node.get("leftHandSide", {})
            if not isinstance(target, dict):
                continue
            var = target.get("name") or target.get("memberName") or ""
            if var in state_vars:
                writes.append((_function_name(fn), var))
    events = tuple(
        c.get("name", "") for c in children if c.get("nodeType") == "EventDefinition"
    )
    errors = tuple(
        c.get("name", "") for c in children if c.get("nodeType") == "ErrorDefinition"
    )
    return ContractGraph(
        name=name,
        kind=cd.get("contractKind", "contract"),
        functions=tuple(sorted(_function_name(f) for f in fns)),
        edges=tuple(sorted(set(edges), key=lambda e: (e.callee, e.kind))),
        state_var_writes=tuple(sorted(set(writes))),
        events=events,
        errors=errors,
        fn_facts=tuple(_fn_facts(f) for f in fns),
    )


def _entrypoints(cd: dict[str, Any]) -> tuple[str, ...]:
    """Externally callable function names of one contract node."""
    return tuple(
        sorted(
            _function_name(c)
            for c in _child_dicts(cd)
            if c.get("nodeType") == "FunctionDefinition"
            and (
                c.get("visibility") in ("public", "external")
                or c.get("kind") in ("receive", "fallback")
            )
        )
    )


def _storage_layout(cd: dict[str, Any]) -> tuple[tuple[str, str, str], ...]:
    """(contract, variable, type) triples from an AST contract node."""
    return tuple(
        (
            str(cd.get("name") or ""),
            str(c.get("name") or ""),
            str(c.get("typeDescriptions", {}).get("typeString") or ""),
        )
        for c in _child_dicts(cd)
        if c.get("nodeType") == "VariableDefinition"
    )


def _cycles(edges: tuple[tuple[str, str], ...]) -> tuple[tuple[str, ...], ...]:
    """Inheritance cycles as sorted node tuples (self-edges included)."""
    parents: dict[str, list[str]] = {}
    for child, parent in edges:
        parents.setdefault(child, []).append(parent)
    cycles: set[tuple[str, ...]] = set()
    for start in parents:
        seen = [start]
        frontier = list(parents.get(start, []))
        while frontier:
            node = frontier.pop()
            if node in seen:
                if node == start:
                    cycles.add(tuple(sorted(set(seen))))
                continue
            seen.append(node)
            frontier.extend(parents.get(node, []))
    return tuple(sorted(cycles))


def build(ast_by_source: dict[str, dict[str, Any]]) -> CallGraph:
    """Build a CallGraph from ``{source name: AST}`` standard-json ASTs."""
    contract_defs: list[dict[str, Any]] = []
    for ast in ast_by_source.values():
        for node in _walk(ast):
            if node.get("nodeType") == "ContractDefinition":
                contract_defs.append(node)
    graphs = tuple(_contract_graph(cd) for cd in contract_defs)
    inheritance: list[tuple[str, str]] = []
    entrypoints: list[str] = []
    layout: list[tuple[str, str, str]] = []
    for cd in contract_defs:
        child = cd.get("name", "")
        for spec in _child_dicts(cd):
            if spec.get("nodeType") == "InheritanceSpecifier":
                base = spec.get("baseName", {}).get("name", "")
                if base and base != child:
                    inheritance.append((child, base))
        entrypoints.extend(_entrypoints(cd))
        layout.extend(_storage_layout(cd))
    events = tuple(sorted({e for g in graphs for e in g.events}))
    errors = tuple(sorted({e for g in graphs for e in g.errors}))
    return CallGraph(
        contracts=graphs,
        inheritance=tuple(sorted(set(inheritance))),
        cycles=_cycles(tuple(sorted(set(inheritance)))),
        entrypoints=tuple(sorted(set(entrypoints))),
        events=events,
        errors=errors,
        storage_layout=tuple(layout),
    )


def build_from_facts(facts: tuple[Facts, ...]) -> CallGraph:
    """Build a CallGraph fallback from line-parser facts (no AST)."""
    graphs = []
    entrypoints: list[str] = []
    layout: list[tuple[str, str, str]] = []
    inheritance: list[tuple[str, str]] = []
    for fact in facts:
        for contract in fact.contracts:
            entrypoints.extend(
                fn.name
                for fn in contract.functions
                if fn.visibility in ("public", "external")
            )
            for var in contract.state_vars:
                layout.append((contract.name, var.name, var.type))
            for parent in contract.inherits:
                inheritance.append((contract.name, parent))
        graphs.append(
            ContractGraph(
                name=fact.contracts[0].name if fact.contracts else fact.path,
                kind=fact.contracts[0].kind if fact.contracts else "contract",
                functions=tuple(
                    sorted({f.name for c in fact.contracts for f in c.functions})
                ),
                edges=(),
                state_var_writes=(),
                events=(),
                errors=(),
                fn_facts=tuple(f for c in fact.contracts for f in c.functions),
            )
        )
    return CallGraph(
        contracts=tuple(graphs),
        inheritance=tuple(sorted(set(inheritance))),
        cycles=_cycles(tuple(sorted(set(inheritance)))),
        entrypoints=tuple(sorted(set(entrypoints))),
        events=(),
        errors=(),
        storage_layout=tuple(layout),
    )
