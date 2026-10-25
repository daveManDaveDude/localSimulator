# Coordinator disposition 7 — build 1 outcome

Date: 2026-10-24

Implementation build ordinal 1 is consumed as **BLOCKED_EXCEPTION**. The bounded runner completed in 16.1827 seconds (under 180 seconds), measured peak working set 607,260,672 bytes, and found all 193 frozen input bindings unchanged before and after execution. Config and frozen-source loading passed; local construction completed with 64,765 vertices, 129,362 triangles and 136,656 constraint edges. Candidate assembly stopped with `Float32CandidateError: chart does not cover candidate vertex [-140.0, -63.0]` before serialization. All eight final gates are correctly marked unavailable after the exception. Chart and construction buffers are retained. Partial output was archived in evidence and the generated candidate output path is absent.

The build-report `workerReturnCode: 0` is inaccurate: the outer command exited 1 and the report status is `BLOCKED_EXCEPTION`; the worker entry swallowed the candidate builder's integer return code. Preserve this discrepancy for correction rather than treating 0 as successful.

The report indicates that the fixed influence geometry includes points beyond chart support. No grading conclusion is drawn from this run; no candidate terrain/road was serialized, and no overlay, gradient, section, road/building/walk, deterministic, browser, or screenshot gate ran. Build 1 does not pass. Do not retry or start a correction until independent Sol review and coordinator disposition.

Evidence: `docs/milestones/artifacts/Teignmouth-float32-topology/build-1/build-report.json`, `supervisor-report.json`, `gate-state.json`, `chart-stage.json`, `construction-stage.json`, and `coordinator-disposition-6.md`.
