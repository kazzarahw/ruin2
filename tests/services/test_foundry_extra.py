"""Extra foundry tests."""

from typing import Any, cast

import pytest

from ruin.core.domain import Poc, Target
from ruin.core.enums import CredentialsRef, TargetMode
from ruin.core.ids import ContractId, RpcUrl
from ruin.core.runs import RunConfig
from ruin.services import fork as forkmod
from ruin.services import foundry as foundry_service


class FakeProcess:
    def __init__(
        self, stdout: str = "0x0", returncode: int = 0, stderr: str = ""
    ) -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


class FakePopen:
    def __init__(self) -> None:
        self.args = []
        self.returncode = 0

    def kill(self) -> None:
        return None

    def wait(self) -> None:
        return None

    def __enter__(self) -> "FakePopen":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def communicate(self, *_args: object, **_kwargs: object) -> tuple[str, str]:
        return ("0x0", "")

    def poll(self) -> int:
        return 0


def test_foundry_run() -> None:
    def fake_run(_argv: list[str]) -> FakeProcess:
        return FakeProcess()

    def fake_popen(*_args: object, **_kwargs: object) -> FakePopen:
        return FakePopen()

    cast("Any", foundry_service).run_command = fake_run
    cast("Any", forkmod).run_command = fake_run
    cast("Any", forkmod.subprocess).Popen = fake_popen
    asset = ContractId.new("0x" + "1" * 40)
    target = Target.new("P", [asset], None, TargetMode.RESEARCH)
    config = RunConfig(
        target=target,
        poc=Poc(method="m", forge_test="t"),
        rpc_url=RpcUrl.new("http://example.com"),
        credentials=CredentialsRef.NONE,
    )
    result = foundry_service.FoundryRunner().run(config)
    assert result.succeeded is True


def test_foundry_failure_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run(_argv: list[str], **kwargs: Any) -> FakeProcess:
        captured["env"] = kwargs.get("env") or {}
        return FakeProcess(stdout="", stderr="Script failed: revert", returncode=1)

    def fake_popen(*_args: Any, **_kwargs: Any) -> FakePopen:
        return FakePopen()

    monkeypatch.setattr(foundry_service.subprocess, "run", fake_run)
    monkeypatch.setattr(forkmod.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(foundry_service, "run_command", lambda *_a, **_k: FakeProcess())
    monkeypatch.setattr(forkmod, "run_command", lambda *_a, **_k: FakeProcess())
    asset = ContractId.new("0x" + "1" * 40)
    target = Target.new("P", [asset], None, TargetMode.RESEARCH)
    config = RunConfig(
        target=target,
        poc=Poc(method="m", forge_test="t"),
        rpc_url=RpcUrl.new("http://example.com"),
        credentials=CredentialsRef.NONE,
    )
    result = foundry_service.FoundryRunner().run(config)
    assert result.succeeded is False
    assert "forge script failed" in result.summary
    assert "revert" in result.summary
    assert "FOUNDRY_BROADCAST" in captured["env"]
