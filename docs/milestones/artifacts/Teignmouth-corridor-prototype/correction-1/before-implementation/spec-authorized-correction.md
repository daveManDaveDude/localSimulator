# Teignmouth corridor-grading prototype

Status: coordinator-accepted fresh experimental issue, 24 October 2026.

## Authorization and issue boundary

The user explicitly authorized a fresh budget and a separate opt-in prototype using the BeamNG.Earth-style shared road/terrain corridor method, with comparison against the current source-draped road. This is a new issue, not a continuation or budget reset of Teignmouth topology-validation v2. The v2 issue remains FIX REQUIRED, exhausted, and unaccepted. Do not edit its runner/config/evidence, enable activation, create permits, or claim v2 acceptance.

Budget for this issue: initial implementation starts with Sol 6.1 medium; at most one Sol correction; one independent Sol review. No parameter sweep. At most one bounded feasibility diagnostic (120 seconds), then at most two deterministic full candidate builds (180 seconds each; the second checks reproducibility). If the sole correction is used and the independent review still finds a substantive failure, stop and report NEEDS USER DECISION.

## Objective

Create a local-only prototype that grades a shared terrain/road corridor for the registered Teignmouth Road section, then compare it with the source-draped baseline in identical views. This is an experimental display treatment, not surveyed pavement data or a replacement elevation source. Keep the public/default viewer, accepted preview, published site and GIS packages unchanged.

## Registered source and target

- Current release: `616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a`.
- Road feature: OSM way `78455395`, part `0`; retain its packaged centerline X/Z and configured estimated 6 m width.
- Assessment stations: 140–155 m, including registered anchor station `148.15104603556912` m at local X/Z `[-139.6017351396, -95.8223807515]` and BNG E/N `[290969.3000825, 65449.3058892]`.
- Existing input elevation is the packaged EA DTM-derived 2 m grid. Do not describe interpolation or resampling as new higher-resolution source data.
- Preserve TQ1 4HN centroid, AOI `selected_pending_coverage` / `not_checked`, historical package, accepted preview assets, current data, source bytes and Site.

## Prototype treatment

Implement a deterministic road-corridor surface as a separate Python builder and a standalone DEV comparison page. Do not modify the product loader or the rejected v2 solver.

- Reuse the source centerline and estimated width. Resample the packaged full road-part profile at 2 m intervals and apply the pinned BeamNG.Earth Gaussian recipe: sigma 12 m, radius `ceil(3*sigma/step)` (18 samples / 36 m here), normalized weights, reflection at the profile ends when the profile has more than the kernel radius, otherwise edge padding. Record all resulting centerline elevation and signed-grade differences. Profile reads outside the treated rectangle are allowed only from this already packaged road part; they do not expand the terrain-treatment domain. Reference reviewed at commit `a08461b1b99aa38e296c9464b72e9ab11ab25ca9`, `server/grading.py` and `native/earthfast/src/lib.rs`; implement an independent equivalent and do not import BeamNG code.
- Shape one conforming surface: flatter cross-section across the carriageway plus a 1 m shoulder; transition to unchanged source terrain with the documented 1:2 slope rule and 2–12 m blend distance. Record the actual profile and transition parameters in the candidate manifest.
- Build a local 0.5 m conforming patch snapped to existing 2 m grid boundaries, with patch boundary heights exactly matching the source surface. Remove replaced coarse terrain faces, and use one composite display-surface sampler for the candidate terrain, roads, nearby building contact and walking. No overlay ribbon concealing unchanged terrain, stacked meshes, manual point-height patch or disconnected road-only mesh.
- Keep the patch within the already registered Teignmouth local domain and its existing influence/fade bounds. Do not add an arbitrary memory or payload-byte cap. Measure and report actual peak memory, buffer sizes, vertex/triangle counts and load time; the geographic domain, fixed recipe, attempt count and wall-clock limits bound this experiment.
- Exclude structures tagged as bridges/tunnels/off-ground from normal corridor grading. Resolve junction/nearby-road ownership deterministically; stop if the target cannot be isolated within this local domain.
- Generate ignored candidate data under `data/generated/teignmouth-corridor-prototype/`, outside `public/`. Serve only fixed allowlisted files through a standalone Vite DEV config on strict port 4213. No candidate asset may enter product/share builds or be requested by `/` or `/?roadSurface=preview`.
- Label the view: “Experimental corridor grading · estimated road width · interpolated EA DTM terrain”.

## Evaluation and stop conditions

Keep every existing source, preservation, global terrain-change, building-footing, added-gradient, junction and longitudinal-profile limit. Preserve registered old local thresholds as evaluation criteria; do not weaken them to obtain a candidate. Report any deviation from source centerline elevation (≤0.10 m prior local criterion), signed-grade limits, ≤5% full-width cross-slope, ≤0.30 m full-width span, and the existing global earthwork/added-gradient ceilings. The prototype can be shown as an experimental comparison when a local QA target fails, but it cannot be described as an accepted fix or promoted. Stop before browser integration for non-finite geometry, invalid topology, unresolved ownership, changed protected bytes, a global safety-ceiling violation, required domain expansion, timeout, or loss of coherent fallback.

Include nearby building `osm:way:208684847` and every complete building footprint within the candidate influence in numerical and visual contact checks. Verify finite Float32 geometry, nondegenerate upward triangles, exact shared boundaries, no holes/T-junctions/overlaps, and road/terrain agreement within 1 mm after the existing +0.05 m visual road offset. Walking must sample the same display surface and retain 1.70 ±0.05 m eye clearance.

## Comparison evidence

Use one standalone local harness and identical source assets, materials, lighting, viewport and camera matrices for source-draped baseline and graded corridor. Capture Chromium at 1440 × 960, DPR 1 and FOV 54°:

- Original circled view: XYZ `[-136.407629, 7.750687, 99.286006]`, bearing `344.6°`, pitch `-24°`.
- Close oblique: XYZ `[-156.818885, 6.073672, -77.695888]`, bearing `43.526184°`, pitch `-17.129901°`.
- Freeze and record a close overhead pose that shows stations 140–155 m, full estimated width, transition shoulders and nearby building context before capture.

Save new paired screenshots and machine-readable camera/runtime evidence under `docs/milestones/artifacts/Teignmouth-corridor-prototype/`; never overwrite prior captures. Inspect every image. Record target visibility, screenshot hashes, browser console/network results, mesh statistics, asset bytes, actual memory and frame/load measurements. Include the accepted preview as a read-only third comparison when its existing asset can be loaded without rebuilding it.

## Verification and handback

Run focused corridor/topology/road/terrain Python tests, Ruff and format checks; scoped TypeScript, lint, format and Vitest; two source-bound deterministic builds; actual Chromium paired comparison; malformed/missing-candidate fallback; applicable default, accepted-preview, historical, synthetic and share regressions; and `git diff --check`. Use fresh evidence paths and isolated port 4213; preserve port 5173. Record commands and actual results. A Sol reviewer who did not implement the issue must inspect the actual diff, source/preservation hashes, geometry, test results and screenshots. The handback states behavior, changed files, data provenance, commands/results, screenshot links, limitations, review verdict and next authorized action.

## User-authorized single correction — continuous station/lateral topology, 24 October 2026

After independent Sol review of build 1, the user authorized continuing with the recommended approach: use the one remaining Sol correction to try a different local corridor topology while retaining the strict `<5 m` absolute terrain-change and `<1 m/m` positive added-gradient limits. This is **not** approval to relax any criterion, resume topology-validation v2, run its guardian/permit/profile, or modify published/default assets.

### Diagnosis and correction recipe

The reported worst edge is on the inside of the packaged road bend. Independent review found a plausible cause: the first builder independently selected a nearest full-part segment/station for each raster vertex. Adjacent vertices can switch station ownership across a bend, so a raster edge can cross a discontinuous station/profile assignment. This is a structural hypothesis based on the code and reported edge, not a confirmed cause for all failure metrics.

Replace only that raster nearest-segment topology with a continuous station/lateral chart:

- Freeze cross-sections at source vertices, 0.5 m station intervals, stations 140 m and 155 m, the exact anchor station, and both longitudinal fade endpoints. Use deterministic miter/bisector joins. Interpolate station and lateral coordinates inside the chart; never reassign each mesh vertex to the nearest full-part segment.
- Keep the same full-part Gaussian profile, source centerline X/Z, estimated 6 m carriageway, 1 m shoulders, 2–12 m / 1:2 blend rule, 32 m longitudinal fade, local rectangle, source release and influence bounds from the original spec. No parameter sweep, local target adjustment, road movement, width change or threshold change.
- Node the chart, carriageway, shoulder, blend and influence boundaries into one conforming planar surface. Preserve the exact original 2 m perimeter and source planes outside the influence. Reject inverted/crossing sections, overlapping station ownership, unresolved junctions, or off-ground structure conflicts; do not expand or move the domain to avoid them.
- Before full mesh assembly, perform the `<5 m` necessary earthwork preflight in the same corrected build at chart vertices, source-plane intersections and required target samples. Record the first violating station, lateral offset, X/Z, source/candidate heights and rule, then stop. Preflight pass is necessary but not sufficient.
- For final safety, measure the source/candidate triangle overlay including intersection points and all final edge grades; require strict `<5 m` absolute change and `<1 m/m` positive added gradient. If a final geometry gate fails, persist the failed buffers and hashes only under the new evidence directory outside all runtime-serving paths, then stop. Do not create or serve a candidate derivative on failure.

### Remaining execution budget and stop

The single diagnostic invocation and original full build 1 are consumed. This correction consumes the sole Sol correction and remaining full build 2 (≤180 seconds); no third build, retry, parameter sweep or separate preliminary numerical probe. Build 2 may independently regenerate the corrected geometry in-process and compare exact hashes as supplemental determinism evidence, but it cannot claim a second independent full build of the corrected algorithm. Record this evidence limitation.

Only if preflight and all final safety/topology/provenance checks pass may the correction continue to the standalone DEV harness, road/building/walk coherence checks, remaining scoped quality gates and same-camera Chromium screenshot pairs. Browser work remains blocked if any safety, topology, ownership or protected-byte gate fails. A passing experimental comparison remains local and opt-in; it does not activate the public/default map. Independent Sol review is still required for any acceptance claim.
