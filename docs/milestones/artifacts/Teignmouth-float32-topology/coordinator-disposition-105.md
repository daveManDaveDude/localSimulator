# Coordinator disposition 105 — reconcile retry-4 evidence hash transcription

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Disposition 104; this resolves only the reported preservation-comparison discrepancy and does not alter evidence or counters.

## Coordinator reconciliation

Luna stopped before edits because its local expected value for retry-4 `supervisor-script-start.json` was `72f9f46afadbd1199b5bfbb091ed9dba06a23297c194f6de985f07a27e0d306d`. Coordinator independently recalculated the on-disk SHA-256 as `72f9f46afadbd1199b5bffb091ed9dba06a23297c194f6de985f07a27e0d306d`. The actual digest exactly matches both authoritative records: disposition 89's 11-file retry-4 matrix and `retry4-conhost-lifecycle-diagnosis.md`. A repository-wide exact-digest search found only those two authoritative entries, both with the actual digest; the transposed `...b5bfbb...` value appears in no repository artifact. File size is 1,037 bytes.

This is an implementer-side transcription discrepancy, not a changed evidence file or incorrect accepted matrix. The immutable file and historical documents are not modified. The other 36 entries were reported matching, but the complete 37-file comparison must be repeated using the authoritative matrices before the path edit proceeds.

## Resumption boundary

Disposition 104's path-only implementation remains in force. Luna may resume by rechecking all 37 prior evidence files against the exact authoritative matrices, recording each filename/count/hash result, and confirming retry-5 absence/alias/ancestor safety. If all pass, Luna may then make only the four accepted W/S/H literals and run the authorized Ruff/AST/inverse/protected-file gates. Any actual mismatch, unavailable record, changed bytes, path ambiguity or additional consumer remains a stop. No root creation or invocation is authorized.

## Preserved status

Retry-1 through retry-4 remain consumed, immutable and non-PASS. Candidate remains **NO-GO and unservable**; build 3 unreserved. No evidence edit, commit, push or merge.
