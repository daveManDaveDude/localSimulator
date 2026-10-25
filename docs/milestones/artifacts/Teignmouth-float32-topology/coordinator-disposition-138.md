# Coordinator disposition 138 — release static gates after exact inverse proof

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** D134 implementation scope, D137 finite proof search, proof report below.

## Accepted proof

Accept `build-3/retry6-s-inverse-hash-proof-report.md`, SHA-256 `e424848a43bc48503b04a5ec15da550506907dd12ff3169e0575508b41edadef`. It independently reproduced Luna's failed inverse candidate from current S and the supplied original replacement literals; of the ten permitted two-LF seam pairs, exactly A-end+B-end matched full baseline S SHA `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff` at 232,527 bytes. This proves current S's delta is confined to the two D134-authorized regions. It does not establish implementation correctness or runtime behavior.

Current S must remain bound at `96daa955ce2ebe7a6315c000c99f174189d26bcf8941684541703ef688d921c7` unless and until an authorized gate/document updates it. Retry1–6 evidence remains untouched.

## Authorization: resume D134's static gates and independent source review

Authorize Luna to recheck current S/W/H/P hashes and consumed path literals against D134, record the exact two-region raw-byte diff and exact in-memory inverse proof (including the two seam separators and full baseline hash), then run only:

- `ruff check pipeline/scripts/run_teignmouth_float32_build3.py`
- `ruff format --check pipeline/scripts/run_teignmouth_float32_build3.py`
- the read-only exact filename/count/hash preservation gate for the70 bound evidence files and six protected source/config/test bindings.

If any bound hash, count, filename set, protected binding, raw diff, inverse result or required tool is unavailable/mismatched, stop and report. Do not edit source further under this disposition. Record exact commands and outputs without overclaiming.

After those gates, authorize a separate non-implementing Sol 6.1 reviewer to inspect the actual S bytes and handoff against the v2 plan, D134, and proof report. The review must assess strict/default call branches, terminal error capture ordering, wait/census state machine, proof/error/cleanup sequencing, two-region confinement, hashes/inverse and preservation evidence. It must write PASS or FIX REQUIRED and stop for coordinator decision. No implementation or automatic correction is authorized by a review finding.

## Explicit boundary

No tests/imports/parsers/compiler, process/runtime inspection, path/root/alias/absence work, retry7 creation or invocation, self-check, preflight, build, GIS/numerical work, serving/publication, product/AOI change, commit/push/merge or TVW-016 is authorized. Candidate stays **NO-GO and unservable**, build3 unreserved. A future retry invocation requires the independent source review to PASS and a separate new coordinator disposition with a one-use gate.
