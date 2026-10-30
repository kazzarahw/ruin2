"""Serialization helpers for structured operation output."""

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Any, cast


def _convert(obj: object) -> object:
    """Recursively convert domain objects to JSON-safe primitives."""
    if isinstance(obj, (int, float, bool, Enum)):
        return obj.value if isinstance(obj, Enum) else obj
    if dataclasses.is_dataclass(obj):
        raw = dataclasses.asdict(cast("Any", obj))
        return {k: _convert(v) for k, v in raw.items()}
    if isinstance(obj, dict):
        return {str(k): _convert(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert(item) for item in obj]
    return _leaf(obj)


def _leaf(obj: object) -> object:
    """Convert a non-container leaf value."""
    if obj is None:
        return None
    as_str = getattr(obj, "as_str", None)
    if callable(as_str):
        return cast("Any", as_str)()
    return str(obj)


def to_dict(obj: object, *, drop_none: bool = False) -> object:
    """Convert a domain object to a JSON-safe dictionary.

    ``drop_none`` drops keys whose value is ``None`` from the top-level
    mapping, for payloads whose text side omits absent fields.
    """
    data = _convert(obj)
    if drop_none and isinstance(data, dict):
        typed = cast("dict[str, object]", data)
        return {key: value for key, value in typed.items() if value is not None}
    return data
