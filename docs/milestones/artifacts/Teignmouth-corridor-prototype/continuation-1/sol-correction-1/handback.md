# Sol correction 1: stopped at Float32 topology collision

Status: **STOP; submitted for separate independent Sol review.** The single Sol correction and final implementation build ordinal 6 are consumed. No further correction, retry, diagnostic, confirmation build, browser work or runtime integration was performed.

## Approved change and files

The coordinator's [limit decision 1](../limit-decision-1.md) changes only the continuation candidate's absolute source-relative terrain-change cap from strict `<6.0 m` to strict `<6.5 m`. Every other limit, source identity, geographic bound, road width, profile, chart and grading rule remains unchanged. This is a candidate-local allowance, not a public/product policy change.

- `pipeline/torquay_pipeline/teignmouth_corridor_continuation.py`: expected cap, necessary preflight, final overlay gate and associated report text now use strict `<6.5 m`.
- `config/road-surface-teignmouth-corridor-continuation.json`: the same candidate-only cap.
- `pipeline/tests/test_teignmouth_corridor_continuation.py`: equality rejection for both signs at 6.5 m and acceptance of 6.499 m as a necessary-only preflight result.
- `pipeline/scripts/build_teignmouth_corridor_continuation.py`: fresh exact build-6 output guard and corresponding exclusion/text only.

The [implementation diff](implementation.diff) compares these files with their exact pre-implementation archives. The [authorization bindings](authorization-bindings.json) preserve the archived source/config/test/runner/spec/ledger identities and bind the unchanged diagnostic and coordinator decision. Coordinator-owned specification/checkpoint files were not edited by this implementer. The attempt ledger was updated after the one build to consume its existing reservations.

## Actual build result

The exact repository virtual environment passed the GIS-free import smoke. Build 6's leaf was absent before invocation and was created by the runner. The [actual report](build-6/report.json) records **STOP**, with no primary telemetry error:

```text
TopologyError: distinct Float64 topology vertices collide after Float32 conversion:
(-164.2316811012587, -85.5) and (-164.23167542853238, -85.5)
```

The existing mesher rejects these distinct construction vertices because they map to one Float32 coordinate. No merging, snapping tolerance change, triangulation change or retry was attempted. Mesh construction began but no final mesh was returned, serialized or validated. Its incomplete internal construction data was not available after the exception; the actual chart buffers and exact collision coordinates remain available.

Measured build wall time: **7.3737599000 seconds** against 180 seconds. Actual peak process working set: **564,113,408 bytes**. No arbitrary memory/payload cap was introduced.

## Earthwork and stage evidence

Reaching `assemble_corrected` establishes by control flow that necessary preflight and the preliminary nearby-road core-ownership check returned passing results. The runner's existing exception handler replaces the intermediate report, so their detailed build-6 reports were not retained. This is an explicit evidence limitation; it is not a separately certified ownership result.

The actual build-6 chart buffers are byte-identical to diagnostic 1's bound build-5 buffers. The field, source loader, chart, ownership and section-sampler function ASTs are unchanged. Therefore [diagnostic 1](../diagnostic-1/full-field-earthwork.json) supplies reusable sampled-earthwork evidence for the unchanged field, rather than a new numerical execution:

- Complete required sample count: **21,336**.
- Maximum sampled absolute change: **6.397848390875038 m**, below the new 6.5 m cap; this is not a continuous-field or final-mesh maximum.
- Maximum-cut witness: station **145.5973799475 m**, lateral **−4.6887005660 m**, X/Z **`[-144,-98]`**; source Y **3.5783228874 m**, candidate Y **−2.8195255035 m**.
- Maximum sampled fill: **+3.1074350717 m**.
- There is no retained build-6 first earthwork violation. The earlier 6.0568207573 m first violation concerned the old 6 m cap and remains historical evidence.

The [stage observations](stage-observations.json) distinguish retained measurements, reused evidence and control-flow inferences.

## Gates and preservation

- Chart: constructed; three actual buffers retained, totaling **78,048 bytes**.
- Necessary earthwork preflight: passed by control-flow inference; prior complete diagnostic reused with bound identical inputs.
- Preliminary road-core ownership: passed by control-flow inference; detailed result lost on the later exception.
- Float32 topology: **failed during construction**.
- Final source/patch overlay earthwork, added gradients, exact final perimeter and local section gates: **not reached**.
- Complete building contact, road reclip/drape and shared walking surface: **not implemented/evidenced**; no pass claimed.
- Independent corrected-algorithm determinism: **not established**; confirmation build unused.
- Candidate serving, browser screenshots, fallback and product/share integration: **not performed; serving blocked**.

The build's before/after snapshots compare **944 protected paths**, with zero changed paths. A current rehash of all 944 paths also found zero mismatches. Scope covers the recorded repository/public-package and historical-evidence files, including build 5 and diagnostic 1; it does not independently hash every ignored raw GIS download. Sources, accepted preview, current/historical packages, Site, AOI, default/product code and port 5173 were not modified. No commit, push or merge occurred. Old v2 remains separate and inactive.

## Checks and next action

Focused synthetic continuation/continuous/original-corridor tests: **38 passed in 7.24 s**. Scoped Ruff check and format check passed. Exact-venv GIS-free import smoke passed. `git diff --check` passed with existing CRLF warnings. [Verification](verification.json) records commands, directories and results.

Counters at submission: four Luna correction cycles used; one Sol correction used; six implementation builds used; one diagnostic used; zero confirmation builds used. No additional attempts remain for implementation. The reserved confirmation allowance cannot repair a failed candidate.

A separate Sol agent/session must independently review the actual changes and evidence. This implementer has not self-reviewed or assigned an acceptance verdict. Further work requires coordinator/user disposition consistent with the exhausted correction budget and recorded topology failure.
