"""Address-clustering service for ``ruin``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.core.clustering import Cluster, cluster_infos, render_clusters
from ruin.services.chains import get_adapter

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ruin.core.enums import Chain


def fetch_cluster_bytecodes(
    addresses: Sequence[str], chain: Chain, rpc: str
) -> list[Cluster]:
    """Fetch deployed code for each address and cluster by shared code.

    Args:
        addresses: Addresses to inspect.
        chain: The chain they live on.
        rpc: The RPC endpoint URL.

    Returns:
        Clusters grouping addresses that share deployed code.
    """
    adapter = get_adapter(chain)
    infos = [adapter.fetch_bytecode(address, rpc) for address in addresses]
    return cluster_infos(infos)


def cluster_addresses(addresses: Sequence[str], chain: Chain, rpc: str) -> str:
    """Cluster addresses by shared deployed code and render a report."""
    return render_clusters(fetch_cluster_bytecodes(addresses, chain, rpc))
