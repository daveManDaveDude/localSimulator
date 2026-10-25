# Coordinator disposition 95 — submit stdio-release correction for independent review

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Disposition 94 and the user's continuing authorization. Historical counters and consumed roots remain unchanged.

## Correction handoff and checks

Luna's correction handoff is `docs/milestones/artifacts/Teignmouth-float32-topology/build-3/selfcheck-console-inheritance-correction-handoff.md`, SHA-256 `09436b0c03a9de7d6bce387c23b5a5d0f8a6348bd6aa177e6aba3028741cf5c3`. Current S SHA-256 is `f50cbb07a0d745eb87d4d4c8e357e0168801507aae2de28f915e3d7ae30e4a55`; W/H/P remain at their accepted hashes.

Coordinator reran the authorized static gates from `pipeline/`:

- `.venv/Scripts/python.exe -m ruff check scripts/run_teignmouth_float32_build3.py` — exit 0, `All checks passed!`.
- `.venv/Scripts/python.exe -m ruff format --check scripts/run_teignmouth_float32_build3.py` — exit 0, `1 file already formatted`.

The handoff reports one close attempt per owned stdio handle, explicit confirmed/unconfirmed state, immediate last-error capture for false BOOL results, preservation of an earlier query/CreateProcess exception, and termination/observation of a created but still-suspended child before authorization/resume if release is unconfirmed. These claims require independent source review; no runtime failure was induced or tested.

## Independent review gate

Submit exact S bytes for fresh independent Sol review of the disposition-93 finding and disposition-94 correction. Verify false return and raised-exception paths, immediate native-error capture, all three close attempts exactly once, primary versus secondary diagnostics, persistence visibility of close failures, no successful authorization/resume with unconfirmed release, and bounded suspended-child cleanup/handle ownership. Also recheck the accepted console query, exact two opt-ins, unchanged defaults, strict census gates and hashes/inverse scope. Return PASS or precise FIX REQUIRED. Do not edit, test, invoke W, create a root, inspect processes or perform downstream work.

## Preserved status

Retry-1 through retry-4 remain consumed, immutable and non-PASS. Candidate remains **NO-GO and unservable**; build 3 unreserved. No further self-check is authorized until this implementation receives independent PASS, a new unique-root binding plan/review passes, and a separate one-use coordinator gate is recorded. The outer exit discrepancy and unsaved historical `957157…` digest remain separate.
