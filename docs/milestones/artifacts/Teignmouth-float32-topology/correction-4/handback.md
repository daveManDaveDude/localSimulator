# Luna correction 4 handback

Date: 2026-10-24

Disposition: implementation and focused checks complete; independent Sol review pending. Candidate remains NO-GO. No candidate build or browser check was run.

Prototype-local overlay accounting now retains strictly positive finite fragments (including sub-tolerance fragments), uses fsum for aggregate areas, checks geometric gap/excess and pairwise source overlap against the existing tolerance, measures extrema on exterior and interior ring vertices, and reports wholly empty assessed regions explicitly. All three prototype overlay assessments use the local helper. Historical shared helper hash remains identical to the frozen diagnostic manifest. Production association, source-plane extrema, exact-zero requirements and every numeric limit remain unchanged.

## Focused checks

- From pipeline/: .venv/Scripts/python.exe -m pytest tests/test_teignmouth_float32_candidate.py tests/test_road_surface_float32_frame.py — 27 passed in 2.60 s.
- From pipeline/: .venv/Scripts/python.exe -m ruff check torquay_pipeline/teignmouth_float32_candidate.py tests/test_teignmouth_float32_candidate.py — All checks passed.
- From pipeline/: .venv/Scripts/python.exe -m ruff format --check torquay_pipeline/teignmouth_float32_candidate.py tests/test_teignmouth_float32_candidate.py — 2 files already formatted.
- One earlier pytest collection attempt from repository root failed with ModuleNotFoundError for torquay_pipeline. Its exact command was not retained. The three checks above were rerun successfully from pipeline/.

## File hashes

- pipeline/torquay_pipeline/teignmouth_float32_candidate.py: a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b
- pipeline/tests/test_teignmouth_float32_candidate.py: 26e293446b2dfcbbf35fba5a1227d1a9d53db6366a1336997003cfb3f2f51352
- pipeline/tests/fixtures/teignmouth_overlay_face_19669.json: b95b6c2e68ffd5b280798a124e2d6fe1b40e6b4a70ffba3ee3994234096d80f7
- Preserved pipeline/torquay_pipeline/road_surface_topology.py: 88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880

Machine-readable record: implementation-summary.json (SHA-256 e45f1a859fc6f309fd458e5eeb5a12870a63332e381610b1db14d113b5f9534a).

No full candidate build, browser/product integration, serving, or broader test suite was run. The exact source-plane-zero gate remains in place and may expose a separate blocker.
