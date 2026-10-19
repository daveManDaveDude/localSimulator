# Torquay Virtual World

A Windows-friendly browser proof of concept for a future real-data view of Torquay. The default viewer loads a checked-in synthetic Float32 heightfield and renders its terrain mesh, hill, ridge, grid and north cue. The prior M0 analytic scene remains available at `/?world=m0`. The **EA terrain** selector loads a locally generated 2 m Float32 heightfield from the verified Environment Agency DTM tiles when that ignored package exists in `public/worlds/torquay-poc-001/`. A separate explicit route can add the locally published OSM building layer to that terrain.

The synthetic heightfield, hill, ridge, analytic slope, blocks and their measurements are fictional; they are not Torquay measurements. The real terrain mode uses the actual Environment Agency DTM source tiles and displays their source attribution and Ordnance Survey Newlyn vertical reference. Its heights are stored relative to a deterministic center origin. The HUD links to the publisher catalogue and Open Government Licence v3.0. EA raster coverage and resampling passed for the candidate square. Optional OSM building and road layers load from separately generated local packages with contributor credit and an ODbL link. TVW-012 records three qualitative road-placement passes against an independent OS OpenMap–Local map. The overall AOI remains `selected_pending_coverage` / `not_checked`: mapped counts and three spot comparisons do not establish completeness, and broader feature-coverage checks remain outstanding. See [the TVW-012 report](docs/milestones/TVW-012.md).

## Requirements

- Windows 11 with PowerShell
- Node.js 22.13 or later within the 22.x line, 24.x, or 26.x and later
- npm, included with Node.js
- Python 3.12+ for the offline AOI and EA raster tools (Windows validation used Python 3.13.7)
- A recent desktop browser with WebGL support

## Start locally

On a clean clone, install the locked dependencies once from PowerShell:

```powershell
npm ci
```

Then start the viewer with one command from the repository folder:

```powershell
npm run dev
```

Open the local address printed by Vite. `npm ci` restores the exact dependencies in `package-lock.json`; the initial clean install needs access to the npm registry. Once installed, the application uses local files only and does not call a hosted service.

The refreshable project dashboard is at `/progress.html` on the same local server. It reads `public/project-progress.json`; update that snapshot as milestone handbacks change, then use **Refresh status** to load the latest project position and forecast. See [docs/project-dashboard.md](docs/project-dashboard.md) for the update fields and status rules.

Click **Start exploring** to enter pointer lock. Move the mouse to look. **W/S** and **A/D** move in the current navigation mode; **Shift** boosts speed. Both modes use 15 m/s normal speed and 41.25 m/s boosted speed. In **fly mode**, movement follows the full camera look direction and **Space/Ctrl** rise or descend. In **walk mode**, movement follows camera yaw, ignores vertical keys, and keeps the eye 1.7 m above the active terrain sample. Use the **Enter walk mode** button or **F** while pointer-locked; if you are flying above the terrain, the camera smoothly acquires walk height. Use **F** again to cancel acquisition. **R** restores the fly spawn, or resets to the sampled walk spawn while remaining in walk mode. **Esc** releases the pointer and pauses movement/acquisition; click the scene or the mode-appropriate **Resume** button to relock. The camera stays inside finite world bounds; the status pill signals when you reach an edge. Use **G** or the terrain-grid button to toggle grid and north cues; the wireframe button changes the terrain mesh display.

The live HUD reports the loaded world, source mode, grid dimensions, sampled ground height, camera position and bearing/pitch, lock state, speed, FPS and boundary state. A load error identifies the failing stage and offers retry and a link to the M0 analytic demo.

## Project commands

```powershell
npm run dev          # Start the local development server
npm run build        # Type-check and produce the static build in dist/
npm run preview      # Serve the production build locally
npm run typecheck    # Run strict TypeScript validation
npm run lint         # Run ESLint
npm run format:check # Check formatting with Prettier
npm run test         # Run movement, navigation, asset, terrain-grid, and mesh unit tests
npm run generate:synthetic-heightfield # Rebuild both deterministic synthetic fixture packages
npm run test:e2e:install # Download Playwright's Chromium browser (first time only)
npm run test:e2e     # Run real-browser synthetic, local GIS, and walk-mode regressions
```

The generator writes the original 3 × 3 loader fixture plus a separate 25 × 19, 2 m-spaced terrain demo. The latter contains a fictional base slope, Gaussian hill and narrow ridge, with little-endian Float32 samples and a SHA-256 in its manifest. `docs/asset-contract.md` documents both manifest variants, local-path and sampling contracts. The synthetic viewer loads the checked-in fixture; the EA mode loads only the generated local package and does not fetch geographic data from a service.

## TVW-012 independent road placement comparison

The completed TVW-012 report compares three registered road junctions against the April 2026 OS OpenMap–Local raster and the actual local 3D scene. It records qualitative PASS at Second Avenue / Main Avenue, Pencorse Road / Audley Avenue, and Teignmouth Road / Snowberry Close; the earlier St Vincent’s Road / Chapel Court candidate remains separately preserved as inconclusive. No numeric offset was measured. The combined M5 gate was accepted after independent review. This completes the road import/rendering and three-spot placement work, but it does not establish AOI completeness or approval. See [the report and screenshots](docs/milestones/TVW-012.md) and the exact source/member hashes in [the comparison source manifest](data/comparison-source-manifest.json).

The raw OS comparison archive is not tracked. Its public portal selection was the 349,405,146-byte April 2026 SX GeoTIFF package (SHA-256 `d9a01900c4dd5c26af50d6aed79f419a1957acf4167aedef97bb905ffcdff853`); only the verified `SX96NW.tif` and `SX96SW.tif` members are used. To restore it on a clean clone, create `data/raw/comparison/os_openmap_local/`, download the recorded `openmaplocal-2026-04-sx-geotiff.zip` from the URL in the manifest, then run `inspect-comparison-source`, `compare-alignment` and `validate-alignment-report` from `pipeline`. OS attribution is `Contains Ordnance Survey data © Crown copyright and database right 2026`; the product is under [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).

## AOI and EA DTM inspection

The Python pipeline is separate from the browser and uses no online transformation-grid downloads. The 2026-10-17 user-approved revision derives a 1,000 m × 1,000 m EPSG:27700 candidate from the configured TQ1 4HN WGS84 postcode centroid using pyproj with explicit longitude/latitude axis order. It keeps the previously verified WGS84 and BNG centre unchanged. The anchor is a postcode centroid, not a property or survey point. The candidate remains `selected_pending_coverage`; OSM building footprints and roads have been imported and QA-checked, and three road placement comparisons are complete. Their mapped counts and local placement checks do not prove complete feature coverage. OS building checks and broader OSM/OS feature-coverage checks remain outstanding, so the AOI is not frozen.

Create the isolated Python environment in PowerShell:

```powershell
py -3.13 -m venv pipeline\.venv
pipeline\.venv\Scripts\python.exe -m pip install -r pipeline\requirements.txt
```

Install the isolated, pinned Python dependencies and validate the source config or regenerate the projected selection, QA GeoJSON, and report from the repository root:

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-aoi --config ..\config\aoi.torquay.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli select-aoi --config ..\config\aoi.torquay.json --output-dir ..\docs
.\.venv\Scripts\python.exe -m pytest tests
.\.venv\Scripts\ruff.exe check torquay_pipeline tests
.\.venv\Scripts\ruff.exe format --check torquay_pipeline tests
Pop-Location
```

`config/aoi.torquay.json` is the editable input. Changing only its anchor coordinates and rerunning `select-aoi` refreshes the projected centre/bounds there and regenerates `docs/aoi-selection.json`, `docs/aoi-selection.geojson`, and `docs/aoi-selection.md`. Outputs are staged and each destination is atomically replaced. The GeoJSON uses RFC 7946 longitude/latitude coordinates, contains a closed counter-clockwise polygon and the anchor point, and has no legacy `crs` member. The transform operation, reported accuracy, listed grid availability and network-grid state are included in the machine-readable report. `docs/aoi-selection.md` records the anchor/map provenance and the still-pending coverage check.

### TVW-007 EA DTM check

The local inspection used two public Environment Agency LIDAR Composite DTM 1 m (2022 composite) tiles. Their exact portal download links, archive names, byte sizes, SHA-256 digests, extracted TIFF metadata and tile-level XML provenance are recorded in [data/source-manifest.json](data/source-manifest.json). The archives and extracted files belong under ignored `data/raw/ea_dtm/`; the tracked manifest does not contain raster data. Follow [docs/data-sources.md](docs/data-sources.md) to restore the exact files on a clean clone.

From PowerShell, after restoring the source files:

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli inspect-sources
.\.venv\Scripts\python.exe -m torquay_pipeline.cli preview-terrain
Pop-Location
```

`inspect-sources` verifies archive and raster hashes/metadata, then samples the source pixel containing each AOI-aligned 1 m cell center. It does not interpolate or fill missing cells. The measured report is `docs/milestones/artifacts/TVW-007-coverage.json`; its result is 1,000,000 valid cells out of 1,000,000, no uncovered, masked, NoData or nonfinite cells, and an EA DTM-only pass against the 1% threshold. The sample range is 29.529–98.171 m; the configured center sample is 47.620 m. At the TVW-007 handback, `coverage_status` remained `not_checked` pending later feature checks. TVW-009 added OSM building-footprint measurements, TVW-011 completed road import and rendering, and TVW-012 completed three qualitative road placement comparisons. Broader OSM/OS feature-coverage checks remain outstanding.

`preview-terrain` writes an actual north-up PNG from those measured samples at `docs/milestones/screenshots/TVW-007-ea-dtm-preview.png`. It shows the exact AOI border, BNG metre axes, 250 m scale bar, centre sample, measured elevation colorbar and Environment Agency attribution. This raster preview is a separate Python QA artifact; TVW-008 adds a locally generated browser heightfield without changing the synthetic default.

### TVW-008 local terrain package and viewer

After restoring the source archives and extracted rasters as described in `docs/data-sources.md`, build the local browser package from the `pipeline` folder:

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli build-terrain
Pop-Location
```

The builder verifies the source archive, TIFF and XML hashes, rechecks EA DTM coverage, bilinearly samples the 1 m area-pixel centers onto the exact 501 × 501, 2 m AOI vertex grid, and writes a center-relative little-endian Float32 field. It refuses missing positive-weight contributors, does not fill or extrapolate, and publishes the manifest last. QA and the actual-data north-up PNG are written to `docs/milestones/artifacts/TVW-008-qa.json` and `docs/milestones/screenshots/TVW-008-terrain-preview.png`.

The generated browser package at `public/worlds/torquay-poc-001/` is intentionally ignored by Git because it is derived from locally restored publisher data. On a clean clone the default synthetic viewer continues to work; the EA selector explains how to restore sources and rebuild the package. To open the real mode directly after building it, use `http://localhost:5173/?world=torquay-poc-001`. To return to the retained analytic demo, use `/?world=m0`. The real mode stays local to the Vite app and adds no network service. The EA cell-level result does not approve the broader candidate AOI; `coverage_status` remains `not_checked` pending broader OSM/OS feature-coverage checks and AOI review. Road import/rendering and three qualitative placement comparisons are complete; M2 remains incomplete.

### TVW-009 OSM building footprint import and QA

TVW-009 creates an offline OSM footprint package and placement/count QA. TVW-010 adds an optional browser renderer for that package on the EA terrain; it remains off unless explicitly requested. The source PBF, generated package/intermediate and published browser package are ignored by Git. See [docs/data-sources.md](docs/data-sources.md) for the exact dated Geofabrik extract, hashes, licence, attribution, and restoration steps, and [docs/building-asset-contract.md](docs/building-asset-contract.md) for the package shape and coordinate rules.

After restoring `data/raw/osm/devon-261016.osm.pbf`, run the pipeline from PowerShell:

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli inspect-building-source
.\.venv\Scripts\python.exe -m torquay_pipeline.cli import-buildings
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-buildings
.\.venv\Scripts\python.exe -m torquay_pipeline.cli preview-buildings
.\.venv\Scripts\python.exe -m torquay_pipeline.cli publish-buildings
Pop-Location
```

The importer verifies the exact PBF hash and header, assembles building areas before filtering, reads a 50 m buffer, clips geometry to the reviewed 1,000 m square, applies the documented height fallback, and writes a separate local package under `data/generated/buildings/torquay-poc-001/`. `import-buildings` also writes `docs/milestones/artifacts/TVW-009-buildings-qa.json`, `docs/milestones/screenshots/TVW-009-buildings-preview.png`, and an ignored raw-tag intermediate. The current measurement exported 1,000 footprints covering 172,969.138 m²; 998 use the configured 8 m visual default and 2 use `building:levels × 3 m`. None had a usable direct `height` tag. These counts describe mapped OSM data, not completeness or verified building heights. The OSM-specific placement check and current implementation status are recorded in [docs/milestones/TVW-009.md](docs/milestones/TVW-009.md).

### TVW-010 optional browser building layer

After restoring the exact source PBF and local EA terrain package and running the TVW-009 commands above, `publish-buildings` validates the source package and atomically copies its three byte-identical assets into the ignored Vite public tree. The default synthetic world and `/?world=m0` are unchanged; the EA terrain-only route is `/?world=torquay-poc-001`; the explicit building route is `/?world=torquay-poc-001&buildings=1`. The EA terrain HUD also has a **Load OSM buildings** control. The optional package never triggers a remote request. `npm run build:share` excludes the real terrain/building package.

The renderer preserves the package's local XZ positions and shows polygon roofs and terrain-following exterior/courtyard walls. A feature's flat roof is set to the maximum terrain sample under all its components, excluding hole interiors, plus its validated tagged or estimated height. This is a visual placement convention, not a measured roof or foundation height; wall bases are lowered by 0.02 m to avoid seams. The HUD reports the actual feature/component and height-method counts, credits © OpenStreetMap contributors and Geofabrik GmbH, links the ODbL, and states that heights are estimates or tagged-but-unverified. If the optional package is absent or invalid, terrain remains usable and the UI gives retry, terrain-only and synthetic recovery actions.

Mapped building and road counts do not establish completeness. The AOI stays `selected_pending_coverage` / `not_checked` and M2 remains incomplete. See [TVW-010 handback](docs/milestones/TVW-010.md) for implementation evidence and limitations.

### TVW-011 optional browser road ribbons

TVW-011 reuses the dated, locally recorded Geofabrik Devon OSM PBF and creates a separate ignored road package; it does not request data at runtime. From the `pipeline` folder, run the commands below to rebuild and check the package. `publish-roads` validates the source and writes byte-identical files under ignored `public/worlds/torquay-poc-001/roads/`.

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli inspect-road-source
.\.venv\Scripts\python.exe -m torquay_pipeline.cli import-roads
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-roads
.\.venv\Scripts\python.exe -m torquay_pipeline.cli preview-roads
.\.venv\Scripts\python.exe -m torquay_pipeline.cli publish-roads
Pop-Location
```

Roads are opt-in at `/?world=torquay-poc-001&roads=1`; combined layers use `/?world=torquay-poc-001&buildings=1&roads=1`. The default synthetic world, `/?world=m0`, terrain-only route and buildings route remain available. The browser uses an exact local terrain grid and same-origin package files only. The extractor excludes bridge/tunnel/ambiguous vertical cases and records them as QA exclusions. Ribbon widths are configurable visual estimates, not measured road widths. TVW-011's dated run mapped 198 ways (171 vehicular streets and 27 paths) across 198 clipped centerline parts; this is not a completeness measure. Those ways form 200 separate clipped ribbon components. The UI reports OSM extract vintage, estimated-width policy and `© OpenStreetMap contributors` / Geofabrik attribution with an ODbL link. A missing or invalid roads package leaves terrain usable and provides retry/terrain-only/synthetic recovery.

The optional road package and source-derived outputs are ignored by Git. Share builds preserve tracked synthetic assets and exclude the whole real terrain parent, including buildings and roads. See [TVW-011 handback](docs/milestones/TVW-011.md), [road data provenance](docs/data-sources.md#osm-highway-roads-tvw-011), and [the road package contract](docs/asset-contract.md#optional-osm-road-package-tvw-011).

### TVW-015 optional street-name annotations

On the explicit real-terrain roads route, `/?world=torquay-poc-001&roads=1`, wait for the local road package to load, then use **Street names: off** in the road controls. The opt-in DOM overlay derives names only from each validated road feature's `sourceTags.name`, trims outer whitespace, and places one label at each eligible clipped centerline-part midpoint, sampled 0.25 m above terrain. It shows at most 20 labels within 500 m, avoids the visible interface panels and screen-space collisions, and follows the camera and viewport. Turning the road layer off also turns labels off; labels remain disabled by default.

These are screen annotations rather than physical signs: they are not depth-occluded by terrain or buildings and their counts describe only current display candidates, not road coverage. OSM contributor and Geofabrik attribution stays visible with the road layer. `npm run test:e2e:tvw015:real` builds and checks the production local-data route on an isolated preview port; `npm run test:e2e:tvw015:share` builds the clean share variant and checks that synthetic startup has no road assets or names. Both use local packages only.

### M8 optional offline geographic overview

On the explicit real terrain route, use **Open overview** to lazily load a fixed north-up MapLibre view of the selected AOI ring, plus road centerlines and building footprints only when those optional layers are already loaded and visible in the main viewer. The panel includes a legend, north cue, metric scale, OSM/Geofabrik attribution when OSM features are shown, separate EA source context, and MapLibre licence credit. It is a local GeoJSON overview: it does not show the EA raster, follow the camera, or make a new alignment/completeness claim. Synthetic worlds report that geographic overview is unavailable and never assign real coordinates to fictional geometry.

To build, validate and publish the separate derived overview after restoring the exact local terrain, road and building packages described above:

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli build-overview
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-overview
.\.venv\Scripts\python.exe -m torquay_pipeline.cli publish-overview
Pop-Location
```

The commands use the configured AOI and current validated local packages; they do not download inputs. The generated package is ignored under `data/generated/overview/`, and the byte-identical browser copy is ignored under `public/worlds/torquay-poc-001/overview/`. A clean clone without that copy keeps the synthetic viewer working and presents a retry message on the real overview. The share build excludes the complete real-world parent. MapLibre GL JS 6.15.0 and its CSS/worker are bundled locally and loaded only when a real-world user opens the panel; the overview has no remote style, tiles, fonts, sprites or service. Production build output adds approximately 1.09 MB of minified MapLibre JavaScript, 71 KB CSS, and a 518 KB worker asset (plus a small worker URL wrapper); the worker and map code are lazy-loaded. See the [overview asset contract](docs/overview-asset-contract.md) and [M8 handback](docs/milestones/M8-overview-minimap.md) for hashes, browser evidence and exact limits.

Playwright's install command downloads a local Chromium build and requires internet access. After installation, the browser tests use local files. The persistent Chromium suite covers both the retained M0 viewer and loaded terrain, pointer lock and movement, terrain grid and wireframe controls, optional building publication/load/render/toggle and recovery, ground-height telemetry, resize, Escape release, and held-key cleanup. Vitest covers movement, manifest validation, binary decoding/loading, terrain grid/sampling, and Three.js mesh geometry.

## M7 clean demo, local real-data rebuild, and benchmark

The synthetic default and `/?world=m0` need only the tracked repository and Node.js; neither requires the ignored EA/OSM sources or generated real-world packages. On a clean clone, run `npm ci`, `npm run build:share`, then `npm run test:e2e:tvw014:share`. The share build intentionally omits `public/worlds/torquay-poc-001/`; the smoke test checks synthetic startup, pointer-lock navigation, movement, boost, reset, Escape, resize, and recovery when the optional EA package is absent. This verifies the share build and missing-data path, not a real-world source build.

To regenerate the existing local real-data packages, restore only the exact ignored source files documented in [docs/data-sources.md](docs/data-sources.md) and hash-checked in [data/source-manifest.json](data/source-manifest.json). This project does not download data at runtime. From PowerShell, run the current inspection, terrain build, building import/publication, and road import/publication commands from `pipeline`:

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli inspect-sources
.\.venv\Scripts\python.exe -m torquay_pipeline.cli build-terrain
.\.venv\Scripts\python.exe -m torquay_pipeline.cli inspect-building-source
.\.venv\Scripts\python.exe -m torquay_pipeline.cli import-buildings
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-buildings
.\.venv\Scripts\python.exe -m torquay_pipeline.cli publish-buildings
.\.venv\Scripts\python.exe -m torquay_pipeline.cli inspect-road-source
.\.venv\Scripts\python.exe -m torquay_pipeline.cli import-roads
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-roads
.\.venv\Scripts\python.exe -m torquay_pipeline.cli publish-roads
Pop-Location
npm ci
npm run build
npm run test:e2e:tvw014:real
```

The six benchmark workloads cover synthetic M0, EA terrain, terrain plus either optional layer, and the combined scene in fly and walk modes. The command `npm run benchmark` starts its own production preview on a newly allocated local port and refuses to attach to a pre-existing server. It writes raw frame intervals and a summary to `docs/milestones/artifacts/TVW-014-benchmark.{json,md}` and actual-browser captures to `docs/milestones/screenshots/TVW-014-*.png`. It uses a 1920 × 1080 CSS viewport at DPR 1 when the browser permits, a 3-second warm-up, and three 10-second runs per workload. The report records fresh-context and warm-context load time plus Chromium's observed disk/service-worker/prefetch cache-hit counts, frame interval mean/median/p95/p99/maximum, draw calls, triangles, geometry/texture object counts, package manifest/payload/QA bytes, browser/OS/renderer, and sampled JS heap where Chromium exposes it. Renderer memory geometry/texture values are object counts, not byte counts; JS heap is not total process or GPU memory; FPS is not GPU execution time. Measurements describe only the recorded machine and renderer and have no pass/fail threshold. The benchmark samples focus and visibility on every animation frame and records blur/focus events; any transient loss invalidates the affected run.

The viewer credits the Environment Agency and links its catalogue and Open Government Licence v3.0 for the EA terrain. OSM layers credit © OpenStreetMap contributors, name Geofabrik GmbH as the extract provider, and link the ODbL. The OS OpenMap–Local raster appears only as a separate comparison source in [TVW-012](docs/milestones/TVW-012.md), not as rendered terrain, buildings, or roads. The exact source, product, vintage, attribution, and package identities are documented in the source manifest and the [TVW-014 handback](docs/milestones/TVW-014.md). The 1,000 m candidate remains `selected_pending_coverage` / `not_checked`; EA raster coverage, mapped feature counts, and three qualitative alignment observations do not prove complete feature coverage or approve/freeze the AOI.

## Project documents

- `docs/project-plan.md` is the canonical working copy of the plan.
- `docs/Torquay_JS_Virtual_World_PoC_Codex_Plan.md` is the supplied source plan and is preserved unchanged.
- `AGENTS.md` records the project working rules and current authorization boundary.
- `docs/milestones/M0.md` records the synthetic M0 browser evidence.
- `docs/milestones/TVW-004.md` records the synthetic manifest, binary fixture and loader evidence.
- `docs/milestones/M1.md` records TVW-005 terrain and browser evidence.
- `docs/milestones/TVW-006.md` records the candidate AOI calculation, CLI and verification.
- `docs/milestones/TVW-007.md` records EA DTM acquisition, exact cell coverage and preview evidence.
- `docs/milestones/TVW-008.md` records the resampling/export QA, local viewer behavior and browser evidence.
- `docs/milestones/TVW-009.md` records the dated OSM source, local building-footprint QA, placement checks and implementation handback.
- `docs/milestones/TVW-010.md` records optional building rendering, local package publication and browser evidence.
- `docs/milestones/TVW-011.md` records the local OSM highway pipeline, terrain-draped ribbons, QA and browser evidence.
- `docs/milestones/TVW-015.md` records optional street-name labels, the production browser evidence and the labels-off/on observation.
- `docs/milestones/TVW-014.md` records the clean-clone smoke, restored-source regeneration, production checks, benchmark, screenshots and limitations.
- `docs/milestones/M8-overview-minimap.md` records the fixed local geographic overview implementation and browser evidence.
- `docs/overview-asset-contract.md` documents the separate RFC 7946 overview derivative, integrity checks and recovery behavior.
- `docs/data-sources.md` documents publisher provenance, local source-file restoration and the current inspection result.
- `docs/building-asset-contract.md` documents the local OSM footprint package, coordinates, height provenance and QA meaning.
- `data/source-manifest.json` records actual source URLs, archive checksums, raster metadata, licence and attribution.
- `docs/milestones/screenshots/TVW-006-postcode-context.png` is the dated, attributed OSM anchor-context screenshot.
- `docs/milestones/screenshots/TVW-006-aoi-boundary.png` preserves the original 500 m candidate square over an attributed OSM map as historical evidence.
- `docs/milestones/screenshots/TVW-006-aoi-boundary-1km.png` shows the user-approved 1,000 m candidate square over an attributed OSM map.
- `config/aoi.torquay.json` is the editable candidate anchor and size; generated bounds and provenance are in `docs/aoi-selection.json` and `docs/aoi-selection.geojson`.
- `docs/asset-contract.md` describes synthetic and real manifest provenance, coordinates, triangulation and sampling semantics.

The original plan remains preserved unchanged at `docs/Torquay_JS_Virtual_World_PoC_Codex_Plan.md`; the canonical copy records the verified anchor and user-approved 1,000 m pending candidate square. EA DTM cell coverage has been measured and passes its 1% threshold. OSM building-footprint counts and placement QA are available; broader OSM/OS feature-coverage checks remain M2 work, so the candidate remains pending and is not coverage-approved or frozen.
