"""Recon types and parsing for ``ruin``."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruin.core.protocols import ProtocolDetail
from dataclasses import dataclass, field

from ruin.core.domain import Target
from ruin.core.enums import Chain, Language, TargetMode
from ruin.core.ids import ContractId, ProtocolName
from ruin.core.value_objects import Amount


@dataclass
class ReconEntry:
    """A single discovered contract from recon."""

    address: ContractId
    label: str = ""
    tvl: Amount | None = None


@dataclass
class ReconSpec:
    """How to scope a recon."""

    name: ProtocolName
    mode: TargetMode
    min_tvl: int | None = None
    chain: Chain = Chain.EVM
    language: Language = Language.SOLIDITY


@dataclass
class ReconResult:
    """The result of recon."""

    name: ProtocolName
    contracts: list[ReconEntry] = field(default_factory=list)
    tvl: Amount | None = None
    mode: TargetMode = TargetMode.RESEARCH
    chain: Chain = Chain.EVM
    language: Language = Language.SOLIDITY

    @staticmethod
    def scope(spec: ReconSpec, entries: list[ReconEntry]) -> ReconResult | None:
        """Scope entries by spec, dedupe, and aggregate TVL."""
        seen: set[str] = set()
        contracts: list[ReconEntry] = []
        total: Amount | None = None
        for entry in entries:
            if spec.min_tvl is not None and (
                entry.tvl is None or entry.tvl.units < spec.min_tvl
            ):
                continue
            if entry.address.as_str() in seen:
                continue
            seen.add(entry.address.as_str())
            if entry.tvl is not None:
                if total is None:
                    total = Amount(asset=entry.tvl.asset, units=entry.tvl.units)
                else:
                    total = Amount(
                        asset=total.asset,
                        units=total.units + entry.tvl.units,
                    )
            contracts.append(entry)
        if not contracts:
            return None
        return ReconResult(
            name=spec.name,
            contracts=contracts,
            tvl=total,
            mode=spec.mode,
            chain=spec.chain,
            language=spec.language,
        )

    def to_target(self) -> Target:
        """Convert a scoped recon result into a target."""
        return Target.new(
            self.name.as_str(),
            [entry.address for entry in self.contracts],
            self.tvl,
            self.mode,
        ).with_ecosystem(self.chain, self.language)

    def is_well_formed(self) -> bool:
        """Return whether the recon result is well-formed."""
        return bool(self.contracts)


def parse_recon(json_text: str) -> list[ReconEntry]:
    """Parse a recon JSON document into validated entries."""
    try:
        doc = json.loads(json_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid recon document: {error}") from error
    if not isinstance(doc, dict):
        raise TypeError("invalid recon document: expected object")
    asset_raw = doc.get("tvl_asset")
    contracts_raw = doc.get("contracts")
    if not isinstance(asset_raw, str) or not isinstance(contracts_raw, list):
        raise TypeError("invalid recon document: bad shape")
    asset = ContractId.new(asset_raw)
    entries: list[ReconEntry] = []
    for item in contracts_raw:
        if not isinstance(item, dict):
            raise TypeError("invalid recon document: bad contract")
        address_raw = item.get("address")
        if not isinstance(address_raw, str):
            raise TypeError("invalid recon document: bad address")
        address = ContractId.new(address_raw)
        label = item.get("label", "")
        if not isinstance(label, str):
            label = ""
        tvl_raw = item.get("tvl")
        tvl = Amount(asset=asset, units=0)
        if tvl_raw is not None:
            if not isinstance(tvl_raw, int):
                raise ValueError("invalid recon document: bad tvl")
            tvl = Amount(asset=asset, units=tvl_raw)
        entries.append(ReconEntry(address=address, label=label, tvl=tvl))
    return entries


def recon_document(detail: ProtocolDetail, tvl_asset: ContractId) -> str:
    """Build a recon document JSON string from a protocol detail."""
    contracts: list[dict[str, object]] = []
    if detail.primary is not None:
        contracts.append(
            {
                "address": detail.primary.as_str(),
                "label": detail.name,
                "tvl": None,
            }
        )
    doc = {"tvl_asset": tvl_asset.as_str(), "contracts": contracts}
    return json.dumps(doc, separators=(",", ":"))


_CHAIN_ALIASES = {
    "eth": Chain.EVM,
    "ethereum": Chain.EVM,
    "optimism": Chain.EVM,
    "arbitrum": Chain.EVM,
    "base": Chain.EVM,
    "polygon": Chain.EVM,
    "bsc": Chain.EVM,
    "avalanche": Chain.EVM,
    "solana": Chain.SOLANA,
    "aptos": Chain.MOVE,
    "sui": Chain.MOVE,
    "starknet": Chain.CAIRO,
    "cosmos": Chain.COSMWASM,
}


def _extract_evm_address(text: str) -> str | None:
    match = re.search(r"0x[0-9a-fA-F]{40}", text)
    return match.group(0) if match is not None else None


def _immunefi_entry(asset: dict[str, object]) -> ReconEntry | None:
    if asset.get("type") != "smart_contract":
        return None
    chain_name = str(asset.get("chain", "")).lower()
    chain = _CHAIN_ALIASES.get(chain_name, Chain.EVM)
    if chain is not Chain.EVM:
        return None
    address = None
    address_raw = asset.get("address")
    if isinstance(address_raw, str):
        address = _extract_evm_address(address_raw)
    url_raw = asset.get("url")
    if address is None and isinstance(url_raw, str):
        address = _extract_evm_address(url_raw)
    if address is None:
        return None
    return ReconEntry(
        address=ContractId.new(address),
        label=str(asset.get("name", "")),
        tvl=None,
    )


def parse_immunefi_scope(json_text: str) -> list[ReconEntry]:
    """Parse an Immunefi scope document into EVM recon entries."""
    try:
        doc = json.loads(json_text)
    except (json.JSONDecodeError, TypeError) as error:
        raise ValueError(f"invalid immunefi scope: {error}") from error
    if not isinstance(doc, dict):
        raise TypeError("invalid immunefi scope: expected object")
    assets = doc.get("assets", [])
    if not isinstance(assets, list):
        return []
    entries: list[ReconEntry] = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        entry = _immunefi_entry(asset)
        if entry is not None:
            entries.append(entry)
    return entries
