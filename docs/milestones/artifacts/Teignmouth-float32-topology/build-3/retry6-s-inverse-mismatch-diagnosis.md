# S inverse mismatch — bounded read-only diagnosis

2026-10-25. Issue `Teignmouth-float32-topology-representation-1`; disposition135. **The available evidence supports a manually reconstructed inverse shortfall, not an exact two-byte source diagnosis. No independently available full baseline byte source exists in the authorized records. Exact source-delta confinement therefore remains unproven.** Stop with current source unchanged for coordinator decision.

## Bound observations

| State | SHA-256 | Bytes |
| --- | --- | ---: |
| Current S, independently rehashed | `96daa955ce2ebe7a6315c000c99f174189d26bcf8941684541703ef688d921c7` | 239683 |
| Implementer's reported inverse candidate | `90c3e919e7e05f9cb4add4eca6e201ea97b42605c0173dec45e384bed53a009b` | 232525 |
| D134 pinned pre-edit S | `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff` | 232527 |

Current S is strict-decodable UTF-8, has no UTF-8 BOM, zero CR bytes,5264 LF bytes and a final LF. Decode/re-encode as UTF-8 preserves its byte length. Its function boundary contains the expected LF-separated gap before `def _contained_interpreter_child`; no current encoding fact identifies two erroneous bytes. These are current-source observations, not a full baseline comparison. The inverse candidate's digest/length are Luna's report; its full bytes were not retained as an independently inspectable snapshot.

The v2 plan is `retry6-s-wait-callback-correction-plan-v2.md`, bound by D134 to `d44d4133875c8b5d378335ee176a01637961980846ad76521f69743245e67e05`. It authorizes only the opt-in containment helper and self-check tree block, and requires an exact inverse to the pinned S baseline. This diagnosis does not waive that gate.

## Reported inverse method and its limits

Luna's method, relayed by the coordinator, was:

1. Read current S bytes and strictly decode UTF-8 without BOM handling/normalization.
2. Replace the slice beginning `def _assert_tree_contained(` and ending immediately before `def _contained_interpreter_child(` with a **manually copied pre-edit function here-string**.
3. Replace the slice beginning `        containment_deadline = deadline - 1.0` and ending immediately before `        root_marker_path = SELF_RUN / "tree-root-started.json"` with a **manually copied pre-edit wait-block here-string**.
4. Re-encode UTF-8 without BOM and hash. No trimming or line-ending normalization was reported.

These boundaries include or abut newline/separator bytes. A manually copied function replacement must reproduce not only statement text but exactly the trailing separator bytes before the next definition. The wait replacement must likewise reproduce exactly its final LF before the surviving marker line. Here-string delimiter/newline ownership can affect either boundary. Missing LF bytes are therefore a possible explanation, but **no specific boundary, byte value or offset is established** by the available records.

Luna acknowledges that its manual replacement text was two bytes shorter overall. The candidate has a **net two-byte deficit** against the pinned baseline length. That does not prove two LF deletions, identify which replacement is short, or exclude additional equal-length differences. The unequal SHA proves the candidate is not the exact baseline; it does not locate the differences or establish whether current source outside the authorized spans is unchanged.

The reported UTF-8 decode/encode procedure is consistent with the current file's no-BOM/LF facts and is not, by itself, a normalization operation. A missing UTF-8 BOM would be three bytes, not this net deficit alone; no current BOM exists. Neither that arithmetic nor current zero-CR facts can prove old-source separator/encoding bytes without the full baseline. A “fix” by inserting two guessed newlines, adding a BOM, trimming, restoring or normalizing source would be unsupported.

## What is and is not established

Established: current S matches the reported edited-source binding; the manually reconstructed inverse reportedly differs in both length and hash from D134's exact baseline. Existing plan/handoff hashes identify intended source states but do not supply a full pre-edit raw S image. There is no exact pre-edit S snapshot available in the authorized material, and no raw-byte diff against it can be independently completed here.

Not established: exact missing byte values/offsets, exact separator ownership in Luna's two replacement strings, absence of equal-length replacement errors, or absence of an out-of-span current-source change. No implementation correctness verdict follows from this diagnostic. In particular, do not describe the inverse as corrected or confinement as proven merely because the size difference looks like two newlines.

## Minimal next action and boundary

Keep S frozen at `96daa955…`. Coordinator must decide whether an already existing exact baseline byte source or retained raw inverse/replacement text can be obtained under a new bounded read-only scope, or whether a separate explicitly authorized recovery/proof procedure is necessary. Require the full baseline hash and exact scoped diff/inverse before claiming confinement or releasing remaining gates. No baseline reconstruction, source edit or guessed separator repair is authorized or performed by this report. Do not run Ruff/preservation/runtime merely to bypass the failed inverse gate.

Only current S and authorized non-consumed disposition/plan/supporting-document reads/searches, hashing and in-memory length/encoding/boundary observations occurred. Only this expressly requested diagnosis report was written; no source or other artifact was edited. No consumed retry1–6 evidence contents, Ruff/gates/tests/imports/parsers/compiler, live processes, path/root creation/reservation or runtime/self-check/build invocation occurred. Retry1–6 remain consumed/immutable/non-PASS, counters unchanged, retry7 unselected/unreserved, candidate NO-GO/unservable and build3 unreserved. Stop for coordinator decision.
