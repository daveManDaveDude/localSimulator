# Teignmouth timing bootstrap — Stage A stopped

Status: **BLOCKED at the approved source-request representability assessment**.
No Stage A readiness PASS, implementation integration, permit or trial dispatch.
The approved proposal remains byte-identical and live activation stays false.

## Actual result — 24 October 2026

The existing Unicode-safe `value_bound()` estimator rejected an unmodified subgraph
of the actual pinned `ReleaseInputs` loaded through `load_candidate_inputs()`:

| Observation | Actual value |
| --- | ---: |
| First rejected `require_memory` argument | 114,744,396 bytes |
| Unchanged construction/transport ceiling | 67,108,864 bytes (64 MiB) |
| Source loading | 0.470322500 s |
| Bound inspection | 2.720697400 s |
| External assessment elapsed | 4.313512000 s |
| Exit status | 2 |

The failed subgraph is part of `CompositeSurface.inputs`, which the current fixed
codec recursively transfers. Additional mesh/candidate/request fields cannot reduce
its bound. This proves failure of the current protocol's admitted-source estimator,
not an actual allocation/RSS overrun. Traversal stopped at the first rejected
subgraph: the complete source/request total is unknown and deliberately recorded
as null. The source road JSON is 87,338,409 bytes; that file size alone was not used
as proof. The actual source-object estimator produced the rejection.

The diagnostic only loaded and hash-validated the frozen source/release/accepted
preview. It observed calls to `require_memory`, then invoked the unchanged original
guard. Codec encoding/decoding/sidecars, canonical request serialization, topology,
solver, validation/assembly and worker launch were guarded against invocation;
there were zero forbidden call attempts. No station/topology/candidate was generated.

## Evidence and preservation

- `artifacts/Teignmouth-unicode-timing/bootstrap/source-request-readiness-assessment.py`:
  exact diagnostic source, SHA-256
  `78a3a3804b1a45e47fc603e6e958452a4e8679b6e1798560f298640b88f812d6`.
- `source-request-assessment-command.json`: exact argv/cwd, 30 s external bound,
  script hash, stdout/stderr, elapsed time and exit status.
- `source-request-representability.json`: actual inputs/source maps, versions,
  estimator module hash, first rejected count, before/after bindings and absent
  collar/candidate directories. Its elapsed values are diagnostic accounting,
  not timing qualification evidence or a validation profile.
- `.codex/history/2026-10-24-unicode-timing/stage-a-before/manifest.json`: seven exact
  before-images captured before assessment. Source/config/spec/tests were not edited.
- `stage-a-stopped-preservation.json` and `stage-a-stopped-manifest.json`: final
  preserved-input/history identities and stopped-stage bindings.

Requested model/effort: gpt-6.1-sol / medium. Actual runtime settings are unknown
because they are not exposed; issue usage unavailable. Existing Phase 1 safety PASS
and historical containment results remain unchanged, but do not establish request
representability. No test, probe, profile/replay, solver, trial, candidate build,
activation, browser, publication or commit ran. `collar-05` and public candidate
output remain absent. No one-use permit or dispatch marker was created/consumed.

## Stop and remaining scope

Per the accepted Stage A implementation plan, readiness stops before substantial
integration on this result. The shared receipt verifier, evidence-only admission,
permit handling and timing/profile instrumentation were not implemented.
No limit was raised, no source was cropped and no serialization/representation was
changed. A separately scoped decision about representing the full source-bound input
is needed before Stage A can resume; this handback does not approve one. Do not
consume collar-05 or either retained profile to diagnose this blocker.

Initial Stage A work stopped at its first diagnostic; no implementation safety
submission/PASS exists. No Sol correction was used or reserved. Trial/profile
allowances remain unused and gated; this metadata record does not reset any budget.
Next action: coordinator/independent read-only assessment of the exact blocker.
