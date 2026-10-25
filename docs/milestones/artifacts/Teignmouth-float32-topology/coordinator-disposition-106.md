# Coordinator disposition 106 — stop retry-5 patch on W inverse mismatch

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Disposition 104 plus hash reconciliation in disposition 105. This is a preservation stop, not a new attempt.

## Observed state

Luna reports that the full 37-file prior-evidence comparison passed after disposition 105, and that retry-5 path/ancestor checks and Ruff/PowerShell AST checks passed. No root/evidence was created or modified. The required inverse proof then failed on W and work stopped before a handoff.

Coordinator read-only checks confirm:

- W current hash: `26350581425f4853f25eeac3c05a14c32a94ab1f6e6589d5a5a67dcf3df497af`.
- Replacing only its two exact retry-5 parent literals in memory yields W inverse hash `4f0c60e7cebca4048af5d67b409d41a416c91d60dc5c88db1db016800d139116`, not accepted baseline `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b`.
- S and H current inverse checks each replace exactly one planned literal and reproduce their accepted current baseline hashes (`28c92cc60e38ae23dcf58874eca67b8308b22772eee03b36d69471624fcdb089` and `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501`). P remains `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`.
- W has exactly two retry-5 literals and zero retry-4 literals; S/H each have the expected one retry-5 literal and zero retry-4 literals. Retry-5 root remains absent.

The W inverse discrepancy is unresolved. The current W is no longer review-ready. No rollback, line-ending conversion, re-encoding, manual repair or additional source edit is authorized until a read-only diagnosis identifies the delta and a concrete preservation-safe recovery. Preserve current W/S/H bytes exactly while diagnosing; do not create the root or invoke W.

## Next gate

Authorize Sol for read-only source-byte diagnosis: inspect current W encoding/line endings and available historical/baseline copies or records; explain why the two-span inverse yields `4f0c…` rather than the accepted `6ed89…`; determine whether an exact restoration can be proven without guessing. Do not edit, reformat, normalize line endings, inspect live processes, read or modify consumed evidence contents beyond the already required preservation check, or run wrapper/self-check/runtime. Return the minimal safe recovery or a precise blocker.

## Preserved status

Retry-1 through retry-4 remain consumed, immutable and non-PASS. Retry-5 remains absent and unconsumed. Candidate stays **NO-GO and unservable**; build 3 unreserved. No new self-check is authorized. No commit, push or merge.
