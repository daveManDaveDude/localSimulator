# Coordinator disposition 31 — authorize one replacement-supervision implementation

Date: 2026-10-24

**Decision: GO for one operational replacement implementation submission under the user's explicit “I authorise.” This does not renew or erase the failed prior operational correction. Candidate remains NO-GO; build 3 remains unreserved.**

Accepted scope and design: `build-3/supervisor-replacement-plan.md`, SHA-256 `01be9327b245c8f3645e688f2d6590aa93dcd921d70596eec590466b3e0ddf1b`. The plan retains the approved venv entry point and establishes exact launcher/interpreter identities and containment. Keep the previous failed submission/review and dispositions 26–30 immutable.

Authorize Luna to implement exactly these four operational files:

- `pipeline/scripts/run_teignmouth_float32_build3.py`
- `pipeline/scripts/teignmouth_build3_runtime_preflight.py`
- `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py`
- `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`

Address the review-15 blockers using the accepted plan, including the exact launcher → base interpreter process chain, outer/inner Job ownership and membership, mode-isolated handoffs, PowerShell startup/setup durability, native exit capture, correct memory-sample unavailable states, phase-specific manifest/reservation controls and fail-closed cleanup. Do not silently change executable, Python environment, package closure, time budgets or candidate criteria.

Static acceptance checks authorized after implementation:

- Ruff check and format check for the three Python files.
- PowerShell AST parse only; do not invoke the wrapper.
- Compile-only validation of the embedded interop declarations, without executing methods, where the required compiler is available. Report unavailable if not.

Submit exact hashes and those static results to an independent non-implementing Sol reviewer. No code edits after submission under this authorization. If review is FIX REQUIRED, stop and return for user direction.

## Explicit exclusions and unchanged candidate counters

This authorizes no wrapper/supervisor/helper execution; no self-check, runtime preflight, diagnostic, GIS load, candidate build, browser check or publication. The earlier conditional self-check authorization did not pass its review gate and is not restored. Runtime-preflight-only execution and build 3 each need separate future dispositions.

- Candidate diagnostics: 2/2 used.
- Candidate Luna corrections: 4/4; candidate Sol correction: 1/1.
- Candidate implementation builds: 2/6 used; zero reserved.
- Independent confirmation: 0/1 and ineligible.
- Failed dispatch-preparation correction 1/1 remains consumed. This separately authorized replacement submission is operational-only and changes none of the above counters.

Keep all candidate source/origin/domain/recipe/collision guards, exact nonempty source-plane-zero gate and numerical limits unchanged. Do not change AOI, packages, products, historical evidence, attempt resets or counters.
