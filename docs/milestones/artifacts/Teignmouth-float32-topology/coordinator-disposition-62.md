# Coordinator disposition 62 — bounded continuation after review 10

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** The user's new direction, “Continue,” after disposition 61's request for new user direction. Coordinator's communicated scope: one narrowly bounded caller-owner correction, independent Sol review, and one wrapper self-check only if the review passes.

## Scope and accepted plan

Address only review 10's finding in W: `Assert-OwnedCallerDestination` must validate the proposed caller payload's `wrapperPid`, `startQpc` and `mode` against the current wrapper PID, QPC start and selected mode, in addition to its existing persisted-destination checks. Preserve legitimate evolving caller telemetry and all fixed-path, schema, handoff, persistence, cleanup and error behavior. W is the only implementation file allowed to change.

Reuse the accepted Sol plan `docs/milestones/artifacts/Teignmouth-float32-topology/build-3/post-review9-handoff-ownership-plan.md` (SHA-256 `1da1e35a4c95c946b423746decc6ef64ccedb469a1c78c67b1a0410745e5296e`), which explicitly requires the supplied Caller record to belong to the current wrapper/start/mode. Review 10 is the actionable issue-specific finding. No new diagnosis, widening, schema/path change or weakening of a criterion is authorized.

## Bounded gates

- One new Luna correction: maximum 1, used 0, reserved 1. This is a new post-review-10 allowance; it does not reset or transfer any predecessor budget.
- Run the affected static gate: PowerShell AST parse without invoking W. Reuse the exact-revision unchanged S/P/H Ruff results and embedded C# compile-only result from the immediately preceding reviewed correction only if hashes remain unchanged. No runtime, wrapper, test or self-check during implementation/review.
- Submit to independent Sol review 11. A FIX_REQUIRED result ends this bounded allowance.
- Only after independent PASS, run exactly one wrapper-driven self-check at the already specified `.codex/build3-supervisor-selfcheck-retry-1/` root with the existing 10-second maximum. Preserve its actual result; no collection, identity verification, manifests, GIS/numerical work, candidate build, serving or browser action follows without later user direction.

## Preservation and current status

Keep W's handoff validator, S/H/P, candidate/source/test/config/GIS/product assets, original failed evidence, existing schemas, modes, commands, environment, budgets and source/numerical limits intact. Original failed caller files must remain byte-identical; the fresh retry root must remain absent until the conditional one-shot self-check. Candidate stays **NO-GO and unservable**; build 3 stays unreserved. No commit, push or merge.
