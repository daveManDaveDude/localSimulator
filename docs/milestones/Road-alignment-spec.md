# Road-alignment investigation

Status: accepted scope for one focused diagnostic issue, 21 October 2026. This is not TVW-016. Investigate the named current 2 km road candidates in the user's screenshots; do not change road rendering or geographic assets without demonstrating a defect and documenting its narrow correction first.

## Evidence and limits

Read-only planning inspected AGENTS.md, the canonical project plan, the coordinator checkpoint, road extraction/tessellation, terrain interpolation, renderer and active release `616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a`. The package uses 1,001 by 1,001 terrain samples at 2 m spacing from EA 1 m DTM, OSM roads dated 16 October 2026, configured estimated widths, and a 0.05 m surface offset. The pinned coordinate operation reports 2 m accuracy with the preferred OSTN15 grid unavailable; this is a limitation, not a measured offset.

The renderer already samples every road vertex from TerrainGrid and checks terrain-triangle containment and a 1 mm centroid drape tolerance. An independent read-only double-precision scan of all 416,298 vehicular and 47,439 path faces found maximum centroid residuals of 6.53e-13 m and 3.19e-13 m respectively, with no residual above 1 mm. This is package analysis, not browser verification.

Candidate profiles below use the package terrain and intervals no longer than 5 m. Longitudinal grades use successive centerline samples; cross grades use opposite samples at plus/minus half the configured width at interval midpoints. Grades are absolute percentages. These describe terrain beneath estimated ribbons, not surveyed carriageway grades. Signed elevation change follows stored way direction.

| OSM way / source name      | Length m | End minus start m | Long grade median / max % | Cross grade median / max % |
| -------------------------- | -------: | ----------------: | ------------------------: | -------------------------: |
| 22975541 / Teignmouth Road |  566.082 |           -20.469 |              4.44 / 13.61 |               1.69 / 22.98 |
| 22976771 / Teignmouth Road |  523.248 |            -9.912 |               1.91 / 4.09 |                1.12 / 7.39 |
| 24806641 / Teignmouth Road |   40.310 |            -1.975 |               4.81 / 5.57 |                1.17 / 3.41 |
| 30480035 / Teignmouth Road |  733.466 |           +15.347 |              4.68 / 13.33 |               1.65 / 13.70 |
| 78455395 / Teignmouth Road |  232.352 |            -7.620 |              3.16 / 32.36 |              10.85 / 82.95 |
| 78455388 / Pennys Hill     |  145.870 |           -10.571 |              7.17 / 15.43 |              18.95 / 48.26 |
| 30482119 / Arthington      |   59.158 |            -0.889 |               1.24 / 4.63 |                1.71 / 3.89 |
| 30482121 / Arthington      |    5.966 |            -0.093 |               1.56 / 2.23 |                1.70 / 1.82 |

At the sampled maximum crossfall station on Pennys Hill (approximately local X -244.518, Z -58.794), the 7 m ribbon spans 3.378 m of package height change. The existing independent bilinear sampler reads 3.4259 m from the original 1 m EA raster at the same opposite offsets. Teignmouth way/78455395 near X -141.545, Z -93.777 spans 4.977 m across 6 m in the package and 4.9069 m in the source. These are computed stations, not user-specified positions. Reproduce and retain full coordinates in the diagnostic output.

The evidence supports investigating estimated-width ground draping across steep adjacent terrain, with moderate confidence locally. Near-ground perspective may explain the apparent enormous road-colored areas, but camera pose is missing. Horizontal centerline error, a coordinate-operation error and engineered road elevation remain unproven. Do not infer the exact screenshot segment from a visible road label alone. The source spelling is `Pennys Hill`.

## Scope and concrete files

Implement repeatable diagnostics and bounded browser reproduction only:

- Add `pipeline/torquay_pipeline/road_alignment.py` for diagnostic calculations using existing coordinate/terrain contracts, and `pipeline/tests/test_road_alignment.py` for independent controls.
- Add `scripts/assess-road-alignment.py` as a read-only driver. Interface: `--output-dir docs/milestones/artifacts/Road-alignment`. Bind output to active release and input hashes; never publish/regenerate assets.
- Extend `tests/e2e/alignment-evidence.spec.ts` with one separately titled current-2km diagnostic test. Preserve the historical TVW-012 test and its output names; select only the new test in the dedicated profile.
- Add only `playwright.road-alignment.config.ts`, necessary because existing active configs run production cleanup tests, while the existing pose setter is DEV-only. Use isolated Vite development port 4212, `reuseExistingServer: false`, one worker, retries zero, 240-second test timeout, and `testMatch: 'alignment-evidence.spec.ts'` plus `grep: /Road-alignment current 2km/`.
- Reuse `src/app/alignmentQaCamera.ts`, its existing tests, and existing telemetry. Do not add another camera hook or production mutable camera API.
- Add `docs/milestones/Road-alignment.md` and new evidence under `docs/milestones/artifacts/Road-alignment/` and `docs/milestones/screenshots/Road-alignment/`.

The existing alignment E2E already clicks Start, sets a DEV-only pose, verifies telemetry and captures one oblique scene per historical 1 km context at approximately 35 m above camera-local terrain, pitch -35 degrees. It does not capture paired overhead/near-ground views at these current 2 km candidates. That is the gap this issue addresses; do not run the historical test and overwrite its accepted evidence.

## Numerical and source comparison

Use named ways above, plus Cricketfield Road ways 23595196, 686711262 and 689028452. Arthington is the mild crossfall control. Required output:

1. Resolve original PBF nodes, apply the existing pinned projection and local origin, and compare against clipped package centerlines. Report actual deltas and documented 1 mm quantization effects; do not introduce a geographic transform in browser code.
2. Compare configured-width source buffers with actual visible package surfaces, accounting for group unions, priority partitioning, clipping and junction overlap. Inspect whether a claimed enormous surface exists numerically.
3. Reproduce longitudinal and cross profiles in package terrain and original EA rasters. Retain sample coordinates, direction, station spacing, width, source methods, elevation ranges and signed endpoint changes. Separate observed terrain crossfall from any claim about real road engineering.
4. Independently inspect face containment and drape against the fixed terrain triangles, including Float32 renderer representation. Retain renderer tolerances; report collapsed/reoriented slivers without treating them as a large surface defect.
5. Produce registered reference/OSM overlay panels from existing April 2026 OS OpenMap-Local rasters using the existing comparison machinery where practical. Both files are present: `data/raw/comparison/os_openmap_local/selected-members/SX96NW.tif` (2,620,996 bytes) and `SX96SW.tif` (2,248,452 bytes). Bind actual hashes and existing source manifest. Generalized map symbols cannot establish surveyed kerb width or elevation.
6. Classify each context as demonstrated defect, source/representation limitation, or inconclusive, with evidence and uncertainty. Do not adopt grade thresholds, global translations, width changes, flattening/smoothing, transform replacement or finer-grid regeneration as fixes without source evidence.

## Required browser proof

Run one actual Chromium test titled `Road-alignment current 2km` using current `/`. Confirm real terrain/buildings/roads and active release, click Start and verify pointer lock before any capture. Derive camera targets/tangents from package centerlines and camera heights from its terrain; record actual poses and their derivation. Use the existing DEV-only setter without implying camera travel.

Capture an overhead and a low oblique view for each of three contexts: Pennys Hill/adjacent Teignmouth steep section, Cricketfield/Teignmouth junction, and Arthington control. Save six fresh PNGs under `docs/milestones/screenshots/Road-alignment/` and inspect them. Keep labels/ordinary product context useful for orientation. Record viewport/DPR, browser/version/GPU, camera pose, sampled ground, visible source names, release ID and errors. Require no relevant console/page/request errors and no remote runtime dependency. Label captures as candidate reproductions when exact correspondence to the user's camera cannot be established. A label alone is insufficient evidence of a match.

## Commands and acceptance

From repository root, run sequentially after implementation. The diagnostic script/profile below are new interfaces to implement, not claims of existing commands or executed results.

```powershell
pipeline\.venv\Scripts\python.exe scripts\assess-road-alignment.py --output-dir docs/milestones/artifacts/Road-alignment
pipeline\.venv\Scripts\python.exe -m pytest pipeline/tests/test_road_alignment.py pipeline/tests/test_roads.py pipeline/tests/test_coordinates.py pipeline/tests/test_terrain_export.py
pipeline\.venv\Scripts\python.exe -m ruff check pipeline scripts/assess-road-alignment.py
pipeline\.venv\Scripts\python.exe -m ruff format --check pipeline scripts/assess-road-alignment.py
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run format:check
npm.cmd test
npx.cmd playwright test --config=playwright.road-alignment.config.ts
npm.cmd run test:e2e:cleanup:real
npm.cmd run test:e2e:cleanup:share
git diff --check
```

Use meaningful synthetic controls: deliberately translated centerline, non-flat longitudinal slope, steep cross section, exact terrain-conforming triangle and a face crossing a terrain diagonal. Check inputs/read-only output guards before writes. Do not create tests that merely restate implementation calculations. Production real/share profiles build their corresponding variants and must run serially because they share `dist`.

Acceptance requires reproducible hash-bound numerical/source findings, six inspected after-Start screenshots, separate longitudinal/crossfall interpretation, independent controls and listed gates with actual results, unchanged protected hashes, and independent review. The handback must list commands/results, screenshots, known limitations and the smallest evidenced next correction, if any. No browser pass may be claimed without actual browser execution. If access fails, record the blocker and exact local reproduction steps.

## Preservation and unresolved limits

Preserve all raw/source/intermediate/generated GIS and package bytes, current ready/release/inventory, historical 1 km package, synthetic fixtures/fallback, AOI files and statuses, all previous reports/screenshots, immutable original plan, installer, recovery directories and unrelated working changes. Hash protected files before and after; include the input inventory and comparison in the handback. Leave port 5173 untouched. Keep TQ1 4HN and `selected_pending_coverage` / `not_checked`; no completeness or AOI approval is implied. Add no source acquisition, API, dependency or feature UI.

Exact screenshot-to-segment correspondence remains unresolved. Source names provide bounded candidate areas, so diagnostics can proceed without user intervention. Perspective, estimated width, source vintage, generalized map symbols, coordinate-operation accuracy and unknown engineered surfaces limit conclusions. Diagnostic completion does not itself authorize renderer/data corrections; a demonstrated defect needs a concrete narrow amendment before such edits.
