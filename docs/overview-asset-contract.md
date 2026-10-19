# Offline geographic overview asset contract

The M8 overview is a separate, derived package. It does not change the existing terrain, road or building render packages and is not committed with its source-derived geometry.

## Files and commands

The generator writes `data/generated/overview/manifest.json` and `features.geojson`. Publication copies those two files byte-for-byte to `public/worlds/torquay-poc-001/overview/`. Both locations are ignored. The share build omits the complete `public/worlds/torquay-poc-001/` parent.

Run these commands from `pipeline` after restoring and validating the exact input packages:

```powershell
.\.venv\Scripts\python.exe -m torquay_pipeline.cli build-overview
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-overview
.\.venv\Scripts\python.exe -m torquay_pipeline.cli publish-overview
```

`build-overview` defaults to the checked-in AOI configuration and the published local terrain, road and building packages. It accepts `--terrain-dir`, `--roads-dir`, `--buildings-dir`, `--aoi-config`, `--aoi-geojson`, `--source-manifest`, `--layers` and `--output-dir`. The required `aoi` layer can be built without optional features using `--layers aoi`. `validate-overview` accepts `--package-dir` and the same source/input overrides. It rebuilds the derivative in memory and compares the full manifest and GeoJSON bytes. `publish-overview` accepts `--package-dir` and `--output-dir`; it revalidates inputs, stages the copy and preserves an earlier good output if installation fails. None of these commands downloads or replaces source inputs.

## Manifest and geometry

The version 1 manifest identifies world `torquay-poc-001`, `worldType=real`, `format=RFC 7946`, the included layer set, AOI selection/coverage status, BNG bounds and centre, the verbatim recorded WGS84 AOI boundary, and Python-derived geographic centre/fit bounds. It contains terrain manifest/heightfield identity, and identity records for each included optional layer: its manifest, geometry payload and QA paths, byte lengths and SHA-256 values, plus source extract metadata. It also records the exact coordinate operation, its stated 2 m accuracy, selected-grid status and missing preferred-grid caveat, coordinate precision/round-trip limits, generator version, feature and coordinate counts, local URLs, licences and required attributions.

GeoJSON uses longitude/latitude order. It contains one AOI Polygon, clipped roads as separate-part MultiLineStrings, and buildings as MultiPolygons preserving their component exteriors and holes. Stable namespaced source identities are retained with only the properties needed by the map. Coordinates are finite, rounded to the documented fixed precision, checked against the candidate boundary and assigned deterministic feature/property order. Ring winding follows RFC 7946. Disconnected parts are not joined, geometry is not repaired/simplified, and omitted road centerlines are counted in the manifest.

The exporter applies the recorded local convention `E = originE + x`, `N = originN - z`. Conversion is performed in Python using the pinned EPSG:1314 + EPSG:19916 operation with explicit XY order and PROJ networking disabled. A numerical inverse/forward round-trip check of at most 0.02 m is a serialization-consistency check, not an absolute geodetic-accuracy claim. The operation reports 2 m; the preferred OSTN15 grid operation is unavailable locally. The overview never reprojects local coordinates in TypeScript.

The serialized package has deterministic bytes and no generation timestamp in its content identity. Manifest size is limited to 128 KiB, GeoJSON to 8 MiB, features to 10,000 and positions to 250,000. The exporter rejects unsafe paths, nested input/output paths, mismatched source/package/terrain identity, invalid geometry and exceeded size/count limits. It stages output and rolls back replacement failures. Validation regenerates and byte-compares the declared derivative before publication.

## Browser validation and display

The browser fetches only the fixed same-origin manifest and its safe relative GeoJSON path. It enforces size while reading the stream (including absent or false `Content-Length`), exact byte length and SHA-256 before JSON parsing. Unknown manifest and GeoJSON input is validated before use: coordinate domains, counts, roles, IDs, ring closure/winding, bounds, source metadata, terrain identity and optional package identity must be consistent. Stale optional road/building identities are excluded with an explanatory rebuild message; the viewer does not load those packages from the overview loader.

MapLibre GL JS is imported only after opening the panel on a real terrain route. Its CSS and Vite-bundled worker are same-origin package assets. The map uses an inline version 8 style with a local GeoJSON source, background/fill/line layers, fixed Mercator projection, fixed north-up bearing and pitch, and no animation. It contains no remote style, tiles, sprites, fonts, telemetry or geolocation. Map movement and camera-follow behavior are disabled. The panel provides a north cue, metric scale, layer legend and “no live camera position” explanation. MapLibre licence notice remains visible; OSM/Geofabrik attribution appears when a road or building layer is actually shown. The EA catalogue/licence is identified separately as context only; the overview does not render the EA heightfield.

Opening a synthetic world shows a geographic-overview-unavailable status without importing MapLibre, issuing an overview request or assigning geographic coordinates. Missing/corrupt package, identity mismatch and WebGL errors have distinct recovery messages; optional map failure leaves the main terrain available. Closing or replacing the world aborts in-flight work, removes the MapLibre instance and disposes its observer/listeners. Reopen creates one fresh map canvas.

## Limits

The map is a fixed 2D display of the local derived GeoJSON. It has no live camera marker, terrain raster, terrain shading, pan/zoom/rotation, routing, teleportation or independent map-alignment result. The displayed feature counts do not prove feature completeness. The candidate AOI remains `selected_pending_coverage` / `not_checked`; this package does not approve or freeze it.
