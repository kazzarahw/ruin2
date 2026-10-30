# Plan: Remaining work to complete ruin2

> **2026-10-23:** This plan predates the October refactor. Command names,
> flags, and layout now follow `docs/refactor_plan.md` (namespaced CLI, `api`
> layer, `protocol` subsystem). Kept as a historical record of open work.

This plan covers the work still needed to move `ruin2` from "green gate" to a
validated, deployable Prime Agent skill with live end-to-end proof.

## Phase 1 — Live end-to-end validation

Goal: prove the Python port performs a real fork measurement, not only mocked
subprocesses.

Tasks:
1. Create a minimal Solidity fixture under `tests/fixtures/`:
   - `Vault.sol` with a withdraw reentrancy or simple drainable balance.
   - `Drain.t.sol` or `Drain.s.sol` that performs the drain via `vm.broadcast`.
2. Add an integration test in `tests/integration/test_end_to_end.py`:
   - skip unless `RUIN_INTEGRATION=1` and `anvil`, `cast`, `forge` are installed.
   - start `anvil` on port 8545.
   - run `ruin run <recon> --name Vault --forge-test <test> --method drain --rpc http://127.0.0.1:8545`.
   - assert the report contains `Proof of Drain` and a non-zero amount.
3. Add a GitHub Actions job that installs Foundry and runs only
   `tests/integration/test_end_to_end.py`.
4. Document the fixture and expected drain in `docs/testing.md`.

Acceptance:
- `RUIN_INTEGRATION=1 uv run pytest tests/integration/test_end_to_end.py -q` passes
  on a machine with Foundry installed.
- CI job is green.

## Phase 2 — Slither live validation

Goal: prove Slither parsing and triage against real analyzer output.

Tasks:
1. Add `tests/integration/test_slither_live.py`:
   - skip unless `RUIN_INTEGRATION=1` and `slither` is installed.
   - run `slither` on the vulnerable vault fixture.
   - assert `weak-prng` or `reentrancy` appears in triage output.
2. Add the Slither step to the integration workflow.

Acceptance:
- Integration test passes locally and in CI.

## Phase 3 — Prime Agent deployment validation

Goal: validate the skill in the actual Prime Agent kernel.

Tasks:
1. Package the repo as a Prime skill directory:
   - `.prime/agent/skills/ruin/` with `SKILL.md`, `pyproject.toml`, and `src/ruin`.
2. Install Prime Agent locally and start a fresh session.
3. Verify:
   - `import ruin`
   - `help(ruin.run)`
   - `await ruin.run("research", mechanism="m", summary="s")`
   - `!ruin research m s`
4. Document the installation and verification steps in `README.md`.
5. Add a smoke script under `scripts/prime_smoke.py` that prints the results of
   the above checks (developer use only).

Acceptance:
- All four checks succeed in a Prime kernel.
- `SKILL.md` routes correctly based on its description.

## Phase 4 — Mutation testing and test strengthening

Goal: reduce mutation survivors and pin behavior.

Tasks:
1. Run `uv run mutmut run` locally.
2. Review survivors with `uv run mutmut results`.
3. For each survivor:
   - strengthen the relevant test (exact `match=` messages, boundary values), or
   - delete genuinely redundant code.
4. Re-run `uv run mutmut run` until survivors are explained.
5. Add a weekly CI artifact upload for `mutants/mutmut-cicd-stats.json`.

Acceptance:
- `mutmut results` shows no unexplained survivors.
- `make check` remains green.

## Phase 5 — Rendering parity and golden tests

Goal: lock every renderer to the Rust reference output.

Tasks:
1. Add golden tests for:
   - `Report.render_markdown`
   - `TargetScreen.render_markdown`
   - `PipelineStatus.render_markdown`
   - `ReportBundle.render_markdown`
   - `TrustModel.render_markdown`
   - `RngHackAssessment.render_markdown`
   - `FuzzResult.render_markdown`
   - `VulnTriage.render_markdown`
2. Compare each golden file byte-for-byte with the Rust output.
3. Fix any whitespace or ordering differences.
4. Store goldens under `tests/golden/`.

Acceptance:
- All golden tests pass.
- No renderer changes without a golden update.

## Phase 6 — Documentation and packaging polish

Goal: make the repository self-describing and Prime-ready.

Tasks:
1. Replace the remaining template text in `README.md` and `AGENTS.md`.
2. Add a `CHANGELOG.md` with the initial Python port.
3. Set `[project].authors` and repository URL in `pyproject.toml`.
4. Add a `LICENSE` check to CI (already present via hygiene).
5. Add a `docs/deployment.md` with Prime skill installation steps.

Acceptance:
- No `TODO(template)` markers remain.
- `grep -R "TODO(template)" .` returns nothing (excluding `.git`).

## Phase 7 — Performance and robustness

Goal: make external calls safe and predictable.

Tasks:
1. Add retry/backoff to HTTP calls in `services/http.py`.
2. Add a configurable timeout to subprocess calls.
3. Improve error messages for missing `anvil`, `cast`, `forge`, and `slither`.
4. Add a `--json` output option to the CLI for machine consumption.

Acceptance:
- External calls fail fast with actionable messages.
- CLI supports both Markdown and JSON output.

## Phase 8 — Final validation

Goal: declare the project complete.

Tasks:
1. Run `make check` locally.
2. Run integration tests with `RUIN_INTEGRATION=1`.
3. Run mutation tests.
4. Verify Prime Agent installation.
5. Tag a release (`v0.1.0`).

Acceptance:
- All gates green.
- Release tagged on `main`.

## Risks

- Foundry/Slither availability in CI.
- Prime Agent kernel environment differences.
- Golden tests may expose previously hidden rendering drift.
- Mutation testing may require test strengthening.

## Non-goals

- No new DeFi analysis capabilities beyond the Rust reference.
- No GUI or web interface.
- No replacement of Foundry/Slither with pure Python.