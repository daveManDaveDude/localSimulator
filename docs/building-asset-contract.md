# OSM building footprint asset contract

**Version:** 1 · **Status:** TVW-009 package and QA artifact; awaiting independent review. The browser does not load this package. Building rendering and terrain-following bases belong to TVW-010.

## Files and provenance

The generated local package is `data/generated/buildings/torquay-poc-001/manifest.json`, `buildings.json`, and the package-local `qa.json`. The external QA report and preview are `docs/milestones/artifacts/TVW-009-buildings-qa.json` and `docs/milestones/screenshots/TVW-009-buildings-preview.png`; the package-local and external QA reports are byte-identical. The manifest binds `qa.json` by relative path, exact byte length, and SHA-256. The raw-tag buffered intermediate is `data/intermediate/osm/torquay-poc-001/assembled-buffered.geojson`. Raw and generated data are ignored by Git; the small source manifest and QA evidence are tracked. Before publishing and during `validate-buildings`, the package validator checks payload and QA integrity, exact configured AOI ring/bounds, current local terrain manifest/origin/elevation/heightfield identity, dated PBF provenance, operation and processing policy, QA structure, and each feature's height/geometry fields. It recomputes method, confidence, parsed value/unit, clamped height, and fallback reason from retained tags using the shared resolver and effective package policy. QA method and clamp distributions and the minimum, maximum, and mean height summary must match the validated features. Numeric values must be finite JSON numbers; booleans are rejected where a number is required. Invalid or missing nested fields produce a contextual validation error.

The manifest binds the asset to the exact EA terrain package by world ID, BNG origin including elevation, grid dimensions, `heightfield.f32` path, byte length and SHA-256, and vertical reference. It also records the approved candidate AOI bounds and closed WGS84 boundary, OSM/Geofabrik source URL, source filename, acquisition date, extract timestamp, byte size, SHA-256 and publisher MD5, licence and attribution, the full pinned coordinate operation definitions/accuracy/grid caveat, generator version and Python/GEOS dependency versions. The effective height and geometry policies are recorded with version, numeric settings, unit/precedence, clipping buffer, minimum area, quantization, winding and duplicate/overlap rules. Detailed source values and restoration instructions are in [data-sources.md](data-sources.md) and `data/source-manifest.json`.

## Coordinates and geometry

All lengths and coordinates are metres. The footprint payload uses local XZ positions relative to the same center as the terrain package:

```text
x = BNG easting - origin easting
z = origin northing - BNG northing
```

Thus +X is east, +Z is south, north is -Z, and +Y is up. No absolute BNG coordinate is repeated for every footprint vertex. `geometry` is represented as `MultiPolygon`, with closed exterior rings and optional closed interior rings. The canonical stored XZ exterior winding is counter-clockwise and hole winding is clockwise. Source polygons are validated without silent geometry repair, clipped to the exact AOI, rounded to 1 mm, and validated again. Footprint area is measured in square metres from the stored, millimetre-quantized coordinates.

Each building record includes its OSM way or relation ID, version and timestamp; local polygon geometry; footprint area; clipping flag and quality flags; duplicate references; selected raw tags; and a height value with method, confidence, raw input, parsed value/unit, clamp state, and fallback reason. Tag subset includes `building`, `building:part`, `building:use`, `height`, `building:levels`, `min_height`, `roof:height`, `roof:shape`, name/address fields, and relation type. The import selects polygon `building=*` features, excludes `building=no`, and counts/excludes features tagged only with `building:part`. Areas are assembled before filtering so relation multipolygons keep their holes and member geometry.

## Height policy

`height` takes precedence when it contains one positive, unambiguous metric value or an explicitly marked feet/inches value. Otherwise a positive integer `building:levels` is multiplied by the configured 3 m per level. If neither is usable, the configured 8 m visual default is used. The final value is clamped to the configured 1–150 m range. Ambiguous or malformed values such as ranges are not guessed. Height sources and estimates are recorded separately; OSM values are tagged-but-unverified. `roof:height` and `min_height` are retained as raw tags but are not added to the total building height. TVW-010 must sample terrain for building bases; this package does not derive bases, mesh vertices, or terrain-dependent geometry.

## Source and licence

The current package uses the dated `devon-261016.osm.pbf` regional extract and does not fetch data at runtime. Transformations use the pinned EPSG:1314 + EPSG:19916 operation, longitude/latitude axis order explicitly normalized, 2 m reported accuracy, and PROJ network downloads disabled. The preferred 1 m OSTN15 grid operation is noted as unavailable. This stated limitation is part of provenance, not a survey-accuracy claim.

Credit `© OpenStreetMap contributors`, link to the [OpenStreetMap copyright and ODbL page](https://www.openstreetmap.org/copyright), and credit Geofabrik GmbH as extract provider. The local package is not published. Review ODbL obligations before redistributing any derived data.

## QA meaning

The QA report reconciles source object tags, assembled areas, filtering and clipping counts; records exclusions, unsupported non-area building relations separately from true multipolygon/boundary area-assembly failures, invalid geometry, small footprints, exact duplicates and near overlaps; and summarizes component/hole counts, footprint area, density, heights and map-check candidates. Unsupported relation records include their OSM IDs, relation type, skip reason and available member-way location bounds as evidence only, not as asserted footprints. Density is the mapped OSM footprint area divided by the candidate AOI area; it is not a completeness estimate. The output remains associated with `selection_status: selected_pending_coverage` and `coverage_status: not_checked`. Three object outlines have been compared against independently served OSM context as placement spot checks. Road and other feature checks remain outstanding.

For source and QA commands, see the TVW-009 section in [README.md](../README.md). The package remains disconnected from the browser until TVW-010 is separately authorized and reviewed.
