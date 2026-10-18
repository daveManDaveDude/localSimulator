# Torquay Virtual World

A Windows-friendly browser proof of concept for a future real-data view of Torquay. The default viewer loads a checked-in synthetic Float32 heightfield and renders its terrain mesh, hill, ridge, grid and north cue. The prior M0 analytic scene remains available at `/?world=m0`. The **EA terrain** selector loads a locally generated 2 m Float32 heightfield from the verified Environment Agency DTM tiles when that ignored package exists in `public/worlds/torquay-poc-001/`.

The synthetic heightfield, hill, ridge, analytic slope, blocks and their measurements are fictional; they are not Torquay measurements. The real terrain mode uses the actual Environment Agency DTM source tiles and displays their source attribution and Ordnance Survey Newlyn vertical reference. Its heights are stored relative to a deterministic center origin. The HUD links to the publisher catalogue and Open Government Licence v3.0. EA raster coverage and resampling passed for the candidate square, and a separate OSM building-footprint package and QA map have been generated. The overall AOI remains `selected_pending_coverage` / `not_checked`: these mapped building counts do not establish completeness, and the planned road/OS feature checks remain outstanding. The viewer does not load OSM/OS data, real roads or buildings.

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

Click **Start exploring** to enter pointer lock. Move the mouse to look; use **W/S** to fly along the full camera direction, **A/D** to strafe, **Space/Ctrl** to rise and descend, **Shift** to move faster, **R** to restore the spawn position and view, and **Esc** to release the pointer. The camera stays inside the finite synthetic terrain bounds; the status pill signals when you reach an edge. Click the scene or **Resume flying** to relock after pressing Esc. Use **G** or the terrain-grid button to toggle grid and north cues; the wireframe button changes the terrain mesh display.

The live HUD reports the loaded world, source mode, grid dimensions, sampled ground height, camera position and bearing/pitch, lock state, speed, FPS and boundary state. A load error identifies the failing stage and offers retry and a link to the M0 analytic demo.

## Project commands

```powershell
npm run dev          # Start the local development server
npm run build        # Type-check and produce the static build in dist/
npm run preview      # Serve the production build locally
npm run typecheck    # Run strict TypeScript validation
npm run lint         # Run ESLint
npm run format:check # Check formatting with Prettier
npm run test         # Run movement, asset, terrain-grid, and mesh unit tests
npm run generate:synthetic-heightfield # Rebuild both deterministic synthetic fixture packages
npm run test:e2e:install # Download Playwright's Chromium browser (first time only)
npm run test:e2e     # Run real-browser synthetic and local EA terrain regressions
```

The generator writes the original 3 × 3 loader fixture plus a separate 25 × 19, 2 m-spaced terrain demo. The latter contains a fictional base slope, Gaussian hill and narrow ridge, with little-endian Float32 samples and a SHA-256 in its manifest. `docs/asset-contract.md` documents both manifest variants, local-path and sampling contracts. The synthetic viewer loads the checked-in fixture; the EA mode loads only the generated local package and does not fetch geographic data from a service.

## AOI and EA DTM inspection

The Python pipeline is separate from the browser and uses no online transformation-grid downloads. The 2026-10-17 user-approved revision derives a 1,000 m × 1,000 m EPSG:27700 candidate from the configured TQ1 4HN WGS84 postcode centroid using pyproj with explicit longitude/latitude axis order. It keeps the previously verified WGS84 and BNG centre unchanged. The anchor is a postcode centroid, not a property or survey point. The candidate remains `selected_pending_coverage`; OSM building footprints have been imported and QA-checked, but their mapped count does not prove completeness. OS building and OSM/OS road checks remain outstanding, so the AOI is not frozen.

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

`inspect-sources` verifies archive and raster hashes/metadata, then samples the source pixel containing each AOI-aligned 1 m cell center. It does not interpolate or fill missing cells. The measured report is `docs/milestones/artifacts/TVW-007-coverage.json`; its result is 1,000,000 valid cells out of 1,000,000, no uncovered, masked, NoData or nonfinite cells, and an EA DTM-only pass against the 1% threshold. The sample range is 29.529–98.171 m; the configured center sample is 47.620 m. At the TVW-007 handback, `coverage_status` remained `not_checked` pending later feature checks; TVW-009 now adds OSM building-footprint measurements, while road and remaining feature checks are still outstanding.

`preview-terrain` writes an actual north-up PNG from those measured samples at `docs/milestones/screenshots/TVW-007-ea-dtm-preview.png`. It shows the exact AOI border, BNG metre axes, 250 m scale bar, centre sample, measured elevation colorbar and Environment Agency attribution. This raster preview is a separate Python QA artifact; TVW-008 adds a locally generated browser heightfield without changing the synthetic default.

### TVW-008 local terrain package and viewer

After restoring the source archives and extracted rasters as described in `docs/data-sources.md`, build the local browser package from the `pipeline` folder:

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli build-terrain
Pop-Location
```

The builder verifies the source archive, TIFF and XML hashes, rechecks EA DTM coverage, bilinearly samples the 1 m area-pixel centers onto the exact 501 × 501, 2 m AOI vertex grid, and writes a center-relative little-endian Float32 field. It refuses missing positive-weight contributors, does not fill or extrapolate, and publishes the manifest last. QA and the actual-data north-up PNG are written to `docs/milestones/artifacts/TVW-008-qa.json` and `docs/milestones/screenshots/TVW-008-terrain-preview.png`.

The generated browser package at `public/worlds/torquay-poc-001/` is intentionally ignored by Git because it is derived from locally restored publisher data. On a clean clone the default synthetic viewer continues to work; the EA selector explains how to restore sources and rebuild the package. To open the real mode directly after building it, use `http://localhost:5173/?world=torquay-poc-001`. To return to the retained analytic demo, use `/?world=m0`. The real mode stays local to the Vite app and adds no network service. The EA cell-level result does not approve the broader candidate AOI; `coverage_status` remains `not_checked` pending road and remaining feature checks, and M2 remains incomplete.

### TVW-009 OSM building footprint import and QA

TVW-009 creates an offline OSM footprint package and placement/count QA only. It does not add buildings to the viewer; the local browser remains on synthetic terrain unless the separately implemented EA terrain mode is selected. The source PBF and generated package/intermediate are ignored by Git. See [docs/data-sources.md](docs/data-sources.md) for the exact dated Geofabrik extract, hashes, license, attribution, and restoration steps, and [docs/building-asset-contract.md](docs/building-asset-contract.md) for the package shape and coordinate rules.

After restoring `data/raw/osm/devon-261016.osm.pbf`, run the pipeline from PowerShell:

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli inspect-building-source
.\.venv\Scripts\python.exe -m torquay_pipeline.cli import-buildings
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-buildings
.\.venv\Scripts\python.exe -m torquay_pipeline.cli preview-buildings
Pop-Location
```

The importer verifies the exact PBF hash and header, assembles building areas before filtering, reads a 50 m buffer, clips geometry to the reviewed 1,000 m square, applies the documented height fallback, and writes a separate local package under `data/generated/buildings/torquay-poc-001/`. `import-buildings` also writes `docs/milestones/artifacts/TVW-009-buildings-qa.json`, `docs/milestones/screenshots/TVW-009-buildings-preview.png`, and an ignored raw-tag intermediate. The current measurement exported 1,000 footprints covering 172,969.138 m²; 998 use the configured 8 m visual default and 2 use `building:levels × 3 m`. None had a usable direct `height` tag. These counts describe mapped OSM data, not completeness or verified building heights. The OSM-specific placement check and current implementation status are recorded in [docs/milestones/TVW-009.md](docs/milestones/TVW-009.md); combined M4 remains pending TVW-010.

Playwright's install command downloads a local Chromium build and requires internet access. After installation, the browser tests use local files. The persistent Chromium suite covers both the retained M0 viewer and loaded terrain, pointer lock and movement, terrain grid and wireframe controls, ground-height telemetry, error retry/return, resize, Escape release, and held-key cleanup. Vitest covers movement, manifest validation, binary decoding/loading, terrain grid/sampling, and Three.js mesh geometry.

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
- `docs/data-sources.md` documents publisher provenance, local source-file restoration and the current inspection result.
- `docs/building-asset-contract.md` documents the local OSM footprint package, coordinates, height provenance and QA meaning.
- `data/source-manifest.json` records actual source URLs, archive checksums, raster metadata, licence and attribution.
- `docs/milestones/screenshots/TVW-006-postcode-context.png` is the dated, attributed OSM anchor-context screenshot.
- `docs/milestones/screenshots/TVW-006-aoi-boundary.png` preserves the original 500 m candidate square over an attributed OSM map as historical evidence.
- `docs/milestones/screenshots/TVW-006-aoi-boundary-1km.png` shows the user-approved 1,000 m candidate square over an attributed OSM map.
- `config/aoi.torquay.json` is the editable candidate anchor and size; generated bounds and provenance are in `docs/aoi-selection.json` and `docs/aoi-selection.geojson`.
- `docs/asset-contract.md` describes synthetic and real manifest provenance, coordinates, triangulation and sampling semantics.

The original plan remains preserved unchanged at `docs/Torquay_JS_Virtual_World_PoC_Codex_Plan.md`; the canonical copy records the verified anchor and user-approved 1,000 m pending candidate square. EA DTM cell coverage has been measured and passes its 1% threshold. OSM building-footprint counts and placement QA are available; road and remaining feature checks remain M2 work, so the candidate remains pending and is not coverage-approved or frozen.
