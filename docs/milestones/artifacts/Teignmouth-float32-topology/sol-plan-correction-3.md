# Sol plan — chart support and worker status correction

Date: 2026-10-24

## Diagnosis from build 1 evidence

Build 1 failed at `[-140,-63]` because the implementation treated the 35 m influence buffer around stations 140–155 as if every point inside it had a chart owner. The saved chart instead spans stations 108–187 and lateral coordinates −16 m through +16 m. Those extents match the frozen recipe: 32 m longitudinal fade and `3 m half-road + 1 m shoulder + 12 m maximum blend = 16 m` lateral reach. At station 140 the center is approximately `[-145.2152464267,-89.9123856158]`; `[-140,-63]` is approximately 27.4 m away, inside the 35 m influence but outside the chart strip. At lateral ±16 m and stations 108/187, the frozen treatment weight is zero.

The predecessor implementation left source heights unchanged when chart lookup returned no field. The new unconditional exception applied an unnecessarily broad ownership requirement. Nothing in this failure supports extending the chart, changing the recipe, or assuming a chart defect within the active treatment region.

## Correction 3 scope

1. Validate the chart’s complete triangle support and ownership. Keep station/lateral coordinates, source geometry, domain, frame, recipe, collision guard and all limits fixed. Do not widen chart or fades, add extrapolation, or sweep parameters.
2. Distinguish support classes for candidate vertices and required samples:
   - outside influence: unchanged source;
   - inside influence but outside validated chart treatment support: unchanged source, because the treatment weight is zero there;
   - inside expected chart support without a valid owner: hard failure;
   - required carriageway or shoulder samples without support: hard failure.
3. Preserve the zero-treatment boundaries and verify source-plane continuity there. Extend the source-overlay validation to the newly classified outside-support region while retaining the existing outside-influence check. Report outside-support counts, representative coordinates and source/candidate height differences, separately from required-target coverage/completeness.
4. Fix worker status telemetry. `_worker_build()` returns a logical failure code, but `_worker_entry()` currently discards it, so the child process can exit 0 while the build report says failure. Propagate a nonzero logical result as a nonzero child exit and report logical worker result, actual child exit, runner result, and externally observed command exit only when captured. Do not substitute the previously reported outer/tool value for a captured process code.

## Focused synthetic tests

- A point inside a broad influence buffer but outside a finite chart support retains source height.
- Missing ownership inside chart support and missing required carriageway/shoulder coverage fail.
- A corrupted chart support/completeness report fails.
- Lateral/fade boundaries have zero treatment and source contact; just-inside active samples remain treated.
- Worker logical result 2 propagates to child exit 2 and an unservable failed runner result; handled worker exceptions remain failures.

No numerical diagnostic or build was run for this plan. Build 1 remains consumed and immutable; all candidate numerical gates are still unavailable. This plan is for one bounded Luna correction only and does not authorize another build or browser/product integration.
