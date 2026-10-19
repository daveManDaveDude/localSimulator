# TVW-012: Independent three-spot alignment comparison specification

**Status:** Accepted by coordinator on 2026-10-19 for TVW-012 implementation. Sol 6.1 medium specification only. No comparison-source download, geographic modification, application change, comparison result, test execution or new browser evidence is claimed by this document.

## 1. Authority and original requirements

The user's separate “lets continue” authorizes **TVW-012 only**, following TVW-011 PASS. Produce a reproducible, independently sourced three-spot map comparison and an issue report. Do not repair source geometry, retune transforms, re-export terrain/buildings/roads, move the AOI, introduce walk mode, or start TVW-013+.

Authoritative references in `docs/Torquay_JS_Virtual_World_PoC_Codex_Plan.md`: §3.3 road alignment/estimated widths (133–140), §3.4 provenance/licensing (142–154), §§4–6 common AOI/coordinates/contracts, §10 M5 acceptance/exit (547–566), §11 visual acceptance matrix (642 onward), §13 quality gates (677–703), §14 handback (707–738), §15 TVW-012 and dependencies (760/764), ADR-002/003/004, and §17 road alignment verification at three local points (790). Read alongside canonical `docs/project-plan.md` §10 M5 (553–576), §§11/13/14, §15 TVW-012/dependencies (770/774), and the accepted TVW-011 spec/handback. Canonical status explicitly leaves the combined M5 exit pending this issue.

The 1,000 m size is the recorded user override to the source plan's original 500 m. Preserve the immutable source-plan SHA-256 `144C9C704EA1C10FA2D503DBA3233B089528585BE7D36B7B94164D28BA40D571`.

## 2. Inspected baseline and current gaps

- Starting HEAD: `07713e3`; working tree contains only the user-owned untracked installer. Preserve that file, existing screenshots, source manifests/raw files and the running port 5173 server.
- Read the complete source/canonical plans, AGENTS, checkpoint, TVW-011 accepted spec/handback, source manifest and actual road QA. TVW-011 was independently accepted after `9fcf638`, `ed29006`, `3ae4e3a`; its renderer and optional-layer error handling are outside this issue's implementation scope.
- Current mapped output is 198 ways, 198 clipped line parts, 1,000 building footprints, and a 501 × 501 terrain grid at 2 m. These are counts, not completeness findings. The road QA records 39 road/building intersection pairs and 97.465114 m² overlap without repairing them; use these as existing issues to assess locally, not proof that all are errors.
- No independent OpenMap/OpenRoad/comparison files exist under local `data/`. Existing OSM object captures and TVW-011 placement observations compare the **same underlying OSM source family**. They do not fulfill the independent-map gate.
- Missing: verified independent comparison source, registered map panels, three actual match observations, explicit uncertainty/availability outcomes, and a linked issue report. No browser comparison page, pipeline comparison CLI or report schema currently exists.
- Retain centre `[-3.536013,50.477853]`, BNG centre `[291108.9018176432,65353.48350844931]`, and exact west/south/east/north bounds `[290608.9018176432,64853.48350844931,291608.9018176432,65853.48350844931]`. Keep `selected_pending_coverage` / `not_checked`; neither three spot checks nor M5 acceptance establishes complete M2 coverage or AOI approval.

## 3. Independent map choice and access

### Preferred source: OS OpenMap–Local GeoTIFF

Use an actual published **Ordnance Survey OpenMap–Local raster** as the reference map, independently of the local Geofabrik/OSM data. OS documents it as a generalised street-level product at nominal 1:10,000, with raster and vector forms. Its overview identifies OS MasterMap-derived generalised building geometry. This supports a different publisher/product reference, not a claim that every feature has an entirely unrelated historical lineage or survey-grade accuracy.

This choice provides readable roads/buildings/labels, georeferenced alignment and an offline repeatable map without introducing an interactive mapping SDK or public-service dependency. A map rendered locally from a verified OS raster is still an independent **source** map: rendering locally does not make the source OSM. Conversely, different styling, another OSM tile server, current OSM.org, Geofabrik versus OSM.org, or a different snapshot date does not supply an independent geometry source.

Official pages checked during planning:

- [OS OpenMap–Local product](https://www.ordnancesurvey.co.uk/products/os-open-map-local): available formats and product scale.
- [Product documentation](https://docs.os.uk/os-downloads/products/maps-and-imagery-portfolio/os-openmap-local) and [overview](https://docs.os.uk/os-downloads/products/maps-and-imagery-portfolio/os-openmap-local/os-openmap-local-overview): source character, update cycle, generalisation and viewing limitations.
- [Downloads documentation](https://docs.os.uk/os-downloads/products/maps-and-imagery-portfolio/os-openmap-local/os-openmap-local-downloads): GeoTIFF georeferencing and map legend. The linked demonstration covers Exeter/Newport/Inverness; it does not establish Torquay coverage.
- [OS OpenData licensing/access guidance](https://www.ordnancesurvey.co.uk/products/product-support): OGL and required OS credit.
- [OS Data Hub product portal](https://osdatahub.os.uk/downloads/open/OpenMapLocal): actual portal must be inspected in a JavaScript browser during implementation. The text browser returns only a JavaScript requirement; no specific Torquay file, release, URL, size or access entitlement was verified here.
- [OS Downloads API documentation](https://docs.os.uk/os-apis/accessing-os-apis/os-downloads-api): currently says API-project access requires an API key. Do not assume an older unauthenticated endpoint still works, create an account/key, or silently add an authenticated service. Prefer the public product portal/download route if available.

OS advertises free product download, but that does not prove the current portal can be completed unattended without an account. Implementation must check the live public workflow before declaring an access blocker. Record the observed page, selected product/format/edition, coverage selection, authentication requirement and any exact error. Do not infer October 2026 availability merely from a nominal April/October update cycle.

### Bounded acquisition during implementation

Planning downloads nothing. Once this candidate is accepted, acquiring the minimum OS raster package covering the three comparison windows is within TVW-012's evidence scope. Keep it comparison-only, separate from production OSM/EA sources and never publish it as a new viewer world. Select files from publisher metadata/index/coverage; derive required tiles from actual bounds. Do not guess filenames or reuse EA tile names as OS filenames. Where the portal only offers a larger archive, report advertised size first and use the smallest offered regional selection; avoid a national download. If the smallest choice is unexpectedly large, return its measured size/options to the coordinator before acquisition.

Store downloads/extracts under ignored `data/raw/comparison/os_openmap_local/`; register provenance in a new **comparison-only** namespace/file rather than altering the accepted EA/OSM namespaces. Record exact landing/download URL, acquisition UTC/date, product/release/edition, publisher versus survey date distinction, source/archive/member filenames, sizes, SHA-256, available publisher checksums, CRS/affine/bands/extent/pixel resolution, licence link and required year-specific attribution. Verify archive CRCs and bind extracted bytes to their named archive members. Do not treat a world file guessed from a filename as georeferencing. Compare source CRS/affine metadata to the selected area and reject missing/contradictory registration.

Use the actual data's required credit, typically `Contains OS data © Crown copyright and database right [year]`, with the actual metadata year and OGL link. Keep OSM/Geofabrik/EA credits on their own overlays. Raw data stays ignored; limited derived, attributed comparison images and metadata/report may be tracked under the applicable terms. A screenshot's existence does not establish redistribution permission for an unrelated proprietary basemap.

### Alternatives and explicit unavailability

OS Open Roads is a possible separate comparison-only fallback if its verified public download is obtainable, but [OS describes its approximate carriageway alignment and generalised 1:25,000 scale](https://docs.os.uk/os-downloads/products/transport-network-portfolio/os-open-roads/os-open-roads-overview). It alone cannot support detailed building-footprint comparisons or a precise footpath check. Accept this substitute only after the coordinator records how three identifiable road/landmark relationships remain testable; document its limitations and actual source provenance. Do not silently substitute it for OpenMap–Local.

Do not assume an OS-branded consumer map's default layer is independent: inspect the selected layer attribution and provenance. A licensed OS raster layer can qualify if documented and accessible; a mixed/OSM/unknown basemap cannot. No paid plan, API key, premium login or map provider change is automatic authorization.

If the public portal is account-gated or unavailable, write an explicit `unavailable` report containing the exact product/region/format required, portal URL, observed access barrier/date and useful screenshot, and the precise user action needed: obtain the appropriate OpenMap–Local GeoTIFF archive and its metadata/legend and place them in the ignored comparison folder. Request no password or secret. Complete source-independent scaffolding/tests and preserve the working viewer, but **do not call the comparison, TVW-012 verification gate or combined M5 exit PASS**. This is an external blocker, not a failed geometry finding and not grounds to invent a reference map.

## 4. Three registered contexts and selection discipline

Start from the existing three manually chosen contexts below. Values are copied from the actual TVW-011 QA; no new road/junction position is implied.

| Context                                            | Existing OSM building | Representative lon/lat                     | Local XZ (m)                                | Existing road observation                                                                                  |
| -------------------------------------------------- | --------------------- | ------------------------------------------ | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| NE Second Avenue                                   | way/208552436         | `[-3.5332476398607215,50.480951244856804]` | `[203.32051374798175,-340.4368796944909]`   | named way/30982869; nearest point `[190.02965312784104,-340.1357720410472]`; 13.294 m from building point  |
| NW Baron Road / Lindfield Close                    | way/193285347         | `[-3.54291445782617,50.48047580317829]`    | `[-483.60802391561447,-301.78087954761577]` | named targets absent from export; nearest eligible way/193285418 is an unnamed footway, 47.415 m away      |
| SW Mount Stuart / St Vincent's Road / Chapel Court | way/181620525         | `[-3.5417691183482414,50.475127986993755]` | `[-414.6965762343025,294.5276208946598]`    | named way/30482106; nearest point `[-432.51349951958537,332.64398540041356]`; 42.075 m from building point |

Building representative points are navigation/registration context, not matched road control points or survey monuments. Their distance to a road is not road misalignment. Nearby candidates must be manually identified on **both** maps using actual geometry/topology and surrounding buildings, not accepted just because they are nearest or share a label.

The NW context is only about 16 m inside the western AOI edge. A named road outside the export boundary is a clipping/context limitation, not automatically missing coverage. Show the AOI edge prominently; distinguish independently visible outside-AOI context from exported geometry. Do not label the unnamed footway “Baron Road” or “Lindfield Close.” If the independent map does not represent that path or an identifiable in-AOI relationship, classify this context `unavailable`/`ambiguous`. Propose a replacement **actual** in-AOI junction/landmark with source IDs/coordinates and selection rationale; coordinator must accept the change and retain the failed initial context in the report. The AOI must not move and a third successful check cannot be manufactured by recycling one road segment.

For each accepted spot record: stable ID, selection rationale, original context IDs, actual exported OSM way/node/building IDs, independent map product and tile/pixel-window or vector IDs, BNG bounds, local XZ bounds, matched feature role (bend/junction/building-to-street relationship), exact data-derived coordinates where available, any manual click/pixel reference, and match confidence. Use three spatially distinct contexts. Record both supported matches and missing/ambiguous features.

## 5. Registration, uncertainty and comparison method

1. Use existing tested Python coordinate modules only. Convert local data back with `E=originE+x`, `N=originN-z`; retain the pinned explicit-XY transform/no-network/no-grid behavior for WGS84 context. Never fit a translation/rotation/scale to make maps align. Reference raster CRS must be verified; if EPSG:27700, compare directly in BNG with no unnecessary WGS84 round-trip.
2. Generate same-bounds, same-scale north-up panels: independent map alone; independent map plus thin exported centreline/building outlines; exported scene/map alone. Use the existing `roads.json` and `buildings.json`, not a new OSM fetch or a regenerated line that differs from the rendered package. Display AOI boundary, north arrow, metre axes/scale, spot IDs, legend and all required credits. Estimated ribbon width/roof height are not measurement references; prefer road centreline and footprint outlines.
3. Inspect and retain raster affine/pixel-edge semantics; use source pixel corners/centres consistently. Respect rotated affines or explicitly reject unsupported ones. Crop windows deterministically without warping source geometry or borrowing another map's coordinates. Avoid visual stretching to match a screenshot. A perspective browser view cannot supply a quantitative map measurement; pair it with georeferenced overhead panels.
4. Inspect at least one actual 3D browser view per spot with the accepted terrain/building/road package and the existing debug marker/camera controls. Record pose, viewport/DPR/browser, source package hashes and which real scene feature is visible. Existing markers can anchor context but need not equal the selected road control point. No new application feature is necessary merely to make the report.
5. At each spot compare the same bend/junction arrangement, street side/order of buildings, relative road/building positions and clipping. Record signed offsets only for genuinely comparable positions or manually digitised independent reference points; include their pixel/world coordinates and method. Do not compute a “road error” from a building centroid or from arbitrary nearest unrelated features.
6. Record uncertainty components separately: the selected OSM-to-BNG operation's **reported 2 m** accuracy and unavailable preferred OSTN15 grid; source map generalisation/edition; raster pixel resolution; symbol/line thickness; manual selection uncertainty; different source vintages; OSM mapping uncertainty. Do not present these as measured standard deviations or combine them into a statistical confidence interval without supporting metadata. Round observations according to their weakest source; millimetre arithmetic precision is not positional truth.

The source plan has no numeric alignment tolerance. Use a predeclared **10 m discrepancy screening threshold** for sustained like-for-like road offset, after considering map scale/line thickness; it is an investigation trigger, not an OS accuracy guarantee or permission to overlook smaller systematic problems. Explain scale-dependent ambiguity. If uncertainty makes a 10 m discrepancy unresolvable, mark the spot inconclusive rather than increasing the threshold post hoc. Clear wrong-side relationships, mirrored axes, wrong junction topology or wrong feature identity fail regardless of a small nearest-distance number. A short cartographic generalisation or label displacement may be a documented nonblocking difference when the underlying relationship remains identifiable.

## 6. Results, issues and gate decisions

Use separate statuses for **evidence availability**, **spot alignment**, **issue completion** and **combined M5**. A machine-readable report must never derive alignment PASS merely from three image files existing.

| Result              | Required meaning                                                                                                                                                                                               |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Spot `pass`         | Independent source/provenance verified; same feature confidently identified; registered evidence and actual scene inspection agree on road/building horizontal relationships; no unexplained material mismatch |
| Spot `fail`         | Evidence identifies a material coordinate/axis/registration/feature-placement or renderer discrepancy; record IDs, observed extent, reproducible evidence and severity                                         |
| Spot `inconclusive` | Source exists but generalisation, vintage, ambiguous identity, boundary context or measurement uncertainty prevents a supported conclusion                                                                     |
| Spot `unavailable`  | Required source, access, coverage or browser evidence cannot be obtained; record the exact barrier and action needed                                                                                           |

Issue report classifications: implementation/coordinate defect; source-geometry conflict; expected visual policy (estimated widths/heights, skipped bridge/tunnel); AOI clipping; generalisation/scale; vintage difference; missing feature/source coverage; ambiguous correspondence; unavailable verification. Assign severity/action/owner and cite evidence. Distinguish confirmed cause from hypothesis. Preserve existing road/building conflicts and inspect whether any selected spot exhibits them; do not generalise three observations to all 39 pairs or all source coverage.

**TVW-012 comparison/report may be accepted as complete** when three valid independent comparisons and the truthful issue report exist, even if a spot finds a real mismatch; in that case the alignment/combined M5 gate is explicitly FAIL/pending and a separately scoped remediation decision is needed. A data-analysis report is not defective merely for discovering a problem. **Unavailable/inconclusive mandatory comparisons do not constitute an execution PASS**; checkpoint the blocker or required selection decision. The independent reviewer must state both the issue artifact verdict and the alignment gate verdict, with no ambiguous overall PASS that conceals missing evidence.

**Combined M5 PASS is possible only if** all three distinct accepted spots have independent, supported alignment PASS; the prior TVW-010/011 functional gates remain valid; no unresolved material road/building alignment defect remains in these checks; screenshots and limitations are reviewed; and the coordinator explicitly records the combined checklist. Cosmetic/expected policy differences may remain documented. M5 PASS does not approve/freeze the AOI, prove coverage/completeness, complete M2, verify heights or authorize TVW-013. If a material mismatch is found, do not fix it inside this issue; propose a focused authorized follow-up.

## 7. Concrete files and implementation sequence

1. Inspect live public OS product workflow and source metadata; obtain minimal comparison-only source if publicly available. Add `data/comparison-source-manifest.json` (or an explicit new comparison namespace) and `docs/data-sources.md` notes without changing accepted production records. Raw files remain ignored.
2. Add `config/alignment.torquay.json` with the three source-backed contexts, registered windows, source descriptors, screening rule and explicit result/evidence fields. Unknown outcomes initially remain null/unavailable; no seeded “pass.” Do not modify AOI config, transforms or actual production packages.
3. Add small Python modules `comparison_sources.py` (source verification/metadata), `alignment_report.py` (strict schema, registration/result validation and deterministic rendering/report), plus corresponding tests. Reuse Rasterio/NumPy/Matplotlib/pyproj/Shapely already installed; no new dependency or web-map service is necessary. Factor only small tested helpers where needed. CLI: `inspect-comparison-source`, `compare-alignment`, `validate-alignment-report` with explicit source/config/output paths.
4. Generate `docs/milestones/artifacts/TVW-012-alignment.json`, `docs/milestones/TVW-012.md`, and new `TVW-012-{ne,nw,sw}-{reference,overlay,scene}.png` files under screenshots. Source panels may be combined into one labelled composite per spot if all components remain readable. Report records which observations were manually inspected, when and by whom/which run; generated metrics cannot impersonate a human visual assessment.
5. Optionally create a small standalone **local report HTML** under ignored analysis output to inspect registered panels; this is not a new viewer mode or hosted map. Open the actual files/browser and capture proof. No frontend code change is expected. Update README links, canonical/checkpoint/AGENTS issue/gate statuses only after review, retaining pending AOI state and TVW-013 prohibition.

## 8. Validation and evidence requirements

Strict tests must cover malformed/null/bool/nonfinite config/report values, missing sources, bad hashes/CRC/member binding, wrong/missing CRS/affine, coverage gaps, rotated affine handling, pixel centre/edge registration, BNG/local inverse signs in all quadrants, wrong AOI/package hash, same-OSM/unknown-source rejection as independent, source/tile/spot mismatches, duplicate spot/control IDs, fabricated metrics without reference points, wrong or missing attribution, missing evidence files, and inability to mark unavailable/inconclusive evidence as PASS. Use tiny visibly fictional map rasters offline; never claim their comparison proves Torquay alignment.

Test deterministic rendering/JSON/Markdown with fixed source/input/observation records; changing a manually recorded conclusion requires an explicit report input change. Preserve provenance/extract timestamps rather than inserting wall-clock dates into deterministic outputs. Failure leaves the previous report intact. Validate actual file sizes/hashes and safe local evidence paths. A report validator can enforce consistency/evidence linkage but cannot prove a visual match; independent inspection remains mandatory.

Proposed implementation commands, not claims of execution:

```powershell
cd C:\vibe\localSimulator\pipeline
.\.venv\Scripts\python.exe -m torquay_pipeline.cli inspect-comparison-source --config ../config/alignment.torquay.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli compare-alignment --config ../config/alignment.torquay.json
.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-alignment-report --report ../docs/milestones/artifacts/TVW-012-alignment.json
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\python.exe -m pip check
cd C:\vibe\localSimulator
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run format:check
npm.cmd test
npm.cmd run build
npm.cmd run build:share
npm.cmd run test:e2e -- --output test-results/tvw012-implementation
git diff --check
```

Run independent report generation twice into isolated ignored directories and compare bytes/hashes. Inspect new evidence images directly and open the actual local browser scene at each documented spot. Use an isolated server/output for tests if necessary; do not stop the user's 5173 server or overwrite historical screenshots. Full Node gates/E2E guard the unchanged viewer; distinguish executed gates from retained prior evidence. Verify share output still contains synthetic assets and no local real/comparison source. Comparison data must never be served automatically by the synthetic route.

Handback includes source access/provenance and licence, raw/generated/package hashes, all three comparison identities and windows, actual map/scene evidence, uncertainty, observed issues with locations/severity, commands/results, unavailable/inconclusive details, explicit TVW-012 and combined M5 verdicts, unchanged AOI/source plan/installer/baseline evidence, and the next proposed task requiring separate authorization.

## 9. Ready state and coordinator decisions

Coordinator acceptance decisions (2026-10-19):

- Accept a minimal **publicly obtainable**, comparison-only OS OpenMap–Local source. This does not authorize an API key, account-gated access, paid plan, unrelated provider, or national-scale download. If only an unexpectedly large option exists, report its actual size/options before acquisition.
- Size decision (2026-10-19): implementation inspection reports the public portal's April 2026 custom SX GeoTIFF selection at 349.41 MB, the smallest relevant offered option. Coordinator accepts this bounded archive, conditional on verifying the response/size and using only the necessary 5 km member(s) where available.
- Accept 10 m only as a predeclared discrepancy investigation trigger after source scale, symbol width and uncertainty are considered. It is not a survey tolerance, OS accuracy guarantee or reason to discount clear topology/identity errors.
- Accept separate issue-report and alignment/combined-M5 verdicts. A truthful completed report may reveal a mismatch; such a result does not pass alignment or M5. Missing mandatory comparison evidence cannot produce execution PASS.
- Keep the NW context provisional. If it cannot be matched, preserve that result and submit a source-backed, in-AOI replacement candidate for coordinator acceptance before treating it as one of the three spots.

The preferred source is clear, but actual Torquay files/edition/download access remain unverified until implementation inspects the portal. No comparison result exists. Account-gated access requires the precise manual-file intervention described above, not fabricated success or a silent switch to an OSM basemap. TVW-013+ remains unauthorized throughout.
