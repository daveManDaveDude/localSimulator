# Coordinator disposition 144 — implement formatter lambda collapse

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** D142, D143 plan review, D141 gate release and D137 inverse proof.

## Plan acceptance

Accept `build-3/retry6-s-formatter-lambda-collapse-plan.md`, SHA-256 `86ea2c2461871603a4a55b590dc44844c14b2a9449d6eaa996b3e3b4d8959d29`, with independent PASS review `build-3/retry6-s-formatter-lambda-collapse-plan-independent-review.md`, SHA-256 `cbd3ff313a6c19febdf83ea314a902748c19c10fd4b96783e49d53ae23b0308f`.

## Narrow edit and gates

Authorize Luna to collapse only the exact three-line `_sample_job` callback in the D134 self-check wait block to the exact 91-column one-line call in the accepted plan. Required pre-edit S hash is `7a1c38fe72ea274777538135154200c03cd5de8eeb6f4cd3d8d0b89b169228cc` (239775 bytes). Preserve lambda/deferred semantics and all arguments. Any mismatch, source drift or additional formatter request is a stop; no broader formatting.

Record tight raw-byte diff/final S hash and prove this inverse chain entirely in memory: reverse only the lambda collapse to recover pre-collapse S `7a1c38fe…`; reverse only the two accepted E501 wraps to recover S `96daa955ce2ebe7a6315c000c99f174189d26bcf8941684541703ef688d921c7`; then apply the D137-proven A-end/B-end LF inverse to recover accepted baseline S `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff`,232527 bytes. Do not write or execute reconstructed bytes.

Rerun, in order, S Ruff check, S Ruff format-check, and the read-only exact filename/count/hash comparison for all70 bound evidence files and six protected source/config/test bindings. Also verify unchanged W/H/P/path/default/strict-proof/cleanup hashes and bindings. Preserve both earlier E501 failures and the D141 formatter request in the handoff. Stop immediately on failure; do not make another edit under this disposition.

After every required gate passes, authorize separate non-implementing Sol actual-byte review against D134/v2, D137, and both accepted formatting plans/reviews. The reviewer must bind final S/W/H/P and preservation evidence, inspect exact change scope and semantics, then return PASS or FIX REQUIRED. No execution authority follows automatically.

## Explicit boundary

No tests/imports/parsers/compiler beyond the listed Ruff gates, process inspection, path/root/alias/absence work, retry7 path or invocation, self-check, preflight, build, GIS/numerical work, serving/publication, product/AOI changes, commit/push/merge or TVW-016. Retries1–6 remain consumed/immutable/non-PASS; counters unchanged. Candidate remains **NO-GO and unservable**, build3 unreserved.
