"""Verified-source ingestion for ``ruin``.

Fetches Sourcify first (no API key), then falls back to the Etherscan v2 API
when an API key is available. Non-EVM chains delegate to their adapter.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ruin.core.enums import Chain
from ruin.core.onchain import SourceInfo
from ruin.core.sources import etherscan_source, explorer_url, sourcify_source
from ruin.services.chains import get_adapter
from ruin.services.rpc import SHARED_TRANSPORT

if TYPE_CHECKING:
    from ruin.services.rpc import RpcTransport

_KEY_ENV = "RUIN_ETHERSCAN_API_KEY"
_SOURCIFY = "https://sourcify.dev/server"
_ETHERSCAN = "https://api.etherscan.io/v2/api"


def _sourcify_url(chain_id: int, address: str) -> str:
    """Return the Sourcify v2 contract URL for an address."""
    return f"{_SOURCIFY}/v2/contract/{chain_id}/{address}?fields=sources,metadata"


def _try_sourcify(
    transport: RpcTransport, chain_id: int, address: str
) -> SourceInfo | None:
    """Try the Sourcify v2 contract endpoint, returning a verified source if found."""
    try:
        doc = transport.get_json(_sourcify_url(chain_id, address))
    except RuntimeError:
        return None
    name, text, language, remappings, compiler_version = sourcify_source(doc)
    if text:
        return SourceInfo(
            chain=Chain.EVM,
            address=address,
            name=name,
            language=language,
            source_text=text,
            url=explorer_url(address, chain_id),
            verified=True,
            remappings=remappings,
            compiler_version=compiler_version,
        )
    return None


def _try_etherscan(
    transport: RpcTransport, chain_id: int, address: str, api_key: str
) -> SourceInfo | None:
    """Try the Etherscan v2 API, returning a verified source if found."""
    url = (
        f"{_ETHERSCAN}?chainid={chain_id}&module=contract"
        f"&action=getsourcecode&address={address}&apikey={api_key}"
    )
    try:
        doc = transport.get_json(url)
    except RuntimeError:
        return None
    name, text, language, link = etherscan_source(doc, address, chain_id)
    if not text:
        return None
    return SourceInfo(
        chain=Chain.EVM,
        address=address,
        name=name,
        language=language,
        source_text=text,
        url=link,
        verified=True,
    )


def fetch_source(
    address: str,
    *,
    chain: Chain = Chain.EVM,
    chain_id: int = 1,
    api_key: str | None = None,
    transport: RpcTransport | None = None,
) -> SourceInfo:
    """Fetch verified source for an address.

    Args:
        address: The contract / account address.
        chain: The target chain.
        chain_id: The EIP-155 chain id used for EVM explorers.
        api_key: Optional Etherscan key; defaults to ``RUIN_ETHERSCAN_API_KEY``.
        transport: Optional transport, injectable for tests.

    Returns:
        A ``SourceInfo``; ``verified`` is False when no source is found.
    """
    active = transport or SHARED_TRANSPORT
    if chain is not Chain.EVM:
        delegate = get_adapter(chain, active).fetch_source(address)
        return delegate or SourceInfo(chain=chain, address=address)
    found = _try_sourcify(active, chain_id, address)
    if found is not None:
        return found
    key = api_key or os.environ.get(_KEY_ENV, "")
    if key:
        scanned = _try_etherscan(active, chain_id, address, key)
        if scanned is not None:
            return scanned
    return SourceInfo(chain=Chain.EVM, address=address, verified=False)
