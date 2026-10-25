# Coordinator disposition 142 — Sol diagnosis/plan for Ruff formatter diff

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Coordinator stop after D141 format-check failure.

## Bound result

The D141 two-wrap edit passed `ruff check` and its in-memory inverse chain. `ruff format --check` did not pass; it requests only collapsing the multiline `_sample_job` lambda in the self-check tree block to the one-line form shown in the check output. The preservation gate did not run. Current actual S has SHA-256 `7a1c38fe72ea274777538135154200c03cd5de8eeb6f4cd3d8d0b89b169228cc`, size239775 bytes. Keep it frozen.

## Authorization: Sol read-only diagnosis and correction plan only

Authorize Sol to inspect current S, the Ruff format-check output in the D141 handoff/message, D134/v2, the accepted E501 wrap plan/review, and D137 inverse proof. Confirm that the requested `_sample_job` lambda collapse is within the D134-authorized wait-block region, exact-call behavior is unchanged, the one-line form is within configured width, and the change can be added to the exact in-memory inverse chain. Write a concise plan with exact source text/spans, expected changed line, inverse validation, affected Ruff reruns and preservation requirements.

Plan/diagnosis only: no source edit, no Ruff/format command (including `--diff`), no preservation gate/tests/imports/parsers/compiler/process/path/root/runtime/self-check/build, and no consumed retry1–6 evidence reads. If actual S differs from the bound or a broader format change is needed, stop. Stop after the plan for separate independent Sol plan review and coordinator decision.

Retries1–6 remain consumed/immutable/non-PASS, counters unchanged; retry7 unselected/unreserved. Candidate remains **NO-GO and unservable**, build3 unreserved. No source repair or further gate is authorized here.
