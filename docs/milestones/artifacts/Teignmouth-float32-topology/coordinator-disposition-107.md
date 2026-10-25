# Coordinator disposition 107 — authorize the proven W indentation recovery

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User's continuing authorization for as many bounded attempts as needed; retry and consumed-root counters do not change.

## Diagnosis accepted

Accept Sol's read-only diagnosis in `build-3/retry5-w-inverse-mismatch-diagnosis.md`, SHA-256 `67246c232cb9590f6f79c86b4f67ea3ddfd8014844c7997bdb9a0f117398c08d`. The discrepancy consists exactly of two unauthorized indentation spans in W: line 23 has eight leading ASCII spaces instead of four, and line 344 has zero instead of four. No encoding or line-ending change is indicated.

The coordinator independently verified in memory that each exact span occurs once; correcting only those two spans produces projected retry-5 W SHA-256 `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0`, and reversing only the two retry-5 path literals from that projection returns accepted W baseline `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b`. This verification wrote no source bytes.

## Narrow correction authority

Authorize Luna to edit only `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` (W), replacing exactly the two leading indentation spans described above with four U+0020 spaces. Preserve the retry-5 path literals, every other W byte, and S/H/P bytes. Do not restore or rewrite W from a template or Git object. Do not alter line endings, encoding, BOM, final newline, other files or historical evidence. Stop if an expected span is missing/duplicated or any result differs from the required hashes.

At handoff, require W's complete SHA-256 to be exactly `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0`; the exact two-literal retry-5 path inverse must return `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b`. Confirm S/H exact path inverses to `28c92cc60e38ae23dcf58874eca67b8308b22772eee03b36d69471624fcdb089` and `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501`, with P unchanged at `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`. Repeat the original plan's exact literal counts, protected-source hashes, full 37-file preservation comparison, path/alias/ancestor checks and authorized Ruff/PowerShell AST checks. Save exact outputs and the source/evidence hashes in a handoff. Root and leaf remain absent. Independent Sol implementation review and a separate immediate coordinator one-use gate are still required before exactly one retry-5 invocation.

## Preserved limits

This authorization supersedes disposition 106 only for the two W indentation spans and the cited read-only verification. It does not authorize other source edits, root creation, invocation, preflight, numerical/GIS/build/browser work, serving, publication, commit, push or merge. Retry-1 through retry-4 remain immutable, consumed and non-PASS. Retry-5 remains unconsumed; candidate remains **NO-GO and unservable**; build 3 unreserved.
