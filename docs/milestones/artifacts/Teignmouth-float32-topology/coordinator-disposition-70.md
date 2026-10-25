# Coordinator disposition 70 — bounded correction for review-14 error masking

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Disposition 64 and the user's authorization for as many attempts as needed to pass the supervisor self-check.

## Review finding accepted

Sol review 14 (`docs/milestones/artifacts/Teignmouth-float32-topology/build-3/independent-supervisor-review-14.md`, SHA-256 `d664f8dbb27136675c0fd7e517540f25b2a31ebfe8700bdf9fc4024c87b7194a`) is FIX_REQUIRED. Current S's guarded `checkpoint_normal_failure(exc)` records the primary normal-stage error, but the enclosing exception handler later calls `_update_owned(record_path, record)` unguarded at line 3102. If this write fails, it replaces the original normal-stage exception. Finally cleanup remains reachable.

This is explicitly within the accepted plan's existing requirement to keep primary, evidence-write and final-cleanup errors separate. Reuse that plan; no new architecture or acceptance change is needed.

## Reserved correction

Reserve one additional Luna S-only correction to guard the outer error-record update so a secondary persistence failure is recorded separately when possible and never replaces the original `exc` raised from the handler. Preserve sticky BLOCKED/non-PASS, the initial guarded checkpoint, final Job/handle cleanup and primary exception text/type. Do not weaken/omit the reaping checks, change W/H/P, add a schema/path/filename, alter the 10-second deadline, or touch candidate/GIS/source/geometry/recipe/numerical/product limits.

Luna may run only Ruff check/format for S and static checks required by the accepted plan. No tests, imports, probes, process inspection, wrapper/self-check/preflight/runtime, or evidence/root changes in this correction/review. Independent Sol review 15 is required. A failed review or static gate returns to another plan-conforming correction cycle under disposition 64; no operation runs before review PASS plus a separately reviewed fresh retry-3 path binding.

The current S at correction entry hashes to `45a7f343644f0fbdeeb66b982c572bf123dffba2f021e0db314060ae1d83b024`. Luna previously reported another hash (`957157…`) for which no saved copy exists; review 14 explicitly recorded this limitation. Review the actual current bytes and disclose the same provenance limitation. Preserve W/H/P and all original/retry evidence byte-for-byte.

Candidate remains **NO-GO and unservable**, build 3 unreserved. No runtime collection, manifest/GIS/numerical/build, serving/publication or browser action. No commit, push or merge.
