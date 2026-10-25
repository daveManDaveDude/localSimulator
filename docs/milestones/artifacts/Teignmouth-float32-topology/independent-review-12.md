# Independent Sol review 12 — Luna correction cycle 4

Date: 2026-10-24. Reviewer: `/root/sol_review_face_diag`, independent non-implementing Sol session.

## Disposition

**FAIL for correction-4 acceptance pending focused regression corrections. No build-3 reservation is recommended yet. Candidate remains NO-GO.** The inspected implementation addresses the diagnosed accounting defect without relaxing the fixed limits. Two concrete validation gaps remain below. A separately prepared/reviewed build-3 proposal becomes justified only after those gaps are corrected under coordinator authorization and independent review. This review authorizes no correction, test, build or diagnostic execution.

Reviewed against `sol-plan-correction-4.md`, diagnostic-2 saved evidence, coordinator dispositions 19–20, the frozen diagnostic manifest and correction-4 handback. Luna cycle 4 is consumed; this review does not grant another Luna attempt. Any eligible Sol correction must be explicitly reserved and reviewed by a different Sol session.

## Concrete blockers

1. **The saved-case fixture substitutes an already clipped region for the original outside geometry.** `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json:29–30` uses `faceReconstruction.expectedOutsideClip.wkt`, which is already `face.intersection(outside_geometry)`. Tests pass that as `clip_geometry` at `pipeline/tests/test_teignmouth_float32_candidate.py:398` and use it for both ordering comparisons at lines 430–434. The tested production expression is consequently `(face intersection source) intersection (face intersection outside)`, rather than diagnostic 2's `(face intersection source) intersection outside`. Diagnostic 2 specifically demonstrates that algebraic equivalence does not imply identical floating geometry. This fixture does not reproduce the exact failing operands or the saved clipping-order comparison. The original `outsideGeometry` is available in `diagnostic-2/run-1/clip-reconstruction.json`; bind its provenance and store its exact saved geometry as the regression input. Keep expected face clip separately. Assertions at test lines 401–404 currently inspect canned `expectedFragmentAreaM2` values rather than recomputing the actual fragment areas. Assert the computed production fragments are positive and individually <=1e-12, their expected aggregate failure pattern and retained extrema, without requiring alternative associations to be bit-identical.

2. **The genuine gap and overlap regressions do not isolate the protections they claim to verify.** The no-coverage case at test lines 537–551 exercises only the early no-positive-fragments error. The combined equal-gap/overlap case at lines 554–571 fails on both a gap and overlap, so it would still pass if either independent rejection condition were removed. Add a partially covered face with positive fragments and a genuine gap but no overlap, and a fully covered face with a genuine overlap but no gap. Require typed failures with the respective geometric witnesses/source IDs under `partition_verified=True`; retain the existing cancellation case. These are the focused missing-coverage and actual-overlap protections requested by the accepted plan, rather than new product scope.

## Implementation assessment

In `pipeline/torquay_pipeline/teignmouth_float32_candidate.py`, lines 954–977 retain every strictly positive finite polygon component and aggregate with `math.fsum`; the original per-fragment <=1e-12 discard is absent. Lines 986–1001 compute union/gap/excess and raw subtraction residuals. Lines 1003–1040 inspect actual source-pair intersection geometry and compare coverage residual, gap, excess and pairwise overlap area against the unchanged `max(area_tolerance_m2, expected_area*1e-10)`. This occurs irrespective of `partition_verified`, so equal gap/overlap cancellation is rejected by the implementation. A small positive sum-minus-union subtraction alone is not mislabeled as source overlap. Source IDs and geometry witnesses are present in typed coverage failures.

Lines 1072–1112 evaluate exterior and interior ring vertices for every retained positive polygon and preserve signed/absolute extrema and finite witnesses. Nonzero deltas are not rounded to zero. The hole-ring test explicitly expects six tested vertices. Finite geometry and plane checks remain present. Empty assessed faces are handled separately at lines 943–952; wholly empty assessment returns explicit null extrema at lines 1114–1145. The two source-plane callers record vacuity for a genuinely empty region, while nonempty assessments retain exact `maximumAbsoluteChangeFromSourceM == 0.0` at lines 1318–1319 and 1328–1329. Whole-surface safety explicitly rejects an empty/no-extrema assessment at lines 1364–1367. All three prototype overlay calls use the local helper at lines 1315, 1322 and 1349; historical consumers remain isolated.

The saved diagnostic's nonzero plane differences remain a likely subsequent exact-zero gate blocker; repairing coverage accounting is not evidence that build 3 would pass. Per-face union and pairwise work also adds cost; no full-build performance claim is established by focused tests. These observations do not justify relaxing a limit or running a diagnostic again.

## Hashes, preservation and test evidence

Independently verified changed-file hashes:

- `pipeline/torquay_pipeline/teignmouth_float32_candidate.py`: `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b`.
- `pipeline/tests/test_teignmouth_float32_candidate.py`: `26e293446b2dfcbbf35fba5a1227d1a9d53db6366a1336997003cfb3f2f51352`.
- `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json`: `b95b6c2e68ffd5b280798a124e2d6fe1b40e6b4a70ffba3ee3994234096d80f7`.

All four fixture provenance references match the saved evidence hashes. The problem is the selected geometry field, not fabricated provenance. Historical `road_surface_topology.py` remains `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880`, identical to the frozen diagnostic manifest. Rehashing all 291 diagnostic bindings found only the two authorized modified implementation/test files changed; the other 289 remain identical. The new fixture is additive. This verifies preservation of fixed source/config/origin/domain/recipe/guards/limits and historical/product bytes represented in that manifest; it is not a claim about every unbound repository file.

Implementation-summary SHA-256 matches disposition 20: `e45f1a859fc6f309fd458e5eeb5a12870a63332e381610b1db14d113b5f9534a`. The handback reports exact-venv focused pytest **27 passed in 2.60 s**, Ruff success and two files already formatted, all from `pipeline/`. It also discloses an earlier root-directory collection failure whose exact command was not captured. These are reported implementer results inspected in the summary/handback; raw check logs are not present there, and this reviewer did not rerun the checks. No candidate build, browser check or serving success is claimed.

## Boundary

Read-only inspection, JSON comparisons and file hashing only. No code edits, imports, compilation, tests, diagnostic, build, numerical reconstruction or browser activity occurred. No ledger/checkpoint was changed. Only this explicitly requested review document was written. Preserve the current implementation/evidence as reviewed and seek coordinator direction for the bounded validation correction; candidate remains unservable.
