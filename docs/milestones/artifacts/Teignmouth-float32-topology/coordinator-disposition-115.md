# Coordinator disposition 115 — authorize Luna correction cycle 1 for W diagnostics

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User's continuing authorization for as many bounded attempts as needed; disposition 113 implementation release and disposition 114 review-only gate.

## Independent review finding accepted

Accept `build-3/retry6-w-descendant-escape-implementation-independent-review.md`, SHA-256 `3ab8e4d9ec1bf785b45c665907451a34890985e5ad57efa99cc8c2f3a1bb39d6`, as **FIX REQUIRED** for the exact W hash `dee858ce20851a306b157096d106ff79f6e9a6f89875f40dfee9d4b828bc9442`. The reviewer independently passed the exact inverse, static AST/C# compile-only gates, all 53 prior evidence files, six protected hashes and unchanged S/H/P; no runtime/self-check was run. The report identifies six implementation findings:

1. Capture helper reads a top-level cutoff absent from the initialized payload, so normal detail capture is skipped.
2. Reserve-path payload loses the supplied roots; capped chains must not claim an unknown root connection.
3. Optional clock, allocation/bookkeeping or serialization can replace a confirmed false-membership rejection; failed native membership queries need immediate error capture; commit the original rejection before fallible telemetry.
4. Raised close errors are suppressed on default and non-rejection paths, changing accepted behavior.
5. No-reserve handling builds a large payload before close, ancestry reconstruction can work over 65,536 rows before applying the 64-edge cap, and late allocations/completion are not consistently deadline-checked.
6. The no-reserve branch shadows the original Job ID count; over-limit serialization can attempt the minimal fallback twice.

## Bounded Luna correction authority — cycle 1

Authorize Luna to correct only these six findings in W, `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`, while implementing the already accepted diagnostic plan. Keep S/H/P, retry-1 through retry-5 evidence, source paths, caller schema, identity/census acceptance, false-member rejection, cleanup, defaults and 10-second total QPC deadline unchanged. Default/non-self-check callers must avoid diagnostic QPC/bookkeeping/overload effects; primary query error or false rejection is established before optional telemetry; diagnostic failures/clock/allocation/serialization cannot replace it; exactly one CloseHandle is attempted as the first finally operation, with baseline behavior retained outside the established self-check false-member path. Use the initialized cutoff consistently; retain bounded original roots/counts; skip detail/chain work when reserve is unavailable; cap chain work as well as storage to 64 edges; do not claim an omitted root link; preserve original counts when only storing the first 64 IDs; permit only one minimal serialization fallback attempt. Keep the primary failure, rejection and cleanup semantics unchanged.

Before and after correction, verify exact inverse to accepted pre-correction W `dee858ce20851a306b157096d106ff79f6e9a6f89875f40dfee9d4b828bc9442` by reversing only correction spans; also retain the accepted baseline inverse chain to `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0`. Preserve all 53 old evidence files and six protected hashes; S/H/P and retry-5 bytes remain unchanged. Run only authorized PowerShell AST parse and embedded C# compile-only gates; no method calls, tests, imports, runtime, process probes, wrapper/self-check/preflight, path change or root creation. Save exact byte-delta/inverse proof and full handoff for another independent Sol implementation review. If a correction would expand scope or cannot preserve original behavior/cleanup bounds, stop and report.

This is the first Luna correction submitted for independent review for this W-only diagnostic implementation; it does not reset historical correction or self-check counters. No invocation is authorized by this disposition.

## Preserved status

Retries 1–5 remain immutable, consumed and non-PASS. Retry-6 remains unselected, unreserved and absent. Candidate remains **NO-GO and unservable**; build 3 unreserved. No preflight, runtime profile, GIS/numerical/candidate build, reservation, serving/publication/browser work; no commit, push or merge.
