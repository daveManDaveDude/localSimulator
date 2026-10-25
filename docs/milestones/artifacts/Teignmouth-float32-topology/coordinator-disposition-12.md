# Coordinator disposition 12 — reserve implementation build 2

Date: 2026-10-24

**Decision: GO for one bounded offline candidate build, ordinal 2, maximum 180 seconds.** Independent Sol review 6 approved the supplemental manifest after recomputing all 225 bindings. The manifest includes all 20 build-1 evidence files and their inventory; the archived partial-output directory remains empty. The coordinator also independently verified all 225 entries. Candidate output was absent before reservation.

Use the correction-3 implementation with `build-2/input-manifest.json`, current attempt ledger, build ordinal 2, and a fresh evidence directory `docs/milestones/artifacts/Teignmouth-float32-topology/build-2/run-1/`. Do not edit code/config or change either immutable manifest. Enforce the runner's 180-second limit and capture logical worker status, child exit, runner result, externally observed command result if available, elapsed/peak-memory telemetry and pre/post preservation. Do not retry if it fails.

This reserves only one offline build. It does not accept the candidate, authorize serving, or authorize browser/product/public integration. The candidate remains ineligible until every offline gate passes and a separate review accepts the evidence.

## Counters after reservation

- Initial Luna implementation: 1 used, 0 reserved.
- Luna correction cycles: 3 used, 0 reserved.
- Sol corrections: 0 used, 0 reserved.
- Diagnostics: 1 used, 0 reserved.
- Implementation builds: 1 used, 1 reserved (build 2 of 6).
- Independent confirmation builds: 0 used, 0 reserved.
- Candidate serving/runtime output: ineligible.
