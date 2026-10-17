# Torquay Virtual World

A Windows-friendly browser proof of concept for a future real-data view of Torquay. The default viewer loads a small, checked-in synthetic Float32 heightfield and renders its terrain mesh, hill, ridge, grid and north cue. The prior M0 analytic scene remains available at `/?world=m0`.

Every browser world is fictional and marked **SYNTHETIC**. The heightfield, hill, ridge, analytic slope, blocks, dimensions and elevations are invented examples; they are not Torquay measurements. Both local fixtures use zero-valued local origins and contain no geographic coordinates. No EA DTM, OSM/OS extract, real roads or other geographic dataset is loaded into the browser. The offline Python tool records TQ1 4HN as a postcode-centroid anchor for a 500 m candidate AOI, with data coverage still unchecked.

## Requirements

- Windows 11 with PowerShell
- Node.js 22.13 or later within the 22.x line, 24.x, or 26.x and later
- npm, included with Node.js
- Python 3.12+ for the offline AOI CLI (TVW-006 tested with Python 3.13.7)
- A recent desktop browser with WebGL support

## Start locally

On a clean clone, install the locked dependencies once from PowerShell:

```powershell
npm ci
```

Then start the viewer with one command from the repository folder:

```powershell
npm run dev
```

Open the local address printed by Vite. `npm ci` restores the exact dependencies in `package-lock.json`; the initial clean install needs access to the npm registry. Once installed, the application uses local files only and does not call a hosted service.

Click **Start exploring** to enter pointer lock. Move the mouse to look; use **W/S** to fly along the full camera direction, **A/D** to strafe, **Space/Ctrl** to rise and descend, **Shift** to move faster, **R** to restore the spawn position and view, and **Esc** to release the pointer. The camera stays inside the finite synthetic terrain bounds; the status pill signals when you reach an edge. Click the scene or **Resume flying** to relock after pressing Esc. Use **G** or the terrain-grid button to toggle grid and north cues; the wireframe button changes the terrain mesh display.

The live HUD reports the loaded world, source mode, grid dimensions, sampled ground height, camera position and bearing/pitch, lock state, speed, FPS and boundary state. A load error identifies the failing stage and offers retry and a link to the M0 analytic demo.

## Project commands

```powershell
npm run dev          # Start the local development server
npm run build        # Type-check and produce the static build in dist/
npm run preview      # Serve the production build locally
npm run typecheck    # Run strict TypeScript validation
npm run lint         # Run ESLint
npm run format:check # Check formatting with Prettier
npm run test         # Run movement, asset, terrain-grid, and mesh unit tests
npm run generate:synthetic-heightfield # Rebuild both deterministic synthetic fixture packages
npm run test:e2e:install # Download Playwright's Chromium browser (first time only)
npm run test:e2e     # Run real-browser M0 and M1 smoke/navigation tests
```

The generator writes the original 3 × 3 loader fixture plus a separate 25 × 19, 2 m-spaced terrain demo. The latter contains a fictional base slope, Gaussian hill and narrow ridge, with little-endian Float32 samples and a SHA-256 in its manifest. `docs/asset-contract.md` documents the manifest, local-path and sampling contracts. The loader validates the manifest and binary before the viewer creates geometry; it does not import geographic data.

## AOI candidate tooling

The Python pipeline is separate from the browser and uses no online grid downloads. It derives a 500 m × 500 m EPSG:27700 candidate from the configured TQ1 4HN WGS84 postcode centroid using pyproj with explicit longitude/latitude axis order. The anchor is a postcode centroid, not a property or survey point. The candidate is `selected_pending_coverage`; EA DTM coverage and local OSM/OS feature density have not been checked, and this is not a frozen AOI.

Create the isolated Python environment in PowerShell:

```powershell
py -3.13 -m venv pipeline\.venv
pipeline\.venv\Scripts\python.exe -m pip install -r pipeline\requirements.txt
```

Validate the source config and regenerate the projected selection, QA GeoJSON, and report from the repository root:

```powershell
Push-Location pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-aoi --config ..\config\aoi.torquay.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli select-aoi --config ..\config\aoi.torquay.json --output-dir ..\docs
.\.venv\Scripts\python.exe -m pytest tests
.\.venv\Scripts\ruff.exe check torquay_pipeline tests
.\.venv\Scripts\ruff.exe format --check torquay_pipeline tests
Pop-Location
```

`config/aoi.torquay.json` is the editable input. Changing only its anchor coordinates and rerunning `select-aoi` refreshes the projected centre/bounds there and regenerates `docs/aoi-selection.json`, `docs/aoi-selection.geojson`, and `docs/aoi-selection.md`. Outputs are staged and each destination is atomically replaced. The GeoJSON uses RFC 7946 longitude/latitude coordinates, contains a closed counter-clockwise polygon and the anchor point, and has no legacy `crs` member. The transform operation, reported accuracy, listed grid availability and network-grid state are included in the machine-readable report. `docs/aoi-selection.md` records the anchor/map provenance and the still-pending coverage check.

Playwright's install command downloads a local Chromium build and requires internet access. After installation, the browser tests use local files. The persistent Chromium suite covers both the retained M0 viewer and loaded terrain, pointer lock and movement, terrain grid and wireframe controls, ground-height telemetry, error retry/return, resize, Escape release, and held-key cleanup. Vitest covers movement, manifest validation, binary decoding/loading, terrain grid/sampling, and Three.js mesh geometry.

## Project documents

- `docs/project-plan.md` is the canonical working copy of the plan.
- `docs/Torquay_JS_Virtual_World_PoC_Codex_Plan.md` is the supplied source plan and is preserved unchanged.
- `AGENTS.md` records the project working rules and current authorization boundary.
- `docs/milestones/M0.md` records the synthetic M0 browser evidence.
- `docs/milestones/TVW-004.md` records the synthetic manifest, binary fixture and loader evidence.
- `docs/milestones/M1.md` records TVW-005 terrain and browser evidence.
- `docs/milestones/TVW-006.md` records the candidate AOI calculation, CLI and verification.
- `docs/milestones/screenshots/TVW-006-postcode-context.png` is the dated, attributed OSM map-context screenshot.
- `config/aoi.torquay.json` is the editable candidate anchor and size; generated bounds and provenance are in `docs/aoi-selection.json` and `docs/aoi-selection.geojson`.
- `docs/asset-contract.md` describes synthetic fixture provenance, coordinates, triangulation and sampling semantics.

The original plan remains preserved unchanged at `docs/Torquay_JS_Virtual_World_PoC_Codex_Plan.md`; the canonical copy records the verified anchor and pending candidate square. Coverage inspection, data availability and any final frozen AOI remain M2 work for a separately authorized issue.
