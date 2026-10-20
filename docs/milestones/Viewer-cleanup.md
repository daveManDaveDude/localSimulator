# v0.1.0 viewer cleanup handback

**State:** Accepted after independent Sol review and coordinator acceptance on 2026-10-20. User authorization covers this descriptive cleanup only, with Sol implementation. TVW-016 and later remain unauthorized.

## Result

The product entry `/` loads the existing current 2 km terrain/buildings/roads release. The existing current bookmark works, and its layer flags cannot disable product layers. Navigation remains available through Start, mouse look, WASD, vertical fly movement, Shift, fly/walk, Reset, Controls and Escape. Normal/boosted speed remains 15/41.25 m/s; walking retains 1.7 m eye clearance.

World/layer selection, visible telemetry, terrain grid/axes/north helpers, wireframes, road context markers, street-name toggles and the unavailable overview are absent from the product UI. The grid starts hidden and `G` has no effect. Roads and validated OSM name annotations are on by default in the current 2 km scene. Existing read-only telemetry and loader/controller internals remain in an inaccessible diagnostics subtree, preserving observation without a visible debug mode. No new debug query parameter was added.

The current scene displays **2 km candidate · AOI pending; feature coverage not checked.** EA/OSM attribution and licence links remain visible during navigation. Sources provides publisher links, vintage, Newlyn reference and estimated building-height/road-width limitations. A missing or invalid current package automatically loads clearly labelled fictional synthetic terrain without rewriting the Torquay bookmark; Retry Torquay attempts the real package again. Detailed validation causes remain available as invisible observations. Individual building/road errors retain usable terrain and provide focused retry buttons.

Internal `/?world=synthetic`, `/?world=m0` and historical `/?world=torquay-poc-001&buildings=1&roads=1` routes remain for reproduction, with no product chooser. The historical 1 km package, current immutable release, sources and pending AOI were not regenerated or adjusted. Package version remains 0.1.0.

## Browser evidence

Fresh evidence is confined to `screenshots/Viewer-cleanup/` and `artifacts/Viewer-cleanup/`; earlier accepted evidence is preserved.

- [Default map](screenshots/Viewer-cleanup/default-map.png)
- [Active map](screenshots/Viewer-cleanup/active-overview.png)
- [Sources disclosure](screenshots/Viewer-cleanup/sources.png)
- [Outer-annulus walk view](screenshots/Viewer-cleanup/outer-annulus.png)
- [Layer retry](screenshots/Viewer-cleanup/road-recovery.png)
- [Share fallback](screenshots/Viewer-cleanup/share-default-fallback.png)

Chromium **156.0.8078.4** ran the isolated production profiles at **1440 × 960 CSS pixels**, DPR **1.5**, with the real scene's existing DPR-1 buffer cap. The real case resized to **1280 × 800** and confirmed the new backing-buffer width. Renderer: **ANGLE / Vulkan / SwiftShader**, so this is software-rendered browser evidence, not hardware performance validation.

The full real profile passed **5 tests with 1 expected share-only skip** in 4.6 minutes. A focused repeat after the Sources size/contrast adjustment passed the complete default/navigation/Sources case **1/1 in 3.3 minutes**; it confirmed the final EA link is in the viewport. The share profile passed **3 tests with 3 expected real-only skips** in 19.8 seconds. Default real loading used release `616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a`, with 3,613 building footprints and 1,044 road ways. No unexpected page, console or HTTP errors occurred in that default case. The share default recorded no unexpected page/console/HTTP errors; missing/invalid readiness and deliberately injected 503 layer responses are expected recovery cases.

The actual mouse/pointer-lock/WASD/vertical/boost/fly-walk/reset/help/resize checks passed. The camera travelled from spawn `x=0, z=400` to `x=0, z=595.9375`, beyond the old 1 km bounds, with walk clearance checked against 1.7 m. This low view shows terrain and neighbouring building rows; it is not an alignment comparison. The fresh default/active/Sources/outer-area/fallback/retry images were opened and visually inspected. Sources now shows the final finer-resolution paragraph and both final EA links fully within the desktop viewport, with bounded internal scrolling available for smaller views. See [real browser observations](artifacts/Viewer-cleanup/real-browser.json) and [share browser observations](artifacts/Viewer-cleanup/share-browser.json).

## Commands and results

- `npm.cmd run typecheck` — passed.
- `npm.cmd run lint` — passed.
- `npm.cmd test` — 299 passed across 23 files.
- `npm.cmd run build` — passed; existing native-config extension and MapLibre large-chunk advisories remain.
- `npm.cmd run format:check` — passed.
- `npm.cmd run test:e2e:cleanup:real` — 5 passed, 1 expected profile skip.
- `npm.cmd run build`, then `npx.cmd playwright test --config=playwright.viewer-cleanup-real.config.ts --grep "default real map"` — 1 passed after final Sources/layout and walk-shot changes.
- After adding a dark backdrop to layer-error feedback, `npm.cmd run build`, then `npx.cmd playwright test --config=playwright.viewer-cleanup-real.config.ts --grep "current bookmark"` — 1 passed in 49.6 seconds, including independent building/road retry; the refreshed retry screenshot was inspected.
- `npm.cmd run test:e2e:cleanup:share` — 3 passed, 3 expected profile skips; includes the share production build.
- Share output inspection found only `synthetic-heightfield` and `synthetic-terrain-demo` under `dist/worlds`; neither real package nor recovery/intermediate assets was present.
- Normal production output was rebuilt after share checks, leaving `npm run preview` ready for the local real package.
- Protected-file before/after comparison — 149 files, zero changes.
- `git diff --check` — passed.

The first real-browser run passed four cases with one profile skip and failed a test-authored fixed 700 ms strafe threshold. A second run passed the other four cases with one profile skip and exposed a test baseline mistake: strafe displacement was measured from spawn after mouse look and forward movement had already changed X. The corrected test observes movement with bounded polling against the immediate pre-movement camera position. Neither failure indicated a loader/rendering error; the corrected runs passed as recorded above.

## Test profile transition

The current suite is `tests/e2e/viewer-cleanup.spec.ts`, with separate production real/share configs. `npm run test:e2e` builds the share distribution and runs clean-clone smoke; `test:e2e:cleanup:real` and `test:e2e:cleanup:share` select explicit profiles. Previous TVW-014/015/overview/2km config filenames are compatibility aliases to the current profile, rather than tests of removed product controls. Earlier E2E source files remain historical acceptance records and are no longer scheduled by those configs. They must not be interpreted as newly passing tests of the removed interface. Vitest loader/schema/mesh/controller coverage remains in place.

No Python/pipeline test or GIS regeneration is required for these presentation changes; no Python pipeline/config source was edited. No existing port-5173 service was stopped or replaced. Isolated production previews use ports 4210 and 4211.

Changed files are `src/app/createApp.ts`, `src/style.css`, `package.json`, the Playwright profile configs, `tests/e2e/viewer-cleanup.spec.ts`, README, AGENTS, the project-plan amendment, this specification/handback and the new cleanup evidence directories. No dependency or package-lock change was needed.

## Source resolution and road-position limits

The current browser samples EA Composite DTM **1 m source cells into a 2 m mesh**. Local source metadata is a 2022 composite with tile-wide 2003–2022 survey dates, not a 2026 survey. Finer sampling could retain more source detail but would not itself correct horizontal OSM geometry. The official [EA composite catalogue](https://www.data.gov.uk/dataset/01b3ee39-da3f-47b6-83da-dc98e73a461f/lidar-composite-dtm-2022-1m) describes this composite, and the [time-stamped catalogue](https://www.data.gov.uk/dataset/8275e71e-1516-42a1-bb0c-4fa73807fe2b/lidar-dtm-time-stamped-tiles) describes nominal 0.25/0.5/1/2 m products nationally.

The saved local index measured 0.5 m metadata footprints over **397,628.696 m² / 9.9407%** of the AOI, dated 2010-04-04, using OSTN'02/OSGM'02. No finer raster was checked or adopted. These are metadata footprints, not proven finer-raster coverage or point-cloud spacing.

The local [Geofabrik Devon](https://download.geofabrik.de/europe/united-kingdom/england/devon.html) OSM extract is dated 2026-10-16. Roads are centrelines buffered with estimated widths and draped 0.05 m above terrain. Current release QA records 283 road/building intersection pairs and 1,701.249047 m² overlap; these are measured source conflicts, not proof that roads alone are misplaced. Three historical junction contexts passed qualitative comparison, with no numeric offset measurement and no expanded-area completeness claim.

QA records a coordinate operation with 2 m reported accuracy, `best_available=false`, and the preferred OSTN15 grid unavailable. [OS transformation guidance](https://www.ordnancesurvey.co.uk/geodesy-positioning/coordinate-transformations/resources) describes the metre-scale limits of simple transformations and the OSTN15 alternative. A transform limitation is a possible contributor to terrain-relative placement, not a measured diagnosis; buildings and roads share that operation. Source geometry, widths, footprints and terrain sampling remain other hypotheses. No alignment repair, new source acquisition, transformation or resolution change was performed.

## Preservation and remaining scope

A protected-file snapshot and post-run comparison cover source/config/package/fixture files, prior screenshots/evidence, installer, recovery tree, immutable source plan and private checkpoint: **149 files, zero changes**, recorded in [the preservation report](artifacts/Viewer-cleanup/preservation.json). The source plan remains SHA-256 `144c9c704ea1c10fa2d503dba3233b089528585be7d36b7b94164d28ba40d571`; installer `b4edf70fa040968958c662ffb09feeeb0eeca07759e6ed7742606bcc39f29fc6`; current readiness `08399e71ba3a0c6d421982b5cd47973114a48060ddb4c0931378663faf07b3b4`. The checkpoint's pre-existing modification remains coordinator-owned and uncommitted by this issue.

Remaining feature coverage and AOI approval remain outstanding; this does not authorize subsequent implementation.

## Default road-name amendment and marker correction

The user clarified that roads and road names should be on by default. The coordinator amended the specification in `b6f1d28`; this correction enables the existing TVW-015 overlay automatically for the current 2 km product, without exposing a toggle. It uses only validated `sourceTags.name`, with the existing 20-label pool, 500 m camera-distance bound, viewport projection, duplicate/collision filtering and terrain-relative anchors. Product controls now participate in panel filtering; the pointer-locked hidden Start card no longer masks labels as a visible obstacle. The overlay retains `pointer-events: none`. Labels remain display annotations, not occlusion-aware surfaces or completeness evidence.

Preliminary independent inspection also found that the initial cleanup still created the automatic road QA context marker after roads loaded. Hiding its selector did not suppress that scene object. The current-product load no longer calls that marker path, and the marker helper rejects current-profile requests. A read-only observation counts actual attached QA marker groups; the current-map E2E requires zero after road loading. Historical internal reproduction remains supported.

Correction verification passed:

- `npm.cmd run typecheck`, `npm.cmd run lint`, `npm.cmd run format:check`, `npm.cmd test` (299 tests), normal production build and `git diff --check` passed.
- `npm.cmd run test:e2e:cleanup:real` — **5 passed, 1 expected share-only skip**, 5.3 minutes. The default case observed **11 visible names** matching the immutable release's actual `sourceTags.name` and clipped-part identities, drawn from 481 named source parts. Distances were 288.5853–483.3745 m in that viewport, within the unchanged 500 m bound and 20-label cap. Duplicate/collision/product-panel filtering, pointer transparency, actual navigation and **zero attached QA marker groups** passed. The default real case had zero unexpected page, console or HTTP errors.
- `npm.cmd run test:e2e:cleanup:share` — **3 passed, 3 expected real-only skips**, 20.4 seconds. Synthetic fallback had **0 visible road-name labels**, with no unexpected page/console/HTTP errors and no downstream real GIS requests after readiness. Share output contained only the two synthetic fixtures. Normal production output was rebuilt afterwards.

The fresh [labelled scene without a QA marker](screenshots/Viewer-cleanup/labels-active-no-marker.png) was captured after Start and opened for inspection. It visibly shows source names including Lymington Road, Chatto Road, Haslam Road and Wright's Lane, with no red QA marker or label toggle. The refreshed Sources, active/outer-area and share fallback images remain under this issue's evidence folder; the labelled active and share fallback captures were inspected. Chromium was 156.0.8078.4, at 1440 × 960 CSS pixels and DPR 1.5 before the existing resize check; the recorded renderer remains ANGLE/Vulkan **SwiftShader software rendering**, not hardware performance validation.

The saved initial [149-file preservation snapshot](artifacts/Viewer-cleanup/preservation.json) remains historical and unchanged. A separate [correction comparison](artifacts/Viewer-cleanup/correction-preservation.json) confirms **148 protected files unchanged**, excluding only the coordinator-private checkpoint from the historical comparison because the coordinator changed it between phases. The source/package/config/fixture, installer, recovery-tree and older evidence identities still match. The implementation correction did not edit that checkpoint or the original snapshot. No GIS input, geometry, transform, AOI, resolution, dependency or version change was made.

## Independent review and coordinator acceptance

Final independent Sol review of `c504cb4`, `b6f1d28` and `32c4cf3` returned **PASS** on 2026-10-20, with no remaining actionable findings. The reviewer independently ran typecheck, lint, formatting, `git diff --check` and all 299 Vitest tests; these passed. An isolated Chromium probe on port 4212 verified the current real map, Start/pointer lock, H/G/Escape, 11 default source-derived labels matched to immutable release names and clipped-part identities within 500 m, and zero attached QA markers. Invalid readiness preserved the full bookmark, fell back to clearly labelled synthetic terrain, displayed zero real road names, and caused no page errors. The reviewer inspected the fresh labelled, Sources and outer-area captures and independently confirmed 148 protected files match. The full real/share E2E profile results are recorded above and were reviewed from implementation evidence rather than rerun during independent review. The preview on port 4212 was stopped; the user's port 5173 remained running and untouched.

Coordinator acceptance is limited to v0.1.0 presentation cleanup. The AOI remains `selected_pending_coverage` / `not_checked`, feature completeness remains unverified, and TVW-016 or later work is not authorized.
