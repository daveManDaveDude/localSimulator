# Coordinator disposition 137 — bounded hash-confirmed inverse proof

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Coordinator decision after D136 no-match report SHA-256 `2f91c4aa0af2f118235528d727e812f83dc6f674c800ed1c7da6b1b16617cba6` and D135 inverse diagnosis SHA-256 `af487080b0ec87658674ae48dbff65d68aaed420a8d24ce54822fb1afa53d9fd`.

## Frozen inputs

Current S must remain unchanged at SHA-256 `96daa955ce2ebe7a6315c000c99f174189d26bcf8941684541703ef688d921c7`. Target pre-edit S SHA-256 is `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff`.

Luna reports the failed inverse used two splice replacements: (A) the slice starting at `def _assert_tree_contained(` and ending before `def _contained_interpreter_child(`; (B) the slice starting at `        containment_deadline = deadline - 1.0` and ending before `        root_marker_path = SELF_RUN / "tree-root-started.json"`. The reconstructed candidate was 232,525 bytes, two bytes shorter than the target.

## Authorization: one in-memory proof search

Authorize Sol and Luna to recover Luna's exact replacement here-string texts from the completed implementation turn if still present in their task context, without reading consumed evidence or using filesystem recovery. Then authorize Sol to:

1. Recreate the same inverse candidate entirely in memory from current S and those exact reported replacement texts, using strict UTF-8 without BOM, with no line-ending normalization or trimming.
2. Search only the finite candidate family formed by inserting exactly two `0x0A` LF bytes at any pair (including twice at one seam) of these four immediate splice boundaries: A start, A end, B start, B end. Do not alter any other byte, move/delete bytes, or expand the search family.
3. SHA-256 each candidate and report success only if the full candidate has exact target hash `1cee4b1d…` and byte length232,527. A matching cryptographic digest is evidence of exact restoration; list the two seam positions and resulting size/hash. On no match or unavailable literal text, report no proof and stop. Do not infer success from length alone.

This proof is strictly in memory. No source restoration/edit, file write except the final report, Ruff/preservation gate, tests/imports/parsers, process inspection, path/root work or runtime invocation is authorized. Current S remains frozen. Do not read any consumed retry1–6 evidence or leave the permitted candidate family.

## After the search

Write a short report bound to current S SHA, input method, exact candidate-space bounds, result and limitations. Stop for coordinator decision. Even a proven inverse does not itself authorize running gates or code review; a new disposition is required. Retries1–6 remain consumed/immutable/non-PASS, counters unchanged, retry7 unselected/unreserved, candidate **NO-GO and unservable**, build3 unreserved.
