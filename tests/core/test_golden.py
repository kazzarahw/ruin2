"""Golden rendering tests."""

from ruin.core.domain import Vuln
from ruin.core.enums import Severity, VulnClass
from ruin.core.research import research_card


def test_research_card_golden() -> None:
    vuln = Vuln(klass=VulnClass.LOGIC, severity=Severity.HIGH, summary="s")
    expected = """# Research Card — s

- **Mechanism:** `m`
- **Class:** `Logic`
- **Severity:** `High`

## Sources to consult

- (not researched yet)

## Rule out (false-positive patterns)

- [ ] a `call` to a known/user address with the return checked
- [ ] an assembly XOR (`^`) or shift flagged as `incorrect-exp` / `incorrect-shift`
- [ ] standard ERC20 (`transfer` / `transferFrom`) that always returns `true`
- [ ] a `block.timestamp` feeding a TWAP accumulator: the `uint32` wrap is a documented feature and the `MAX_TIME` guard lives in the external consumer (as in Uniswap V2)
- [ ] a `divide-before-multiply` in a display/string utility (base64, `toLocaleString`), not financial math
- [ ] an `uninitialized-local` that is set inside an assembly block
- [ ] a `weak-prng` that is a wall-clock time for an expiry, not a random selection

## Confirm (real-bug patterns)

- [ ] an unguarded reentrancy: an external call to an unknown contract before/after a state update, with no reentrancy guard
- [ ] a TWAP/oracle consumer with a missing `MAX_TIME` / `skipIfTimestampExceeded` cap
- [ ] a precision loss in financial math (LTV, leverage, fee, interest): divide-before-multiply
- [ ] an unsafe/unchecked transfer on a path that assumes it succeeded
- [ ] a missing access control on a state-changing function
- [ ] an RNG (`blockhash`, `difficulty`, `timestamp`) used for a decision an attacker or sequencer can manipulate

> Verdict: record which pattern matched and why. Do not dismiss a finding without checking the sources and both category lists."""
    assert research_card(vuln, "m").render_markdown() == expected
