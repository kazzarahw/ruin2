"""Off-chain / infrastructure review templates for ``ruin``.

Structured checklists for the parts of a protocol that live off-chain: the
keeper/relayer, the oracle backend, and multisig/ops roles. These are review
aids, not analyzers: they tell a researcher what to look at and why. Pure data.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReviewTemplate:
    """A checklist for reviewing one off-chain/infra component."""

    name: str
    focus: str
    checks: list[str] = field(default_factory=list)
    look_fors: list[str] = field(default_factory=list)

    def render_markdown(self) -> str:
        """Render the template as a Markdown review checklist."""
        lines: list[str] = [
            f"# Infra Review — {self.name}",
            "",
            f"Focus: {self.focus}",
            "",
        ]
        lines.append("## Checks")
        lines.append("")
        for check in self.checks:
            lines.append(f"- [ ] {check}")
        lines.append("")
        lines.append("## Look-fors")
        lines.append("")
        for look in self.look_fors:
            lines.append(f"- {look}")
        return "\n".join(lines)


REVIEW_TEMPLATES: dict[str, ReviewTemplate] = {
    t.name: t
    for t in [
        ReviewTemplate(
            name="keeper",
            focus="an EOA or contract that triggers protocol actions off-chain",
            checks=[
                "Confirm the keeper key's custody and rotation (hardware? hot?).",
                "Verify the trigger predicate cannot be forced by an attacker.",
                "Check the keeper pays fees/gas it can actually afford.",
                "Confirm a failed upkeep cannot brick a safety-critical action.",
            ],
            look_fors=[
                "Keeper racing that front-runs a liquidation for profit.",
                "A keeper-only function an attacker can call if the key leaks.",
                "Off-chain config that silently disables a required upkeep.",
            ],
        ),
        ReviewTemplate(
            name="oracle-backend",
            focus="the off-chain service that signs/publishes prices",
            checks=[
                "Identify the signing key and its rotation/compromise path.",
                "Confirm price staleness bounds are enforced on-chain.",
                "Verify the backend cannot sign two conflicting prices per round.",
                "Check the feed's source exchanges and outage behavior.",
            ],
            look_fors=[
                "A stale round accepted because max-age is misconfigured.",
                "A signer that can pump any price in a flash-loan block.",
                "Round-id gaps that let a wrong answer persist.",
            ],
        ),
        ReviewTemplate(
            name="multisig",
            focus="owner/admin multisig and timelock governing the protocol",
            checks=[
                "Confirm threshold, signer set, and rotation procedure.",
                "Verify a timelock delay exists before privileged actions.",
                "Check whether any single key can upgrade or pause unilaterally.",
                "Confirm the emergency-pause role cannot be captured.",
            ],
            look_fors=[
                "A low threshold (1-of-N) that makes compromise cheap.",
                "Upgrade executed inside the timelock window bypassing delay.",
                "Guardian/pauser whose key, if leaked, freezes funds forever.",
            ],
        ),
        ReviewTemplate(
            name="bridge-relayer",
            focus="an off-chain relayer attesting cross-chain messages",
            checks=[
                "Confirm the relayer set and quorum required to attest.",
                "Verify the on-chain verifier rejects a single misbehaving relayer.",
                "Check replay protection across source/destination chains.",
                "Confirm a paused source chain cannot be spoofed on destination.",
            ],
            look_fors=[
                "A message minted twice (no nonce/domain separation).",
                "A quorum small enough that a few keys capture the bridge.",
                "Destination accepting a stale source-chain finality assumption.",
            ],
        ),
    ]
}


def get_template(name: str) -> ReviewTemplate:
    """Return a built-in infra review template by name."""
    key = name.strip().lower()
    template = REVIEW_TEMPLATES.get(key)
    if template is None:
        known = ", ".join(sorted(REVIEW_TEMPLATES))
        raise ValueError(f"unknown infra template {name!r}; known: {known}")
    return template


def list_templates() -> list[str]:
    """Return the available infra review template names."""
    return sorted(REVIEW_TEMPLATES)
