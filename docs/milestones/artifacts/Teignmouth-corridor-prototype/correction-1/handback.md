# Continuous station/lateral correction: stopped at necessary earthwork preflight

Status: **NEEDS USER DECISION; not accepted; independent Sol review pending.** The sole Sol correction and final authorized build were used. The corrected chart still violates the unchanged strict `<5 m` source-relative earthwork criterion. No retry, third build, browser integration or candidate derivative is authorized by this result.

## Exact measured failure

The one [build 2 report](build-2/report.json) stops at its necessary preflight, before full mesh assembly. After 7,990 checked samples, the first violating sample was:

| Field                    | Actual value                               |
| ------------------------ | ------------------------------------------ |
| Station                  | 141.0 m                                    |
| Lateral coordinate       | −6.2086573699419745 m                      |
| Local X/Z                | `[-147.91999534598952,-96.08000465401048]` |
| Source terrain Y         | 2.934379492879626 m                        |
| Fixed-recipe candidate Y | −2.076721888421713 m                       |
| Absolute change          | **5.011101381301339 m**                    |
| Strict limit             | **<5 m: FAIL**                             |
| Sample rule              | Chart/source-plane edge intersection       |

This is the first failing sample in deterministic station/lateral/rule/X/Z order, not a completed global maximum. It lies in the lateral transition, outside the estimated 6 m carriageway and 1 m shoulder. The chart's source-plane intersections and target samples are necessary checks, not a replacement for final overlay/gradient/topology validation. The stop means those final gates did not run.

Actual measured build wall time was **3.1481524000 s** against 180 s. Actual peak process working set was **512,299,008 bytes**. No arbitrary allocation or payload cap was added. The saved chart has **1,467 vertices and 2,592 triangles**; X/Z, station/lateral and index buffers are **23,472 + 23,472 + 31,104 = 78,048 bytes**. These are the chart buffers, not a completed terrain/road mesh or runtime payload.

## Correction and preservation

Three new Python paths implement this correction; the initial Python files were left unchanged:

- `pipeline/torquay_pipeline/teignmouth_corridor_continuous.py`: fixed station sections at source vertices, half-metre intervals, target endpoints, anchor and fade endpoints; source miter/bisector joins interpolated along each source segment; continuous barycentric station/lateral fields; necessary earthwork preflight before full assembly. It contains no per-vertex nearest-segment selection. Further assembly code is unreachable after this measured preflight failure.
- `pipeline/scripts/build_teignmouth_corridor_continuous.py`: fixed fresh build-2 evidence directory, one 180 s watchdog, actual Windows memory measurement, exception/timeout records and preservation of initial evidence.
- `pipeline/tests/test_teignmouth_corridor_continuous.py`: eight synthetic controls for miter width, station union, chart continuity, invalid joins/triangles, source-plane intersections, strict preflight semantics and off-ground conflicts. Synthetic tests read no real source package and consume no additional build.

The [authorization transition](authorization-transition.json) binds the amended specification and all initial-code archives. The exact original specification was recovered from the unchanged prefix and verified against its original submission SHA-256 before being archived. The original handback and submission hash manifest were not modified. [Invariant checks](invariants.json) verify all ten original submission entries against unchanged originals or, for the intentionally amended specification, its exact archived bytes. They also verify that the complete profile station/source/smoothed arrays are identical to build 1 and that all pre-build correction code/archive bindings still match.

The pinned source remains release `616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a`, source heightfield SHA-256 `c61bd03d4172bffb07be596c4f63cc11a0681d0cacd884bb7dfcf3411be815af`, road payload SHA-256 `cd44d5c9aa4f8ef107176b31b86dbfe4ad5f98271ccbcbc5a05d677a38385986`. The same full-part Gaussian profile, centerline, estimated width, shoulders, blend rule, influence, fade and registered rectangle were retained. No source/profile parameters were tuned. Lateral chart lines explicitly include the carriageway/shoulder and minimum/maximum blend envelopes; any final mesh would still require its actual boundaries and overlay to pass all gates.

The [before](build-2/preservation-before.json) and [after](build-2/preservation-after.json) snapshots compare **880 paths with zero changed paths**, including old prototype evidence and the old handback. Coordinator-owned checkpoint/spec and new correction evidence remain explicitly outside that snapshot; the amended spec is separately frozen in the authorization transition. The scan does not independently hash all ignored raw GIS downloads. No GIS/package/source writer, old v2 runner/guardian/permit/profile/activation machinery, public/default loader, main Vite config, accepted preview, Site, historical package or AOI writer was invoked. Port 5173 was not touched. No commit/push/merge occurred.

## Evidence and validation

Actual geometry is available for independent inspection:

- [Chart X/Z Float64 buffer](build-2/chart-xz.f64), SHA-256 `fd90cdeb162afd8232fbd03531341d02acd1210e315bfce4582afa1e9ac6379e`.
- [Chart station/lateral Float64 buffer](build-2/chart-station-lateral.f64), SHA-256 `422ca324ba995f82eadf136b7b0716e4265e3b84b4731eb3e971549cd44f29e8`.
- [Chart triangle UInt32 buffer](build-2/chart-indices.u32), SHA-256 `8ba1c505d505ab25ce69db419ebfac7d9d7f22de92f4defe206fcb397e42e911`.

The [verification record](verification.json) lists exact commands/results. Focused corridor/road/topology/terrain tests: **131 passed, 1 skipped in 4.55 s**. The existing skipped test requires Windows directory-symlink privilege. Scoped Ruff lint and formatting passed. Final Markdown/JSON formatting and diff checks are recorded separately in that verification record.

Full candidate mesh/road buffers, final source/terrain overlay and added-gradient gates, complete building contact including `osm:way:208684847`, local full-width acceptance, composite walking, DEV harness, browser fallback, TypeScript/Vitest harness gates, camera pairs, screenshot inspection and product/share browser regressions did not run because the preflight stop applied. No failed final mesh is missing: final mesh assembly never began; the actual failed chart inputs and exact witness were retained outside runtime-serving paths. There is no screenshot or visual acceptance claim.

Build 2 is the only execution of the corrected algorithm. It cannot constitute an independent second build of that algorithm; no independent reproducibility claim is made. The original diagnostic and build 1 remain consumed, and the sole Sol correction is now consumed. This result does not establish that every continuous corridor method is infeasible; it establishes failure of this frozen recipe at the recorded necessary sample. The next action is independent Sol review of these actual files/evidence, followed by user disposition. No further implementation, retuning or browser work follows automatically.

## Correction checklist

- [x] Bind the authorized specification transition and archive original implementation bytes.
- [x] Replace nearest-segment assignment with a continuous chart in a separate correction module.
- [x] Verify synthetic controls and execute the final authorized build exactly once.
- [x] Save the actual chart buffers, exact preflight failure, source hashes and preservation evidence.
- [x] Stop before final assembly, runtime output or browser integration.
- [ ] Independent Sol review of the correction.
- [ ] User disposition of the exhausted experiment.
