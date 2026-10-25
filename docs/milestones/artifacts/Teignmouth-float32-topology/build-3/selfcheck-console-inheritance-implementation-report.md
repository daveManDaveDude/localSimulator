# Self-check console inheritance implementation handoff

Date: 2026-10-25. Scope was coordinator disposition 92 and the accepted plan `selfcheck-console-inheritance-plan.md` (SHA-256 `d8400f4fa3c1b5c1e294cffbac6586eaea9830e20ea2dc9b10cdea0e3d2d519`). Independent plan PASS: `360b568618b24f554d4fa44e4d455d48641c71b3fccf600b804a3950a8d15155`.

## Changes

Only `pipeline/scripts/run_teignmouth_float32_build3.py` was changed. Pre-edit S baseline SHA-256: `64bf2c4abf822ad55252789315d71731d2660d66bb5b6bc7d60f810f2de492c7`. Added lazy, bounded `_require_current_console`: it binds `GetConsoleProcessList` locally; checks the authenticated process ID; queries using a 32-entry initial buffer with no more than four calls or 4096 DWORDs; rejects zero, duplicate, missing-current, malformed, incomplete, unavailable, and late results. It creates no handles and does not inspect or admit peer PIDs.

`_launch_suspended` now accepts keyword-only `inherit_current_console=False`, rejects non-bools, and preserves its default `CREATE_SUSPENDED | CREATE_NO_WINDOW` behavior. The option is enabled only at the self-check normal-helper and tree-root-helper calls. Each checks console attachment immediately before creation, with `CREATE_SUSPENDED` retained. Existing authentication callback, Job assignment-before-resume, process/thread ownership, deadline and cleanup paths remain in place. The stdio handles are each given one close attempt in a `finally`; a close exception cannot mask the launch error or skip later close attempts. `CreateProcessW` failure error is captured immediately before cleanup.

Static source review confirmed the two opted-in call sites and three unchanged callers: standalone preflight, build preflight, and build runner omit the option. Their default creation flags remain unchanged. No runtime behavior or console-host ownership claim is asserted.

## Verification

Commands run from `pipeline/`:

- `.venv/Scripts/python.exe -m ruff check scripts/run_teignmouth_float32_build3.py` — exit 0, `All checks passed!`
- `.venv/Scripts/python.exe -m ruff format --check scripts/run_teignmouth_float32_build3.py` — exit 0, `1 file already formatted`

Static source/diff review was performed by reading the changed function and all five call sites. No tests, imports, Python script execution, process lookup/probes, wrapper/self-check, preflight/runtime, evidence-root writes, or downstream work were performed.

## Final hashes

- S `pipeline/scripts/run_teignmouth_float32_build3.py`: `107e60ec49a929e83511e832db4858884ac4c60327110d4fb7a085fd731bfd0d`
- W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`, unchanged: `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b`
- H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py`, unchanged: `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501`
- P `pipeline/scripts/teignmouth_build3_runtime_preflight.py`, unchanged: `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`

The retry-4 path is the expected consumed root from the authorized call under disposition 88, with immutable evidence recorded by disposition 89. This task did not create, inspect, modify, or use that root or its contents. Existing retry evidence remains preserved.

The earlier outer exit 1 versus internal exit 2 discrepancy remains unresolved. The unsaved historical `957157…` hash remains untraceable. Candidate remains NO-GO/unservable; no self-check is authorized by this implementation handoff. Stop for independent Sol review.

