# Independent Sol review 4 — implementation build 1 evidence

Date: 2026-10-24

## Decision

Build 1 evidence consistently establishes **BLOCKED_EXCEPTION**. The run is consumed; this review does not authorize a retry. There is no evidence blocker to a later bounded Luna correction 3, after coordinator review of the Sol diagnosis.

## Evidence checks

- Recorded elapsed time is 16.1827 seconds, below the 180-second maximum; no timeout.
- Peak working set is 607,260,672 bytes as reported by `GetProcessMemoryInfo`.
- Pre-run and post-run records each report 193 bindings checked, zero changed.
- Chart and construction buffers exist, with counts consistent with the report: 64,765 vertices, 129,362 triangles, and 136,656 constraints.
- Candidate assembly stopped at chart lookup for `[-140.0, -63.0]`, before serialization.
- All eight final candidate gates are unavailable/false. Config, source load and local construction are preliminary stage results, not candidate acceptance.
- The archived partial-output directory is empty and the generated output path is absent, consistent with failure before serialization.

## Exit status limitation

The build report and supervisor report say `workerReturnCode: 0`. The worker entry calls `_worker_build()` but discards its integer failure return, so child process exit 0 does not mean the build passed. The runner source returns 2 on a non-PASS result. Luna reported outer exit 1, but no raw captured outer exit record was found; preserve the observed discrepancy as **unverified**, and do not equate any zero with candidate success.

## Recommended next scope

Sol planner should explain the chart/influence support mismatch from saved chart/source evidence without another numerical run. A subsequent correction may classify out-of-chart points as unchanged source only when it proves those points lie outside the nonzero treatment support; otherwise missing chart coverage remains a failure. The correction should also propagate/report the worker result unambiguously. Keep domain, source, origin, recipe, limits and collision guard unchanged. Preserve build 1 and its evidence.

No files were edited, and the reviewer did not rerun resource/hash verification, tests, source loading, diagnostic, or candidate build.
