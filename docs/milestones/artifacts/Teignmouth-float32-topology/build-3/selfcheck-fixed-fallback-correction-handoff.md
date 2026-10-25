# Fixed exception fallback correction handoff

Date: 2026-10-25. Implemented the narrow S-only correction authorized by disposition 100. Review finding: `fa2e03204a91ce6637fef40279eb788e70222cbedf9938b5154945e751fdb23c`. Pre-edit S SHA-256: `376187f474f4e91739d732ba064ec1db39be5863cfd5ce746250d0863c35a997`.

In `_exception_message_with_notes`, the `except BaseException` branch after `str(exc)` fails now directly returns the fixed literal `exception message unavailable`. It performs no type lookup, note extraction, JSON serialization, allocation, or further formatting on that branch. When `str(exc)` succeeds, its exact string remains the prefix; bounded note extraction and serialization are unchanged. The two existing callsites, schema, launch, cleanup, console query, and all other source bytes are unchanged.

Static review confirmed the single-line change at the fallback branch. The only authorized checks, run from `pipeline/`, passed:

- `.venv/Scripts/python.exe -m ruff check scripts/run_teignmouth_float32_build3.py` — exit 0, `All checks passed!`
- `.venv/Scripts/python.exe -m ruff format --check scripts/run_teignmouth_float32_build3.py` — exit 0, `1 file already formatted`

No tests, imports, scripts, process probes, wrapper/self-check, retry root, evidence writes, runtime, or downstream work ran.

Final hashes:
- S: `28c92cc60e38ae23dcf58874eca67b8308b22772eee03b36d69471624fcdb089`
- W unchanged: `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b`
- H unchanged: `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501`
- P unchanged: `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`

The prior fallback handoff and all consumed evidence remain untouched. Candidate remains NO-GO/unservable. Stop for independent Sol review; no self-check is authorized.
