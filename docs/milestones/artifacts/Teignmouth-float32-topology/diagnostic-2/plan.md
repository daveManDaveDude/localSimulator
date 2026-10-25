# Diagnostic 2 plan: face 19669 source-overlay coverage

Issue: `Teignmouth-float32-topology-representation-1`. Status: **plan only; not executed**. One remaining diagnostic, maximum **120 seconds wall time**, with one invocation and no retry. Coordinator freezes inputs and reserves execution before dispatch. This document consumes no diagnostic/build/correction attempt.

## Question and frozen failure

Build 2 failed in the outside-influence source-plane overlay at `teignmouth_float32_candidate.py:973`, calling the unchanged `affine_surface_overlay_extrema`. The recorded face is **19669**, full face area **0.020639419555664062 m²**, expected clipped area **1.1028883815799223e-12 m²**, accumulated covered area **0**. Existing code skips each intersection whose area is `<=1e-12 m²` before both coverage accumulation and extrema evaluation. It then compares the aggregate coverage residual with `max(1e-12, expected_area*1e-10)`.

Determine whether individually discarded positive-area fragments collectively cover this clip, or whether there is a real indexed source-partition gap/overlap or an operation-order/clipping arithmetic mismatch. The first explanation is a hypothesis, not an accepted diagnosis. The failed candidate stays NO-GO; diagnostic observations cannot accept it or change the filter/tolerance.

## Exact inputs to freeze

Bind SHA-256 and byte lengths before execution for:

- `build-2/input-manifest.json`, `build-2/run-1/build-report.json`, `supervisor-report.json`, `candidate-failure.json`, `gate-state.json`, `serialization-stage.json`, and existing preservation records under this issue.
- Actual saved `build-2/run-1/serialized-local-positions.xyz.f32`, `serialized-world-positions.xyz.f64`, `serialized-indices.u32`, `serialized-candidate-y.f32` and `serialized-source-y.f32`. The serialized triangles and decoded world positions, not construction coordinates, define face 19669. Include `construction-world-xz.f64` only as a labelled secondary comparison.
- Saved `chart-stations.f64`, `chart-points.xz.f64`, `chart-fields.station-lateral.f64`, `chart-indices.u32` and `chart-stage.json`, plus exact fixed origin/config.
- Frozen `teignmouth_float32_candidate.py`, `road_surface_float32_frame.py`, `road_surface_topology.py`, relevant imported pure helpers, new diagnostic script if prepared, current spec/limit decision and an immutable pre-run ledger snapshot. Bind installed Python/NumPy/Shapely/GEOS identities and the exact repository interpreter.
- The original release heightfield/manifest/inventory/readiness identities already recorded by build 2. Read only the heightfield nodes needed for intersecting source triangles, using the unchanged grid contract and source IDs. Hash the bound heightfield without loading/rebuilding the whole release; no buildings, roads or unrelated GIS reload is needed unless an exact clip cannot otherwise be reconstructed.

Reconstruct the precise `outside_geometry = box(*EXPECTED_BOUNDS).difference(corridor.influence)` used by the failing call. Prefer a saved exact geometry if one exists. Otherwise use the saved target centreline sections/source-break evidence to reproduce the same stations 140–155 line and unchanged Shapely 35 m buffer; retain default buffer discretization and operation order. Verify that there is no omitted source break inside that window. If saved data cannot establish the exact clip, stop with the missing-input requirement rather than inventing an equivalent region or reloading the full candidate pipeline.

## One face-only calculation

1. Decode face 19669's three indices and stored local XYZ bytes; reconstruct world XYZ through the fixed origin and verify against the saved world/Y buffers. Record vertex IDs, raw/decoded coordinates, candidate heights, face WKB/WKT, validity and area. Reproduce the reported expected clipped area and original filtered covered area before interpreting the failure; record any discrepancy explicitly.
2. Identify only original source cells intersecting the face's closed envelope, including boundary-touching neighbours, within the original index bounds. Reconstruct their unchanged source triangle geometry, IDs and heights in original row/column order. Record the complete queried triangle set and why no other source triangle can intersect this face. No full source index, graded mesh, candidate assembly or all-face scan.
3. For each source triangle, compute the **same ordered operations** as production: `face.intersection(source_triangle)` followed by `.intersection(outside_geometry)`. Retain every result, including empty, line/point and polygon components. Record source ID, WKB/WKT, validity, component/vertex counts, positive polygon area and whether the frozen `<=1e-12` filter would discard it. Do not alter that production filter or its inclusive comparison.
4. Report separately: production-order filtered accumulated area; unfiltered ordinary sum; `math.fsum` of all positive fragment areas; sum of discarded positive areas; union area of all positive fragments; summed-area minus union-area overlap; expected-clip minus union uncovered geometry/area; union minus expected-clip excess; and symmetric-difference geometry/area. Store actual geometries, not only rounded decimal areas.
5. Check the local source partition independently of the filter: expected clip minus union of queried source triangles, source-union excess where relevant, and positive-area pairwise source overlaps within the clip. Compare the single alternative association `face.intersection(outside_geometry).intersection(source_triangle)` with production ordering, using the same inputs and unchanged precision model. This single algebraic comparison diagnoses clipping arithmetic; it is not a tolerance/parameter sweep or an alternative acceptance method.
6. Evaluate candidate-minus-source plane extrema at **all polygon-fragment vertices**, including rings and discarded tiny fragments. Retain first/min/max signed/absolute witnesses, source IDs and coordinates. Separately label zero-area contact observations. Use the frozen plane definitions and actual stored candidate Y; stop on nonfinite/ill-conditioned planes. No source-height, earthwork, exact source-plane-zero or other criterion is relaxed.

## Classification and evidence

- **Consistent with per-fragment discard:** positive fragments are individually filtered, their unfiltered union/sum explains the expected clip, and no source-partition gap/overlap or material clipping-order mismatch explains the residual. Report raw residuals and the unchanged existing tolerance comparison; do not call near-equality an exact partition proof.
- **Partition gap/overlap:** retain explicit uncovered/excess/overlap geometry and source IDs; distinguish an incomplete queried set from an actual source-index partition defect.
- **Clipping arithmetic mismatch:** equivalent operation ordering or source-union comparison yields inconsistent clipped geometry/area; retain both constructions and residuals without selecting whichever passes.
- **Inconclusive:** insufficient exact inputs, failed reproduction, nonfinite/invalid geometry or deadline. State what remains unknown. No automatic follow-up run.

Write a fresh diagnostic execution leaf beneath `diagnostic-2/` (for example `diagnostic-2/run-1/`), keeping this plan and frozen manifest in its parent. Only the runner creates the absent execution leaf. Persist per-source fragment records/geometries and a final report incrementally, including partial results on error/timeout. Verify all frozen input hashes before and after, recording checked count/mismatches and the explicit source-read scope. A post-stop inventory alone is not a before/after preservation pass.

Use exactly `pipeline/.venv/Scripts/python.exe`. Invoke the one-shot external supervisor with:

```powershell
pipeline/.venv/Scripts/python.exe -B pipeline/scripts/run_teignmouth_overlay_face_diagnostic.py
```

Bind the supervisor path/hash in the diagnostic manifest. It creates durable `diagnostic-2/invocation.json` before launch, verifies the frozen manifest, then creates the diagnostic runner process suspended and assigns it to a Win32 Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` before resuming it. If job creation/configuration/assignment fails, fail closed before numerical execution. The supervisor owns one 120-second total deadline, reserves time for bounded post-stop preservation hashing, and closes the Job Object on timeout so numerical descendants are terminated. It records child exit, chosen outer exit, deadline/termination state, and pre/post hashes in the parent invocation record; it mirrors that record into `run-1/external-supervisor.json` only when the runner created `run-1`. It never writes the worker's `report.json`. The runner remains the only creator of the absent execution leaf.

Record interpreter/environment, actual elapsed wall time, peak working set if available, logical result, actual worker exit, runner exit and separately observed outer-command exit. Telemetry failure must not erase the primary result or preservation evidence. Coordinator consumes diagnostic 2 once after any invocation; this is not another implementation build.

Stop on mismatched inputs, inability to reproduce the exact face/clip/source set, invalid/nonfinite arithmetic, missing source nodes, timeout or any proposed source/domain/origin/recipe/guard/limit change. Preserve all build-2 and predecessor evidence. No code edits, tolerance change, repair, parameter sweep, full build, product integration, browser or screenshot follows from this plan. A diagnosis may support a separately reviewed bounded correction proposal; it is not permission to implement one.

## Addendum: exact target-source extraction

Because the saved buffers lack exact clip provenance, the diagnostic may scan the manifest-bound original `roads/roads.json` with the standard-library `JSONDecoder`, walking the features array one feature at a time to extract only OSM way **78455395, part 0**. Do not retain the full payload object or construct unrelated road geometry. Verify the payload hash and source identity first; use the exact bound helper/config and original operation order to reconstruct the stations 140–155 centreline, default Shapely **35 m buffer**, and outside-influence clip. Do not call the full candidate loader or assemble a mesh. Source-heightfield reads remain memory-mapped and limited to the needed local nodes. If the reconstructed face/clip fails to reproduce the recorded area and filtered-coverage failure, stop as inconclusive; no substitute geometry or tolerance change is authorized. This addendum prepares no script and executes no diagnostic.
