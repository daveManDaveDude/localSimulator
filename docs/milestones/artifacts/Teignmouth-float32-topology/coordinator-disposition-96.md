# Coordinator disposition 96 — serialize bounded secondary cleanup notes

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User's continuing authorization for as many bounded attempts as needed; all historical counters and self-check roots remain intact.

## Review finding accepted

Accept Sol's independent review `docs/milestones/artifacts/Teignmouth-float32-topology/build-3/selfcheck-stdio-release-correction-independent-review.md`, SHA-256 `1cd46eb6654ca8f9c070bdc1fab347910d7d7767043432a8dcf36ed89bb4dd24`, as **FIX REQUIRED**. It confirms the stdio-close failure blocks resume and uses the existing suspended-child cleanup, but the secondary close failures live only in exception notes. `checkpoint_normal_failure` and outer error serialization persist only `str(exception)`, which omits those notes. No actual close failure was induced. The report also identifies a typo in Luna's handoff S digest; coordinator source hash and this disposition use the recalculated correct hash, and the historical handoff is left immutable.

## Correction authority

Authorize Luna to make the narrowest S-only correction that serializes secondary failure notes into the **existing message field** at both the normal-helper checkpoint and outer self-check failure record. Keep primary exception type, exact original message as a prefix, phase, identity and propagation unchanged; append a bounded JSON-safe representation of available secondary notes without adding schema fields/version, filenames or modes. Extraction/formatting must be best-effort so it cannot mask the primary error or block cleanup. Cover both query/CreateProcess failures with close failures and the created-but-unconfirmed-release cleanup path.

No change to false/raised close handling, one-attempt semantics, suspended-child cleanup, console query/launch behavior, W/H/P or acceptance gates. Run only the existing plan-authorized Ruff check/format gates and static review. No tests/imports, live process inspection, runtime, wrapper/self-check, new root, evidence mutation or downstream work. Submit current S for fresh independent Sol review; this disposition authorizes no self-check.

## Preserved status

Retry-1 through retry-4 remain consumed, immutable and non-PASS. Candidate remains **NO-GO and unservable**; build 3 unreserved. Outer exit1/internal exit2 and historical unsaved `957157…` hash remain separate unresolved facts.
