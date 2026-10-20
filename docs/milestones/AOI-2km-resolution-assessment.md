# AOI 2 km revision and elevation-resolution assessment

**State:** implementation handback submitted for independent review. The current AOI remains `selected_pending_coverage` / `not_checked`; this report does not approve or freeze it.

## Candidate revision

On 2026-10-20, the user authorized expanding the pending candidate to 2,000 m × 2,000 m around the existing TQ1 4HN postcode centroid. The center remains E `291108.9018176432`, N `65353.48350844931` (EPSG:27700). The current bounds are `[290108.9018176432, 64353.48350844931, 292108.9018176432, 66353.48350844931]`, ordered west, south, east, north. The anchor is still a postcode centroid, not a property or survey point.

`config/aoi.torquay.json` explicitly selects `current_2km`. `config/aoi.torquay-1km.json` is a separate `historical_1km` profile with the same center and pending statuses; it exists so prior packages can be validated or regenerated intentionally. Its projected selection snapshot is in [`artifacts/AOI-1km-selection/`](artifacts/AOI-1km-selection/). Current selection outputs remain at `docs/aoi-selection.{json,geojson,md}`. No package generation command silently changes between these profiles.

## Independent map context

The [independent OpenStreetMap capture](screenshots/AOI-2km-independent-OSM-context.png) was made from the live OSM page on 2026-10-20 at zoom 15, with a 1440 × 905 px map viewport. The browser loaded 24 of 24 visible map tiles. The orange outline and TQ1 4HN center marker were overlaid in the browser from the exact WGS84 ring and anchor in `docs/aoi-selection.geojson`; no coordinates were invented. The visible base map retains the OSM contributors attribution. The screenshot provides geographic context for the user-authorized size expansion. The candidate remains `selected_pending_coverage` / `not_checked`.

## Existing 1 m raster reassessment

The verified EA Composite DTM source archives and `data/source-manifest.json` were left unchanged. The existing two 1 m GeoTIFFs were inspected over the revised AOI. [`AOI-2km-1m-coverage.json`](artifacts/AOI-2km-1m-coverage.json) records 4,000,000 / 4,000,000 valid 1 m cell-center samples over 4,000,000 m², zero uncovered or invalid cells, sample range 12.288–104.355598 m, and center sample 47.619999 m. This is the EA raster threshold result only. It does not change the overall `coverage_status`.

The north-up [2 km raster preview](screenshots/AOI-2km-1m-preview.png) was generated from those actual source samples and visually inspected. It shows the candidate boundary, center, BNG metre axes, explicit north arrow, 250 m scale, elevation range, missing-cell legend, and EA attribution. No browser heightfield or GIS package was regenerated, so existing ignored terrain/building/road browser packages remain the earlier 1 km outputs.

The real EA viewer mode continues to display the retained earlier 1 km terrain package; optional buildings and roads also remain earlier 1 km packages. The current 2 km candidate has not been rendered in the browser. A persistent real-route HUD notice and the welcome copy now state this distinction. The real-route browser screenshot is [`AOI-2km-real-route-1km-package-notice.png`](screenshots/AOI-2km-real-route-1km-package-notice.png); it is captured after Start dismisses the landing overlay.

## EA nominal DTM resolution-index assessment

The official [EA LIDAR DTM Time Stamped Tiles catalogue](https://www.data.gov.uk/dataset/8275e71e-1516-42a1-bb0c-4fa73807fe2b/lidar-dtm-time-stamped-tiles), updated 2026-04-07, documents nominal 0.25 m, 0.5 m, 1 m and 2 m DTM outputs. Its Newlyn vertical-reference and ±15 cm RMSE statements are catalogue-level claims. They do not verify each indexed raster. The product's [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) attribution is `© Environment Agency copyright and/or database right 2020. All rights reserved.`

An explicit online capture queried the official [EA Survey Index WFS](https://environment.data.gov.uk/spatialdata/survey-index-files/wfs), feature type `dataset-9f0fa3fc-a860-4729-adc9-47fe53f658d0:LIDAR_DTM_Time_Stamped_Extents`. The request used the exact current EPSG:27700 bounds and `count=1000`; WFS `startIndex` was zero (default). On 2026-10-20 at `06:03:41Z`, the server returned HTTP 200, JSON in EPSG:27700, `numberMatched=50`, `numberReturned=50`, and 50 feature records. The raw response is 904,542 bytes with SHA-256 `cda7ce43af709ac2177cf000b404525d59476426ab22ad8a7404498d39a71de4`. Its exact URL and response timestamp `2026-10-20T06:03:41.185Z` are recorded in [`data/elevation-index/ea-dtm-time-stamped-2km-2026-10-20.source.json`](../../data/elevation-index/ea-dtm-time-stamped-2km-2026-10-20.source.json); raw GeoJSON is [`data/elevation-index/ea-dtm-time-stamped-2km-2026-10-20.geojson`](../../data/elevation-index/ea-dtm-time-stamped-2km-2026-10-20.geojson).

The bounded capture command issues one page only, with a 30-second default timeout and 16 MiB maximum body. It verifies the endpoint, exact AOI request, HTTP status, JSON content type, CRS, and equality of matched, returned, and feature counts. If the one-page result is truncated, it fails before writing either file rather than silently paginating or retaining a partial snapshot. Assessment and ordinary automated tests are offline and use the saved snapshot or fixtures.

The assessment found 42 nominal 1 m features, 4 nominal 2 m features and 4 nominal 0.5 m features intersecting the query. The four 0.5 m records are dated 2010-04-04, list `OSTN'02` / `OSGM'02`, and identify tiles SX9064, SX9164, SX9165 and SX9265. Their polygon union clipped to the candidate covers 397,628.696 m², or 9.9407% of the AOI. [`AOI-2km-resolution-index.json`](artifacts/AOI-2km-resolution-index.json) is the deterministic measured report.

These are metadata footprints only. No 0.5 m raster was acquired or tested for download availability, pixel validity, or NoData. No 0.5 m raster was adopted. Point-cloud spacing is a separate property and was not assessed here. The broader OSM/OS feature-completeness checks remain outstanding; the candidate stays pending.

## Commands and evidence status

Commands executed during implementation are recorded in the task handback. The essential offline commands, run from `pipeline/`, are:

```powershell
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-aoi --config ..\config\aoi.torquay.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli select-aoi --config ..\config\aoi.torquay.json --output-dir ..\docs
.\.venv\Scripts\python.exe -m torquay_pipeline.cli inspect-sources --config ..\config\aoi.torquay.json --report ..\docs\milestones\artifacts\AOI-2km-1m-coverage.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli assess-resolution-index --config ..\config\aoi.torquay.json --index ..\data\elevation-index\ea-dtm-time-stamped-2km-2026-10-20.geojson --source-metadata ..\data\elevation-index\ea-dtm-time-stamped-2km-2026-10-20.source.json --report ..\docs\milestones\artifacts\AOI-2km-resolution-index.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli capture-resolution-index --config ..\config\aoi.torquay.json --output-dir ..\data\raw\ea_dtm_time_stamped_index\final-capture-2026-10-20 --timeout-seconds 30
.\.venv\Scripts\python.exe -m torquay_pipeline.cli preview-terrain --config ..\config\aoi.torquay.json --output ..\docs\milestones\screenshots\AOI-2km-1m-preview.png
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-buildings --aoi-config ..\config\aoi.torquay-1km.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-roads --aoi-config ..\config\aoi.torquay-1km.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-overview --aoi-config config/aoi.torquay-1km.json
```

The actual raster preview above is a separate 2D Python QA image. The explicit capture-resolution-index command is the only online path; assess-resolution-index reads a saved response and sidecar. Ordinary tests use local fixtures only.

## Verification results

The Python checks ran from `pipeline/`: `python -m pytest -q` passed 268 tests, Ruff check and format check passed, and `python -m pip check` reported no broken requirements. The local historical package validators passed with an explicit 1 km profile: buildings reported 1,000 features and SHA-256 7ffe824db1f0bafadf48c14f610a357f2a001791658078b12442a71e13ea8f48; roads reported 198 features and SHA-256 56d017df60cfb4c655cf484c58e17cc858d0959da211c225501ca56676fd1ec3; overview reported 1,197 features with manifest SHA-256 226d2bb12618c578848d09767a1698b5535dad1e398a903b8ebd2b93dac9cc76 and feature SHA-256 8c6e2e7155337bf1bcb931592b5463ad1936feab7ebacd2ce308b3f492148916.

The current 2 km raster inspection reported 4,000,000 / 4,000,000 valid 1 m cell centers and zero missing. Its deterministic coverage-report SHA-256 is 12055299e34ac568b964df1be7acc23082af856aa7dd6f5563ea28775124f235. The PNG was re-rendered after adding a compact north arrow and visually inspected; it shows the arrow pointing toward the top/north edge, the candidate bounds, center marker, 250 m scale, elevation colorbar, missing-cell legend and EA attribution. Two renders matched at SHA-256 f59ef055575e19a6c430a99332b74298de1f880d4afffda02fc7c842d78976d8.

The online capture returned HTTP 200, 50 matched and 50 returned records in one complete page. Its raw response is 904,542 bytes, SHA-256 cda7ce43af709ac2177cf000b404525d59476426ab22ad8a7404498d39a71de4. The saved-response assessment was repeated from the local snapshot and produced byte-identical JSON with SHA-256 a7788fc919ed247a21508c68ba889c538c6999c589de6649f06c82b43a8e0cf6. One repeated relative-path coverage-report replacement transiently returned Windows WinError 5; the prior report remained intact. The same report command then succeeded again using an absolute destination and the documented relative destination, with identical SHA-256 output.

The existing Node install was used; no JavaScript dependencies changed. `npm.cmd ls --depth=0`, `npm.cmd run typecheck`, `npm.cmd run lint`, `npm.cmd run format:check`, `npm.cmd test`, and `npm.cmd run build` all succeeded; Vitest passed 275 tests in 20 files. The build emitted Vite's existing large MapLibre chunk warning. `npm.cmd run test:e2e:tvw014:real` passed 3/3 tests after the final UI and assertion changes. The run verified the persistent 1 km package / pending 2 km candidate notice remains visible in the real route after Start dismisses the landing view, confirmed the retained terrain is 501 × 501 at 2 m spacing, checked the loaded 1,000 building footprints and 198 road ways, then verified synthetic recovery hides the real-only notice. The real-route screenshot was captured in bundled Chromium 156.0.8078.4 at 1440 × 900 CSS pixels and DPR 1.5 (2160 × 1350 image pixels). The notice is visibly legible in the HUD; terrain and optional 1 km features remain shown behind it. Historical terrain/building/road browser packages and the older TVW-007 screenshot remain unchanged.
