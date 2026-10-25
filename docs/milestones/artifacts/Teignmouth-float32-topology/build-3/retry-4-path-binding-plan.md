# Retry-4 wrapper self-check — exact fixed-path plan

2026-10-25. Sol 6.1 medium planner `/root/sol_review17_plan`. Planning only under disposition 85, following accepted independent review 19.

**Feasible: four exact literal substitutions in W/S/H only.** Propose `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-4\` and its existing `run-1` leaf. No root/record is created by this plan. Coordinator acceptance, Luna implementation, independent Sol PASS and a separate coordinator gate are required before exactly one later wrapper self-check. This plan grants no operation.

## Current accepted bytes and authority

Read disposition 85/review 19 and actual W/S/H/P; searched executable/config/test consumers and inspected current one-shot validation/derived paths. Full source SHA-256 values were recalculated:

| File | Current hash and required future inverse baseline |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `c3f1f49cb574793c1cdbc2d905fd3d36f646b6f32ffb7c200a96c9792d5ce84f` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `886280c5c5aeaf519929a5b6b1fa3c78c72a9f7a6874fbd8c4d60f09abdbb7e6` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `cf1145b33397066559b89c11aa1cb0ebcf4d6d4d470f6521d96fe9e1f4ecccab` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` — wholly unchanged | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

Disposition 85 hash: `9f27cfa75e4b6c85bb5b4cf711ad63aa97fc5ab5aca9d39b771dcfe25952e62f`. Review 19 accepted report hash: `936a9e5a9a013d8716136de3ba03162cd2cf41e25829c05ad17030c3182c1e83`. Its static acceptance covers the direct mandatory close before optional telemetry and observable path/file-metadata checks before hash promotion. It is not a runtime closure/diagnostic/timing PASS.

Use only the actual current S hash above for the new path inverse. Historical S `957157…` remains unsaved/untraceable; neither this plan nor a future inverse supplies its bytes, repairs that provenance or creates a reliable Git index history. The prior outer `pwsh` exit **1** versus retained internal launcher/supervisor exit **2** remains separate and unresolved. Do not silently attribute or repair it during path binding.

## Observed absence/ancestors and required future refusal

Static Test-Path found retry-4 absent. `.codex` enumeration found no file/directory with the same case-insensitive name. `C:\`, `C:\vibe`, workspace and `.codex` are existing directories with no ReparsePoint attribute; `.codex` resolves exactly to `C:\vibe\localSimulator\.codex`. These are current read-only observations, not a concurrent-replacement guarantee.

Require the exact target still absent, alias-free and safe at implementation/review handback and again immediately before any separately authorized invocation. Recheck canonical workspace containment, each existing ancestor/type/reparse status, and case-distinct/case-folded collision. Any inaccessible/ambiguous check is refusal, not absence. Do not create a dummy directory or record to test the path.

Preserve W's initial refusal when the fixed parent already exists, including an empty parent. Keep its caller/update/fallback/handoff/handoff-update/consumed/start/log/run checks and exclusive creation. An absent parent and leaf imply absent fixed descendants, but later exclusive operations still enforce ownership against races. No deletion, adoption or auto-selected alternative on collision.

## Exactly four substitutions and their counts

| Current consumer/line | Old full literal | New full literal | Count |
| --- | --- | --- | --- |
| W 23, self-check `$baseEvidence` | `.codex\build3-supervisor-selfcheck-retry-3` | `.codex\build3-supervisor-selfcheck-retry-4` | 1 |
| W 344, fallback `$expectedRoot` | `.codex\build3-supervisor-selfcheck-retry-3` | `.codex\build3-supervisor-selfcheck-retry-4` | 1 |
| S 39, `SELF_ROOT` | `.codex/build3-supervisor-selfcheck-retry-3` | `.codex/build3-supervisor-selfcheck-retry-4` | 1 |
| H 17, `EVIDENCE` | `.codex/build3-supervisor-selfcheck-retry-3/run-1` | `.codex/build3-supervisor-selfcheck-retry-4/run-1` | 1 |

The executable/config search found only these four active full-root literals. No targeted self-check root/script assertion was found in `pipeline/tests`; no test edit/run is proposed. P has its unrelated standalone-preflight root, unchanged. W's mode-specific Handoff expected path already derives from `$baseEvidence`; changing that validation logic would be out of scope.

Change no other bytes, encoding/BOM/newlines or formatting. Keep the accepted unsigned CreateFile access constants, separate exact Caller/Handoff ownership, PREPARED snapshot/hash and five-field launcher transition, same-directory replacement, error/fallback, native identity/containment/Job/cleanup clocks, S retained nonzero handles/exit proof/census/reaping/tree gates and guarded error reporting intact. Preserve the newly accepted diagnostic single-close ordering, image endpoint/metadata comparability, partial states and all atomicity/mapped-image limitations. Every unexpected PID remains unconditionally rejected; no guessed auxiliary-class exemption.

No new schema/record name/mode/phase/dependency/command/environment/native flags/access rights or runtime-root category. No automatic counter/root search, multiple-slot allowlist, arbitrary path input, old-root fallback or `run-2`. Historical docs/reviews/evidence remain unchanged; coordinator may separately update current metadata after dispatch/review, without rewriting historical path references.

## Full derived producer/consumer agreement

| Path/authority | Contract after four substitutions |
| --- | --- |
| W caller | Retry-4 parent `caller-invocation.json` and exclusive `.update`; exact proposed/persisted literal schema/wrapper PID/start/mode and owned regular destination validation unchanged. |
| W terminal fallback | Fixed parent `caller-invocation.failure.json`; its independent allowlist root must also be retry-4. Failure-only exclusive write, existing schema, sticky exit 2 and no caller/pending overwrite remain. |
| W → S handoff | Parent `self-check-handoff.json`/`.update`; S consumes to `self-check-handoff.consumed.json`. Exact selected-mode path, separate ownership/immutable identity/hash/nonce/clock/verified suspended-launcher transition preserved. |
| S → W supervisor startup/stdio | Parent `supervisor-script-start.json`, `supervisor.stdout.log`, `supervisor.stderr.log`. S `_startup_record_path`/`_handoff` and W readers agree. Do not put startup/handoff inside an initially absent leaf. |
| S-owned leaf/checkpoints | `SELF_RUN = SELF_ROOT / "run-1"`; S alone creates it exclusively. Existing `invocation.json`/`.pending` holds normal completion/snapshot/member details/error evidence; no new root or filename for recent diagnostics. |
| S ↔ H helper authorization | Leaf `nonzero-authorization.json`/`tree-root-authorization.json` and matching consumed files; native launcher/interpreter/nonce/creation/QPC checks still bind the same exact leaf. |
| Helper markers/stdio | Leaf `nonzero-script-start.json`, `tree-root-script-start.json`, `nonzero-helper.json`, `tree-root-started.json`, `tree-child-started.json`, plus `nonzero.stdout.log`, `nonzero.stderr.log`, `tree.stdout.log`, `tree.stderr.log`, derived from SELF_RUN/EVIDENCE. |

New payload paths are generated from the new constants only during a later real invocation. Do not copy old caller/handoff/auth records, identities, nonces, QPC times, exits or hashes into a new slot. No source/runtime manifest or reservation snapshot is prepared by this step. Runtime-preflight/build/source/geographic paths remain unchanged.

## All consumed evidence and protected bytes

All **26** saved files under the four old roots were enumerated/rehashed during this plan and match their accepted matrices:

| Immutable root under `.codex/` | Files | Accepted full hash-matrix reference |
| --- | --- | --- |
| `build3-supervisor-selfcheck/` | 2 | Disposition 56 / review 19 original caller/pending bindings |
| `build3-supervisor-selfcheck-retry-1/` | 2 | Disposition 63 / review 19 caller/PREPARED handoff bindings |
| `build3-supervisor-selfcheck-retry-2/` | 11 | Disposition 67 / review 19 complete retry-2 matrix |
| `build3-supervisor-selfcheck-retry-3/` | 11 | Disposition 78 / review 19 complete retry-3 matrix |

Key independently confirmed anchors: original caller/pending `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e` / `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75`; retry-1 caller/handoff `f992b356191d202a5e2357cffb1d64d90b4dd7f8ac54cd0b76ab2e0d7540dcf3` / `b73738fc81644b942ea4f84890146e1bdfc73d925005552cb34db1af05aadc79`; retry-2 caller/invocation `4dbb3ff5f821edefe0a9d5fa1c822ef7cb0d296f346853013d620a3abaf5f00e` / `7b40f2f6f218e491034c6f621108faedf6d0137557379f80fa0802c2313ab592`; retry-3 caller/invocation `f1bf3a880a821626daef625f60459d037a8aa9509246e401a06f9440cb8134d6` / `dcf98d8471df615acbaa74d3eece7f8a774e86cac22b0864931e556f2ae627e5`. Anchor checks do not replace the required all-file comparison at handback/review.

All 26 files, directories, logs/empty logs/markers/consumed/pending records remain immutable, consumed and non-PASS. No move/delete/promotion/reset/repair, no reclassification after later PASS, no same-slot replay. Existing old roots are expected and never satisfy retry-4's authority. Historical evidence hashes/counters and source/GIS/product/candidate/helper/builder/test/fixture/config bytes, source/origin/domain/recipe/collision/numerical/geographic limits remain protected. Preserve pending AOI/not_checked status and accepted viewer/synthetic behavior.

## Luna static gates and inverse proof

After coordinator acceptance/release, Luna edits only the four spans. Keep retry-4 absent during implementation/review. Run only affected static gates authorized for this correction: Ruff check/format check on changed S/H, PowerShell AST parse without invoking W, and in-memory byte inverse/hash proof. Unchanged P and C# declarations may reuse pinned prior static evidence; no methods are invoked if specifically authorized compile-only evidence is repeated. No imports/tests/probes, operational script or dummy evidence.

Inverse acceptance requirements:

1. Read final source bytes without executing/importing. Require exactly two new full root occurrences in W, one new full root in S, and one full new leaf in H, with no active retry-3 literal left in those executable files.
2. Reverse **only those exact byte spans** in memory, preserving every other byte/BOM/encoding/newline. Do not write reconstructed source or perform substitutions in docs/evidence.
3. Required inverse W/S/H hashes are precisely the full current baseline hashes in the first table; P's final full hash must remain unchanged. In particular, S inverse must equal `886280c5c5aeaf519929a5b6b1fa3c78c72a9f7a6874fbd8c4d60f09abdbb7e6`, not pre-diagnostic S, missing `957157…` or another historical revision.

These are requirements for a future patch, not a claim prospective bytes/hashes were generated now. No reliable Git index delta is assumed for the untracked operational files. Handback reports exact final/inverse hashes, occurrence counts, exact static commands/results/preliminary failures, P/protected hashes, all 26 evidence hashes/file counts and new-root/alias/ancestor absence observations.

## Independent Sol review matrix

| Criterion | Required actual-byte/static proof |
| --- | --- |
| Exact delta/revision | Four literal substitutions only; full current/final/inverse bindings and counts. Preserve current accepted diagnostic/reporting code and unresolved history limitation. |
| Producer/consumer agreement | Every row of the cross-file table traced; W independent fallback allowlist updated as well as base root; S parent handoff/start versus leaf creation; H markers/auth/stdio agreement. |
| One-use/collision/safety | Retry-4 absent with no case-folded alias; ancestors canonical directories/no reparse. Occupied/unsafe/inaccessible slot, stale pending/fallback/consumed/start/leaf refuses without adoption/cleanup. |
| Ownership/persistence | Caller and Handoff exact validators/kinds remain disjoint; prepared identity/hash/nonce/native transition checks and exclusive fallback unchanged. Old records cannot authenticate new slot. |
| Accepted semantic gates | Actual exit-7 proof, complete primary capture/zero-empty-zero, unconditional unexpected-ID BLOCKED, same-handle details/cap/close/metadata partial semantics, later tree/Jobs/cleanup/10-second total all unchanged. No constant subtraction, forced cleanup-to-PASS or source/class allowance. |
| Preservation | Unchanged P/protected files and every one of 26 old evidence files; retry-4 absent through review. No schema/mode/command/environment/root-category/dependency/data/tests/history edits. |
| Authority | Reviewer's independent PASS is static only. Separate coordinator gate required before any one-shot; no post-self-check collection/build authority. |

Reviewer must be a non-implementing Sol session. Syntax/format/inverse PASS alone does not demonstrate live diagnostic coverage, CloseHandle success, image stability, persistence, containment or actual 10-second fit. The separate 30-second runtime-profile fit also remains unmeasured.

## Stops and no-execution handback

Stop on baseline/evidence drift, unexpected additional consumer, more than four required literal edits, inverse mismatch, alias/ancestor/root collision or unsafe/unreadable path, changed ownership/protocol, review failure or new behavioral need. Return the exact issue for a bounded plan rather than broadening or selecting retry-5 automatically. No runtime source/class exemptions, atomicity/mapped-image claim or reconstruction of missing S history.

This plan does not authorize a run. After coordinator acceptance, Luna implementation and independent PASS, a **separate coordinator gate** may authorize exactly one reviewed W-driven self-check at retry-4 with its own original **10-second total QPC** deadline. Preserve actual outer/internal exits and all evidence; stop afterward, and plan/review any next defect before another invocation. A future PASS does not resolve historical outer exit1/internal2 or retroactively pass old slots.

No self-check now; no collection/verification/preflight/manifests/GIS/numerical/candidate build/reservation/serving/publication/browser step before or after a self-check under this plan. Candidate remains NO-GO/unservable, build 3 unreserved; counters and limits unchanged. No commit/push/merge.

Planning comprised static source/document reads/searches, hashing and directory/ancestor/alias/absence inspection, plus writing this plan. No code/evidence/checkpoint/ledger/test edits, root creation, parser/linters/compiler/tests/imports/probes/process inspection, wrapper/runtime/self-check or other operational/evidence action occurred. Return plan SHA for coordinator acceptance and stop.
