# Coordinator disposition 82 — accept review-18 findings; request bounded correction plan

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Dispositions 64, 78, 80–81 and the user's authorization for as many attempts as needed to pass the supervisor self-check.

## Review 18 findings accepted

Independent Sol review 18 is FIX_REQUIRED (SHA-256 `9d4dfa9b32f141b3f5fd2d5775af7b4f8e2d12581b916d766b9fca92a947be7c`). Its addendum (SHA-256 `8902b1cee5fe309a38075e4ea876acc4b38c11fb12429a42e72117d73ebe5267`) confirms a second unclosed predicate. Reviewed S hash is `81fcdc0b199497d92d17c09c758a62b8861e7fcb7b41bb6a1c1663a1f76256af`.

1. In the diagnostic handle `finally`, `time.monotonic()` is called before `CloseHandle`. A reachable allocation failure there can skip the required single close attempt.
2. The executable image is hashed without before/after file/path identity checks. A detectable image/path change can still be marked simply observed, contrary to the accepted plan's requirement that changing observations remain partial.

The original complete census and sticky unexpected-PID rejection remain correct and unchanged. No evidence shows the retry-3 image actually changed or identifies PID 20712. No source-class exemption is justified.

## Next authorized action: Sol plan only

Request a concrete S-only plan for both findings under `retry3-unexpected-member-evidence-plan.md`. It must guarantee a CloseHandle attempt independent of timestamp/error-record allocation and keep optional close telemetry best-effort; detect and mark observable image/path instability as changed/partial using a bounded same-path metadata/identity comparison around hashing; preserve unknown/unverifiable stability as partial; and avoid claiming atomicity, mapped-image attestation or complete protection from concurrent same-metadata replacement. It must not change the shared `_sha256` semantics, APIs/rights, normal acceptance, W/H/P, schema ID, new files, deadline, root, evidence or other behavior. No implementation until coordinator plan acceptance.

Retry-3 and every prior evidence tree remain immutable/consumed/non-PASS. Outer `pwsh` exit 1 versus recorded supervisor/launcher exit 2 remains unresolved. The unsaved/untraceable `957157…` S-history limitation remains. No tests/imports/probes/process inspection/wrapper/self-check/preflight/runtime/evidence edits. Candidate stays **NO-GO and unservable**, build 3 unreserved. No commit, push or merge.
