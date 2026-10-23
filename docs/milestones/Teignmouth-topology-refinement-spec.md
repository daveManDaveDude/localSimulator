# Teignmouth local topology and refinement study

Planning specification, 23 October 2026. The user separately authorized this fresh focused continuation after the previous correction budget was exhausted: compare alternative conforming topology, then localized refinement; consider a candidate-local limit change only if evidence supports it. This is not TVW-016. This document does not accept any candidate or change a released policy. Preserve the preceding failed attempts and their counters; coordinator records the new task separately under the Sol planner / Luna implementer / independent Sol reviewer protocol.

## Objective and evidence boundary

Remove the circled transverse Teignmouth Road wedge with one coherent terrain/road display surface. Reuse the registered way `78455395`, part 0, stations 140–155 m, estimated 6 m width and anchor station `148.15104603556912`, X/Z `[-139.6017351396,-95.8223807515]`. Retain the original source longitudinal hump. Width and heights remain visual approximations, not surveyed pavement.

Sources of requirements and implementation evidence:

- `docs/milestones/Road-surface-treatment-teignmouth-spec.md`: target, poses, shared-surface contract, preservation and all numeric gates; this document supersedes only its fixed 0.5 m regular-interior topology assumption for the new study.
- `docs/milestones/Road-surface-treatment-spec.md` and `docs/milestones/Road-surface-treatment.md`: accepted Correction 2 controls, global limits and immutable preview.
- `.codex/torquay-plan-implementation.md`: previous exhausted attempt and independently accepted infeasibility evidence, not candidate acceptance.
- `.codex/evidence/teignmouth-road-surface-fix4/offline-aggregate.json`: residual 0.005621414 m, local slope 6.762173%, added gradient 1.006173611 m/m; other recorded gates pass. SHA-256 `e293437a49d6c5409fa717cd65cc4e498344fe86cf6cf14b5dc0df0da13abde1`.
- `.codex/evidence/teignmouth-road-surface-sol-escalation/solver-phase.json`: 135 positively weighted local inequalities yield a 0.000643617664561382 m contradiction over the permitted bounds. The weights concern local crossfall and signed longitudinal grade, with zero centerline-envelope weight. Certificate SHA-256 `27ae05ea2987c7c464057fac2918a0b2d61048ceae510522b7fe6cbae74cb098`; aggregate SHA-256 `944ab8a6adc92f5f67ac46d60a900ac03c505704eca851ee076fdfbc8db4c066`.
- `pipeline/torquay_pipeline/road_surface_patch.py`, its tests, `src/geo/terrainGrid.ts`, `src/scene/createRoads.ts` and `docs/asset-contract.md`: present interpolation, ownership and asset assumptions.

The certificate proves infeasibility only for that exact mesh, station union and inequalities. It is not evidence that every 0.5 m topology, finer mesh or continuous surface is infeasible. A finer source dataset is neither needed nor authorized: all refinement interpolates the existing pinned source/accepted surfaces.

## Immutable inputs and domain

Pin current release `616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a`, its readiness/inventory/terrain/road/building identities and the accepted preview:

| File | SHA-256 |
| --- | --- |
| `heightfield.f32` | `037a74320557088135e0885386c24fdcdea6171469db1d6329c3e82997f5c1e9` |
| `manifest.json` | `9a3cb6c08fb57a19f94e1215ac526b1baf28634d38be1ffc7d4ed61f2de7c6f7` |
| `qa.json` | `43d7058a339416d308be09292598949d3d97f4b764a147ccc2d5fb771d434f20` |

Use the same 42 × 41 coarse-cell replacement set: first column 409, first row 432; local rectangle X `[-182,-98]`, Z `[-136,-54]` (84 × 82 m). No domain expansion. Keep the existing deformation influence, maximum 32 m shoulder transition measured from the configured ribbon edge, along-road fade and source-derived centerline/width unchanged. Do not replace the full-world grid.

Preserve default `/`, accepted `/?roadSurface=preview`, public Site/`sites/`, synthetic and historical packages, source GIS, existing reports/captures/installers/recovery material, port 5173, TQ1 4HN and AOI `selected_pending_coverage` / `not_checked`. No downloads, dependency or transform changes.

## Staged decision matrix

Run synthetic topology/solver controls before any real trial. Freeze the full existing station/offset union before comparing variants; do not remove conflicting sample locations. Freeze parameters and input hashes in a write-once study inventory. Each trial has one bounded solve; distinguish certified infeasible, unresolved numerical result, failed global QA and fully passing Float32 result.

| Stage / ID | Topology change | Resolution / purpose | Advance rule |
| --- | --- | --- | --- |
| Reference `existing-05` | Retained regular source-half-cell mesh | Existing evidence only; do not rerun it | Control for certificate and topology comparisons |
| `flip-05` | Deterministic alternate diagonal/edge flips inside deformation, same existing vertices; mandatory source-plane edges retained outside deformation | Isolate connectivity from vertex density | Record all unchanged-limit local and global outcomes |
| `road-05` | Road-aligned polygon subdivision using centerline, configured ribbon edges, station-normal sections and influence boundary as explicit constraints; deterministic constrained triangulation | Nominal 0.5 m along/across carriageway; no finer regular lattice | Prefer if complete gates pass; new intersection vertices are reported separately from nominal density |
| `collar-05` | Same road-aligned core, alternative conforming collar with graded 0.5 → 1 → 2 m edge scales within the same domain | Isolate transition connectivity and pinning | Do not change influence or outer boundary to obtain feasibility |
| `local-025` | Best defensible road-aligned topology from the completed topology comparison, refined only in the target ribbon/support zone | 0.25 m nominal local spacing; 0.5 m background | Only if no 0.5 m variant passes, or a documented remaining interpolation defect requires refinement |
| `local-0125` | Same selected topology and refined zone | 0.125 m nominal local spacing | Only after 0.25 m result; last exploration level |

The refined zone is derived generically from the complete target-window ribbon and supporting local-constraint triangles, expanded by one original 2 m cell and clipped to the existing influence. Record its polygon and selection rule; do not refine only the single worst coordinate. Preserve all target-window samples. Keep 0.5 m background and the conforming 2 m outer boundary; fine-to-coarse transitions must have paired edges without hanging vertices.

At most five distinct exploratory real solves, each ≤2,000 iterations and ≤120 s including preparation, with one additional independent reproduction solve only for a fully passing selected winner. No retries of a failed trial, silent parameter tuning or automatic extra levels. Do not run refinement before the three topology alternatives are classified. Stop refinement once a candidate passes complete QA and visible acceptance. A nonconvergent result is not an infeasibility certificate. Exhaustion produces a comparison handback and stops; it does not authorize another search.

## Meshing, baseline and contract changes

Use installed NumPy/Shapely only. Local inspection found Shapely 2.2.0 / GEOS 3.14.1. Polygon-constrained triangulation is available: [official Shapely API](https://shapely.readthedocs.io/en/stable/reference/shapely.constrained_delaunay_triangles.html). It preserves polygon boundaries, not arbitrary internal lines passed as points. Node the planar constraint arrangement, form its polygon faces and triangulate those faces; test that every intended constraint edge survives. Do not substitute unconstrained `triangulate(MultiPoint)` and assume road edges are retained.

Road normals/offset sections can intersect at bends. Resolve their planar intersections deterministically and retain the original sample coordinates/inequalities; do not repair centerline geometry, widen/narrow the published road footprint or discard sections to make meshing easier. Reject invalid/overlapping subdivisions with exact diagnostics.

Inside permitted deformation, replacement triangles may cross original coarse source half-cell boundaries. The existing one-source-half-per-patch-face assumption is a representation restriction, not source provenance. Replace it with an explicit bounded face/source-triangle overlap index. Sample baseline heights with the unchanged original fixed-triangle sampler; compute earthwork extrema on the overlay, including intersection vertices. Reclip source road/path polygons using spatial overlap queries, retaining source IDs, group priority, horizontal area and exact display-face ownership. Unaffected source faces remain unchanged.

Outside deformation, preserve original accepted breaklines as constrained edges and reproduce their planes. Embed the influence boundary so a triangle crossing it does not accidentally pin otherwise permitted interior vertices. All fixed/outside vertices remain exact accepted Float32 values. Keep the existing 2 m outer perimeter bytes, coarse-cell replacement set and normal/seam policy; no T-junctions, cracks, holes, overlaps, downward/degenerate faces or multiple heights at one X/Z.

Generalize `PatchMesh` vertex identity from a hardcoded half-metre integer lattice to stable canonical Float32 X/Z keys plus deterministic triangle ordering. Retain Float64 construction coordinates for provenance/diagnostics, but perform final topology, intersection and ownership checks on actual Float32 geometry. Reject coordinate collisions or changed winding instead of merging them silently. Replace source-half lookup assumptions with a bounded spatial index; no per-walk-query full scan.

Reuse the seven-file local-triangle asset contract and exact guarded candidate path `public/worlds/torquay-road-surface-teignmouth-candidate/`; no candidate has been accepted/published there. Add a distinct supported algorithm identifier and mesher/refinement parameters; never relax the accepted grid-derivative schema. Manifest must identify constraint arrangement, source-overlap index semantics, replacement cells, source/base hashes, topology/solver versions and output descriptors. Derive ordered serialized Y hash from XYZ and compare the external witness; compare exact topology, road buffers and owner IDs against the validated surface. Runtime QA remains a compact summary; full certificates belong only in offline evidence.

## Unchanged acceptance gates

- Whole target window at the frozen ≤1 m station union (source vertices, integer/control/fallback stations and exact anchor retained), full 6 m width at ≤0.25 m offsets: maximum **local** lateral slope ≤5%, endpoint span ≤0.30 m, source centerline deviation ≤0.10 m, signed grade change ≤2 percentage points. Median or endpoint crossfall cannot replace local-slope checks.
- Preserve all 439 accepted severe-station controls, both Parkfield controls and seven full-way centerline/longitudinal profiles. No regression is hidden by a better target average.
- Absolute source-relative earthwork strictly <5 m and positive added gradient strictly <1.0 m/m on every final edge and preserved original 2 m X/Z controls. Overlay extrema must include source/patch intersections. Fixed/outside accepted geometry remains unchanged.
- Recompute all 3,613 complete building footprints: base displacement p95 ≤0.183 m, max ≤2.424 m; Newton legacy ±0.05 m. Review shifts >0.50 m, Newton/Sanford/Cavern sections/footings and nearby building `osm:way:208684847` without obscuring terrain defects.
- Road/path drape ≤1 mm with existing +0.05 m offset, barycentric violation ≤1e-6, existing area/degenerate/Float32 coverage limits unchanged; displayed-terrain walk clearance 1.70 ±0.05 m with road, shoulder and seam coverage. Numerical arithmetic allowance cannot mask missing coverage.
- Exact protected hash preservation, finite Float32 witness, complete deterministic ownership, valid seams and two independently reconstructed/serialized outputs with matching hashes. No publishing or runtime progression on failed or unavailable offline gates.

Retain resource ceilings: one patch, ≤250,000 total replacement terrain-plus-road triangles, ≤150,000 vertices, ≤4 added draw calls; runtime payload ≤8 MiB, manifest ≤256 KiB, QA ≤512 KiB; added resident geometry ≤16 MiB, peak construction CPU/GPU buffers ≤64 MiB. Include replaced/temporary index buffers and report total/net geometry. Count before solving and after road clipping. Reject a level that exceeds a ceiling; do not increase a budget or silently enlarge the core. No new FPS guarantee is inferred from SwiftShader.

## Threshold decision

**No threshold change is currently warranted.** The retained certificate establishes a topology/formulation conflict involving crossfall and signed grade; it does not identify an incorrect threshold or justify removing the source hump. Test representation alternatives first with identical gates and source comparisons.

If every authorized topology/refinement fails, produce a candidate-local sensitivity proposal only: identify the smallest conflicting row set, vary one local parameter at a time, retain all other/global gates, and report the necessary bound together with changes in centimetres, local slope, longitudinal hump and shoulder/building consequences. Include equal-scale section/mesh plots and distinguish an interval estimate from proven feasibility. No value is pre-authorized merely because it makes a solve pass. A proposed revised bound needs independent rationale and coordinator acceptance of a narrowly amended candidate specification before a changed-limit build or runtime comparison. Global accepted policies remain unchanged.

## Files and reproducibility

Expected offline implementation files:

- `pipeline/torquay_pipeline/road_surface_topology.py` and `pipeline/tests/test_road_surface_topology.py`: deterministic strategy/PSLG/refinement generation and topology controls.
- `pipeline/torquay_pipeline/road_surface_patch.py`, `pipeline/tests/test_road_surface_patch.py`: generalized mesh/overlap queries and complete unchanged gates; preserve prior solver/certificate controls.
- `config/road-surface-teignmouth-topology-study.json`: fixed study IDs, constraints, bounds, source identities and bounded run policy; leave the old candidate config/history intact.
- `pipeline/scripts/run_teignmouth_topology_study.py`: explicit single-trial CLI, write-once inventory, witness/certificate/aggregate retention, no automatic publisher.
- `.gitignore`: only exact new generated evidence/candidate exclusions if required; do not hide source/spec/test edits.

Use exactly `.codex/evidence/teignmouth-topology-study/<trial-id>/` for write-once raw trials; allowed files `attempt.json`, `topology.json`, `constraints.json`, `candidate-heights.f32`, `patch-vertices-xz.f64`, `patch-base-heights.f32`, `patch-triangles.u32`, `solver-phase.json`, `offline-aggregate.json`, `certificate-verification.json`. A rejected trial may lack a witness, but must say why. Refuse an existing trial directory before source processing; no resume/overwrite. Guard trial IDs against traversal and aliases, exact path overlaps/reparse points, and every protected input before writes. Store hashes, byte lengths, code/config/solver/environment identities and source snapshots before/after; independently verify certificates against regenerated rows with exact rational or high-precision arithmetic. Reference immutable source files rather than copying datasets.

New durable comparison evidence: `docs/milestones/artifacts/Road-surface-treatment/teignmouth-topology-study/` with `comparison.json`, `comparison.md`, `profiles/`, `topology/`, `screenshots/`, `browser-evidence.json`, `preservation.json` and isolated `regressions/`. Keep old paths/evidence untouched. Handback: `docs/milestones/Teignmouth-topology-refinement.md` records every attempted/unattempted trial, commands, proofs/limits, selected candidate and independent review. Before the study, record hashes of previous evidence plus all protected input trees; no source mutation is authorized.

If a winner clears complete offline gates, implement the already specified `DisplaySurface`, typed local-patch schema/loader and shared terrain/roads/buildings/labels/walk consumers in the existing narrow file list; update `docs/asset-contract.md` for the new algorithm only. Add `tests/e2e/teignmouth-surface.spec.ts` and reuse existing camera instrumentation. Extend only the test-match list in `playwright.road-surface.config.ts` to admit that test; retain its existing isolated DEV server, port 4213, strict-port refusal, 1440 × 960/DPR 1, no retries and no server reuse. Default and accepted-preview behavior remain isolated. Two fresh canonical candidate execution records must represent actual independent generation/validation, not duplicated records from one assembly. Missing/stale/corrupt/oversize/invalid/cancelled candidate loading falls back coherently to validated accepted preview, then source if needed, with truthful notices and disposal.

## Verification commands and browser gate

These are implementation commands, **not commands run during planning**. The study runner/tests named below are to be added, not claimed to exist already. Run from repository root with `PYTHONPATH=pipeline`, `PYTHONDONTWRITEBYTECODE=1`, and pinned runtime/dependencies; record actual versions and limits.

```powershell
pipeline/.venv/Scripts/python.exe -m pytest -p no:cacheprovider pipeline/tests/test_road_surface_topology.py pipeline/tests/test_road_surface_patch.py pipeline/tests/test_road_surface.py pipeline/tests/test_road_alignment.py pipeline/tests/test_roads.py pipeline/tests/test_terrain_export.py pipeline/tests/test_alignment_report.py
pipeline/.venv/Scripts/ruff.exe check pipeline/torquay_pipeline/road_surface_topology.py pipeline/torquay_pipeline/road_surface_patch.py pipeline/tests/test_road_surface_topology.py pipeline/tests/test_road_surface_patch.py pipeline/scripts/run_teignmouth_topology_study.py
pipeline/.venv/Scripts/ruff.exe format --check pipeline/torquay_pipeline/road_surface_topology.py pipeline/torquay_pipeline/road_surface_patch.py pipeline/tests/test_road_surface_topology.py pipeline/tests/test_road_surface_patch.py pipeline/scripts/run_teignmouth_topology_study.py
pipeline/.venv/Scripts/python.exe pipeline/scripts/run_teignmouth_topology_study.py --config config/road-surface-teignmouth-topology-study.json --trial flip-05
```

Run subsequent declared IDs individually only when their stage is eligible; no shell loop that ignores failures. Synthetic tests cover bends/self-intersecting normals, near-collinear constraints, influence holes, original breakline intersections, alternate diagonals, refinement collars, exact plane reproduction, Float32 collision/slivers/negative-coordinate shared ownership, immutable fixed nodes, row scaling/certificates, source overlay maxima, road area/drape, complete footprints, resource rejection, path aliases and write-once safety.

After complete offline PASS and integration:

```powershell
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run format:check
npx.cmd vitest run --exclude "sites/**"
npm.cmd run build
npx.cmd playwright test --config=playwright.road-surface.config.ts tests/e2e/teignmouth-surface.spec.ts --workers=1
git diff --check
```

The dedicated E2E must explicitly start an isolated DEV server on port **4213** (DEV-only route), without reusing or touching 5173. Require actual Chromium captures after Start at 1440 × 960, DPR 1, FOV 54° for source / accepted preview / winner at both exact registered poses from the preceding spec, plus one recorded unobstructed overhead pose. Add matched seam/maximum-gradient, nearby building and Newton/Sanford/Cavern views. Record source-to-pixel target registration, poses, screenshot hashes, runtime/GPU/triangle/draw/buffer counters, frame timings, requests/console/page errors, clipping and actual walk clearances. Require visible removal of the transverse wedge and no new crack, floating edge, wall or concealed defect. Preserve and disclose the longitudinal hump.

Run applicable default/accepted-preview/synthetic/historical/share exclusion, fallback/cancellation/disposal and navigation regressions, isolating their new outputs. Report the unrelated `sites/**` Vitest collection issue and Windows symlink skip honestly. Do not claim any browser or physical-device result without a real run. Independent Sol review must inspect all selected-candidate images, exact final assets, numeric/source comparisons, preservation and resource evidence before acceptance. No public Site publication or default activation follows from this study.
