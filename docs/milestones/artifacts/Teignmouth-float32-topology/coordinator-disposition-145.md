# Coordinator disposition 145 — correct read-only binding assertion and handoff

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Coordinator stop after D144 verification-script pattern mismatch.

## Bound implementation state

Current S `pipeline/scripts/run_teignmouth_float32_build3.py` is SHA-256 `fda96d4edd66327e50c34ee1345d1a098aced4a7b58dcd1c088a4cd8c44c616f`,239737 bytes. Luna reports the D144 inverse chain, S Ruff check, S Ruff format-check, 70-file matrix and six protected hashes passed. The run then stopped because a verification script searched for `require_complete_snapshot=False`, while the planned actual signature is typed (`require_complete_snapshot: bool = False`). No source edit followed; no final handoff was written. The prior gate results remain Luna-reported until independently reviewed; no test/runtime was run.

## Authorization: read-only assertion correction and report

Authorize Luna to perform only a corrected read-only marker/binding check using the exact typed signature `require_complete_snapshot: bool = False` from the accepted v2 plan, confirm strict-proof/default-caller markers and D134 unchanged W/H/P/path bindings, and write a handoff recording exact commands/results and the prior verification-script typo. Do not rerun Ruff or preservation unless current hashes differ from D144's result; if a current hash or gate result cannot be recovered, report unavailable and stop rather than rerun unauthorized gates. No source or other implementation edit is allowed.

After the handoff, authorize a separate non-implementing Sol reviewer to inspect current S bytes and the complete D134/v2, D137, E501-wrap and lambda-collapse proof/gate evidence. This review must independently confirm final source hash, both gate outcomes, preservation evidence, exact in-memory inverse chain and actual strict/default branches. Return PASS or FIX REQUIRED and stop for coordinator decision.

## Boundary

No tests/imports/parsers/compiler, further lint/format/preservation gates, process/path/root/runtime/self-check/preflight/build/retry invocation, GIS/numerical/product/AOI/serving/publication, commit/push/merge or TVW-016. Retries1–6 remain consumed/immutable/non-PASS; counters unchanged. Candidate remains **NO-GO and unservable**, build3 unreserved.
