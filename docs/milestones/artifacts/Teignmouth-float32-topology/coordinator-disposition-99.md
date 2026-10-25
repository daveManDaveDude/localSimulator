# Coordinator disposition 99 — submit fixed exception fallback for review

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Disposition 98 and the user's continuing authorization. Preserve all counters and consumed roots.

## Handoff and checks

Luna's S-only handoff is `docs/milestones/artifacts/Teignmouth-float32-topology/build-3/selfcheck-note-serialization-fallback-handoff.md`, SHA-256 `aa14cf4baf1aa6b9898a1dabee093eb68575460af089368faf15fbeb0937621a`. Current S SHA-256 is `376187f474f4e91739d732ba064ec1db39be5863cfd5ce746250d0863c35a997`; W/H/P retain their pinned hashes. The `str(exc)` failure branch now returns a fixed literal; type fields remain separate and successful primary strings/notes are unchanged.

Coordinator reran the authorized static gates from `pipeline/`:

- `.venv/Scripts/python.exe -m ruff check scripts/run_teignmouth_float32_build3.py` — exit 0, `All checks passed!`.
- `.venv/Scripts/python.exe -m ruff format --check scripts/run_teignmouth_float32_build3.py` — exit 0, `1 file already formatted`.

## Independent review gate

Submit exact S bytes for independent Sol review of the disposition-97 fallback finding. Confirm no formatting/type lookup remains outside the guard when `str(exc)` fails; both persistence paths still serialize bounded notes and preserve the primary message/type/phase when available; fallback cannot mask the primary or block cleanup; and all previously accepted close/console/Job/deadline/census gates remain unchanged. Return PASS or precise FIX REQUIRED. No runtime or self-check is authorized here.

## Preserved status

Retry-1 through retry-4 remain consumed, immutable and non-PASS. Candidate remains **NO-GO and unservable**; build 3 unreserved. Outer exit1/internal exit2 and historical unsaved `957157…` remain separate unresolved facts. Fresh-root plan/review and separate one-use gate still required after implementation PASS.
