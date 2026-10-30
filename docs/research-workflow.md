# Research workflow for the web3 transition

Every phase in `docs/web3-transition-plan.md` must be preceded by a research
note in `docs/research/`. A phase is not ready for implementation until its
research note answers the questions below and is reviewed.

## Required research questions

1. What web3 ecosystems or workflows does this phase enable?
2. What are the smallest useful abstractions that preserve the pure core?
3. Which existing modules, tests, and fixtures must change?
4. What external tools or standards are involved?
5. What are the failure modes and compatibility risks?
6. What is the minimal acceptance test that proves the capability?

## Research note template

Create `docs/research/phase-N-<slug>.md` with:

- Scope and non-goals
- Ecosystem coverage
- Relevant codebase touchpoints
- External standards and tools
- Compatibility risks
- Proposed minimal implementation
- Acceptance tests
- Open questions

## Rule

No implementation work for a phase begins until the corresponding research note
exists and its open questions are resolved or explicitly deferred.