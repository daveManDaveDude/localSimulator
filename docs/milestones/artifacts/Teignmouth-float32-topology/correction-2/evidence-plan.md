# Correction 2 evidence plan — Float32 topology representation 1

Status: Luna correction cycle 2 implementation submitted for coordinator review and independent Sol re-review. No candidate build, source load, diagnostic, browser or screenshot was run.

## Frozen evidence

The adjacent manifest binds 193 current inputs, all correction-1/prebuild evidence and reviews, current implementation/tests/config, and the exact venv identity. The active attempt ledger is recorded separately as mutable coordinator metadata. Correction-1 evidence was not modified. The candidate output path was absent when this plan was written.

The manifest records 2 expected changed path(s) from correction 1. The source/config/origin/guard/limits were not changed.

## Finding addressed

Candidate assembly now goes through `_serialize_position_buffers`, which constructs explicit world columns `[X, unrounded Y, Z]` before calling the frame serializer. Decoded stored-local Float32 positions retain that order as `[X,Y,Z]`. Displacement compares decoded stored positions against pre-serialization positions with the same ordering, and separately reports horizontal X/Z and vertical Y errors. The regression uses non-exact X/Z and Float64 Y, and asserts exact stored local X/Z bytes, reconstructed XYZ, and per-axis displacement values.

Correction-1 section sampling, incremental chart/construction/serialized/gate evidence, bounded parent-supervised runner, pre/post hash checks, memory telemetry, and failed-output evidence archival are retained.

## Checks run

- Exact venv focused pytest from `pipeline/`: 13 passed.
- Ruff check and format check on the five new implementation/test files: passed.
- Exact venv `py_compile` on frame, candidate and runner: passed.
- Exact venv build-runner `--import-smoke`: `PASS_IMPORT_ONLY`.

## Gates and next step

No real source load or candidate build was run. Actual candidate topology, source overlays, gradients, sections, roads, building contact, shared walk/contact, independent determinism, browser and screenshot remain unmeasured or false. Candidate is unservable. Build ordinal 1 remains unreserved. Coordinator and independent Sol re-review correction 2 next; no build is authorized by this submission.
