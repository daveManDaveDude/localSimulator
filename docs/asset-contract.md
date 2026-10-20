# Local terrain asset contract, version 1

TVW-004/005 define the browser-side boundary between a local manifest and a binary heightfield. TVW-008 extends the discriminated v1 contract to fully attributed real EA terrain while retaining the synthetic format and decoder. Manifest validation, byte decoding and loading remain independent of Three.js. Synthetic terrain remains the default; the analytic M0 scene remains available at `/?world=m0`.

## Manifest fields

`formatVersion` is the integer `1`. `id` and `name` are non-empty strings. `worldType` selects one of two validated variants: `synthetic` with `sourceCrs: "LOCAL_SYNTHETIC"`, or `real` with `sourceCrs: "EPSG:27700"`. Both require `axisConvention: "+X east, +Y up, -Z north"`. No other CRS or world type is accepted.

`origin` has finite `eastingM`, `northingM`, and `elevationM` numbers. Synthetic fixtures use fictional zero values; these are local placeholders, not projected coordinates. `extentM` has positive finite `width` and `depth` values in metres.

`heightfield` contains:

- A safe package-relative `path` to the binary asset.
- Integer `columns` and `rows`, each at least 2, and positive finite `spacingM`.
- `rowOrder: "north-to-south"`, `byteOrder: "little-endian"`, and `encoding: "float32"`.
- `valueMeaning: "world Y in metres relative to origin elevation"`.
- A 64-character hexadecimal `sha256` of the raw binary bytes.

The real EA manifest also records `heightfield.byteLength`; it must equal `columns × rows × 4`. This lets validation reject inconsistent byte metadata before a browser requests the binary.

The horizontal dimensions must satisfy `(columns - 1) × spacingM = width` and `(rows - 1) × spacingM = depth`. Computed extents must remain finite before comparison. Comparisons use a relative tolerance of `1e-9 × max(1, |declared extent|, |computed extent|)` to absorb floating-point representation error. The product `columns × rows` must be safe integer arithmetic and cannot exceed **16,000,000 samples** (64 MB of Float32 data) before the decoder allocates its output.

For synthetic worlds, `provenance` requires `kind: "synthetic"`, a non-empty generator name and version, and a note. Optional `buildings` and `roads` strings are validated as safe local paths only; no payload schemas are defined here.

Real worlds require `provenance.kind: "real"`, generator name/version, publisher, product, licence and licence URL, attribution, vertical reference, publisher catalogue URL and product-wide survey period. The manifest preserves the XML `useLimit`/`idCredit` copyright-year conflict. `coordinateOperation` records the pinned EPSG:1314 + EPSG:19916 operation identity, complete normalized PROJ definition, reported 2 m accuracy, selected-grid use, `best_available`, preferred missing grid name and the `PROJ_NETWORK=OFF` caveat. The browser validator compares every normalized pipeline parameter against the complete pinned operation definition; it does not perform coordinate transformations. Each source record includes archive/TIFF/XML identity, sizes, SHA-256 hashes, CRS, affine transform, bounds, dimensions, resolution, data type and NoData value. The generated TVW-008 manifest records both Environment Agency archives and tile-specific XML provenance. `provenance.selectionStatus` remains `selected_pending_coverage` and `coverageStatus` remains `not_checked`; the real DTM analysis does not approve the broader AOI. Resampling and no-fill behavior are explicit provenance fields, with QA error maxima recorded separately for source resampling and Float32 quantization.

Real-world `aoi.boundaryWgs84` contains the generated polygon exterior ring copied from `docs/aoi-selection.geojson`. Its `crs` is `EPSG:4326`, `coordinateOrder` is `longitude-latitude`, `geometryType` is `Polygon`, and `ring` is the ordered list of `[longitude, latitude]` positions: the four candidate corners followed by the first point repeated to close the ring. For this candidate the ring matches the reviewed EPSG:27700 `boundsM`; Python verifies the source GeoJSON ring against the configured bounds before publishing, and TypeScript validates shape, finite/ranged coordinates, closure, and exact candidate-ring/bounds consistency without transforming coordinates. `aoi` also includes the configured WGS84 postcode centroid and source metadata, projected center, reviewed 1,000 m × 1,000 m EPSG:27700 bounds, and the same pending statuses. Validation checks that the bounds, extent, sample dimensions, spacing, origin and configured anchor agree. The real-world HUD exposes accessible links to the publisher catalogue and licence.

## Paths, decoding, and loading

Asset paths consist of non-empty ASCII letter/digit/dot/underscore/hyphen segments separated by `/`. Absolute paths, schemes, backslashes, percent escapes, query/hash characters, and `.` or `..` path segments are rejected. The loader also confirms that a resolved heightfield URL remains in the manifest directory and origin.

The decoder requires exactly `rows × columns × 4` bytes. It reads a little-endian Float32 at each row-major offset into an owned `Float32Array`. Row zero is the northern edge; subsequent rows move south. Non-finite values fail with sample index, row, and column. Finite negative and zero values are valid. The decoder does not apply origins, interpolate, sample, or build geometry.

The loader checks manifest HTTP status and JSON parsing, validates the complete manifest before requesting binary data, checks binary HTTP status, verifies its SHA-256 with Web Crypto, then decodes the bytes. Failures identify the stage and asset involved. Browser fetch is the default; tests inject a fetch function. The default heightfield viewer loads the local synthetic package. The explicit historical 1 km profile loads `/worlds/torquay-poc-001/` directly. The current 2 km profile first requests the fixed same-origin `/worlds/torquay-poc-001-2km/ready.json`; it then validates the bounded readiness document and content-addressed inventory before requesting any terrain, building, or road runtime asset. Missing or invalid readiness stops the load before those package requests. The inventory allowlists the runtime files and binds each file's byte length and SHA-256; the loader pins the resulting release ID for the whole scene and compares each fetched runtime file against that inventory. Both routes are selected through a fixed application registry and bind the terrain/building/road assets to the selected profile, AOI and terrain identity; arbitrary manifest URLs and cross-profile layer mixing are rejected. The current 2 km package has no overview asset, so its overview UI reports unavailable rather than fetching the historical 1 km overview. The app displays the real publisher attribution and Newlyn vertical reference, and labels sample heights as local relative heights and Newlyn elevations. `/?world=m0` bypasses the loader and opens the retained analytic M0 demo.

## Reproducible fixture

`public/worlds/synthetic-heightfield/` contains a fictional 3 × 3 fixture with 2 m spacing and a 4 × 4 m extent. Its row-major values are `[-2.5, 0, 1.25, 10, 11.5, 12, 20, 21, 22.75]`. The manifest has local zero origins, marks its source and provenance synthetic, and includes the binary checksum. It is retained for decoder and loader tests.

`public/worlds/synthetic-terrain-demo/` is a separate 25-column × 19-row fixture with 2 m spacing and a 48 × 36 m extent. Its deterministic generator combines a gentle planar slope, a Gaussian hill and a narrow ridge. It records generator `scripts/generate-synthetic-heightfield.mjs`, version `1.0.0`, synthetic provenance and the binary SHA-256 `cf57dd9d5551eaad413c5e1ea43c8d2f9acb709c410bb016e8fbf7afd95dcd3b` (1,900 bytes). The formula and all samples are fictional and are not measurements of Torquay. Neither fixture contains geographic coordinates, buildings or roads.

## Terrain-grid and mesh interpretation

The renderer places the first sample at the north-west corner and the final sample at the south-east corner. For a grid with width `W`, depth `D`, and spacing `s`, sample `(row, column)` maps to `x = column × s − W/2`, `y = height[row × columns + column]`, and `z = row × s − D/2`. Thus columns increase east on +X, rows move south on +Z, and row zero is north on −Z. Heights are world Y values relative to `origin.elevationM`; the renderer does not add an elevation offset. For real terrain, the HUD reports both this relative local height and the corresponding Newlyn value (`origin.elevationM + local height`).

Each cell uses a fixed diagonal from NE to SW. For `a=NW`, `b=NE`, `c=SW`, and `d=SE`, indices are `(a,c,b)` and `(b,c,d)`, which wind upward. The sampler interpolates those exact two planes: when cell fractions `u+v ≤ 1`, `h = a + (b−a)u + (c−a)v`; otherwise `h = d + (c−d)(1−u) + (b−d)(1−v)`. Maximum-edge queries use the final cell with fraction 1; non-finite queries and positions outside the finite extent return `null`, with no extrapolation.

Regenerate both files deterministically with:

```powershell
npm run generate:synthetic-heightfield
```

The generator reproducibly writes both fixture packages as little-endian Float32 bytes and derives each manifest checksum from those exact bytes. Its version is recorded in both manifests. Unit tests verify fixture dimensions and hashes, row orientation, mesh normals/winding, and triangle-consistent sampling.

## Optional OSM road package (TVW-011)

The road package is a separately versioned local asset under `/worlds/torquay-poc-001/roads/`; it is requested only with `?world=torquay-poc-001&roads=1`. A combined building-and-road view adds `&buildings=1`. It is never fetched for the synthetic default, M0, terrain-only or buildings-only route. Its Python package and browser publication are derived from the exact local PBF and verified EA terrain package; no raw PBF or extracted tags are copied into the public output.

The unknown-safe browser schema binds package ID, source manifest and PBF digest/header, pinned coordinate operation and its unavailable preferred-grid caveat, exact pending AOI ring/bounds, terrain manifest digest/heightfield/grid identity, width/ground/clip/triangulation policies, counts, and package-local asset lengths/SHA-256. Python package validation additionally re-derives the output from the verified source before accepting it. QA counts and landmark placement contexts are source-backed; they cannot establish completeness or certify road position against a survey.

`roads.json` retains source way identity/version/timestamp, class and selected raw tags, visual full-width estimate, clipping provenance, excluded vertical-ground rules, and clipped centerline parts. Display batches are already-unioned and priority-partitioned polygons represented as local `[x,z]` vertices and indexed triangles, with the exact owning terrain `cellRow`, `cellColumn` and fixed `triangle` for every triangle. The browser requires each reference to match the terrain grid cell and triangle, samples every vertex using the shared exact `TerrainGrid` sampler, and applies the 0.05 m display offset. Python omits only triangles whose three horizontal vertices collapse to fewer than three distinct Float32 positions; QA records the count and omitted area. The historical 1 km profile caps this total at 1e-6 m². The expanded current 2 km profile uses a separately validated 2e-5 m² cap to account for the larger number of terrain-cell intersections and Float32 coordinate spacing; its report includes the actual omitted area and triangle count. These limits affect only degenerate sub-Float32 surface triangles, not source feature selection. These are derived visual road surfaces, not measured road elevations, an engineered junction network, or routable graph. No repair, bridge elevation, lanes, traffic or road furniture is implied.

The publisher validates against the local terrain and publishes byte-identical manifest, road payload and QA files only into the ignored `roads/` child directory. The renderer owns and disposes its geometry and materials independently of terrain and buildings. Hiding the layer preserves validated way-count/width metadata; load or validation errors leave the terrain usable and expose retry, terrain-only and synthetic recovery. `build:share` copies tracked synthetic public fixtures but excludes the entire real `torquay-poc-001/` parent.
