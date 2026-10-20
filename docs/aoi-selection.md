# AOI selection candidate

**Status:** `selected_pending_coverage`<br>
**Coverage:** `not_checked` — EA DTM cell coverage is measured separately from the broader AOI gate. OSM/OS feature counts remain unchecked, so overall AOI coverage is still pending.

## Anchor provenance

- Postcode: **TQ1 4HN**
- WGS84 centroid: longitude `-3.536013`, latitude `50.477853`
- Meaning: Postcode centroid; not a property or survey point.
- Provider: [Postcodes.io](https://api.postcodes.io/postcodes/TQ1%204HN) (quality 1); retrieved 2026-10-17
- Licence: OS OpenData licence (provider documentation)

## Candidate square

- Selection profile: `current_2km`
- Projected centre: `291108.902 m E, 65353.484 m N` (EPSG:27700)
- Bounds `[west, south, east, north]`: `[290108.902, 64353.484, 292108.902, 66353.484] m`
- Dimensions: `2000.0 m × 2000.0 m`
- This is a derived postcode-centred candidate. It is not coverage-approved or frozen.

## Transformation evidence

PROJ network access was disabled. The tool pins EPSG operation 1314 (OSGB36 to WGS 84 (6)) plus EPSG operation 19916 (British National Grid) by operation identity, so local grid availability cannot reorder or replace the selected 2 m fallback.

- WGS84 → BNG operation: `EPSG:1314 + EPSG:19916` — Inverse of OSGB36 to WGS 84 (6) + British National Grid (with axis order normalized for visualization)
  - Reported accuracy: 2.000 m; chosen operation uses grids: `false`; selected EPSG:1314 + EPSG:19916 operation uses no grid files.
  - Preferred operation set best available: `false`; missing preferred operations/grids: Inverse of OSGB36 to WGS 84 (9) + British National Grid (uk_os_OSTN15_NTv2_OSGBtoETRS.tif available=false).
- BNG → WGS84 operation: `EPSG:1314 + EPSG:19916` — Inverse of British National Grid + OSGB36 to WGS 84 (6) (with axis order normalized for visualization)
  - Reported accuracy: 2.000 m; chosen operation uses grids: `false`; selected EPSG:1314 + EPSG:19916 operation uses no grid files.
  - Preferred operation set best available: `false`; missing preferred operations/grids: Inverse of British National Grid + OSGB36 to WGS 84 (9) (uk_os_OSTN15_NTv2_OSGBtoETRS.tif available=false).

## Map context and limits

This link is generated from the configured WGS84 anchor and centres OpenStreetMap on the current candidate. It is a visual map-context link only; regenerated reports make no fixed road or landmark assertions. EA DTM cell coverage is assessed separately; OSM/OS feature counts and overall AOI coverage remain unchecked and pending.

Map: [OpenStreetMap view](https://www.openstreetmap.org/?mlat=50.47785300&mlon=-3.53601300#map=16/50.47785300/-3.53601300). © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright).
Provider reference: [Postcodes.io API documentation](https://postcodes.io/docs/).
Coordinate reference: [pyproj Transformer documentation](https://pyproj4.github.io/pyproj/stable/api/transformer.html).

To regenerate after changing only the configured anchor or AOI parameters from PowerShell, run `.\.venv\Scripts\python.exe -m torquay_pipeline.cli select-aoi --config ..\config\aoi.torquay.json --output-dir ..\docs` from `pipeline/`.
