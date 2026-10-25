# Coordinator disposition 21 — reserve one Sol correction for test evidence

Date: 2026-10-24

**Decision: correction 4 fails acceptance review pending two focused test/fixture corrections. Reserve the sole authorized Sol correction (1/1), limited to the regression fixture and tests. No candidate build is authorized; candidate remains NO-GO.**

Independent Sol review 12 (SHA-256 1b4b34864a27d8f5745e42557410ff77669402f9eb88bd4295a5656acfbf887d) inspected correction 4 and found the implementation's prototype-local fragment aggregation, gap/excess checks, pairwise overlap detection, extrema handling, empty behavior and call-site isolation sound. It identified two validation gaps:
1. The saved fixture uses the already face-clipped expectedOutsideClip as the clip operand, rather than the original outsideGeometry used by diagnostic 2 and production. The exact original is in diagnostic-2/run-1/clip-reconstruction.json, SHA-256 b4f66ff2e950bfcfb7a8e3cf2d047987dfb5d2bf2f4ecb7c4b59ccb921b4afee.
2. The tests need separate partially covered gap-only and fully covered overlap-only cases, retaining the existing equal-gap/equal-overlap cancellation case.

All four Luna correction cycles have now received independent reviews: correction 1 (review 2), correction 2 (review 3), correction 3 (review 5), and correction 4 (review 12). The single Sol correction is therefore eligible under the carried-forward workflow authorization.

Sol correction 1 may edit only pipeline/tests/test_teignmouth_float32_candidate.py and pipeline/tests/fixtures/teignmouth_overlay_face_19669.json. Bind and use the original outsideGeometry WKT from the saved clip reconstruction, while keeping expectedOutsideClip separately. Assert recomputed production-order fragment areas are positive and individually <=1e-12 m², aggregate coverage reproduces the saved case, and retained extrema remain present. Compare production and alternative association using the same original operands without requiring bit-identical geometry. Add independent gap-only and overlap-only tests plus preserve the existing cancellation test. Do not change the implementation module unless a test uncovers a behavior defect; in that event stop and report it for coordinator review. No changes to the historical helper, source, origin, domain, recipe, collision guards, tolerance or numeric limits.

Authorized checks: rerun only the exact-environment two focused pytest modules and Ruff check/format for the test module. No diagnostic, broader suite, candidate build, browser check, serving, or publication. A different Sol session must independently review the Sol correction before any build-3 proposal is considered. If this single correction does not pass review, stop with candidate NO-GO; no further fix attempt is available.

## Counters after reservation

- Diagnostics: 2/2 used.
- Luna correction cycles: 4/4 used and independently reviewed.
- Sol corrections: 0/1 used, 1 reserved.
- Candidate implementation builds: 2/6 used; none reserved.
- Independent confirmation builds: 0/1 used; unavailable until all offline gates pass.
- Candidate serving/runtime output: ineligible.
