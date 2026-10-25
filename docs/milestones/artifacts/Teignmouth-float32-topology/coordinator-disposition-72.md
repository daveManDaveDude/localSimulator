# Coordinator disposition 72 — best-effort secondary error recording

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Dispositions 64, 69–70 and the user's authorization for as many attempts as needed to pass the supervisor self-check.

## Review 15 finding accepted

Independent Sol review 15 is FIX_REQUIRED (report SHA-256 `2e11ee6efcd03189d59505976d95fa9d39b0f6ef3580a54210146b92f97ac845`). In S at the current reviewed hash `672838756b4183a14ffcf849671e2b90cc5828123dfb34cec92412d4ce9238b9`, the outer handler catches a secondary `_update_owned` exception, but dictionary construction, exception formatting, record insertion and error-list append at S:3105–3113 are not guarded. A reachable `MemoryError` in this best-effort recording can replace the original exception before the bare re-raise.

This is within disposition 70's accepted requirement: record secondary persistence errors when possible and never let them replace the original `exc`. Reuse the accepted `retry2-nonzero-reaping-plan.md`; no new behavior or acceptance criteria are introduced.

## Reserved correction

Reserve another Luna correction in S only. Guard the entire in-memory secondary-error reporting block so ordinary reporting failures (including allocation failure) cannot escape and mask the original exception; after best-effort recording, bare-raise the original. Do not change the primary BLOCKED record attempt, sticky non-PASS, final cleanup, normal reaping/identity/membership checks, original 10-second deadline, W/H/P, schema/path/filename, evidence, candidate/GIS/numerical/product artifacts or limits.

Luna may run only S Ruff check/format and plan-required non-operational static checks. No tests, imports, probes, process inspection, wrapper/self-check/preflight/runtime, or evidence/root changes. Independent Sol review 16 is required. Any failure returns to another plan-conforming diagnosis/correction/review cycle under disposition 64. Retry-2 stays consumed/non-PASS; no self-check before PASS and a separately reviewed fresh retry-3 path binding.

At entry, S is `672838756b4183a14ffcf849671e2b90cc5828123dfb34cec92412d4ce9238b9`; W/H/P and all original/retry evidence hashes are pinned in review 15. Preserve the earlier unsaved `957157…` hash limitation. Candidate remains **NO-GO and unservable**, build 3 unreserved. No runtime collection, manifests, GIS/numerical/build, serving/publication or browser action. No commit, push or merge.
