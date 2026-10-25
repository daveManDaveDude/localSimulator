# Independent Sol review 13 — sole Sol correction 1

Date: 2026-10-24. Reviewer: `/root/sol_review_face_diag`, distinct from implementer `/root/sol_fixture_correction`.

## Disposition

**PASS: both review-12 blockers are closed.** The test/fixture correction stays within coordinator disposition 21. Together with review 12's implementation assessment, this supports coordinator acceptance of the corrected cycle-4 result and preparation of a **separate, reviewed build-3 proposal**. Build 3 remains unreserved; this review does not authorize execution. Candidate remains **NO-GO** and unservable.

## Original operands and retained extrema

The updated fixture's `clipWkt` is textually identical to saved `diagnostic-2/run-1/clip-reconstruction.json`'s `outsideGeometry.wkt`. That provenance file independently hashes to `b4f66ff2e950bfcfb7a8e3cf2d047987dfb5d2bf2f4ecb7c4b59ccb921b4afee`, matching the fixture and disposition 21. All five fixture provenance hashes match their saved evidence files.

`expectedOutsideClip` remains a separate fixture field with the original three coordinate values and area 1.1028883815799223e-12 m². Its WKT starts at a different vertex than the saved face-reconstruction WKT, a cyclic ring rotation, so those two strings are not identical. It is not used as the production clip operand. The original outside geometry itself is copied exactly; no coordinate substitution or reconstruction is used for that operand.

In `pipeline/tests/test_teignmouth_float32_candidate.py:388–399`, the test now computes `face.intersection(source).intersection(original_outside)` for each actual saved source triangle, derives the resulting areas, requires both to be strictly positive and <=1e-12 m², and requires their `math.fsum` to exceed 1e-12 while agreeing with the expected clip within the existing tolerance. The old canned-area assertion is replaced. Lines 412–438 require the helper's aggregate to match the computed aggregate, retain two fragments/all seven polygon vertices, retain tiny nonzero extrema and locate extremum witnesses on the actual computed fragment rings.

The association test at lines 447–483 uses the same original face, source triangles and outside geometry for production and alternative ordering. It compares union-area and symmetric-difference areas against the unchanged area tolerance; it does not assume bitwise geometry or coordinate-sequence equality. Nonzero extrema and the production association remain asserted. This closes the original-operand regression blocker.

## Independent coverage protections

The new partial-gap-only case at lines 573–594 supplies one source triangle covering half the assessed face with `partition_verified=True`. It checks positive coverage, explicit gap geometry/area, zero excess and zero pairwise overlap.

The new full-coverage overlap-only case at lines 597–624 supplies the full face plus a half-face source triangle, again with `partition_verified=True`. It checks empty gap geometry, zero excess, 1 m² of true pairwise source overlap, exact source IDs and overlap geometry. These independently exercise genuine gap and actual overlap scenarios rather than depending solely on the cancellation case.

The equal-gap/equal-overlap case remains at lines 627–644, requiring both 1 m² gap and 1 m² source overlap and their source witnesses despite aggregate area cancellation. The no-positive-coverage case also remains. These close the second review-12 blocker.

## Isolation, hashes and check evidence

Independently verified current changed-file hashes:

- `pipeline/tests/test_teignmouth_float32_candidate.py`: `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8`.
- `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json`: `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea`.

Candidate implementation remains exactly the cycle-4 reviewed bytes: `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b`. Historical shared helper remains `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880`. Rehashing all 291 diagnostic manifest bindings again shows only the previously authorized candidate implementation and focused test module differ from the pre-correction freeze; the other 289 remain unchanged. The fixture is additive. This confirms no source/config/domain/origin/recipe/limit/shared-helper/product change among the protected bindings. All three local call sites, the implementation's coverage/overlap logic, exterior/interior extrema, explicit empty handling and nonempty exact source-plane-zero comparisons therefore remain as assessed in review 12.

Sol-correction summary SHA-256 independently matches the handback: `68f8207fbe1e86bb1a34dc15f5f7b82d2fd97e11a6ea558d6092ffb8ce89ada9`. It reports the two focused exact-venv pytest modules **29 passed in 2.64 s**, Ruff check success and one test file already formatted, from `pipeline/`. Preliminary formatting and overly exact coordinate-sequence assertion failures are disclosed. These results are implementer-reported evidence inspected in the summary/handback, not independently rerun tests. No full candidate build, diagnostic rerun or browser check is reported. Candidate output remains absent.

The live ledger records diagnostics 2/2, Luna cycles 4/4 and Sol corrections 1/1 consumed, with none reserved. Implementation builds remain 2/6 used and unreserved; independent confirmation is 0/1 and not eligible until all offline gates pass. No attempt is added or reset by this review. The remaining exact source-plane-zero risk and full-build performance are unresolved candidate questions, not waived conditions.

## Boundary

Read-only source/test/fixture/evidence inspection, JSON comparisons and independent file hashing only. No imports, compilation, numerical reconstruction, tests, build, diagnostic or browser action occurred. No implementation, ledger or checkpoint was edited. Only this explicitly requested review document was written. PASS closes the focused validation findings; it does not accept the failed candidate or authorize serving.
