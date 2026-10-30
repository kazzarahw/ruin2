"""Structured-output builders for the protocol namespace.

Merged into ``BUILDERS`` by :mod:`ruin.services.operations_builders`; each
builder serializes the exact payload the text handler builds.
"""

from __future__ import annotations

from typing import Any

from ruin.services.operations_ext_protocol import (
    invariant_specs,
    protocol_of,
    surface_rows,
)
from ruin.services.serialize import to_dict


def _resolve_data(kwargs: dict[str, Any]) -> object:
    """Build the resolve payload: full protocol facts including graph."""
    return to_dict(protocol_of(kwargs))


def _enumerate_data(kwargs: dict[str, Any]) -> object:
    """Build the enumerate payload: ranked surface rows."""
    return to_dict({"rows": surface_rows(kwargs)})


def _model_data(kwargs: dict[str, Any]) -> object:
    """Build the model payload: protocol facts plus the ranked surface."""
    return {
        "protocol": to_dict(protocol_of(kwargs)),
        "surface": to_dict({"rows": surface_rows(kwargs)}),
    }


def _invariants_data(kwargs: dict[str, Any]) -> object:
    """Build the invariants payload: specs plus optional scaffold note."""
    return {"specs": to_dict({"items": invariant_specs(kwargs)})}


PROTOCOL_BUILDERS: dict[str, Any] = {
    "resolve": _resolve_data,
    "enumerate": _enumerate_data,
    "model": _model_data,
    "invariants": _invariants_data,
}
