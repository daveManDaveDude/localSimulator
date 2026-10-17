# EA DTM source and local restore instructions

## Product and licence

The inspected product is the Environment Agency **LIDAR Composite DTM 1 m (2022)**. The [government catalogue page](https://www.data.gov.uk/dataset/01b3ee39-da3f-47b6-83da-dc98e73a461f/lidar-composite-dtm-2022-1m) describes the product-wide source range as 2000-06-06 through 2022-04-02. The tile XML sidecars for the two downloaded tiles state that their composite surveys run from 2003-02-14 through 2022-05-05. Those are different scopes: neither range describes a uniform survey date for every AOI cell.

The publisher provides the data under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) and requests this attribution:

> Environment Agency copyright and/or database right 2022. All rights reserved.

The tile XML `useLimit` contains that 2022 reuse instruction. An XML `idCredit` field elsewhere reports 2020; the conflict is recorded here and in the manifest, and the explicit reuse instruction is followed.

## Downloaded source files

The public [Environment Agency survey portal](https://environment.data.gov.uk/survey) was used on 2026-10-17. The AOI used for source selection is the reviewed 1,000 m square in EPSG:27700, bounds `[290608.9018176432, 64853.48350844931, 291608.9018176432, 65853.48350844931]` in west, south, east, north order. The portal map was used to find candidate 1 m composite tiles on both sides of northing 65000; the tile endpoints below returned the ZIPs. The committed AOI polygon is available at [aoi-selection.geojson](aoi-selection.geojson). Portal map selection is recorded as candidate discovery; the exact coverage result comes from reading the raster pixels against the AOI bounds.

| Tile | Portal download URL | Archive filename | Size | SHA-256 |
| --- | --- | --- | ---: | --- |
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

## AOI coverage method and current result

Coverage analysis constructs an exact 1 m grid aligned to the configured AOI bounds. The grid has 1,000 columns × 1,000 rows and a denominator of 1,000,000 cells / 1,000,000 m². Each cell is sampled at its center by selecting the containing source pixel. The algorithm does not interpolate, extrapolate, reproject, or replace NoData with zero. It distinguishes uncovered centers, masked/NoData samples and nonfinite samples. Valid zero and negative elevations remain valid. If tiles overlap, inputs are sorted by path and the first valid source sample wins; overlap cells are counted once and differing overlapping values are reported.

The generated [coverage report](milestones/artifacts/TVW-007-coverage.json) records the current result:

- 1,000,000 valid cells (100%).
- 0 uncovered, masked/NoData, nonfinite, or otherwise invalid cells.
- 0 m² missing on the defined 1 m analysis grid, below the 1% DTM threshold.
- AOI sample elevations from 29.529 m to 98.171 m; the exact configured center's containing-pixel sample is 47.620 m from `SX96nw_DTM_1m.tif`.

This is the EA DTM threshold result only. `selection_status` remains `selected_pending_coverage` and overall `coverage_status` remains `not_checked` because planned OSM/OS road and building feature counts are not inspected in TVW-007. The two source tiles and the measured preview are not loaded into the synthetic browser.

The actual north-up [DTM preview PNG](milestones/screenshots/TVW-007-ea-dtm-preview.png) has metre axes, a 250 m scale bar, the exact AOI border, center marker, elevation colorbar, missing-cell display and EA attribution. The preview is generated from the same sampled grid as the report.
