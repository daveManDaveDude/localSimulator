# Road-surface treatment preview

Status: coordinator-accepted specification, 22 October 2026. One focused user-authorized visual treatment issue; not TVW-016. Implement as a labelled comparison preview only; retain the accepted default route and all source/package bytes. Use Luna implementation and separate independent Sol review under the Torquay protocol.

## Objective and evidence

Provide a generic local preview of flatter road cross sections on steep ground, with coherent terrain contact. Preserve source alignment and the accepted product route while comparing the approximation against the existing rendering. No surveyed pavement elevations or measured road edges are available.

The accepted Road-alignment investigation established that source/package centerlines agree after quantization and existing road triangles follow the current terrain. The user now authorizes a visual treatment rather than a source-coordinate repair. New map URLs identify WGS84 points `50.4783696,-3.5383277` and `50.4777531,-3.5375891` (latitude, longitude). The coordinator's pinned-operation conversion gives local X/Z approximately `[-163.041,-60.841]` and `[-112.057,8.793]`. These are context points, not exact road-surface controls: the first is approximately 6.895 m from Pennys Hill way 78455388; the second is approximately 2.510 m from Lymington Road way 1363931058 and 44.021 m from Parkfield Road way 30480989. Reproduce those measurements in Python before using them as camera targets. Retain the 2 m reported transform accuracy and missing preferred OSTN15 grid caveat.

Parkfield way 30480989 is a 501.035 m residential source line with configured 6 m width, not a measured carriageway polygon. The coordinator's existing-method profile reports 4.448% median and 42.710% maximum terrain crossfall at station 409.261 m; the latter spans 2.563 m across the estimated width. The original EA raster maximum is 41.494% / 2.490 m. Retain full station/coordinate records when reproducing; these values concern terrain beneath the ribbon, not road engineering. Other mandatory comparison candidates are Pennys Hill 78455388, adjacent Teignmouth 78455395, Lymington 1363931058 and mild Arthington 30482119/30482121. Cricketfield/Teignmouth provides a junction check. Do not edit the accepted Road-alignment report or reuse its evidence filenames.

## Options and selected scope

| Option                                                                                | Assessment                                                                                                                                                             |
| ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Adaptively narrow the road until it fits the terrain                                  | Avoids grade separation but can turn configured streets into narrow strips and does not fix longitudinal bumps. No kerb evidence supports the resulting widths. Defer. |
| Cap crossfall at a chosen percentage                                                  | Requires a display policy without local design evidence. A numerical cap must not be presented as measured or engineering-correct. Defer arbitrary nonzero caps.       |
| Flatten only the road mesh                                                            | Can float above ground or sink into the hillside; skirts alone do not remove terrain protruding through the pavement. Reject as the standalone treatment.              |
| Flatten road cross sections in a separate visual terrain grid and blend the shoulders | Selected coherent prototype: terrain, road, footing and navigation share one surface. It changes displayed local ground and remains an explicit approximation.         |

Use the user's authorized flattening fallback as a **zero imposed crossfall target**, anchored to original terrain sampled along existing OSM centerlines. Preserve longitudinal terrain variation; do not promise a flat longitudinal road or remove genuine hills. This avoids inventing an engineering crossfall cap. The 2 m mesh will approximate the target rather than realize perfectly flat continuous cross sections.

Deliver an internal comparison route `/?roadSurface=preview` for the current 2 km scene. `/` retains the accepted source-draped rendering in this issue; activation as the sole product default requires review of the concrete preview and a recorded coordinator scope decision. No product layer/world/debug controls are added. The preview visibly states `Road-surface preview · approximate road grading; surrounding ground adjusted.` Sources explains that EA/OSM supply the inputs and the changed pavement/shoulders are a visual model. The pending notice remains exact. Historical and synthetic routes ignore the preview parameter and request no derivative.

## Offline algorithm and derivative

Keep all coordinate transforms, centerline projection and grading calculations in tested Python. Read only the accepted release `616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a`. Generate a separate local derivative at `public/worlds/torquay-road-surface-preview/`; never replace or change current/historical releases, manifests, readiness or inventories.

1. Read eligible published ground-assumed **vehicular** centerlines and configured widths. Preserve all X/Z geometry, AOI and source elevations. Do not infer heights for bridges/tunnels or add excluded features. Paths remain displayed and drape to the shared display ground if nearby grading changes it; report that consequence.
2. For each existing 2 m grid vertex inside an eligible ribbon/transition neighborhood, find its nearest eligible centerline projection using a spatial index. Compute target local Y from the **unchanged baseline terrain sampler at that projection**. The ideal lateral target has zero imposed crossfall; its longitudinal elevation follows the original sampled centerline. Use original terrain for all anchor heights, never recursively grade from already changed values.
3. Inside the configured half-width use the target; outside it blend back to original terrain with a continuous, zero-end-slope smoothstep weight. Initial shoulder transition distance is `max(configured full width, 2 × grid spacing)` beyond the ribbon edge: an explicit visual configuration intended to span multiple mesh cells, not a measured earthwork width. Include the exact policy/values in provenance and QA. Leave all vertices beyond the influence region byte-identical to baseline.
4. Use one deterministic nearest-projection selection over the whole eligible network, with stable feature/part/segment tie-breaking. Audit junctions, parallel carriageways and nearby roads at different elevations; do not average disconnected road heights or silently connect them. The grid mesh remains continuous, but nearest-road influence can introduce unwanted ridges. Where that occurs, report the affected connected local region and retain original ground there rather than inventing engineered vertical separation. Document all local exclusions and their effect on the objective. Do not hide inability to improve a mandatory candidate by excluding it.
5. Produce one Float32 visual heightfield with the original grid dimensions, spacing, extent, origin and fixed triangle convention. Use that same display grid for terrain triangles, roads (+0.05 m), building bases/roof-base policy, street anchors, spawn/bounds and walking. Do not create a separate flattened road sampler over an unchanged visible terrain mesh. No physical simulation or road collision is added.
6. Source-package validation continues against the immutable original manifest/binary; display grading is a separately validated derivative. The derivative contract binds original ready/release/inventory, terrain and road hashes, algorithm version, parameters, derivative hash/length and interpretation. Do not pass the derivative off as an EA heightfield or change the source identity to make existing loaders accept altered bytes.

Use a bounded output allowlist with pre-write guards against source/ancestor/descendant overlap, symlinks/junctions and unowned entries. Owned temporary writes must not delete unrelated backup paths. Verify protected input hashes before and after. Build twice from identical inputs and require byte-identical derivative and deterministic QA; timestamps belong in a separate execution record if needed.

## Browser integration and failure behavior

Load and validate the derivative before constructing the preview world; install one display grid before asynchronous road/building attachment begins. Preserve the original manifest and integrity objects for existing package validators. An optional typed display-grid input to world assembly is preferable to mutating loaded source arrays or rebuilding road/terrain objects independently after loading. Validate dimensions, finite values, checksums, source identities and the supported algorithm version. Clear stale preview state on cancellation, retry, world replacement and disposal.

Missing/corrupt/stale derivative must give a truthful `Road-surface preview unavailable; showing source terrain.` state and show the existing coherent source scene. Do not leave a partially graded scene. Ordinary `/`, historical and synthetic navigation must not depend on derivative presence. Keep the existing share allowlist unchanged so it excludes real preview assets; verify clean-clone synthetic fallback. Preview data is local/generated and ignored by Git; commit code, contracts, bounded evidence and handback only.

## Files

- New: `config/road-surface-preview.json`, `pipeline/torquay_pipeline/road_surface.py`, `pipeline/tests/test_road_surface.py`, `scripts/build-road-surface-preview.py`.
- New typed contract/loader and tests: `src/geo/roadSurfaceSchema.ts`, `src/geo/roadSurfaceSchema.test.ts`, `src/app/roadSurfaceLoader.ts`, `src/app/roadSurfaceLoader.test.ts`.
- Narrow integration: `src/scene/createHeightfieldWorld.ts` and its tests, `src/app/createApp.ts`, `src/style.css` only if needed for the preview notice. Existing terrain/road/building algorithms remain source-compatible; do not weaken their validation or drape guarantees.
- New browser proof: `tests/e2e/road-surface.spec.ts`, `playwright.road-surface.config.ts`, isolated port 4213, one worker, retries zero. Reuse the existing DEV-only alignment camera hook; do not duplicate it.
- Documentation: `docs/asset-contract.md`, `docs/milestones/Road-surface-treatment.md`, artifacts/screenshots in dedicated `Road-surface-treatment/` directories, `.gitignore` for the new generated derivative directory. Coordinator updates the checkpoint. Preserve all earlier reports and screenshots.

If implementation needs additional product architecture or package formats beyond these changes, return a concrete amendment before expanding the issue.

## Acceptance and evidence

1. Meaningful Python controls: flat terrain remains unchanged; a longitudinal hill stays longitudinally graded; a planar lateral slope receives the zero-crossfall target; shoulders return continuously to baseline; unchanged outer vertices are exact; perpendicular junction, curved road, parallel/disconnected roads at different heights, AOI edge and ambiguous influence cases are deterministic and finite. Exercise output guards, checksum identity and reproducibility.
2. Report original versus preview **same-station** longitudinal/cross profiles at maximum 5 m spacing, original 1 m DTM comparison, changed-vertex counts/area, maximum/percentile cut and fill, transition gradients, centerline vertical deviations, building-base changes and all excluded regions. Keep source/published XZ and configured widths unchanged. At Parkfield and Pennys/adjacent Teignmouth steep candidates, median and maximum sampled crossfall must be lower than baseline, with actual reductions reported; no claim of surveyed or design-correct grade. Do not smooth away longitudinal hills to obtain that result. If the fixed 2 m representation cannot achieve useful visible improvement without serious new banks/ridges, record failure and return to planning rather than flattening a larger district.
3. Exact shared-grid terrain/road centroid agreement and Float32 tolerance remain valid. Steady-state walk eye clearance is 1.7 m +/-0.05 m above **displayed** terrain in both treated corridors and transition zones. Building walls remain attached; local footing changes are disclosed. No new terrain holes, cracks, buried roads, floating road ribbons or conspicuous transition walls in the required views.
4. Actual after-Start Chromium comparison: baseline and preview overhead/low-oblique pairs at Parkfield's measured severe station, Pennys/Teignmouth and Arthington control (12 PNGs). Add a fixed view spanning the Parkfield/Lymington context and a Cricketfield junction pair if the primary views do not cover them. Derive points/tangents in Python and camera Y from each displayed local grid; explicitly keep local/orthometric datums distinct. Retain labels, attribution, pending/approximation notices, camera pose, baseline/derivative hashes, viewport/GPU/runtime errors, local request list and achieved clearance. Inspect all images; no exact match to the user's Google camera is claimed.
5. Browser assertions cover preview activation, source default unchanged, shared road/building/walk sampling, reset/resize, missing/corrupt/stale derivative fallback, cancellation/retry, historical/synthetic routes without derivative requests, and share exclusion. No relevant runtime errors or external requests. Measure preview load time and geometry/frame behavior descriptively; add no arbitrary FPS promise.
6. Independent Sol review verifies every mandatory result. A useful preview does not establish correct road engineering, AOI coverage or default activation approval. Handback states what worked, what remains a visual approximation and whether the concrete preview merits activation.

## Verification commands

Proposed interfaces below are to be implemented. Run from the repository root, sequentially when outputs/build roots overlap; preserve port 5173. Two derivative builds must each save an input/output-hash execution record in the dedicated evidence directory.

```powershell
pipeline\.venv\Scripts\python.exe scripts/build-road-surface-preview.py --config config/road-surface-preview.json
pipeline\.venv\Scripts\python.exe scripts/build-road-surface-preview.py --config config/road-surface-preview.json
$env:PYTHONPATH = (Resolve-Path pipeline).Path
pipeline\.venv\Scripts\python.exe -m pytest pipeline/tests/test_road_surface.py pipeline/tests/test_road_alignment.py pipeline/tests/test_roads.py pipeline/tests/test_terrain_export.py
pipeline\.venv\Scripts\python.exe -m ruff check pipeline scripts/build-road-surface-preview.py
pipeline\.venv\Scripts\python.exe -m ruff format --check pipeline scripts/build-road-surface-preview.py
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run format:check
npm.cmd test
npx.cmd vitest run --exclude "sites/**"
npx.cmd playwright test --config=playwright.road-surface.config.ts
npm.cmd run test:e2e:cleanup:real
npm.cmd run test:e2e:cleanup:share
git diff --check
```

The known default Vitest collection conflict with unrelated untracked `sites/` must remain disclosed if present; the scoped command is an explicit repository-only result, not a claim that the default command passed. Unlike the prior diagnostic-only fix, this issue changes runtime integration, so real/share browser regression evidence must be refreshed in isolated evidence locations without overwriting accepted cleanup artifacts. Record failures accurately and resolve relevant regressions before PASS. Run the full Python suite if shared export/coordinate modules change.

## Preservation and risks

Hash and preserve original source GIS, intermediate/generated inputs, current and historical browser packages, readiness/inventory, original supplied plan, accepted Road-alignment and prior evidence, installer/recovery files, `sites/`, and unrelated working changes. Preserve TQ1 4HN, current AOI dimensions and `selected_pending_coverage` / `not_checked`. No new source acquisition, Google imagery extraction/redistribution, paid service, dependency or API. User-provided Google references are location/context evidence only.

The treatment changes visible terrain around roads, can alter building footing/roof baselines and nearby path ground, can expose nearest-road conflicts at junctions, and cannot recover actual cuttings, walls, cambers or engineered road elevations. A 2 m grid limits the surface approximation. These risks are why the output is a separately labelled preview with source fallback and retained baseline comparisons. This issue authorizes no coordinate correction, surveyed-road claim, physical driving system, lateral building/road relocation or AOI approval.
