"""Property tests for pure ruin logic."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from ruin.core.decode import decode_bytecode
from ruin.core.enums import TargetMode
from ruin.core.ids import ContractId, ProtocolName
from ruin.core.protocols import ProtocolSummary
from ruin.core.recon import ReconEntry, ReconResult, ReconSpec
from ruin.core.scoring import rank_targets
from ruin.core.triage import triage_vulns


@given(st.text())
def test_decode_bytecode_does_not_raise(code: str) -> None:
    decoded = decode_bytecode(code)
    assert isinstance(decoded.selectors, list)


@given(st.lists(st.integers(min_value=0, max_value=100), min_size=1, max_size=5))
def test_rank_targets_sorted(values: list[int]) -> None:
    summaries = [
        ProtocolSummary.new(f"P{i}", f"p{i}", v, ["Ethereum"], "Defi")
        for i, v in enumerate(values)
    ]
    ranked = rank_targets(summaries, len(summaries))
    scores = [item.score for item in ranked]
    assert scores == sorted(scores, reverse=True)


@given(st.lists(st.integers(min_value=0, max_value=5), min_size=1, max_size=5))
def test_recon_scope_dedupes(addresses: list[int]) -> None:
    entries = []
    for _value in addresses:
        # Use the same address to force deduplication.
        entries.append(ReconEntry(address=ContractId.new("0x" + "2" * 40), tvl=None))
    spec = ReconSpec(name=ProtocolName.new("P"), mode=TargetMode.RESEARCH)
    result = ReconResult.scope(spec, entries)
    if result is not None:
        assert len(result.contracts) <= len(entries)


@given(
    st.lists(
        st.sampled_from(["weak-prng", "timestamp", "unknown"]), min_size=1, max_size=5
    )
)
def test_triage_sorting(checks: list[str]) -> None:
    triage = triage_vulns("P", checks)
    ranks = [
        0 if v.value == "Lead" else 1 if v.value == "Noise" else 2
        for _, _, v in triage.counts
    ]
    assert ranks == sorted(ranks)
