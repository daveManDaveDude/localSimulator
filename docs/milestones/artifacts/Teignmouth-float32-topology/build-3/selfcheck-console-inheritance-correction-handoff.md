# Self-check stdio release correction handoff

Date: 2026-10-25. Implemented the narrow S-only correction authorized by disposition 94 for review finding `d46ec3ca18f2465ec5093109b4eb39b4e1f1353c8bfc6bf870cec6226923b34f`. Pre-edit S SHA-256 was `107e60ec49a929e83511e832db4858884ac4c60327110d4fb7a085fd731bfd0d`.

## Change and source review

Only `pipeline/scripts/run_teignmouth_float32_build3.py` changed. `_launch_suspended` now records each of the three stdio handle close outcomes in fixed per-handle slots: a truthy `CloseHandle` return is confirmed; a false return is unconfirmed and its `ctypes.get_last_error()` is captured immediately; a raised close exception is unconfirmed. The loop attempts each owned stdout/stderr/stdin handle once and does not retry or double-close.

When a current-console query or `CreateProcessW` failure is already primary, close failures are attached as best-effort secondary notes and the original exception propagates. On successful process creation with any unconfirmed stdio release, launch fails before Job assignment, helper authorization or resume. The failure enters the existing suspended-process cleanup handler while the child is still unassigned; it uses the established terminate, bounded wait/exit observation, process-handle cleanup and thread-handle `finally` cleanup. When all three releases are confirmed, the existing Job assignment-before-resume path proceeds unchanged.

Static source/diff review covered the changed close block and its surrounding creation/cleanup flow. No other S behavior or file was changed. Retry-4 and prior evidence roots were not accessed or modified. No runtime test or process inspection was performed.

## Static checks

Commands run from `pipeline/`:

- `.venv/Scripts/python.exe -m ruff check scripts/run_teignmouth_float32_build3.py` — exit 0, `All checks passed!`
- `.venv/Scripts/python.exe -m ruff format --check scripts/run_teignmouth_float32_build3.py` — exit 0, `1 file already formatted`

The first check reported Ruff `B007` for an unused loop control variable. The first format check reported the loop layout would be reformatted. The variable was removed and the loop was manually adjusted; both final authorized checks pass. No formatter write was run.

## Final hashes

- S `pipeline/scripts/run_teignmouth_float32_build3.py`: `f50cbb07a0d745eb87d4d4c8e357e0168801507aa2de28f915e3d7ae30e4a55`
- W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`, unchanged: `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b`
- H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py`, unchanged: `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501`
- P `pipeline/scripts/teignmouth_build3_runtime_preflight.py`, unchanged: `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`

No tests, imports, script execution, process lookup/probes, wrapper/self-check, preflight/runtime, evidence-root writes, or downstream work ran. Candidate remains NO-GO/unservable. Stop for fresh independent Sol review; this handoff does not authorize another self-check.
