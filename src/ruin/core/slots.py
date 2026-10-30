"""Storage-layout constants for namespaced (ERC-7201) upgradeable contracts."""

from __future__ import annotations

from dataclasses import dataclass

NAMED_BASE_SLOTS: dict[str, int] = {
    # ERC-7201 bases as OpenZeppelin v5 derives them: double-hash the id
    # string minus one, then clear the lowest byte.
    "ERC20": (0x52C63247E1F47DB19D5CE0460030C497F067CA4CEBF71BA98EEADABE20BACE00),
    "AccessControl": (
        0x02DD7BC7DEC4DCEEDDA775E58DD541E08A116C6C53815C0BD028192F7B626800
    ),
    "UUPSUpgradeable": (
        0x6910533D2C5CB89D5385CD7222FA1039AB69891D1140A4D48D331DF0B2B40C00
    ),
    "Initializable": (
        0xF0C57E16840DF040F15088DC2F81FE391C3923BEC73E23A9662EFC9C229C6A00
    ),
    "EIP712": (0xA16A46D94261C7517CC8FF89F61C0CE93598E3C849801011DEE649A6A557D100),
    "Pausable": (0xCD5ED15C6E187E77E9AEE88184C21F4F2182AB5827CB3B7E07FBEDCD63F03300),
    "ReentrancyGuard": (
        0x9B779B17422D0DF92223018B32B4D1FA46E071723D6817E2486D003BECC55F00
    ),
    "AccessControlDefaultAdminRules": (
        0xEEF3DAC4538C82C8ACE4063AB0ACD2D15CDB5883AA1DFF7C2673ABB3D8698400
    ),
}


@dataclass(frozen=True)
class SlotHuntReport:
    """Balances-slot hunt result for one token.

    ``found`` is False when the fork did not boot or no base slot matched;
    the located-slot fields stay ``None`` in that case.
    """

    token: str
    found: bool
    account: str | None = None
    base_slot: str | None = None
    family: str | None = None
    formula: str | None = None
    signals: tuple[str, ...] = ()

    def render_markdown(self) -> str:
        """Render the hunt result exactly as the CLI text output does."""
        lines: list[str] = [f"# Balances slot — {self.token}", ""]
        if not self.found:
            detail = self.signals[0] if self.signals else "unknown"
            lines.append(f"- verdict: not-found ({detail})")
            return "\n".join(lines)
        lines.append(f"- account: {self.account}")
        lines.append(f"- base slot: {self.base_slot}")
        if self.family:
            lines.append(f"- named storage: {self.family} (ERC-7201)")
        lines.append(f"- value slot: {self.formula}")
        return "\n".join(lines)
