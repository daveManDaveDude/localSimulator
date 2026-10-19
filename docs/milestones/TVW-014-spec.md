# TVW-014: Local demo smoke test, benchmark, README and attribution

**Status:** Accepted by the coordinator on 2026-10-19. Implementation authorized for TVW-014 only; TVW-015 and later remain unauthorized.

## Authority and goal

The user separately authorized TVW-014 on 2026-10-19. This issue implements the M7 work item in `docs/project-plan.md`: end-to-end local-demo smoke coverage, benchmark reporting, README instructions and attribution. It follows M7 work and acceptance plus the project testing, source provenance and handback protocols. Performance measurements are evidence, not pass/fail targets: the plan leaves the 60/30 FPS aspirations non-gating until a target machine is defined.

Deliver a local demo that starts synthetically from a clean checkout without GIS datasets, can use the documented local real-data packages after source restoration/regeneration, has accurate attribution and limitations, and produces repeatable workload-specific benchmark evidence.

## Preserve

- The synthetic M0 default and synthetic heightfield world.
- Existing terrain, optional buildings and roads, walk/fly controls and source contracts.
- The TQ1 4HN centroid, 1,000 m candidate AOI and `selected_pending_coverage` / `not_checked` status.
- Existing local raw/generated GIS files, source manifests, package hashes and historical screenshots.
- The supplied original plan and user-owned untracked installer.

Do not acquire new geographic data, modify geographic coordinates, infer missing coverage, approve/freeze the AOI, deploy/host the application, or start TVW-015/M8 work. Do not optimize without a measured problem and before/after evidence.

## Current findings

- Installed versions were checked: Node 22-compatible project; Three.js 0.186.1, Vite 8.3.4, TypeScript 6.0.3, Vitest 5.0.5, Playwright 1.64.1, ESLint 10.13.0, typescript-eslint 8.71.2 and Prettier 3.9.10. No dependency addition is needed.
- Existing local raw inputs are under `data/raw/ea_dtm` and `data/raw/osm`; derived terrain/building/road packages are ignored local assets under `public/worlds/torquay-poc-001`. Their identities must be verified before reuse. No package belongs in the clean-clone share build.
- The current full Playwright suite exercises local real-data routes and therefore cannot by itself prove clean-clone operation. Add a dedicated production smoke profile that runs without these ignored packages and confirms synthetic startup and graceful missing-package recovery.
- Use a separate isolated clone/copy and unique ports/output paths. Do not reuse, stop or overwrite the user's existing server, tracked historical captures or source files.
- The current repository-wide format check has two known markdown failures (`docs/milestones/TVW-012.md`, `docs/milestones/TVW-013-spec.md`). Correct these formatting-only issues as part of quality closure without changing their evidence/content.

## Accepted implementation scope

### 1. Clean-checkout synthetic production smoke

- Make a clean Git clone from the completed TVW-014 commit in a temporary isolated location; run locked dependency installation there. Do not use copied `node_modules` or untracked GIS data to qualify as a clean clone.
- Build/preview the share mode on a unique port with an isolated Playwright output directory.
- Verify renderer readiness, visible synthetic terrain and blocks, expected default/status labels, pointer-lock/WASD/Shift/reset/Escape interaction, resize and page recovery.
- Verify an unavailable optional real package produces a clear recoverable state and a working return to synthetic mode, without a blank page or unhandled page/console error.
- Verify the share build contains no real terrain/building/road package payloads.

### 2. Restored-source real-data smoke and regeneration

- Document the precise existing local EA DTM and OSM input paths, publisher/source identifiers, vintages, licences, hashes and existing pipeline commands. Do not download replacement sources.
- In an isolated checkout, restore only the named local source inputs, verify each input hash before use, and run the documented existing validation/export/import/publication sequence.
- Record generated package hashes and confirm repeatability when the same inputs/config/pipeline version are used.
- Run production browser smoke for terrain-only, terrain + buildings, terrain + roads, and combined terrain/buildings/roads routes. Check actual loaded-layer/provenance state, attribution, pending AOI status, walk/fly controls and recovery.
- Keep existing development-only QA camera hooks out of production; prove the tested production build does not install them.

### 3. Repeatable benchmark

Add a script and documented command that launches or targets the intended production preview without claiming measurements from an unknown/stale server. Use a dedicated, unique port and record build/commit and package identities.

Required workloads: synthetic M0; real terrain only; terrain + buildings; terrain + roads; combined scene flying; combined scene walking. Use documented stable scene-local poses. Prefer a 1920 × 1080 CSS viewport and DPR 1; if unavailable, report actual viewport and drawing-buffer dimensions.

For each workload, warm for approximately 3 seconds and collect 3 timed runs of approximately 10 seconds each, with the page visible and focused and requested layers fully loaded. Save raw frame-interval samples and report sample count, duration, mean, median, p95, p99 and maximum frame time; calculate FPS from frames divided by observed duration. Measure loading from navigation to the first rendered frame after requested layers finish, separately identifying fresh-context and warm-cache results. Record draw calls and rendered triangles from the renderer after actual render frames, along with active geometry/texture counts and exact asset-byte totals by manifest/payload/QA category without double-counting copies.

Sample JavaScript heap maximum when the browser exposes a supported measurement; record `unavailable` when it does not. `renderer.info.memory` geometry/texture values are object counts, not byte usage. Do not label JS heap as whole-process/GPU memory or frame cadence as GPU execution time. Report hidden-page throttling, focus loss, load failure, missing metrics, software rendering and other invalidating conditions; unavailable data must not be replaced with zero.

Include browser/version, operating system, renderer/GPU and hardware/software classification when observable, viewport/DPR, build identity, route, source/package hashes, pose and timing methodology. Do not use historical FPS as a current result. Performance aspirations remain descriptive; no arbitrary numeric threshold is added.

### 4. README, attribution and handback

Document supported Node/Python versions, locked install, immediate synthetic startup, local-only real data restoration/regeneration, optional routes/layer controls, normal/Shift speeds (15 / 41.25 m/s), walk clearance, benchmark usage and interpretation, missing coverage, estimated building heights, alignment limits, local asset/share-build separation, and recovery instructions. Clarify that the app performs no runtime source downloads and uses no hosted backend.

Keep Environment Agency, OpenStreetMap/Geofabrik and OS OpenMap comparison attribution tied to their actual use. Do not imply comparison imagery supplies the rendered terrain/building/road layers. Keep readable credits and source/licence links in the app and README/data-source documentation.

Produce a TVW-014 handback with exact commands/results, source and package hashes, clean-clone/real-regeneration/browser observations, benchmark JSON and human-readable summary, fresh screenshots for synthetic startup, combined real scene with attribution/status, and walking mode, plus defects/limits and next issue. Link the retained independent alignment comparison from TVW-012 rather than repeating that completed issue. Store new test artifacts under isolated `test-results/` output and explicitly promote only the selected new evidence; historical screenshot paths remain byte-identical.

## Likely files

- `scripts/benchmark.mjs` and a focused benchmark report validator/test if needed.
- `package.json` and an isolated Playwright smoke/benchmark configuration.
- `tests/e2e/local-demo.spec.ts` plus narrowly scoped corrections to existing selectors/configuration.
- `src/app/createApp.ts` or a small diagnostics module only if actual production renderer counters cannot be measured externally.
- `README.md`, `docs/data-sources.md`, `AGENTS.md`, `docs/project-plan.md`.
- `docs/milestones/TVW-014.md`, new evidence under `docs/milestones/screenshots/` and benchmark JSON under `docs/milestones/artifacts/`.
- Formatting-only changes to the two known Markdown baseline failures.

No terrain/building/road geometry or schema changes are expected. No additional large dependency, service, API, credential or container is allowed.

## Acceptance and verification

- A fresh Git clone with no GIS files builds, launches and passes the synthetic production smoke; the share build excludes real packages.
- Documented local-source restoration and regeneration runs from verified existing sources, and real production routes load with correct provenance/attribution and without critical browser errors.
- Automated smoke covers startup, missing-package recovery, actual layer selection, walk/fly controls, reset, Escape, resize, visibility/route recovery and share-data exclusion.
- The benchmark emits complete raw data and environment metadata for every required workload, or explains precisely which optional measurement is unavailable. No invented measurement and no ungrounded performance pass/fail threshold.
- README, in-app attribution, AOI caveats and source/package identities are accurate; synthetic fallback remains functional.
- Screenshots show the actual production browser scenes and do not overwrite historical evidence.
- Typecheck, lint, format check, unit tests, production/share builds, existing and new Playwright tests, Python pytest, Ruff and pip checks pass. Record any environmental limit rather than claiming an unexecuted gate.
- TVW-014 acceptance does not establish overall feature completeness, approve/freeze the AOI, authorize redistribution/deployment, or start TVW-015/M8.

## Official API references

- [Three.js WebGLRenderer](https://threejs.org/docs/pages/WebGLRenderer.html) and [renderer statistics](https://threejs.org/docs/pages/Info.html) for drawing-buffer, render-call, triangle and active geometry/texture-count definitions.
- [Playwright web server configuration](https://playwright.dev/docs/test-webserver) for isolated server lifecycle/port behavior, and [screenshots](https://playwright.dev/docs/screenshots) for browser captures.
- [Vite static deployment and preview](https://vite.dev/guide/static-deploy.html) for production-output verification.

### Planning result

No implementation blocker found. The target machine is not formally defined, so report observed performance without converting aspirations into an acceptance threshold. The planner performed read-only inspection and official documentation/version checks; no source edits, downloads, benchmark, test or browser run occurred during planning.
