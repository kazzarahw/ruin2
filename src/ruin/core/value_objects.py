"""Small value objects used by the ``ruin`` domain."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruin.core.ids import ContractId


@dataclass(frozen=True)
class Amount:
    """A denominated amount of an asset."""

    asset: ContractId
    units: int


@dataclass(frozen=True)
class ExploitCall:
    """One step in a proof-of-concept."""

    target: ContractId
    signature: str
    args: list[object] = field(default_factory=list)
    value: int = 0
