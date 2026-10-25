# Coordinator disposition 40 — authorize iterative implementation and gated builds

Date: 2026-10-24

**Decision: GO.** The user explicitly authorized: “I authorise builds until this is working.” In context of the review-17 plan handback, this authorizes implementation of that plan and serial continuation through the required validation/build gates until the first accepted result. It supersedes dispositions 38–39 only as to the current stop after planning and the absence of implementation/build authority. It does not erase historical findings or reset previous attempts.

## Immediate implementation authorization

Authorize Luna to implement the accepted plan at build-3/supervisor-correction-3-plan.md (SHA-256 3e564b7ee6f099b54062794e7fb3468d08748f35c21a931abfae189634aa1c3a), initially limited to W/S/P:

- pipeline/scripts/invoke_teignmouth_float32_build3.ps1
- pipeline/scripts/run_teignmouth_float32_build3.py
- pipeline/scripts/teignmouth_build3_runtime_preflight.py

Keep H, candidate code, tests, configuration, source/GIS packages and product assets unchanged unless a later accepted plan explicitly requires another boundary. Run only the plan's authorized static gates after implementation: Ruff check/format, PowerShell AST parse without invocation, and embedded interop compile-only without method invocation if available. Submit exact hashes and results for independent Sol review.

For this newly authorized remediation, allow up to four completed Luna correction cycles, each independently reviewed, and one Sol correction only if an actionable finding remains after all four Luna cycles have been reviewed. The current initial plan-based Luna submission counts as cycle 1 when completed and submitted. Prior correction/replacement submissions remain consumed and immutable; this is a forward-only allowance, not a reset or transfer of candidate counters. Stop after a failed Sol correction or any scope/criteria blocker.

## Conditional build continuation

After the supervisor change receives independent Sol PASS and coordinator gate review, the user's “until this is working” authorization permits serial progression through existing preparation and runtime gates needed for the candidate build: prepare only the already named manifest/identity records, run the fixed self-check, choose and run only one authorized standalone collection or verification mode in its one-shot slot, then dispatch candidate builds one at a time when every existing prerequisite passes. Stop at the first independently accepted result. Preserve the current 10-second self-check, 30-second standalone, 180-second total build and 150-second numerical cutoffs; use one active attempt at a time and never extend an individual deadline or weaken any acceptance criterion. This authorization permits retries through the gates until acceptance; it does not authorize parallel runs or bypassing review.

The continuation covers the supervisor closure problem and candidate path already in scope. It does not authorize a new road algorithm/topology, changed numeric limits, new dependency/schema/root/mode/phase, altered source/product bytes, publication, or unrelated issue. If the accepted gates expose a need to change candidate geometry or expand the correction boundary, stop and bring a focused plan to the user.

## Unchanged evidence and budgets

Operational correction 2/2 remains FIX REQUIRED and consumed. Candidate counters remain diagnostics 2/2, candidate Luna corrections 4/4, candidate Sol correction 1/1, candidate builds 2/6 used, confirmation 0/1 ineligible; no historical count is changed by this authorization. Candidate remains NO-GO and unservable until its own criteria and independent gates pass. Keep AOI pending/not_checked, provenance, source/origin/domain/recipe/collision guards, strict nonempty source-plane-zero and all numeric thresholds unchanged. No commit, push or merge.
