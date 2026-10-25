# Independent Sol review — corridor topology correction

Verdict: **FIX REQUIRED — prototype objective incomplete; correction budget exhausted.** Review was read-only; no code, numerical, test or browser work was run by the reviewer.

## Findings

1. **Strict earthwork criterion fails (behavior/formulation conflict).** The corrected preflight correctly rejects absolute change `>=5 m`. The saved witness is source Y `2.9343794929`, candidate Y `-2.0767218884`, difference `5.0111013813 m` at station 141 m, lateral `-6.20865737 m`, outside carriageway/shoulder in the lateral transition. This is a witness, not a global maximum. The code stops before ownership checks and final mesh assembly. Keep the limit and stop; no integration or automatic retry.
2. **Required prototype comparison remains incomplete (missing evidence).** There is no final Float32 mesh, complete overlay/added-gradient result, junction/road ownership evaluation, affected building contact (including `osm:way:208684847`), walk/fallback verification, runtime candidate or same-camera screenshot. This follows the required early stop but prevents acceptance.

The continuous topology correction addresses the plausible nearest-station discontinuity structurally: miter/bisector sections and `Chart.locate` interpolate shared station/lateral fields without per-vertex nearest-segment reassignment. Synthetic tests exercise chart continuity and strict threshold behavior. This does not establish that the original worst-edge gradient is fixed because corrected final geometry did not exist.

## Evidence and preservation

- All 20 correction-submission file size/hash entries and 9 authorization bindings match.
- The amended spec matches its authorization hash; all 10 original submission entries match the unchanged originals or exact archived original spec.
- Before/after preservation snapshots are identical; all 880 listed current paths rehash without mismatch. The scan excludes some ignored raw GIS data as disclosed.
- Profile arrays exactly match build1. Persisted chart buffers match their declared hashes and lengths: 1,467 Float64 X/Z/field records and 2,592 UInt32 triangles.
- Chart geometry/sampling and the 7,990-sample preflight are builder-reported evidence; reviewer did not regenerate them. Reported `131 passed, 1 skipped`, Ruff/format, runtime and memory figures are not rerun reviewer results.
- No new byte cap, profile change, public/default modification or extra numerical execution is evidenced. Corrected-algorithm independent reproducibility is unestablished.

All new-issue budgets are consumed: diagnostic1, builds1–2, and the sole Sol correction. The previous Teignmouth v2 issue remains separate, exhausted, FIX REQUIRED and inactive. Next disposition requires fresh user direction.
