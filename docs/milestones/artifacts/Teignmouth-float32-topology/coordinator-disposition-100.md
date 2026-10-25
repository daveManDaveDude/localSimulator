# Coordinator disposition 100 — return fixed fallback immediately

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User's continuing authorization for as many bounded attempts as needed; preserve all historical counters and consumed roots.

## Review finding accepted

Accept independent Sol report `docs/milestones/artifacts/Teignmouth-float32-topology/build-3/selfcheck-fixed-fallback-independent-review.md`, SHA-256 `fa2e03204a91ce6637fef40279eb788e70222cbedf9938b5154945e751fdb23c`, as **FIX REQUIRED**. S currently assigns the fixed fallback and continues into optional note extraction/serialization. Disposition 98 requires an immediate return so no further lookup/allocation occurs if `str(exc)` fails. The previous unguarded f-string issue is closed; all other reviewed behavior is unchanged and the source delta is exactly one line.

## Narrow correction authority

Authorize Luna to change only the `except BaseException` branch of `_exception_message_with_notes` to `return "exception message unavailable"` directly. Keep the existing successful-string note serialization untouched and all types/phases/persistence/cleanup/source scope unchanged. Run only the two accepted Ruff gates and static review, save a handoff, and submit the exact S source for independent Sol review. No tests/imports/scripts/probes/wrapper/self-check/new root/runtime/downstream work is authorized.

## Preserved status

Retry-1 through retry-4 remain consumed, immutable and non-PASS. Candidate is **NO-GO and unservable**; build 3 unreserved. Outer exit1/internal exit2 and unsaved `957157…` remain separate unresolved facts.
