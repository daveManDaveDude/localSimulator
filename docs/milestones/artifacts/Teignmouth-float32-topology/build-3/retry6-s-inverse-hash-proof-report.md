# S inverse hash proof — finite seam search

2026-10-25. Issue `Teignmouth-float32-topology-representation-1`; D137 bounded read-only proof. **Unique match: insert one LF at A-end and one LF at B-end in the exact reported inverse candidate. The result matches the pinned full S baseline hash and byte length.** No source file changed; this is byte/scope proof, not implementation correctness acceptance.

## Input and exact reproduction

Only current `pipeline/scripts/run_teignmouth_float32_build3.py` was read. Its actual SHA-256 is `96daa955ce2ebe7a6315c000c99f174189d26bcf8941684541703ef688d921c7`,239683 bytes. Strict UTF-8 decoding and UTF-8 encoding without BOM were used; no trimming, line-ending normalization, source restoration or file output occurred.

Used Luna's supplied old function A and old wait block B with the prescribed slices:

- A: `def _assert_tree_contained(` through immediately before `def _contained_interpreter_child(`.
- B: `        containment_deadline = deadline - 1.0` through immediately before `        root_marker_path = SELF_RUN / "tree-root-started.json"`.

The supplied replacement A's body/string retained two trailing LF bytes after its final statement; B retained none after its final early-exit raise. With the supplied bodies and these replacement-string boundaries, the independently recreated candidate is exactly **232525 bytes**, SHA-256 **`90c3e919e7e05f9cb4add4eca6e201ea97b42605c0173dec45e384bed53a009b`**. The candidate binding was checked before running the finite search; it matches Luna's failed inverse completely, not merely its size.

## Four seams and permitted search

Zero-based UTF-8 offsets in that failed candidate:

| Seam | Byte offset |
| --- | ---: |
| A-start |14454|
| A-end, immediately before the surviving next definition |16631|
| B-start |183005|
| B-end, immediately before the surviving marker line |183489|

Tested exactly the10 unordered pairs with repetition, inserting exactly two `0A` bytes and changing nothing else. Each resulting candidate is232527 bytes:

| Insertions | Candidate SHA-256 | Match |
| --- | --- | --- |
| A-start + A-start |`700304c26123d73810871117f8b814d9ec996446983dc1dd7d18a3e12f305db7`|No|
| A-start + A-end |`fbf8584fb0e2fd3245ab0eee0b8e2f4b6ea877dba6d8382c49476282dc8da044`|No|
| A-start + B-start |`d3d91c40ee4456b07c6c6242553934c19e971bc62c50ea1f8ee4b7349f5be783`|No|
| A-start + B-end |`8ea1199e03877597794cc1f02e45bb4fd78ab1ffbff42082eb26cffe1bbf5eb0`|No|
| A-end + A-end |`b6c781fd9e999d67d0bd7c0eeda822019d9ed9757f519dd33a688f5c7358a47f`|No|
| A-end + B-start |`7bbe9cd5a8c12579b497f7600b796805ba0348f5f9316d2880de259e2a04057f`|No|
| **A-end + B-end** |**`1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff`**|**Yes**|
| B-start + B-start |`33227fa4f1e4defc205d89eccf7267b7d6ecbd1e706172637ea8161cbe423da4`|No|
| B-start + B-end |`130aa7427ee9b5f4c2b9839aa4fa2a16c21c71f91f90cffe4fb253b937919505`|No|
| B-end + B-end |`67c9607bc23b8c8a808f26ccc50397a970b4419ecbad410100b1eb583c106843`|No|

## Exact discrepancy and proof-safe operation

The manual inverse replacement strings omitted:

1. One separating LF at A-end before `def _contained_interpreter_child(`. The bound baseline requires three LF bytes after A's final statement; the failed candidate has two.
2. One LF at B-end between the early-exit raise and `root_marker_path`. The failed replacement string has no terminating LF; the baseline has one.

For the specifically bound failed candidate, insert LF at zero-based offset183489 first, then at16631, so the earlier insertion cannot shift the later offset. Equivalent ascending insertion uses16631 and then183490. Both refer to the same two original seams. Require the initial candidate hash/length and final full baseline hash/length; no general newline cleanup or normalization is justified.

This exact result resolves the previously unproven net deficit under D137's expressly bounded search. It demonstrates that reversing only the two authorized current S regions, with their exact baseline separator ownership, restores **all232527 baseline bytes** at the pinned full hash. Current source changes are therefore confined to those two regions. It does not establish branch/API/error/deadline correctness, Ruff results, preservation or runtime behavior. No baseline snapshot was found or claimed; the baseline bytes were reconstructed only in memory by the specifically authorized finite hash proof and were not written or executed.

## Boundary and handback

Only current S was read and this proof report written. No consumed evidence or other file was read during this proof. No source edit/restore, broader candidate search, Ruff/gates/tests/imports/parsers/compiler, process inspection, path/root operation or runtime invocation occurred. Current S remains `96daa955…`, edited and awaiting coordinator decision/independent implementation review. Retries1–6 remain consumed/immutable/non-PASS, counters unchanged, retry7 unselected/unreserved, candidate NO-GO/unservable and build3 unreserved. Stop; no further source correction or gate execution follows automatically.
