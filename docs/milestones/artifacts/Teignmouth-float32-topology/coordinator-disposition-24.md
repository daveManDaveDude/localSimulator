# Coordinator disposition 24 — authorize build-3 supervision preparation only

Date: 2026-10-24

**Decision: GO for bounded operational dispatch-preparation work described in the build-3 dispatch/supervision subplan. This is not a candidate correction, geometry diagnostic, or candidate build. No candidate build is reserved. Candidate remains NO-GO and unservable.**

Accepted planning evidence:
- Build-3 proposal: build-3/evidence-plan.md, SHA-256 0f5ad7fef03c201314411b6d7ebbfc856ec2aa2cc489632a1ddcaf2fbb2e5f20.
- Dispatch/supervision subplan: build-3/dispatch-supervision-plan.md, SHA-256 260b1d6d89ad364748c23419dc4e1ac575ff8bba12f212cbe99364f51489417e.

Authorize Luna to implement only the three proposed build-3 infrastructure files:
- pipeline/scripts/run_teignmouth_float32_build3.py
- pipeline/scripts/teignmouth_build3_runtime_preflight.py
- pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py

The code must implement the fixed ordinal-3 builder dispatch, suspended Win32 Job Object assignment with kill-on-close, one 180-second total external deadline, bounded termination/preservation tail, truthful actual exit and resource telemetry, non-overwriting invocation/log/evidence paths, and external runtime bindings described in the accepted subplan. The separate self-check may launch only its fixed nonnumerical helper; the runtime-preflight-only mode may inspect runtime/modules but must not load GIS geometry or dispatch the builder. Keep the existing diagnostic supervisor and candidate builder bytes unchanged.

Authorize static Ruff check/format and one bounded nonnumerical self-check, maximum 10 seconds, but execute the self-check only after a different Sol session reviews the exact implementation hashes and confirms that its mode cannot reach candidate code/data. The self-check must not create build-3 run/output or consume any diagnostic/build/correction attempt. The runtime-preflight-only mode is not yet authorized to execute; request a separate coordinator disposition after the self-check review.

This operational preparation is separately classified because it does not modify the candidate or perform numerical construction. It reopens or resets no exhausted correction/diagnostic budget. Any scope expansion into candidate algorithms, source geometry, numerical diagnostics, package changes, or a build is unauthorized here.

After the supervisor self-check is reviewed, the coordinator may authorize one isolated runtime identity preflight. Only after its exact external-runtime closure is reviewed, the complete build-3 manifest is independently verified, and paths are fresh may a new coordinator disposition reserve build 3. The fixed 180-second maximum, no-retry rule, strict exact source-plane-zero gate and all data/geometry/guard limits remain unchanged.

## Counters

- Diagnostics: 2/2 used.
- Luna correction cycles: 4/4 used.
- Sol correction: 1/1 used.
- Candidate implementation builds: 2/6 used; build 3 unreserved.
- Confirmation builds: 0/1, ineligible until all offline gates pass.
- Candidate serving/runtime output: ineligible.
