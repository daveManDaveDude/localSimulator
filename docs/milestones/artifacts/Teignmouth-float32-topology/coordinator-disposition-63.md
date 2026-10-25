# Coordinator disposition 63 — self-check stopped before launcher creation

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Disposition 62 and the user's “Continue” instruction authorized one bounded post-review-10 correction, independent review, and exactly one 10-second wrapper self-check if review passed.

## Review gate and one-shot result

Sol review 11 passed static acceptance of the W-only caller-owner correction. It confirmed both proposed and persisted Caller records require the literal schema and current wrapper PID, QPC start and selected mode; handoff checks and protected hashes remained intact. Review report: `docs/milestones/artifacts/Teignmouth-float32-topology/build-3/independent-supervisor-review-11.md`, SHA-256 `581c9177f37a5150cbfd749ff6b33b55a5cd74e92dfbb3b583440249c989d613`.

The coordinator then invoked exactly once:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File pipeline/scripts/invoke_teignmouth_float32_build3.ps1 -Mode self-check
```

Actual wrapper exit code: **2**. The resulting `caller-invocation.json` reports a `System.Management.Automation.MethodException` before native launcher creation: PowerShell could not convert `CreateFile` argument `access`, value `-2147483648`, to `System.UInt32`. `launcherCreated`, `launcherAssigned`, `launcherResumed`, `nativeProcessLaunched` and `candidateBuildExecuted` are false; the prepared handoff exists. No Python supervisor, candidate build, or numerical work ran. The one-shot authorization is consumed; do not retry or continue to collection/build under disposition 62.

## Preserved result evidence

- W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`: SHA-256 `c8fcd7c3d4ae8b1535f930533c838bd7e1818624c83798961b388f90660ccb74`.
- `.codex/build3-supervisor-selfcheck-retry-1/caller-invocation.json`: SHA-256 `f992b356191d202a5e2357cffb1d64d90b4dd7f8ac54cd0b76ab2e0d7540dcf3`.
- `.codex/build3-supervisor-selfcheck-retry-1/self-check-handoff.json`: SHA-256 `b73738fc81644b942ea4f84890146e1bdfc73d925005552cb34db1af05aadc79`.
- Original failed caller evidence remains unchanged at `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e` and `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75`.

No second wrapper call, runtime/preflight, identity collection, manifest preparation, GIS/numerical operation, candidate build, serving or browser action occurred. The retry root now exists with only the two listed JSON evidence files; preserve it byte-for-byte.

## Disposition

Stop and await new user direction before any correction or operational attempt. The post-review-10 correction and its single self-check are consumed. Historical counters remain unchanged; candidate remains **NO-GO and unservable** and build 3 remains **unreserved**. The self-check failure is an interop argument-type issue to diagnose; do not infer broader memory, GIS, or topology changes from it.
