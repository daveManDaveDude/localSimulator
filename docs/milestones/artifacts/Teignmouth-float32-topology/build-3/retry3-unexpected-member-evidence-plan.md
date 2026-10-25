# Unexpected inner Job members — bounded S-only diagnostic evidence plan

2026-10-25. Sol 6.1 medium planner `/root/sol_review17_plan`. Planning only under disposition 79, accepting diagnosis SHA-256 `68723a79fc0f6c470d3254d6a893fbd1a4593ef5c09704af994d058ef8c0c6af`.

**Feasible in S only without changing rejection or acceptance.** Enrich an already captured complete inner-Job snapshot with immediate bounded member-detail observations. They remain diagnostic, never authority to admit a process. No implementation, evidence/root preparation, probe or operation is authorized by this plan. Stop for coordinator acceptance before dispatch.

## Exact current baseline and hard boundaries

Read disposition 79 and actual S API bindings, same-handle identity routine, `_selfcheck_job_snapshot`, normal-stage capture/checkpoint code and rejection/drain predicates. Recalculated source hashes match the task packet:

| File | SHA-256 |
| --- | --- |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `d498bc294390d8645c6acc59773ba50f417493926d8bbfb3564d34504e8a407a` |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `c3f1f49cb574793c1cdbc2d905fd3d36f646b6f32ffb7c200a96c9792d5ce84f` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `cf1145b33397066559b89c11aa1cb0ebcf4d6d4d470f6521d96fe9e1f4ecccab` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| Disposition 79 | `2368bbc687fe19674f383f694fa7f42780949fa9c0e58a45dd40884772b5c4ce` |

Only S may change. Preserve W/H/P, fixed retry-3 path, exact record names/schema IDs, commands/environment/creation flags, existing native API declarations/rights, modes/roots/dependencies, caller/handoff/type/path fixes, nonzero actual exits 7, authenticated handles, complete census and zero/empty/zero gate, containment/cleanup/tree-probe behavior and original inherited 10-second deadline. No signature/path/class/console-host allowlist, constant subtraction, grace for unknown processes or success after forced normal cleanup.

Retry-3 remains immutable/consumed/non-PASS at the eleven hashes in disposition 78 and the accepted diagnosis, including caller `f1bf3a880a821626daef625f60459d037a8aa9509246e401a06f9440cb8134d6` and invocation `dcf98d8471df615acbaa74d3eece7f8a774e86cac22b0864931e556f2ae627e5`. Prior retry/original evidence also stays immutable. This plan cannot identify historical PID 20712; no current PID lookup is permitted. Outer command exit **1** versus recorded supervisor/launcher **2** remains unresolved and separate. The unsaved/untraceable historical S `957157…` limitation remains.

## Exact touched functions and ordering

Add one private S helper, `_observe_selfcheck_unexpected_members(kernel, job, deadline, snapshot)`, with private small per-query routines local to it if needed. Modify only the tail of `_selfcheck_job_snapshot` (current 2048–2270) to call it and attach its diagnostic result. Existing normal-stage checkpoint/retain/exception logic already serializes the snapshot into `normalHelperCompletion.firstSnapshot`/`latestSnapshot` in the existing `run-1/invocation.json`; no new call site, file or reporting mode is needed.

Required order:

1. Preserve the existing primary accounting-before → complete PID-census → accounting-after sequence **unchanged**, including strict buffer/assigned/listed/duplicate/range/status/deadline rules. Complete the existing snapshot dictionary, including its original end timestamp, complete flag and original `unexpectedPids`, before any diagnostic process handle is opened.
2. Invoke enrichment only when that snapshot is complete, the exact owned inner Job is available and its existing `unexpectedPids` list is nonempty. Incomplete snapshots already fail; do not inspect partial-list PIDs or widen the target to process names/host enumeration. Empty/unknown cases can receive a small not-needed/not-eligible status, but no raw-query field changes.
3. Immediately observe selected unexpected PIDs **before JSON persistence or rejection**. The original snapshot's count/set/timestamps remain authoritative. Detail timestamps cover a later interval, clearly distinct from the census. Do not move diagnostic work inside its accounting envelope, recensus until quiet, replace the original list or mark a disappeared member absent from that earlier sample.
4. Attach a nested `unexpectedMemberDetails` result under that snapshot in a fully guarded best-effort block. Then return the original snapshot to the existing `retain_snapshot` → persistence → rejection path. Existing `unexpectedPids` rejection remains unconditional and sticky; a later exception-checkpoint zero/classification/vanished member cannot clear it or reach the tree probe.

Do not modify shared `_process_identity`, `_process_identity_from_handle`, `_process_list`, acceptance helpers, Job setup, waits, handle-release/drain or outer exception semantics. The new helper uses existing primitives but records partial fields separately instead of the all-or-raise identity helper, which would lose creation/liveness evidence if image hashing failed.

## Bounded fields inside the existing record

The new nested result contains: `status`, diagnostic start/end timestamps, `originalSnapshotPhase`, `sourceCensusComplete`, `eligiblePidCount`, `attemptedPidCount`, `detailLimit=8`, `omittedDetailCount`, `deadlineReached`, `observations`, and best-effort diagnostic errors. The cap limits detail work **only**: original census/unknown-PID set remains complete and is never truncated for acceptance. Select the first eight existing unexpected IDs in deterministic numeric order; no preferred/familiar executable filter. Process each selected PID once per snapshot, no open/requery retries.

Each observation has:

- original `censusPid` and source snapshot timing, plus detail query timing; an explicit `censusIdentityAssociation=unproven` unless an already captured immutable creation identity genuinely establishes an earlier same-process association (this change adds no historical identity);
- `open` status/error and requested existing access mask; no raw handle value as identity;
- same-handle `membershipBefore`/`membershipAfter` with observed Boolean or null/status/error; **exact supplied inner Job**, never `IsProcessInJob(handle, None)`;
- `creationFileTime`, `exitFileTime`, native image raw/canonical path and image SHA-256, each with its own status/error so partial observations survive;
- nonblocking process wait return/signaled status and raw GetExitCodeProcess value/status/error; interpretation labeled only at that observation, not at the earlier census;
- diagnostic handle ownership/close-attempt/success status and structured close error or unknown release state;
- `parentOrigin`/class authentication explicitly unestablished: no guessed parent, console-host classification, trusted basename or approved-process designation.

Additional fields use existing invocation schema/nested snapshot maps. Do not introduce another schema ID, filename, artifact directory, process inspector or event stream. First/latest snapshots remain distinct. No full history/allocation growth beyond the per-snapshot eight-row cap; existing first/latest retention is sufficient.

## Per-member native query order and semantics

For a selected original PID, check the original deadline before every operation and after any potentially blocking/native/filesystem work. Use **only** the API bindings/rights already present in S:

1. Prepare the minimal row, then `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_QUERY_INFORMATION | SYNCHRONIZE, False, pid)` once. These are the query/wait rights already used for retained interpreter observation; no terminate/VM/debug/all-access request, privilege change or inherited handle.
2. On successful open, enter a `try/finally` owning **that exact handle** immediately, before fallible allocations/reporting. Query exact inner Job membership; if unavailable or false, record unknown/mismatch and do not assert that this is the original census incarnation. Do not follow some other PID, reopen, query by name or classify an escape from this mismatch alone.
3. Capture GetProcessTimes creation/exit FILETIME, `WaitForSingleObject(handle, 0)` and GetExitCodeProcess promptly, before slower path resolution/hashing. Keep their individual results/timestamps. A zero-time wait is an observation, not a new wait budget. WAIT_OBJECT_0 means signaled at that call; WAIT_TIMEOUT means nonsignaled at that call; errors mean unknown. Preserve the raw exit value even if it equals STILL_ACTIVE (259); do not infer liveness from that sentinel alone when a separate signaled observation says the object terminated. Inconsistent/transitional results stay explicitly ambiguous.
4. QueryFullProcessImageNameW on the **same** handle, bounded by the existing 32768-character buffer. Preserve returned path before canonical resolution. Reuse existing canonical-file and `_sha256(path, deadline)` behavior without adding any root/class trust; missing/unsafe/unreadable/changing image observations remain partial diagnostics. Hash only while original time remains; check between existing hash chunks. A matching familiar image/hash is evidence about the opened object, not admission authority.
5. Recheck GetProcessTimes creation and exact Job membership on that same handle if time remains; record inability due to expiry as unknown. Handle identity is stable while held, but creation time/membership after a census do not authenticate the census's earlier incarnation automatically. A newly opened PID may have been reused before the open; even true membership now must be labeled contemporaneous membership rather than proof of the historical process. Do not reopen a closed handle/PID to manufacture continuity.
6. In `finally`, make exactly one CloseHandle attempt for every successfully opened diagnostic handle, regardless of query/serialization/allocation failure. Record successful release only if CloseHandle succeeds. False/error is `close-failed/release-unconfirmed`, not “closed”; no retry/double-close or transfer to the normal-pair `handles` list. Diagnostic close failure is a fault on an already blocked observation, never PASS. Existing final process/Job cleanup remains mandatory; do not claim it proves the diagnostic handle closed. If the OS ultimately releases resources at S exit, that is not an observed CloseHandle success.

An open failure (including access denied, invalid/not-found-like errors or expiry) does not prove the earlier PID was exited, harmless, escaped or reused. Save the actual error/unknown state. No native calls, handles or errors can retroactively rewrite the original complete snapshot. Opening a diagnostic handle may itself retain an object; preserve timing/order rather than claim observation is lifetime-neutral.

No Toolhelp/host-wide parent census, WMI, tasklist, debugger, ETW or new native API is part of this change. S's existing required containment census is unchanged. Parent/origin/class identification may therefore remain incomplete even with a captured image; the result cannot authorize a new trusted auxiliary-process class.

## Time/coverage bounds and in-interval census decision

Use only the inherited absolute deadline supplied to the snapshot. No new relative timeout, clock reset, sleep, polling loop, process enumeration or retry is added for details. Cap eight open attempts per existing snapshot, stop initiating work on expiry and mark remaining details omitted/deadline-exhausted. Long OS/filesystem calls cannot be proven preemptible; a late return preserves actual timestamps and the already non-PASS outcome. No deadline extension or measured fit is claimed.

**Do not add an extra in-interval census in this correction.** A single strict snapshot after authenticated helper startup is technically implementable with the existing APIs and deadline, but there is no observed spare-time/fit proof for the extra query/persistence work in the short helper interval. Disposition 79 conditions that addition on showing it fits. Current accepted post-wait/drain/exception snapshots already supply exact owned-Job census targets; immediate enrichment is the narrow sufficient next evidence change. If processes vanish before detail acquisition, retain unknown and seek a separately justified observation-timing plan, not an implicit new sampling/probe phase or longer H sleep.

For query/snapshot failures the existing normal stage remains blocked. Detail coverage incomplete/capped/unknown never grants success and never changes `snapshot.complete`, which specifically means the original accounting/PID capture was complete. Report the two notions separately. Keep original 10-second total, exit-7 proof, zero/empty/zero gate and later tree probe unchanged; no 30-second runtime-profile assertion follows.

## Best-effort error isolation

Every enrichment entry/return/attachment/reporting step is diagnostic-only and guarded with the same lesson as accepted review 16: the entire secondary reporting body, including dictionary/list/string allocation, is inside its own `try/except Exception`. If even constructing/attaching an error record fails, suppress that secondary reporting failure without losing the already-built primary snapshot or replacing the existing accepted exception. Do not broadly catch/ignore failures from the primary census or its acceptance checks.

Native handle closure belongs in finally outside/before fallible telemetry construction. Query errors are isolated per field where feasible to preserve earlier fast facts. A diagnostic helper error cannot skip the normal original rejection, convert missing fields to observed zero/empty, change a failure into finalAcceptance, mask the primary error or prevent final Job/owned-normal-handle cleanup. No recursive persistence, evidence rewrite, alternate fallback file or retry after a pending-write failure.

## Future implementation/review gates

After coordinator plan acceptance/release, Luna changes S only. Affected static gates are S Ruff check/format and authorized syntax checking only; reuse pinned unchanged W/H/P/native declaration evidence. No new tests/probe artifacts, module imports, wrapper/self-check/runtime call or evidence directory. Submit exact final S, unchanged W/H/P/protected/prior evidence hashes and exact commands/results/preliminary failures. Preserve all eleven disposition-78 retry-3 evidence hashes.

Independent non-implementing Sol review must establish:

| Case | Required static result |
| --- | --- |
| Primary capture | Before/census/after/timestamps/complete/unexpected IDs unchanged; diagnostics start afterward and cannot edit/reclassify the original set. |
| Selection/scope/bounds | Only unexpected IDs from a complete exact-owned-Job snapshot; eight-row cap, one open each, no whole-host/new process probe, no in-interval census. |
| Same-handle detail | Existing query/SYNCHRONIZE rights and APIs only; creation/path/membership/wait/exit from one owned handle, no PID reopen/name-based identity or guessed origin. |
| Disappearance/reuse/inaccessibility | Actual error plus unknown historical association; false membership/vanished PID is not proof of benignness, an escape or natural exit. |
| Timing/transitions | Zero-time waits; raw code 259 not the sole liveness test; per-query ambiguity/late/capped fields truthful; every operation original-deadline bounded in acceptance. |
| Ownership/errors | Every successful open has one finally-close attempt; close errors visible if possible; no normal-handle-list transfer/double close. Reporting/allocation failures cannot mask primary capture/rejection/cleanup. |
| Acceptance | Any original unexpected PID stays sticky BLOCKED even if later gone, signaled, familiar/System32, code 7 or final empty. All exit/identity/complete-zero/containment/tree/cleanup gates unchanged. |
| Scope/preservation | S-only delta; schemas/paths/flags/commands/environment/roots/dependencies/deadlines fixed; old evidence/hashes unchanged; outer exit discrepancy and missing historical provenance not “resolved.” |

Static PASS proves no runtime identity, timing or diagnostic coverage. If a fixed required error/cleanup contract cannot be preserved without additional scope, stop for the exact prerequisite; no unsafe partial implementation.

## Stop and execution boundary

Stop on baseline drift, need for new APIs/rights/schema/root/filename/mode/dependency/host probe, a desired auxiliary-process exemption or changed rejection/flags/deadline, or an inability to keep raw capture independent of best-effort details. Vanished/inaccessible/partially observed members remain unresolved; do not chase them outside the original interval or weaken the gate to continue.

Coordinator acceptance, implementation and independent PASS precede any separate fresh fixed-path plan/review/gate for another wrapper self-check. Retry-3 is consumed and cannot be reused; no new root is chosen/prepared here. No collection/verification/manifests/GIS/numerical/candidate build/reservation/serving/publication/browser step follows this plan. Candidate remains NO-GO/unservable and build 3 unreserved; counters/source/geometry/recipe/numerical/product constraints unchanged. No commit/push/merge.

Planning consisted only of static source/document reads/hashes and writing this plan. No code/evidence/checkpoint/ledger edits, new root/record, tests/imports/parsers/linters/compilers, process inspection/probes, wrapper/self-check/preflight/runtime/collection, manifests/GIS/numerical/build or browser work occurred. Return plan hash to coordinator and stop.
