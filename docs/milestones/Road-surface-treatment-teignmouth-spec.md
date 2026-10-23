# Teignmouth circled road-surface correction

Status: coordinator-accepted specification, 23 October 2026. This is a focused continuation of the user-authorized road-surface preview, prompted by the circled Teignmouth Road section in `codex-clipboard-398f65b1-a0a7-402d-98b4-b886d2d0d566.png`. It is not TVW-016. Use the Torquay Sol/Luna/independent-Sol protocol. Keep all candidates local and opt-in.

## Objective

Resolve the remaining conspicuous transverse road wedge visible in the user's captured view. The accepted preview halves cross-slope at this location but leaves a road ribbon that still looks excessively steep. A new candidate must treat the shared display terrain and road coherently, retain OSM centerline geometry and the source-derived longitudinal profile, and be compared against both source terrain and the accepted preview. Do not change the default route, accepted preview bytes, source GIS, active or historical packages, AOI or public Site.

## Registered location and current measurements

- Source feature: Teignmouth Road, OSM way `78455395`, part 0.
- Bounded treatment and assessment window: centerline stations 140–155 m; sample spacing no greater than 1 m, including source vertices and the registered worst section.
- Registered anchor: station `148.15104603556912` m, local X/Z `[-139.6017351396, -95.8223807515]`, BNG E/N `[290969.3000825, 65449.3058892]` from the accepted package QA.
- The configured 6 m width is a visual estimate, not a measured road edge.
- At the anchor, current accepted-preview full-width crossfall/span is `46.997399% / 2.819844 m`; source terrain is `94.028134% / 5.641688 m`. The anchor is classified treated. The published centerline is retained within `0.10 m`.
- The anchor's road edges project to `[969.642,104.609]` and `[991.435,122.168]` pixels in the captured 1440 × 960 viewport; center projects to `[980.208,115.408]`. This locates the white-circled orange mound, not an exact user-selected point.
- The high-resolution EA DTM has approximately `91.484%` crossfall beneath this estimated ribbon; this describes terrain, not engineered pavement.

## Comparison capture poses

Capture the original view in Chromium at 1440 × 960, DPR 1, FOV 54°, with the exact same absolute pose for source terrain, accepted preview and new candidate:

```text
XYZ [-136.407629, 7.750687, 99.286006]
bearing 344.6°, pitch -24°
```

Also capture the unobstructed close oblique view from the same absolute pose for every variant:

```text
XYZ [-156.818885, 6.073672, -77.695888]
bearing 43.526184°, pitch -17.129901°
target distance approximately 25 m
```

Add a close overhead comparison that shows all of stations 140–155 m, the full estimated width and nearby terrain/building context. Record the explicit pose, target projection, camera FOV, viewport, DPR, runtime/console/network results and screenshot hashes. Verify Chromium actually shows the full target without a building or UI obscuring it. Save new material under `docs/milestones/artifacts/Road-surface-treatment/teignmouth-circled-segment/`; never overwrite prior evidence.

## Candidate and safeguards

1. Generate a separate ignored derivative at `public/worlds/torquay-road-surface-teignmouth-candidate/`. Keep the accepted `public/worlds/torquay-road-surface-preview/` byte-for-byte unchanged. Any output-path expansion must be a strict exact-path allowlist with the existing symlink, overlap, ownership and source-preservation guards intact.
2. Reuse the existing deterministic centerline-anchored shared-surface method. Do not change source X/Z, configured width, source elevation, centerline longitudinal profile, AOI or source identity. Do not make a road-only mesh float over unchanged terrain, add manual height patches, silently narrow the road or call the candidate surveyed/engineered data.
3. Retain every existing global terrain-change, added-gradient, building-footing, longitudinal-profile, junction, source-integrity and preservation limit. Include nearby building `osm:way:208684847` (about 13.19 m from the anchor) in numerical and visual review. If a local candidate cannot meet the new section gate without breaking an existing limit, report the conflict and stop; do not weaken prior gates.
4. New local endpoint gate: at stations 140–155 m, including anchor 148.151046 m, sample the complete configured 6 m width every 0.25 m including both edges. Maximum absolute local lateral slope is ≤5% and endpoint-to-endpoint height span is ≤0.30 m. These are preview visual-QA thresholds only, not claims about real-road design.
5. At the registered section, source-baseline-to-candidate centerline deviation is ≤0.10 m. Recheck the longitudinal elevations/grades at ≤1 m along the window and retain the previously accepted signed-grade limits. The source longitudinal hump at station 148 m is deliberately retained; if that is still what the user means by “flat”, report it as a separate unresolved longitudinal-policy choice.
6. Verify unchanged source road geometry and width, fixed-triangle road/terrain agreement, finite deterministic output, exact unchanged source bytes, candidate identity/hash binding, fallback on missing/invalid derivative, and 1.70 ±0.05 m walk clearance.

## Visual acceptance

- The candidate removes the conspicuous transverse gold wedge in the original registered camera view compared with the accepted preview and source baseline.
- Close oblique and overhead views show continuous road contact, no terrain protrusion, floating edges, cracks, new conspicuous shoulder wall or obscured section.
- The candidate clearly improves the registered 140–155 m section in actual screenshots. Numeric results alone cannot substitute for visible browser evidence.
- The default `/`, accepted preview, current/historical data packages, public build/share behavior and pending AOI remain unchanged.

## Files and verification plan

Expected changes: bounded output configuration/path validation in `pipeline/torquay_pipeline/road_surface.py`, its tests, a separate exact-path candidate config, an isolated Playwright comparison that can serve the candidate without changing the product loader, and this issue's handback/evidence. The implementation may refine this list after inspection, but must not expand product scope.

Run the focused Python road-surface/alignment/road/terrain tests, Ruff and formatting; repository typecheck, lint, format and Vitest excluding unrelated untracked `sites/**`; deterministic candidate builds using fresh unused execution records; the dedicated Chromium same-camera comparison; applicable default/preview/historical/share regressions; and `git diff --check`. Record actual commands and results. Preserve port 5173 and use isolated port 4213 for browser QA. Independently review the exact generated candidate, measurements, captures and hashes before marking this correction accepted.

## Preservation and scope boundary

Keep AOI `selected_pending_coverage` / `not_checked`, the TQ1 4HN centroid, current and historical packages, GIS inputs, original road-surface preview, existing milestone reports/screenshots, public Site source, installer, recovery material and port 5173 unchanged. No publication, default activation, TVW-016, other issue or source-data acquisition is authorized.

## Implementation review outcome — blocked under the 2 m grid

**Status: BLOCKED; this specification is not accepted as implemented.** The candidate-only implementation is retained as a failed diagnostic, but it produced no derivative, build record, browser run or comparison screenshot. The registered Teignmouth section therefore remains visibly unresolved in the accepted preview.

Independent Sol review established that increasing the projection iteration limit cannot solve the accepted local criteria on the current 2 m terrain representation. A read-only phase-I feasibility check over the 42 original grid vertices supporting the target samples found the inclusive 5% lateral constraints feasible alone, but contradictory after adding the required ±0.10 m centerline envelopes. Its numerical certificate reduces the constraints to `0 ≤ −0.0130248506123 m` (combined variable coefficients ≤ `1.23e−14`). The relaxed check omitted global gradient, building, ownership and fixed-node restrictions, so this demonstrates a local representation conflict, not that any alternative surface is globally safe. A 1 m representation also failed the necessary local feasibility check; a 0.5 m representation had a local feasible witness only, without global or transition checks.

No accepted threshold was relaxed. Keep the existing `/` route and accepted preview unchanged. A separately reviewed and authorized bounded investigation could test a 0.5 m local conforming shared-surface representation while retaining all current local and global limits. Its required signed-grade verification at ≤1 m, building/transition checks, deterministic candidate output and same-camera browser evidence remain outstanding. Do not describe the 0.5 m feasibility probe as an implemented fix.

### Checks and preservation

- `pipeline/.venv/Scripts/python.exe -m pytest tests/test_road_surface.py tests/test_road_alignment.py tests/test_roads.py tests/test_terrain_export.py -q` — **74 passed, 1 skipped**. The skip requires Windows directory-symlink privilege unavailable to this account.
- `pipeline/.venv/Scripts/python.exe -m ruff check torquay_pipeline/road_surface.py tests/test_road_surface.py` — passed after correcting one line-length issue; `ruff format --check` — passed.
- `npm.cmd run typecheck`, `npm.cmd run lint`, `npm.cmd run format:check`, `npx.cmd vitest run --exclude "sites/**"` — passed; Vitest **307 tests across 26 files**.
- `git diff --check` — passed. No candidate assets or new browser screenshots exist; browser verification and deterministic candidate builds were not run because the strict feasibility gate failed.
- The accepted preview assets still match their recorded SHA-256 values: `heightfield.f32` `037a74320557088135e0885386c24fdcdea6171469db1d6329c3e82997f5c1e9`, `manifest.json` `9a3cb6c08fb57a19f94e1215ac526b1baf28634d38be1ffc7d4ed61f2de7c6f7`, and `qa.json` `43d7058a339416d308be09292598949d3d97f4b764a147ccc2d5fb771d434f20`.

## Authorized additive amendment — local 0.5 m conforming surface, 23 October 2026

**Status:** the user explicitly authorized this representation amendment. Proceed under the existing Sol planner / Luna implementer / independent Sol reviewer protocol for the same focused Teignmouth correction. The 2 m candidate above remains blocked and unaccepted; preserve its diagnostics as history. No further representation approval is required to perform the bounded work below. This authorizes a local opt-in candidate, not default activation, publication, a replacement source dataset, or TVW-016.

All earlier numeric, visual and preservation gates remain binding. This section replaces only the assumption that the candidate must use a uniform 2 m display grid. Any conflict with an earlier status saying that representation authorization is pending is superseded by this explicit authorization.

### Evidence boundary and staged go/no-go plan

The independent read-only probe found the local lateral/centerline requirements infeasible on the 42 supporting vertices of the original 2 m triangles, even without global edge, building or fixed-node restrictions. Removing numerical headroom did not remove that conflict. A further local probe using the unchanged source sampler found a 1 m representation infeasible with the local signed-grade constraints, while a 0.5 m representation admitted a numerical witness over 434 vertices (maximum residual approximately 7.2e-14 m).

That witness is a feasibility hint only. It did not include complete patch boundaries, building footprints, global slope checks, renderer Float32 conversion, road re-triangulation or browser evidence. It does not establish that the full candidate is feasible or visually useful.

1. **Offline gate:** construct the bounded composite topology and solve against the complete unchanged constraints, including seam, influence, building and local signed-grade requirements. Recheck the quantized final triangles. Require a feasible final candidate and passing numerical/topology QA before implementing its browser activation. On failure, record the actual conflicting constraints or unresolved solver result and stop this attempt; do not increase domain/resource limits or weaken gates to obtain a pass.
2. **Integration gate:** implement and test the separate typed asset contract and shared display surface, keeping source validation and default routes intact. Missing/invalid data must exercise the coherent fallback before visual acceptance.
3. **Evidence gate:** build twice deterministically, run actual same-camera Chromium comparisons and runtime regressions, inspect every image, then obtain independent Sol review. Numerical success alone is not completion.

### Immutable base, scope and exact output

The composite display uses the accepted build-19/20 preview outside the patch. Bind its manifest, heightfield and QA hashes listed above; do not regenerate or overwrite it. Original release terrain remains the baseline for source-derived anchors, earthwork, building and longitudinal comparisons. Refinement samples the existing piecewise planar source/accepted surfaces; it introduces no claim of new measured 0.5 m elevation data.

Retain way `78455395`, part 0, the 140–155 m window, exact registered anchor, original X/Z and configured 6 m width. Retain the 32 m maximum transition distance beyond the configured ribbon edge and existing bounded along-road fades. Derive bounds in Python from those constraints, snap them to complete source 2 m cells, and record the resulting coordinates and affected coarse cells. Do not broaden treatment to another issue or silently narrow the ribbon.

Use exactly `public/worlds/torquay-road-surface-teignmouth-candidate/`, already reserved for the failed candidate, with a new distinct package type and algorithm version. There are no accepted candidate assets at this path to replace. Keep the accepted preview and all source/current/historical roots protected. Extend only the exact owned filename allowlist needed by the new contract; retain preflight before directory creation or any output write, canonical containment, symlink/junction rejection, ancestor/descendant protection, bounded temporary ownership and exclusive new execution records. Record protected hashes before and after generation.

### Patch topology and seam contract

- Generate **one patch**, with a 0.5 m regular interior and a conforming transition collar to the original 2 m boundary. Maximum axis-aligned bounds are **160 m × 160 m**; actual bounds must follow the permitted target/transition influence. This is a hard resource ceiling, not permission to deform the entire rectangle.
- Remove exactly the covered coarse terrain faces before inserting replacement triangles. Use an explicit coarse-cell replacement set. A road-only overlay, a second overlapping full-world terrain mesh and depth-bias concealment are prohibited.
- The outer patch boundary uses the existing 2 m boundary vertices/edges, with identical Float32 X/Y/Z and deterministic IDs/ownership. Coarsen the inner fine mesh through an explicit stitched collar; no hanging edge vertex, T-junction, overlapping face or hole is permitted. Preserve original triangle breaklines wherever necessary to represent unchanged accepted terrain exactly as planes.
- Outside the permitted deformation influence, the composite surface equals the accepted preview surface. Inside the rectangular mesh replacement but outside deformation, refinement must reproduce the accepted piecewise planes rather than merely copy heights at a few vertices. Source and accepted heightfield bytes remain untouched.
- Require upward winding, finite nondegenerate triangles, a single-valued X/Z surface, complete polygon coverage and paired interior edges. Boundary mesh and sampler agree within the existing 1 mm Float32 tolerance; shared boundary vertex bytes match exactly. Check terrain normals/shading at the seam and define a common boundary-normal policy so separate draw batches do not create a conspicuous seam.
- A uniform 2 km 0.5 m replacement would require 4001 × 4001 samples and 32 million terrain triangles. It is outside this amendment. A full-world 2001 × 2001 replacement is also outside scope.

### Concrete candidate asset contract

Introduce `packageType: "road-surface-local-triangle-patch"`, `formatVersion: 1`, and a new supported algorithm identifier distinct from `road-surface-preview-3.0.0`. The old heightfield derivative schema/loader must not accept this package by relaxing its grid checks.

Owned files under the exact candidate directory:

| File                         | Content                                                                                                                                              |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `manifest.json`              | Bounded typed metadata, identities, counts, descriptors, patch bounds, coarse-cell replacement runs, seam policy and road batch ranges               |
| `terrain-vertices.f32`       | Little-endian Float32 local X/Y/Z triples for indexed patch/collar vertices                                                                          |
| `terrain-indices.u32`        | Little-endian Uint32 triangle triples referencing patch vertices                                                                                     |
| `road-vertices.f32`          | Little-endian Float32 X/Z pairs for affected display-road/path batches; Y is derived from the validated composite surface plus existing layer offset |
| `road-indices.u32`           | Little-endian Uint32 triangle triples, partitioned into existing display groups                                                                      |
| `road-terrain-triangles.u32` | One patch triangle ID per replacement road/path face                                                                                                 |
| `qa.json`                    | Bounded runtime validation summary and hashes pointing to the detailed offline evidence                                                              |

The manifest binds the exact original release ID, readiness/inventory, terrain and road manifest/payload identities, building payload identity, and all three accepted-preview hashes. State local metre coordinates, north at negative Z and the unchanged vertical origin. Include explicit byte lengths, element counts and SHA-256 for every asset, mesher/solver/parameter versions, grid alignment, selected source feature/part/window and the mathematical meaning of refinement.

Cap the manifest at 256 KiB and runtime QA at 512 KiB. Asset paths are fixed owned basenames only, fetched same-origin with redirect rejection, exact declared/read lengths and streaming limits. Validate index ranges, overflow, Float32 finiteness, triangle containment/winding, coarse-cell set bounds, seam identity and source/base hash agreement before installation. Detailed station, feasibility and preservation reports belong in the issue evidence directory and need not be fetched at runtime.

### Terrain, roads and shared-surface integration

The present `TerrainGrid`, `createTerrain` and published road references assume a uniform grid. Do not pretend this patch is another `displayHeights` array or change the original manifest to make it fit those assumptions.

Add a narrow `DisplaySurface` abstraction that provides the world extent, deterministic `sampleHeight`, containing-triangle identity and bounded triangle queries. The ordinary grid implementation retains existing behavior. The candidate implementation combines the immutable accepted grid outside the replacement cells with the indexed patch/collar inside them, using a spatial lookup rather than a full triangle scan per sample.

Keep source-package validation against the immutable original source grid. Then assemble the display derivative separately. Existing source batches reference original `[row,column,triangle]` cells; replacing only their vertex heights would let faces cross fine surface triangles and break drape. Offline Python must reclip the affected validated road and path footprints against the new triangles. Preserve source alignment, configured width, display-group priority/union and horizontal coverage; retain existing degenerate-area limits and report quantization effects. Unaffected source faces remain unchanged. Each replacement display face references its exact owning composite triangle and meets the existing +0.05 m road offset and 1 mm drape checks.

Terrain rendering, road/path rendering, complete-footprint building-base evaluation, street anchors, bounds/spawn and ground-following walking must consume the same installed display surface. Buildings retain their original height/roof-base policy; their ground maxima must be evaluated over actual footprint/triangle intersections, not just old 2 m sample nodes. Preserve original source identity for validators and expose display identity separately.

### Unchanged numerical gates, extended to the actual composite surface

1. Sample the entire registered 140–155 m window at ≤1 m station spacing, including source vertices and anchor 148.15104603556912 m. Sample the full configured width every 0.25 m. Maximum absolute local lateral slope is ≤5%; endpoint span is ≤0.30 m; centerline deviation from original source baseline is ≤0.10 m. Preserve the source longitudinal hump.
2. Check signed longitudinal grades at **≤1 m spacing throughout the local window**, including its endpoints/source vertices, and retain the ≤2 percentage-point change limit. Add these interpolated envelope/grade inequalities to the solve rather than substituting stronger whole-triangle source pins. Keep the previously accepted full-corridor and seven-way longitudinal checks passing, including all 439 severe-station comparisons and both Parkfield controls.
3. Retain the strict <5 m absolute terrain-change and <1.0 m/m positive added-gradient gates. Preserve existing original-2 m X/Z edge checks, and assess every fine/collar triangle edge against the source surface sampled at that edge's endpoints. Report actual directional gradients and baseline comparisons. Check earthwork extrema on the overlay of final triangles with original source triangles, including intersection vertices, so an interior extremum cannot escape a vertex-only check.
4. Retain building-base p95/max absolute displacement limits of 0.183/2.424 m and local review of shifts exceeding 0.50 m. Recompute all 3,613 complete footprints against the composite surface. Newton legacy bases stay within ±0.05 m; recheck Newton/Sanford/Cavern footings. Register nearby `osm:way:208684847`, its full footprint, local sections and wall contact. No new terrain hole or intrusive retaining-like wall may be hidden behind a building.
5. Require exact unchanged protected bytes and unchanged accepted surface outside permitted influence, deterministic finite output and stable triangle ownership at boundaries. Keep fixed-triangle/road drape tolerances, candidate identity validation and 1.70 ±0.05 m walking clearance through pavement, shoulders and fine/coarse seams.

### Resource ceilings and observation

These are explicit candidate budgets, not measured performance claims or a promise of hardware FPS:

- One patch, bounds ≤160 m per side.
- Incremental terrain plus road/path replacement geometry ≤250,000 triangles and ≤150,000 vertices; report both total candidate counts and net increases over accepted-preview geometry.
- At most four additional draw calls over the same accepted-preview scene.
- All candidate runtime files together ≤8 MiB; manifest/QA individual limits above still apply.
- Additional steady-state decoded geometry buffer residency ≤16 MiB; additional peak CPU/GPU buffer residency during validated scene construction ≤64 MiB. Include temporary/replaced index buffers and avoid retaining duplicate full-world meshes after installation.
- Bounded spatial lookup and asset decoding; no full-world high-resolution array or per-walk-query scan of all patch triangles.

Measure actual payload, typed-array/geometry buffer lengths, renderer triangle/draw/geometry counters, load time, frame pacing and disposal behavior using matched camera/runtime conditions. Distinguish measured buffer sizes from unavailable driver/process memory. Do not claim smooth physical-device playback from SwiftShader observations. Stop for review rather than silently raising a ceiling.

### Isolated activation, fallbacks and visual evidence

Register the explicit **DEV-only** QA route `/?roadSurface=teignmouth-patch`. It may fetch only the fixed candidate directory after validating the current release and accepted base. Production/default `/`, the accepted `/?roadSurface=preview`, historical/synthetic routes and share builds must not request or depend on patch assets; keep the existing share allowlist excluding real candidate data. Add no product layer/world controls.

Load and validate the complete candidate before assembling the world or attaching asynchronous roads/buildings. Missing, stale, corrupt, oversized or invalid patch data must produce a truthful candidate-unavailable notice and the coherent validated accepted preview. If that accepted base is unavailable/invalid, use the existing coherent source-terrain fallback and state that actual outcome. Clear/dispose pending state on cancellation, retry and world replacement; no partially patched terrain/road scene is acceptable.

Use isolated port 4213 and the existing DEV camera hook. Capture source, accepted preview and candidate at the **identical absolute poses** already registered above: original circled viewport, close oblique, and explicit close overhead covering the full target. Keep FOV 54°, 1440 × 960 and DPR 1. Add seam/maximum-gradient and nearby-building views. Require an unobstructed target, visible removal of the transverse gold wedge, continuous terrain/road contact, and no new conspicuous seam, wall, crack or floating edge. Disclose the retained longitudinal hump separately; do not count numerical flattening as visual completion.

Save new builds, full QA, section plots, source-to-pixel overlays, deterministic input/output inventories, screenshot hashes, poses, runtime/GPU metadata, local requests/errors and walk clearances under `docs/milestones/artifacts/Road-surface-treatment/teignmouth-circled-segment/`. Use fresh unused canonical execution-record numbers under the existing dedicated build-record directory; preserve build-19/20 and all accepted captures. Re-run applicable real/share/default/preview/historical/synthetic regressions because this amendment changes runtime integration. Isolate new regression evidence and restore any accepted evidence paths byte-for-byte if existing runners overwrite them.

### Concrete implementation plan and files

1. **Python feasibility/topology:** retain `pipeline/torquay_pipeline/road_surface.py` as the source-bound entry point and add a focused `pipeline/torquay_pipeline/road_surface_patch.py` with `pipeline/tests/test_road_surface_patch.py`. Extend only the exact candidate variant/config/output allowlist. Implement local topology, road reclipping, full constraint/Float32 QA, deterministic publication and resource accounting; prove the complete offline gate first. Keep the failed 2 m candidate path/behavior documented rather than describing it as successful.
2. **Typed surface/assets:** add `src/geo/displaySurface.ts`, `src/geo/roadSurfacePatchSchema.ts`, `src/app/roadSurfacePatchLoader.ts` and focused tests under `tests/geo/` and `tests/app/`. Retain original `terrainGrid.ts` and heightfield/source schemas. Define stable composite triangle IDs and boundary rules shared with Python.
3. **Candidate-only scene assembly:** narrow changes to `src/scene/createHeightfieldWorld.ts`, `src/scene/createTerrain.ts`, `src/scene/createRoads.ts`, `src/scene/createBuildings.ts`, their focused tests, and `src/app/createApp.ts` to install one display surface and DEV-only candidate activation. Adapt label/walk consumers through that same surface interface. Do not weaken original package checks. Reuse the existing camera hook.
4. **Verification/handback:** add an isolated `tests/e2e/teignmouth-surface.spec.ts` using the existing port-4213 configuration, and update `docs/asset-contract.md`, this specification and a dedicated Teignmouth handback/evidence. Keep unrelated reports and private checkpoint outside implementation edits unless separately assigned by the coordinator.

Run focused Python road-surface/patch/alignment/road/terrain tests, Ruff check/format, repository typecheck/lint/format, scoped Vitest, two deterministic candidate builds, candidate Chromium comparisons and real/share runtime regressions, then `git diff --check`. Exercise flat/oblique/hill/curved/junction controls, conforming collar coverage, source-plane reproduction outside influence, Float32 edge/corner ownership, road area/drape, building footprint maxima, malformed mesh/oversize/path rejection, fallbacks/cancellation/disposal and resource ceilings. Record the known unrelated default Vitest `sites/**` collection conflict separately from scoped results.

An independent Sol review must verify the exact final diff, asset contract, completed constraints, preservation/resource evidence and actual images before PASS. If the complete refined candidate is infeasible, exceeds a budget or fails visual acceptance, preserve the failed diagnostic and stop for a bounded next decision; no default activation or further representation expansion follows automatically.
