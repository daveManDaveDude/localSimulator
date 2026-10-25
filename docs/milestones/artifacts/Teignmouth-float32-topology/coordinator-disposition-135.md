# Coordinator disposition 135 — read-only diagnosis of failed inverse gate

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Coordinator stop/review required by disposition 134 after Luna reported a failed exact in-memory inverse.

## Observed state

Luna reports the D134 baseline hashes matched before editing and `_api()` matched the planned last-error setup. After edits to the two authorized S regions, current S is `96daa955ce2ebe7a6315c000c99f174189d26bcf8941684541703ef688d921c7` (239,683 bytes). The implementer's inverse operation produced `90c3e919e7e05f9cb4add4eca6e201ea97b42605c0173dec45e384bed53a009b` (232,525 bytes), not baseline S `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff` (232,527 bytes). No Ruff or preservation gate ran; no implementation handoff was written.

## Authorization: Sol read-only byte/inverse diagnosis only

Authorize a non-implementing Sol diagnostician to examine the current S bytes, the v2 plan, D134, and Luna's stated sizes/hashes to explain the exact two-byte discrepancy and determine whether it comes from the inverse procedure, encoding/newline handling, or an edit outside the two authorized spans. It may inspect only current S and existing non-consumed plan/handoff documents; do not read consumed retry1–6 evidence contents. If there is no independently available exact baseline byte source, say so rather than reconstructing or fabricating it.

The diagnostic may calculate hashes, lengths, line-ending/BOM facts, and read-only in-memory comparison offsets. It must not write/edit any file, restore or patch source, run Ruff or other gates, tests/imports/parsers, inspect processes, perform paths/roots, invoke any runtime/self-check/build, or make a pass/fail claim about implementation correctness. Write a concise diagnostic report bound to the observed current S hash and stop for a new coordinator decision.

## Preserved boundary

Current S remains edited and unreviewed; do not discard or amend it. No further source edit or static gate is authorized until the diagnostic is received and a new coordinator disposition is made. Retries1–6 remain consumed, immutable and non-PASS; counters unchanged. No retry-7 path/invocation, build, GIS/numerical work, publication or product/AOI change is authorized. Candidate remains **NO-GO and unservable**; build3 unreserved.
