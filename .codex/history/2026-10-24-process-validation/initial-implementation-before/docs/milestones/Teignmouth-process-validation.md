# Teignmouth process-isolated validation

**Status:** Initial Sol implementation authorized and reserved on 2026-10-24.  
**Scope:** A new issue, separate from the exhausted line-tracing correction. This issue is an offline validation/timing prerequisite; it does not authorize a candidate trial, activation, publication or viewer change.

## User authorization and fixed boundaries

The user approved pursuing a different validation approach with a new explicit attempt budget. The prior correction remains FIX REQUIRED with its own exhausted budget. Do not relabel it, reset it, or alter its historical results.

Keep the v2 transition disabled and preserve its current policy: T0+120 s for input/preparation/solver, T0+125 s for complete offline validation, T0+135 s for finalization, with qualification requiring complete projected end-to-end time ≤125 s in both the implementer and independent profiles. Keep the 2,000 iteration limit, 84 × 82 m domain, source and accepted surfaces, road station union, all twelve gates, geographic/numeric/resource limits, source provenance, pending AOI/TQ1 4HN, consumed-trial inventory, accepted preview, default viewer and synthetic fallback unchanged. Do not create candidate output or run a solver, topology trial, browser comparison or public-site operation.

## Approach

Replace per-line Python tracing as the production deadline mechanism with one parent-supervised worker process for the whole post-solver transaction: offline gates, conditional deterministic assembly, both independent asset validations, resource checks and deterministic hashes. Keep the existing v2 gate arithmetic and cooperative checks. The parent owns the single monotonic T0. Worker launch, transfer, import, reconstruction, execution, return transfer, parent verification and cleanup count against the existing deadlines. A worker timestamp cannot extend them.

Use a fixed, versioned request/result protocol, not pickle or an arbitrary function runner. Use primitive metadata plus canonical binary arrays, and WKB only if the worker needs the influence geometry. Bind the request and response to invocation ID, protocol/worker version, exact byte lengths, dtype/shape/hash, candidate Float32 and accepted-grid identity, topology/constraints, source and release manifests with distinct labels, code/config/spec hashes, environment versions, protected snapshots, and consumed inventory. Reconstruct worker-local geometry and `ValidationContextV2` from the transferred bytes. Parent identity and cache objects do not cross the process boundary.

On Windows, contain the worker in a task-owned Job Object with kill-on-close. Create the process suspended, assign it to the job, then resume it. Do not allow breakaway. If creation or containment fails, terminate/wait the suspended process and fail closed; never fall back to an uncontained worker. On timeout, cancellation, parent exception, malformed output or worker failure, terminate the job and confirm exit within the remaining finalization budget before removing only that invocation's scratch. Cleanup failure is explicit. Never remove files while a worker may still write. Use bounded file-based request/result envelopes or a demonstrably deadlock-free bounded transport; do not block indefinitely on pipes. Account for every transfer copy inside the existing buffer limits.

Python `subprocess.run` documents timeout termination and wait behavior, but also notes that process creation itself may not be interruptible on some platform APIs. The Windows Job Object API manages process groups, can terminate all associated processes, and `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` terminates associated processes when the final job handle closes. The worker start/assignment ordering must be verified against the official Windows process APIs. See [Python subprocess](https://docs.python.org/3/library/subprocess.html), [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects), [AssignProcessToJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject), and [CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw).

Accept a result only after the parent verifies one complete envelope before T0+125 and confirms all requested operations occurred exactly once and in the prescribed order. Missing, duplicated, replayed or mismatched operations fail closed. A full envelope may contain failing gate results; it is not candidate acceptance. Without a complete envelope, emit the existing twelve unavailable/failed entries. A well-formed partial report may retain completed diagnostics, but later gates remain unavailable and `validationComplete=false`. No partial state can yield aggregate PASS. Keep worker scratch private and never promote it to candidate/public paths.

## Qualification evidence and stop conditions

Before a retained replay, run exactly one synthetic Windows containment probe, ≤15 s total, covering immediate success, a native-like blocking call, timeout, descendant containment, and parent-abort kill-on-close. It uses no project geometry, solver or trial. Stop if containment or bounded cleanup cannot be verified.

Then perform at most one implementer retained replay using the immutable `flip-05` buffers/report, externally capped at 135 s; no solver or trial. If complete, perform at most one independent Sol replay of the exact reviewed implementation/config/environment, also capped at 135 s. Record a complete accounting table for preflight, input loading, worker launch/transfer/reconstruction, all twelve gates, assembly and both validations, resource/hash checks, result verification, preservation, serialization/fsync/commit and cleanup. The runs must distinguish real failures from timing-only work. Do not force validation pass flags or fabricate approval receipts.

Complete qualification requires all twelve actual gate reports and reference equivalence, plus timing coverage for the successful assembly/validation/finalization path and activation-receipt preflight. Use only a legitimate retained fixture and shared production helpers to measure those operations. If a legitimate fixture or read-only preflight harness cannot cover a required path, record the specific missing evidence and stop; synthetic behavior tests and a mixed proxy do not qualify. Stop on an incomplete run, any preservation/protocol/resource mismatch, or complete projected duration >125 s. Do not start another timing variant or cap change under this issue. A correction that invalidates replay evidence does not automatically receive another replay; ask for a narrowly scoped execution-budget decision.

No trial or activation is authorized by timing qualification alone. A later trial still requires a fresh exact independent review/config/coordinator acceptance chain under the disabled transition rules, plus the existing stage-order and write-once protections.

## Files and checks

Expected focused changes:

- Add `pipeline/torquay_pipeline/road_surface_validation_process_v1.py` for the fixed protocol, Windows process containment, deadline supervision and bounded cleanup.
- Add `pipeline/scripts/run_teignmouth_validation_worker_v1.py` for the single worker entrypoint.
- Route the v2 wrapper through the worker without changing T0 offsets, gate arithmetic, resource limits or frozen runner behavior.
- Extend transition code-map bindings for the new worker/protocol/profile entrypoints and tests. Keep previous profile/review artifacts immutable.
- Add synthetic lifecycle/protocol tests and one solver-free retained-input profiling script. Add new issue evidence under `docs/milestones/artifacts/Teignmouth-process-validation/`.
- Update the transition specification with this issue's approach and status only after preserving its exact pre-change bytes. Record source-manifest and release-manifest identities separately.

Required checks: focused validator v2, transition, process lifecycle/protocol, profile and frozen-runner tests; Ruff check and format; `git diff --check`; preservation comparisons for protected source/release/preview inputs and consumed trial bytes. Browser work is not required because the issue changes offline supervision only; state explicitly that no browser run occurred. Do not claim timing qualification until both complete profiles and independent review pass.

## Explicit finite attempt budget

- One initial implementation by the Sol 6.1 / medium role; implementation agent actual runtime model/effort must be reported if exposed, otherwise unknown.
- At most one Sol correction, reserved for a specific independent-review finding. Zero Luna corrections.
- One ≤15 s synthetic containment probe, one ≤135 s implementer retained replay and one ≤135 s independent retained replay.
- No additional full replay is included if a correction invalidates evidence; stop for a specific user decision. No solver, topology trial, candidate generation, browser comparison or activation attempt is included.
- Independent Sol 6.1 / medium reviewer must not implement this issue. The planned reviewer is `/root/review_sol_escalation`; verify availability at review time.

After the initial implementation or sole correction receives FIX REQUIRED and the bounded budget cannot resolve it, stop with NEEDS USER DECISION. Do not relax limits or consume an unbudgeted attempt.
