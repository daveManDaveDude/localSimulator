# Correction 1 evidence plan — Float32 topology representation 1

Status: Luna correction cycle 1 implementation submitted for coordinator review and distinct Sol re-review. No candidate build or source-load diagnostic was run.

## Frozen evidence

`input-manifest.json` binds 188 current inputs, the immutable prebuild-1 manifest/evidence plan, Sol review 1, coordinator disposition 2, and the exact venv identity. The active attempt ledger is separated as mutable coordinator metadata. The earlier prebuild-1 manifest and evidence plan were not modified.

The manifest records 3 path(s) with expected correction changes relative to the initial submission. Those are correction-scoped candidate code, runner and focused regression files. Frozen config, frame contract, diagnostic evidence and protected source inputs remain bound. Candidate output was absent when this plan was written.

## Review findings addressed

1. Section stations and 0.25 m full-width offsets use `sample_stored_triangle_surface` over actual stored local Float32 positions reconstructed to world Float64. No inherited global-Float32 section sampler remains. Synthetic tests include the known global-collision pair sampled separately and an ideal flat recipe that passes while a synthetic stored mesh fails at 6% cross-slope.
2. The chart arrays, exact construction Float64/local Float32 buffers, constraints, boundary, serialized XYZ/index/Y buffers and each completed gate are persisted immediately. Failure records retain the primary typed exception and mark later gates unavailable.
3. Full builds are launched only as a supervised multiprocessing child; no CLI worker bypass is exposed. The parent enforces 180 seconds, samples peak Windows working set with declared WinAPI signatures, records elapsed/status, verifies bindings before and after, and archives any failed partial output into that attempt's evidence so the generated output path remains fresh.
4. Outside-influence source reproduction is checked by final candidate-triangle/source-triangle overlay clipped to the outside region. Serialization displacement compares decoded stored XYZ against pre-serialization construction world XZ and unrounded candidate Y.

## Checks run

- `pipeline/.venv/Scripts/ruff.exe check ...` on the five new implementation/test files — passed.
- `pipeline/.venv/Scripts/ruff.exe format --check ...` — passed.
- `pipeline/.venv/Scripts/python.exe -m pytest tests/test_road_surface_float32_frame.py tests/test_teignmouth_float32_candidate.py -q` from `pipeline/` — 12 passed.
- Exact-venv `python -m py_compile` on frame, candidate module and runner — passed.
- Exact-venv `python scripts/build_teignmouth_float32_candidate.py --import-smoke` — `PASS_IMPORT_ONLY`.

## Gates and next step

No real source load, candidate build, browser, or screenshot was run. Road reclip/drape, building contact, shared road/building/walk contact, source overlays on actual candidate data, candidate sections on actual data, and deterministic confirmation remain unmeasured or false; the candidate remains unservable. No threshold/config/source change was made. Build ordinal 1 remains unreserved.

Coordinator and distinct Sol re-review the correction and these checks next. A candidate build remains prohibited unless a later explicit coordinator disposition reserves it; preserve correction-1 and prebuild-1 evidence unchanged.
