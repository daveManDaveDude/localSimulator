# Coordinator disposition 77 — one retry-3 self-check

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User authorization for as many attempts as needed, dispositions 64 and 74–76.

## Independent PASS and exact revision

Independent Sol review 17 is **PASS** for the exact four retry-3 path substitutions. Report SHA-256: `2fe8d73fbd1d814b84cf855e61d1ff6c0bf362849e620ab54379a9b98e368eeb`. Current W/S/H/P hashes are pinned in disposition 76 and match the plan/review. Review 17 verified exact inverse hashes, path agreement, safe ancestors, no retry-3 alias, and unchanged protected sources plus all original/retry evidence. It is static only; the earlier S digest beginning `957157…` remains unsaved/untraceable.

Immediately before this gate, coordinator rehashed W/S/H/P and all four matched review 17; confirmed `.codex/build3-supervisor-selfcheck-retry-3` and all case-insensitive aliases were absent; rechecked canonical non-reparse directory ancestors; and resolved `pwsh` to the configured native PowerShell executable. The wrapper's own fixed-path/ownership checks remain authoritative at invocation. This point-in-time precheck does not exclude a concurrent replacement; any wrapper refusal/non-PASS consumes this attempt and must be preserved.

## Exactly one authorized invocation

Run once, through W, from the workspace root:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File pipeline/scripts/invoke_teignmouth_float32_build3.ps1 -Mode self-check
```

Use retry-3 only, with the unchanged inherited **10-second total QPC deadline** and all caller/handoff/identity/Job/membership/reaping/tree/cleanup gates unchanged. Capture the actual process exit and resulting evidence. Do not replay this invocation or reuse any part of retry-3. Preserve all output/evidence bytes exactly, including a failure. After recording the single result, stop for diagnosis and a new bounded plan/review under disposition 64 if needed.

This gate authorizes only that one nonnumerical supervisor self-check. It does not authorize runtime preflight/identity collection, manifests, GIS/numerical/candidate build or reservation, serving/publication, browser action or any later phase. Retry-2 and all prior evidence remain immutable. Candidate remains **NO-GO and unservable**; build 3 remains unreserved. No commit, push or merge.
