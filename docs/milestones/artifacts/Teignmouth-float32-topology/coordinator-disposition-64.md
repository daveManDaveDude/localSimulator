# Coordinator disposition 64 — iterative repair authorization for self-check

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User instruction: “I authorise as many attempts that are needed to get this working,” following the coordinator's explicit scope that the current target is making the supervisor self-check pass, while not authorizing a candidate build or GIS work.

## Authorized target

Continue repairing the wrapper-driven 10-second nonnumerical supervisor self-check until it passes, using serial diagnose/plan → Luna implementation → independent Sol review → one wrapper self-check after each PASS. Preserve earlier attempts and counters; this additive authorization does not rewrite or reset them. Keep one change/review/self-check cycle active at a time. Any different or broader issue requires separate authorization.

The latest failed one-shot is documented in disposition 63. It returned exit 2 before native launcher creation because `CreateFile` argument `access` was supplied as `-2147483648` and could not be converted to `UInt32`. The caller record reports no process launch and no candidate build. Treat this as a PowerShell/.NET interop numeric-type defect; do not infer or alter memory, GIS, topology, road grading, source, geometry or numerical parameters.

## Current-cycle requirements

1. Sol creates a bounded read-only plan for the exact `CreateFile` access-argument type issue using the actual W declaration/call, failed caller record and official PowerShell/Windows API documentation. No operational calls while planning.
2. Luna implements the accepted minimal W-only correction. Preserve exact destinations, ownership checks, handoff identity, cleanup, deadlines, sticky failure semantics, and no-launch-before-review.
3. Luna runs the affected non-operational static checks; reuse unchanged S/P/H Ruff and interop declaration evidence when their pinned hashes remain identical.
4. Independent Sol review inspects actual W and preservation evidence. A FIX_REQUIRED result authorizes another bounded Luna correction cycle under this disposition; no operational run follows until PASS.
5. After PASS, run exactly one wrapper-driven self-check with the existing 10-second cap, capture its actual result, then stop and plan the next cycle if it failed. Do not repeat a wrapper invocation within one cycle.

## Excluded work and preservation

This authorization does not reserve or execute build 3; authorize runtime identity collection/verification, manifests, GIS/numerical work, serving or browser actions; change candidate limits; or authorize publication. Candidate remains **NO-GO and unservable**, build 3 unreserved. Preserve all prior evidence byte-for-byte, including the first failed retry caller/handoff records in `.codex/build3-supervisor-selfcheck-retry-1/`. No commit, push or merge.
