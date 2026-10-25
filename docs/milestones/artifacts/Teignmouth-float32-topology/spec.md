# Teignmouth Float32 topology representation 1

Issue ID: `Teignmouth-float32-topology-representation-1`.

Status: **PLANNED; coordinator acceptance and execution reservations pending.** Date: 24 October 2026. This document authorizes no execution by itself.

## Authority and distinct scope

The user replied “Continue” to the explicit handback proposal for a separately bounded approach to representable topology. This supports a distinct local representation investigation, followed by an opt-in comparison only if every required gate passes. The current dispatch permits planning documents and a new proposed zero-counter ledger only; no code, numerical diagnostic, test, build, profile or browser work was performed during planning. The coordinator accepts the plan and reserves each executable attempt before dispatch.

This is a representation issue, not a renamed retry of `Teignmouth-corridor-prototype-continuation-1`. That predecessor remains **exhausted / NEEDS USER DECISION**, with four Luna corrections, one Sol correction, six implementation builds and one diagnostic consumed. Its unused confirmation/diagnostic allowance cannot repair or run this new issue. Preserve its complete code, config, evidence and counters as history. Topology-validation v2, its guardian/permits and other topology-refinement issues remain untouched and inactive. No source, package, AOI, product/default viewer, accepted preview, Site or publication change is authorized.

## Frozen road, field and limits

Inherit the actual frozen field and constraints from `docs/milestones/Teignmouth-corridor-prototype-continuation-spec.md` and its candidate-local limit decision 1. Pin their exact bytes in the new issue's input manifest before execution; do not edit them to implement this issue.

- Release: `616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a` and its readiness/inventory/terrain/road/building descriptors.
- OSM way `78455395`, part 0, source X/Z and estimated 6 m carriageway; 1 m shoulders; fixed Gaussian sigma 12 m, 2 m profile sampling, 2–12 m / 1:2 blend, 32 m fades and existing 35 m target influence.
- One patch in the existing rectangle X `[-182,-98]`, Z `[-136,-54]`; 0.5 m local display refinement. No domain, road footprint or source-resolution expansion.
- Assessment stations 140–155 m, including the exact registered anchor 148.15104603556912 m, source vertices and endpoints.
- Strict absolute source-relative terrain change **<6.5 m**; strict positive added edge gradient **<1.0 m/m**; full-width local cross-slope **≤5%**; full-width height span **≤0.30 m**; centerline source-height deviation **≤2.0 m**; absolute longitudinal grade **≤10%**.
- Existing building-footing limits remain: global p95 ≤0.183 m, maximum ≤2.424 m; Newton legacy ±0.05 m; inspect every displacement >0.50 m. Include every complete footprint intersecting deformation, including holes and `osm:way:208684847`, rather than selecting by centroid.
- Preserve source attribution, TQ1 4HN, AOI `selected_pending_coverage` / `not_checked`, historical/current packages and synthetic fallback. This is an interpolated experimental display surface, not surveyed pavement.

No tolerance, collision guard, grading recipe or limit may be relaxed to pass this issue. Any such proposal is a stop for a separate coordinator/user decision.

## Known failure and uncertainty

Predecessor build 6 rejected distinct Float64 construction points `(-164.2316811012587,-85.5)` and `(-164.23167542853238,-85.5)` because their global X/Z Float32 byte keys collide. Its trace stops inside `road_surface_topology.build_constrained_mesh`, before a complete final mesh is returned. The guard is correct for its global-buffer contract.

The predecessor's complete preflight diagnostic measured 6.397848390875038 m maximum absolute change over 21,336 required samples; it does not certify continuous-field, final overlay or gradient extrema. Build 6's preflight/core-ownership passes are control-flow inferences because its exception handler discarded detailed intermediate reports. None of this establishes a usable candidate.

The observed pair is separated by approximately 0.00000567 m. Float32 spacing near global magnitude 164 is approximately 0.00001526 m; near patch-local magnitude 24 it is approximately 0.00000191 m. This suggests, but does not prove, that a fixed local frame can preserve that pair. Other construction points may be closer, local re-noding may introduce different numerical distinctions, and road/terrain serialization or transforms can reintroduce quantization. No fix is selected as proven by this plan.

## Minimal diagnostic and decision gate

Reserve one **topology-only diagnostic, ≤120 seconds**, after coordinator acceptance. Use exactly `pipeline/.venv/Scripts/python.exe`; verify its GIS-free imports and record executable/version before numerical work. Fresh evidence goes under this issue's `diagnostic-1/`, never under a predecessor or implementation-build leaf.

Use one predetermined candidate frame: `originXYZM = [-140,0,-95]`, the exact integer centre of the existing rectangle, with metre units, unchanged Y and north at negative Z. No origin search, scale change, rotation, threshold sweep or automatic tiling. Translate the same frozen linework/domain into this frame and inspect the complete noded/triangulated arrangement's construction vertices. Enumerate exact Float64-to-local-Float32 aliases, including the recorded pair. Reuse the existing collision-key guard semantics; diagnostic enumeration does not authorize merging a failing pair.

The diagnostic produces topology precision evidence only: actual input identities, local/global bounds, vertex/pair counts, all collision witnesses or an explicit zero count, round-trip displacement, winding/degeneracy and constrained-edge/seam observations where computed. Retain raw arrangement/vertex witnesses and the algorithm's exact coordinate convention. Do not grade or publish a complete terrain/road candidate as a diagnostic. Do not label checking only the known pair a complete representability pass.

Assess the actual installed Three.js transformation path from local buffers to final view/clip position. Record which operations use JavaScript Float64 versus GPU Float32. Confirm that no intermediate global Float32 vertex buffer or key conversion recreates the old collision. Diagnose the known pair under the registered camera transforms with Float32-equivalent operations; distinguish numeric reconstruction error from ordinary subpixel projection and do not claim screen-coordinate equality proves a topology defect or absence of one.

**Go:** all actual construction vertices are uniquely representable in this fixed stored frame, mandatory constraint identities remain meaningful, and a coherent runtime/source-frame contract is credible. **No-go:** any required collision, inverted/degenerate subdivision, uncontrolled coordinate movement, seam incompatibility, lost constraint or timeout. Record the result and stop; do not try another origin or representation automatically. This gate is not final-mesh or runtime acceptance.

## Representation and runtime contract

If the diagnostic supports implementation, add a new explicitly versioned prototype contract, rather than weakening the existing global-X/Z Float32 contract.

- Store X/Z as actual local Float32 coordinates with explicit immutable origin metadata. Keep source centreline/footprint metadata in its original global coordinates. Y remains the pinned vertical-origin convention; do not introduce a height rebase.
- Invoke the unchanged collision guard in the coordinates actually serialized. Two distinct Float64 construction coordinates mapping to one stored local Float32 key still fail, with no epsilon merge or silent deduplication.
- Reconstruct world coordinates for Python QA and JavaScript sampling as `origin + Float64(decodedLocalFloat32)`. Do not cast these reconstructed world coordinates back to Float32 for meshing, identity, overlay, road ownership or CPU sampling. Report serialization displacement and rerun every geometric gate on that actual decoded surface.
- Pin exact source-perimeter world X/Z and original Float32 Y. The integer origin allows integer 2 m perimeter positions to remain exact, but that must be verified for every boundary vertex/edge. Retain source breaklines outside deformation and prove unchanged source planes after reconstruction.
- Prefer one prototype display frame for source terrain, replacement patch and contact-dependent layers, with a shared origin transform. Merely rebasing the patch while rendering unrelated world-coordinate buffers is not sufficient proof of a crack-free seam. Apply frame conversion through one typed surface/frame interface, not ad-hoc transforms in render logic.
- Keep position attributes local through upload. Installed Three.js projects using `modelViewMatrix` directly, but some shader paths also construct `worldPosition`; inspect every enabled material/lighting/picking path. CPU matrix composition and GPU uniform quantization must preserve the intended sampling/visual contact within existing tolerances. Do not add high/low shaders, floating-origin machinery or new dependencies automatically if this simple frame fails.
- Report boundary reconstruction exactly and GPU/view-space error separately. Use existing 1 mm road/terrain tolerance and geometric coverage checks; do not invent a looser coordinate tolerance. Test seams with the same frame/matrix path on both sides. No claim that every subpixel triangle remains distinguishable in screen pixels is required or appropriate.

## Offline acceptance before any browser integration

Persist source/config/code/frame identities and actual chart/final buffers on failures as well as success, outside runtime-serving paths. Preserve the most recent completed stage's report even when a later stage raises; include typed errors and truthful unavailable gates.

Required gates, in order:

1. Frozen input/provenance and frame validation; complete local Float32 uniqueness; no coordinate collisions, nonfinite values, overflow, inverted/nondegenerate-face failure, missing constrained edges, holes, overlaps or T-junctions. Validate actual stored bytes and reconstructed world surface, not only construction vertices.
2. Complete final indexed mesh; exact source perimeter X/Z/Y and seam coverage; source-plane reproduction outside influence; deterministic triangle ownership and normal policy.
3. Complete candidate/source triangle overlay extrema, including intersections; strict <6.5 m earthwork; all final edge and retained original-grid added-gradient controls strictly <1.0 m/m. No sampled-preflight maximum substitutes for this overlay result.
4. Full actual serialized-surface sections at ≤0.5 m station spacing, source vertices/endpoints/anchor, and ≤0.25 m offsets across the 6 m width. Require all four section/profile gates, including actual mesh signed grades across the whole window.
5. Real nearby-road/path ownership, junctions and off-ground exclusions over the entire affected influence, not only the target core. Reclip roads to the same final triangles, preserving original source identity/footprint/area constraints and existing +0.05 m visual offset; drape error ≤1 mm.
6. Recompute all complete affected building footprints and global footing statistics using certified unchanged outside values; retain existing global/base and Newton controls. Building roofs/bases must not be changed merely to conceal grading defects.
7. Same composite display surface for road/building/label/walking consumers; pavement, shoulder and seams covered; walking eye clearance 1.70±0.05 m. Missing data/invalid frame must give one coherent source fallback, with no partial patch and truthful notices.
8. Protected bytes unchanged, measured geometry/buffer/memory/time results, and an independently regenerated passing candidate with identical ordered serialized hashes. A confirmation build verifies a passing candidate; it cannot repair a failing one.

Offline tests may inspect runtime frame math without launching a browser. Browser integration/captures remain blocked until all offline gates pass. Preserve failures as failures, not merely “experimental” acceptance.

## Files and isolation

Expected new files, created only after plan acceptance:

- `pipeline/torquay_pipeline/road_surface_float32_frame.py`: typed frame encoding/decoding and collision-preserving local construction adapter.
- `pipeline/torquay_pipeline/teignmouth_float32_candidate.py`: frozen-field reuse, new frame contract, complete staged QA and candidate assembly.
- `pipeline/scripts/diagnose_teignmouth_float32_frame.py` and `pipeline/scripts/build_teignmouth_float32_candidate.py`: bounded single-attempt CLI, interpreter check, durable stage reports and strict fresh paths.
- `pipeline/tests/test_road_surface_float32_frame.py` and `pipeline/tests/test_teignmouth_float32_candidate.py`.
- `config/road-surface-teignmouth-float32.json` with pinned inherited limits/recipe and the single fixed origin.
- Only after offline acceptance: isolated `src/prototypes/teignmouthFloat32/` frame/schema/sampler/loader/scene modules and tests, a standalone DEV entry, dedicated Vite/Playwright configs and comparison test.

Keep predecessor continuation code/config/runner/test bytes and `road_surface_topology.py` unchanged; import compatible pure helpers read-only. Do not update its guard to bypass collisions. Any extra shared-helper change requires a concrete dependency finding and coordinator decision before edits. Use a separate ignored candidate root `data/generated/teignmouth-float32-topology/`. Do not put new assets in `public/` or change the product loader, normal build inputs, accepted preview or share allowlist. Serve fixed allowlisted candidate files only through an isolated DEV workflow on strict port 4213, preserving 5173.

## Verification, browser evidence and handback

Synthetic regressions cover the exact failing pair (global collision remains rejected), local encoding/round-trip, another pair that still collides locally and must fail, negative coordinates/zero normalization, shared-vertex identity, frame metadata corruption, Float32 winding/slivers, constraint coverage, exact perimeter Y/X/Z, source-plane reconstruction, actual mesh sections rather than ideal field, overlay extrema, ownership/off-ground conflicts, complete footprints, walking/seams and malformed/missing candidate fallback.

Run focused Python tests, Ruff and format, typed frame/schema/sampler tests, and applicable TypeScript/lint/format/Vitest gates. Exact-venv import-only smoke precedes each new executable recipe/environment; reusable unchanged checks must be linked to hashes. A fresh output leaf is created only by its runner; preparatory manifests stay in its parent. Record actual commands/results and interpreter/dependency identities.

After all offline gates pass, capture actual Chromium source/candidate pairs at 1440×960, DPR1, FOV54°. Original pose: XYZ `[-136.407629,7.750687,99.286006]`, bearing344.6°, pitch−24°. Close oblique: XYZ `[-156.818885,6.073672,-77.695888]`, bearing43.526184°, pitch−17.129901°. Freeze a full-window overhead pose before captures; add shoulder/seam/building views. Record matrices/frame, target visibility, screenshot hashes, network/console results, actual geometry/draw/buffer statistics and load/frame observations. Inspect every image. The source baseline must use the same frame/harness/materials/lighting as the candidate. No screenshot or browser pass is claimed until an actual run.

Protect predecessor evidence/code/config/ledgers, public packages, GIS/source files, default viewer, preview, Site and history before/after every run. Hash all directly read inputs and prior issue artifacts; explicitly disclose raw GIS scan scope. Exclude only the current owned evidence leaf and named coordinator metadata. New issue metadata must not overwrite old metadata. Handback includes exact files, commands, gate evidence, reused evidence, defects, budgets and independent review verdict.

## Budget and exact stops

Luna medium coordinates; Luna high implements initial submission and at most four completed, independently reviewed correction cycles. Only after all four are reviewed may Sol 6.1 medium make one correction for a specific actionable finding; a different non-implementing Sol session reviews it. A Sol planner who only plans this issue may independently review Luna work; implementation removes that eligibility. Actual coordinator settings remain unknown unless exposed.

Fresh ceilings: two cause-specific diagnostics, ≤120 seconds each; six implementation builds, at most one per submission and ≤180 seconds each; one independent confirmation build only after a passing candidate, ≤180 seconds. Total full builds ≤7. No parameter/origin sweeps, automatic extra levels or unlimited resources. The fixed geographic domain, field, one frame, attempts and externally enforced wall deadlines bound work; measure actual memory/buffers without adding arbitrary byte admission caps. A simple bounded external process timeout may supervise a single worker; do not reuse the old guardian/permit system or create a new approval framework.

Stop an attempt for any bound-input change, collision, invalid geometry/ownership, failed inherited limit, building/contact failure, source/perimeter discrepancy, timeout, required new frame/domain/recipe or preservation risk. A repeated substantive failure surviving one Luna correction requires bounded Sol diagnosis before another dispatch; do not diagnose repeatedly without new evidence. Stop the issue early if no safe concrete correction exists. After the sole Sol correction fails independent review, mark NEEDS USER DECISION and stop dependent dispatch. No remaining diagnostic or confirmation allowance creates another correction.

At planning completion all counters remain zero/unreserved. Coordinator acceptance and explicit reservations are required before executable dispatch.
