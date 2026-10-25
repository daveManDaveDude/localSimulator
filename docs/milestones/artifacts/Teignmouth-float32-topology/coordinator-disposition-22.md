# Coordinator disposition 22 — consume Sol correction 1 for distinct review only

Date: 2026-10-24

**Decision: the single Sol correction is consumed. Its fixture/test-only changes and authorized focused checks are ready for independent review by a different Sol session. No candidate build is authorized. Candidate remains NO-GO and unservable.**

The correction summary is sol-correction-1/implementation-summary.json, SHA-256 68f8207fbe1e86bb1a34dc15f5f7b82d2fd97e11a6ea558d6092ffb8ce89ada9. It records that the fixture uses the exact hash-bound original outsideGeometry while retaining expectedOutsideClip separately; tests measure the actual production fragment areas; and independent gap-only and overlap-only checks accompany the cancellation regression. The implementation module and historical shared helper are unchanged.

The exact-environment two-module pytest completed with 29 passed. Ruff check and format checks passed. The handback discloses the corrected preliminary formatting and equality-assertion failures. No build, diagnostic, browser or serving action was run.

A different Sol session must review whether the review-12 blockers are closed and verify the changed files and scope. If accepted, the coordinator may consider a separately reviewed and manifested build-3 proposal; this disposition does not reserve one. The exact source-plane-zero requirement and all numeric/data constraints remain unchanged.

## Counters after Sol correction 1

- Diagnostics: 2/2 used.
- Luna correction cycles: 4/4 used and independently reviewed.
- Sol corrections: 1/1 used; none remain.
- Candidate implementation builds: 2/6 used; none reserved.
- Independent confirmation builds: 0/1 used; unavailable until all offline gates pass.
- Candidate serving/runtime output: ineligible.
