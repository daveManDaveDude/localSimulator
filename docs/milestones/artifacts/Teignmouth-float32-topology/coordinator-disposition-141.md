# Coordinator disposition 141 — implement E501-only wraps and rerun gates

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** D139, D140 plan-only review, D138 static gates, D137 exact inverse proof.

## Plan acceptance

Accept Sol plan `build-3/retry6-s-e501-wrap-plan.md`, SHA-256 `5a1eec1464cabbc962b5d79ef07e8987c5a668665139834f461afb704f86ae3a`, and its independent PASS review `build-3/retry6-s-e501-wrap-plan-independent-review.md`, SHA-256 `52a4725ae556f69d59d05be02e08c2224ea346e70b2c9023bd12afbe1cc505b5`.

## Narrow Luna edit and required verification

Authorize Luna to edit only the two exact single-line TimeoutError calls in `pipeline/scripts/run_teignmouth_float32_build3.py` listed in that plan, wrapping the existing call in parentheses while preserving the exception type and entire message string byte-for-byte. Required pre-edit S hash: `96daa955ce2ebe7a6315c000c99f174189d26bcf8941684541703ef688d921c7`. Any source drift, target-text mismatch, broader formatting or semantic change is a stop.

Record tight raw-byte diff and final S hash. Prove exact scope in memory in two steps: reverse just the two wraps to require current pre-wrap S hash/size `96daa955ce2ebe7a6315c000c99f174189d26bcf8941684541703ef688d921c7`; then apply the already hash-proven D137 A-end/B-end inverse and require original accepted S hash `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff`,232527 bytes. Do not write or execute reconstructed bytes.

Then run only S `ruff check`, S `ruff format --check`, and the read-only exact filename/count/hash preservation gate for all70 bound evidence files and six protected source/config/test bindings. Rerun unchanged W/H/P/path/default/strict-capture/proof/cleanup static bindings. Preserve and report the earlier E501 failures. If any gate is missing or fails, stop without another edit; do not run later gates after an earlier required gate failure.

After all listed gates pass, a separate non-implementing Sol 6.1 reviewer must inspect the actual final S bytes and the full evidence package against D134/v2, D137, and the accepted two-wrap plan. Reviewer returns PASS or FIX REQUIRED and stops. No later runtime action is authorized by this disposition.

## Explicit boundary

No tests/imports/parsers/compiler beyond the listed Ruff gates, process inspection, path/root/alias/absence work, retry7 path or invocation, self-check, preflight, build, GIS/numerical work, serving/publication, product/AOI changes, commit/push/merge or TVW-016. Retries1–6 remain consumed/immutable/non-PASS, counters unchanged; candidate remains **NO-GO and unservable**, build3 unreserved. Any further code correction or retry invocation requires separate review and a new coordinator disposition.
