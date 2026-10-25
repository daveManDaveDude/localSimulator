# Independent Sol review 7 — implementation build 2 evidence

Date: 2026-10-24. Reviewer: `/root/sol_correction_reviewer`, independent non-implementing Sol session.

## Decision

Build 2 is a genuine validation failure, but the captured error does not establish a physical topology hole. **Candidate serving remains NO-GO.** No retry is authorized by this review.

## Findings

The artifact and inspected code agree: face **19669** has full area **0.020639419555664062 m²**, while its intersection with the outside-influence mask is only **1.1028883815799223e-12 m²**. The overlay helper discards each source-intersection fragment <=`1e-12` before accumulating coverage or testing extrema. Multiple discarded fragments could therefore produce `coveredArea=0`, followed by failure against the slightly larger total expected area. Clipping arithmetic is another possibility. The captured error alone cannot distinguish these causes.

The traceback stops at the first outside-influence call to `affine_surface_overlay_extrema` from `_serialize_candidate`. This is a clipped source-plane validation failure; it is not evidence that the entire 0.020639419555664062 m² face lacks source coverage. The earlier stored-local-topology gate passed, but that result does not substitute for the failed source overlay or any later acceptance gate.

Earlier evidence is internally consistent: four support/topology gates passed; seven later gates remain unavailable. Serialization buffers survived. Reports record **33.19761470000958 seconds**, **225 unchanged bindings**, and logical worker, actual child and runner-chosen exits all **2**; external command exit remains explicitly uncaptured. Failed output was archived and generated output was absent at inspection. Measurements and preservation reports were inspected, not independently recomputed.

## Narrow next action

One bounded, saved-artifact diagnostic on this face and its source intersections is the narrowest safe next action. Record every fragment, including discarded fragments, its union, summed area, uncovered/overlapping area and extrema witnesses. No full rebuild or parameter sweep is needed. This recommendation does not reserve or execute the remaining diagnostic.

A correction is justified if that diagnostic confirms accounting or clipping inconsistency. Required invariants and tests:

- Positive-area fragments contribute consistently to coverage and extrema.
- Several individually subthreshold fragments cannot disappear from a covered region.
- Genuine missing coverage and overlapping source partitions still fail.
- Empty clips behave explicitly; ordinary complete overlays retain their results.
- Fixed origin, domain, source, collision guard and every numeric limit remain unchanged.

Use the evidence to scope the **last Luna correction**, without relaxing tolerances. A shared-helper change requires explicit coordinator approval; a prototype-local implementation can preserve historical helper bytes. Consume/reconcile build 2 in the ledger before further dispatch. One diagnostic remains; no automatic retry is authorized.

## Exact evidence and source paths

- `docs/milestones/artifacts/Teignmouth-float32-topology/build-2/run-1/build-report.json`
- `docs/milestones/artifacts/Teignmouth-float32-topology/build-2/run-1/supervisor-report.json`
- `docs/milestones/artifacts/Teignmouth-float32-topology/build-2/run-1/gate-state.json`
- `docs/milestones/artifacts/Teignmouth-float32-topology/build-2/run-1/serialization-stage.json`
- `docs/milestones/artifacts/Teignmouth-float32-topology/build-2/run-1/gates/storedLocalTopology.json`
- `docs/milestones/artifacts/Teignmouth-float32-topology/build-2/run-1/serialized-world-positions.xyz.f64`
- `docs/milestones/artifacts/Teignmouth-float32-topology/build-2/run-1/serialized-indices.u32`
- `docs/milestones/artifacts/Teignmouth-float32-topology/build-2/run-1/serialized-candidate-y.f32`
- `docs/milestones/artifacts/Teignmouth-float32-topology/build-2/run-1/partial-candidate-output/`
- `docs/milestones/artifacts/Teignmouth-float32-topology/build-2/input-manifest.json`
- `docs/milestones/artifacts/Teignmouth-float32-topology/build-2/prior-build-1-preservation.json`
- `docs/milestones/artifacts/Teignmouth-float32-topology/attempt-ledger.json`
- `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` (`_serialize_candidate`, first outside-influence overlay)
- `pipeline/torquay_pipeline/road_surface_topology.py` (`affine_surface_overlay_extrema`, per-intersection area filtering and verified-partition coverage comparison)

## Review boundary

The assessment was read-only. No build, numerical diagnostic, source load, test, numeric reconstruction, or implementation edit occurred. Existing reports/code and saved-artifact presence were inspected using read-only file commands; no numerical verification was executed. This document is the subsequent authorized persistence of that assessment, and its own SHA-256 is calculated for handback without repeating the review commands.
