# Independent Sol review — Sol correction 1

Date: 2026-10-24. Reviewer: `/root/sol_correction_reviewer`, separate non-implementing Sol 6.1 medium session. Verdict: **FIX REQUIRED — NEEDS USER DECISION**. The approved cap correction is correctly scoped, but the candidate fails mandatory topology acceptance and must remain unservable.

## Inspection boundary

Inspected the active specification, workflow/skill, limit decision 1, diagnostic 1 metadata/bindings, archived pre-correction files, current source/config/tests/runner, actual read-only before/current diffs, build-6 report/traceback, observations, preflight, verification, handback, authorization/submission hashes and preservation snapshot entries. No tests, scripts, builds, diagnostics, profiles, browser sessions or numeric/hash recomputation were performed. Only this review and authorized ledger/checkpoint metadata were written.

Numeric values, resource measurements, buffer lengths, test results and SHA-256 values were inspected as recorded evidence, not independently recomputed. This review does not certify current file hashes or a fresh executable result.

## Scope

Actual four-file before/current diffs agree with `implementation.diff`. The implementation changes only the continuation expected/configured cap, necessary rejection at `difference >= 6.5`, final overlay acceptance at `<6.5`, and corresponding report text. Tests reject equality at both -6.5 and +6.5 m and accept 6.499 m as necessary-only evidence. Runner changes only the fresh build-6 output guard, preservation exclusion and text. The existing evidence leaf remains write-once.

Every other limit and recipe is unchanged by these diffs: added gradient `<1.0 m/m`, local cross-slope <=5%, span <=0.30 m, centerline deviation <=2.0 m and longitudinal grade <=10%; source identity, field/chart, widths, fades, bounds and topology guard remain unchanged. Wider dirty files include earlier unrelated work and cannot be attributed to this submission from repository status alone.

## F1 — mandatory Float32 topology validity fails

Type: behavior/geometry blocker. The existing guard at `pipeline/torquay_pipeline/road_surface_topology.py:566` rejects distinct construction vertices `(-164.2316811012587, -85.5)` and `(-164.23167542853238, -85.5)` mapping to one Float32 key. The actual report traceback leads through continuation `assemble_corrected` at line 443, before a mesh is returned. The guard compares Float32 keys with exact construction coordinates; rejecting a collision prevents silent conflation of distinct noded topology. Preserving the guard and failed evidence is correct. Float32 conversion was not independently recalculated in this inspection.

Expected eventual correction, only under new user authority: produce source-conforming geometry representable in the required Float32 contract, preserving source planes/perimeter, coverage, ownership and every accepted numeric limit, then establish the missing offline and independent evidence. No correction is authorized under the exhausted current budget. Do not relax the Float32 guard/tolerance or use confirmation capacity to repair this failed candidate.

## Durability and stage context

`build-6/report.json` durably contains error type, exact coordinates, traceback, interpreter, STOP reasons, resources, preservation and serving=false. `stage-observations.json`, source/config bindings and retained chart buffers provide recipe/stage context; submission hashes bind the report and observations. This is sufficient durable context to establish the topology stop. Recorded wall time is 7.373759900016012 s against 180 s; peak working set is 564,113,408 bytes. Neither was remeasured.

The existing exception handler replaces the intermediate report, losing detailed build-6 profile/source/preflight/ownership objects. Reaching `assemble_corrected` supports the explicitly labelled control-flow inference that preflight and preliminary ownership early-return gates passed. It supplies no separately certified ownership result. The handback accurately discloses this limitation. No completed mesh existed to serialize; incomplete mesher internals were not retained. These limitations prevent stronger acceptance claims but do not obscure the captured failure or justify another attempt to restate it.

## Gates

- Reached: source load/chart construction; three retained chart buffers (recorded total 78,048 bytes); preflight and preliminary ownership passed by control-flow inference; mesh construction entered.
- Reused sample-only evidence: diagnostic 1 records 21,336 samples, maximum cut 6.397848390875038 m and maximum fill +3.107435071671972 m. Diagnostic chart hashes agree with recorded build-6 chart hashes; inspected diffs leave the field/sample construction unchanged. This supports reuse below the approved cap, not a final mesh or continuous-field maximum. Diagnostic 1's original 6 m failure remains historical truth.
- Failed: Float32 topology during construction, before final mesh completion.
- Not reached: final source/patch overlay extrema, added gradient, final topology/coverage/perimeter/source-plane and final local cross-slope/span/centerline/grade gates.
- Not implemented/evidenced: complete building contact, road reclip/drape/coherence and shared walking surface. No deterministic confirmation, browser/screenshots or runtime acceptance; serving remains blocked.

Recorded 38 passing focused tests, Ruff checks and exact-venv import smoke are implementer evidence only; they do not establish missing real-candidate gates. No browser or fresh quality-gate pass is claimed by this reviewer.

## Preservation, counters and disposition

Report records 944 compared paths and zero changes. Submission records give identical before/after snapshot digests `6b54d426e3e857548aa36532ff0a092901e3a888a811b40fd82500a29133f695`; inspected entries agree for AOI config, topology module, build-5 report and diagnostic 1. Preflight records 925 prior paths checked and no unexpected changes, with explicit authorized changed paths. Scope excludes ignored raw GIS, mutable ledger/checkpoint and current build output. These support preservation within the stated scope, not a claim that all raw GIS was rehashed. No preservation defect identified in inspected evidence. Hashes were inspected, not recomputed. This review's metadata writes are an explicit post-submission transition; historical hashes remain unchanged.

Counters: **Luna corrections 4/4; Sol corrections 1/1; implementation builds 6/6; diagnostics 1/3; independent confirmation 0/1; total full builds 6/7; reserved attempts 0.** Review consumes zero attempts. Remaining diagnostic/confirmation capacity grants no new correction or acceptance.

Stop issue and dependent dispatch at **NEEDS USER DECISION**. Preserve build 6 and all history, preserve the guard, and keep the candidate unservable. No retry, additional diagnostic, confirmation, browser/product integration, further limit change or renaming to reset the budget follows from review. Bounded next action: coordinator handback for a user decision whether to stop or explicitly authorize a separately bounded approach to representable topology and outstanding offline gates. TVW-016+, topology-validation v2 and geographic/product preservation constraints remain unchanged.
