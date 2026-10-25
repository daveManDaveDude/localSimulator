# Pre-build evidence plan — Float32 topology representation 1

Status: initial Luna implementation submitted for coordinator review. No candidate build has been reserved or run.

## Frozen scope

The adjacent `input-manifest.json` binds the diagnostic 1 evidence/source set (excluding only the mutable active attempt ledger), the exact new code/config/tests, current runtime dependencies and the exact Python interpreter. The current attempt ledger hash is recorded separately and remains coordinator-mutable. All 178 non-ledger diagnostic bindings match their diagnostic-1 hashes. The candidate output path `data/generated/teignmouth-float32-topology/` was absent at preparation.

## Checks already run

- Exact venv: `pipeline/.venv/Scripts/python.exe -m pytest tests/test_road_surface_float32_frame.py tests/test_teignmouth_float32_candidate.py -q` — 8 passed.
- Exact venv Ruff check and `ruff format --check` on the new implementation, runner and two test files — passed.
- Exact venv `python -m py_compile` on the frame module, candidate module and runner — passed.
- Exact venv `python scripts/build_teignmouth_float32_candidate.py --import-smoke` — `PASS_IMPORT_ONLY`; no GIS load or candidate build.

## Not run / gates remaining

No source loading, numerical geometry, topology candidate build, overlays, gradients, full-width sections, all-road reclip/drape, complete building-contact metrics, shared display sampler/walk clearance, deterministic independent rebuild, browser or screenshot was run. Road/building/walk/contact and independent confirmation gates remain false/unavailable; candidate is not servable. No build ordinal is reserved.

## Next authorized step

Coordinator reviews this pre-build binding and implementation. Only after explicit fresh reservation of build ordinal 1 may one full candidate build be invoked, once, with a maximum 180-second bound. Before invocation, confirm every frozen file hash still matches, ledger records the ordinal reservation, and output remains absent. Retain all failed buffers/reports in issue evidence; never place them in runtime-serving paths or modify source/product/default/preview assets.
