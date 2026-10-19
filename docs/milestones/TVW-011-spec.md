# TVW-011 implementation specification

**Status:** Accepted by the coordinator for TVW-011 implementation on 2026-10-19 after independent Sol 6.1 medium planning. Specification only at acceptance; no road import, renderer, test run or browser verification is claimed here.

## Authority and source requirements

The user's separate “please continue” after TVW-010 authorizes **TVW-011 only**: offline OSM road extraction and a terrain-draped ribbon renderer. Keep this one focused issue, with pipeline and renderer implemented sequentially. TVW-012's separate comparison/issue-report task, walk mode, traffic, routing, realistic junction engineering and subsequent issues remain unauthorized.

Read against the immutable source plan `docs/Torquay_JS_Virtual_World_PoC_Codex_Plan.md`: §3.2 acquisition, §3.3 roads (lines 133–140), §3.4 provenance (142–154), §§4–6 common AOI/axes/contracts, §9 repository layout, §10 M5 (547–566), §§11/13/14 tests/gates/handback, §15 TVW-011/012 and dependencies (759–764), and ADR-002/003/004/005 (§16, 773–776). Canonical equivalents are `docs/project-plan.md` §§3.3–6, §10 M5 (553–572), §§11/13/14, §15 (765–770), and §16. Original §4/ADR-006's 500 m size was explicitly superseded by the recorded user-approved 1,000 m revision; do not edit the original.

**Accepted boundary reconciliation:** M5's combined exit gate requires three independent map comparisons, while §15 splits the formal three-spot comparison and issue report into TVW-012. TVW-011 will provide three existing landmark debug locations and record only bounded, source-backed placement observations where available. This does not start TVW-012 or satisfy/claim the combined M5 exit gate. Any unavailable comparison remains explicitly unverified; never invent road IDs, junctions or successful checks. The coordinator accepts this split for this TVW-011-only authorization.

## Baseline, inspected inputs and gaps

- Main HEAD at inspection: `a66f5c6`; preserve the coordinator's modified checkpoint and user-owned untracked `TMOG-Task-Manager-1.0.1-Setup.exe`. Keep the running port 5173 server. AGENTS/canonical still contain historical “TVW-011 unauthorized” wording; the current checkpoint correctly records the newer user authorization. Coordinator should update current status text without rewriting history.
- Both complete plan files, AGENTS, checkpoint, TVW-009 handback, TVW-010 spec/handback, asset contract, source manifest, configs, CLI, loaders, terrain sampler, building publisher and renderer integration were inspected. TVW-009's accepted brief is in the checkpoint/contracts; no standalone TVW-009-spec file exists.
- Retain TQ1 4HN centroid `[-3.536013, 50.477853]`, BNG centre `[291108.9018176432, 65353.48350844931]`, and exact `[west,south,east,north]` bounds `[290608.9018176432,64853.48350844931,291608.9018176432,65853.48350844931]`. Status stays `selected_pending_coverage` / `not_checked`; mapped road counts cannot approve completeness or freeze the AOI.
- Local ignored `data/raw/osm/devon-261016.osm.pbf` exists. Personally executed existing `inspect-building-source`: manifest verification passed, 58,254,938 bytes; SHA-256 `52942b39636e1cb002e5d78a004668996cb469ee9c9e9b9b93049c66b9ac2cd5`; MD5 `c9c2018b331d8affd6b7be6464444bc5`; PBF header timestamp `2026-10-16T20:21:21Z`, sequence `4932`, generator `osmium/1.16.0`. No road-named package exists under raw/intermediate/generated/public assets. Reuse this dated extract; no download/API replacement is needed.
- Existing real terrain and building packages are present. Terrain is the validated 501 × 501, 2 m grid; heightfield byte count 1,004,004 and SHA-256 `1d0a9f27d9e150a422541b3ba2bd175f05d18c5ef58f8d8f4a4f586694c48183`. Bind to its actual manifest/origin/elevation and hash rather than copying constants into independent runtime transforms.
- Missing: road policy/config, way extraction/QA, typed road assets, publisher, bounded browser loader, ribbon geometry, independent visibility/retry state, landmark debug selection and road-specific evidence/tests. Reuse existing safe package and lifecycle patterns, not building-height semantics.

## Pipeline and extraction policy

1. Add strict `config/roads.torquay.json`, read alongside the existing AOI, QA GeoJSON and real terrain manifest. Use existing pinned explicit-XY Python coordinate operation, PROJ network off, no grid acquisition. Record its complete definition, stated 2 m accuracy and unavailable preferred OSTN15 grid caveat. Round-trip agreement is not absolute alignment accuracy.
2. Reuse the verified PBF source namespace and header/hash checks. Preserve exact publisher landing/file/checksum URLs, acquisition timestamp, extract timestamp and ODbL/Geofabrik attribution already recorded. Add road derivation metadata separately; do not alter EA/building source facts or pretend to acquire a new snapshot. Retain source tags and node IDs in an ignored intermediate.
3. Resolve full ordered way node geometry before spatial filtering, using PyOsmium location support. Filter in a 50 m BNG acquisition buffer; exact final centreline/ribbon exports are clipped to the unchanged AOI. A line crossing the AOI with both endpoints outside must survive. Do not use endpoint-only selection or a bounding-box approximation as final clipping.
4. Include the following line `highway` values, retaining original class/name/ref/access/surface/oneway/junction/width/lanes/bridge/tunnel/layer/covered tags. Widths below are **full-width visual estimates**, never measured kerbs or verified OSM widths. Retain raw width/lanes without using them in this first policy. Distinguish vehicular streets from paths in counts and materials; access tags are information, not permission or a routing claim.

| Classes                                                                | Estimated full width (m) |
| ---------------------------------------------------------------------- | -----------------------: |
| motorway, trunk                                                        |                       12 |
| motorway_link, trunk_link, primary_link, secondary_link, tertiary_link |                        6 |
| primary                                                                |                       10 |
| secondary                                                              |                        8 |
| tertiary                                                               |                        7 |
| unclassified, residential                                              |                        6 |
| living_street, road                                                    |                        5 |
| service                                                                |                      3.5 |
| track, pedestrian                                                      |                        3 |
| cycleway                                                               |                        2 |
| bridleway                                                              |                      2.5 |
| footway, path                                                          |                      1.5 |

Paths are included as useful neighbourhood cues, separately labelled; they are not vehicle roads. Exclude and count `steps` (no stair model), construction/proposed/abandoned/disused/raceway/bus_guideway/escape, unknown classes, point features, and `area=yes`/`area:highway` surfaces. Closed highway lines such as roundabouts remain eligible; closure alone does not make an area. Exclusion counts must reconcile, including unknown classes, rather than silently disappearing.

5. Render ground-assumed ways only. Skip and report a whole source way if bridge/tunnel has any value other than absent or explicit `no`, if `covered` is non-`no`, or if layer is nonzero/malformed/multivalue. Accept absent layer or a strictly parsed integer zero. Empty/ambiguous values are unsupported, not confirmation of ground level. Retain flags/IDs/reasons; never turn layer numbers into metres or drape a bridge/tunnel on the DTM. Missing tags imply an explicit visual assumption, not proof. Preserve existing source way splits at bridge approaches.
6. Missing/invalid node locations, nonfinite transforms and fewer than two distinct vertices reject the affected way with contextual ID/node evidence; never join across a missing node. Remove consecutive duplicate points only. Preserve ordered source geometry and closed loops; handle clipping-generated parts deterministically. Do not connect unrelated source ways or infer road connectivity from crossing coordinates. Report unusually long source segments; finite exact clipping and terrain subdivision must prevent a giant rendered triangle even for a legitimate long straight source segment.
7. Deduplicate source IDs, then exact coincident/reversed normalized lines with matching effective class/width/ground policy; retain contributing IDs and deterministic winner. Preserve distinct parallel carriageways. Flag partial overlaps and conflicting classes; do not claim to repair network topology. Stable part IDs use source way ID and deterministic part ordering; canonical duplicate keys must also catch redundant collinear points. Source orientation/oneway metadata must not be changed by the duplicate-key normalization.

## Ribbon geometry and terrain contract

Perform projection, clipping and width buffering in Python (ADR-002). Export local XZ metres only: `x=E-originE`, `z=originN-N`; north is negative Z. No browser lon/lat transformation. Quantize normalized centreline coordinates to 1 mm, then revalidate length, shape and bounds. Use full width/2 for Shapely buffers, **flat caps and bevel joins**; do not allow unbounded miter spikes. Exact AOI clipping applies to final ribbon edges, not just centrelines. Reject invalid derived geometry rather than silently applying `buffer(0)`/make-valid.

Use these concrete surface preparation steps to avoid centreline-only draping and z-fighting at junctions:

1. Union valid buffered polygons within each display group; partition overlapping groups with deterministic priority vehicular > cycleway > pedestrian/path. Preserve all source features/IDs separately from these display polygons. This is a simple surface union, not an engineered junction or a connected routing graph. Same-level intersections are contiguous without duplicate coplanar triangles. Road geometry is not subtracted from buildings; record visible source conflicts instead of inventing repairs.
2. Intersect display polygons with the existing terrain's individual fixed triangles `(NW,SW,NE)` and `(NE,SW,SE)` across the `u+v=1` diagonal. Use bounded grid ranges/spatial indexing, not every polygon against every cell. Constrained triangulation of each resulting polygon, including holes, produces a small set of triangles each entirely inside one terrain triangle. Existing Shapely/GEOS supports this without a new dependency. Keep source holes/roundabout islands; unconstrained Delaunay alone is insufficient.
3. Export indexed local XZ render vertices/triangles plus their terrain cell/triangle identity. Keep intersection precision (up to 9 decimal metre places); do not snap those intersections back to 1 mm and move them across terrain diagonals. Canonical vertex/triangle ordering and upward winding are deterministic. Reject degenerate, duplicate, nonfinite, outside-AOI, self-overlapping or invalid-index output. Verify union area and absence of interior triangle overlap within a declared numerical tolerance.
4. Browser validates all indices/limits/cell ownership before allocation, samples each vertex with the **existing exact TerrainGrid sampler**, and sets `y=sampleHeight(x,z)+0.05 m`. Do not use bilinear heights, an analytic plane, vertex-index rounding, a constant road elevation or polygon offset as a substitute for draping. Every triangle lies on one sampler plane, so its full width/interior follows terrain. Require sampled vertex and barycentric interior deviation from terrain+offset ≤0.001 m after Float32 conversion; contextual null/nonfinite/Float32-collapse failure leaves terrain usable.
5. Build shared indexed BufferGeometry batches for subdued vehicular/cycle/path materials; compute finite upward normals/bounds. No walls, collision, labels requiring a new library, lane markings or street furniture. Optional wireframe is a debug view. Dispose owned geometry/materials on partial failure, stale load, replacement and teardown.

The pre-tessellated XZ surface is an extension to the plan's centreline JSON contract, not a new geographic source or a stored measured road elevation. Document it; the centreline/name/class/width/non-ground fields remain inspectable. If actual measured size makes this approach impractical, report counts/bytes first and obtain a bounded spec revision rather than silently reducing accuracy or adding a geometry dependency.

## Package, validation and publication

Create ignored `data/generated/roads/torquay-poc-001/{manifest.json,roads.json,qa.json}`. `roads.json` contains unique source-way records and clipped parts, retained relevant tags, effective estimated width/method, exclusion/ground assumptions, and display batches with XZ vertices/indices/cell references. Preserve skipped feature reasons in QA; no fake rendered bridge. Do not package raw PBF or full Devon tags.

Use a separate versioned road manifest/schema with exact supported literals. Include world/package ID, type `osm-road-ribbons`, local axes/units, exact BNG and WGS84 AOI ring from the accepted GeoJSON, pending statuses, terrain manifest identity/origin/elevation/grid/heightfield descriptors, complete pinned operation metadata, source PBF size/hash/header/vintage/acquisition/licence links, effective inclusion/width/ground/clip/buffer/quantization/triangulation/offset policies, generator/version, package-local asset paths and actual byte counts/SHA-256, source/part/batch/triangle counts and QA summary.

Python authoritative package validation and TS unknown-safe validation must reject null/bools masquerading as numbers, nonfinite values, unsafe paths, wrong literals, mismatched AOI/terrain/policy/source/QA identity, duplicate IDs/geometry, inconsistent counts, out-of-bounds or malformed line/ring/triangle data and oversized allocations. Recompute policy-derived values and counts rather than trusting rehashed metadata. Validate QA against the actual feature/exclusion totals. Test fully rehashed adversarial inputs. Initial hard limits: manifest 64 KiB, QA 2 MiB, payload 32 MiB, 100,000 source-way records, 1,000,000 render vertices and 1,000,000 render triangles; enforce both byte and structural limits, with actual package sizes reported. Increasing a cap requires measured justification.

Publish byte-for-byte only to ignored `public/worlds/torquay-poc-001/roads/`, after validating against the local terrain package. Reuse or factor the tested staged-directory/rollback pattern. Source/destination must be separate and non-nested; guard symlinks/ancestor replacement. Revalidation failure or injected write/rename failure preserves prior roads, terrain, buildings and input bytes. Never replace the real-world parent. Repeated import and publication must produce identical artifact bytes/hashes; timestamps come from recorded inputs, not wall-clock execution. `build:share` must still exclude the whole real parent, including roads.

## Browser behavior

Add an independent opt-in `roads=1` only for `world=torquay-poc-001`; retain synthetic `/`, M0, terrain-only and existing buildings routes unchanged. `?world=torquay-poc-001&buildings=1&roads=1` displays both optional layers. Do not request a road package at synthetic/default startup. No external GIS/API requests, downloads or new authentication/backend.

Road loader uses same-origin package-local paths, status/JSON/schema/hash/length stages, actual streamed byte limits independent of Content-Length, cancellation, and attempt guards. Verify all package/terrain/QA identity before Three allocation. Missing/corrupt roads show actionable command/retry feedback, hide-roads/continue-terrain and return-synthetic options without breaking already loaded terrain/buildings. Missing local sources on a clean clone leave synthetic fully functional; do not fabricate a real package. Synthetic unit/E2E fixtures remain visibly fictional and do not borrow real-source labels.

Visible UI: loading/loaded/error/hidden state; unique mapped way and clipped-part counts (distinct from surface batches), street/path and skipped bridge/tunnel/ambiguous counts; visibility and optional wireframe; estimated-width notice; OSM extract timestamp, OSM copyright/ODbL link and Geofabrik credit; retained EA attribution; pending AOI/completeness caveat. Hide/show must preserve correct metadata/counts and avoid duplicate load/geometry. Add accessible landmark selector/debug marker and selected supplied road name/ID if available. Preserve controls, Escape, reset, resize, grid/north cue, FPS and ground-height HUD.

## Existing three landmark contexts

These manually selected contexts already have source-backed TVW-009 objects/captures. Coordinates are **building representative points, not invented road junctions**. Retain this distinction and derive marker XZ using the existing local feature or tested Python transform. During extraction identify adjacent actual highway way/node IDs and record source-derived comparison points before claiming road alignment.

| Context                                                      | Existing OSM building way | Existing representative lon/lat            | Prior capture           |
| ------------------------------------------------------------ | ------------------------- | ------------------------------------------ | ----------------------- |
| NE, Second Avenue                                            | 208552436                 | `[-3.5332476398607215,50.480951244856804]` | `TVW-009-object-ne.png` |
| NW, Baron Road / Lindfield Close                             | 193285347                 | `[-3.54291445782617,50.48047580317829]`    | `TVW-009-object-nw.png` |
| SW, Mount Stuart Hospital / St Vincent's Road / Chapel Court | 181620525                 | `[-3.5417691183482414,50.475127986993755]` | `TVW-009-object-sw.png` |

Prior captures are under `docs/milestones/screenshots/`; re-open them and actual map contexts before making current claims. Local PBF observations establish that features exist; the independent OSM map is a qualitative placement check, not an independent survey/source database or completeness proof. Save the road feature IDs, relevant node/closest-line point, expected local XZ, camera/marker, observable alignment and limitations. Do not infer a junction from an arbitrary line crossing. If a named road/landmark is absent or non-ground in the dated extract, record that fact and leave comparison pending; changing landmarks requires another real existing feature, not invented coordinates.

## Concrete files and sequence

1. Update current authorization/status docs with coordinator; implement config and extraction using `pipeline/torquay_pipeline/road_config.py`, `roads.py`, `road_geometry.py`; add `road_export.py`, `road_preview.py`, `road_publish.py`, CLI subcommands. Reuse source/coordinate checks; factor generic OSM verification only if compatibility is covered. Do not duplicate a second coordinate operation.
2. Add pipeline fixture/test modules for config/PBF extraction/geometry/export/preview/publisher. Generate and validate real package; inspect north-up road QA map with terrain/AOI/landmark overlays, metre axes/scale/legend, attribution and exclusion summary. Capture actual counts without assuming them beforehand.
3. Add `src/geo/roadSchema.ts`, `src/geo/roadGeometry.ts`, `src/app/roadLoader.ts`, `src/scene/createRoads.ts` and focused tests. Reuse TerrainGrid and bounded-stream helpers where appropriate without weakening building tests.
4. Integrate `src/app/createApp.ts`, scene ownership/disposal, HUD/help/styles and route parsing; add `tests/geo/road*.test.ts`, loader/lifecycle tests and `tests/e2e/roads.spec.ts`. Extend existing test/config coverage rather than inventing a second runner.
5. Update `docs/asset-contract.md`, `docs/data-sources.md`, README, canonical issue status, AGENTS and coordinator-owned checkpoint; create `docs/milestones/TVW-011.md`, tracked QA summary/map and new screenshot evidence. Source/raw/intermediate/generated/published geodata remain ignored. Preserve old screenshots, source plan, AOI and dependency pins; no road assets inside synthetic fixtures.

## Required tests, commands and proof

Offline Python fixtures must use tiny fictional PBFs through the actual PyOsmium path: cross-AOI lines, repeated/missing nodes, one-node/closed-way/area cases, included/excluded classes, tags with malformed booleans/layers, bridge/tunnel/covered variants, loop/roundabout, reverse/collinear duplicates, partial overlaps and separate parallel ways. Test empty results, contextual corrupt/missing source errors, config-only reproducibility, four-quadrant origin signs, clip edges, finite geometry, acute hairpin joins, holes, intersection priority, exact terrain-cell/diagonal subdivision, union area, deterministic ordering and atomic rollback/source preservation.

TS tests cover unknown/malformed/rehashed package and QA inputs, real terrain binding, missing/wrong Content-Length streamed caps/cancel, cell/index/byte limits before allocation, flat/slope/ridge and cross-slope ribbons, diagonal/edge/null terrain samples, finite Float32 normals/bounds, area/offset and interior samples, duplicates/stale requests/repeated visibility/disposal. Test rendering geometry against the actual sampler, not a mocked flat result. Test a valid fictional roads package offline even when no local real package is available; never count that as actual-source evidence.

Implement these CLI interfaces with existing analogous flags/defaults (`--config`, `--source-manifest`, optional `--source`, `--aoi-config`, `--aoi-geojson`, `--terrain-package`, `--package`, and import `--output`):

```powershell
cd C:\vibe\localSimulator\pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli inspect-road-source
.\.venv\Scripts\python.exe -m torquay_pipeline.cli import-roads
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-roads
.\.venv\Scripts\python.exe -m torquay_pipeline.cli preview-roads
.\.venv\Scripts\python.exe -m torquay_pipeline.cli publish-roads
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pip check
cd C:\vibe\localSimulator
npm.cmd ls --depth=0
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run format:check
npm.cmd test
npm.cmd run build
npm.cmd run build:share
npm.cmd run test:e2e -- --output test-results/tvw-011-implementation
git diff --check
```

The road subcommands above are proposed interfaces, not existing/passed commands. Repeat actual import into two separate ignored directories and compare payload/manifest/QA/intermediate/preview bytes; record hashes and verify publication/public/dist identity. Use separate normal/share build output directories or sequence builds so share's omission is not confused with a missing normal package. Use an isolated E2E server/output/config if a matching-port server is already active; never reuse stale 4173 output or stop the user's 5173 server. Preserve pre-existing tracked screenshots; report any runner side effects for coordinator cleanup.

Actual browser gates: existing M0/synthetic/terrain/buildings regressions plus real local roads, combined layers, counts/toggles/landmark marker/wireframe, movement/reset/resize, missing/corrupt manifest/payload/QA, streamed failure/retry, return to terrain/synthetic, no stale duplicate layers, no unexpected console/page/HTTP error on normal load and no external GIS requests. The actual-source test must execute here; an optional clean-clone skip alone is not proof.

After normal production build, run a separate preview, for example `npm.cmd run preview -- --host 127.0.0.1 --port 4188 --strictPort` (choose another free port if occupied). Personally inspect `/?world=torquay-poc-001&buildings=1&roads=1` and terrain-only/synthetic routes. Save and inspect `TVW-011-roads-overview.png`, `TVW-011-roads-ground.png`, and bounded landmark/map evidence under `docs/milestones/screenshots/`, using new filenames. Record browser/version, viewport/DPR/backing buffer, pose, renderer/GPU, sampled FPS/draw calls/triangles, asset bytes and observed road-terrain offset/alignment. Distinguish hardware rendering from SwiftShader and claims from personally observed runs; do not silently inherit TVW-010's 60 FPS. A real hardware sample is desirable; disclose inability and any regression. Preserve existing baseline hashes and user installer.

## Installed versions and official API evidence

Personally verified `npm.cmd ls --depth=0`: Three 0.186.1 / types 0.186.0, Vite 8.3.4, TypeScript 6.0.3, Vitest 5.0.5, Playwright 1.64.1, ESLint 10.13.0, TS-ESLint 8.71.2, Prettier 3.9.10; Node engine `^22.13.0 || ^24.0.0 || >=26.0.0`. Python 3.13.7: osmium 4.3.1, Shapely 2.2.0 / GEOS 3.14.1, pyproj 3.8.0, Rasterio 1.5.2, NumPy 2.5.4, Matplotlib 3.11.2, pytest 9.1.1, Ruff 0.17.1. Reuse these pins; no new package/service is required. Latest PyOsmium docs currently identify 4.3.2, so verify calls against installed 4.3.1 rather than upgrading from documentation alone.

Official sources opened during specification:

- [Geofabrik Devon publisher/download register](https://download.geofabrik.de/europe/united-kingdom/england/devon.html): dated source and publisher checksum; public PBF omits personal contributor metadata. Reuse exact recorded snapshot.
- [PyOsmium geometries](https://docs.osmcode.org/pyosmium/latest/user_manual/03-Working-with-Geometries/): ordered way locations, missing/invalid geometry handling and object lifetime.
- [OSM highway](https://wiki.openstreetmap.org/wiki/Key:highway), [bridge](https://wiki.openstreetmap.org/wiki/Key:bridge), [tunnel](https://wiki.openstreetmap.org/wiki/Key:tunnel), [layer](https://wiki.openstreetmap.org/wiki/Key:layer): class/tag semantics; layer is relative ordering, not an elevation measurement.
- [OSM copyright/ODbL](https://www.openstreetmap.org/copyright): visible contributor credit and licence link; keep derived layers separable and real assets out of share builds. Do not imply local derivation removes redistribution obligations.
- [Shapely buffer](https://shapely.readthedocs.io/en/stable/reference/shapely.buffer.html): explicit keyword cap/join policies; [constrained triangulation](https://shapely.readthedocs.io/en/stable/reference/shapely.constrained_delaunay_triangles.html): respects polygon boundaries, unlike unconstrained point triangulation. Installed 2.2.0/GEOS 3.14.1 supports the selected API.
- [Three BufferGeometry](https://threejs.org/docs/pages/BufferGeometry.html), [MeshStandardMaterial](https://threejs.org/docs/pages/MeshStandardMaterial.html), [Material](https://threejs.org/docs/pages/Material.html): indexed buffers, computed normals/bounds, wireframe and resource disposal; use installed r186 APIs. Small geometry elevation offset supplies draping clearance.

## Acceptance checklist and unresolved limits

- [x] Coordinator accepted this specification and recorded TVW-011-only authority/current status; no TVW-012 implementation or combined M5 PASS claim.
- [ ] Verified dated local PBF reused; no new acquisition, invented feature or unsupported source/height claim; raw/generated data ignored.
- [ ] Explicit class/width/non-ground policy, exact AOI clipping, identity/exclusion reconciliation, provenance/operation/terrain/QA binding and deterministic package/publication pass tests and actual-source checks.
- [ ] Rendered road surfaces follow the exact terrain across their entire width, including grid/diagonal crossings; no giant/NaN/duplicate/unsupported elevated ribbons; real counts and estimated widths visible.
- [ ] Optional roads and buildings coexist; synthetic default and clean-clone behavior, controls, error/retry and ownership cleanup remain intact; share build excludes all real assets.
- [ ] All stated quality gates actually run; screenshots personally inspected; three extant landmark candidates/feature identities prepared and any actual bounded map observations truthfully recorded. Formal TVW-012 comparison/issue report remains pending.
- [ ] Handback lists exact commands/results, artifact/source hashes, sizes/counts, browser/GPU/FPS evidence and limitations, exclusions/source conflicts, source-plan/installer/baseline preservation and next proposed issue requiring separate authorization.

No missing source blocks implementation here. Source tagging cannot prove ground level, estimated road width or completeness; missing/non-ground ways stay visible as exclusions. The exact PBF highway counts, adjacent road IDs at the three contexts and browser alignment are deliberately unknown until the implementation performs those checks. Original source-plan SHA remains `144C9C704EA1C10FA2D503DBA3233B089528585BE7D36B7B94164D28BA40D571`. Specification work has acquired no data and run no application tests/browser checks.
