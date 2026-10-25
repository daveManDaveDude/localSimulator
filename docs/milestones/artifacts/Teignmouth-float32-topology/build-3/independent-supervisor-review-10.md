# Independent supervisor review 10 — W-only ownership correction

2026-10-25. Independent non-implementing Sol reviewer `/root/sol_review_face_diag`. Authority: disposition 60 and the review dispatch. Read disposition 60, review 9, the current checkpoint and accepted `post-review9-handoff-ownership-plan.md` (`1da1e35a4c95c946b423746decc6ef64ccedb469a1c78c67b1a0410745e5296e`), then inspected current W ownership/persistence, preparation/binding call sites, failure capture and cleanup. **FIX_REQUIRED: the handoff correction resolves review 9, but the proposed Caller payload lacks the plan's owner-field validation.**

The operational files have no reliable Git index baseline; no diff or exhaustive unrelated-workspace preservation claim is made. Scope evidence is current source inspection and the independently unchanged protected bindings below. This report authorizes no subsequent action.

## Current SHA-256 and preservation

| File relative to repository root | Independently calculated SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `3eef94ca3bfeee4dfc19c60e089e2e97a5d12eec8fa205c38e16e2533ddff613` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `17a7a347b175bfa3ad1a1dcbdc4167d3d4b1c8a73da0dc09d537ec1c6d4a8ef6` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `3419551b5c19e69c2487bb57c1bc49c102d4b7bfe1db1f93aea60cf038ebe05a` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| Candidate `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| Shared helper `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| Builder `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| Focused test `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| Fixture `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| Configuration `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |
| Original `.codex/build3-supervisor-selfcheck/caller-invocation.json` | `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e` |
| Original `.codex/build3-supervisor-selfcheck/caller-invocation.json.update` | `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75` |

S/H/P and all protected/evidence files match the accepted pre-correction bindings. W is the only changed submitted operational file evidenced by these hashes. `.codex/build3-supervisor-selfcheck-retry-1/` remains absent; no retry/evidence descendant was created during review.

## Concrete residual finding

**FIX_REQUIRED — validate proposed caller ownership as well as existing destination ownership.** W **189–203**, invoked at both **136** and **170**, checks the supplied `$Record.schema` and persisted `$existing.schema`, but its PID/start/mode predicates at **200–201** apply only to `$existing`. It does not require proposed `$Record.wrapperPid`, `$Record.startQpc` and `$Record.mode` to equal the current `$PID`, `$startQpc` and `$Mode`.

Static refusal case: an owned exact caller destination still contains the correct invocation; a supplied Caller payload retains the literal caller schema but changes its PID, start or mode. Both validations pass, exclusive pending creation/flush succeeds, and File.Move at **176** can replace the owned file with the different-owner payload. A later save would refuse that now-altered persisted ownership, but that does not prevent the earlier replacement. No such payload was executed or persisted by this review, and no claim is made that normal current telemetry updates intentionally alter those fields.

The accepted plan explicitly requires: “Supplied caller record still belongs to the current wrapper/start/mode.” Checking only the old file does not meet that condition. Require the proposed caller's immutable owner fields to match the trusted invocation in both validations, while allowing legitimate evolving telemetry. This is a narrow missing ownership guard, not a request to broaden paths, change schemas or relax the handoff checks. No correction is made or authorized here.

## Remaining plan cases

| Criterion | Static result and current W line references |
| --- | --- |
| Separate caller/handoff authority and fixed paths | **PASS:** explicit kind dispatch at 181–186; Caller exact path/schema checks 189–203; Handoff current-mode exact path/ownership checks 272–288. Caller→handoff, Handoff→caller, unknown kind, arbitrary sibling/consumed/fallback path are refused before pending creation. Proposed Caller owner fields remain the finding above. |
| Exclusive PREPARED handoff ownership | **PASS:** flags initialize false (1185–1189); exclusive write completes before ownership (1391–1392), scalar snapshot is separately copied (1393–1394), prepared hash/parsed identity are checked against trusted W locals (1395–1405). Failure is not adopted as a new baseline. |
| Both validations bind the same immutable prepared identity | **PASS:** Handoff validator at 279–299 requires owned existing unconsumed/no-start destination, captured digest before/after parsing, exact snapshot key/value comparison and correspondence to trusted constants/locals. Dispatcher invokes it before pending creation and immediately before move (136/170). Persisted destination is compared to PREPARED, not the already-mutated proposed payload. |
| Only five proposed changes / verified suspended launcher | **PASS:** 301–322 preserves exact keys and all immutable values; only status/PID/creation/image path/image hash may change. These are compared to verified native launcher identity and pinned executable/hash, with created=true, assigned=false, resumed=false. Integral values are compared without floating conversion; null/string/bool distinctions are retained. Repeated transition is refused by the bound flag. |
| Fixed pending and replacement semantics | **PASS:** kind/path context, stale pending refusal, exclusive CreateNew, positive pending ownership, flush/close, second ownership/reparse/file check and the same supported File.Move overwrite at 130–178. No delete/truncate/alternate-method retry. Initial one-use checks include handoff `.update` (1207/1222); bound flag is set only after successful move. No crash-atomicity or power-loss durability claim is made. |
| Correct call-site and launch ordering | **PASS:** Save-Caller explicitly selects Caller at 1107; the handoff selects Handoff at 1472, fixing review 9. Original deadline is checked before/after update. Move and its successful gate precede outer Job assignment (1482) and resume (1495). |
| Sticky structured errors and direct cleanup | **PASS:** handoff failures preserve actual kind/path/stage and secondary close errors (1132–1151), then rethrow from preparation/update (1408–1410/1478–1480). Persistence failure remains sticky through caller finalization. The catch reaches direct termination/wait/exit capture of a created unassigned launcher (1600–1619); final handles/clock/terminal fallback remain separately guarded. Later caller-save success cannot turn earlier handoff failure into PASS. |
| Existing retry/process/profile/build boundaries | **PASS retained static structure:** fixed W/S/H retry path, one-use nonce/identity/clock/launcher/base/Job gates, original 10/30/180-second budgets and 150-second numerical cutoff remain. S/H/P bytes are unchanged. No runtime/manifest/candidate policy or source/numerical change is evidenced. |

## Scope and disposition

This was static inspection/hashing only, plus writing this report. No source/ledger/checkpoint/manifest/original evidence was edited. No parsers, linters, compilers, tests, imports, wrapper/scripts, self-check/preflight/runtime/collection, manifest preparation, retry path, GIS/numerical/build or browser action was run or created. Any implementation-reported syntax/static PASS is not rerun here and cannot satisfy the missing ownership predicate.

**30-second fit remains unmeasured.** No actual persistence, native cleanup, self-check success, exit/timing, memory or runtime profile evidence is produced. File-hash ownership checks remain observational, not atomic exclusion of hostile concurrent replacement.

Return FIX_REQUIRED to the coordinator. This report grants no further correction, retry/self-check or dependent action; disposition 60 makes a failed review the end of this bounded allowance absent new user direction. Preserve all historical counters and original failed evidence, and the still-absent fresh retry root. Candidate remains **NO-GO and unservable**; build 3 remains **unreserved**.
