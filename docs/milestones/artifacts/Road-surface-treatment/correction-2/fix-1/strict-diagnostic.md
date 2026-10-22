# Correction 2, Luna fix 1: strict diagnostic

**Date:** 23 October 2026

**Status:** Candidate fails mandatory numerical gates; not accepted.

**Policy:** The accepted Correction 2 limits are unchanged. This is an in-memory diagnostic only, not a derivative build record or browser-evidence record.

## Changes exercised

- Bumped the Python derivative version to `road-surface-preview-3.0.0` and synchronized the typed browser contract. Loader/schema tests reject the previous `2.0.0` asset as stale.
- Made intersected road-support triangle vertices protected carriageway core, including after shoulder fallback masks are applied.
- Took immutable snapshots for adjacent core conflict scanning and accumulated conflicts before writing sentinels.
- Fixed expanded shoulder projection eligibility to use the station-specific transition extent. Previously the tile query included the widened 32 m shoulder, but active projections were still clipped at the old default influence radius.

## Parkfield controls

Each full 6 m width was sampled at 0.25 m intervals (25 positions including both edges and center). These are display-grid terrain comparisons, not surveyed pavement values.

|    Station | Baseline span / crossfall | Corrected candidate span / crossfall | Center deviation | Result              |
| ---------: | ------------------------: | -----------------------------------: | ---------------: | ------------------- |
| 396.0108 m |   2.155838 m / 35.930637% |               0.018222 m / 0.247913% |      +0.013162 m | Passes this control |
| 409.2610 m |   2.562585 m / 42.709744% |               0.007073 m / 0.054913% |      +0.002441 m | Passes this control |

## Strict global results

The candidate before local harm fallback had maximum added gradient **4.008736 m/m**, at `[-836,384]` to `[-834,384]`; its maximum absolute terrain change was **10.454731 m**. After the connected source-ground fallback, the strict run still rejected the grid at **1.963506 m/m** on way `197534372`, part 1, station 6.0503–6.1507 m. The failing edge is `[208,968]` to `[210,968]`, with baseline magnitude 0.609388 m/m and preview magnitude 2.572894 m/m. The post-fallback grid has 12 connected harm components. Its maximum cut is **4.522749 m** and maximum fill is **4.791126 m**, within the 5 m preview policy.

This residual is a source-ground fallback seam, not a clipped 32 m treatment projection. At the two edge vertices, baseline heights are −22.880493 / −24.099270 m; the widened treatment candidate is −27.754692 / −28.030825 m; post-fallback heights are −22.885036 / −28.030825 m. The treatment candidate reduces the baseline edge slope to 0.138066 m/m, but the fallback boundary raises the preview edge slope to 2.572894 m/m. Projected to the way's first bend, these vertices are at approximately 6.11 m and 4.19 m lateral offset. The nearest building is `osm:way:197534355`, 8.96 m from the edge. No further grading/fallback change was made in this bounded fix.

## Building-base limits

The post-fallback display grid changed 1,202 of 3,613 building bases. Absolute shifts exceed the accepted 0.183 m p95 limit for **268** buildings, the 0.50 m local review threshold for **92**, and the accepted 2.424 m maximum for **9**. The global p95 absolute shift is **0.268273 m** and the maximum is **4.014984 m**. Largest individual shifts are:

| Building             | Signed base shift |
| -------------------- | ----------------: |
| `osm:way:198604317`  |       +4.014984 m |
| `osm:way:207474135`  |       +3.910545 m |
| `osm:way:208684714`  |       +3.816081 m |
| `osm:way:206414752`  |       +3.079797 m |
| `osm:way:1338740950` |       −3.018524 m |
| `osm:way:207473996`  |       +2.995960 m |
| `osm:way:208877527`  |       −2.905375 m |
| `osm:way:207341702`  |       +2.476441 m |
| `osm:way:207474015`  |       −2.461670 m |

A building-triggered source-ground fallback was not added. The measured violations span many separate locations and coexist with the residual slope failure; no bounded fallback was demonstrated that satisfies the strict building and gradient caps while preserving the mandatory roads. This candidate therefore remains a failed numerical result, not a claim that no future method can satisfy the amendment.

## Verification boundary

- Focused Python road-surface tests: 24 passed, 1 skipped because this Windows account cannot create a directory symlink.
- Ruff check passed.
- No derivative, execution record, screenshot, or browser run was produced. The strict numeric gates failed before the build/evidence stage, as required by the accepted protocol.
- Default `/`, source GIS, current/historical packages, AOI/status, TQ1 4HN, `sites/`, BeamNG installer, coordinator checkpoint, and port 5173 were not changed by this candidate.
