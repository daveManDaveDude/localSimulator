# TVW-013: Ground-following walk mode

**Status:** Accepted by coordinator on 2026-10-19 for TVW-013 implementation.
**Authority:** The user's “continue with the next step” after TVW-012 PASS authorizes TVW-013 only. The user also requested doubling normal movement speed and Shift-boost speed. TVW-014 and later remain unauthorized.

## Requirements and preserved state

Follow the immutable source plan `docs/Torquay_JS_Virtual_World_PoC_Codex_Plan.md`: §10/M6 (walk mode and its 1.7 m eye-height gate), §11 testing and visual acceptance, §§13–14 quality gates and handback, and §15/TVW-013/dependencies. Read with `docs/project-plan.md` §10/M6 and §15. Source-plan SHA-256 remains `144C9C704EA1C10FA2D503DBA3233B089528585BE7D36B7B94164D28BA40D571`; do not edit the source plan.

Implement only M6 ground-following navigation. Preserve the working synthetic default, existing real terrain/building/road routes and package data, attribution, coordinate conventions, TQ1 4HN anchor, and AOI `selected_pending_coverage` / `not_checked` status. Do not modify source GIS data, AOI configuration, projection transforms, package manifests, or dependencies. Do not begin TVW-014.

## Accepted movement speeds

The existing `DEFAULT_FLIGHT_CONFIG` is 7.5 m/s with a 2.75× Shift multiplier (20.625 m/s boosted). Double both absolute speeds and retain that multiplier:

| Mode | Normal movement | Shift movement |
|---|---:|---:|
| Fly | 15 m/s | 41.25 m/s |
| Walk | 15 m/s horizontal | 41.25 m/s horizontal |

These are fast navigation speeds, not a realistic pedestrian simulation. Walking speed measures horizontal displacement; terrain following changes Y independently. Normalize diagonal input in both modes. Flight retains full look-direction movement and Space/Control vertical movement. In walking mode, horizontal movement follows camera yaw, pitch does not change horizontal speed, and Space/Control do not cause vertical movement.

## Navigation behavior

Use explicit `fly`, `entering-walk`, and `walk` states. Newly loaded worlds start in fly mode. Provide an accessible mode button and an `F` shortcut while pointer lock is active; ignore repeated keydown so holding F cannot toggle repeatedly.

- **Fly → walk:** retain XZ and orientation. If the camera is below sampled terrain, reject entry with a clear message and make no positional correction. Otherwise approach `sampleHeight(x,z) + 1.7 m` monotonically at a documented 20 m/s vertical maximum. Hold XZ during acquisition and report the acquisition state and remaining clearance. Enter steady walk mode only when the target is reached. Pressing the fly toggle cancels acquisition at the current pose.
- **Walk → fly:** preserve the complete XYZ position and orientation at the mode switch.
- **Steady walk:** move horizontally from camera yaw; after each accepted movement step, set Y to the active terrain sample plus 1.7 m. Do not smooth vertical movement in a way that causes uphill penetration or downhill hovering.
- **Reset:** fly mode retains the existing exact spawn reset. Walk mode remains in walk, returns to spawn XZ at sampled terrain +1.7 m, and restores spawn orientation. This explicit reset is an intentional repositioning.
- **Input lifecycle:** pause walking/acquisition when unlocked, blurred or hidden; clear held keys on unlock, blur, visibility change, reset, route/world change and disposal. A mode toggle itself must not move XZ or change orientation.

Use the active world's existing sampler and bounds. Clamp XZ to the valid world bounds before sampling. If a sample is null/nonfinite or the sample domain is incompatible with the bounds, retain the last valid pose and show contextual feedback; never substitute zero elevation. Walking follows terrain under road ribbons. Building/road collision, jump, gravity, stairs, slope limits and obstacle avoidance are deferred.

Consume ordinary frame deltas in bounded substeps: process up to 0.25 seconds per update, with substeps no larger than 0.05 seconds; deliberately discard excess suspension time. Verify frame-partition equivalence at 6/30/60/144 Hz and clear input while suspended so background time does not become catch-up travel.

## Implementation surface

Likely files (the implementer may adjust names while preserving the isolated design):

- `src/camera/movement.ts`: speed defaults and bounded timing policy.
- New `src/camera/walkMovement.ts` and tests: planar movement, sampling, transition and timing helpers.
- `src/camera/FreeFlyController.ts`: mode ownership and integration with the existing pointer-lock lifecycle.
- `src/app/createApp.ts` and `src/style.css`: accessible mode control, mode/speed/ground/clearance telemetry and help.
- Camera/movement unit tests and a focused `tests/e2e/navigation.spec.ts`.
- `README.md`, `AGENTS.md`, M6 status in `docs/project-plan.md`, this milestone handback, and `.codex/torquay-plan-implementation.md`.

Avoid multiple pointer-lock owners. Preserve the controller's listener cleanup, the synthetic M0 analytic terrain sampler, heightfield `TerrainGrid.sampleHeight`, building/road layer ownership, and existing error/recovery behavior.

## Acceptance and proof

- Normal/Shift movement is exactly 15/41.25 m/s in both modes; Shift ratio remains 2.75. Diagonal movement does not exceed configured speed.
- Once walking, camera clearance is 1.7 m ±0.05 m on flat terrain, slopes, ridges, both terrain-triangle halves, corners and exact valid bounds.
- Acquisition is continuous, bounded and visibly distinct; below-ground entry rejects without repositioning. Walk-to-fly preserves XYZ immediately. Mode changes otherwise preserve XZ and orientation.
- Pitch changes do not alter walking horizontal speed. Walking Space/Control do not change clearance. No nonfinite position, below-ground camera or off-grid sample is accepted.
- Reset, Escape/unlock, blur, visibility, world changes and disposal clear input safely. Synthetic default/M0 and terrain-only and combined real routes remain usable.
- UI identifies current mode, configured speed, sampled ground and eye clearance. Attribution and AOI status are unchanged.
- Unit tests cover negative terrain elevations, slopes/ridges, both triangle halves, edges/corners, invalid samples/bounds/time, diagonal and Shift speeds, frame partitioning, vertical camera look, ignored walking vertical keys, acquisition/rejection/cancellation and reset/mode semantics.
- Playwright verifies pointer lock, mode switching and movement in synthetic heightfield and actual combined terrain/building/road routes; sampled clearance while moving uphill/downhill and with Shift; pose preservation; Escape/input cleanup; and world-switch regressions. Save new walking and flying screenshots; record browser, renderer, viewport, camera pose, mode, speed, clearance and observations. Do not overwrite historical screenshots.

## Verification commands

From the repository root on Windows:

```powershell
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run format:check
npm.cmd test
npm.cmd run build
npm.cmd run build:share
npm.cmd run test:e2e -- --output test-results/tvw013-implementation
git diff --check
```

From `pipeline`, retain Python regression gates:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\python.exe -m pip check
```

Use actual browser evidence where available and inspect the screenshots. Report any software-renderer or browser limitations; do not claim hardware performance from SwiftShader. The milestone handback must list files, commands/results, actual browser observations and screenshot paths, provenance, limitations, and next proposed issue. TVW-014 remains unauthorized.
