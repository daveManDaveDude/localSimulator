# Coordinator disposition 26 — one bounded build-3 supervision correction

Date: 2026-10-24

**Decision: FIX REQUIRED on build-3 operational review 14. Authorize one Luna operational-preparation correction only. Candidate remains NO-GO; build 3 remains unreserved.**

Review evidence: `build-3/independent-supervisor-review.md`, SHA-256 `79f6169bf35c9d20c6edbea89df77895bb851dcee4e42e76a95c35d578aceaa2`.

Accepted remediation plan: `build-3/supervisor-correction-plan.md`, SHA-256 `379e6f798a711171a28f78d7e724b9fcc5e2b9bfd19fae2407764050d53b2395`.

Authorize one bounded correction to exactly these four operational files:

- `pipeline/scripts/run_teignmouth_float32_build3.py`
- `pipeline/scripts/teignmouth_build3_runtime_preflight.py`
- `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py`
- `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`

Address all nine actionable findings in review 14 using the accepted remediation plan. The wrapper must supply the caller-owned monotonic start/deadline handoff and capture the supervisor's actual native exit. Keep fixed modes, no arbitrary commands/paths/durations, one-use evidence paths and fail-closed containment. Preserve the 180-second total build budget, 150-second numerical cutoff, 10-second self-check, 30-second standalone preflight, kill-on-close containment, and every existing numerical gate and limit.

**This is dispatch-preparation work only.** It does not alter or consume candidate correction, diagnostic or implementation-build counters. No candidate builder, candidate algorithm, geometry, shared helper, test/fixture, package, GIS/source/product file or previous evidence may change. No imports, supervisor/self-check/preflight execution, GIS loading, numerical work, build, browser or product action is authorized in this correction. Only the already authorized static Ruff check and format check may run.

After one implementation submission, a non-implementing Sol session independently reviews exact file hashes against all nine findings. Only if review passes may the previously conditional 10-second nonnumerical self-check run through the fixed caller wrapper. Runtime-preflight-only execution still needs its own later disposition. A failed correction review stops this preparation; no further correction is authorized by this disposition.

## Unchanged counters and status

- Diagnostics: 2/2 used.
- Candidate Luna corrections: 4/4 used; candidate Sol correction: 1/1 used.
- Candidate implementation builds: 2/6 used; build 3 is not reserved.
- Independent confirmation: 0/1, ineligible.
- Dispatch-preparation correction: 1 bounded Luna submission authorized; candidate counters are not reopened or reset.
- Runtime preflight, candidate build, candidate serving, browser verification and publication remain unauthorized.
