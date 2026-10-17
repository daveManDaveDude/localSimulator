# Torquay Virtual World

A Windows-friendly browser proof of concept for a future real-data view of Torquay. The default viewer loads a small, checked-in synthetic Float32 heightfield and renders its terrain mesh, hill, ridge, grid and north cue. The prior M0 analytic scene remains available at `/?world=m0`.

Every current world is fictional and marked **SYNTHETIC**. The heightfield, hill, ridge, analytic slope, blocks, dimensions and elevations are invented examples; they are not Torquay measurements. Both local fixtures use zero-valued local origins and contain no geographic coordinates. No AOI, real roads, GIS downloads or real-world asset are included. TQ1 4HN remains an unverified candidate for location and coverage checks in M2.

## Requirements

- Windows 11 with PowerShell
- Node.js 22.13 or later within the 22.x line, 24.x, or 26.x and later
- npm, included with Node.js
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

Playwright's install command downloads a local Chromium build and requires internet access. After installation, the browser tests use local files. The persistent Chromium suite covers both the retained M0 viewer and loaded terrain, pointer lock and movement, terrain grid and wireframe controls, ground-height telemetry, error retry/return, resize, Escape release, and held-key cleanup. Vitest covers movement, manifest validation, binary decoding/loading, terrain grid/sampling, and Three.js mesh geometry.

## Project documents

- `docs/project-plan.md` is the canonical working copy of the plan.
- `docs/Torquay_JS_Virtual_World_PoC_Codex_Plan.md` is the supplied source plan and is preserved unchanged.
- `AGENTS.md` records the project working rules and current authorization boundary.
- `docs/milestones/M0.md` records the synthetic M0 browser evidence.
- `docs/milestones/TVW-004.md` records the synthetic manifest, binary fixture and loader evidence.
- `docs/milestones/M1.md` records TVW-005 terrain and browser evidence.
- `docs/asset-contract.md` describes synthetic fixture provenance, coordinates, triangulation and sampling semantics.

The working plan does not commit AOI coordinates or placeholder AOI configuration. Location verification, coverage inspection and the frozen 500 m square belong to M2.
