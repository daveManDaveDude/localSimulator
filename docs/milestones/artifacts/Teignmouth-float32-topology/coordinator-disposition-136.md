# Coordinator disposition 136 — bounded search for exact pre-edit S bytes

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Coordinator decision after disposition 135 diagnosis SHA-256 `af487080b0ec87658674ae48dbff65d68aaed420a8d24ce54822fb1afa53d9fd`.

## Decision

The diagnosis establishes a manually reconstructed inverse shortfall but cannot establish exact missing byte positions or source-delta confinement. Keep current S frozen at SHA `96daa955ce2ebe7a6315c000c99f174189d26bcf8941684541703ef688d921c7` (239,683 bytes).

## Read-only search scope

Authorize a separate Sol reviewer to search filenames and inspect only non-consumed project history/handoff material under:

- `docs/milestones/artifacts/Teignmouth-float32-topology/`, excluding any files/roots that are bound consumed retry1–6 evidence;
- `.codex/history/` for this issue's non-consumed handoffs/checkpoints;
- the current repository's non-consumed implementation handoff artifacts.

Search for an already existing full raw copy of `pipeline/scripts/run_teignmouth_float32_build3.py` matching the pinned pre-edit SHA `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff`, or retained exact pre-edit byte strings sufficient to perform and independently verify the planned two-region inverse. Hash a candidate before reading its contents where possible. Do not inspect any consumed retry1–6 evidence contents or traverse the `.codex/build3-supervisor-selfcheck-retry-1` through `retry-6` roots. Do not inspect unrelated user folders or use untracked/temporary files unless already identified within the named non-consumed scope.

Write a concise search report listing searched non-consumed directories, filenames of any candidate found, candidate hash/size and match result, or state that no exact baseline was found. Do not infer a baseline from line endings or add guessed bytes.

## Prohibited actions

No source/artifact edits except the search report, restore, reconstruction, Ruff or other gates, tests/imports/parsers, process inspection, path/root creation/reservation, runtime/self-check/build, or candidate/output work. Current S remains frozen. Stop after the report for coordinator decision.

Retries1–6 remain consumed, immutable and non-PASS; budgets/counters unchanged. Retry7 remains unselected/unreserved. Candidate remains **NO-GO and unservable**; build3 unreserved.
