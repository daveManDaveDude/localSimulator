# TVW-010 implementation specification

**Status:** Accepted for implementation on 2026-10-18 after Sol 6.1 medium specification and coordinator review. This is a browser-rendering issue only.

## Scope and boundaries

Load the already validated local TVW-009 OSM building package as an optional layer on the existing EA terrain world. Keep `/` synthetic by default, `/?world=m0`, and the existing terrain-only `/?world=torquay-poc-001`. Add an explicit terrain-plus-buildings route/toggle. Do not acquire or modify source data, add roads, change AOI coordinates/status, infer verified building heights, add walk mode, or begin TVW-011. Preserve `selected_pending_coverage` / `not_checked`, OSM/EA attribution and the working clean-clone synthetic world.

## Architecture and assets

- Add an offline publisher that first runs authoritative TVW-009 package validation, then stages and atomically publishes `manifest.json`, `buildings.json`, and `qa.json` byte-for-byte under ignored `public/worlds/torquay-poc-001/buildings/`. Publication must preserve the prior valid output on failure, be repeatable, never overwrite terrain files, and remain excluded by `build:share`.
- Load buildings only when explicitly requested. Validate nested JSON and safe same-origin package paths, size/hash, source and height semantics, QA summaries, and identity against the already validated real terrain manifest before creating Three.js resources. No transforms or remote requests in the browser.
- Preserve the TVW-009 package's local XZ coordinate convention and feature identities. Use Three.js `ShapeUtils.triangulateShape` for owned contour/hole copies; verify triangulation area, indices and winding. Support valid concave, rotated, multipolygon and holed features. Reject malformed/self-intersecting geometry with feature context; never silently repair or quietly skip a valid difficult feature.
- Build custom roofs and walls. Subdivide each outer and hole boundary at terrain grid lines and the terrain sampler's `u+v=1` triangle diagonals; sample each breakpoint with the existing `TerrainGrid.sampleHeight`. A null/nonfinite height fails the buildings layer while leaving terrain usable. Hole walls face into courtyards. Roof/wall normals stay sharp and finite.
- **Roof reference policy:** all components of a feature share a horizontal roof at `max(terrain Y across the complete footprint) + validated heightM`. Include interior terrain vertices and footprint/triangle intersections in the maximum; exclude hole interiors. This gives the supplied estimated height clearance above the highest underlying terrain and makes downhill walls taller. It is a visual placement convention, not a measured roof or foundation elevation. Document it in UI/handback and test the interior-peak case. Any small numerical burial allowance must be documented and separately tested.
- Use shared confidence materials and dispose owned GPU resources on failure/replacement/teardown. Layer retries and route changes must not append duplicate or stale geometry.

## Visible state and failure behavior

Show building load state, building and component counts, height-method breakdown, and the explicit statement that all heights are tagged-but-unverified or estimates. Display OSM extract vintage, contributor credit, ODbL link and Geofabrik credit alongside retained EA provenance. Preserve accurate pending-AOI text: mapped counts do not establish completeness; road and remaining checks are outstanding. Provide a visibility toggle, retry, continue-terrain-only, return-to-synthetic, and contextual package-publication instructions. A failed/incomplete layer must never claim to be loaded.

## Verification and acceptance

1. Add engine-independent validators for unknown/null/malformed payloads, paths, same-origin requests, size/hash, terrain/AOI/operation identity, feature IDs, duplicate geometry, height/provenance semantics and QA integrity. Test allocation limits before reading oversized payloads.
2. Cover convex, rotated, concave, hole, multi-component/island, nested-invalid, flat/slope/ridge, grid-edge/diagonal, interior-peak, AOI edge/outside, degenerate and Float32-collapse cases. Verify roof area excluding holes, upward roof winding/normals, courtyard-facing walls, constant feature roof height, and terrain contact at both segment endpoints and intermediate crossings.
3. Test deterministic asset publication, corrupt/missing inputs, injected failure/rollback, repeated layer load/toggle/disposal, and preserve terrain/synthetic recovery.
4. Extend Playwright to keep existing regressions; verify actual local package loads all 1,000 features/1,002 components, statuses/counts/provenance/toggle, navigation and recovery. Missing/corrupt manifest, payload and QA must show useful errors; no GIS network request. The actual-package browser test must run here, not be skipped.
5. Run Node typecheck, lint, format check, Vitest, build, share build and Playwright; run Python pytest, Ruff, formatter, pip check, existing building validation and publisher checks. Compare repeated output bytes/hashes with the validated source package and confirm share output excludes local real assets.
6. Run an actual browser production preview with locally published data. Inspect and save overhead and ground-eye screenshots showing footprint variety, terrain alignment, level roofs, HUD and attribution. Record browser/GPU/renderer, viewport/DPR, poses, FPS, draw calls and triangles; distinguish hardware from SwiftShader. Restore pre-existing unrelated evidence outputs after testing.

## Likely files

New: `src/geo/buildingSchema.ts`, `src/geo/buildingGeometry.ts`, `src/app/buildingLoader.ts`, `src/scene/createBuildings.ts`, corresponding tests, `pipeline/torquay_pipeline/building_publish.py`, `pipeline/tests/test_building_publish.py`, and `docs/milestones/TVW-010.md` plus screenshots.

Modify as needed: `src/app/createApp.ts`, `src/scene/createHeightfieldWorld.ts`, `src/scene/disposeSceneResources.ts`, `src/style.css`, `pipeline/torquay_pipeline/cli.py`, browser tests, building asset contract, README, canonical project status and the coordinator checkpoint. Do not edit the supplied original plan, the AOI config, the source package or dependency pins.

## Current API/package evidence

Installed: Three.js 0.186.1 / types 0.186.0, Vite 8.3.4, TypeScript 6.0.3, Vitest 5.0.5, Playwright 1.64.1; no dependency addition is required. Three.js documents [`ShapeUtils.triangulateShape`](https://threejs.org/docs/pages/ShapeUtils.html), opposite winding for shape holes in [`Shape`](https://threejs.org/docs/pages/Shape.html), and indexed custom mesh attributes/normals/disposal in [`BufferGeometry`](https://threejs.org/docs/pages/BufferGeometry.html). Vite's [`public` assets](https://vite.dev/guide/assets.html) are served locally and copied to build output; the existing share-build exclusion must remain in effect.

Local package inspection: 1,000 OSM features, 1,002 polygon components, zero actual holes, 998 default-height estimates and two `building:levels` estimates. This is a dated mapped-data count, not completeness evidence or verified heights. The terrain is the validated 501 × 501 grid at 2 m spacing for the unchanged pending 1,000 m TQ1 4HN candidate.
