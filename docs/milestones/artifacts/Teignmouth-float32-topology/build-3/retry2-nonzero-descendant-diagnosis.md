# Retry-2 nonzero-helper descendant observation — read-only diagnosis

2026-10-25. Sol 6.1 medium `/root/sol_review17_plan`, under disposition 67. **Retry-2 remains BLOCKED/non-PASS.** The assertion uses an insufficiently specific instantaneous Job accounting observation; preserved evidence cannot identify the allegedly running descendant. A minimal S-only helper-reaping/evidence correction is feasible, subject to a separately accepted bounded plan and independent review. No implementation, live-process inspection or operational probe occurred.

## Complete preserved evidence inspected

Read all retry-2 files: caller, consumed handoff, supervisor-start, supervisor stdout/stderr, run invocation, consumed nonzero authorization, nonzero helper/start markers, and both helper logs. Rehashed every file; all match disposition 67. No tree-root authorization/marker/log was present: the error occurs before that probe launches.

| Retry-2 file (relative to `.codex/build3-supervisor-selfcheck-retry-2/`) | SHA-256 |
| --- | --- |
| `caller-invocation.json` | `4dbb3ff5f821edefe0a9d5fa1c822ef7cb0d296f346853013d620a3abaf5f00e` |
| `self-check-handoff.consumed.json` | `bb773f7991eaa34c9f87ede7df8dd48d4eea899fbbd711eea009e3f7631abb0c` |
| `supervisor-script-start.json` | `8ecc5f87c87c90b3f1b73e9bf07814b7b6409a308971a6c83751be09c4f058d5` |
| `supervisor.stderr.log` | `92875c22d9084e2f791f53e02c09bc03d6b2bd16f28655fcffa3be5380c3ba51` |
| `run-1/invocation.json` | `7b40f2f6f218e491034c6f621108faedf6d0137557379f80fa0802c2313ab592` |
| `run-1/nonzero-authorization.consumed.json` | `e448045f4930ff8ab2c47341daeabb63bd0cef8008f5265b1d344167d53548f8` |
| `run-1/nonzero-helper.json` | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| `run-1/nonzero-script-start.json` | `767458b7ce651898f16c7bec8c2d3370eeaaff4d1d1802663edf3b77b7b86d24` |
| `supervisor.stdout.log`, `run-1/nonzero.stdout.log`, `run-1/nonzero.stderr.log` (each empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Current source hashes, independently recalculated: W `3078e1df4bf89438208bbcfc09150dbce77f180259f847a84287892d26662989`; S `2bae9a35ee91ca154bba19c0a3848b0bda2f46930f38e9090bd632ff5653300d`; H `e3cdadced5d90a669155002870636610e77df68b8a013deeef187893fbd65e78`; P `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`. W/S/H refer to the three existing `pipeline/scripts/*build3*` wrapper/supervisor/selfcheck files; P is runtime preflight. Source line references below use these hashes.

## Precisely which processes, Job and predicate

| Role | Preserved PID / creation FILETIME |
| --- | --- |
| W PowerShell wrapper | 27904 / 134373826648196070 |
| W's venv launcher for S | 2324 / 134373826658982900 |
| S base-interpreter script | 22844 / 134373826660203615 |
| S's venv launcher for nonzero H | 37852 / 134373826661390832 |
| H base-interpreter nonzero script | 32724 / 134373826661629982 |

Nonce `b5a7d4f83c3645f0be37d9db9ba4021c` and inherited QPC deadline 3004208976473 at frequency 10000000 agree across handoff/start/helper records. Original start is 3004108976473, giving 10 seconds total. Authenticated script/native identities distinguish launcher from interpreter; they are not the same PID.

S creates a new inner Job at `_selfcheck` before launching H; S does **not** assign itself to that new Job. `_launch_suspended` assigns H launcher 37852 to it before resume. Its interpreter child 32724 inherits that membership under the intended no-breakaway chain. W's outer Job contains its S launcher/base and their descendants; the inner Job is the helper subset. The supervisor/wrapper/outer launcher must not be subtracted from the inner count because they were never assigned to this inner Job. Microsoft describes nested Jobs as subset hierarchies with child accounting aggregated upward, not unrelated parent processes aggregated down. [Nested Jobs](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs)

At S 2315–2321, `_wait_process` waits on **normal["handle"]: the retained process handle for launcher PID 37852**. It is appended to `handles` at 2298 and not closed until `_selfcheck`'s final cleanup. This wait does not separately wait on H interpreter PID 32724. `_contained_interpreter_child`/`_verify_helper_start` earlier authenticated that script, but their temporary query handles were closed.

At 2323–2325, S reads the launcher exit and rejects timeout or any exit other than 7. Reaching the subsequent distinct error branch is source/evidence support that this guard accepted expected exit 7; however the normal-exit/telemetry locals were not persisted before raising. The helper marker alone records **intended** exit 7, not an independent OS exit observation.

At 2326–2327 the predicate is exactly `_job_active_count(kernel, job) != 0`. That function at 1972–1978 queries `JobObjectBasicAccountingInformation` for the **inner** Job and returns `info.ActiveProcesses`. Its structure at 123–133 matches the inspected documented field order. The branch queries **no PID set and no individual liveness**. It establishes only a nonzero returned integer. **The actual integer and contributing PID(s) are absent from the persisted evidence.** It cannot be retrospectively asserted to be 1, 2, 32724, 37852, S itself or an unexpected process.

This is not `_assert_tree_contained`'s separate escaped-descendant failure. That path compares a Toolhelp ancestry census with exact Job membership and emits `live descendant PID ... escaped the exact inner Job`. The actual error is a different accounting predicate after a launcher wait. `_wait_process` checks containment only after timed-out poll slices; an immediate signaled wait can return without another census. No sampled telemetry or final PID census from this precise stage was durably stored.

## Semantics: what is proved and what is not

Microsoft defines `ActiveProcesses` in terms of processes associated with the Job and notes decrement after termination and release of references. It is not a PID-specific proof of runnable work. S retains the exited launcher's handle across this check, and normal process/Job bookkeeping may not be interchangeable with a signaled launcher wait. That supplies a concrete plausible false-positive mechanism; it does not prove that retained handle caused this particular count. [JOBOBJECT_BASIC_ACCOUNTING_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information)

A terminated process object can remain because another process holds an open handle, and process termination does not automatically terminate its children. A wait on one process therefore neither proves its descendants are gone nor identifies a remaining Job member as running. [Terminating a Process](https://learn.microsoft.com/en-us/windows/win32/procthread/terminating-a-process)

H's `nonzero` branch writes its expected marker, sleeps at most 0.15 seconds within the inherited deadline, and returns 7. It does **not** spawn the child in the later `tree-root` branch. Thus the reviewed expected nonzero tree is the launcher/interpreter pair only. No actual evidence identifies an unexpected spawned/escaped process.

**Verdict on cause:** likely a too-early/coarse accounting assertion, but **not conclusively distinguishable** from a briefly late, still-contained known interpreter or another unexpected member with the recorded data. The assertion's phrase “descendant running” overstates what it measured. It is not evidence of an escaped process; it is also not sufficient evidence to declare a harmless false positive or retroactive PASS. Do not remove the zero-membership requirement or assume all counts are stale.

Final S cleanup requested Job termination and recorded `terminationConfirmed=true`, `activeProcessCountAfterRequest=0`, `deadlineReached=false`. This occurred **after** failure; final outer W termination is also confirmed, both script/launcher exits are 2, and elapsed wrapper time is about 1.345 seconds. TerminateJobObject acts on associated processes and nested child Jobs; successful cleanup may eliminate actual remaining work, or simply observe a now-empty Job. Later zero cannot reveal the earlier membership/liveness. [TerminateJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject)

## Concrete minimum repair/missing-evidence recommendation

Affected behavioral file: **S only**, limited to `_selfcheck` normal-helper completion/reaping and its evidence. H's nonzero behavior and W's ownership/interop fixes need no behavior change. Do not change shared build-dispatch acceptance or globally reinterpret `_job_active_count`. A future executable attempt will separately require a fresh fixed W/S/H path binding because retry-2 is consumed; this diagnosis does not choose/create a new slot.

Recommended bounded change for the next narrow plan:

1. Before the nonzero assertion can raise, persist its actual stage evidence in the **existing** invocation record: authenticated launcher/base-script identities, timeout result, observed launcher exit, helper-start/marker result, existing telemetry, raw inner Job accounting count and complete PID census. Record query failures/partial observations, not zero placeholders. Do not infer successful OS exit from the helper's JSON marker. Existing one-use schemas/record locations need not change; additional nested stage evidence uses the current invocation schema.
2. Explicitly observe both known launcher and authenticated interpreter termination/exit without confusing their handles. Retain/open an appropriate SYNCHRONIZE/query handle to the interpreter **while its authenticated PID/creation/native identity is still available**, rather than opening a possibly reused PID after launcher exit. Use the existing launcher handle, creation identities and exact inner Job membership. Waits must use the original deadline; observed code 7 is required for the normal helper's intended exit. An unavailable interpreter observation is a typed non-PASS, not an assumed exit.
3. Once the known normal pair's required termination/exit evidence is captured, close their owned handles exactly once and remove/invalidate them from final cleanup ownership. Do not retain completed-process references merely for later telemetry or close a handle still being waited on. Preserve scalar identities/exit observations in the invocation instead. Handle-close/query failure remains non-PASS. Existing `_verify_helper_start` temporary handles must not be reused after close.
4. Replace the single immediate accounting assertion with a **deadline-bounded normal drain/reconciliation**, not forced cleanup-to-PASS: query/persist raw ActiveProcesses and the complete inner PID list, continue existing exact containment checks, and allow known terminated-pair accounting to settle only within the original time. Wait/sleep slices are recomputed from remaining original time, with no fresh allowance or unbounded spin. An unexpected authenticated member/live descendant, unsafe identity reuse, unavailable membership/liveness, or deadline expiry fails and reaches existing cleanup. Do not subtract a constant, count S as an exempt inner member, or turn inaccessible queries into empty sets.
5. Normal-stage completion requires launcher/interpreter expected-exit evidence and an **observed zero inner accounting count plus empty complete inner PID census before deadline**, without using TerminateJobObject to manufacture that normal-stage result. Then and only then launch the existing deliberate tree probe. The tree probe still must prove its intended child started, exact containment and forced termination/zero remainder within the same 10-second total cap. No overall PASS after an unexpected normal-stage forced cleanup.
6. Store first/last drain observations, bounded summary/counts and any last nonempty member/liveness identities before raising, so a later failure can distinguish known terminated bookkeeping, actual late helper, unknown member and unavailable evidence. Keep primary error and final cleanup separately labeled. Preserve all original terminal persistence/ownership checks; no new evidence filename, generic process inspector, dependency, mode or live diagnostic phase.

Microsoft's Job PID list includes members of nested child Jobs, and its assigned/listed counts must be reconciled to obtain a complete enumeration. Reuse the existing bounded `_process_list` only with completeness/capacity checks; a truncated/failed query cannot support emptiness. [JOBOBJECT_BASIC_PROCESS_ID_LIST](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_process_id_list)

This design repairs the evidentiary/lifecycle gap without presuming which runtime hypothesis is true. Merely inserting a fixed sleep, deleting the assertion, accepting count-minus-one, or treating final termination as normal completion would weaken the self-check and is not recommended. Merely closing the launcher handle without confirming the interpreter and preserving membership evidence is also insufficient to establish descendant absence.

## Static acceptance, review and stops

A separately accepted implementation plan should identify exact S changes and any required existing Win32 query/synchronization access constants; no API probe is needed during planning. Independent non-implementing Sol review must trace:

- normal branch versus tree-root branch, launcher versus interpreter PID/creation/native/Job identities, exact process handle rights/lifetime and no double-close or reuse;
- stage evidence persisted before failure, raw count versus enumerated PIDs versus per-process wait/exit, complete-query refusal, no fabricated historical observations;
- known normal pair exits then handle release/drain; unknown/live/escaped/unavailable/late cases stay non-PASS; normal completion never forced into PASS;
- empty-count/empty-list requirement before tree launch, unchanged deliberate-child containment/termination proof and all final cleanup gates;
- original 10-second total inherited deadline through every wait/query/evidence operation, no new clock or 30-second/profile/build authorization;
- immutable retry-2/original/retry-1 evidence, unchanged H/W/P behavior except separately reviewed future slot binding, and protected candidate/source/test/config/product/geometry/recipe/numeric limits.

Static checks after a future authorized correction may verify syntax/format, but cannot prove Job observation timing. If a drain cannot fit alongside the tree probe within 10 seconds, retain non-PASS and return the actual evidence; no deadline increase or weaker proof is inferred. Stop for a need to change process-containment architecture, exclude real members, relax identity/termination checks, add a runtime diagnostic mode or touch candidate/GIS behavior. If exact pre-exit interpreter identity/handle acquisition cannot be established safely within S, return that concrete missing prerequisite for coordinator review before implementation.

No new self-check is authorized by this diagnosis. Coordinator must first accept a narrow plan, dispatch implementation, obtain independent PASS and reconcile a fresh exact evidence path under disposition 64. Then at most one wrapper invocation per reviewed cycle; preserve actual result and plan the next defect on failure. No collection/verification/manifests/candidate/GIS/numerical/build/browser/serving work follows, even if a later self-check passes. Candidate remains NO-GO/unservable and build 3 unreserved; historical counters stay unchanged.

Work comprised static source/document/evidence reads/searches, directory inspection, file hashing and official Microsoft documentation retrieval, plus writing this report. No code/evidence/checkpoint/ledger/other artifact edits, parser/linters/compiler/tests/imports, process inspection/runtime probe, wrapper/self-check/preflight, GIS/numerical/build or browser application work occurred. An initial process-termination documentation URL was unavailable; the official procthread page cited above was then read. All preserved evidence remains unchanged. Return to coordinator; stop here.
