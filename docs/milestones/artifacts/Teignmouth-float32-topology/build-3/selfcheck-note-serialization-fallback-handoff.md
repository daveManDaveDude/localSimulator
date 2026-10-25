# Secondary-note serialization fallback handoff

Date: 2026-10-25. Implemented the one-line S-only fallback correction authorized by disposition 98. Finding: `bafe857fb8554431c6a02d418c3df1435dbc75b1bd3977bbe8cbd68ccc40c7b5`. Pre-edit S SHA-256: `a0ebfebbde4eabdba0dc3946d0222070b3ee8b28b8f8aa3a2d69234c01538e1e`.

Changed only the `str(exc)` failure branch in `_exception_message_with_notes`: it now returns the fixed literal `exception message unavailable`, avoiding further exception-type formatting in that failure path. When `str(exc)` succeeds, its exact text remains the stored message prefix. Existing bounded note serialization and both message-field call sites are unchanged. No schema, cleanup, query, launch, path, or other source behavior changed.

Static review inspected the helper and confirmed the change is a single fallback literal. Ruff gates, run from `pipeline/`:

- `.venv/Scripts/python.exe -m ruff check scripts/run_teignmouth_float32_build3.py` — exit 0, `All checks passed!`
- `.venv/Scripts/python.exe -m ruff format --check scripts/run_teignmouth_float32_build3.py` — exit 0, `1 file already formatted`

No tests, imports, scripts, process inspection, wrapper/self-check, retry root, evidence writes, runtime or downstream work ran.

Final hashes:
- S: `376187f474f4e91739d732ba064ec1db39be5863cfd5ce746250d0863c35a997`
- W unchanged: `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b`
- H unchanged: `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501`
- P unchanged: `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`

The prior handoff's documented S-hash typo remains unchanged. Candidate remains NO-GO/unservable. Stop for independent Sol review; no self-check is authorized.
