# AOI selection candidate

**Status:** `selected_pending_coverage`<br>
**Coverage:** `not_checked` — EA DTM and OSM/OS feature coverage have not been checked in TVW-006.

## Anchor provenance

- Postcode: **TQ1 4HN**
- WGS84 centroid: longitude `-3.536013`, latitude `50.477853`
- Meaning: Postcode centroid; not a property or survey point.
- Provider: [Postcodes.io](https://api.postcodes.io/postcodes/TQ1%204HN) (quality 1); retrieved 2026-10-17
- Licence: OS OpenData licence (provider documentation)

## Candidate square

- Projected centre: `291108.902 m E, 65353.484 m N` (EPSG:27700)
- Bounds `[west, south, east, north]`: `[290858.902, 65103.484, 291358.902, 65603.484] m`
- Dimensions: `500.0 m × 500.0 m`
- This is a derived postcode-centred candidate. It is not coverage-approved or frozen.

## Transformation evidence

PROJ network access was disabled. These records describe the operations actually used for the forward centre transform and inverse corner transform.

- WGS84 → BNG operation: `pipeline` — Inverse of OSGB36 to WGS 84 (6) + British National Grid (with axis order normalized for visualization)
  - Reported accuracy: 2.000 m; grids: no grid files listed for the operation used.
- BNG → WGS84 operation: `pipeline` — Inverse of British National Grid + OSGB36 to WGS 84 (6) (with axis order normalized for visualization)
  - Reported accuracy: 2.000 m; grids: no grid files listed for the operation used.

## Map context and limits

An independent OpenStreetMap view centred on the postcode showed Wrights Lane, Haslam Road, Chatto Way and Charito Road in a built-up inland context (viewed 2026-10-17, zoom 18). This check confirms map context only. EA DTM coverage, OSM/OS feature counts and local data availability have not been checked; those remain TVW-007 work.

Map: [OpenStreetMap view](https://www.openstreetmap.org/?mlat=50.477853&mlon=-3.536013#map=18/50.477853/-3.536013). © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright). The saved screenshot is a dated map-context reference, not source geometry.
Provider reference: [Postcodes.io API documentation](https://postcodes.io/docs/).
Coordinate reference: [pyproj Transformer documentation](https://pyproj4.github.io/pyproj/stable/api/transformer.html).
Saved map context: [TVW-006 postcode screenshot](milestones/screenshots/TVW-006-postcode-context.png).

To regenerate after changing only the configured anchor or AOI parameters from PowerShell, run `.\.venv\Scripts\python.exe -m torquay_pipeline.cli select-aoi --config ..\config\aoi.torquay.json --output-dir ..\docs` from `pipeline/`.
