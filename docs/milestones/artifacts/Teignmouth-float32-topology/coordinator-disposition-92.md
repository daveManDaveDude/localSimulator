# Coordinator disposition 92 — accept plan and authorize S-only correction

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User authorization for as many attempts as needed, with each correction and self-check independently gated. No counters or evidence roots are reset.

## Accepted plan and independent PASS

Accept `docs/milestones/artifacts/Teignmouth-float32-topology/build-3/selfcheck-console-inheritance-plan.md`, SHA-256 `d8400f4fa3c1b5c1e294cffbac6586eaea9830e20ea2dc9b10cdea0e3d2d519`, after independent Sol plan review `docs/milestones/artifacts/Teignmouth-float32-topology/build-3/selfcheck-console-inheritance-plan-independent-review.md`, SHA-256 `360b568618b24f554d4fa44e4d455d48641c71b3fccf600b804a3950a8d15155` (PASS for the plan only). Reviewer verified the exact W/S/H/P baseline and found no API, deadline, ownership or acceptance blocker. Current S matches the plan baseline `64bf2c4abf822ad55252789315d71731d2660d66bb5b6bc7d60f810f2de492c7`.

## Implementation authority

Authorize Luna to implement exactly the plan's **S-only** change in `pipeline/scripts/run_teignmouth_float32_build3.py`: a finite fail-closed current-console precondition and keyword-only inheritance opt-in at exactly the normal-helper and tree-root helper launch calls. Keep W/H/P unchanged. Preserve all exact acceptance and failure semantics in the plan, including unchanged defaults for all other callers, `CREATE_SUSPENDED`, Job assignment before resume, redirected stdio, original 10-second deadline, unconditional unexpected-member failure, complete zero/empty/zero before tree probing, error/cleanup ownership, no console creation/attachment/window, and no candidate/GIS access.

Implementation may run only the planned Ruff check and format check on S and perform the stated static diff/branch review. No wrapper/self-check, tests, imports, runtime, process probes, preflight, manifests, evidence-root writes, GIS/numerical/build/serving/publication/browser work or W/H/P edits. Preserve current source/evidence and stop with exact hashes, diff summary, commands/results and any blocker. Then submit actual S bytes for independent Sol implementation review; this disposition does not authorize another self-check. A subsequent fresh-root plan/review and one-use coordinator gate remain mandatory.

## Preserved status

Retry-1 through retry-4 stay consumed, immutable and non-PASS. Outer `pwsh` exit 1 versus internal exit 2 and historical unsaved `957157…` S hash remain separate unresolved facts. Candidate is **NO-GO and unservable**; build 3 unreserved. No commit, push or merge.
