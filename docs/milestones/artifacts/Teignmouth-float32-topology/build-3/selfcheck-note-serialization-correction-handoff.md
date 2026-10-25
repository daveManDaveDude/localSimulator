# Self-check secondary-note serialization correction handoff

Date: 2026-10-25. Implemented the bounded S-only correction authorized by coordinator disposition 96. Independent finding report SHA-256: `1cd46eb6654ca8f9c070bdc1fab347910d7d7767043432a8dcf36ed89bb4dd24`. The exact pre-edit S baseline was `f50cbb07a0d745eb87d4d4c8e357e0168801507aae2de28f915e3d7ae30e4a55`.

## Change and static review

Only `pipeline/scripts/run_teignmouth_float32_build3.py` changed. Added `_exception_message_with_notes`, used at the normal-helper failure checkpoint's existing `primaryError.message` and the outer self-check's existing `error.message`. It preserves `str(exc)` verbatim as the prefix and, when available, appends a JSON-serialized list of at most four string notes, each capped at 512 characters. Extraction/serialization is best-effort and falls back to the primary message; if even `str(exc)` raises, it emits a type-tagged message-unavailable fallback. No schema fields or versions were added, and type, phase, propagation and cleanup control flow were not changed.

Static source review traced both paths: a primary current-console/CreateProcess exception receives stdio-close notes in `_launch_suspended`, then those notes are serialized at the normal checkpoint and outer error record. For successful creation with unconfirmed stdio release, the existing RuntimeError reaches the suspended-process cleanup path; its unconfirmed-release and cleanup notes are serialized by the outer error record. The primary message remains the start of the stored message. This is source review only; no failures were induced.

## Authorized checks

Commands run from `pipeline/`:

- `.venv/Scripts/python.exe -m ruff check scripts/run_teignmouth_float32_build3.py` — exit 0, `All checks passed!`; Ruff printed a cache warning (`Access is denied`, OS error 5) but reported no lint findings.
- `.venv/Scripts/python.exe -m ruff format --check scripts/run_teignmouth_float32_build3.py` — exit 0, `1 file already formatted`.

No tests, imports, script execution, live process inspection, wrapper/self-check, runtime/preflight, evidence-root writes or downstream work ran.

## Final hashes

- S `pipeline/scripts/run_teignmouth_float32_build3.py`: `a0ebfebbde4eabdba0dc3946d0222070b3ee8b28b8f8aa3a2d69234c01538e1e`.
- W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`, unchanged: `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b`.
- H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py`, unchanged: `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501`.
- P `pipeline/scripts/teignmouth_build3_runtime_preflight.py`, unchanged: `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`.

The prior stdio-release handoff remains unchanged with its documented S hash typo; current S was independently recalculated from file bytes above. No retry root or prior evidence was touched. Candidate remains NO-GO/unservable. Stop for fresh independent Sol review; no self-check is authorized.

