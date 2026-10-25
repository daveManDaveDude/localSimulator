# Sol correction 1 handback

Date: 2026-10-24. The sole Sol correction is complete; a different Sol review is pending. Candidate remains NO-GO. No candidate build or browser check was run.

The saved-face fixture now uses the hash-bound original outsideGeometry operand from diagnostic 2 and retains the expected face-clipped region separately. Regression tests recompute production-order fragment areas, confirm both are positive and individually at or below 1e-12 m² while their sum covers the expected clip within unchanged tolerance, and verify retained extrema. Production and alternative clip associations use the same original operand. Separate partial-gap-only and full-coverage-overlap-only cases now accompany the existing equal-gap/equal-overlap cancellation test. No implementation module changed.

Commands run from C:\vibe\localSimulator\pipeline:
- .venv/Scripts/python.exe -m pytest tests/test_teignmouth_float32_candidate.py tests/test_road_surface_float32_frame.py — 29 passed in 2.64s.
- .venv/Scripts/python.exe -m ruff check tests/test_teignmouth_float32_candidate.py — All checks passed.
- .venv/Scripts/python.exe -m ruff format --check tests/test_teignmouth_float32_candidate.py — 1 file already formatted.

A preliminary formatting check requested a single-line call and was corrected. A preliminary pytest assertion used exact coordinate-sequence equality; it was replaced with the existing area tolerance. Final authorized checks passed.

SHA-256:
- test module: 34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8
- fixture: 4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea
- unchanged candidate module: a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b
- unchanged shared helper: 88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880
- bound clip reconstruction: b4f66ff2e950bfcfb7a8e3cf2d047987dfb5d2bf2f4ecb7c4b59ccb921b4afee

Machine-readable summary SHA-256: 68f8207fbe1e86bb1a34dc15f5f7b82d2fd97e11a6ea558d6092ffb8ce89ada9. No diagnostic, candidate build, browser, serving, broader suite, commit, push or merge was run.
