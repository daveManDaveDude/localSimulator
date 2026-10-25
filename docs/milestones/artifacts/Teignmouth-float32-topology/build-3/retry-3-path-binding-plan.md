# Retry-3 self-check — exact fixed-path binding plan

2026-10-25. Sol 6.1 medium planner `/root/sol_review17_plan`. **Planning only under disposition 74.** Read current W/S/H/P, review 16 and dispositions 65–66/74; searched current executable/config/test consumers and inspected the derived owner/handoff/start/helper paths.

**Feasible: four path-literal substitutions across W/S/H, with no behavior/schema change.** Propose only `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-3\` and its existing `run-1` leaf. No implementation, reservation, root preparation or execution is authorized by this plan. Coordinator acceptance, Luna implementation, independent Sol review and a separate coordinator gate remain required before a single later wrapper self-check.

## Exact current source/provenance boundary

Full SHA-256 values recalculated from actual current source:

| Label and exact workspace-relative path | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `3078e1df4bf89438208bbcfc09150dbce77f180259f847a84287892d26662989` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `9452b2b00f3c72b8bef5f9a2e5cab2992947d0072a71901710cac129057c0733` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `e3cdadced5d90a669155002870636610e77df68b8a013deeef187893fbd65e78` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

Review 16's accepted report hash is `184cb13cadbbd9a065a5abd560fc8beabe233b4900c0f632c24cda071fb8f4a6`; disposition 74 hash is `7cd52b89497016327bd8b912208bc01134cdbdc99ec29611627de144026119a6`. Review 16 accepts the actual current guarded reporting and retained nonzero completion/drain logic. **The earlier S digest beginning `957157…` remains unsaved/untraceable.** This plan does not reconstruct it, recover its bytes, assert a complete historical reaping delta or supply missing provenance. The future inverse proof below establishes only the exact new path delta from the four current hashes above.

Dispositions 65–66 provide the precedent for one exact four-literal binding, independent inverse proof and later separate wrapper gate. They authorized consumed retry-2, not reuse of its root or automatic selection of retry-3. Historical plans/reviews/dispositions/ledger facts remain immutable; coordinator may update current metadata separately after dispatch/review. No historical path strings or evidence are bulk-replaced.

## Observed root safety and required rechecks

Static `Test-Path` found retry-3 absent. A direct `.codex` child listing found no case-insensitive same-name entry, whether file or directory. `C:\`, `C:\vibe`, workspace and `.codex` were inspected as directories without a ReparsePoint attribute; `.codex` resolves to `C:\vibe\localSimulator\.codex`. This is a planning-time observation, not a guarantee against later races or concurrent replacement.

Before implementation/review handback and again before any separately authorized invocation, require the exact candidate root to remain absent, including case-distinct/case-folded aliases. Verify every existing ancestor remains canonical, within the workspace, a directory and without reparse/symlink redirection. An inaccessible or ambiguous check is refusal, never absence. Do not create a directory to test permissions or path agreement.

At the later invocation only, preserve W's current lexical/no-reparse/existing-root refusal and initial checks for caller, caller `.update`, fallback, handoff, handoff `.update`, consumed handoff, supervisor-start, wrapper logs and `run-1`. The absent root/leaf implies absence of all helper descendants; subsequent exclusive create/consume checks still apply. Parent existence at entry consumes/refuses the one-shot even if empty; no adoption, cleanup or retry reuse. Exclusive creation must win its own race. No stale/unowned file is removed.

## Four and only four source substitutions

| Current file/line and consumer | Exact old literal | Exact replacement |
| --- | --- | --- |
| W 23, self-check `$baseEvidence` | `.codex\build3-supervisor-selfcheck-retry-2` | `.codex\build3-supervisor-selfcheck-retry-3` |
| W 344, terminal fallback `$expectedRoot` | `.codex\build3-supervisor-selfcheck-retry-2` | `.codex\build3-supervisor-selfcheck-retry-3` |
| S 39, `SELF_ROOT` | `.codex/build3-supervisor-selfcheck-retry-2` | `.codex/build3-supervisor-selfcheck-retry-3` |
| H 17, `EVIDENCE` | `.codex/build3-supervisor-selfcheck-retry-2/run-1` | `.codex/build3-supervisor-selfcheck-retry-3/run-1` |

A repository source/config search found these four active literals and no additional executable root consumer; the targeted `pipeline/tests` search found no self-check root/script-specific assertion. All other matching old-root references are historical evidence/metadata/docs, which must stay unchanged. P's standalone root is `.codex/build3-runtime-preflight/run-1`, unrelated and unchanged. No test changes/runs are needed for this path-only change.

The patch must not otherwise reformat/re-encode files or change line endings. W's literal unsigned access masks, exact Caller/Handoff kind dispatcher and validators, PREPARED snapshot/hash/five-field transition, one-use flags, same-directory Move/fallback/error/cleanup logic stay byte-identical outside the two path spans. S's accepted retained-handle authentication, separate actual exit-7 observations, strict membership observations, release/drain, zero/empty/zero gate, tree probe and nested reporting guards stay byte-identical outside SELF_ROOT. H behavior stays byte-identical outside EVIDENCE. P remains wholly unchanged.

No automatic attempt numbering/search, arbitrary CLI/environment path, old-root fallback, root allowlist containing multiple retry slots, additional `run-N`, new schema/record/mode/phase/dependency/command/environment, privilege/access-right or deadline change.

## Derived cross-file contract to verify

| Records/operation | Agreement required after substitution |
| --- | --- |
| W caller ownership | Parent `caller-invocation.json` and `.update` derive from retry-3. Exact owned existing caller schema/wrapper/start/mode validation retained; no handoff/caller authority mixing. |
| W fallback | Fixed `caller-invocation.failure.json` derived parent equals W's **independent** retry-3 `$expectedRoot` allowlist. Keep self-check-only, exclusive failure-only creation and sticky exit 2; no write into retry-2/original root. |
| W handoff → S consumption | Parent `self-check-handoff.json` plus `.update` and consumed `self-check-handoff.consumed.json`. W's selected-mode Handoff expected path already derives from `$baseEvidence`; S `_handoff` at 577 onward derives from SELF_ROOT. Do not add another path literal or loosen ownership/hash/nonce/deadline/identity checks. |
| S startup → W | Parent `supervisor-script-start.json`; W reads the same path. Preserve parent-before-leaf ordering. Wrapper `supervisor.stdout.log`/`supervisor.stderr.log` stay in parent. |
| S invocation/evidence | S alone exclusively creates `SELF_RUN = SELF_ROOT / "run-1"`; leaf `invocation.json` and its existing `.pending` update path. New normal-completion/error checkpoints use the same record, not a new root/file. |
| S ↔ H auth/start | Leaf `nonzero-authorization.json`/`tree-root-authorization.json`, corresponding consumed forms, `nonzero-script-start.json`/`tree-root-script-start.json`. Both parent and child use the same exact leaf and current native/nonce/creation/QPC checks. |
| Helpers and logs | Leaf `nonzero-helper.json`, `tree-root-started.json`, `tree-child-started.json`, `nonzero.stdout.log`, `nonzero.stderr.log`, `tree.stdout.log`, `tree.stderr.log`; all still derived from SELF_RUN/EVIDENCE. Fixed commands/helper modes unchanged. |

All existing schema identifiers and field meanings remain unchanged. Newly generated caller/handoff path fields will name retry-3 from the exact constants; old JSON is never rewritten. New nonce/PID/creation/native/hash/QPC/exit values must come from the future real invocation. No identity/manifest/snapshot preparation is part of this binding.

## Immutable evidence baseline

All original/retry-1/retry-2 files were statically rehashed during this plan and match their accepted values. Old roots are expected to exist and must never satisfy new-slot records.

| File (under `.codex/`) | SHA-256 |
| --- | --- |
| Original `build3-supervisor-selfcheck/caller-invocation.json` | `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e` |
| Original `build3-supervisor-selfcheck/caller-invocation.json.update` | `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75` |
| Retry-1 caller | `f992b356191d202a5e2357cffb1d64d90b4dd7f8ac54cd0b76ab2e0d7540dcf3` |
| Retry-1 PREPARED handoff | `b73738fc81644b942ea4f84890146e1bdfc73d925005552cb34db1af05aadc79` |
| Retry-2 caller | `4dbb3ff5f821edefe0a9d5fa1c822ef7cb0d296f346853013d620a3abaf5f00e` |
| Retry-2 consumed handoff | `bb773f7991eaa34c9f87ede7df8dd48d4eea899fbbd711eea009e3f7631abb0c` |
| Retry-2 supervisor-start | `8ecc5f87c87c90b3f1b73e9bf07814b7b6409a308971a6c83751be09c4f058d5` |
| Retry-2 supervisor.stderr.log | `92875c22d9084e2f791f53e02c09bc03d6b2bd16f28655fcffa3be5380c3ba51` |
| Retry-2 run-1/invocation.json | `7b40f2f6f218e491034c6f621108faedf6d0137557379f80fa0802c2313ab592` |
| Retry-2 consumed nonzero authorization | `e448045f4930ff8ab2c47341daeabb63bd0cef8008f5265b1d344167d53548f8` |
| Retry-2 nonzero-helper.json | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| Retry-2 nonzero-script-start.json | `767458b7ce651898f16c7bec8c2d3370eeaaff4d1d1802663edf3b77b7b86d24` |
| Retry-2 supervisor.stdout.log, nonzero.stdout.log, nonzero.stderr.log (each empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Retry-2's eleven files remain consumed, immutable and **non-PASS**. Later static correction acceptance supplies no historical runtime success and does not identify what produced retry-2's nonzero accounting count. Preserve all failed bytes, directories, markers/logs and historical counters. No delete/move/promotion/reset/retrospective rehash-and-refresh of evidence or caller fields. Protected candidate/helper/builder/test/fixture/config/source/GIS/product bytes and all geographic/source/origin/domain/recipe/collision/numeric constraints remain unchanged.

## Luna static gates and exact inverse proof

After coordinator plan acceptance, Luna may implement only the four substitutions. Keep retry-3 absent; no operational call or dummy evidence. Record final W/S/H/P and all prior evidence hashes, source-match counts, root/ancestor/alias absence observations, exact commands/results and any preliminary gate failure.

Affected static checks: Ruff check and Ruff format check on changed S/H (unchanged P evidence may be reused with its exact hash), PowerShell AST parse without wrapper invocation, plus the following non-executing inverse proof. Embedded C# declarations do not change; reuse pinned compile-only evidence, or repeat only if specifically authorized without calling any method. No imports, tests, process probes or operational script execution.

Inverse proof, in memory only:

1. Read final W/S/H as exact bytes. Require exactly two occurrences of the new full root literal in W, one in S, one full new leaf literal in H; ensure no active retry-2 root literal remains in those executable files. Do not count/rewrite historical docs/evidence.
2. Reverse **only those exact new literal byte spans** to the old ones in the table, preserving every other byte including BOM/encoding/newlines. Do not write or execute reconstructed source.
3. Hash the reconstructed bytes. Required inverse results: W `3078e1df4bf89438208bbcfc09150dbce77f180259f847a84287892d26662989`; S `9452b2b00f3c72b8bef5f9a2e5cab2992947d0072a71901710cac129057c0733`; H `e3cdadced5d90a669155002870636610e77df68b8a013deeef187893fbd65e78`. P's full final hash must still be `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`.

These are acceptance requirements for the future patch, not a claim that prospective source bytes or hashes have already been generated. Never use `957157…`, the old pre-reaping S hash, or a reconstructed historical file as the inverse target. No reliable Git index diff is assumed.

## Independent Sol review matrix

| Criterion | Required independent static evidence |
| --- | --- |
| Exact revision/delta | Final hashes, exact occurrence counts and inverse hashes above; only four literal changes. Current accepted S baseline, no fabricated missing history. |
| All consumers/producer agreement | Whole derived path table traced through W/S/H, especially W's independent fallback allowlist, parent handoff/start versus S-created leaf, H consumed auth/marker paths and new normal-completion checkpoint's existing invocation path. |
| Existing safety | Exact Caller/Handoff ownership, PREPARED immutable fields/hash, one bound launcher transition, stale pending/fallback/consumed refusal, no reparse/adoption, exclusive writes/consumption and sticky failure unchanged. |
| Slot collision/aliases | New parent absent and no case-folded alias; all ancestors canonical/safe. Hypothetical occupied root/empty parent/stale child/unsafe ancestor refuses; no cleanup/unlock behavior. Old-root evidence cannot authenticate new-slot paths. |
| Accepted process semantics | Unsigned CreateFile masks, retained normal-pair handle/identity/exit proof, complete zero/empty/zero gate, primary/secondary reporting separation, tree probe/Jobs/cleanup and original inherited 10-second limit unchanged. No timeout reset/constant subtraction/forced cleanup-to-PASS. |
| Preservation/scope | P and all protected sources/candidate/test/config/evidence hashes unchanged; eleven consumed retry-2 files unchanged; new root absent through review; no test/doc/history rewrite, schema/mode/dependency/environment/root-category/command change. |
| Authorization boundary | Planning/static PASS is not a run. Coordinator acceptance/release, independent PASS and a separate coordinator execution gate required; no subsequent collection/build inference. |

Independent reviewer must not have implemented the path change. Static syntax/format PASS alone does not establish cross-file path correctness or actual 10-second completion/drain/containment behavior.

## Stop conditions and future gate boundary

Stop on source-hash drift, additional executable consumer, any need for more than four literal edits, inverse mismatch, unsafe/occupied/ambiguous retry-3 or ancestor, changed ownership/schema/path protocol, evidence drift, failed review or new behavioral defect. Return exact evidence for a bounded plan; no automatic retry/root selection or implementation broadening. No crash atomicity or concurrent-replacement guarantee is claimed.

This plan neither authorizes nor performs a wrapper self-check. Only a **separate coordinator gate after accepted implementation and independent PASS** may authorize exactly one W-driven self-check at retry-3. Its fresh original QPC clock remains **10 seconds total**, through the existing W → venv launcher → base → S → H chain, unchanged command/mode/identity/Job/termination/evidence gates. Preserve actual result and stop. Retry-3 becomes consumed on its owned preparation; no same-slot replay. Actual reaping/drain/persistence and runtime timing remain unmeasured here; 30-second runtime-profile fit is also unmeasured.

No preflight/runtime identity collection/verification, manifests, GIS/numerical/candidate build/reservation, serving/publication/browser action is authorized before or after a self-check by this plan/disposition 74. Candidate remains NO-GO/unservable, build 3 unreserved. No commit/push/merge or historical counter reset.

Planning consisted only of static document/source/evidence reads/searches, file hashing, directory/ancestor/absence inspection and writing this one plan. No source/tests/evidence/metadata edits, new root/record, parser/linters/compiler/tests/imports, process inspection/probes, wrapper/self-check/preflight/runtime or candidate/GIS/numerical/build/browser work occurred. Return this concrete plan hash to coordinator for acceptance; stop here.
