# Torquay 2 km fly-through package — accepted specification

**State:** Accepted by the coordinator on 2026-10-20 for implementation after the user's explicit request for 2 km terrain, buildings, and roads. This is a descriptive focused issue, not a new TVW backlog ID.

## Authority and limits

The user authorized generation of a 2,000 m × 2,000 m browser scene around the existing TQ1 4HN candidate. This authorization covers terrain, OSM buildings, OSM roads, browser selection/rendering, package QA, documentation, and verification required to deliver the fly-through. It does not approve or freeze the AOI, establish feature completeness, authorize new data sources/downloads, or authorize later work beyond this issue.

Preserve the exact current candidate center and bounds, `selected_pending_coverage` / `not_checked` statuses, and the synthetic scene. Do not infer completeness from feature counts. Preserve the existing 1 km package, historical profile, evidence, and their byte identities.

## Verified inputs and current gaps

- EA Composite DTM 1 m 2022 archives and extracted `SX96nw` / `SX96sw` GeoTIFFs are present and previously verified in `data/source-manifest.json`.
- The local Geofabrik Devon PBF `data/raw/osm/devon-261016.osm.pbf` is present; its recorded size and SHA-256 match the manifest.
- Existing terrain, buildings, and roads browser packages under `public/worlds/torquay-poc-001/` represent 1 km only. Do not modify these package bytes.
- Terrain export and real terrain validation encode the 501 × 501 / 1 km profile. Building/road schemas and browser loaders bind to one 1 km URL/profile. The current road payload is 18,160,963 bytes; measure the expanded payload before adjusting finite limits.
- The source manifest's acquisition AOI describes historical acquisition. Keep it unchanged; record processing extent in new package manifests and evidence.
- No dependencies or new data downloads are needed. Inspected versions include Node 22.20.0, Python 3.13.7, Three 0.186.1, Vite 8.3.4, TypeScript 6.0.3, Playwright 1.64.1, Vitest 5.0.5, Rasterio 1.5.2, NumPy 2.5.4, pyproj 3.8.0, Shapely 2.2.0, and osmium 4.3.1.

## Package and route

Publish a separate ignored package at `public/worlds/torquay-poc-001-2km/` with terrain, building, and road manifests/data/QA. Use separate generated and intermediate directories plus new QA evidence paths. Keep the logical candidate ID `torquay-poc-001` and add an explicit, strictly validated scene profile `current_2km`; the old package is accepted only as the exact historical 1 km profile.

Add an explicit local scene registry and route `/?world=torquay-poc-001-2km&buildings=1&roads=1`. The primary real-scene selector opens this combined 2 km route; the synthetic default stays `/`. Retain an explicitly labelled historical 1 km route. Bind each layer to the selected profile, AOI, origin, terrain-manifest identity, and heightfield identity. Do not permit arbitrary asset URLs or mix packages across profiles. The 2 km profile must show an unavailable overview state rather than loading the historical 1 km overview.

## Generation rules

Keep the current anchor `[-3.536013, 50.477853]`, BNG center `[291108.9018176432, 65353.48350844931]`, and bounds `[290108.9018176432, 64353.48350844931, 292108.9018176432, 66353.48350844931]` (west, south, east, north). Preserve pending statuses.

At 2 m spacing, terrain is 1,001 × 1,001 samples, 4,008,004 little-endian float32 bytes, and 2,000,000 triangles. Row zero is north; columns increase east and north maps to negative local Z. Keep the existing source-pixel-center sampling, interpolation, NoData rejection, seam handling, and exact mesh/sampler diagonal. Validate every source contributor needed for interpolation. The center origin uses the exporter's bilinear center sample; it must not be replaced with the coverage-report cell-center value. The new grid's central rows/columns 250–750 should agree with the previous grid where their source/lattice samples coincide.

Re-extract buildings and roads from the existing dated Devon PBF against the expanded buffered AOI. Do not stretch/copy the old clipped packages. Preserve reviewed topology, deduplication, height and width policies, road exclusions, terrain footing/draping, exact clipping, tags/source IDs, and provenance. Report measured counts and exclusions without claiming completeness.

Add an offline scene orchestrator that validates all inputs, builds to a unique owned staging area, runs terrain/building/road and combined validation, then publishes atomically. Guard protected inputs and symlinks before writes. Use collision-safe owned backup/staging paths and rollback; preserve any prior destination on failed validation/publication. Build and validate the 2 km package twice and compare deterministic artifact hashes.

Measure actual payload and geometry sizes before changing any browser limits. If a limit must grow, make it finite and profile-specific, match the Python and TypeScript contracts, document it, test malformed/oversized streaming responses and cancellation, and do not omit valid features to fit. `build:share` must exclude both real packages.

## Acceptance and evidence

Automated/data acceptance:

- Strictly reject mixed 1 km/2 km profiles, AOI rings, grids, origins, terrain hashes, or layer QA identities, including fixtures whose checksums are recomputed after mutation.
- Preserve prior unknown-safe schema, building-topology, and road-geometry tests.
- Check terrain center/corners/seams and at least ten deterministic source comparison samples; finite vertices/normals, valid index ranges, and mesh/sampler agreement.
- Prove valid building/road features exist in the new outer annulus and pass exact clipping/terrain validation. Record actual feature and geometry counts.
- Deterministic repeated builds match hashes. Missing/corrupt inputs, stage failures, and publication failures leave prior/current historical packages unchanged.
- Verify source manifest, raw input, synthetic fixture, historical package/evidence, and user installer hashes are preserved.

Production-browser acceptance on the combined route:

- Renderer ready with 1,001 × 1,001 terrain at 2 m, validated actual building/road counts, truthful 2 km pending AOI label, source vintages/licences, and estimated-height/width caveats.
- Real pointer-lock look, WASD/vertical navigation, 15 / 41.25 m/s speed, reset, Escape unlock, resize, and travel beyond the former ±500 m bounds into the added area; new bounds are ±1,000 m.
- Walk mode maintains 1.7 m ±0.05 m clearance; optional-layer failure retains terrain and retry/synthetic recovery work.
- Historical 1 km route loads unchanged; synthetic and share routes request no real assets; 2 km never requests the historical overview.
- No unexpected page, console, request, or HTTP errors. Save and inspect overview and low-altitude screenshots including an outer-annulus location. Record browser, viewport/DPR, GPU/backend when available, load time, frame-time/FPS measurements, draw calls, triangles, and package bytes. Existing 1 km performance does not establish 2 km usability; report what is measured.

## Expected files and checks

Likely new files: `pipeline/torquay_pipeline/scene_profiles.py`, `scene_build.py`, their tests, 2 km building/road configs, `src/app/realSceneProfiles.ts`, an isolated Playwright config/spec, milestone handback, inventory/QA JSON, and screenshots. Focused existing changes are expected in terrain/building/road exporters/publishers/CLI, the scene/building/road schemas and loaders, `createApp.ts`, terrain spawn/bounds logic, build/share config, asset contracts, README, project plan, AGENTS, and checkpoint.

From `pipeline/`: `python -m torquay_pipeline.cli build-scene --profile current_2km`; `validate-scene`; `pytest -q`; Ruff check/format; `pip check`. From root: typecheck, lint, format check, Vitest, production build, isolated 2 km E2E, full TVW-014 browser profile, share build/share E2E, and `git diff --check`. Add commands as needed for deterministic repeated build/hash comparison and actual package browser verification. Do not stop or replace the user's existing port-5173 service.

## Sources

Use existing official EA and Geofabrik source metadata and attribution. Current official documentation reviewed during planning: [Rasterio resampling](https://rasterio.readthedocs.io/en/stable/topics/resampling.html), [PyOsmium area/geometry guidance](https://docs.osmcode.org/pyosmium/latest/user_manual/03-Working-with-Geometries/), [Three.js BufferGeometry](https://threejs.org/docs/pages/BufferGeometry.html), and [Geofabrik Devon extract page](https://download.geofabrik.de/europe/united-kingdom/england/devon.html). Do not reinterpret public documentation as proof of dataset completeness or a new survey.
