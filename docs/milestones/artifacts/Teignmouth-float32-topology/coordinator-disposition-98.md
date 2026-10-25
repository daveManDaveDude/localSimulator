# Coordinator disposition 98 — make exception-message fallback non-allocating

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User's continuing authorization for as many bounded attempts as needed; counters and consumed evidence remain unchanged.

## Review finding accepted

Accept independent review `docs/milestones/artifacts/Teignmouth-float32-topology/build-3/selfcheck-note-serialization-independent-review.md`, SHA-256 `bafe857fb8554431c6a02d418c3df1435dbc75b1bd3977bbe8cbd68ccc40c7b5`, as **FIX REQUIRED**. Both persisted error paths now serialize bounded notes, but `_exception_message_with_notes` at S line 3601 performs a second formatted allocation after `str(exc)` fails. This can mask the original exception and interrupt failure checkpointing. No resource-failure path was induced.

## Narrow correction authority

Authorize Luna to change only `_exception_message_with_notes` so a failed `str(exc)` returns a fixed preexisting literal directly, without another formatting, type lookup, allocation or unguarded operation. Keep type/phase fields in their existing records, preserve the exact primary string prefix whenever `str(exc)` succeeds, and keep optional note extraction, JSON serialization and concatenation best-effort. Preserve both call sites, the schema and all close/console/launch/cleanup logic.

Run only the two approved Ruff gates and static review; no tests/imports/scripts/process probes/wrapper/self-check/new root/runtime/downstream operation. Save the correction handoff and submit exact S for fresh independent Sol review. No self-check is authorized by this disposition.

## Preserved status

Retry-1 through retry-4 remain consumed and non-PASS. Candidate is **NO-GO and unservable**; build 3 unreserved. Outer exit1/internal exit2 and historical `957157…` remain separate unresolved facts.
