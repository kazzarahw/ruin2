"""Protocol summaries and details for ``ruin``."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ruin.core.ids import ContractId, ProtocolName


@dataclass
class ProtocolSummary:
    """A protocol summary from a data source."""

    name: ProtocolName
    slug: str
    tvl_usd: int
    chains: list[str] = field(default_factory=list)
    category: str = ""
    address: str = ""
    listed_unix: int = 0
    audits: int = 0

    @classmethod
    def new(
        cls,
        name: str,
        slug: str,
        tvl_usd: int,
        chains: list[str],
        category: str,
    ) -> ProtocolSummary:
        """Construct a summary, validating the name."""
        return cls(ProtocolName.new(name), slug, tvl_usd, chains, category)

    def chain_of_interest(self) -> str:
        """Primary chain label from the feed, or empty when unlisted."""
        return self.chains[0] if self.chains else ""


@dataclass
class RankedTarget:
    """A ranked candidate target."""

    summary: ProtocolSummary
    score: int


@dataclass
class ProtocolDetail:
    """A protocol's detail from a data source."""

    name: str
    category: str = ""
    chains: list[str] = field(default_factory=list)
    primary: ContractId | None = None


def _int_field(item: dict[str, object], key: str) -> int:
    """Read a numeric field, accepting digit-only strings and rejecting bools."""
    raw = item.get(key)
    if isinstance(raw, bool):
        return 0
    if isinstance(raw, (int, float)):
        return int(raw)
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    return 0


def _text_field(item: dict[str, object], key: str) -> str:
    """Read a text field, returning empty for missing or blank values."""
    raw = item.get(key)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return ""


def parse_protocols(json_text: str) -> list[ProtocolSummary]:
    """Parse a DefiLlama protocols JSON array."""
    try:
        raws = json.loads(json_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid recon document: {error}") from error
    if not isinstance(raws, list):
        raise TypeError("invalid recon document: expected array")
    results: list[ProtocolSummary] = []
    for item in raws:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        if not isinstance(name, str) or not name.strip():
            continue
        slug = item.get("slug", "")
        if not isinstance(slug, str):
            slug = ""
        tvl_usd = _int_field(item, "tvl")
        chain = item.get("chain", "")
        chains = [chain] if isinstance(chain, str) and chain.strip() else []
        category = item.get("category", "")
        if not isinstance(category, str):
            category = ""
        summary = ProtocolSummary.new(name, slug, tvl_usd, chains, category)
        summary.address = _text_field(item, "address")
        summary.listed_unix = _int_field(item, "listedAt")
        summary.audits = _int_field(item, "audits")
        results.append(summary)
    return results


def parse_protocol(json_text: str) -> ProtocolDetail:
    """Parse a DefiLlama protocol detail JSON document."""
    try:
        raw = json.loads(json_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid recon document: {error}") from error
    if not isinstance(raw, dict):
        raise TypeError("invalid recon document: expected object")
    name = raw.get("name", "")
    if not isinstance(name, str):
        name = ""
    category = raw.get("category", "")
    if not isinstance(category, str):
        category = ""
    chains_raw = raw.get("chains", [])
    chains = (
        [c for c in chains_raw if isinstance(c, str)]
        if isinstance(chains_raw, list)
        else []
    )
    address = raw.get("address")
    primary = None
    if isinstance(address, str):
        try:
            primary = ContractId.new(address)
        except ValueError:
            primary = None
    return ProtocolDetail(name=name, category=category, chains=chains, primary=primary)
