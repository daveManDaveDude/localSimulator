# Independent Sol review — correction cycle 1

**Verdict: FIX REQUIRED.** Reviewer: `/root/beamng_corridor_plan` (`gpt-6.1-sol`, medium), who planned but did not implement this issue. Review was read-only; no tests, builds, diagnostics, profiles or browser attempts were spent.

## Findings

1. **[P1] Repository-root CLI cannot import the pipeline package — behavior defect.** `build_teignmouth_corridor_continuation.py` imports `torquay_pipeline` without making `root/pipeline` importable. The ordinal-2 report captures the resulting `ModuleNotFoundError` and traceback. Compilation and `--help` do not exercise the import. Add repository-root import discovery and an import-only smoke test that does not read GIS.
2. **[P2] Missing telemetry-failure regression test — evidence gap.** Code now preserves primary exceptions and separates optional telemetry failure, but the promised synthetic test combining a primary build/config error with memory-telemetry failure is absent. Add it with correction 2.

## Review of prior findings

- The continuation-only strict config parser now validates the submitted config and rejects altered/unexpected values without changing the legacy loader.
- Windows API bindings now use pointer-sized ctypes signatures. Build 2 demonstrates durable primary-error reporting and successful memory measurement.
- Target-section metrics now sample final serialized Float32 triangles rather than the ideal profile. Synthetic controls include an adversarial 10% actual mesh cross-slope, centerline displacement, a flat control, anchor and endpoints.
- Preservation includes earlier corridor artifacts. Sol rehashed **910 listed paths** with zero mismatches; before/after snapshots match. Ignored raw GIS data remains outside the scan as disclosed.
- Candidate serving remains blocked: road/building/walk gates are explicitly false, no runtime candidate exists, and no browser/product/default path was added.

The ledger correctly shows build ordinal 2 and Luna correction cycle 1 used, with zero diagnostics and Sol corrections used. The 18-test/static results are Luna-reported only; I inspected relevant tests but did not rerun them. No geographic candidate gate has been reached or passed.

## Authorized next action

One bounded Luna correction cycle 2 is justified: fix repository-root package discovery, add the import-only and combined primary-error/telemetry-failure regressions, preserve durable failure handling, and update the exact build evidence path/preservation exclusions. After focused checks pass, reserve one fresh build ordinal 3 (≤180 seconds). Do not rerun ordinal 2, run a diagnostic, change thresholds, or start browser work.
