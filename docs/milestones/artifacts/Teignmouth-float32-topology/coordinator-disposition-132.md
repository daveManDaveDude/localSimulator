# Coordinator disposition 132 — resolve missing final-census completeness proof

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User's continuing authorization; dispositions 130/131 and independent plan review.

## Plan finding accepted

Accept `build-3/retry6-s-wait-callback-correction-plan-independent-review.md`, SHA-256 `15e309662c714efc684d86896d4037a452892c7419d4be5446eacc1bcfa0a062`, as **FIX REQUIRED for the plan only**. F1 is a valid completeness gap: the unchanged `_assert_tree_contained` stops when `Process32NextW` returns false, but exposes no reason/completion state. A wrapper around its normal return cannot distinguish complete end-of-snapshot from enumeration error, so it cannot truthfully record the planned complete final census. No implementation authority was granted and no source changed.

## Explicit S-only scope resolution for a revised plan

Authorize Sol 6.1 to prepare one revised, focused S-only plan that may change the self-check tree containment enumeration helper and its self-check call site as strictly necessary to expose verified completion of the **same bounded census**. The revised design must capture/validate the terminal enumeration status immediately after the existing `Process32NextW` false result, distinguish documented normal end-of-snapshot from errors, and propagate every unknown/error/incomplete outcome as BLOCKED. It may not duplicate or broaden the census, treat any false return as complete, weaken row/pass/time bounds, or consume an unchecked prefix as complete.

The plan may propose using an already configured `ctypes` last-error mechanism. If that facility is not actually available at the call site, the plan must identify the smallest required S-local binding/configuration change, its error-capture ordering, and why the existing mechanism cannot suffice. This disposition authorizes planning that bounded option only; it does **not** authorize implementation of a new API/binding. Any broader/new Win32 dependency, changed acceptance, shared default/build/preflight behavior, W/H/P change, or inability to prove terminal status is a stop for a further coordinator decision.

The revised plan must combine this completeness proof with the reviewed wait/callback-boundary fix: preserve the three-second deliberate wait, the inherited ten-second total QPC budget and cleanup reserve, local fail-closed late/unknown behavior, one mandatory final census after the wait horizon, exact Job/identity/marker/termination checks, default callers and all current path bindings. Keep retry-6 evidence immutable; do not read prior retry1–5 evidence contents. No source change, test, parser/compiler/linter, runtime/process inspection, retry-7 path/root, self-check or candidate build. Save a new v2 plan without editing the old plan/review; stop for separate independent Sol plan review and a new coordinator decision.

## Preserved state

Retry-1 through retry-5 and retry-6 remain consumed, immutable and non-PASS. Retry-7 remains unselected/unreserved. No issue counters reset. Candidate remains **NO-GO and unservable**; build 3 unreserved; the original ten-second QPC deadline remains unchanged.
