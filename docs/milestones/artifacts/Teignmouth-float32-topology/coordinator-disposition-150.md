# Coordinator disposition 150 — immediate retry-7 source/path preflight only

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** D149 final independent review PASS.

## Accepted source/path review

Accept `build-3/retry-7-path-binding-final-independent-review.md`, SHA-256 `655436f6b1009457a62fd26c6ec36798b5a6a2fcf1bdc56495c83f9103dfcb6f`, for static four-literal implementation only. Corrected handoff SHA-256 is `af6d8e923a9d86f2054a5e1174fd3db1e9d2404f55751d700c1bc791e248365b`; final source W/S/H/P hashes and static/preservation results are bound there. No retry7 path availability is claimed.

## Authorization: coordinator preflight, no invocation

Authorize the coordinator to perform one immediate, read-only preflight against the exact retry7 proposal in the accepted plan:

- Recheck W/S/H/P hashes against the corrected handoff; exact retry7 counts W/S/H=2/1/1, zero active retry6 literals, P=0; exact path plan/handoff/review bindings.
- Verify the existing canonical ancestor chain `C:\`, `C:\vibe`, `C:\vibe\localSimulator`, and `C:\vibe\localSimulator\.codex` consists of ordinary directories with no reparse-point/symlink component.
- Confirm the proposed parent `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-7` is absent as file and directory. Enumerate the safe existing `.codex` parent and reject any child whose name equals the retry7 leaf under case-insensitive comparison or Windows trailing-dot/space normalization.
- Confirm the accepted plan's protected refusal targets `C:\vibe\localSimulator\data\generated\teignmouth-float32-topology` and `C:\vibe\localSimulator\docs\milestones\artifacts\Teignmouth-float32-topology\build-3\run-1` are absent as file/directory, including a normalized alias in any existing safe immediate parent. Require existing ancestors to be safe ordinary directories; any unsafe/missing premise required by the plan is a stop.
- Because the parent must be absent, all derived retry7 parent/leaf outputs are absent; do not create, reserve or write the root during this preflight.

Record exact commands/observations and whether every predicate passed. Do not inspect consumed retry1–6 roots/content, run process checks, or create any target. If any source/hash/path/alias/ancestor/refusal predicate fails or is ambiguous, stop; do not try another path.

## Separate one-use gate required

This disposition does **not** authorize an invocation. Only if every preflight predicate passes may the coordinator issue a new immediate one-use disposition binding the freshly observed state and authorizing exactly one wrapper command:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File pipeline/scripts/invoke_teignmouth_float32_build3.ps1 -Mode self-check
```

No direct S/H call, replay or alternate path. Any invoked refusal, partial start, timeout, nonzero result or non-PASS consumes retry7; preserve outputs and stop without replay. Candidate stays NO-GO/unservable even if self-check passes; no build/serving/publication authorization follows.

Retries1–6 remain consumed/immutable/non-PASS, counters carry forward. Retry7 remains unselected/unreserved until the separate one-use gate. No candidate build, GIS/numerical/product/AOI change, commit/push/merge or TVW-016.
