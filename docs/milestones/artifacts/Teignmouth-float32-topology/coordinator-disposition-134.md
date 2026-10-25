# Coordinator disposition 134 — implement retry-6 S census correction

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User's continuing authorization; disposition 133 and the independent PASS review bound below.

## Decision and binding

Accept the independent plan-only PASS for `build-3/retry6-s-wait-callback-correction-plan-v2.md`, SHA-256 `d44d4133875c8b5d378335ee176a01637961980846ad76521f69743245e67e05`. The review is `build-3/retry6-s-wait-callback-correction-plan-v2-independent-review.md`, SHA-256 `e8e7c30ba8622e80ed604385c146fdc277a60356dc507211df77ef4978d5a404`.

Authorize one Luna implementation of that exact S-only correction. Required baseline hashes before editing:

- S `pipeline/scripts/run_teignmouth_float32_build3.py`: `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff`
- W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`: `f600efc92fd040aa5b91cf543210be139ed50f895eba7d62c34175e73dc7dc8b`
- H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py`: `75678b51d0e17d89862bf0a7ee3446014969ba73aae6cd31606288553b163e27`
- P `pipeline/scripts/teignmouth_build3_runtime_preflight.py`: `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`

## Implementation scope and required evidence

Change S only in the two regions defined in the v2 plan: `_assert_tree_contained` (strict opt-in same-snapshot terminal enumeration proof, default false preserving existing callers) and the self-check tree wait block (separate wait horizon, bounded containment deadline, periodic census, and exactly one mandatory final complete census before unchanged downstream marker checks). Use the existing last-error-enabled kernel and preserve the immediate error capture ordering, row/ancestry/Job bounds, fail-closed errors, deadline/reserve behavior, primary-error handling and cleanup. Do not broaden the census or change the shared `_wait_process` implementation.

Record a tight raw-byte diff, resulting S hash, unchanged W/H/P and consumed path literals, and an exact in-memory inverse demonstrating restoration to baseline S. Stop and return for coordinator review if the baseline differs, the existing ctypes last-error setup does not match the plan, or implementation requires a wider edit/new binding/API/import/right or changes default/shared behavior.

After implementation, the authorized static gates are S Ruff check and Ruff format-check, plus a read-only exact filename/count/hash preservation gate for all 70 bound evidence files and six protected source/config/test bindings. Record commands and results accurately. An unavailable tool or failed gate is a stop, not a pass. A separate non-implementing Sol actual-byte/branch/hash/inverse/preservation review is mandatory before any further coordinator decision.

## Explicit boundary

This authorizes the S source edit and the specified static/preservation gates only. It does not authorize parser/compiler/linter beyond the specified Ruff gates, tests/imports, runtime/process inspection, new path/root/alias work, any retry-7 path or invocation, preflight, self-check, build, GIS/numerical work, candidate serving/publication, product/UI changes, AOI status changes, commit/push/merge, or TVW-016. Retries 1–6 remain consumed, immutable and non-PASS; budgets/counters carry forward. Candidate remains **NO-GO and unservable**; build 3 remains unreserved. Any later retry invocation requires independent implementation review and a new explicit coordinator disposition and one-use gate.

Stop for review after implementation and the listed static gates; no retry or runtime action follows automatically.
