"""Error messages used across the ``ruin`` domain.

Python uses specific built-in exceptions. These helpers keep messages
consistent between validation sites.
"""


def invalid_address(raw: str) -> ValueError:
    """Return a ``ValueError`` for a malformed contract address."""
    return ValueError(f"invalid contract address {raw!r}")


def invalid_protocol_name(raw: str) -> ValueError:
    """Return a ``ValueError`` for a malformed protocol name."""
    return ValueError(f"invalid protocol name {raw!r}")


def invalid_rpc_url(raw: str) -> ValueError:
    """Return a ``ValueError`` for a malformed RPC URL."""
    return ValueError(f"invalid rpc url {raw!r}")
