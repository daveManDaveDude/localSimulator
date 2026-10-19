# M8 overview/minimap: offline MapLibre geographic overview

**Status:** Accepted by the coordinator on 2026-10-19; implementation is authorized for this issue only.

**Issue identity:** M8 overview/minimap. Do not assign TVW-016. The latest user instruction separately authorizes this one M8 slice after TVW-015 acceptance. TVW-016 and later remain unauthorized.

## Authority and accepted interpretation

Canonical `docs/project-plan.md` section 10/M8 names "Street labels and a MapLibre overview/minimap". TVW-015 completed street labels; this issue completes the bounded overview portion. Apply sections 11, 13 and 14 for tests, quality gates and handback, plus current AGENTS.md. M6 and M7 prerequisites are accepted.

The original source is absent from the workspace root but remains at `docs/Torquay_JS_Virtual_World_PoC_Codex_Plan.md`. Preserve it unchanged. Its known SHA-256 is `144C9C704EA1C10FA2D503DBA3233B089528585BE7D36B7B94164D28BA40D571`.

Coordinator decisions accepted for this specification:

- Use MapLibre GL JS 6.15.0, with local data and no external map service.
- Deliver a fixed, north-up geographic overview of the selected candidate AOI geometry, loaded road centerlines and loaded building footprints.
- Do not implement a live camera marker, camera following, terrain raster, terrain shading, pan/zoom/rotation, routing or click-to-teleport.
- Synthetic worlds remain fully usable and show a truthful geographic-overview-unavailable state. Do not assign fictional local worlds real-world coordinates.

Update current authorization/status records during implementation to reflect this scoped instruction. Do not mark all M8 options or the whole PoC complete.

## Preserve and non-goals

Preserve synthetic default, M0, existing real viewer routes, navigation speeds/modes, optional road/building visibility, street labels, source attribution, missing-data recovery and development-only QA-hook boundaries.

Keep the TQ1 4HN centroid, 1,000 m candidate AOI and `selected_pending_coverage` / `not_checked` status unchanged. Mapped counts and this overview do not establish completeness, independent alignment or AOI approval/freezing.

Do not acquire geographic data, enable PROJ networking/grid downloads, edit existing source/render packages, change their contracts, add API keys/services, deploy, export GLB, add unrelated stretch features or change historical evidence. Preserve the coordinator checkpoint change and user-owned installer.

## Existing state and dependency decision

Planning inspected HEAD `fc0930c`, AGENTS/checkpoint, canonical M8, TVW-015 spec/handback, UI integration and typed terrain/road/building contracts. The real packages already contain validated local XZ geometry. They do not provide geographic road/building geometry suitable for direct MapLibre ingestion.

Personally checked installed versions: Three 0.186.1, Vite 8.3.4, TypeScript 6.0.3, Vitest 5.0.5, Playwright 1.64.1, ESLint 10.13.0 and Prettier 3.9.10. MapLibre is not installed.

Add exactly pinned `maplibre-gl` 6.15.0 and update the npm lockfile. Registry metadata reports BSD-3-Clause, Node >=16.14/npm >=8.1, and 28,785,416 bytes unpacked. That distribution size is not the browser bundle size. The project's stricter supported Node range remains unchanged. No additional application/Python dependency is expected; existing pyproj and Shapely suffice.

Load MapLibre and its bundled CSS lazily on the first eligible explicit activation. Do not eagerly load it for synthetic startup. Record actual added production JS/CSS/worker bytes and first overview load time; no arbitrary FPS threshold applies. MapLibre is the explicitly accepted mapping dependency, not permission to add other mapping frameworks.

## Architecture

### Separate derived overview package

Add an offline Python exporter/validator/publisher. Existing local render packages remain byte-identical. The new derivative is necessary because all application geographic transformations must stay in tested Python.

Proposed outputs:

```text
data/generated/overview/manifest.json
data/generated/overview/features.geojson
public/worlds/torquay-poc-001/overview/manifest.json
public/worlds/torquay-poc-001/overview/features.geojson
```

Keep both locations ignored; existing ignored parent directories already cover them. Do not commit real generated features. The synthetic share build must exclude the whole real-world parent, including this derivative.

Proposed CLI contract, with paths resolved from the repository rather than the caller's working directory:

- `build-overview`: default terrain source is the published local terrain directory; default included layers are `aoi,roads,buildings`; default output is `data/generated/overview`.
- Accept explicit `--terrain-dir`, `--roads-dir`, `--buildings-dir`, `--layers` and `--output-dir` arguments. `--layers aoi` supports a terrain-only overview. AOI is always required; requested missing/invalid optional packages fail contextually rather than being silently omitted.
- `validate-overview`: default generated package; accept `--package-dir` and the same input directory options. Recompute the expected derivative from its declared input layers and compare geometry, metadata and integrity descriptors.
- `publish-overview`: validate the generated package and copy byte-identical files to the ignored public overview directory. Accept `--package-dir` and `--output-dir`.

CLI errors use nonzero exit codes and identify the relevant file/stage. No command downloads or replaces inputs.

### Python conversion and integrity

1. Validate the existing terrain manifest/heightfield identity, candidate config and approved AOI ring. Use existing standalone building/road validators for each requested layer, including package QA/source/terrain bindings.
2. Recover BNG positions from validated local coordinates using `E = originE + x`, `N = originN - z`.
3. Reuse `coordinates.py`'s pinned inverse EPSG:1314 + EPSG:19916 operation with explicit XY order, networking disabled and no grid downloads.
4. Reuse the recorded candidate WGS84 AOI ring verbatim from `docs/aoi-selection.geojson`; do not generate another candidate boundary.
5. Export RFC 7946 longitude/latitude GeoJSON: one AOI Polygon, road MultiLineStrings preserving separate clipped parts, building MultiPolygons preserving components and holes. Do not join disconnected roads, repair/simplify geometry or infer absent features.
6. Preserve stable source feature IDs and only minimal properties: layer role, source identity, road name/highway/display group or building identity. Do not publish all raw tags, measured-height claims or new source-derived attributes.
7. Validate finite coordinates, supported geometry types, closed rings, RFC winding, matching counts, unique namespaced IDs and containment within the declared candidate with documented numerical tolerance. Preserve holes even after winding normalization.
8. Serialize deterministically with stable feature/property order, fixed whitespace/newline policy and no runtime timestamp in content identity. Preserve AOI coordinates verbatim; document a fixed precision policy for transformed feature coordinates. Demonstrate <=0.02 m numerical inverse round-trip consistency after serialization; this is not absolute geodetic accuracy.

Manifest version 1 must include:

- World ID, non-synthetic designation, exact candidate statuses and included layer list.
- AOI config/approved ring identity, BNG bounds, local origin and WGS84 map fit bounds/centre derived in Python.
- Terrain manifest and heightfield SHA/byte identities; for included optional layers, manifest/payload/QA SHA/byte identities and source extract identity/vintage.
- Complete pinned operation metadata, stated 2 m accuracy and unavailable preferred OSTN15 grid caveat. Do not call the fallback survey-accurate or equate round-trip agreement to accuracy.
- Output relative path, exact length, SHA-256 and feature/coordinate counts by role.
- Generator/format versions, precision policy, licences, source URLs and required attribution tied to actual displayed sources.

Initial bounds: manifest <=128 KiB; GeoJSON <=8 MiB; <=10,000 features and <=250,000 positions. Reject limits contextually; never truncate to fit. Confirm retained inputs fit during implementation.

Generation/publication must use staging and replacement with rollback. Refuse source/output nesting or paths that could overwrite terrain, road, building or raw inputs. A failed validation/write/publication must preserve previous good output byte-for-byte. Publish the manifest last and require browser checksum validation so mixed generations cannot be displayed.

### Browser loader and map

Add typed unknown-safe manifest/GeoJSON validation and a bounded, abortable same-origin loader. Enforce size while streaming, including absent/incorrect Content-Length; check exact length/SHA before parsing/plotting. Reject unsafe paths, duplicate IDs, malformed/nonfinite coordinates, unsupported geometries and contradictory role/count/status/provenance fields with contextual messages.

Compare overview terrain identity against the currently loaded terrain. Before showing each optional layer, compare its declared identities against the actually loaded road/building package. An unmatched optional layer is not displayed; report that the overview must be rebuilt if identities conflict. Do not fetch another road/building payload or perform BNG/WGS84 transforms in TypeScript. Numerical source-to-geographic recomputation belongs to the Python validator.

Map configuration:

- Inline style version 8, explicit Mercator projection, fixed bearing/pitch 0, inline validated GeoJSON and background/fill/line layers only.
- No remote style URL, vector/raster tiles, sprites, glyphs, symbol/font layers, geolocation, terrain DEM, logo service or telemetry endpoint.
- Use locally bundled MapLibre JS/CSS/workers. Document expected same-origin and blob worker resources; reject unexpected external request URLs.
- Initialize with the package's genuine geographic centre/fit bounds and `fitBounds` with zero animation. No hardcoded invented geographic centre.
- Display AOI outline plus included optional layers only when their corresponding main-viewer layers are loaded and visible. Clearly report absent/not-included layers; do not automatically load them to populate the overview.
- Fixed extent and disabled map gestures protect existing pointer-lock navigation. Provide a north cue, metre scale, legend and clear "Local package overview; no live camera position" description.
- Keep EA terrain identity/source context separate from OSM feature attribution. Do not imply the overview draws an EA raster or OS comparison imagery. Show OSM/Geofabrik credit when their features are visible, and retain MapLibre licence notices.

MapLibre's internal rendering projection of valid geographic input is expected. Application-specific local/BNG/WGS84 conversion remains exclusively in Python.

### UI and lifecycle

Provide an initially closed accessible `Overview` control with accurate expanded state and a labelled panel. Use a responsive, bounded panel that does not obscure primary controls or attribution; include it in street-label panel avoidance.

Real-world activation lazily imports MapLibre and loads the derivative. Give distinct loading, ready, missing, corrupt, identity-mismatch and WebGL-unavailable states, with retry and close actions. Optional overview failure must never blank, unload or disable the main viewer.

In either synthetic world, show a truthful unavailable explanation without instantiating a geographic map, loading a real overview or assigning synthetic geometry longitude/latitude. Returning from real to synthetic immediately removes real map content.

Use attempt tokens/abort handling for world replacement and overlapping loads. Closing/replacing/disposal must call `map.remove()`, detach handlers/ResizeObserver, abort requests and release workers/context resources owned by the map. A failed or stale initialization cannot attach a map later. Reopening must create no duplicate map/canvas/control nodes. Resize calls `map.resize()` and re-fits the fixed package bounds.

## Concrete files

- `pipeline/torquay_pipeline/overview_export.py`, `overview_publish.py`, existing `cli.py` and focused tests.
- `src/geo/overviewSchema.ts`, `src/app/overviewLoader.ts`, `src/app/createOverview.ts` and focused tests.
- `src/app/createApp.ts`, `src/style.css`, `src/app/createRoadLabels.ts` for integration/panel avoidance.
- `package.json`, `package-lock.json`; Vite configuration only if local worker/chunk handling requires it.
- Isolated overview production/share Playwright configs and tests; include new configs in strict typecheck.
- `docs/overview-asset-contract.md`, README, this spec's handback/evidence, canonical authorization/status and coordinator checkpoint updates.

Do not edit existing source/render schemas or packages. New tests/screenshots write to ignored isolated outputs by default; explicitly promote selected new overview evidence only.

## Tests and proof

Python offline fixtures must cover local XZ signs in every quadrant, known inverse coordinates, explicit axis order, rectangular bounds, disconnected roads, concavity/holes/multipolygons, winding/closure, nonfinite/bool/malformed data, exact AOI/input identity, changed origin, stale optional package, altered geometry with refreshed hashes, requested missing inputs, deterministic generation and publication failure rollback. Record the pinned operation/no-network/no-grid caveat. Test CLI nonzero errors and output path safety.

TypeScript tests must cover unknown input/schema errors, size/stream cancellation, checksum/length, safe paths, terrain/optional identity mismatches, malformed GeoJSON, stale/cancelled loads and failure recovery. Browser integration must prove disposal, resize, repeated toggle/world replacement and existing street-label collision avoidance.

Actual production browser acceptance:

1. Open the real overview and visibly inspect genuine AOI/road/building geographic data against the Python derivative. Confirm source feature IDs/counts and representative positions, not merely a nonblank canvas.
2. Verify north-up fixed framing, metre scale, legend, attribution, pending AOI and no-live-position wording.
3. Verify road/building hide/show and missing/not-included/identity-mismatch behavior without changing main-viewer package state.
4. Verify resize/backing dimensions, close/reopen, repeated world switches and cancellation without duplicate maps/listeners or stale real features.
5. Verify pointer lock, movement, mode switching and street labels remain usable and avoid the overview panel.
6. Exercise missing/corrupt derivative, failed lazy import/map initialization or WebGL-unavailable recovery. Main terrain and synthetic recovery remain functional.
7. Test clean share/synthetic mode: no real overview request, truthful unavailable state, synthetic world usable, no real geometry/package in share output.
8. Observe network/worker activity and assert no external requests, styles, tiles, fonts or services. No unexpected page/console errors.

Save fresh production real-overview and synthetic-unavailable screenshots showing readable status/credits. Record commit, input/output identities, browser/version, software/hardware renderer, viewport/DPR, added bundle bytes and first activation time. Performance measurements are descriptive; do not infer hardware performance from SwiftShader. This is not a new independent map-alignment check or coverage proof.

## Commands and acceptance gates

From repository root, after exact dependency addition:

```powershell
npm.cmd ci
npm.cmd ls --depth=0
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run format:check
npm.cmd test
npm.cmd run build
npm.cmd run build:share
```

From `pipeline` (proposed CLI names/options are requirements above):

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest tests
.\.venv\Scripts\ruff.exe check torquay_pipeline tests
.\.venv\Scripts\ruff.exe format --check torquay_pipeline tests
.\.venv\Scripts\python.exe -m torquay_pipeline.cli build-overview
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-overview
.\.venv\Scripts\python.exe -m torquay_pipeline.cli publish-overview
```

Repeat generation in a separate ignored output directory and compare manifest/GeoJSON hashes. Verify publication bytes match the generated package and existing terrain/building/road identities remain unchanged.

Run existing profiles against the correct build, sequentially; never run a real profile after a share build without rebuilding normal production output:

```powershell
npm.cmd run test:e2e:tvw014:full
npm.cmd run build
npm.cmd run test:e2e:tvw014:real
npm.cmd run test:e2e:tvw015:real
npm.cmd run build:share
npm.cmd run test:e2e:tvw014:share
npm.cmd run test:e2e:tvw015:share
```

Add focused `test:e2e:overview:real` and `test:e2e:overview:share` scripts that build the appropriate mode and use unique ports, no server reuse, retries disabled and isolated outputs. Do not stop the user's development server. Preserve historical captures and record all failed runs; retries do not repair a failed acceptance result.

All required gates and actual browser checks must pass before independent review can return PASS. Confirm original plan/source hashes, AOI status, installer and unrelated coordinator changes remain preserved. No source acquisition is required.

## Handback and limits

Record changed files, dependency/lockfile and bundle impact, exact commands/results, two deterministic package identities, source/accuracy/licence metadata, actual screenshots/network observations, cleanup/recovery checks, failed runs and remaining limits.

State explicitly: fixed MapLibre geographic overview, no live camera marker or terrain raster; unavailable for unreferenced synthetic worlds; no new alignment/completeness claim; AOI pending; no TVW-016+ authorization. Other M8 items remain outstanding.

## Official references checked during planning

- [MapLibre Map API](https://maplibre.org/maplibre-gl-js/docs/API/classes/Map/) for construction, fitBounds, resize, source/layer management and remove.
- [GeoJSONSource API](https://maplibre.org/maplibre-gl-js/docs/API/classes/GeoJSONSource/) for local source data.
- [MapLibre style sources](https://maplibre.org/maplibre-style-spec/sources/) and [style specification](https://maplibre.org/maplibre-style-spec/) for inline styles and valid geographic GeoJSON inputs.
- [Pinned package metadata](https://registry.npmjs.org/maplibre-gl/6.15.0) for version, engines, licence and published distribution metadata.

Planning performed read-only repository/API/registry inspection. No package installation, geographic download, export, test or browser verification was performed during specification. The coordinator explicitly accepted the fixed-overview/synthetic-unavailable design boundary; no essential source or user choice blocks this slice.
