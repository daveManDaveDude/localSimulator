# Coordinator disposition 23 — accept focused corrections; authorize build-3 proposal only

Date: 2026-10-24

**Decision: accept correction 4 after independent review 12 and accept the sole Sol fixture/test correction after independent review 13. Authorize Sol to prepare a separate bounded build-3 proposal and complete input manifest only. Do not reserve or invoke build 3. Candidate remains NO-GO and unservable.**

Review 13 is PASS (SHA-256 b69ad8fcbc0a09bb62ffcde101a65e227a3d4c14d61909a15b96e89790f118f5); it closes both review-12 blockers. It confirms the regression uses the original hash-bound outsideGeometry, recomputes the saved positive subthreshold fragment areas, isolates gap-only and overlap-only rejection, retains the cancellation case, and preserves all implementation/source/domain/helper constraints. The implementation summary for Sol correction 1 is SHA-256 68f8207fbe1e86bb1a34dc15f5f7b82d2fd97e11a6ea558d6092ffb8ce89ada9.

The next plan may propose one candidate build, ordinal 3, with a 180-second maximum, using the corrected prototype-local overlay helper. It must bind the corrected implementation, regression evidence, prior failed-build evidence, source/config/domain/origin/recipe/limits, deterministic runtime identity and output isolation. Preserve build 1, build 2 and all diagnostic evidence. Candidate output remains absent until an explicitly reserved run. No arbitrary memory cap, timing relaxation, geometry/tolerance adjustment, or new diagnostic is authorized. Record actual exits, elapsed time, memory measurement scope and before/after preservation; stop at the existing deadline.

The known saved face has nonzero source-plane differences of roughly 1.5e-7 to 2.8e-7 m. Build 3 may expose the unchanged exact-zero plane gate as a failure. This is a required result if observed; do not round it away, accept it as zero, weaken the gate, or treat a failure as candidate acceptance.

After the Sol proposal is saved, an independent Sol reviewer and coordinator must review its exact hashes, complete protected-input closure, fresh output-path absence, runtime identity, gates, supervisor and 180-second bound. Only then may a later coordinator disposition reserve build 3. No code edit, test, build, browser validation, serving or publication is authorized by this disposition.

## Counters

- Diagnostics: 2/2 used.
- Luna correction cycles: 4/4 used and independently reviewed.
- Sol corrections: 1/1 used and independently reviewed.
- Candidate implementation builds: 2/6 used; build 3 is not reserved.
- Independent confirmation builds: 0/1 used; unavailable until every offline gate passes.
- Candidate serving/runtime output: ineligible.
