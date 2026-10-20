# Torquay Virtual World

A Windows-friendly local browser viewer of the current 2 km Torquay candidate. Open `/` to load the existing EA terrain, OSM buildings, OSM roads and source-derived street names together. The existing bookmark `/?world=torquay-poc-001-2km&buildings=1&roads=1` also works; layer query flags do not disable layers on this current map. The terrain mesh has 1,001 × 1,001 samples at 2 m spacing. The app offers navigation, Controls and Sources; world/layer selectors and visual debug options have been removed.

Road names appear automatically from validated OSM `name` tags, with no label toggle. The existing display limits retain at most 20 labels within 500 m, filtering collisions and UI panels. These annotations are not terrain/building occlusion-aware and do not imply complete road-name coverage. Synthetic fallback displays no real road names. The current map does not show a road QA/debug landmark marker.

On a clean clone or share build, the real package is absent. The app automatically opens fictional synthetic terrain, explains the unavailable package, and offers **Retry Torquay**. Its badge and message identify the fallback as synthetic. Restore the documented local sources and publish the current package using the [2 km package handback](docs/milestones/Torquay-2km-viewer.md), then retry. Invalid packages also fall back with their validation reason; they are never treated as real terrain. A building/road failure retains usable terrain and provides a focused layer retry.

The internal reproduction routes `/?world=synthetic`, `/?world=m0`, and `/?world=torquay-poc-001&buildings=1&roads=1` preserve the synthetic fixtures and historical 1 km profile. They are developer bookmarks, not product world choices. The sections below describing earlier milestone controls are historical implementation records; the current product behavior is described here and in the [cleanup handback](docs/milestones/Viewer-cleanup.md).

The synthetic terrain and its measurements are fictional. Real terrain comes from EA Composite DTM 1 m cells sampled into the current 2 m mesh. **Sources** retains publisher/licence links, Newlyn height reference, source vintages and estimated-height/width caveats. EA and OSM attribution remains visible during navigation. The app states **2 km candidate · AOI pending; feature coverage not checked.** The overall AOI remains `selected_pending_coverage` / `not_checked`: mapped counts and placement checks do not establish completeness. The 1 m raster check found 4,000,000 valid cell centers; the separate saved index has nominal 0.5 m footprints over only 9.9407% and no finer raster was checked. The OSM extract is dated 2026-10-16. TVW-012 records three qualitative road-placement passes and no numeric offset measurement. Its 2 m reported coordinate-operation accuracy and missing preferred OSTN15 grid are limitations, not a diagnosed road offset. See [the TVW-012 report](docs/milestones/TVW-012.md).

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

Click **Start exploring** to enter pointer lock. Move the mouse to look. **W/S** and **A/D** move in the current navigation mode; **Shift** boosts speed. Both modes use 15 m/s normal speed and 41.25 m/s boosted speed. In **fly mode**, movement follows the full camera look direction and **Space/Ctrl** rise or descend. In **walk mode**, movement follows camera yaw, ignores vertical keys, and keeps the eye 1.7 m above the active terrain sample. Use the **Enter walk mode** button or **F** while pointer-locked; if you are flying above the terrain, the camera smoothly acquires walk height. Use **F** again to cancel acquisition. **R** restores the fly spawn, or resets to the sampled walk spawn while remaining in walk mode. **Esc** releases the pointer and pauses movement/acquisition; click the scene or the mode-appropriate **Resume** button to relock. The camera stays inside finite world bounds; the status pill signals when you reach an edge. Terrain grid, axes, north helpers and wireframes are hidden; **G** has no effect.

Use **Show controls** or **H** for navigation help, and **Sources** for data context and licence links. Telemetry and visual debug controls are absent from the product UI. Read-only invisible observations remain available to local browser checks. A load failure explains the unavailable Torquay package and opens a labelled fictional fallback with **Retry Torquay**; individual layer failures retain terrain and provide focused retries.

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

The Python pipeline is separate from the browser and uses no online transformation-grid downloads. On 2026-10-20 the user authorized expanding the pending candidate to 2,000 m × 2,000 m in EPSG:27700 around the existing TQ1 4HN WGS84 postcode centroid. The WGS84 and BNG centres are unchanged; the anchor is a postcode centroid, not a property or survey point. The earlier 1,000 m candidate and its EA/browser package remain historical. The separate 2 km package is built from the same verified local sources and does not overwrite the 1 km outputs. The current candidate remains `selected_pending_coverage`; OSM building footprints and roads have been imported and QA-checked, and three road placement comparisons are complete. Their mapped counts and local placement checks do not prove complete feature coverage. OS building checks and broader OSM/OS feature-coverage checks remain outstanding, so the AOI is not frozen.

`config/aoi.torquay.json` is the current `current_2km` profile. The separate `config/aoi.torquay-1km.json` is an explicit frozen `historical_1km` profile for validating or reproducing the older GIS packages; it retains the same verified center and pending status. The regenerated 1 km selection evidence is saved under `docs/milestones/artifacts/AOI-1km-selection/`. Commands that operate on old packages must pass that historical config explicitly; normal defaults continue to use the current 2 km candidate.

### Generate and open the 2 km fly-through

Restore the exact EA archives/rasters and Devon PBF listed in `data/source-manifest.json` under ignored `data/raw/` paths. Follow [docs/data-sources.md](docs/data-sources.md) for the original download paths and integrity checks. Then run the local offline builder from PowerShell:

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli build-scene --profile current_2km
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-scene --profile current_2km
Pop-Location
```

The builder creates an ignored content-addressed release beneath `public/worlds/torquay-poc-001-2km/releases/`. It copies only the allowlisted runtime files, verifies each file, writes the inventory last, fully validates the release, and atomically activates the small `ready.json` pointer. The app does not request any 2 km terrain/building/road package files until that pointer and its inventory validate; all three layers then use the same pinned release. If you already have a validated staging directory from an interrupted build, retry publication with `publish-scene --profile current_2km --validated-stage <validated-stage-path>` from `pipeline`; this copies and validates the release without rerunning GIS extraction. The product entry `/` opens that combined 2 km scene. Historical 1 km and synthetic scenes remain on internal reproduction routes. The 2 km scene has no compatible overview package, so the product exposes no overview control. Without a real package, `/` automatically loads a labelled fictional fallback and can run without raw geographic sources.

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

To regenerate the historical 1 km selection without changing the current AOI files:

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-aoi --config ..\config\aoi.torquay-1km.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli select-aoi --config ..\config\aoi.torquay-1km.json --output-dir ..\docs\milestones\artifacts\AOI-1km-selection
Pop-Location
```

### TVW-007 EA DTM check

The local inspection used two public Environment Agency LIDAR Composite DTM 1 m (2022 composite) tiles. Their exact portal download links, archive names, byte sizes, SHA-256 digests, extracted TIFF metadata and tile-level XML provenance are recorded in [data/source-manifest.json](data/source-manifest.json). The archives and extracted files belong under ignored `data/raw/ea_dtm/`; the tracked manifest does not contain raster data. Follow [docs/data-sources.md](docs/data-sources.md) to restore the exact files on a clean clone.

From PowerShell, after restoring the source files:

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli inspect-sources --config ..\config\aoi.torquay-1km.json --report ..\docs\milestones\artifacts\AOI-1km-coverage-reproduction.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli preview-terrain --config ..\config\aoi.torquay-1km.json --output ..\docs\milestones\screenshots\AOI-1km-dtm-preview-reproduction.png
Pop-Location
```

`inspect-sources` verifies archive and raster hashes/metadata, then samples the source pixel containing each AOI-aligned 1 m cell center. It does not interpolate or fill missing cells. The historical TVW-007 report for the then-current 1 km candidate is `docs/milestones/artifacts/TVW-007-coverage.json`; it recorded 1,000,000 valid cells out of 1,000,000, no uncovered, masked, NoData or nonfinite cells, and an EA DTM-only pass against the 1% threshold. Its sample range was 29.529–98.171 m and its configured center sample was 47.620 m. At that handback, `coverage_status` remained `not_checked` pending later feature checks. TVW-009 added OSM building-footprint measurements, TVW-011 completed road import and rendering, and TVW-012 completed three qualitative road placement comparisons. Broader OSM/OS feature-coverage checks remain outstanding.

`preview-terrain` wrote the historical 1 km north-up PNG at `docs/milestones/screenshots/TVW-007-ea-dtm-preview.png`. The new 2 km review regenerated separate coverage and preview artifacts described below; this old screenshot is preserved unchanged. The raster preview is a separate Python QA artifact; TVW-008 adds a locally generated browser heightfield without changing the synthetic default.

### Current 2 km candidate assessment (2026-10-20)

The user-authorized size expansion retains the exact verified centre (E `291108.9018176432`, N `65353.48350844931`) and uses bounds `[290108.9018176432, 64353.48350844931, 292108.9018176432, 66353.48350844931]` in west, south, east, north order. The new [`AOI-2km-1m-coverage.json`](docs/milestones/artifacts/AOI-2km-1m-coverage.json) reports 4,000,000/4,000,000 valid cell centers over 4,000,000 m², with no uncovered, masked/NoData, or nonfinite cells. This is the EA DTM raster gate only; overall `coverage_status` remains `not_checked`.

The [EA LIDAR DTM Time Stamped Tiles catalogue](https://www.data.gov.uk/dataset/8275e71e-1516-42a1-bb0c-4fa73807fe2b/lidar-dtm-time-stamped-tiles) describes 25 cm, 50 cm, 1 m and 2 m DTM products. The exact 2 km EPSG:27700 query to the [EA WFS index](https://environment.data.gov.uk/spatialdata/survey-index-files/wfs) returned 50 records: 42 nominal 1 m, 4 nominal 2 m and 4 nominal 0.5 m records. The four 0.5 m polygons have a clipped union area of 397,628.696 m² (9.9407% of this AOI); they are all dated 2010-04-04 and identify OSTN'02 / OSGM'02. This is index-footprint metadata only: no 0.5 m DTM files were acquired or inspected, and no 0.5 m raster coverage is claimed. The saved WFS response and provenance are in [`data/elevation-index/`](data/elevation-index/); the deterministic summary is [`AOI-2km-resolution-index.json`](docs/milestones/artifacts/AOI-2km-resolution-index.json).

The preview [`AOI-2km-1m-preview.png`](docs/milestones/screenshots/AOI-2km-1m-preview.png) shows the actual 1 m raster samples, exact 2 km border, center marker, scale and attribution. The retained 1 km terrain/building/road package remains unchanged at its historical route. A separately generated 2 km combined package is published as an immutable local release and selected by the primary EA terrain route; its publication and browser evidence are recorded in the [2 km fly-through handback](docs/milestones/Torquay-2km-viewer.md). Neither package establishes complete feature coverage, and the current AOI remains pending. See the [2 km assessment handback](docs/milestones/AOI-2km-resolution-assessment.md) for methods, commands and limits.

`assess-resolution-index` is an offline deterministic calculation from the saved response and sidecar under `data/elevation-index/`; it makes no request. To explicitly refresh the official metadata snapshot, run `capture-resolution-index` with a new output directory. That command sends one WFS 2.0.0 `GetFeature` request to the named EA DTM time-stamped extent layer, using the configured EPSG:27700 AOI bbox, `startIndex=0` (the WFS default) and `count=1000`. It has a 30-second default timeout, a 16 MiB response cap, and writes raw response bytes plus integrity/provenance sidecar only when `numberMatched == numberReturned == features.length`; a truncated page fails without saving. Ordinary tests read fixtures and never access the network.

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli assess-resolution-index
.\.venv\Scripts\python.exe -m torquay_pipeline.cli capture-resolution-index --config ..\config\aoi.torquay.json --output-dir ..\data\raw\ea_dtm_time_stamped_index\refresh-YYYY-MM-DD
Pop-Location
```

### TVW-008 local terrain package and viewer

After restoring the source archives and extracted rasters as described in `docs/data-sources.md`, build the local browser package from the `pipeline` folder:

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli build-terrain --config ..\config\aoi.torquay-1km.json --report ..\docs\milestones\artifacts\TVW-008-qa-reproduction.json --preview ..\docs\milestones\screenshots\TVW-008-terrain-preview-reproduction.png
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
.\.venv\Scripts\python.exe -m torquay_pipeline.cli import-buildings --aoi-config ..\config\aoi.torquay-1km.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-buildings --aoi-config ..\config\aoi.torquay-1km.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli preview-buildings --aoi-config ..\config\aoi.torquay-1km.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli publish-buildings --aoi-config ..\config\aoi.torquay-1km.json
Pop-Location
```

The importer verifies the exact PBF hash and header, assembles building areas before filtering, reads a 50 m buffer, clips geometry to the historical 1,000 m square, applies the documented height fallback, and writes a separate local package under `data/generated/buildings/torquay-poc-001/`. `import-buildings` also writes `docs/milestones/artifacts/TVW-009-buildings-qa.json`, `docs/milestones/screenshots/TVW-009-buildings-preview.png`, and an ignored raw-tag intermediate. The historical 1 km measurement exported 1,000 footprints covering 172,969.138 m²; 998 use the configured 8 m visual default and 2 use `building:levels × 3 m`. None had a usable direct `height` tag. These counts describe mapped OSM data, not completeness or verified building heights. The OSM-specific placement check and implementation evidence are recorded in [docs/milestones/TVW-009.md](docs/milestones/TVW-009.md).

### TVW-010 optional browser building layer

After restoring the exact source PBF and local EA terrain package and running the TVW-009 commands above, `publish-buildings` validates the source package and atomically copies its three byte-identical assets into the ignored Vite public tree. The default synthetic world and `/?world=m0` are unchanged; the EA terrain-only route is `/?world=torquay-poc-001`; the explicit building route is `/?world=torquay-poc-001&buildings=1`. The EA terrain HUD also has a **Load OSM buildings** control. The optional package never triggers a remote request. `npm run build:share` excludes the real terrain/building package.

The renderer preserves the package's local XZ positions and shows polygon roofs and terrain-following exterior/courtyard walls. A feature's flat roof is set to the maximum terrain sample under all its components, excluding hole interiors, plus its validated tagged or estimated height. This is a visual placement convention, not a measured roof or foundation height; wall bases are lowered by 0.02 m to avoid seams. The HUD reports the actual feature/component and height-method counts, credits © OpenStreetMap contributors and Geofabrik GmbH, links the ODbL, and states that heights are estimates or tagged-but-unverified. If the optional package is absent or invalid, terrain remains usable and the UI gives retry, terrain-only and synthetic recovery actions.

Mapped building and road counts do not establish completeness. The AOI stays `selected_pending_coverage` / `not_checked` and M2 remains incomplete. See [TVW-010 handback](docs/milestones/TVW-010.md) for implementation evidence and limitations.

### TVW-011 optional browser road ribbons

TVW-011 reuses the dated, locally recorded Geofabrik Devon OSM PBF and creates a separate ignored road package; it does not request data at runtime. From the `pipeline` folder, run the commands below to rebuild and check the package. `publish-roads` validates the source and writes byte-identical files under ignored `public/worlds/torquay-poc-001/roads/`.

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli inspect-road-source
.\.venv\Scripts\python.exe -m torquay_pipeline.cli import-roads --aoi-config ..\config\aoi.torquay-1km.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-roads --aoi-config ..\config\aoi.torquay-1km.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli preview-roads --aoi-config ..\config\aoi.torquay-1km.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli publish-roads --aoi-config ..\config\aoi.torquay-1km.json
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
.\.venv\Scripts\python.exe -m torquay_pipeline.cli build-overview --aoi-config config/aoi.torquay-1km.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-overview --aoi-config config/aoi.torquay-1km.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli publish-overview --aoi-config config/aoi.torquay-1km.json
Pop-Location
```

The commands use the configured AOI and current validated local packages; they do not download inputs. The generated package is ignored under `data/generated/overview/`, and the byte-identical browser copy is ignored under `public/worlds/torquay-poc-001/overview/`. A clean clone without that copy keeps the synthetic viewer working and presents a retry message on the real overview. The share build excludes the complete real-world parent. MapLibre GL JS 6.15.0 and its CSS/worker are bundled locally and loaded only when a real-world user opens the panel; the overview has no remote style, tiles, fonts, sprites or service. Production build output adds approximately 1.09 MB of minified MapLibre JavaScript, 71 KB CSS, and a 518 KB worker asset (plus a small worker URL wrapper); the worker and map code are lazy-loaded. See the [overview asset contract](docs/overview-asset-contract.md) and [M8 handback](docs/milestones/M8-overview-minimap.md) for hashes, browser evidence and exact limits.

Playwright's install command downloads a local Chromium build and requires internet access. After installation, browser tests use local files. `npm run test:e2e` builds the synthetic share distribution and runs its production smoke suite. `npm run test:e2e:cleanup:real` builds the normal distribution and verifies current 2 km startup, navigation, missing controls, source honesty, failure/retry, internal fixtures and the historical 1 km profile. It requires the locally published real packages. `npm run test:e2e:cleanup:share` explicitly checks the share build. Existing TVW-014/015/overview/2km profile names are compatibility aliases to the corresponding current suite; they no longer schedule the removed-control scenarios. Earlier E2E source files are retained as historical acceptance records. New captures use `docs/milestones/screenshots/Viewer-cleanup/`, preserving accepted older screenshots. Vitest continues to cover movement, manifest validation, binary decoding/loading, terrain sampling and mesh geometry.

## M7 clean demo, local real-data rebuild, and benchmark

The current automatic synthetic fallback and internal `/?world=m0` route need only the tracked repository and Node.js. On a clean clone, run `npm ci`, then `npm run test:e2e`. The share build intentionally omits both real packages and all recovery stages. The smoke suite checks truthful fallback, synthetic navigation/reset/walk, retry, no downstream real GIS requests after unavailable readiness, and fixture/M0 routes. This verifies the share build and missing-data path, not a GIS source build. The regeneration and benchmark descriptions below record the historical M7 workflow; use the current combined 2 km build instructions above for current data restoration.

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

The viewer credits the Environment Agency and links its catalogue and Open Government Licence v3.0 for the EA terrain. OSM layers credit © OpenStreetMap contributors, name Geofabrik GmbH as the extract provider, and link the ODbL. The OS OpenMap–Local raster appears only as a separate comparison source in [TVW-012](docs/milestones/TVW-012.md), not as rendered terrain, buildings, or roads. The exact source, product, vintage, attribution, and package identities are documented in the source manifest and the [TVW-014 handback](docs/milestones/TVW-014.md). The current 2,000 m candidate remains `selected_pending_coverage` / `not_checked`; EA raster coverage, mapped feature counts, and three qualitative alignment observations do not prove complete feature coverage or approve/freeze the AOI. Existing browser packages remain generated for the earlier 1,000 m candidate.

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
- `docs/milestones/screenshots/TVW-006-aoi-boundary-1km.png` shows the user-authorized 1,000 m candidate size over an attributed OSM map.
- `config/aoi.torquay.json` is the editable candidate anchor and size; generated bounds and provenance are in `docs/aoi-selection.json` and `docs/aoi-selection.geojson`.
- `docs/asset-contract.md` describes synthetic and real manifest provenance, coordinates, triangulation and sampling semantics.

The original plan remains preserved unchanged at `docs/Torquay_JS_Virtual_World_PoC_Codex_Plan.md`; the canonical copy records the verified anchor and current user-authorized 2,000 m pending candidate square. The source manifest retains its historical 1,000 m acquisition record; the new 2,000 m processing extent and package identity are recorded separately. The EA DTM cell check measures raster coverage for the current square, while the OS index assessment is footprint metadata only. Building and road packages for both 1,000 m historical and 2,000 m current profiles are source-derived and validated; broader feature-coverage checks remain outstanding, so the candidate remains pending and is not coverage-approved or frozen.
