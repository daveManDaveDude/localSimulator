# Coordinator disposition 88 — one retry-4 self-check

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User authorization for as many attempts as needed, dispositions 64, 85–87.

## Independent PASS and exact revision

Independent Sol review 20 is **PASS** for the exact four retry-4 path substitutions. Report SHA-256: `960d85541339265c7b952f3d9e8bddf905ca755e707839a992120da56a551630`. Review verified W/S/H counts and inverse hashes, all producer/consumer paths, root/alias/ancestor safety, protected bytes and all 26 prior evidence files. It preserves review-19's accepted diagnostics and explicitly grants no run.

Coordinator immediately before this gate rehashed W/S/H/P to the review-20 values, confirmed `.codex/build3-supervisor-selfcheck-retry-4` and every case-insensitive alias were absent, rechecked canonical non-reparse directory ancestors, and resolved `pwsh`. The wrapper's own fixed-path/one-use checks remain required; any refusal or non-PASS consumes this attempt and must be preserved.

## Exactly one authorized invocation

Run once through W from the workspace root:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File pipeline/scripts/invoke_teignmouth_float32_build3.ps1 -Mode self-check
```

Use only retry-4 and the unchanged inherited **10-second total QPC deadline**. Preserve the complete outer command result and all resulting evidence byte-for-byte, including any difference between outer and recorded internal exit codes. Do not replay, clean, adopt or reuse this slot. After capturing the single result, stop for diagnosis and a new bounded plan/review if required.

This authorizes only one nonnumerical supervisor self-check. It does not authorize preflight/runtime identity collection, manifests, GIS/numerical/candidate build or reservation, serving/publication, browser action or any later phase. Retry-1/2/3 remain consumed, immutable and non-PASS. Candidate remains **NO-GO and unservable**; build 3 unreserved. No commit, push or merge.
