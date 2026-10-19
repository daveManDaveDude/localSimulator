# Torquay Virtual World — Browser PoC

**Project plan and Codex implementation specification**  
**Version:** 1.0 · **Prepared:** 17 October 2026  
**Status:** M0, M1 and TVW-001 through TVW-011 passed independent review. The 1,000 m AOI revision and EA DTM inspection passed; TVW-009 completed building import, height policy and QA, TVW-010 completed optional browser building rendering, and TVW-011 completed optional road rendering. Mapped feature counts do not establish completeness; remaining feature checks are outstanding, so the AOI remains pending and is not approved or frozen. TVW-008/M3 is complete as a terrain-only local browser mode. The user separately authorized TVW-012 on 2026-10-19; its formal three-spot independent map comparison and issue report are now the active scope. TVW-013 and later remain unauthorized, and the combined M5 exit gate is pending.
**Target platform:** Windows 11 development machine; recent desktop Chrome/Edge; locally served web application

---

## 0. Executive decision

**Build this in TypeScript, Three.js and Vite, not Unreal Engine.** Use a small offline Python GIS pipeline to transform real Torquay elevation and mapping data into lightweight local scene assets. The browser renders those assets and provides a moveable camera. No imagery streaming, Google Maps API key, Unity or Unreal installation is required for the PoC.

The first proof is deliberately modest: **a recognisable 1,000 m × 1,000 m section of Torquay**, showing believable real elevation, real building outlines as simple extruded blocks, real road alignments, and a camera controllable by mouse and keyboard. The first release is a **world viewer**, not a complete game or driving simulator.

**Non-negotiable rule:** each milestone must produce something directly viewable and testable. Build and demonstrate synthetic data **before** relying on geographic downloads. Codex should not attempt the full town before a small scene is working.

### Definition of first success

A user runs `npm run dev`, opens a local URL, and can:

1. See actual hills and slopes for the selected 1,000 m Torquay area.
2. Recognise local streets from road positions and building footprints.
3. Move a camera with WASD, steer with the mouse, and switch between free-flight and ground-following walking modes.
4. Read position, elevation, FPS, and current data-source information in a small on-screen debug panel.
5. Run a reproducible asset-generation command and automated tests without hand-editing scene files.

**Important distinction:** the location of the ground, roads and buildings should follow source data; building *heights*, roofs, textures and details are initially approximations unless a verified source provides them.

---

## 1. Goals, non-goals, and constraints

### Goals (PoC)

- Run as a locally served 3D web application (no hosted backend and no required external API at runtime).
- Realistic **terrain topography**, prioritising vertical accuracy and horizontal alignment rather than visual realism.
- Real **building footprints** represented by plain, correctly placed volumetric geometry.
- **Road centrelines** represented on terrain, with approximate width and distinctive colours.
- Convenient **free-flight camera** and later a **walking camera** at approximately 1.7 m above terrain.
- Ability to visually compare the scene with an independent map and to identify data gaps.
- Small, isolated, well-tested components that Codex can change without breaking other stages.
- Future option to export geometry to glTF/GLB and/or adopt a larger engine without abandoning GIS processing.

### Not in scope for the first PoC

- Google Photorealistic 3D Tiles / Cesium streaming.
- Satellite or street-level photography; photorealistic architecture.
- Detailed facade textures, house-specific roof shapes or window generation.
- Pedestrians, traffic, physics-grade vehicles, traffic rules, or collisions.
- Full Torquay area, network terrain streaming or multiplayer.
- Automatic registration or subscriptions to commercial geodata services.
- Survey-grade modelling of road surfaces, retaining walls, pavements or bridges.

### Practical constraints

- Prefer cost-free, downloadable, properly licensed input data.
- A project clone should launch against **small checked-in synthetic fixture assets** even when the developer has not downloaded real GIS data.
- The GIS pipeline may depend on local tools; browser startup may not.
- Support Windows 11 / PowerShell; document Python environment setup plainly.
- Do not commit bulk raw datasets, huge generated assets, credentials or secrets to Git.

---

## 2. Recommended technology stack

| Layer | Choice | Why |
|---|---|---|
| Browser application | **TypeScript + Vite** | Fast local feedback, typed modules, minimal framework overhead |
| 3D engine | **Three.js** | Direct control of geometry, camera, lighting and rendering |
| UI | Basic HTML/CSS | A compact control and debug overlay is enough |
| Controls | Three.js `PointerLockControls` plus custom movement logic | Mouse look is supplied; navigation behaviour remains testable |
| Terrain source | **Environment Agency LIDAR Composite DTM 1 m (2022 composite)** | Bare-earth terrain, raster data in British National Grid |
| Structures | **OpenStreetMap**, with **OS OpenMap – Local** as a fallback/augmentation | Real footprints; availability and detail vary locally |
| Roads | OpenStreetMap road geometry; optionally OS Open Roads | Useful metadata, alignment and class tags |
| Offline GIS | Python 3.12+, `rasterio`, `pyproj`, `shapely`, `geopandas`, `numpy` | Read rasters, transform CRSs and clip shapes |
| OSM extract | Download **Geofabrik Devon `.osm.pbf`**; use `osmium-tool` or another documented reader | Avoids repeated public Overpass/API queries |
| Browser tests | Vitest + Playwright | Unit tests plus actual in-browser interaction tests |
| GIS tests | pytest | Projections, height interpolation, building/road geometry |
| Code quality | ESLint, TypeScript strict mode, Prettier, Ruff | Mechanical quality gates |
| Version control | Git + GitHub | Small changes and inspectable PRs |
| Development assistant | Codex + browser automation / Computer Use | Codex writes and tests; visual operation verifies milestones |

**Do not add React, Next.js, a database, Docker, Cesium or MapLibre at the beginning.** Add only when a concrete requirement appears. MapLibre can later provide an overview/minimap if desired.

Official references: [Three.js](https://threejs.org/), [PointerLockControls](https://threejs.org/docs/pages/PointerLockControls.html), [GLTFLoader](https://threejs.org/docs/pages/GLTFLoader.html), [Geofabrik Devon](https://download.geofabrik.de/europe/united-kingdom/england/devon.html).

---

## 3. Real-world data: source decisions

### 3.1 Elevation — primary, highest priority

**Primary:** Environment Agency **LIDAR Composite Digital Terrain Model (DTM) – 1 m** (2022 composite; catalogue updated 2025). It covers approximately 99% of England. Data is offered as 5 km GeoTIFF tiles, in EPSG:27700, with elevation in metres relative to Ordnance Datum Newlyn. The composite incorporates surveys of differing vintages, so it should not be described as a 2026 survey.

- Publisher dataset page: https://environment.data.gov.uk/dataset/13787b9a-26a4-47b6-83da-dc98e73a461f
- Government data catalogue: https://www.data.gov.uk/dataset/01b3ee39-da3f-47b6-83da-dc98e73a461f/lidar-composite-dtm-2022-1m

**Important:** use the dataset landing page, then inspect its current download links and downloaded GeoTIFF metadata; do not hardcode an assumed file URL into the pipeline until verified.

**Operational acquisition:** Start with a *manual download from the Defra Data Services Platform* for the relevant source tile(s). Put them in `data/raw/ea_dtm/`. Automating discovery of downloads is an enhancement, **not** a prerequisite. Record filenames, links, download dates, CRS, elevation datum and checksums. Do not claim the source file is installed until it has been inspected with Rasterio/GDAL.

The DTM removes buildings and vegetation, which makes it the appropriate base for a walkable ground surface. The companion **Digital Surface Model (DSM)** contains buildings/trees and can later provide *approximate* rooftop-height clues, but a DSM–DTM difference is not a reliable per-building height without filtering and quality checks.

- Optional DSM: https://www.data.gov.uk/dataset/cf3f1137-c12b-44a1-a835-e80fe4a60b92/lidar-composite-digital-surface-model-dsm-1m

**NoData and coastlines:** Torquay has coastal edges. Do not turn raster NoData into 0 m: it creates artificial cliffs. For the first tile choose an **inland, mostly fully covered** AOI. If missing cells affect more than the configured threshold (proposed 1%), fail the build with a clear diagnostic and choose another area or a documented interpolation policy.

### 3.2 Building outlines — prioritise quality of footprint

**First trial:** OpenStreetMap polygon features tagged `building=*` (including multipolygons). Download once from a current **Geofabrik Devon** `.osm.pbf`, extract a buffered bounding box and convert to an intermediate GeoJSON/GeoPackage layer with tags preserved. OSM building coverage is variable, so **do not assume coverage is complete**.

- Devon regional download: https://download.geofabrik.de/europe/united-kingdom/england/devon.html
- OSM licence: https://www.openstreetmap.org/copyright
- Osmium clip: https://docs.osmcode.org/osmium/latest/osmium-extract.html
- Osmium export: https://docs.osmcode.org/osmium/latest/osmium-export.html

**Fallback/augmentation:** **OS OpenMap – Local** provides *generalised building polygons*. It is **not detailed cadastral building-part mapping** and does not imply building height data. Download as OS OpenData and inspect its building layer before use. Use it if OSM coverage is sparse; keep a source flag per feature. Avoid blindly overlaying both datasets because you would double-render buildings.

- Product docs: https://docs.os.uk/os-downloads/products/maps-and-imagery-portfolio/os-openmap-local
- Building feature specification: https://docs.os.uk/os-downloads/products/maps-and-imagery-portfolio/os-openmap-local/os-openmap-local-technical-specification/feature-types/building

**Height policy (not a statement of measured truth):**

1. Where a valid numeric OSM `height` is present, parse as metres and use it.
2. Otherwise, where valid `building:levels` exists, use `levels × 3.0 m` (configurable estimate).
3. Otherwise use a **configurable 8 m visual default**, distinctly labelled `estimated_default`.
4. Clamp invalid/absurd values; retain source and confidence in output metadata.
5. Add accurate elevation-based inference from the DSM **after** the basic PoC works.

Do not render all buildings as uniform world-axis cubes: preserve each polygon, including rotation and simple concave outlines. Multipolygons with holes need a tested strategy; skip and log unsupported geometry rather than silently producing wrong solids.

### 3.3 Roads — simple centreline ribbons at first

**Primary:** OpenStreetMap `highway=*` ways for relevant streets and paths. Centreline geometry with widths estimated by highway class is enough to recognise the neighbourhood; it **does not represent measured kerb boundaries**. Include names when supplied. Later consider OS Open Roads for greater general completeness; OS Open Roads is generalised and not a survey-grade road surface.

- https://www.ordnancesurvey.co.uk/products/os-open-roads
- https://docs.os.uk/os-downloads/products/transport-network-portfolio/os-open-roads/os-open-roads-overview

For stage one roads, sample the terrain along each polyline and generate a narrow offset ribbon (slightly above the terrain to avoid z-fighting). Mark tunnels/bridges and split/skip ambiguous segments rather than draping them incorrectly across ground. Do not attempt realistic junction meshes in the initial build.

### 3.4 Source/licensing register

Maintain `docs/data-sources.md` and `data/source-manifest.json`, including:

- Source name, product and publisher; exact source file + acquisition link/date.
- Licence and required attribution; attribution rendered in the browser.
- Data vintage / survey vintage where documented.
- Original CRS; whether elevation datum is known.
- Checksum of inputs; pipeline version; geographic bounding box.

The EA data is distributed under the **Open Government Licence** with a requested Environment Agency credit. OSM is under **ODbL**, with `© OpenStreetMap contributors` and a link to its licence; ODbL also creates obligations if publishing a derived database. OS OpenData has its own attribution terms. **Do not presume that combining and redistributing derived datasets has no licensing implications.** A local PoC can proceed while preserving separable source layers; review obligations before public hosting or redistributing source-derived scene datasets.

Useful references: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/ and https://wiki.openstreetmap.org/wiki/Legal_FAQ.

---

## 4. Define and freeze a concrete area of interest (AOI)

**Candidate anchor:** postcode **TQ1 4HN**. Postcodes.io returned quality 1 and WGS84 longitude `-3.536013`, latitude `50.477853` on 2026-10-17; these are postcode-centroid coordinates, not a property or survey point. The provider's rounded BNG values were easting `291110`, northing `65355`. Independent OpenStreetMap context was inspected at zoom 18 around the anchor and zoom 17 with the original 500 m candidate boundary overlaid. The dated marker-only and 500 m boundary screenshots are historical: `docs/milestones/screenshots/TVW-006-postcode-context.png` and `docs/milestones/screenshots/TVW-006-aoi-boundary.png`. On 2026-10-17 the user approved a 1,000 m square around the same centroid; its boundary capture is `docs/milestones/screenshots/TVW-006-aoi-boundary-1km.png`.

The original TVW-006 scope derived a **500 m × 500 m EPSG:27700 candidate** at the same centre; its bounds and dated screenshot remain historical in `docs/milestones/TVW-006.md`. On 2026-10-17 the user approved a **1,000 m × 1,000 m revision** without changing the WGS84 or projected centre. Current bounds are `[290608.9018176432, 64853.48350844931, 291608.9018176432, 65853.48350844931]` in `[west, south, east, north]` order. The tool pins non-ballpark EPSG operation 1314 (OSGB36 to WGS 84 (6)) plus EPSG operation 19916 (British National Grid), reporting 2 m accuracy; the selected operation uses no grid. PROJ network access is disabled. In this environment the preferred 1 m operation is unavailable because `uk_os_OSTN15_NTv2_OSGBtoETRS.tif` is missing; the tool records `best_available`, missing operation/grid names, and the selected operation definition in `docs/aoi-selection.json`. Full operation metadata and WGS84 QA GeoJSON are generated in `docs/aoi-selection.json` and `docs/aoi-selection.geojson`.

The current config status remains `selection_status: selected_pending_coverage` and `coverage_status: not_checked`. TVW-007's independently reviewed EA DTM center-coverage check passes its 1% missing-cell threshold; see `docs/milestones/TVW-007.md`. TVW-009 adds local OSM building-footprint counts and placement QA, but these counts do not establish completeness; road/remaining feature checks and the M2 exit gate remain pending. Do not describe this candidate as overall coverage-approved or frozen.

**Selection protocol (Codex task):**

1. The TQ1 4HN postcode centroid and independent OSM map context are documented in TVW-006 evidence.
2. Transform WGS84 longitude/latitude to EPSG:27700 with `pyproj` and `always_xy=True`.
3. Construct the user-approved **1,000 m × 1,000 m candidate AOI in British National Grid metres** around that transformed centre.
4. Generate RFC 7946 WGS84 QA GeoJSON with a closed exterior polygon and anchor point.
5. **TVW-007 status:** PASS after Luna fix 1 and independent Sol re-review. The EA 1 m DTM center-grid check passes its threshold; inspect candidate OSM/OS building and road counts only in the next separately authorized issue.
6. Keep the editable anchor, dimensions, and regenerated projected centre/bounds in `config/aoi.torquay.json`; publish operation metadata and QA output under `docs/`.
7. Allow moving the candidate square by changing the input config alone and rerunning the selection CLI.

**Hard rule:** use precisely the same frozen AOI for terrain, buildings, roads, diagnostics, screenshots and tests. Add a small acquisition buffer around it for features crossing boundaries; clip final exports consistently.

The current validated input config stores the editable WGS84 anchor, fixed candidate dimensions, pending-coverage statuses, and the current projected centre/bounds. The CLI refreshes those derived values after an anchor change and publishes operation metadata in `docs/aoi-selection.json`; the QA polygon is `docs/aoi-selection.geojson`. The input config contains no null placeholder coordinates.

**Coverage note:** the candidate coordinates are real transformation outputs derived from the documented postcode centroid. The independently reviewed EA DTM report passes the configured 1% missing-cell threshold. TVW-009 records OSM building footprints and mapped counts; road/remaining feature checks, any final AOI freeze, and M2 completion remain pending.

---

## 5. Coordinate system and 3D conventions

The most common failure mode is subtle misalignment between geospatial datasets and world geometry. Make this a dedicated, heavily tested subsystem.

**Original geographic data:** WGS84 longitude/latitude (`EPSG:4326`) for OSM; **British National Grid EPSG:27700** for EA LiDAR and OS data. Normalise inputs to EPSG:27700 **outside** the browser using `pyproj`/GDAL.

**World coordinates:** Three.js Y-up in **metres**, with a local projected origin. To preserve Three.js handedness:

```text
world.x = easting  - origin_easting       (positive = east)
world.y = elevation_orthometric_m - origin_elevation_m  (positive = up)
world.z = origin_northing - northing      (positive = south, negative = north)
```

This means **north points towards negative Z**. Use the same convention for roads, buildings, terrain, compass and movement. The origin should be near the AOI centre, with an elevation reference from the DTM near that centre. Record all three reference values in scene metadata. Do not pass six-figure easting/northing coordinates directly to a WebGL world; localisation avoids loss of floating-point precision.

**Terrain grid convention:** row 0 = northernmost samples; columns increase eastward; rows increase southward (positive world Z). Document pixel-centre vs raster-corner conventions explicitly. Prefer reading and interpolating directly from Rasterio affine transforms when generating the fixed grid, and ensure that a browser terrain `sampleHeight(x,z)` returns the same surface as the mesh (same two-triangle grid rule or an explicitly bounded interpolation error).

**Vertical datum caution:** Do not silently transform orthometric EA elevations into WGS84 ellipsoidal height. Keeping EA terrain heights, plus a local origin offset, is valid for this scene. If other elevation data is introduced, check datum compatibility.

**Numeric acceptance targets (engineering targets, not source-accuracy guarantees):**

- Projection round-trip of selected test points: ≤0.10 m where the necessary coordinate grids are available; otherwise measure and report actual transform accuracy, never hide a fallback transform.
- Height samples at grid vertices match generated terrain data within `1e-4 m` before quantisation.
- Browser rendered terrain versus collision/height sampling: ≤0.05 m on representative non-vertex samples, or use exact triangle interpolation so they agree.
- Buildings and roads must lie within frozen AOI plus documented clipping tolerance.
- Repeated builds from identical inputs yield equal hashes of deterministic outputs (excluding timestamp-only metadata).

Reference: https://pyproj4.github.io/pyproj/stable/api/transformer.html.

---

## 6. Asset contract between GIS pipeline and browser

Keep the first asset format **simple, inspectable and independent of Three.js**. Avoid committing to mesh exporters or GLB creation before a basic viewer exists.

### Recommended v1 deliverable

```text
public/worlds/torquay-poc-001/
  manifest.json              # CRS, AOI, offsets, sizes, sources, build version
  heightfield.f32             # little-endian float32 heights, row-major
  buildings.json             # local footprints, explicit heights, source IDs
  roads.json                 # local polylines, width/class/name attributes
```

**Example manifest, illustrative:**

```json
{
  "formatVersion": 1,
  "id": "torquay-poc-001",
  "sourceCrs": "EPSG:27700",
  "axisConvention": "+X east, +Y up, -Z north",
  "origin": { "eastingM": 0, "northingM": 0, "elevationM": 0 },
  "extentM": { "width": 1000, "depth": 1000 },
  "heightfield": {
    "path": "heightfield.f32",
    "columns": 501,
    "rows": 501,
    "spacingM": 2,
    "rowOrder": "north-to-south",
    "byteOrder": "little-endian",
    "encoding": "float32",
    "valueMeaning": "world Y in metres relative to origin elevation"
  },
  "buildings": "buildings.json",
  "roads": "roads.json"
}
```

**IMPORTANT:** `origin` values of zero above are just schema examples, not valid real-scene values. Real generated files must contain measured AOI-local projected coordinates and a documented local elevation origin. The manifest should additionally include geographic AOI bounds, source provenance, input hashes and asset checksums in the implementation.

At 2 m spacing, the 1,000 m square has **501 × 501 = 251,001 height samples**, about **1.00 MB** of uncompressed float32 height data. This is small enough for straightforward local browser loading. Retain the **1 m DTM source** for later resampling/LOD rather than discarding it.

For `buildings.json`, store polygon rings in world **XZ metres**, `heightM`, `heightMethod`, footprint provenance and unique ID. Keep a typed schema and validation. For `roads.json`, store line vertices in XZ, name, classification, approximate width, and a non-ground flag for bridges/tunnels when known. **Do not store absolute projected easting/northing** in every browser vertex.

### Browser generation

- Turn the heightfield into a `THREE.BufferGeometry` with indexed triangles, computed normals and one or two simple materials.
- Create building footprints using `THREE.Shape` / triangulation and extruded wall/roof geometry, or custom walls for sloped bases. Preserve concave footprints. Validate winding, holes and intersections.
- Roads are terrain-draped ribbons in local space, slightly elevated from the surface.
- All runtime fetching is from the local Vite public directory. Show load failures rather than silently displaying a blank view.
- Later performance optimisation: use merged geometries/material batching. `InstancedMesh` is appropriate for **repeated** geometries, not a magic solution for thousands of uniquely shaped building footprints.
- Optional future export: `.glb` via a standalone exporter; this should not be necessary for the first working world.

---

## 7. User experience and camera specification

### Screen design

A single, full-window canvas with a minimal HUD:

- World name and provenance indicator (e.g., `SYNTHETIC` or `REAL DATA`).
- Current mode: `FREE FLY` or `WALK`.
- X/Z local position, ground height, camera height, bearing, speed and FPS.
- One-line instructions and a small compass (`N` = negative Z).
- Data diagnostics overlay toggle and reset-to-start button.
- Persistent attribution text and a link to source/licence details.

### Controls (stage-dependent)

| Input | Free-flight | Walking |
|---|---|---|
| Left-click / button | Lock pointer | Lock pointer |
| Mouse | Yaw and pitch | Yaw and pitch |
| W / S | Forward / back in look direction | Forward / back on horizontal plane |
| A / D | Strafe | Strafe |
| Space / Ctrl | Up / down | Optional jump/crouch; initially unused |
| Shift | Faster movement | Faster movement |
| Mouse wheel | Adjust movement speed, if compatible with pointer-lock UX | Adjust speed |
| Esc | Release pointer | Release pointer |
| F | Toggle free-flight/walk | Toggle free-flight/walk |
| R | Reset to saved start | Reset to saved start |
| H | Toggle HUD | Toggle HUD |
| G | Toggle terrain grid / axes debug | Toggle terrain grid / axes debug |

**Initial free-flight target:** intuitive, smoothed-but-responsive mouse-look + frame-rate-independent keyboard translation. Prevent accidental departure from the AOI with clear boundary feedback, unless a debug setting overrides.

**Walking target:** camera eye stays about 1.7 m above sampled terrain; respects slopes, cannot descend below terrain. For the first PoC, walking **does not yet collide with buildings**. Label it as *ground-following navigation*, not physics simulation. Prefer exact heightfield collision sampling over a heavy physics dependency.

**Launch view:** spawn looking across a recognisable slope with roads/buildings visible. Do not start buried in the terrain or facing empty sky.

---

## 8. Suggested repository structure

```text
torquay-virtual-world/
├── README.md
├── AGENTS.md                         # Codex guardrails and completion protocol
├── package.json
├── package-lock.json
├── tsconfig.json
├── vite.config.ts
├── index.html
├── src/
│   ├── main.ts
│   ├── app/
│   │   ├── createApp.ts
│   │   ├── worldLoader.ts
│   │   └── state.ts
│   ├── geo/
│   │   ├── worldCoordinates.ts
│   │   ├── heightfield.ts
│   │   └── sceneSchema.ts
│   ├── scene/
│   │   ├── createScene.ts
│   │   ├── createTerrain.ts
│   │   ├── createBuildings.ts
│   │   ├── createRoads.ts
│   │   └── debugHelpers.ts
│   ├── camera/
│   │   ├── FreeFlyController.ts
│   │   └── WalkController.ts
│   └── ui/
│       ├── hud.ts
│       └── styles.css
├── public/
│   └── worlds/
│       └── synthetic-demo/           # Small checked-in test fixture
├── pipeline/
│   ├── pyproject.toml
│   ├── torquay_pipeline/
│   │   ├── cli.py
│   │   ├── aoi.py
│   │   ├── terrain.py
│   │   ├── buildings.py
│   │   ├── roads.py
│   │   ├── export.py
│   │   └── validation.py
│   └── tests/
├── config/
│   └── aoi.torquay.json
├── data/
│   ├── raw/                         # gitignored
│   ├── intermediate/                # gitignored
│   └── source-manifest.json
├── tests/
│   ├── unit/
│   └── e2e/
├── docs/
│   ├── project-plan.md              # this document
│   ├── data-sources.md
│   ├── aoi-selection.md
│   ├── decisions/
│   └── milestones/
└── .gitignore
```

Use a **single repo**, two build systems (npm and Python), no monorepo tooling. Check in source, scripts, lightweight synthetic fixtures and small representative screenshots. Ignore full Devon data, elevation rasters, intermediate GIS outputs, Playwright video artefacts and generated real-world world packages until an explicit asset distribution decision is made.

---

## 9. End-to-end build process

The system should be composed of discrete commands. Suggested command names below are **requirements for Codex to implement**, not claims that they already exist:

```powershell
# Node application
npm ci
npm run dev
npm run typecheck
npm run test
npm run test:e2e
npm run build

# Python pipeline (run from pipeline/)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m torquay_pipeline.cli validate-aoi --config ../config/aoi.torquay.json
python -m torquay_pipeline.cli inspect-sources --config ../config/aoi.torquay.json
python -m torquay_pipeline.cli build --config ../config/aoi.torquay.json --output ../public/worlds/torquay-poc-001
python -m pytest
```

The CLI must support `--help`, useful diagnostics, deterministic output, and safe failure (missing files, mismatched CRS, empty building layer, incompatible bounds). Avoid one giant `run-all-and-hope` script. Also provide a top-level PowerShell script / npm task that orchestrates the common flow once individual commands work.

### Pipeline sequence

```text
A. Configure AOI in EPSG:27700, choose local origin and asset spacing
B. Inspect downloaded source files (CRS, extent, NoData, row orientation)
C. Clip/resample EA DTM into regular AOI heightfield
D. Extract OSM features / optionally read OS OpenMap Local polygons
E. Reproject, clean, clip, normalise and deduplicate features
F. Convert all geometry to local Three.js X/Y/Z conventions
G. Write binary heightfield and compact JSON feature files
H. Write manifest with provenance, units, dimensions and hashes
I. Validate outputs and render in browser
J. Capture screenshot, report issues and record test outcomes
```

**No live GIS requests on every browser page load.** The browser is an offline renderer of prepared packages.

---

## 10. Implementation plan — vertical slices for Codex

Each milestone ends with a browser-visible demo, test results, a checklist and (where possible) a screenshot. **Codex must not combine all milestones in one giant change.**

### M0 — Repository and synthetic "hello world"

**User-visible result:** browser displays a plane, axes, a few blocks and a free-fly camera. Debug HUD says `SYNTHETIC`.

**Work:**

- Create strict TypeScript/Vite/Three.js project, format/lint/test scripts and README.
- Add ambient light, directional light, grid/axes helpers and responsive rendering.
- Add synthetic fixture with sloped terrain and 3–5 buildings.
- Implement pointer lock, WASD, ascend/descend and speed modifiers.
- Include a start overlay telling the user how to interact, and show useful errors if WebGL or assets fail.
- Add baseline Playwright smoke test; make canvas observable through a test-friendly status element rather than screenshot-only assertion.

**Acceptance:**

- `npm ci`, `npm run dev`, `npm run typecheck`, `npm test`, `npm run build` succeed on a clean checkout.
- Mouse-look + WASD visibly moves camera; Esc releases pointer.
- Window resize works and no console errors occur.
- At least one automated browser test can open and move in the scene.
- README includes one-command start instructions for Windows.

**Exit gate:** a reviewer can navigate synthetic blocks without any GIS setup.

### M1 — Asset schema and deterministic heightfield renderer

**TVW-005 status:** PASS after independent review and final coordinator gates. M1 is complete. TVW-006, including the approved 1,000 m candidate-size revision, passed independent review. TVW-007 also passed independent review after Luna fix 1; it establishes the EA DTM result only. M2 remains incomplete until OSM/OS feature-count checks and the remaining review gates are complete.

**User-visible result:** browser loads a **synthetic terrain hill** from a `heightfield.f32` fixture rather than constructing it ad hoc.

**Work:**

- Define and validate `manifest.json`; implement binary Float32 heightfield loader.
- Implement terrain triangulation, normals and `sampleHeight(x,z)` with exact orientation semantics.
- Create a synthetic heightfield with known corner heights, a slope and a ridge.
- Implement wireframe/terrain grid toggle and ground-height HUD.
- Add schema validation with actionable failures.

**Acceptance:**

- Known synthetic vertex and non-vertex sample heights match expected triangle-interpolated values.
- Northern row renders towards negative Z; a north arrow points correctly.
- Terrain triangles do not show cracks and height values are finite.
- Missing or corrupt heightfield displays an explicit error.

**Exit gate:** browser terrain renderer does not depend on real-world files.

### M2 — Freeze Torquay AOI and verify elevation acquisition

**TVW-006 status:** Original 500 m scope passed after Luna fix 1 and independent re-review. The user authorized a 1,000 m size revision on 2026-10-17; that revision passed independent review by Sol on 2026-10-17. It retains the same postcode-centred candidate and deterministic operation/grid diagnostics. The EA DTM check is documented under TVW-007; OSM/OS feature counts remain unverified, so do not call the AOI coverage-approved or mark the M2 exit gate complete.

**User-visible result:** a **data-inspection report and 2D preview** of actual Torquay elevation, with selected 1,000 m AOI drawn on it. The browser can still run synthetic scene.

**TVW-007 status:** PASS after Luna fix 1 and independent Sol re-review. The public EA LIDAR Composite DTM 1 m (2022) `SX96nw` and `SX96sw` archives were acquired and verified, with extracted TIFF/XML files cryptographically bound to named archive members. The aligned 1 m AOI report measures 1,000,000/1,000,000 valid cell centers, no uncovered/NoData/nonfinite cells, and a pass against the 1% DTM missing threshold. The overall AOI remains pending because OSM/OS building and road counts are not part of this issue and remain unchecked. See `docs/data-sources.md`, `data/source-manifest.json`, and `docs/milestones/TVW-007.md`.

**Work:**

- Select actual AOI by map inspection and convert chosen WGS84 centre to EPSG:27700.
- Download and locally inspect relevant EA DTM GeoTIFF tile(s). **Completed for `SX96nw` and `SX96sw`; exact request links, archive and TIFF hashes, XML metadata, and measured coverage are in the TVW-007 evidence.**
- Build `validate-aoi`, `inspect-sources`, coverage/NoData checks and `docs/aoi-selection.md`.
- Generate a simple PNG height preview with scale bar and sample elevation statistics (min, max, centre, NoData fraction). **Completed at `docs/milestones/screenshots/TVW-007-ea-dtm-preview.png`.**
- Capture input-source names, checksums, documented vertical datum and projection operation/accuracy.

**Acceptance:**

- AOI exactly 1,000 m × 1,000 m in EPSG:27700; the raster preview draws the exact AOI boundary and uses EPSG:27700 metre axes. Road/landmark context and OSM/OS feature counts are separate checks; the DTM raster does not supply road labels.
- Report identifies correct source GeoTIFF(s) and sane elevations; no guessed or silently patched coverage.
- Python tests cover coordinate transformations, bounds and NoData.
- Changing AOI config changes the preview without code changes.

**TVW-007 issue gate:** verified EA data for the chosen Torquay square is present locally, the aligned AOI sample coverage is reported, and an attributed preview exists. **The M2 exit gate remains open** until OSM/OS feature checks and overall AOI review are complete. If EA data is unavailable, flag as blocked and keep synthetic world fully working.

### M3 — Render real Torquay terrain

**TVW-008 status:** PASS after two focused fixes and independent Sol review on 2026-10-17. The delivered terrain-only feature is a selectable, local EA DTM package for the current 1,000 m pending candidate; this does not freeze or otherwise approve the full AOI. See the [TVW-008 handback](milestones/TVW-008.md).

**User-visible result:** replace synthetic ground with **true Torquay LiDAR-derived topography** in browser. Fly over recognisable slopes.

**Work:**

- Read source GeoTIFF(s), normalise to exact grid, use 2 m rendering spacing initially.
- Export `heightfield.f32` + manifest with correct local origin.
- Add selectable world ID (`synthetic-demo` / `torquay-poc-001`) and deterministic start position.
- Add basic height/colour ramp to make contours and slopes legible (avoid noisy photorealistic textures).
- Provide an independent 2D QA image from the raster pipeline.

**Acceptance:**

- Browser loads terrain without external mapping services.
- Grid dimensions and extent are 501×501 and 1,000 m per side if 2 m spacing is selected.
- 10 randomly sampled points agree with source elevations to within a documented **resampling** tolerance (target ≤0.25 m at terrain grid vertices when comparing like-for-like sampling), rather than falsely claiming survey-grade accuracy.
- No inverted hills, mirrored orientation, giant cliffs from NoData or unexpected vertical exaggeration.
- The scene draws at a usable interactive rate; record machine, viewport size and median FPS.

**Exit gate:** saved screenshot of real Torquay terrain in the browser.

**TVW-008 issue gate:** Passed. The 501 × 501 real terrain loaded locally, passed source-sampling QA and browser recovery checks, and has an independently reviewed browser screenshot. Chrome on the host RTX 4070 SUPER / Direct3D11 measured a 60 FPS median; the SwiftShader test path measured 9.1 FPS and remains a documented software-renderer limitation. M2 remains incomplete pending OSM/OS feature checks.

### M4 — Real building footprints (3D blocks)

**TVW-009 status:** Passed independent review after Luna fix 2 (`42bafd6`). The completed issue covers building import, height policy, asset validation and QA only. Preserve the current 1,000 m AOI and pending overall coverage status; mapped building counts do not establish completeness. Roads and remaining feature checks are not included. TVW-010 completed and passed independent review for browser rendering and terrain footing; roads remain outside this issue.

**TVW-010 status:** PASS after Luna fix 3 (`fb287fe`) and independent Sol review on 2026-10-19. The optional browser layer loads and renders the validated local OSM package on EA terrain with terrain-following wall bases. Rehashed topology cases, publisher safety, QA identity, mean rounding, bounded streaming and UI provenance/count persistence passed review. The flat-roof convention is highest terrain beneath each complete footprint plus its validated tagged or estimated height. The synthetic default and pending AOI status are preserved; roads were outside TVW-010 and were authorized separately under TVW-011. See [TVW-010 specification](milestones/TVW-010-spec.md) and [TVW-010 handback](milestones/TVW-010.md).

**User-visible result:** **real buildings** stand on the slopes at approximately correct plan positions and shapes.

**Work:**

- Acquire local OSM building polygons, preserving useful tags, or ingest OS OpenMap Local building polygon layer.
- Validate footprints: non-empty, finite, area threshold, clip to AOI, handle polygon winding and holes.
- Convert world XZ footprint geometry into flat-roofed buildings with terrain-following bottom walls and documented height fallback.
- Place roofs at a consistent elevation for each building, with sensible base treatment on slopes.
- Add buildings count to HUD, optionally colour-code by source and height confidence.
- Save quality report (source counts, dropped invalid objects, source breakdown, height method breakdown).

**Acceptance:**

- No substantial category of duplicated buildings due to source mixing.
- Building roofs/walls align with the same local origin as terrain.
- Buildings have no obvious levitation caused by using a single global terrain level.
- Polygon shapes remain recognisably different from identical rotated rectangles; height estimates are clearly identified as estimates.
- Unit tests cover convex, concave, rotated, holed, sloped and invalid polygons (or explicitly logged holes unsupported at this stage).

**Exit gate:** first credible local-neighbourhood screenshot with real terrain and buildings.

**TVW-009 issue gate:** PASS after Luna fix 2 (`42bafd6`) and independent Sol review. The local OSM footprint package, height policy, provenance/validation and QA report/map are complete and reproducible. TVW-010 separately completed and passed the browser building/terrain-footing gate. The overall mapped-area feature gate remains incomplete because roads and remaining feature checks are outstanding.

### M5 — Roads and navigation cues

**TVW-011 status:** PASS after Luna fix rounds 1 (`ed29006`) and 2 (`3ae4e3a`) and independent Sol review on 2026-10-19. The local optional road layer is source-bound, reproducible, terrain-draped and browser-verified; the dated extract produced 198 ways, 198 clipped centerline parts, 200 ribbon components, 72,098 render vertices and 98,238 triangles. Rehashed adversarial schema cases, synthetic fallback, provenance and QA checks passed review. See the [TVW-011 handback](milestones/TVW-011.md) for commands, hashes, screenshots and limitations. TVW-011 completes its issue scope only; the combined M5 exit gate remains pending TVW-012's formal three-spot independent comparison. The AOI remains `selected_pending_coverage` / `not_checked`, and mapped counts do not establish completeness. The user separately authorized TVW-012 on 2026-10-19; its Sol specification was accepted on 2026-10-19 and implementation is active. TVW-013 and later remain unauthorized.

**User-visible result:** road alignments and major junctions become recognisable; named roads can optionally appear in a selected-road debug label.

**Work:**

- Extract OSM `highway=*` lines and metadata for AOI; decide inclusion of paths vs vehicular streets.
- Normalise line geometry and width estimates by road class.
- Drape ribbon geometry to terrain with vertical offset; clip edges and label unsupported bridge/tunnel geometry.
- Use subdued material colours and optional wireframe so terrain shapes remain visible.
- Display current road count, toggle road visibility and add debug marker at known landmarks.

**Acceptance:**

- Roads demonstrably follow the terrain rather than render as one flat plane.
- Three source-backed landmark contexts and bounded placement observations are recorded. The formal independent three-spot map comparison is TVW-012 work.
- No giant ribbons/triangles caused by NaN, malformed paths or broken polyline segments.
- Road class fallback widths are documented as visual estimates, not survey widths.

**TVW-011 issue gate:** local road ribbons load on terrain; extraction, provenance, schema/geometry QA and synthetic fallback pass; bounded placement observations and screenshots are recorded.

**Combined M5 exit gate:** remains pending the formal independent three-spot comparison and issue report in TVW-012. Do not treat TVW-011's mapped counts or bounded placement observations as a completeness check or AOI approval.

### M6 — Ground-following walk mode

**User-visible result:** a user can walk along slopes at **~1.7 m eye height**, look around, and switch freely back to flying.

**Work:**

- Implement walking camera using shared heightfield sampling.
- Ensure frame-rate-independent movement, bounds clamping, stable camera near tile edge and smooth transitions when changing mode.
- Optional speed cap, slope warning and start position on a road.
- Explicitly defer building collision and road-surface collision.

**Acceptance:**

- Camera does not sink below ground at slopes or off-grid edges.
- Camera eye offset remains 1.7 m ±0.05 m above interpolated terrain in steady state.
- Walk/fly transition does not teleport to wrong geographic location.
- Playwright test checks mode switching and observed position updates; unit tests check height sampling.

**Exit gate — PoC COMPLETE:** person can navigate a recognisable area of Torquay on foot and from above.

### M7 — Review, profile and package

**User-visible result:** clean local project demo plus benchmark and instructions; polished enough to show someone else.

**Work:**

- Measure frame time, loading time, draw calls, geometry count, generated scene bytes and peak memory where practical.
- Tackle only observed performance issues; batch building meshes by material if needed.
- Document missing coverage, alignment imperfections and estimated building heights.
- Test a fresh checkout and regeneration from documented local source files.
- Record milestone screenshots and independent map comparisons in `docs/milestones/`.

**Acceptance:**

- `npm run build`, `npm run test:e2e`, `python -m pytest` pass.
- No critical console errors, blank screens or undocumented installation steps.
- A new developer can run synthetic scene immediately and regenerate the real scene after placing documented source downloads.
- Provenance/attribution shown in app and accompanying docs.

### M8 — Stretch goals only (do not start before M6 sign-off)

- 1 km × 1 km AOI, or 250 m × 250 m chunks with consistent edge height samples.
- Load chunks near camera with frustum culling and/or low-detail terrain at a distance.
- DSM-assisted approximate building heights with confidence scoring.
- Trees, basic land-use colouring, pedestrian paths and roof styles.
- Street labels and a MapLibre overview/minimap.
- Building collision, realistic ground-contact physics, and **drivable roads**.
- Optional export to GLB and deployment as a static website after licence review.

---

## 11. Testing plan

### Automated tests — browser/TypeScript

- Schema validation fails clearly for malformed/missing assets.
- Synthetic terrain mesh sample heights equal walking height sampler.
- Source projection sign convention is respected: north = negative world Z.
- Camera displacement is proportional to elapsed time and not dependent on frame count.
- Travel stays within configured boundaries unless debug override is active.
- Building geometry produces finite coordinates and valid indexed geometry.
- Debug HUD shows actual world type and does not call synthetic data “Torquay”.

### Automated tests — Python/GIS

- WGS84 ↔ British National Grid transformation round-trips known control points within reported accuracy.
- Raster source CRS is inspected and either normalised or rejected; axes and row order are correct.
- AOI width/height, resolution, sample count and output binary byte length agree.
- Bounds and origins are aligned across heights, buildings and roads.
- NoData is never interpreted as sea level or silently replaced without policy.
- Geometry cleaning, clipping and invalid polygon handling are deterministic.
- Building height metadata retains origin, method and value.
- Same inputs/config/pipeline version produce stable content hashes.

### Visual acceptance matrix

| Scenario | Evidence |
|---|---|
| Flat/slope/ridge synthetic fixture | Screenshot + known height sample assertions |
| Torquay topography orientation | Browser vs raster preview; north-arrow screenshot |
| Building placement on hill | Ground-eye screenshot and overhead screenshot |
| Three named junctions/landmarks | Comparison captures and documented observations |
| Walking across a slope | Screen recording or screenshots plus camera-height assertion |
| Error case (missing dataset) | Visible error text and passing negative test |
| Performance | Browser/version/GPU/viewport/FPS log in milestone notes |

**Initial performance aspiration:** steady ~60 FPS on the developer's Windows desktop at 1080p with the 1,000 m AOI; 30 FPS may be acceptable while profiling. These are **targets to measure**, not promises and not automated pass/fail gates until the target machine is defined.

---

## 12. Data-quality and rendering pitfalls to design around

| Failure mode | Mitigation / gate |
|---|---|
| Mirrored or rotated terrain | One fixed axis convention; checkerboard orientation fixture; north arrow |
| Large incorrect vertical scale | Metres end-to-end; no automatic 100× conversion; record elevation origin |
| Buildings below/above terrain | Sample DTM around each footprint; walls to ground; roof relative to footprint elevations |
| Road crossings look wrong | Flag `bridge`, `tunnel`, `layer`; exclude problematic cases in first release |
| Buildings visually incorrect | Tag fallback values as *estimated*; preserve polygon shape; no false claim of real height |
| Raster coastline holes | AOI with good coverage; explicit NoData threshold; separate water design later |
| Mixed data survey dates | Source/version report; warn where alignment seems inconsistent |
| Too much data in Git | Raw/intermediate ignore rules; checksums and acquisition guide; tiny synthetic fixtures |
| FPS collapse from draw calls | Shared materials and geometry batching once measured |
| False assurance from screenshots | Coordinate and sample tests plus independent source comparison |
| Download URL/API changes | Keep original publisher landing links; manual source acquisition fallback |
| Licence confusion | Source manifest, on-screen attribution and redistribution review |

---

## 13. Project commands and quality gates to implement

### Node / frontend

```text
npm run dev          Launch viewer, defaulting to synthetic world
npm run build        Production static build
npm run preview      Preview the production build
npm run typecheck    TypeScript strict validation
npm run lint         ESLint
npm run format:check Prettier check
npm run test         Unit tests (Vitest)
npm run test:e2e     Playwright smoke/navigation tests
```

### Python / GIS

```text
python -m torquay_pipeline.cli validate-aoi ...
python -m torquay_pipeline.cli inspect-sources ...
python -m torquay_pipeline.cli preview-terrain ...
python -m torquay_pipeline.cli build ...
python -m torquay_pipeline.cli validate-output ...
python -m pytest
```

The `inspect-sources` command should produce data availability and statistics **before** asset generation. The viewer must remain functional without real source downloads. Generate output atomically (temporary directory then move) so a failed build does not corrupt the last known-good world.

---

## 14. Codex working protocol / AGENTS.md rules

Copy the following principles into `AGENTS.md` once the repository is created:

1. Work on **one milestone and one focused issue** at a time. Do not implement M3–M6 while completing M0.
2. Start with an implementation plan, concrete files touched, tests and proof of completion.
3. Keep geographic calculations in tested Python modules and typed, documented asset contracts. No ad-hoc coordinate transforms scattered across React/Three.js render logic.
4. Maintain a **fully functioning synthetic world** at all times.
5. Do not fabricate geographic coordinates, downloaded files, measured building heights or successfully run tests.
6. Do not silently add a paid service, large dependency, API key, authentication system, container orchestration or hosted backend.
7. Use official publisher documentation and source metadata when dataset shape, CRS or licence is uncertain.
8. For each change: run quality gates, confirm local browser experience where possible, attach screenshot/observation, record blockers, and update milestone checklist.
9. Do not claim visual tests passed unless an actual browser run occurred. If Computer Use/browser access is unavailable, say so and provide precise local verification steps.
10. Keep source data separate from generated assets; preserve provenance and repeatability.
11. If a source is missing, implement a clear fallback **without pretending fake data is real**.
12. Ask for user intervention only for things Codex cannot reasonably obtain (e.g., an account-gated manual download). Continue with synthetic work rather than blocking every milestone.
13. Make small commits with meaningful messages; do not push or merge without configured repository/user permission.
14. Finish every milestone with a handback: summary, commands run, test results, screenshot links where available, known defects, and next proposed issue.

### Handoff template

```markdown
## Milestone handback: M# — name
- Implemented:
- User-visible demonstration:
- Files changed:
- Commands/tests executed and results:
- Browser verification (actual or not performed):
- Data source/provenance status:
- Screenshot / preview path (if created):
- Known limitations:
- Next recommended task:
```

---

## 15. Suggested sprint-ready backlog

Use the following order, splitting into sub-issues if implementation grows beyond a manageable PR:

| Issue | Milestone | Work item | Verification |
|---|---|---|---|
| TVW-001 | M0 | Scaffold Vite/TypeScript/Three.js; scripts; strict type checking | Starts in clean checkout |
| TVW-002 | M0 | Synthetic geometry, sky/light/grid, camera and pointer lock | Can fly around objects |
| TVW-003 | M0 | HUD, help overlay and basic Playwright smoke test | Browser test and visible state |
| TVW-004 | M1 | Scene manifest/schema and binary heightfield loader | Rejection and happy-path tests |
| TVW-005 | M1 | Terrain mesh/normal generation and exact height sampling | Synthetic 3D slope screenshot |
| TVW-006 | M2 | AOI selection tool, config validation and coordinate tests | BNG AOI and QA GeoJSON |
| TVW-007 | M2 | EA DTM file inspection, coverage report and preview | Real elevation PNG/report |
| TVW-008 | M3 | Real DTM extraction/heightfield export | Real Torquay terrain loads |
| TVW-009 | M4 | OSM or OS building import, height policy and QA report | Counts and building map QA |
| TVW-010 | M4 | Browser extruded buildings with terrain-following wall bases | Ground-level screenshot |
| TVW-011 | M5 | Road extraction and draped ribbon renderer | Visual road/terrain alignment |
| TVW-012 | M5 | Three-spot independent map comparison and issue report | Alignment comparison recorded |
| TVW-013 | M6 | Walk mode, slope/ground sampling and mode switch | 1.7 m height assertion |
| TVW-014 | M7 | End-to-end smoke test, benchmark, README, attribution | Local demo acceptance |

**Dependencies:** TVW-004 → TVW-005 → TVW-008; TVW-006 → TVW-007 → TVW-008; TVW-008 → TVW-010/TVW-011; TVW-010 + TVW-011 → TVW-012; TVW-005 → TVW-013. M0 is prerequisite for all later browser work.

---

## 16. Explicit architecture decisions

| ID | Decision | Reason | Revisit when |
|---|---|---|---|
| ADR-001 | Three.js instead of Unreal | Faster Codex iteration and browser preview | GPU/physics demands exceed web requirements |
| ADR-002 | Python for GIS, TS for rendering | Reliable source handling and simple browser runtime | Need a portable server pipeline |
| ADR-003 | EPSG:27700 to local metre coordinates | UK data alignment, stable precision | Expanding far beyond Devon |
| ADR-004 | Download/compile geodata offline | No API keys, streaming artefacts or per-frame API costs | Frequent map updates become core requirement |
| ADR-005 | Heightfield + JSON first, GLB optional | Inspectable, testable, easy to change | Asset size or loading becomes a bottleneck |
| ADR-006 | 1,000 m AOI, 2 m render grid | User-approved area with a manageable 501×501 render grid | M6 signed off and performance measured |
| ADR-007 | OSM footprints, OS fallback | Start with adaptable coverage, preserve a richer fallback | Inspection reveals insufficient buildings |
| ADR-008 | Ground-following camera before physics | Matches initial objective with little complexity | Building collisions or vehicles are required |

---

## 17. Suggested definition of done for the PoC

The following are all required:

- [ ] Real AOI chosen and frozen, with its geographic location independently checked.
- [ ] Real EA terrain dataset documented and transformed into a **1,000 × 1,000 m** scene.
- [ ] Actual building footprints rendered; estimated heights explicitly identified.
- [ ] Roads displayed with their geographic alignment verified at three local points.
- [ ] Freely moveable camera and functioning 1.7 m ground-following walk mode.
- [ ] Terrain/building/road geometry share one tested coordinate convention.
- [ ] No paid account or real-time mapping API required to view a built local scene.
- [ ] Synthetic fallback still launches on a clean clone without raw downloaded data.
- [ ] Test suites and production browser build pass.
- [ ] Attributions/licences and source vintages visible/documented.
- [ ] README and milestone handbacks make it possible to continue in later Codex sessions.

### Go/no-go after M6

**Go:** the terrain silhouette and street/building relationships look recognisably like the selected area; movement is smooth; regeneration is repeatable. Test chunking and performance at the selected 1 km extent.

**No-go / investigate:** multiple datasets are clearly misaligned, large areas of elevation are missing, road/building detail is insufficient to recognise the neighbourhood, or the browser cannot handle the geometry. Fix data quality, coordinate issues or rendering strategy before expanding beyond the selected 1 km square. Moving to Unreal is not the default remedy for source-data problems.

---

## 18. First Codex prompt (paste directly into Codex)

> You are the implementation engineer for the **Torquay Virtual World Browser PoC**. Read `docs/project-plan.md` in full and follow its architecture, data-source provenance, acceptance gates and Codex protocol. The application will eventually render a 1,000 m × 1,000 m section of Torquay using EA DTM elevation and OSM/OS building and road geometry, but **for this assignment implement M0 only**.
>
> **M0 scope:** scaffold a clean Windows-friendly Vite + strict TypeScript + Three.js project; create a beautiful but deliberately simple synthetic 3D demo with a sloped ground plane, grid, a few blocks, lighting, debug HUD, pointer-lock mouse look, WASD free flight, vertical movement, speed modifier and reset. It must work on a clean clone **without downloaded GIS datasets**. Include npm scripts for dev, build, typecheck, lint and unit/e2e tests; README; `AGENTS.md`; sensible `.gitignore`; and an automated Playwright smoke test. Use current official docs for APIs and check installed package versions before coding. Keep the implementation modular for later binary heightfield loading. Do not bring in React, Cesium, APIs, paid services or unrelated dependencies.
>
> **Workflow:** (1) inspect repo state, (2) summarise an implementation plan, (3) implement M0 in small focused changes, (4) run available quality gates, (5) attempt browser verification with actual screenshots if supported, and (6) provide the milestone handback format in the plan. Do not claim unexecuted tests passed. Do not start M1 until M0 is reviewed. If the document has conflicting or placeholder details, identify and correct them without inventing real geodata.

**Repository note:** this repository already contains the supplied source plan at `docs/Torquay_JS_Virtual_World_PoC_Codex_Plan.md`. During TVW-001, add `docs/project-plan.md` as its canonical copy and apply only the documented AOI-timing, preferred-anchor, status, and repository-path corrections there. Preserve the supplied source plan unchanged.

---

## 19. Sources / verified research links

Publisher and official documentation checked during planning on **17 October 2026**:

1. Environment Agency, LIDAR Composite DTM 1 m, publisher listing — https://www.data.gov.uk/dataset/01b3ee39-da3f-47b6-83da-dc98e73a461f/lidar-composite-dtm-2022-1m
2. Defra DSP, DTM dataset page — https://environment.data.gov.uk/dataset/13787b9a-26a4-47b6-83da-dc98e73a461f
3. Environment Agency, LIDAR Composite DSM 1 m — https://www.data.gov.uk/dataset/cf3f1137-c12b-44a1-a835-e80fe4a60b92/lidar-composite-digital-surface-model-dsm-1m
4. Geofabrik, Devon OSM downloads — https://download.geofabrik.de/europe/united-kingdom/england/devon.html
5. Osmium, bounding-box extract — https://docs.osmcode.org/osmium/latest/osmium-extract.html
6. Osmium, OSM-to-GeoJSON export — https://docs.osmcode.org/osmium/latest/osmium-export.html
7. OS OpenMap – Local documentation — https://docs.os.uk/os-downloads/products/maps-and-imagery-portfolio/os-openmap-local
8. OS OpenMap – Local building geometry specification — https://docs.os.uk/os-downloads/products/maps-and-imagery-portfolio/os-openmap-local/os-openmap-local-technical-specification/feature-types/building
9. OS Open Roads product — https://www.ordnancesurvey.co.uk/products/os-open-roads
10. Three.js PointerLockControls — https://threejs.org/docs/pages/PointerLockControls.html
11. Three.js BufferGeometry — https://threejs.org/docs/pages/BufferGeometry.html
12. Three.js InstancedMesh — https://threejs.org/docs/pages/InstancedMesh.html
13. Three.js glTF loader — https://threejs.org/docs/pages/GLTFLoader.html
14. PyProj Transformer — https://pyproj4.github.io/pyproj/stable/api/transformer.html
15. OpenStreetMap licence and attribution — https://www.openstreetmap.org/copyright
16. OGL v3 — https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/

**What has not yet been checked:** completeness of local OSM building footprints, OSM/OS road coverage and real GPU performance on the user's PC. TVW-009 records counts and placement spot checks for the dated OSM extract, but those do not show whether all relevant features are present. TVW-007 has checked EA DTM cell-center coverage; that DTM-only result does not imply complete coverage for other sources or a frozen AOI.

---

## 20. Future directions (not part of the PoC commitment)

After M6 sign-off, choose one path based on what proves enjoyable:

- **Explorer:** expand around Torquay, add trees, labels, views, sea and better roofs; retain simple walking controls.
- **Driving world:** improve intersections, road widths/grades, guardrails, bridges, lane centres; then introduce vehicles and collision handling.
- **GIS visualiser:** inspection layers, source comparison, feature clicking, area measurement and an overhead map.
- **Interoperable digital twin:** generate GLB or chunked spatial assets and consider Unreal only if desired visual/physics complexity justifies it.

The primary goal remains the same throughout: **recognisable Torquay, from real public geographic data, experienced from a moving camera**.
