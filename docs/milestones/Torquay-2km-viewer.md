# 2 km terrain, buildings and roads handback

**Status:** implementation submitted for independent review. The overall AOI remains `selected_pending_coverage` / `not_checked`; mapped feature counts do not establish completeness.

## Published scene

The explicit `current_2km` route loaded one immutable release and used its readiness pointer, inventory, terrain, building and road assets. Release ID: `616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a`. The inventory totals 97,426,386 bytes. The rendered terrain is 1,001 × 1,001 samples at 2 m spacing. The browser reported 3,613 building footprints and 1,044 road ways; those are imported counts, not a completeness finding.

The release's terrain heightfield is 4,008,004 bytes with SHA-256 `c61bd03d4172bffb07be596c4f63cc11a0681d0cacd884bb7dfcf3411be815af`. The road payload is 87,338,409 bytes with SHA-256 `cd44d5c9aa4f8ef107176b31b86dbfe4ad5f98271ccbcbc5a05d677a38385986`. The buildings payload is 6,015,566 bytes with SHA-256 `8c63da52a578207c2a11afa881fd56524df47e787bf6213d68c77b1784003a58`.

The browser fetches the fixed `ready.json` first, validates the inventory, and pins every subsequent layer request to that release. The production test confirmed terrain/buildings/roads used the same release, the historical overview was not requested, the optional-layer failure preserved terrain and allowed synthetic recovery, and missing readiness caused no real package request. The source road payload remains byte-identical. Its Float32 renderer conversion now reorients one non-degenerate face whose winding flips at renderer precision and omits one face that collapses to zero area at Float32 precision; both source triangles remain represented unchanged in the validated package.

## Browser evidence

The final isolated production Chromium profile passed 3/3 tests on Chrome `156.0.8078.4`. It ran at 1440 × 960 for the overview, then resized to 1280 × 800; DPR was 1.5 and the renderer capped the canvas buffer at DPR 1. The overview and outer-annulus camera poses, canvas dimensions, browser version, load duration, package bytes, draw calls, triangles and frame timings are recorded in [the browser evidence JSON](artifacts/Torquay-2km-browser-evidence.json).

![Active 2 km terrain, building and road overview](screenshots/Torquay-2km-overview.png)

![Walk-mode view in the added outer annulus](screenshots/Torquay-2km-outer-annulus.png)

The outer-annulus image is a low eye-level view at local `x=-86.25 m`, `z=595.9375 m`, 1.70 m above sampled ground. It faces bearing 336.5° at a -7.3° pitch; a road corridor recedes between nearby buildings with terrain visible around it. The nearest road centerline is about 10.3 m away. This demonstrates the added bounds and walk clearance; it is not a street-feature alignment or completeness check.

This run used SwiftShader (`ANGLE`, Vulkan 1.3.0), not a hardware GPU. Across the 5-second frame sample the median was 3.158 FPS, p50 frame time 316.7 ms, p95/p99/maximum 366.7 ms, 15 draw calls and 2,969,639 triangles. This software-rendered result is slow and is not evidence of hardware performance. The package's 97.4 MB inventory and nearly 3 million visible triangles are substantial for this headless renderer.

## Verification

From the repository root:

- `npm.cmd run typecheck` — passed.
- `npm.cmd run lint` — passed.
- `npm.cmd run format:check` — passed.
- `npm.cmd test` — 297 passed across 23 files.
- `npm.cmd run build` — passed as part of `npm.cmd run test:e2e:torquay2km:real`.
- `npm.cmd run build:share` — passed; inspected `dist/worlds`, which contains only the two synthetic fixture directories and no real, recovery-stage, or intermediate GIS assets.
- `npm.cmd run test:e2e:torquay2km:real` — final run 3 passed. Two interim screenshot-pose runs failed only at the newly added test-authored pitch expectations (`-2.0°` expected but `-25.8°` observed; then an `-8°..-15°` range expected but `-7.3°` observed). The final `-5°..-15°` pitch expectation passed and the run captured both active-scene screenshots while confirming release pinning, navigation, resize, outer-annulus travel, layer failure recovery, and no-readiness behavior.
- `git diff --check` — passed before handback.

The historical/share Playwright profiles were not rerun for fix round 2; share-build filtering was checked with `npm.cmd run build:share` and its focused filesystem tests. The deferred deterministic build comparison was completed separately in fix round 3, with both full build roots retained and file-level results recorded below.

From `pipeline/`:

- `.venv\Scripts\python.exe -m pytest` — 293 passed, 1 skipped. The existing directory-symlink test skips because symlink creation is unavailable for this Windows account; the new Windows junction cases ran and passed.
- `.venv\Scripts\ruff.exe check .` — passed.
- `.venv\Scripts\ruff.exe format --check .` — passed.
- `.venv\Scripts\python.exe -m pip check` — passed (`No broken requirements found`).

The real production browser runs initially exposed a normal check on a valid source triangle after conversion to Float32. Inspection found one sub-millimetre face whose horizontal winding flipped and one whose vertices collapsed. The narrow renderer-only correction and unit regression now cover these cases without changing the road package bytes. A subsequent run exposed an outdated resize-test expectation: the real profile caps the WebGL backing buffer to DPR 1, so the assertion now waits for the capped dimensions rather than expecting DPR 1.5. The final production profile passed after both corrections and the final screenshot capture.

Vite emitted its existing native-config extension warning for `scripts/share-assets` and a large-chunk warning for MapLibre. Both builds completed successfully.

## Preservation

- The supplied source plan hash remains `144C9C704EA1C10FA2D503DBA3233B089528585BE7D36B7B94164D28BA40D571`.
- The user-provided installer hash remains `B4EDF70FA040968958C662FFB09FEEEB0EECA07759E6ED7742606BCC39F29FC6`.
- The original validated stage and its two recovery copies each remain 17 files / 106,957,125 bytes with the same inventory digest `E355DD2F36FC4A74F68E466B176602307A8CD3866CE963B3DFD91A3961037A49`.
- The historical 1 km package and prior milestone screenshots were not modified. The 2 km real package's readiness pointer, inventory and GIS payloads were not regenerated for this fix.

No AOI status, data source, dependency, source payload, or 1 km package was changed. The 2 km world remains an explicit local route; the synthetic default and share build remain available.

## Fix round 2 (2026-10-20)

This correction responds to independent review of the Windows path-safety, unbounded inventory-size and stale historical-route test findings. `build-scene`, `validate-scene` and `publish-scene` now inspect lexical path components for symlink/junction reparse points before resolving or writing. Build arguments and manifest-derived source paths are guarded before generation. Windows junction regressions cover output, source-directory and config-file paths, including a junction followed by `..`; they assert rejection before build/validation and sentinel preservation. The only skipped Python test is the pre-existing directory-symlink test because this account lacks symlink creation privilege; the new junction tests ran.

The current 2 km release inventory now rejects byte sizes outside per-asset limits before any terrain or optional-layer request. The fixed 1001 × 1001 Float32 heightfield must be exactly 4,008,004 bytes. Rehashed readiness/inventory tests prove oversized manifests and impossible heightfield descriptors fail after readiness/inventory only, with no downstream runtime request. The historical/share recovery E2E was aligned with the readiness-first protocol: it asserts the unavailable `ready.json` response, zero GIS requests beyond readiness, and working synthetic recovery.

The initial fix-2 handback recorded that a repeated source build had not yet been run. Luna fix 3 completed two full `current_2km` builds from the verified local EA and OSM sources; both source-stage and published-release validators passed, then the runner compared every runtime file against the active package. Run A took 961.423 seconds and run B took 961.508 seconds. Each produced release `616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a`, inventory SHA-256 `a66d56fdc38133e0243904dc842f6a79b08c5e3075d73b83515f7c4709c90cb0`, readiness SHA-256 `08399e71ba3a0c6d421982b5cd47973114a48060ddb4c0931378663faf07b3b4`, and the same 10 runtime asset lengths and hashes (97,426,386 bytes total). Run A is retained at `C:\vibe\localSimulator-2km-determinism-20261020\run-a\public\worlds\torquay-poc-001-2km`; run B is retained at `C:\vibe\localSimulator-2km-determinism-20261020\run-b\public\worlds\torquay-poc-001-2km` for independent review. The [durable comparison report](artifacts/Torquay-2km-determinism.json) records the exact command, pipeline commit and runner hash, working-tree state, source/config identities, run timings, readiness and inventory identities, and each file-level comparison. It also confirms the active package was unchanged during both builds.

Final browser profiles: `npm.cmd run test:e2e:torquay2km:real` passed 3/3 in 2.6 minutes; `npm.cmd run test:e2e:tvw014:real` passed 3/3 in 58.4 seconds; `npm.cmd run test:e2e:tvw014:share` passed 2/2; `npm.cmd run test:e2e:tvw014:full` passed 22 with 8 expected profile skips and 0 failures in 9.1 minutes. The full profile runs the large combined 2 km navigation case and its no-readiness recovery case. Its first run had 20 passed, 2 failed and 8 skipped: the 2 km test exceeded the suite's 60-second timeout, and the unavailable-package case expected a direct manifest request. The next run had 21 passed, 1 failed and 8 skipped because the full profile's 5-second assertion timeout was too short while navigation remained in `entering-walk`. The 2 km test now uses the dedicated profile's 240-second test limit and a 45-second bound for walk/fly and clearance transitions; the full profile then passed. The initial share run had 1 pass/1 failure because it expected a direct manifest request; the readiness-first assertion now verifies one failed/invalid readiness response, no downstream GIS request and successful synthetic recovery, and passes 2/2.

Final code gates: `npm.cmd run typecheck`, `npm.cmd run lint`, `npm.cmd run format:check`, `npm.cmd test` (299 tests), `npm.cmd run build`, `npm.cmd run build:share`; from `pipeline/`, pytest (299 passed, 1 skipped), Ruff check, Ruff format check and `pip check` all passed. The share output scan found only the two synthetic fixture packages and no real GIS, release, recovery-stage or intermediate assets. `git diff --check` passed. Vite retains its native-config extension warning and MapLibre chunk-size advisory.

After browser runs, 17 tracked historical screenshot/evidence files were restored to their Git baseline; all other tracked files in the saved 68-file screenshot/artifact set were already at baseline. The saved pre-run hash for `Torquay-2km-browser-evidence.json` differed from `HEAD`; because the requirement was restoration to the Git baseline, it was restored to and verified against `HEAD`. All tracked screenshot/evidence files are now clean. Source plan SHA-256 remains `144C9C704EA1C10FA2D503DBA3233B089528585BE7D36B7B94164D28BA40D571`; installer SHA-256 remains `B4EDF70FA040968958C662FFB09FEEEB0EECA07759E6ED7742606BCC39F29FC6`. The original validated stage and both recovery copies remain byte-identical: 17 files / 106,957,125 bytes each. No live 5173 process, AOI status, source data, package, dependency or screenshot baseline was changed.
