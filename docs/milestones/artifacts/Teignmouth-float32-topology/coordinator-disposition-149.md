# Coordinator disposition 149 — correct H byte offset in path handoff

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** D148 and independent actual-byte review below.

## Review finding

Accept `build-3/retry-7-path-binding-independent-review.md`, SHA-256 `6101cdc8763c04073ea116e1d0e64a9d258d7c55384e13b6a63c51f9863da14f`, as FIX REQUIRED for one handoff metadata error only. The actual four-literal patch, hashes, inverses, counts, and static/preservation results pass review. In `retry-7-path-binding-implementation-handoff.md`, the H17 changed-digit zero-based offset is incorrectly recorded as391; the independent byte diff establishes offset385. Literal start344 is correct. No source change is indicated.

## Narrow authorization

Authorize Luna to change only the H17 changed-digit offset `391` to `385` in the exact-byte-delta table of `build-3/retry-7-path-binding-implementation-handoff.md`. Do not alter literal start344, any source byte, evidence, gate output or other report content. Rehash the handoff and state the changed field. No Ruff, AST, preservation gate or path/root operation should run.

Then authorize the same separate Sol reviewer to recheck the corrected handoff field against actual H bytes and source hashes, verify no source changed, and issue a final PASS/FIX REQUIRED for the actual-byte review. This is report-only reconciliation; the earlier gate evidence is reused by exact source hashes. Stop for coordinator decision after review.

## Boundary

No path/ancestor/alias/absence check, root selection/reservation/creation, self-check, runtime, process inspection, retry invocation, preflight/build, GIS/numerical/product/AOI/serving/publication, commit/push/merge or TVW-016. Retry7 remains proposed/unselected/unreserved; retries1–6 consumed/immutable/non-PASS and counters unchanged. Candidate remains **NO-GO and unservable**, build3 unreserved.
