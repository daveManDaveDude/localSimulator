# EA DTM source and local restore instructions

## Product and licence

The inspected product is the Environment Agency **LIDAR Composite DTM 1 m (2022)**. The [government catalogue page](https://www.data.gov.uk/dataset/01b3ee39-da3f-47b6-83da-dc98e73a461f/lidar-composite-dtm-2022-1m) describes the product-wide source range as 2000-06-06 through 2022-04-02. The tile XML sidecars for the two downloaded tiles state that their composite surveys run from 2003-02-14 through 2022-05-05. Those are different scopes: neither range describes a uniform survey date for every AOI cell.

The publisher provides the data under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) and requests this attribution:

> Environment Agency copyright and/or database right 2022. All rights reserved.

The tile XML `useLimit` contains that 2022 reuse instruction. An XML `idCredit` field elsewhere reports 2020; the conflict is recorded here and in the manifest, and the explicit reuse instruction is followed.

## Downloaded source files

The public [Environment Agency survey portal](https://environment.data.gov.uk/survey) was used on 2026-10-17 for the then-current historical 1,000 m square in EPSG:27700, bounds `[290608.9018176432, 64853.48350844931, 291608.9018176432, 65853.48350844931]` in west, south, east, north order. The portal map was used to find candidate 1 m composite tiles on both sides of northing 65000; the tile endpoints below returned the ZIPs. This is the earlier raster source-selection record; the exact 2 km cell result was re-run on 2026-10-20. `config/aoi.torquay-1km.json` and the saved historical AOI selection are available for validating or reproducing outputs from the earlier 1 km packages.

| Tile     | Portal download URL                                                                                       | Archive filename                        |             Size | SHA-256                                                            |
| -------- | --------------------------------------------------------------------------------------------------------- | --------------------------------------- | ---------------: | ------------------------------------------------------------------ |
| `SX96nw` | [SX9065 tile](https://environment.data.gov.uk/tiles/collections/survey/lidar_composite_dtm/2022/1/SX9065) | `lidar_composite_dtm-2022-1-SX96nw.zip` | 68,662,575 bytes | `22ac2c453ea79ca050a5c1b5a382ba1409a1f9f2c795ab274e6b78fffb4aecf6` |
| `SX96sw` | [SX9060 tile](https://environment.data.gov.uk/tiles/collections/survey/lidar_composite_dtm/2022/1/SX9060) | `lidar_composite_dtm-2022-1-SX96sw.zip` | 57,405,975 bytes | `46caf90e77dafc3bca95bf7cc0a81bc13601eb9593f7cb9818c25565d9020e6e` |

The archive request responses were HTTP 200 and their body lengths matched the downloaded archive sizes. The archive SHA-256 values are checked by `inspect-sources`. The complete archive-member lists and the GeoTIFF SHA-256 values are in [source-manifest.json](../data/source-manifest.json).

## Restore raw files on a clean clone

Raw publisher files are ignored by Git. From the repository root in PowerShell, create the local folders, download the exact portal archives, and expand each archive into its tile-named subdirectory:

```powershell
New-Item -ItemType Directory -Force data\raw\ea_dtm\SX96nw, data\raw\ea_dtm\SX96sw | Out-Null
Invoke-WebRequest -Uri 'https://environment.data.gov.uk/tiles/collections/survey/lidar_composite_dtm/2022/1/SX9065' -OutFile 'data/raw/ea_dtm/lidar_composite_dtm-2022-1-SX96nw.zip'
Invoke-WebRequest -Uri 'https://environment.data.gov.uk/tiles/collections/survey/lidar_composite_dtm/2022/1/SX9060' -OutFile 'data/raw/ea_dtm/lidar_composite_dtm-2022-1-SX96sw.zip'
Expand-Archive -LiteralPath 'data/raw/ea_dtm/lidar_composite_dtm-2022-1-SX96nw.zip' -DestinationPath 'data/raw/ea_dtm/SX96nw' -Force
Expand-Archive -LiteralPath 'data/raw/ea_dtm/lidar_composite_dtm-2022-1-SX96sw.zip' -DestinationPath 'data/raw/ea_dtm/SX96sw' -Force
Get-FileHash -Algorithm SHA256 'data/raw/ea_dtm/lidar_composite_dtm-2022-1-SX96nw.zip'
Get-FileHash -Algorithm SHA256 'data/raw/ea_dtm/lidar_composite_dtm-2022-1-SX96sw.zip'
```

Check the two hash values against the table before running analysis. Keep the extracted sidecars and metadata GeoPackages next to their TIFFs; the source manifest checks the ZIP member list and XML sidecar digests as well as the TIFF. The expected GeoTIFF paths are `data/raw/ea_dtm/SX96nw/SX96nw_DTM_1m.tif` and `data/raw/ea_dtm/SX96sw/SX96sw_DTM_1m.tif`.

## Measured raster properties

Rasterio 1.5.2 inspected each archive's GeoTIFF. Both are one-band `float32`, 1 m north-up grids in EPSG:27700, 5,000 × 5,000 pixels, with a NoData sentinel of `-3.4028234663852886e+38` and mask flags `nodata`. Their extents meet at N65000:

- `SX96nw_DTM_1m.tif`: E290000–295000 m, N65000–70000 m; SHA-256 `665441c4022f06044e17b501e6e1fe4bf3a2c25f87a7f2fea91c01c1054ba8e1`.
- `SX96sw_DTM_1m.tif`: E290000–295000 m, N60000–65000 m; SHA-256 `8438a544a9f4b4c675d72fd16824d5b75802899e7291edb585e98334da53211f`.

Their XML metadata explicitly says the elevations are metres referenced to Ordnance Survey Newlyn and names OSTN 15 and OSGM 15. This vertical reference is taken from the tile metadata; it is not inferred from EPSG:27700, which is the horizontal CRS. The XML also states a vertical accuracy of ±15 cm RMSE as a publisher product claim. It is not a local accuracy measurement.

The pinned Windows-tested Python runtime uses Python 3.13.7, Rasterio 1.5.2, NumPy 2.5.4, Matplotlib 3.11.2 and pyproj 3.8.0. `pipeline/requirements.txt` pins the complete installed dependency set; `pipeline/pyproject.toml` pins direct runtime and development dependencies.

The inventory scans each complete raster in bounded memory. It measured zero masked/NoData pixels and zero nonfinite pixels in both 25-million-pixel tiles. Full-tile elevation ranges and all measured metadata are recorded in the source manifest.

## Original 1 km AOI coverage method and TVW-007 result (2026-10-17)

Coverage analysis constructs an exact 1 m grid aligned to the configured AOI bounds. The grid has 1,000 columns × 1,000 rows and a denominator of 1,000,000 cells / 1,000,000 m². Each cell is sampled at its center by selecting the containing source pixel. The algorithm does not interpolate, extrapolate, reproject, or replace NoData with zero. It distinguishes uncovered centers, masked/NoData samples and nonfinite samples. Valid zero and negative elevations remain valid. If tiles overlap, inputs are sorted by path and the first valid source sample wins; overlap cells are counted once and differing overlapping values are reported.

The generated [coverage report](milestones/artifacts/TVW-007-coverage.json) records the result for the then-current 1 km candidate:

- 1,000,000 valid cells (100%).
- 0 uncovered, masked/NoData, nonfinite, or otherwise invalid cells.
- 0 m² missing on the defined 1 m analysis grid, below the 1% DTM threshold.
- AOI sample elevations from 29.529 m to 98.171 m; the exact configured center's containing-pixel sample is 47.620 m from `SX96nw_DTM_1m.tif`.

This is the EA DTM threshold result only. `selection_status` remains `selected_pending_coverage` and overall `coverage_status` remains `not_checked` because planned OSM/OS road and building feature counts are not inspected in TVW-007. The two source tiles and the measured preview are not loaded into the synthetic browser.

The actual north-up [DTM preview PNG](milestones/screenshots/TVW-007-ea-dtm-preview.png) has metre axes, a 250 m scale bar, the then-current AOI border, center marker, elevation colorbar, missing-cell display and EA attribution. It remains historical evidence and was preserved during the later size revision.

## Current 2 km candidate and resolution assessment (2026-10-20)

On 2026-10-20, the user authorized expanding the pending candidate to 2,000 m × 2,000 m around the same TQ1 4HN postcode centroid. The verified BNG center remains E `291108.9018176432`, N `65353.48350844931`; current bounds are `[290108.9018176432, 64353.48350844931, 292108.9018176432, 66353.48350844931]` in west, south, east, north order. The status remains `selected_pending_coverage` / `not_checked`.

The original 1 m Composite DTM raster inputs were checked again against this larger AOI without changing `data/source-manifest.json`. [`AOI-2km-1m-coverage.json`](milestones/artifacts/AOI-2km-1m-coverage.json) reports 4,000,000/4,000,000 1 m cell centers valid (4,000,000 m²), zero uncovered/masked/NoData/nonfinite cells, and an EA raster threshold result of `pass`. The exact center sample remains 47.620 m from `SX96nw_DTM_1m.tif`; the measured range is 12.288–104.356 m. The new [north-up 2 km preview](milestones/screenshots/AOI-2km-1m-preview.png) was generated from those measured samples and visually inspected. It shows the exact 2 km boundary, BNG metre axes, north arrow, 250 m scale, center marker and attribution. The older 1 km report and screenshot remain unchanged.

For the separate nominal-resolution assessment, the official [Environment Agency LIDAR DTM Time Stamped Tiles catalogue](https://www.data.gov.uk/dataset/8275e71e-1516-42a1-bb0c-4fa73807fe2b/lidar-dtm-time-stamped-tiles), updated 2026-04-07, documents 25 cm, 50 cm, 1 m and 2 m output resolutions. The publisher describes 5 km GeoTIFF tiles, metre elevations referenced to Ordnance Survey Newlyn and ±15 cm RMSE vertical accuracy; these are product-catalogue statements, not measurements of the 0.5 m polygons in this AOI. The product is under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) and requests `© Environment Agency copyright and/or database right 2020. All rights reserved.`

On 2026-10-20, an HTTP 200 OGC WFS 2.0.0 `GetFeature` request was made to the official [EA survey index service](https://environment.data.gov.uk/spatialdata/survey-index-files/wfs), layer `dataset-9f0fa3fc-a860-4729-adc9-47fe53f658d0:LIDAR_DTM_Time_Stamped_Extents`, using the exact 2 km EPSG:27700 bounding box and `count=1000`. The client captured the response at `2026-10-20T06:03:41Z`; its server response timestamp is `2026-10-20T06:03:41.185Z`. The bounded single page returned/matched 50 records in EPSG:27700, so the result is complete for this request. The saved response is 904,542 bytes, SHA-256 `cda7ce43af709ac2177cf000b404525d59476426ab22ad8a7404498d39a71de4`, at [`data/elevation-index/ea-dtm-time-stamped-2km-2026-10-20.geojson`](../data/elevation-index/ea-dtm-time-stamped-2km-2026-10-20.geojson). The exact URL, retrieval time, response timestamp/status/type, count/pagination policy, catalogue provenance and licence are in its companion `.source.json` file. The index returned 42 nominal 1 m features, 4 nominal 2 m features and 4 nominal 0.5 m features.

The four 0.5 m records all report survey date 2010-04-04 and `OSTN'02` / `OSGM'02`: `SX9064` (`DTM_F0129793_20100404_20100404`), `SX9164` (`DTM_F0129795_20100404_20100404`), `SX9165` (`DTM_F0129796_20100404_20100404`) and `SX9265` (`DTM_F0129797_20100404_20100404`). Their clipped polygons have a union area of 397,628.696 m², 9.9407% of the 4,000,000 m² AOI. The union counts overlaps once and excludes outside-AOI portions. The deterministic report is [`AOI-2km-resolution-index.json`](milestones/artifacts/AOI-2km-resolution-index.json).

This is index-footprint coverage only. No 0.5 m raster was acquired, downloaded, opened or tested for availability, cell validity or NoData; the measured 1 m raster check is a separate operation. Point-cloud spacing is a separate product property and was not assessed by this DTM output-resolution query. Existing ignored terrain/building/road browser packages still describe the earlier 1 km candidate and were left byte-for-byte unchanged; the updated AOI GeoJSON and this assessment do not regenerate or imply a 2 km browser scene. OSM/OS feature completeness and overall AOI approval remain pending.

The report is reproduced offline with the checked-in GeoJSON snapshot and sidecar. Tests use synthetic fixtures only and do not contact the WFS. An explicit online snapshot command is available when a new source response is needed:

```powershell
Push-Location pipeline
# Use a new output directory for each immutable capture.
.\.venv\Scripts\python.exe -m torquay_pipeline.cli capture-resolution-index --config ..\config\aoi.torquay.json --output-dir ..\data\raw\ea_dtm_time_stamped_index\capture-2026-10-20
.\.venv\Scripts\python.exe -m torquay_pipeline.cli assess-resolution-index --config ..\config\aoi.torquay.json --index ..\data\elevation-index\ea-dtm-time-stamped-2km-2026-10-20.geojson --source-metadata ..\data\elevation-index\ea-dtm-time-stamped-2km-2026-10-20.source.json
Pop-Location
```

The capture makes one request with `startIndex=0` (the service default) and `count=1000`, and is bounded to a 30-second request timeout and 16 MiB body. It verifies HTTP 200, JSON, CRS, exact request URL/bounds, and WFS `numberMatched == numberReturned == feature count`. If those counts differ, it refuses to save partial output; it does not silently paginate or claim completeness beyond the one AOI query. The raw response and provenance sidecar are written together to a new local ignored directory. The normal assessment reads only saved bytes and makes no network request.

## OpenStreetMap building footprints (TVW-009)

The building import uses the dated Geofabrik Devon extract downloaded on 2026-10-17. The source PBF is `devon-261016.osm.pbf`, from [Geofabrik's Devon download page](https://download.geofabrik.de/europe/united-kingdom/england/devon.html), with immutable file URL `https://download.geofabrik.de/europe/united-kingdom/england/devon-261016.osm.pbf`. Its size is 58,254,938 bytes, SHA-256 is `52942b39636e1cb002e5d78a004668996cb469ee9c9e9b9b93049c66b9ac2cd5`, and publisher MD5 is `c9c2018b331d8affd6b7be6464444bc5`. The PBF header reports generator `osmium/1.16.0`, replication timestamp `2026-10-16T20:21:21Z`, sequence `4932`, and bounds `[-4.752335, 50.11104, -2.881604, 51.30895]` in longitude/latitude order. The source-manifest OSM namespace records those values and the exact file URL. User names, user IDs and changeset IDs are omitted by this public Geofabrik extract.

The PBF is licensed under the [Open Database Licence 1.0 (ODbL)](https://www.openstreetmap.org/copyright). Credit `© OpenStreetMap contributors` and identify Geofabrik GmbH as the extract provider. The report and QA image link to the OSM copyright/licence page. Follow the ODbL and attribution terms before redistributing derived data; the local generated package is ignored by Git and is not published.

Raw PBF data is ignored under `data/raw/osm/`. To restore the exact recorded extract in PowerShell, use the direct dated URL, then verify it with the project CLI:

```powershell
New-Item -ItemType Directory -Force data\raw\osm | Out-Null
Invoke-WebRequest -Uri 'https://download.geofabrik.de/europe/united-kingdom/england/devon-261016.osm.pbf' -OutFile 'data/raw/osm/devon-261016.osm.pbf'
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli inspect-building-source
Pop-Location
```

The import checks the byte length, SHA-256, publisher MD5 and PBF header against `data/source-manifest.json` before reading OSM objects. It does not request the mutable `latest` alias. The projected AOI and 50 m source buffer use the pinned EPSG:1314 + EPSG:19916 coordinate operation with `always_xy=True`; its reported accuracy is 2 m. PROJ network downloads are disabled, and the preferred 1 m OSTN15 grid operation is unavailable locally. This caveat is included in the QA report; it does not change the coordinate values during later runs on the same pinned operation.

### TVW-009 measured OSM counts

The importer uses libosmium area assembly across the full PBF before applying its buffered spatial filter. It retains polygon and multipolygon footprints with `building=*`, excluding `building=no` and features tagged only with `building:part`. It rejects malformed or invalid geometry without `buffer(0)` repair, clips accepted geometry to the exact unbuffered AOI, and excludes final footprints below 1 m². Output vertices are quantized to 1 mm and stored as local XZ coordinates. `data/generated/buildings/torquay-poc-001/` contains the generated local package and is ignored by Git; `data/intermediate/osm/torquay-poc-001/` contains the raw-tag buffered intermediate and is also ignored.

The historical 1 km deterministic run produced 1,000 building features and 1,002 polygon components, with no exported interior rings. It recorded 17 `building=no` areas, 2,139 `building:part`-only areas, 37 areas outside the acquisition buffer, 192 areas outside the exact AOI, 3 below the 1 m² minimum, and 0 failed `multipolygon`/`boundary` assemblies. Five tagged relations (`7660489`, `9226944`, `9233555`, `9301051`, and `7726123`) have non-area `type=building` or `type=site`; they are intentionally skipped and separately identified with available member-way bounds, not described as failed building areas or AOI features. No candidate geometry was rejected as invalid, and the measured exact-duplicate and near-overlap counts were zero. These counts describe what the dated extract maps; they do not estimate feature completeness or describe the current 2 km candidate.

The clipped footprints total 172,969.138 m², or 0.172969 km² per square kilometre of candidate AOI. Height policy is `height` first (metres, or explicitly identified feet/inches), then a positive integer `building:levels × 3 m`, then 8 m visual default; usable values are clamped to 1–150 m. The actual export contains 998 defaults and 2 level-based estimates; no feature had a usable direct `height` tag. All OSM tagged heights are treated as unverified, `roof:height` and `min_height` are preserved only as tags, and they do not alter footprint extrusion height.

The actual [north-up building QA image](milestones/screenshots/TVW-009-buildings-preview.png) shows the extracted footprints, 1 km boundary, north cue, scale, centre and attribution. Three separated output features were then opened by OSM object ID and checked against the independently served OSM map at zoom 19: `way/208552436` (NE, postcode TQ1 4JD), `way/193285347` (NW, postcode TQ2 7NT), and `way/181620525` (SW, postcode TQ1 4UP). Each object page returned HTTP 200 and highlighted a `building=yes` outline in its surrounding street context; the captured pages include the OSM attribution. These are placement spot checks only, not evidence of survey accuracy, data completeness, or approval of the broader AOI. Screenshots are `milestones/screenshots/TVW-009-object-ne.png`, `TVW-009-object-nw.png` and `TVW-009-object-sw.png`.

## OSM highway roads (TVW-011)

TVW-011 reuses the exact dated Devon extract described above; it does not download a replacement or use a runtime map/API. The source is `data/raw/osm/devon-261016.osm.pbf`, acquired 2026-10-17 from [Geofabrik's Devon download page](https://download.geofabrik.de/europe/united-kingdom/england/devon.html) at the immutable [dated PBF URL](https://download.geofabrik.de/europe/united-kingdom/england/devon-261016.osm.pbf). The recorded source is 58,254,938 bytes, SHA-256 `52942b39636e1cb002e5d78a004668996cb469ee9c9e9b9b93049c66b9ac2cd5`, publisher MD5 `c9c2018b331d8affd6b7be6464444bc5`; its PBF replication timestamp is 2026-10-16T20:21:21Z, sequence 4932. Full source facts and the ODbL attribution requirement are in `data/source-manifest.json` and the TVW-011 QA report.

The pipeline reads complete ordered way locations from the verified PBF, applies its 50 m source filter, and clips exported centerlines and buffered display surfaces to the exact candidate square. It applies a documented class/visual-width policy and skips non-ground or ambiguous bridge, tunnel, layer and covered tags. These assumptions do not establish physical road width, elevation, connectivity or completeness. Geometries are projected with the same pinned EPSG:1314 + EPSG:19916 operation (reported accuracy 2 m); the preferred 1 m OSTN15 grid is unavailable and PROJ network access stays disabled. Roads are stored as local XZ vertices with references to the exact fixed triangles of the verified EA terrain grid, so the browser can drape their surfaces using the terrain sampler.

The measured run exported 198 unique highway ways and 198 clipped centerline parts: 171 vehicular streets, 0 cycleways and 27 paths. Those features form 200 separate clipped ribbon components after width buffering. The published mesh has 72,098 vertices and 98,238 terrain-conforming triangles. Two triangles whose vertices collapse under Float32 conversion are omitted; their combined area is 4.35e-10 m², within the explicit 1e-6 m² limit in QA. The run also counted 193,139 ways outside the acquisition buffer, 5,589 excluded class/surface cases, 6,996 bridge/tunnel/ambiguous-ground exclusions, and 2,909 area surfaces; 49 filtered ways had no clipped line part. No duplicate IDs, missing locations, incomplete way IDs or invalid transformed geometries were recorded. Mapped counts describe this extract only and do not prove coverage. The AOI remains `selected_pending_coverage` / `not_checked`; broader M2 feature checks remain pending. TVW-012's bounded independent map comparison is recorded in [the TVW-012 report](milestones/TVW-012.md).

The generated package `data/generated/roads/torquay-poc-001/` and intermediate raw node/tag records are ignored by Git. To restore the exact source, follow the OSM source restoration steps above, then run the `inspect-road-source`, `import-roads`, `validate-roads`, `preview-roads` and `publish-roads` commands in the README. The publisher writes only the `roads/` child inside the ignored Vite public package; it verifies the dated source and writes a staged package only after validation. Browser credit is `© OpenStreetMap contributors`, with Geofabrik GmbH identified as extract provider and a link to the ODbL. The standalone actual-source preview is `milestones/screenshots/TVW-011-roads-preview.png`.

## OS OpenMap–Local comparison raster (TVW-012)

The TVW-012 comparison uses an independent April 2026 Ordnance Survey OS OpenMap–Local GeoTIFF Full Colour source. The archive was selected from the public OS Data Hub portal on 2026-10-19 at 11:39:33 UTC for the 100 km National Grid square SX. The portal advertised 349.41 MB; the HTTP response was 200 with 349,405,146 bytes, matching the archive and a range-probe total. The source archive SHA-256 is `d9a01900c4dd5c26af50d6aed79f419a1957acf4167aedef97bb905ffcdff853`; ZIP CRC verification passed across 227 members. The selection was comparison-only and not copied into the production world.

The exact archive member paths, CRCs, byte lengths, SHA-256 values, Rasterio properties, OS portal request/redirect, Azure timestamps, licence text, and full attribution record are in [data/comparison-source-manifest.json](../data/comparison-source-manifest.json). The two needed raster members are `OS OpenMap Local (Full Colour Raster) SX/data/SX96NW.tif` (2,620,996 bytes; SHA-256 `fec960fdb94a2e2cc3cdcfa201c35c6070871ae7c86b6c80617bad550799ae1a`) and `OS OpenMap Local (Full Colour Raster) SX/data/SX96SW.tif` (2,248,452 bytes; SHA-256 `546c7a7c60b8c372c35dfd7ad21ddbbd71437ba45966235f6a09264352181838`). Both are palette GeoTIFFs in EPSG:27700, 1 m pixels, 5000 × 5000, AREA_OR_POINT=Area. The source tiles straddle northing 65000; both were required to cover the 1 km AOI and comparison windows. Their source bounds are respectively E290000–295000/N65000–70000 and E290000–295000/N60000–65000.

The source is supplied under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Its archive `doc/licence.txt` explicitly requests `Contains Ordnance Survey data © Crown copyright and database right 2026`. That exact year-specific credit appears in the report panels and browser evidence alongside separate Environment Agency and OpenStreetMap/Geofabrik credits. Raw archive and selected members belong under ignored `data/raw/comparison/os_openmap_local/`; only the attributed comparison evidence and metadata are tracked. Do not redistribute the source raster as a viewer asset.

To restore the comparison source, download the exact archived file from the recorded `requestUrl` in the comparison source manifest into `data/raw/comparison/os_openmap_local/openmaplocal-2026-04-sx-geotiff.zip` and verify its recorded size and SHA-256. Extract only the four bound raster/licence/readme members to the manifest's relative paths; the source verifier then checks the extracted bytes against the exact ZIP members:

```powershell
New-Item -ItemType Directory -Force data\raw\comparison\os_openmap_local | Out-Null
Invoke-WebRequest -Uri 'https://api.os.uk/downloads/v1/products/OpenMapLocal/downloads?area=SX&format=GeoTIFF&subformat=Full+Colour&redirect' -OutFile 'data/raw/comparison/os_openmap_local/openmaplocal-2026-04-sx-geotiff.zip'
Get-FileHash -Algorithm SHA256 'data/raw/comparison/os_openmap_local/openmaplocal-2026-04-sx-geotiff.zip'
@'
from pathlib import Path
from zipfile import ZipFile

root = Path("data/raw/comparison/os_openmap_local")
archive_path = root / "openmaplocal-2026-04-sx-geotiff.zip"
members = {
    "OS OpenMap Local (Full Colour Raster) SX/data/SX96NW.tif": "selected-members/SX96NW.tif",
    "OS OpenMap Local (Full Colour Raster) SX/data/SX96SW.tif": "selected-members/SX96SW.tif",
    "OS OpenMap Local (Full Colour Raster) SX/doc/licence.txt": "selected-members/licence.txt",
    "OS OpenMap Local (Full Colour Raster) SX/readme.txt": "selected-members/readme.txt",
}
with ZipFile(archive_path) as archive:
    for member, relative in members.items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(archive.read(member))
'@ | pipeline\.venv\Scripts\python.exe -
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli inspect-comparison-source
.\.venv\Scripts\python.exe -m torquay_pipeline.cli compare-alignment
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-alignment-report
Pop-Location
```

The verified report is [TVW-012](milestones/TVW-012.md), with per-spot OS reference, registered overlay, OSM-only panel, and actual 3D viewer screenshots. Second Avenue / Main Avenue, Pencorse Road / Audley Avenue, and Teignmouth Road / Snowberry Close are qualitative placement passes; no numeric offset was measured. St Vincent’s Road / Chapel Court is retained as a prior inconclusive candidate and is not counted. The overall AOI is still `selected_pending_coverage` / `not_checked`; three checks do not establish coverage or approval.

## TVW-014 verified local-demo sources

The M7 restored-source smoke reuses only the already inspected inputs listed in `data/source-manifest.json`: the two EA DTM archive/tile pairs `lidar_composite_dtm-2022-1-SX96nw.zip` and `lidar_composite_dtm-2022-1-SX96sw.zip`, plus the dated Geofabrik extract `devon-261016.osm.pbf`. Their publisher links, acquisition dates, sizes, checksums, archive members, product-vintage notes, licences and required attribution remain recorded in the manifest and source sections above. The source paths stay under ignored `data/raw/ea_dtm/` and `data/raw/osm/`; the generated terrain, building and road packages stay under ignored paths and are not distributed in the synthetic share build.

TVW-014 does not download or replace any source. In an isolated checkout it copies the exact locally retained files to the documented ignored paths, checks hashes before running `inspect-sources` / `build-terrain`, building validation/import/publication, and road validation/import/publication. The resulting local browser packages are then loaded through the production preview only. The terrain is Environment Agency data with Newlyn elevation metadata and the publisher-required 2022 attribution; the optional building and road layers are OSM-derived, tagged/estimated per their contracts, with © OpenStreetMap contributors and Geofabrik credit under ODbL. The OS OpenMap–Local raster remains comparison evidence only.

For clean-clone startup, the M7 smoke uses the tracked synthetic fixtures and the `build:share` mode, with no GIS inputs. For actual source identities, regeneration outputs, package hashes, and per-workload runtime measurements, see the [TVW-014 handback](milestones/TVW-014.md) and companion benchmark artifacts. Neither those source checks nor mapped feature counts change the AOI's `selected_pending_coverage` / `not_checked` state.
