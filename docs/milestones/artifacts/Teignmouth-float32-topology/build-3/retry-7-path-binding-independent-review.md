# Independent actual-byte review — retry-7 path binding

2026-10-25. **FIX REQUIRED — handoff metadata only.** Issue `Teignmouth-float32-topology-representation-1`; independent non-implementing reviewer `/root/sol_retry6_path_plan_review`, under D148. The actual four-literal source patch passes the inspected scope/inverse/behavior criteria. One incorrect changed-byte offset in the exact-delta handoff must be reconciled before accepting that report. Do not edit source to match the erroneous offset. Actual model/effort telemetry is unknown. Stop for coordinator decision; no invocation or path work is authorized.

## Exact inputs and source proof

Independently hashed the reviewed handoff to **`d589edb59a5a9638f404aad4296aaca1aed161c6b61f8038e129362503bdc4ff`**, exactly the assigned binding. Independently read and hashed actual W/S/H/P, reversed only the four new literals in memory, and compared original versus inverse byte arrays to identify every changed byte:

| File | Actual final SHA-256 | Bytes | Exact inverse SHA-256 | Changed zero-based offsets |
| --- | --- | ---: | --- | --- |
| W | `842a599fda7d9082b56efb792b10154d3e9096af8ac755f16318777d1495eef8` |132204| `f600efc92fd040aa5b91cf543210be139ed50f895eba7d62c34175e73dc7dc8b` |932,17077|
| S | `8f4dbda2346db49a0b9cead30b33a8515879f9955bbec59d64e23386615f5016` |239737| `fda96d4edd66327e50c34ee1345d1a098aced4a7b58dcd1c088a4cd8c44c616f` |1469|
| H | `f9f48f34198fe54eab800e8d2bc619631c11ce8ed44751a24a2c126e316ed373` |12419| `75678b51d0e17d89862bf0a7ee3446014969ba73aae6cd31606288553b163e27` |385|
| P | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |unchanged|unchanged|none|

Every changed byte is ASCII54→55 (`6`→`7`). Whole-file inverse digests match the exact D148 baselines. This independently proves all non-literal source bytes/encoding/newlines remain accepted, particularly S's final strict wait/census correction at fda96d… rather than its pre-correction baseline. No reconstructed source was written or executed.

Static search across pipeline/scripts, pipeline/tests and config returns only W23/W344, S39 and H17. Current proposed-literal counts are **2/1/1**, old retry-6 counts **0/0/0**, P has no consumer; no additional consumer appeared in the searched scope. Final source digests all match the handoff.

## Actionable finding

**F1 — Incorrect H changed-digit byte offset in the handoff.** In `Exact byte delta and inverse proof`, the H17 row reports literal start344 and changed-digit offset**391**. The actual difference against the exact accepted H inverse is at zero-based byte**385**, value0x36→0x37. The literal-start344 is consistent with that digit being41 bytes into the parent literal; the `/run-1` leaf suffix follows it. Offset391 refers to the end of that leaf literal, not the changed retry digit.

**Required correction:** coordinator-authorized metadata-only correction or explicit authoritative reconciliation of that H row from391 to385, with a newly bound report if the handoff changes. Leave all W/S/H/P bytes untouched. Reuse the valid source inverse/static/preservation results at these unchanged bindings; this finding does not justify rerunning runtime, path or preservation work or altering source. The affected criterion is exact handoff byte-delta evidence. This is not an implementation behavior defect.

## Other criteria and evidence

| Criterion | Assessment |
| --- | --- |
| Four literal scope and accepted S | **PASS.** Whole-file inverses and exhaustive byte differences above establish exactly two W digits and one S/H digit, with no other delta. Strict private-error reset/immediate capture/terminal18, same-snapshot proof, default callers, bounds, wait/final census state machine, error/record/cleanup behavior and shared wait remain byte-identical to accepted final S. W diagnostics and H/P behavior remain unchanged except intended output roots. |
| Namespace/fallback integration | **PASS.** W23 baseEvidence and W344 independent fallback allowlist agree on retry7. S SELF_ROOT/SELF_RUN and H EVIDENCE agree on the same parent/leaf. Existing caller/update/failure, handoff/update/consumed/start/log and leaf invocation/pending/auth/consumption/start/marker/log derivations preserve accepted identity/nonce/QPC/ownership/exclusive-refusal contracts. No output schema/file/mode or direct-helper invocation was added. |
| Static gates | **Recorded PASS reviewed, not rerun.** The exact hash-bound handoff records S/H Ruff check `All checks passed!`, format-check `2 files already formatted`, and W-only AST output `PowerShell AST parse passed; W was not invoked`, with actual commands. These results bind the current source hashes and preserve the separate compile-only/runtime limitations. No lint/format/parser/compiler was run in this review. |
| Preservation evidence | **Recorded PASS reviewed, not independently traversed.** Handoff describes parsing the accepted53-row matrix and D129's17-row inventory, forming70 unique expected relative-name/hash pairs, then full-name/count/hash comparison. Exact output reports70 actual, zero missing/unlisted/changed and70/70 PASS; the seven population counts reconcile2+2+11+11+11+16+17. All six reported protected hashes match accepted candidate/topology/builder/test/fixture/config report bindings. No current evidence/protected-file rehash or traversal is claimed here. |
| Preservation limits | **PASS.** Only metadata/hash preservation is reported; consumed content diagnosis, rewriting/replay/cleanup or retrospective PASS is not authorized. Historical retries1–6 remain consumed/immutable/non-PASS. Any later missing/drifted prerequisite remains a stop. |
| Path/authority boundary | **PASS within available report evidence.** Handoff explicitly reports no retry7 target-root/path/ancestor/alias/absence inspection/reservation and claims no target availability. This reviewer performed none. The report and authorized static operations do not establish current target absence. Separate safe-ancestor/alias/containment/absence checks and immediate one-use coordinator gate remain future requirements. No root is selected/reserved by this source patch or review. |

The final source is suitable for acceptance once the metadata discrepancy is explicitly reconciled by the coordinator. This report itself does not accept the incorrect handoff row or grant the next action.

## Work and limits

Only D148/handoff/current-source reads/searches and hashes, in-memory exact literal inverse and byte-difference arithmetic, accepted report/matrix evidence review and this report write occurred. No source/evidence/checkpoint edits, consumed retry1–6 evidence contents, gate reruns, preservation traversal, tests/imports/parsers/compiler, root/path/ancestor/alias/absence work, process/runtime/self-check/preflight/build, browser/publication, commit/push/merge occurred. Only this review artifact was written.

No runtime efficacy, scheduling/census fit, hard wall-time, cleanup-duration, durable evidence or snapshot-incarnation identity is proved. The original10-second QPC bound, reserve/ownership/cleanup constraints, historical outer-exit/PID31876/provenance uncertainties and all counters remain. Candidate stays **NO-GO/unservable**, build3 unreserved, retry7 proposed/unselected/unreserved. **Stop for coordinator decision on F1.**
