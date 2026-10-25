# Teignmouth corridor-grading prototype — continuation 1

**Status:** user-authorized continuation, 24 October 2026. **Scope:** local, opt-in experimental road/terrain treatment and comparison only. The original prototype and correction-1 results remain immutable failed-attempt history; this continuation has a new counter ledger. It does not reopen topology-validation v2 or authorize its guardian, permit, profile, activation, or product integration.

## Authorization and roles

The user explicitly reset the active corridor prototype's attempt counters and authorized the coordinator to choose candidate limits. Preserve all earlier records and counters as historical evidence; the new continuation ledger starts at zero. Roles: Luna orchestrates and implements; Sol 6.1 plans, diagnoses, and independently reviews. A Sol correction is allowed only after four completed Luna correction cycles have been reviewed, and must be reviewed by a different Sol session.

The user authorization does not alter global product policy, source data, the public/default viewer, accepted preview, Site, historical package, AOI, or source provenance. Candidate geometry remains local and opt-in; no failed or partial candidate may be served.

## Objective and frozen inputs

Continue the separate BeamNG-inspired corridor-grading experiment for the same Teignmouth Road source segment. Compare it with the unchanged source-draped baseline in matched views. This is a visualization prototype, not surveyed pavement geometry or a replacement terrain dataset.

- Base issue and recipe: [original corridor prototype specification](Teignmouth-corridor-prototype-spec.md). Preserve its fixed continuous station/lateral chart, Gaussian sigma 12 m profile, source centerline X/Z, estimated 6 m carriageway, 1 m shoulders, 2–12 m / 1:2 transition, 32 m longitudinal fades, local bounds, source release, provenance, and feature ownership requirements.
- Source release: `616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a`; OSM way `78455395`, part `0`; assess stations 140–155 m and retain the registered anchor at 148.15104603556912 m.
- Input terrain remains the packaged EA DTM-derived 2 m grid. Interpolation and local refinement do not create a higher-resolution source.
- Preserve TQ1 4HN centroid and AOI `selected_pending_coverage` / `not_checked`, all source bytes, historical and current packages, synthetic fallback, accepted preview, public Site, and product default behavior.

## Candidate-local limits

These limits apply only to the isolated continuation candidate. They do not change global terrain policy or accept/promote a road surface.

| Metric | Continuation acceptance | Reason |
| --- | --- | --- |
| Absolute candidate/source terrain change | Strictly `<6.5 m` at all required samples and source/patch overlay extrema | Coordinator decision 2026-10-24: the bounded full-field diagnostic measured a maximum absolute change of 6.3978483909 m across all 21,336 unique required preflight samples, with 49 samples above the former 6 m cap. The 6.5 m candidate-only ceiling permits the frozen recipe to proceed to Float32-mesh and overlay-extrema checks, with about 0.102 m between the sampled maximum and the cap. It is a chosen candidate cap, not an estimate of mesh error or an engineering safety certification. The measured recipe-sample maximum is below the prior topology's reported 6.460917 m, but this new cap itself does not guarantee a better maximum. |
| Positive added edge gradient | Strictly `<1.0 m/m` | Retain; corrected final geometry has not yet demonstrated that the earlier 2.347595 m/m discontinuity is fixed. Diagnose geometry rather than relax this limit. |
| Full-width local cross-slope | `≤5%`, checked locally across the complete 6 m width at no more than 0.25 m lateral spacing | Retains the intended visual flattening and prevents an endpoint-only pass. |
| Full-width height span | `≤0.30 m` | Retains the local-width envelope. |
| Centerline source-height deviation | `≤2.0 m` | The authorized fixed profile smoothing already differs from source by about 1.374 m near the target. Retain the former `≤0.10 m` result as a reported historical comparison, not a hard gate for this smoothed candidate. |
| Absolute candidate longitudinal grade | `≤10%` throughout stations 140–155 m | A finite display constraint for the smoothed profile; it does not claim surveyed road grade. Report source and candidate signed-grade profiles and changes. Retain the former `≤2` percentage-point grade-change result as a historical comparison, not a hard gate for this candidate. |

Keep the existing complete-building contact/footing limits, source-preservation rules, road drape and shared-surface coherence requirements, topology validity, deterministic ownership, walk clearance, and no-bridge/tunnel grading rules. Check every complete footprint that intersects deformation, including `osm:way:208684847`; do not select buildings by centroid or conceal displaced footings. Any changed candidate-local limit beyond this table requires a new coordinator decision; do not widen the table automatically to pass a result.

The specific rationale and evidence for the 6.5 m candidate-local cap are recorded in [limit decision 1](artifacts/Teignmouth-corridor-prototype/continuation-1/limit-decision-1.md). No other limit changed.

## Fresh bounded attempt budget

Counters start at zero in `docs/milestones/artifacts/Teignmouth-corridor-prototype/continuation-1/attempt-ledger.json`; the previous diagnostic, builds, correction, and reviews stay recorded under the original issue paths.

- Luna initial implementation, then up to four completed Luna correction cycles. A correction cycle is one completed Luna correction submitted for Sol review. Stop sooner when the issue passes or no safe, concrete fix remains.
- If an actionable finding remains after all four Luna correction cycles have been reviewed, allow one Sol 6.1 correction. A separate Sol session reviews that correction. Failure after this correction ends with `NEEDS USER DECISION`.
- Up to three cause-specific diagnostics, each with a 120-second limit. No parameter sweep. Reuse compatible hash-bound evidence; diagnostics and re-reading do not count as correction cycles.
- At most one full candidate build per implementation submission, each with a 180-second wall-time limit, plus one independent deterministic confirmation build for the final passing candidate: seven total builds maximum (initial + four Luna corrections + one Sol correction + confirmation).
- No arbitrary memory cap. The 84 × 82 m registered treatment domain, fixed recipe, bounded run count and wall-time limits bound this experiment. Measure actual peak memory, CPU/GPU buffers, vertex/triangle counts, payload bytes, and load time. Do not silently increase domain, recipe, or run counts.

If the same substantive failure survives one Luna correction, obtain bounded Sol diagnosis before the next implementation dispatch. Do not use Sol to implement before the fourth Luna correction has been independently reviewed. Stop before browser integration for a failed candidate-local or retained global limit, invalid or uncovered geometry, unresolved ownership, complete-building failure, changed protected bytes, domain expansion, timeout, or incoherent fallback.

## Implementation and evidence

Create new continuation-specific files, preserving original prototype and correction files:

- `pipeline/torquay_pipeline/teignmouth_corridor_continuation.py`
- `pipeline/scripts/build_teignmouth_corridor_continuation.py`
- `pipeline/tests/test_teignmouth_corridor_continuation.py`
- `config/road-surface-teignmouth-corridor-continuation.json`
- If and only if all offline gates pass: isolated DEV prototype under `src/prototypes/teignmouthCorridor/`, dedicated Vite/Playwright configs and ignored candidate data under `data/generated/teignmouth-corridor-continuation/`.

Write fresh, non-overwriting evidence only under `docs/milestones/artifacts/Teignmouth-corridor-prototype/continuation-1/`. Persist chart and candidate buffers on failure as well as success, outside runtime-serving paths. Record first and maximum earthwork witnesses; validate actual Float32 geometry, upward/nondegenerate faces, coverage, exact source perimeter/heights, source-plane reconstruction outside influence, complete overlay extrema, road ownership/drape within 1 mm, complete building contact, and shared terrain/road/walk samples with 1.70 ±0.05 m eye clearance.

Before any candidate build, hash the source/config/code inputs and protected packages/evidence; repeat afterward. Keep raw-data hashing scope explicit. Run focused synthetic tests for bent roads, continuity, ownership, boundaries, strict thresholds, overlay extrema, building footprints, malformed assets and fallback; then applicable Python/Ruff/TypeScript/Vitest/build checks. Browser work follows only after offline numeric/topology/provenance gates pass. Use isolated port 4213 and capture same-camera source/candidate screenshots at the registered original and close-oblique poses plus a recorded overhead pose, at 1440 × 960, DPR 1, FOV 54°. Inspect and hash every capture; record browser console/network, camera matrices, runtime and memory observations. Do not touch port 5173 or the product Vite/default/share route.

## Sol planning disposition

Sol's bounded continuation plan and limit rationale are recorded in [the continuation plan](artifacts/Teignmouth-corridor-prototype/continuation-1/sol-plan.md). No implementation, build, test, profile, or browser run is authorized by this specification before the Luna implementation dispatch and attempt ledger are recorded.
