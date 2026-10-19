# M8 offline geographic overview handback

**Status:** PASS; coordinator-accepted on 2026-10-19 after final independent Sol review of Luna fix 2 (`9f34784`), following implementation `00aeb53` and fix 1 `81bc911`.

## Delivered

The real-terrain route can open an optional, fixed north-up MapLibre overview from a separate local RFC 7946 package. Python creates, validates, and publishes the package from the existing verified AOI, EA terrain, OSM road, and OSM building packages. The browser validates package limits, hashes, provenance, and the loaded terrain/optional-layer identities before display. MapLibre JS, CSS, and workers are bundled locally and loaded only after opening the real-world overview.

The overview contains one AOI polygon, 196 road centerlines, and 1,000 building footprints (1,197 features and 7,789 positions total). Two validated road ways have no clipped AOI centerline and are omitted from this view; buffered road surfaces are not represented. This is a fixed 2D overview: it has no live camera marker, terrain raster, external basemap, or new alignment/completeness result. Synthetic M0 scenes remain unreferenced and show a compact unavailable explanation without creating a map or requesting real-world assets.

The selected 1,000 m candidate remains `selected_pending_coverage` / `not_checked`. Mapped feature counts and the overview do not establish completeness or approve/freeze the AOI. Other M8 options and later milestones remain outside this implementation.

## Package identity and provenance

The generated and published package is ignored by Git. Its two deterministic builds were byte-identical:

| Asset              |   Bytes | SHA-256                                                            |
| ------------------ | ------: | ------------------------------------------------------------------ |
| `manifest.json`    |  14,428 | `226d2bb12618c578848d09767a1698b5535dad1e398a903b8ebd2b93dac9cc76` |
| `features.geojson` | 450,896 | `8c6e2e7155337bf1bcb931592b5463ad1936feab7ebacd2ce308b3f492148916` |

`validate-overview` accepted both the generated and published package. The published files matched the generated files byte-for-byte. The manifest binds the output to the real terrain manifest (`a398e519ee8537af3bcdcdb781a1501a3e0f45e58e47a4bdd2a986e15a06788f`), the existing OSM packages, and their source identities.

The terrain source is the Environment Agency LIDAR Composite DTM 1 m (2022 composite), attributed under the Open Government Licence v3.0. The OSM features derive from the dated Geofabrik Devon extract `devon-261016.osm.pbf`, extract timestamp `2026-10-16T20:21:21Z`, SHA-256 `52942b39636e1cb002e5d78a004668996cb469ee9c9e9b9b93049c66b9ac2cd5`, under ODbL 1.0 with OpenStreetMap contributor and Geofabrik attribution. The manifest preserves the selected EPSG:1314 + EPSG:19916 operation and its reported 2 m accuracy. The preferred OSTN15 grid is unavailable with PROJ networking disabled; numeric inverse consistency is not absolute geodetic accuracy.

## Browser evidence

Screenshots were captured from the production preview in Chromium 156.0.8078.4 at a 1440 × 960 CSS viewport and DPR 1.5. Both the main viewer and MapLibre reported ANGLE/Vulkan SwiftShader; these captures do not demonstrate hardware-renderer performance.

- [Real terrain, buildings, roads, and opened overview](screenshots/M8-overview-real.png)
- [Synthetic M0 with compact geographic-overview-unavailable explanation](screenshots/M8-overview-synthetic-unavailable.png)
- [Real browser evidence JSON](artifacts/M8-browser-evidence.json)
- [Share-build evidence JSON](artifacts/M8-share-evidence.json)

The real overview showed the AOI outline, road centerlines, and building footprints with north-up framing, metric scale, layer status, pending-AOI wording, separate EA source context, OSM/Geofabrik attribution when OSM layers were visible, and MapLibre licence credit. The MapLibre canvas measured 567 × 375 backing pixels (378 × 250 CSS pixels). The browser observed 32,570 ms from activation click to ready state in this SwiftShader run; this is descriptive only. Requests were limited to same-origin overview manifest/GeoJSON and local bundled resources; external requests and browser errors were zero.

The share build retained the synthetic M0 scene. It made zero MapLibre resource requests, zero real-package requests, and zero external requests. The overview remained unavailable for synthetic geometry, with no geographic map canvas and no real coordinates assigned.

## Verification

Python checks ran against the repository's isolated `pipeline/.venv`:

| Command                                                                                                                                  | Result                                                         |
| ---------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `cd pipeline; .\.venv\Scripts\python.exe -m pytest -q`                                                                                   | 219 passed                                                     |
| `cd pipeline; .\.venv\Scripts\python.exe -m pytest tests/test_overview_export.py -q`                                                     | 20 passed                                                      |
| `cd pipeline; .\.venv\Scripts\ruff.exe check torquay_pipeline tests`                                                                     | Passed                                                         |
| `cd pipeline; .\.venv\Scripts\ruff.exe format --check torquay_pipeline tests`                                                            | 41 files already formatted                                     |
| `cd pipeline; .\.venv\Scripts\python.exe -m pip check`                                                                                   | No broken requirements                                         |
| `cd pipeline; .\.venv\Scripts\python.exe -m torquay_pipeline.cli build-overview`                                                         | Passed; 1 AOI, 196 roads, 1,000 buildings                      |
| `cd pipeline; .\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-overview`                                                      | Passed; generated package valid                                |
| `cd pipeline; .\.venv\Scripts\python.exe -m torquay_pipeline.cli publish-overview`                                                       | Passed; published package byte-identical                       |
| `cd pipeline; .\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-overview --package-dir public/worlds/torquay-poc-001/overview` | Passed; published package valid                                |
| `cd pipeline; .\.venv\Scripts\python.exe -m torquay_pipeline.cli build-overview --output-dir ..\data\generated\overview-m8-repeat-final` | Passed; second deterministic package matched both hashes above |

Node gates ran in an isolated validation copy (`C:\vibe\localSimulator-m8-check-20261019`) after `npm.cmd ci` there succeeded with 0 vulnerabilities. The user's port-5173 server was not stopped or reused.

| Command                               | Result                                                                              |
| ------------------------------------- | ----------------------------------------------------------------------------------- |
| `npm.cmd ls --depth=0`                | Passed; pinned dependency tree present                                              |
| `npm.cmd run typecheck`               | Passed                                                                              |
| `npm.cmd run lint`                    | Passed                                                                              |
| `npm.cmd run format:check`            | Passed                                                                              |
| `npm.cmd test`                        | 20 files, 275 tests passed                                                          |
| `npm.cmd run build`                   | Passed; Vite emitted the existing large-chunk advisory for the lazy MapLibre bundle |
| `npm.cmd run build:share`             | Passed; real-world package excluded from `dist`                                     |
| `npm.cmd run test:e2e:overview:real`  | Passed, 3 tests                                                                     |
| `npm.cmd run test:e2e:overview:share` | Passed, 1 test                                                                      |
| `npm.cmd run test:e2e:tvw014:full`    | Passed, 19 passed, 8 skipped, 0 failed                                              |
| `npm.cmd run test:e2e:tvw014:real`    | Passed, 3 tests                                                                     |
| `npm.cmd run test:e2e:tvw014:share`   | Passed, 2 tests                                                                     |
| `npm.cmd run test:e2e:tvw015:real`    | Passed, 1 test                                                                      |
| `npm.cmd run test:e2e:tvw015:share`   | Passed, 1 test                                                                      |

### Fix round 1 after independent review

The review found output-path protection gaps in overview build/publish and an invalid published-package command. The output guards now canonicalize Windows paths, account for symlink/junction parents, reject equal/ancestor/descendant overlaps with all protected inputs regardless of selected layers, and permit only the exact reserved `terrain/overview` publish destination. Output checks happen before derivation or replacement. Backup directories use unique owned names; a pre-existing fixed-name backup is preserved, and a collision with a generated backup name fails without replacing the package.

The focused `tests/test_overview_export.py` suite covers attempts to write to or over `ROOT/docs`, the AOI config/GeoJSON, source manifest, raw data, terrain paths/files, road/building packages, and package paths; it also verifies input bytes and pre-existing backups remain unchanged on rejection/collision, and verifies rollback. It passed 20 tests. The symlink/junction guard is tested by injecting a linked-path component because Windows denied creating a real symlink in this environment.

From `pipeline`, ran `.\.venv\Scripts\python.exe -m torquay_pipeline.cli validate-overview --package-dir public/worlds/torquay-poc-001/overview`. The CLI resolved the package to `C:\vibe\localSimulator\public\worlds\torquay-poc-001\overview` and validation passed after publication with the package hashes above.

#### Fix round 2

The second review found that the publication exception could also hide an ancestor overlap when a custom terrain directory sat under ROOT/docs or data/raw. The exception is now bound to the exact (terrain_dir / "overview", terrain_dir) pair. Regression cases set terrain to ROOT/docs/milestones and ROOT/data/raw/ea_dtm; both are rejected before package validation and create no output. The focused suite passed 20 tests and the full suite passed 219. Default publication succeeded byte-identically, followed by successful validation of the published package using the corrected command above. Node typecheck, lint, format, unit, and both production builds passed in the isolated validation copy.

Final independent Sol re-review returned PASS. It reproduced both nested-path rejections before validation or writes, confirmed the normal terrain/overview publication path remains allowed, and reran the focused Python suite (20/20), Ruff check/format, and `git diff --check`. The reviewer made no edits and did not repeat the browser run; the production-browser screenshots and profiles above remain the recorded visual evidence for this Python-only correction.

The M8-specific browser profiles and unit/format gates were rerun after the compact synthetic-panel change. The full TVW-014 profile subsequently passed with 19 passed, 8 expected profile skips, and no failures. The dedicated TVW-014/015 real/share profiles passed before that final UI-only adjustment; the full profile and M8 profiles exercised the adjusted code.

## Failed attempts and environment notes

- `npm.cmd ci` in the live checkout failed with Windows `EPERM` while unlinking the in-use `rolldown-binding.win32-x64-msvc.node` beneath `node_modules`; the user-owned Vite process on port 5173 was left running. The partially pruned root dependency tree was not used for verification. A disposable validation copy was created and `npm.cmd ci` succeeded there.
- `npm.cmd ls --depth=0` in the live checkout then failed because the unsuccessful install had partially pruned that dependency tree. `npm.cmd ls --depth=0` passed in the isolated validation copy after its clean install.
- An initial `npm.cmd run test:e2e:tvw014:real` ran after a share build, so its real package was absent and all three tests failed. Rebuilding with `npm.cmd run build` before the real profile resolved the profile setup; the corrected run passed 3/3.
- An initial Python command used an incorrectly formed venv path and did not execute; the corrected commands above ran and passed.
- The first `npm.cmd run build:share` in the isolated validation copy was started concurrently with `npm.cmd run build`; both manipulated the same `dist` directory, producing a transient Windows `ENOTEMPTY` cleanup error. Running `npm.cmd run build:share` serially passed, and the overview share E2E profile passed afterward.
- An initial Prettier check of this handback detected the corrected validation-table row's formatting; Prettier was applied and the final formatting check passed.

## Preservation and limits

The supplied source plan SHA-256 remains `144C9C704EA1C10FA2D503DBA3233B089528585BE7D36B7B94164D28BA40D571`. The user-owned installer SHA-256 remains `B4EDF70FA040968958C662FFB09FEEEB0EECA07759E6ED7742606BCC39F29FC6`. Historical screenshots were not overwritten by the final isolated runs. The M8 derivative stays ignored and no source package, AOI, coordinate transform, or source data was changed.

Remaining limits: MapLibre is unavailable for synthetic worlds; the overview does not render terrain or track the camera; the two roads without AOI centerlines are omitted; feature coverage remains unverified; the AOI remains pending. This handback does not authorize TVW-016 or later work.
