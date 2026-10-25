# Teignmouth corridor prototype: stopped at global safety gate

The initial implementation is **not an accepted fix**. Full build 1 stopped before browser integration because the fixed corridor recipe exceeded both unchanged global safety ceilings. No candidate mesh asset, DEV harness, screenshot or public asset was produced. No build 2 or parameter sweep ran. Independent Sol review is pending.

The [active specification](Teignmouth-corridor-prototype-spec.md) defines this fresh issue separately from exhausted Teignmouth topology-validation v2. The old v2 files, runner, guardian, profile, permit and activation machinery were not modified or invoked.

## Measured result

The [actual build report](artifacts/Teignmouth-corridor-prototype/build-1/report.json) records:

| Check                                   | Result                                                 | Unchanged criterion                |
| --------------------------------------- | ------------------------------------------------------ | ---------------------------------- |
| Maximum absolute source-relative change | 6.4609167576 m                                         | strictly less than 5 m: **FAIL**   |
| Maximum positive added edge gradient    | 2.3475946039 m/m                                       | strictly less than 1 m/m: **FAIL** |
| Float32 X/Z topology                    | 26,415 vertices; 52,662 upward nondegenerate triangles | measured pass                      |
| Exact source perimeter                  | 166 original 2 m boundary edges                        | measured pass                      |
| Holes / overlap                         | 0 / 0 m²                                               | measured pass                      |
| Euler characteristic                    | 1                                                      | measured pass                      |
| Build wall time                         | 5.1803221 s                                            | 180 s limit                        |
| Actual process peak working set         | 512,008,192 bytes                                      | measured; no memory admission cap  |
| Constructed X/Z / Y / index buffers     | 211,320 / 105,660 / 631,944 bytes                      | measured; no payload cap           |

The worst added-gradient edge is X/Z `[-157.5,-89]` to `[-157,-89]`: source Y `[3.0916280746,3.0806255341]`, candidate Y `[1.2596106529,0.0748108104]`. This is a failed experimental recipe, not proof that every corridor method is infeasible.

The first diagnostic invocation failed before any geometry verdict because NumPy 2.5 rejects `np.cross` on 2D X/Z vectors. Its [failure record](artifacts/Teignmouth-corridor-prototype/initial-diagnostic/failure.json) preserves the observed error and consumed invocation. Explicit 2D determinant arithmetic and a synthetic topology/hole regression fixed this implementation defect within the initial submission. The diagnostic was not retried. The coordinator authorized proceeding to the separately budgeted first full build, which then reached the safety stop above.

## Implementation and provenance

Only three new implementation files were created:

- `pipeline/torquay_pipeline/teignmouth_corridor_prototype.py`: independent fixed Gaussian profile and corridor surface, original-source-diagonal 0.5 m mesh with a conforming coarse perimeter, actual Float32 topology and early safety checks.
- `pipeline/scripts/build_teignmouth_corridor_prototype.py`: explicit diagnostic/build modes, fresh evidence directories, 120/180 s watchdog, measured Windows process peak memory and before/after hashes.
- `pipeline/tests/test_teignmouth_corridor_prototype.py`: eight synthetic kernel, boundary, invalid-input, fade and NumPy/topology regression controls.

The builder reads pinned release `616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a`; terrain SHA-256 `c61bd03d4172bffb07be596c4f63cc11a0681d0cacd884bb7dfcf3411be815af`; road payload SHA-256 `cd44d5c9aa4f8ef107176b31b86dbfe4ad5f98271ccbcbc5a05d677a38385986`. It retains OSM way 78455395 part 0 and estimated 6 m width. It does not create higher-resolution source elevations.

The independent Gaussian equivalent uses sigma 12 m, radius 18 samples, normalized weights and reflected endpoints (edge padding when the profile length is at most 18). It reads the packaged full part at nominal 2 m intervals and retains the exact final endpoint; the final interval is shorter and is recorded in the report. It does not import upstream code. There is no upstream 4 m thinning because this experiment specifies a 2 m profile and 0.5 m display patch. The rectangle remains X `[-182,-98]`, Z `[-136,-54]`, with 35 m target-line influence and 32 m along-road fade. The fixed implementation computes blend distance as `clamp(2*abs(target-source),2,12)` per vertex and applies cubic smoothstep weights; this is the prototype's explicit interpretation of the documented 1:2 transition rule. No recipe parameters were tuned after the measured failure.

The [preservation snapshots](artifacts/Teignmouth-corridor-prototype/build-1/preservation-before.json) compare 868 pre-existing repository, untracked and public-package paths with zero changes. Coordinator-owned checkpoint/spec and new prototype evidence were excluded explicitly. All ignored raw GIS bytes were not independently rehashed by this run; no source writer was used. No product loader, main Vite config, accepted preview, historical package, AOI, Site or port 5173 was changed by the implementer. No commit, push or merge occurred.

## Verification and remaining work

The [verification record](artifacts/Teignmouth-corridor-prototype/verification.json) lists exact commands and actual results. Focused corridor/road/topology/terrain Python tests passed: **123 passed, 1 skipped** in 3.66 s; the skip is the existing Windows symlink-privilege test. Scoped Ruff lint and format checks passed. `git diff --check` passed with existing line-ending warnings.

The full report retains every sampled source and smoothed profile elevation, height difference, signed grade and grade difference, plus geometry hashes. Failed mesh bytes were not saved: the implementation writes geometry only after its early safety gate. This limits independent inspection to the actual report, hash witnesses and generation code; no reproducibility result is claimed.

- [x] Preserve dirty workspace and use distinct prototype paths.
- [x] Run one bounded diagnostic; record its implementation error without retry.
- [x] Fix the NumPy compatibility defect and run a focused regression.
- [x] Run full build 1 and record topology, resources and failed safety ceilings.
- [x] Stop before browser integration, candidate output or further builds.
- [ ] Complete source/profile/geometry independent Sol review.
- [ ] Resolve user disposition of the stopped experiment.

Junction/nearby-road ownership, bridge/tunnel handling across surrounding roads, complete building contact (including `osm:way:208684847`), full-width/local acceptance, road reclip/agreement and composite walk clearance were not completed after the safety stop. Neither the standalone harness nor browser captures, runtime fallback, TypeScript/Vitest gates, deterministic build 2 or product/share browser regressions ran. There is no visual acceptance claim.

The initial implementation and its single diagnostic/full-build attempts are submitted for independent review. The sole Sol correction has not been used. Further recipe changes, retries or browser integration require a coordinator/user disposition consistent with the stop condition; this handback does not authorize them or any TVW-016/later work.
