# TVW-015: Optional street-name labels

**Status:** Accepted by the coordinator on 2026-10-19. The user authorized TVW-015 with “can we continue” after M7 acceptance. Implementation is authorized for this issue only; TVW-016 and later remain unauthorized.

## Authority and goal

This issue implements only the street-label part of the M8 suggestion “Street labels and a MapLibre overview/minimap” in `docs/project-plan.md`. It adds optional names to the existing local road layer to make the viewer easier to navigate. The overview/minimap and other M8 options remain future work.

The current retained road package contains 198 mapped features, 95 with a nonblank `sourceTags.name`, and 67 distinct names after trimming outer whitespace. These are properties of the retained OSM extract, not a feature-completeness claim. Examples include Teignmouth Road, Upton Road and Cricketfield Road. No new geographic source or package is needed.

## Preserve

- The synthetic default and `/?world=m0`, including clean-share startup and missing-package recovery.
- Existing terrain, road and building assets, schemas, source hashes and attribution.
- Existing walk/fly controls, movement speeds, loading recovery and browser QA boundaries.
- The TQ1 4HN centroid, 1,000 m candidate AOI and `selected_pending_coverage` / `not_checked` status.
- Historical screenshots and benchmark artifacts, including the accepted TVW-014 results.

Do not download source data, change geographic coordinates or package contracts, claim that labels or mapped counts establish coverage, approve/freeze the AOI, add a minimap, add dependencies, or start TVW-016/M9.

## Accepted implementation scope

### Candidate anchors

- Add a pure, typed and tested module that accepts an already validated `LoadedRoadPackage` and the current terrain sampler.
- Use only `feature.sourceTags.name`. Trim leading/trailing whitespace but preserve spelling and case. Empty names produce no candidate. Never infer a name from nearby context, a road reference, or another source.
- For each clipped centerline part, derive its arc-length midpoint by summing segment lengths and interpolating on the segment containing half the total length. Do not use the midpoint of the part's bounding box or join disconnected parts.
- Sample terrain at the local X/Z anchor and place the label anchor **0.25 m above** that sampled ground. Reject nonfinite, zero-length or unsampleable candidates; never substitute zero elevation.
- Retain road ID, part index and source name so selection and DOM identity remain deterministic.
- Keep all calculations in the existing local metre coordinate system: X is east and negative Z is north. Do not add transforms to the viewer.

### Screen-space label display

- Add a road-controls toggle named **Street names**, initially off. It is enabled only when the validated road package is loaded and the road layer is visible. Hiding roads immediately hides the labels.
- Use a bounded, absolutely positioned DOM overlay projected through the existing Three camera. Labels are annotations, not physical signs.
- Show at most 20 visible labels, no farther than 500 m from the camera. Cull anchors behind the camera and outside the viewport.
- Display no more than one instance of each exact, trimmed name. On every camera update, select deterministically by camera distance, road ID, then part index.
- Use each label's rendered bounds with a small documented padding for screen-space collision rejection. Avoid overlaying the primary controls, telemetry, road/building controls, and attribution panels.
- Use `textContent` for source strings; names containing markup characters must render as text. The overlay must not capture pointer input or interfere with pointer lock, movement, toggles, reset or Escape.
- Reuse a bounded set of DOM nodes and vectors across frames. Do not create labels or allocate candidate arrays on every render frame.
- Update projected positions from the existing render lifecycle and re-evaluate after camera movement and viewport resize.

### Lifecycle and accessibility

- Expose an accessible toggle name and accurate `aria-pressed` state.
- Report currently eligible and visible label counts as display diagnostics, not as road-coverage metrics.
- Failed, stale or cancelled road loads, road hiding, world replacement and application disposal must hide/remove labels and release associated listeners/resources.
- Repeated toggles and road-package reloads must not duplicate nodes. Returning to synthetic terrain must leave no real road names visible or retained in the DOM.
- Keep OSM contributor and Geofabrik attribution visible whenever the real road layer is shown.
- Document that DOM labels are not depth-occluded by terrain/buildings; do not imply they are occlusion-aware.

## Tests and browser evidence

### Unit tests

Use fictional fixtures and cover:

- Straight, bent, reversed and multipart arc-length midpoint calculation.
- Repeated zero-length segments, wholly zero-length parts and invalid/nonfinite samples.
- Sampled terrain-relative Y and the documented offset.
- Blank/missing names and markup-looking strings.
- One exact-name candidate chosen deterministically, including distance and identity tie-breaks.
- Behind-camera, viewport and 500 m distance culling.
- Screen-space label collisions, control-panel avoidance and the 20-label maximum.
- Toggle visibility, road visibility changes, resize, repeated toggles, replacement and disposal without leaked/duplicate DOM nodes.

### Actual browser verification

Run production browser checks against the existing local package:

1. Enable roads and street names; verify every rendered name comes from a loaded `sourceTags.name` value.
2. Inspect at least three named-road annotations in an overview and walk view; capture fresh screenshots with readable text and existing attribution/status.
3. Move and turn the camera, resize the browser, and verify labels stay attached to their projected road anchors.
4. Verify label controls do not block pointer lock, mouse look, WASD, Shift, reset or Escape.
5. Hide/show roads and labels, repeat toggles and world changes, and verify no duplicates or stale real names.
6. Run the clean share build without real assets and verify synthetic startup/recovery remains usable and no real road name appears.
7. Record page/console errors and confirm no runtime source/API requests are introduced.

Save new TVW-015 captures and a separate labels-off/labels-on measurement artifact. Use the same viewport, camera pose, renderer and timed-sampling method for both conditions, record label node counts and renderer/browser identity, and report the observed result without a numeric pass/fail threshold. Do not overwrite TVW-014 benchmark results. A software-renderer measurement must be identified as such and cannot be presented as hardware performance.

## Likely files

- `src/scene/roadLabelCandidates.ts` and focused unit tests.
- `src/app/createRoadLabels.ts` for DOM creation, projection, culling, collision and cleanup.
- `src/app/createApp.ts` and the existing viewer stylesheet for toggle and lifecycle integration.
- `tests/e2e/road-labels.spec.ts` and an isolated production Playwright profile.
- `README.md` for the street-name toggle and its limits.
- `docs/milestones/TVW-015.md`, `docs/milestones/artifacts/TVW-015-label-overhead.{json,md}`, and fresh screenshots under `docs/milestones/screenshots/`.

No Python/GIS pipeline, terrain/building/road package, road asset schema or dependency changes are expected.

## Acceptance gates

- `npm.cmd run typecheck`, `npm.cmd run lint`, `npm.cmd run format:check`, `npm.cmd test`, `npm.cmd run build` and `npm.cmd run build:share` pass.
- Existing `npm.cmd run test:e2e:tvw014:full`, `:share` and `:real` profiles remain passing; focused TVW-015 production E2E passes with the local road package. Isolate its server port and output directory.
- Unit tests establish candidate geometry, terrain attachment, deterministic selection/culling and lifecycle behavior.
- Actual production browser verification meets the seven checks above; attach observed screenshots and record any limitations.
- Labels remain opt-in, synthetic mode stays functional, attribution stays visible, and no new source/dependency is added.
- Original source plan, raw/generated source packages and historical screenshots remain byte-identical. The overall AOI remains pending; feature completeness and AOI approval are outside this issue.

## Official API references

- [Three.js `Vector3`](https://threejs.org/docs/pages/Vector3.html) for camera projection of scene anchors.
- [MDN `Node.textContent`](https://developer.mozilla.org/en-US/docs/Web/API/Node/textContent) for rendering source names as text.

## Planning and authorization result

The planner inspected the current implementation and local road package. The retained package has 198 features, 95 named features and 67 distinct trimmed names. It recommended the street-label portion of M8 as a bounded navigation improvement, with the minimap deferred. The coordinator accepts this TVW-015 scope based on the user's separate “can we continue” instruction. No source files, data, tests or browser state were changed during planning. TVW-016 and later remain unauthorized.
