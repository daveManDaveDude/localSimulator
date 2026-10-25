# S self-check tree wait/census boundary — focused correction plan

2026-10-25. Issue `Teignmouth-float32-topology-representation-1`; **PLAN ONLY** under disposition 130. Accepted diagnosis: `retry6-qpc-deadline-diagnosis.md`, SHA-256 `60070d106c7e81ea492e05591c3db16bbe3d25300466b9bce34072859c3ad220`. No source change, gate execution or further attempt is authorized here. Stop after independent plan review/coordinator consideration.

## Baseline and exact proposed scope

| Source | Required unchanged/current baseline SHA-256 |
| --- | --- |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff` |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `f600efc92fd040aa5b91cf543210be139ed50f895eba7d62c34175e73dc7dc8b` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `75678b51d0e17d89862bf0a7ee3446014969ba73aae6cd31606288553b163e27` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

Only S's self-check tree block **4059–4068**, after `_verify_helper_start` succeeds and before `root_marker_path` is set, may change after a separate implementation release. Replace its horizon/callback wiring with a small self-check-local closure and explicit completion gate. No edits to shared `_wait_process` (3427–3499), `_assert_tree_contained` (391–436), `_sample_job`, `_terminate_job`, the normal stage or any default/build/preflight caller. Existing self-check marker/native identity/membership/termination code from4069 onward remains byte-identical. No import, API, right, path literal, helper launch policy, file, schema version or W change is needed.

The reason for separating deadlines is established: the old local three-second horizon is passed as the census deadline; `_wait_process` may invoke containment after its last native wait crosses that horizon. Expiration of the deliberately limited wait should end the wait, while a still-required containment observation may use remaining **inherited** time. A real failed/incomplete/late containment observation remains a blocker.

## Explicit deadlines and sequence

Use existing `time.monotonic()` and inherited `deadline` only; do not create a new clock domain or relative total budget.

1. Set self-check-local `cleanup_reserve_seconds=1.0`, `containment_deadline=deadline-1.0`, `tree_wait_started=time.monotonic()` and `tree_cutoff=tree_wait_started+3.0`. Require `tree_cutoff < containment_deadline` before starting the tree wait; equality/insufficient time is BLOCKED, not a shorter successful probe. A clock exception also blocks. This keeps the full deliberate three-second wait and leaves a containment opportunity before the reserved second. The reserve is subtracted from the original deadline, not added runtime permission.
2. Pass **tree_cutoff** as `_wait_process`'s wait horizon, preserving its existing return contract. Pass a self-check-local mandatory containment closure in place of the current lambda. Its census receives **containment_deadline**, not tree_cutoff. Any optional sampling at this call site receives the same containment deadline so crossing the wait horizon does not deliberately hand it an expired bound; sample failure retains existing diagnostic-only handling. No other sampling or wait caller changes.
3. Every mandatory closure call checks current monotonic time strictly before containment_deadline, invokes existing `_assert_tree_contained(kernel, job, [tree["pid"]], containment_deadline)`, then checks time strictly before that same deadline again. A successful return after/equal cutoff is **late and BLOCKED**, even if the last native operation returned useful data. No exception is swallowed, retried or converted to an expected timeout. A closure completion counts only when both boundary checks and the complete existing ancestry/Job comparison succeeded.
4. Retain `_wait_process`'s false/true distinction: early process signal returns `tree_timeout=false` and retains the existing early-exit rejection. A true return means only that the deliberate wait ended at its horizon; it is not proof of containment. A callback may begin before or after tree_cutoff and complete after it, but must complete before containment_deadline. Crossing the local wait horizon alone does not invalidate an otherwise complete census under its expressly supplied later bound. Crossing the containment deadline always blocks.
5. After an expected `tree_timeout=true` return, require a fresh monotonic observation at/after tree_cutoff and strictly before containment_deadline. If the wait returned true only because its existing millisecond rounding left less than1ms before the horizon, do not sleep, spin or declare the horizon reached: fail closed for an unobserved horizon. Then perform **exactly one mandatory final containment closure call** before marker processing. Require that final call completed successfully before containment_deadline. This prevents a wait-only return, absent callback, stale successful census or incomplete final census from satisfying the tree gate.
6. Only then enter the unchanged marker/identity/exact child-and-launcher Job checks and termination/exit verification at4069 onward. The existing global deadline continues to bound those operations and final cleanup. Success still requires every existing gate, not just the final census. No result from finally cleanup can repair a missing/failed census.

The shared wait function can still call the mandatory closure after a native WAIT_TIMEOUT has crossed tree_cutoff. This is safe by design here because that closure has an independently explicit absolute bound inside the original budget. Its errors propagate; no blanket `TimeoutError` catch or policy exemption is proposed.

## Work/resource bounds and failure outcomes

The local closure has an explicit maximum **16 periodic calls plus one final call**. Count the periodic call before opening a snapshot; exceeding16 is a resource-limit BLOCKED outcome. The final call is separate and allowed exactly once after the horizon. This is a fail-closed resource guard on this one self-check call site; it does not relax any existing limit. Normal250ms wait cadence over3s ordinarily permits about12 iterations, but no exact scheduling/call count is assumed.

Each call uses the existing at-most65536-row Toolhelp census,64 ancestry passes, bounded Job query, snapshot finally-close and existing membership comparison. No new process scan algorithm, retry, API or right is introduced. No retained census rows/arrays are added to the record. Snapshot/API/clock errors, fixed-bound overflow, missing/unavailable proof, no reserve, periodic-call exhaustion, early exit, final census timeout and post-census late completion all remain BLOCKED. An earlier failed census cannot be overridden by a later successful one because failure immediately propagates.

Native calls, allocation, scheduling and persistence are not preemptible by these checks. The final census's post-check ensures at least one inherited second remained **at census completion**; it does not guarantee that later unchanged identity/marker checks or cleanup finish in one second. Those operations retain their original global deadline/finally rules. No hard wall-time, durable-record or cleanup-duration guarantee is claimed. If review requires a guarantee beyond that original process/API boundary, stop for a scope decision rather than enlarge the allowance or claim preemption.

## Observable proof in the existing S record

Within the same replacement block, add one fixed-size `treeProbeBoundary` group to the existing self-check `record`. This is an explicit additive diagnostic field in S's existing invocation JSON, not a new file/schema version, W caller field or acceptance substitute. It contains only fixed keys/scalars:

- Inherited absolute deadline, cleanup reserve1.0, containment deadline, wait start and wait horizon.
- Wait result (`not-started`, `waiting`, `expected-horizon`, `early-exit`, `failed`), current periodic count and successfully completed periodic count.
- Last periodic census start/end/status, and final census start/end/status (`not-started`, `running`, `complete`, `late`, `failed`, `unavailable`). No array of iterations, rows, exception stacks or arbitrary strings.
- Final completion boolean, set true only after the mandatory final call's successful return and post-deadline check; no null-as-success. Missing clocks remain null/unavailable and block proof.

Maintain mandatory local state independently of diagnostic field assignment. Initialize the bounded group before starting the wait; an allocation failure blocks startup of this proof. During exception recording, preserve the original exception with a bare rethrow after any best-effort status update; a secondary diagnostic assignment failure must not replace an existing census/API/clock failure. Do not catch `TimeoutError` to continue. The existing S catch/finally persistence (4184–4234) carries the group with BLOCKED/error/finallyTermination or PASS. No extra write, update or persistence operation is inserted before mandatory termination. A record/persistence failure is not acceptance proof. No record field is used to admit a result the mandatory local state rejected.

## Observable acceptance/review matrix

Independent static review must trace these exact cases:

| Trigger | Required result |
| --- | --- |
| Native wait crosses only3s horizon; census completes before containment deadline | Expected wait end may proceed only after the separate final complete census and every unchanged downstream gate. |
| Census begins before horizon and finishes after it but before containment deadline | May count as one periodic completion; still require final post-horizon census. |
| Wait returns before horizon through sub-ms rounding | BLOCKED; no sleep/spin/assumed horizon observation. |
| Root signals before intended timeout | Existing early-exit rejection; no final proof-to-PASS. |
| Missing callback, zero periodic completions or local wait-only true | Never sufficient; final census remains mandatory. No invented historical completion. |
| Snapshot incomplete/error, membership rejection, clock unavailable, bound overflow | Original exception/rejection propagates; BLOCKED and finally cleanup. |
| Final census begins late or returns at/after containment deadline | BLOCKED even when native work returned; completion remains false. |
| Less than full3s plus reserve/opportunity remains | BLOCKED before wait; no global/local deadline increase or shortened successful probe. |
| Periodic count exceeds16 or final call attempted twice | BLOCKED before another census. |
| Census succeeds but marker/native identity/Job/termination/exit check fails | Existing rejection; no cleanup-to-PASS or partial evidence promotion. |
| Diagnostic/status/persistence failure while handling primary census error | Preserve primary error and existing mandatory cleanup; no acceptance claim. |

No callback completion proves snapshot PID incarnation association; keep current exact identity/Job validation and the existing limitations. In particular, the retry-6 residual PID31876 remains unidentified and cannot be exempted or attributed to a process class.

## Preservation, reusable evidence and later gates

The retry-6 diagnosis and consumed records already prove the normal stage's actual exit7/7, complete zero/empty/zero and the specific local-horizon error in that attempt. Reuse them for diagnosis and unchanged-branch review only; they cannot supply a later attempt's containment/final/marker proof. The accepted W diagnostic and four-literal path implementation reviews remain valid for unchanged bytes. Existing W AST/C# compile-only evidence can be reused because W/interop are unchanged. S normal/identity/cleanup implementation evidence remains reusable only for byte-identical spans; new behavior requires independent actual-byte review. No runtime fit or correction efficacy is already proved.

After separate plan PASS and coordinator release, Luna edits only the specified S block and records a tight diff, final S hash and exact in-memory inverse restoring the full baseline S hash. W/H/P and all path literals remain unchanged. Proposed later static gates, only if expressly released, are existing Ruff check/format-check for S and source/hash/inverse/branch review. No tests, imports, project execution or self-check are part of implementation/static review. Do not reformat unrelated bytes or alter a source to make a proof script pass.

Preserve all original/retry1–6 evidence: the accepted53 prior files plus the17 retry-6 files, **70 total**, with exact names/counts/hashes. Six protected source/config/test bindings remain unchanged. A later expressly released read-only preservation gate compares the complete accepted matrices; no consumed evidence content is rewritten, normalized, repaired or replayed. Missing authorization/check or any drift is a stop. All historic issue/attempt/correction budgets and counters carry forward without reset.

This plan retains consumed retry-6 literals deliberately. Neither current nor corrected source may be invoked against that root. Any future fresh-path work requires separate authorization, plan/review, actual-byte acceptance and immediate one-use coordinator gating. No retry-7 path is proposed, selected, probed, reserved or created here. Candidate stays NO-GO/unservable and build3 unreserved; no preflight, build, GIS/numerical/product/serving/publication authority follows.

## Planning handback

Only disposition/source reads and this plan artifact write occurred. No source/evidence/checkpoint edits, tests/imports/linter/parser/compiler, process/runtime inspection, resource probe, path/root work, wrapper/self-check/preflight or invocation occurred. No acceptance of new bytes or successful check is claimed. Stop for a separate independent Sol plan review and coordinator decision. If the required state/record/timing behavior cannot fit this one S-only block without changing shared callers or existing proof/cleanup semantics, report that blocker rather than broaden implementation.
