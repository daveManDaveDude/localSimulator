# Coordinator disposition 34 — authorize one focused supervisor remediation

Date: 2026-10-24

**Decision: GO for one additional bounded operational-supervisor correction submission, explicitly authorized by the user's latest “I authorise.” Candidate budgets remain unchanged.**

Review basis: `build-3/independent-supervisor-review-3.md`, SHA-256 `c2d0f8d270f5429e90d26dad596fffed23b0023402d1b2da51017c6a4f39b452`. Accepted design baseline remains `build-3/supervisor-replacement-plan.md`, SHA-256 `01be9327b245c8f3645e688f2d6590aa93dcd921d70596eec590466b3e0ddf1b`.

Authorize a focused Sol remediation plan followed by one Luna implementation submission, with exact implementation scope limited to these four existing operational files:

- `pipeline/scripts/run_teignmouth_float32_build3.py`
- `pipeline/scripts/teignmouth_build3_runtime_preflight.py`
- `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py`
- `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`

The plan and implementation must resolve review 16's findings: the read-only PowerShell `$HOME` collision; one coherent parent/leaf/handoff/start-record ownership sequence for each mode; no overwrite without exclusive caller-record ownership; termination and bounded wait for any launcher created suspended but not yet assigned to a Job; single-owner handle cleanup; deadline-aware census/process-identity loops and recomputed waits; fallback error recording if native setup fails; and truthful, complete collection/verification phase behavior without claiming a runtime match before frozen bindings exist. Preserve the approved CPython venv-launcher chain, exact launcher/base identities, outer/inner Job containment, one-use modes, and fixed product/candidate gates.

The Sol plan must stay within the four-file implementation scope and current operational protocol. If it needs additional files, a changed interpreter/runtime, a new dependency, a different time budget, or a new execution/metadata phase beyond this scope, stop and return the boundary question to the user rather than expanding it. After Luna's sole submission, run only the authorized static checks: Ruff check/format for Python files, PowerShell AST parse without invocation, and interop compile-only without method invocation if available. Send exact hashes and results for independent Sol review. If that review returns FIX REQUIRED, stop again; no additional automatic correction is authorized.

## Explicit exclusions and unchanged budgets

No Python/wrapper execution, self-check, runtime preflight, diagnostic, GIS load, numerical work, candidate build, browser check or publication is authorized. Runtime collection/verification, the 10-second self-check and build 3 retain separate future dispositions. The previous operational correction 1/1 and replacement submission 1/1 remain failed and consumed; this is one newly authorized operational correction 2/2, not a reset.

- Candidate diagnostics: 2/2 used.
- Candidate Luna corrections: 4/4; candidate Sol correction: 1/1.
- Candidate implementation builds: 2/6 used; zero reserved.
- Independent confirmation: 0/1 and ineligible.

Keep AOI, provenance, packages, product bytes, source/origin/domain/recipe/collision constraints, exact nonempty source-plane-zero gate and every numerical threshold unchanged. Candidate remains NO-GO and unservable.
