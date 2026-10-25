# Coordinator disposition 148 — implement retry-7 path binding, static gates only

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** D146, D147 independent plan review, accepted static implementation review.

## Accepted plan

Accept `build-3/retry-7-path-binding-plan.md`, SHA-256 `ea4527b3f0824adb8349d7dfc511d150d98ab8792d953490a257ccf6c589f935`, and independent PASS review `build-3/retry-7-path-binding-plan-independent-review.md`, SHA-256 `4d53a66c09807ba22df426478c860a7dbe0c6b978845d572e2c9ff8947be4c80`.

## Authorized Luna implementation and checks

Authorize exactly four final-digit literal changes, bound to current hashes in that plan: W23 and W344 from retry-6 parent to retry-7 parent; S39 from retry-6 parent to retry-7 parent; H17 retry-6 leaf to retry-7 leaf. P remains byte-identical. Preserve source encodings/newlines and every other byte. Reverse exactly the four literal changes in memory to recover W `f600efc…`, corrected S `fda96d4…`, H `75678b…`, and P unchanged `aa1b4b…`; verify old/new occurrence counts and no additional consumers in the scoped files. Record exact diff, final hashes and inverses.

Run only the plan-authorized later static gates: S/H Ruff check and format-check; W AST parse without invoking it; exact source/count/inverse checks; read-only full70-file name/count/hash preservation and six protected hashes. Verify paths/default/strict proof/cleanup bindings remain as accepted. Record exact commands/results; if any check is unavailable or fails, stop with no further edit. Do not read consumed retry1–6 evidence contents; use accepted reports/matrices only.

After the handoff, authorize a separate non-implementing Sol actual-byte review for source bindings, four literal scope/inverse, W/S/H/P behavior, static gates and preservation result. It must PASS before any root/path check or invocation. No root existence, ancestor, alias, or absence work occurs in this disposition.

## Explicit boundary

Do not check, inspect, probe, create, reserve or write retry7 parent/leaf/derived paths; do not inspect retry1–6 roots. No process inspection, retry/self-check/runtime/preflight/build, GIS/numerical/product/AOI/serving/publication, commit/push/merge or TVW-016. No direct S/H invocation. A later separate immediate one-use gate is mandatory. Retry1–6 remain consumed/immutable/non-PASS; retry7 stays unselected/unreserved until that gate. Candidate remains **NO-GO and unservable**, build3 unreserved.
