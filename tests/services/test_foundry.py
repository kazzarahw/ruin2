"""Tests for foundry service."""

from contextlib import suppress

from ruin.core.domain import Poc, Target
from ruin.core.enums import CredentialsRef, TargetMode
from ruin.core.ids import RpcUrl
from ruin.core.runs import RunConfig
from ruin.services.foundry import FoundryRunner


def test_foundry_no_contracts() -> None:
    target = Target.new("P", [], None, TargetMode.RESEARCH)
    config = RunConfig(
        target=target,
        poc=Poc(method="m", forge_test="t"),
        rpc_url=RpcUrl.new("http://x"),
        credentials=CredentialsRef.NONE,
    )
    with suppress(ValueError):
        FoundryRunner().run(config)
