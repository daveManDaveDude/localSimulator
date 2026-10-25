# Retry-2 nonzero helper — narrow S-only completion/reaping plan

2026-10-25. Sol 6.1 medium planner `/root/sol_review17_plan`. Planning only under disposition 68, which accepts `retry2-nonzero-descendant-diagnosis.md` (SHA-256 `a5e725094fad681f6fe7b3119e6dc078769f1c4a29b044d5941d9e20d7fe112d`).

**Feasible in S only**, using existing Windows APIs and standard-library facilities. Preserve actual exit/identity evidence, release owned completed-process handles, then reconcile a complete empty inner Job within the original 10-second deadline. This does not infer that retry-2 was a false positive or retrospectively change its BLOCKED result. Coordinator must accept this plan before implementation; no code/run is authorized by this document.

## Reconciled exact baseline and scope

Read disposition 68 and actual current S/W/H, including S's API declarations, process identity/child discovery, normal-helper launch/wait, Job census/count/termination and final cleanup; H's nonzero branch still writes its marker, sleeps at most 0.15 seconds and returns 7 without spawning the later tree child.

| Source | Current SHA-256, recalculated statically |
| --- | --- |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `2bae9a35ee91ca154bba19c0a3848b0bda2f46930f38e9090bd632ff5653300d` |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `3078e1df4bf89438208bbcfc09150dbce77f180259f847a84287892d26662989` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `e3cdadced5d90a669155002870636610e77df68b8a013deeef187893fbd65e78` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| Disposition 68 | `a8781f0e8683d0526085b886341c78fc780674c2fbef2f6634155f6215622162` |

Only S changes in this code correction. W/H/P, all fixed path constants/schema IDs/record names, accepted caller/handoff/type fixes, source/config/tests/candidate/GIS/product bytes, original/retry-1/retry-2 evidence, ledgers/checkpoint and historical counters remain unchanged. Do not prepare a new evidence root or rerun the consumed retry-2 slot. A later fresh-slot W/S/H path-binding plan/review is separate.

## Accepted semantics and official basis (reused)

Retry-2 failed at S 2326–2327 on one instantaneous `ActiveProcesses != 0`, without recording the value or members. Later forced cleanup's zero is not normal-stage proof. Launcher and interpreter are distinct authenticated processes: retry-2's IDs were 37852 and 32724; these numbers are history, never constants for the fix.

Microsoft defines Job active accounting in terms of association and reference release; a retained process object may outlive termination. Capture actual waits/exits and release owned completed-process handles before demanding settled accounting. Do not assume reference release caused this particular failure. [Job accounting](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information), [Process termination](https://learn.microsoft.com/en-us/windows/win32/procthread/terminating-a-process)

The inner Job is the normal-helper launcher/interpreter subset, not S itself. Nested membership/accounting covers descendants in child Jobs. Do not subtract S or a fixed allowance from the observed count. PID enumeration must be complete; a partial buffer is not an empty Job. [Nested Jobs](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs), [Job PID list](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_process_id_list)

Waiting on one process observes that handle's signaled state; it is not a descendant census. A waitable handle needs SYNCHRONIZE access and must not be closed while a wait remains pending. The repair uses these existing API declarations, not a new operational probe. [WaitForSingleObject](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject)

The deliberate tree probe's forced Job termination remains a distinct later test. It must not be repurposed to make unexpected normal-helper cleanup appear successful. [TerminateJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-terminatejobobject)

## Concrete S changes and touched functions

### 1. Retain the authenticated interpreter handle during discovery

Add the standard `SYNCHRONIZE = 0x00100000` access constant in S. No API declaration or dependency change is required: `_api` already binds OpenProcess, GetProcessTimes, QueryFullProcessImageNameW, IsProcessInJob, WaitForSingleObject, GetExitCodeProcess and CloseHandle.

Extend `_contained_interpreter_child` (current 405 onward) with an explicit keyword-only option such as `retain_handle=False`. Preserve current return/close behavior for all existing callers by default. **Only the normal self-check call opts in.** Do not change build/preflight/tree-helper behavior or acquire broader rights for their existing calls.

In the opted-in branch, during successful child discovery, open query plus SYNCHRONIZE rights and validate **that very handle** before transferring it to `_selfcheck`:

- expected PID and creation FILETIME match the discovered native child and later authenticated helper-start marker;
- read creation/native image from the retained handle (GetProcessTimes and QueryFullProcessImageNameW), hash its canonical image with the existing deadline-aware hashing, and require the pinned base-interpreter path/hash;
- require exact inner Job membership on that handle and the already required parent relationship to the exact created launcher; launcher PID/creation comes from its original CreateProcess handle, not a newly opened PID;
- if an identity query necessarily used an earlier temporary handle, creation FILETIME and native image must be rechecked on the retained one. Never transfer a handle for a later PID incarnation just because its PID/image name matches;
- any failed/mismatched acquisition closes the local handle and fails closed or continues only the existing bounded discovery of the intended identity. It must never reinterpret unobservability as “already exited.”

Return the retained handle with the identity only after validation, with an explicit ownership-transfer flag so function-level finally does not close it. Every pre-transfer error closes exactly once. `_selfcheck` immediately adds it to its owned-handle collection before any fallible helper-start/evidence work. Existing `_verify_helper_start` must validate the same identity/marker; its own temporary handles are not reused after close.

This timing matters: do not wait for the launcher to exit and then OpenProcess on a potentially reused interpreter PID. If acquisition cannot happen before the short helper exits on a particular run, record a typed incomplete-identity failure and cleanup; do not lengthen H's sleep or fabricate an exit to make it pass.

### 2. Preserve an independently complete self-check membership snapshot

Add a private self-check observation helper in S, e.g. `_selfcheck_job_snapshot`, using the existing inner Job handle and original deadline. It must return structured observations, not make acceptance decisions or swallow query errors as zero:

- monotonic observation start/end and phase;
- raw accounting count before/after the enumeration, each independently `observed`, `unavailable` or `deadline-exhausted` with numeric value or null and structured error;
- complete PID list, assigned/listed/buffer counts, query status and bounded-query error/partial detail;
- authenticated known normal launcher/interpreter scalar identities, wait/exit state known so far, and any unexpected member IDs;
- explicit overall observation completeness; `[]` means successfully observed empty, while an unavailable/truncated query uses null/incomplete state.

For complete enumeration, put a private strict PID-query routine inside the new self-check observation helper, reusing `_process_list`'s existing information class, structure layout and finite capacity/attempt ceilings, but leave `_process_list` and all its other callers unchanged. Never return a list merely because QueryInformationJobObject returned success: require sane header values, `NumberOfProcessIdsInList <= capacity`, enough allocated buffer for listed pointer-sized IDs, assigned/listed equality for a complete snapshot, positive distinct IDs and all loops before deadline. On capacity/assignment mismatch, retain partial header information and retry **within the same deadline** and existing ceilings; exhausted/inconsistent/failed queries are incomplete/non-PASS. Do not read beyond allocated data. Metadata must reach the snapshot rather than be discarded. No fallback to the less-specific shared query is allowed for a failed strict observation.

Do not force accounting-count equality with list length during changing snapshots: record both observations and their times. Final success below explicitly requires two zero counts enclosing a complete empty list. This is a bounded observation, not atomic process-tree immutability.

### 3. Normal-helper stage evidence before any failure escapes

Initialize an additive `normalHelperCompletion` object in the **existing** invocation record before launch, with phase, known identities, handle-ownership state, waits/exits/query statuses and null/unknown observations. No schema/file/path change. Keep existing top-level fields required by downstream evidence.

In `_selfcheck` (2233 onward), stage changes are: `launch`, `authenticate-interpreter`, `verify-start-marker`, `wait-launcher`, `wait-interpreter`, `release-completed-handles`, `drain-inner-job`, `normal-complete`. Every exception exiting this normal stage must route through one guarded evidence checkpoint in `_selfcheck`'s exception path **before cleanup/rethrow**, rather than jumping straight to a generic message. Capture the primary exception first.

That checkpoint obtains the snapshot above, where possible within the remaining original deadline, and persists current identities, actual launcher/interpreter exit observations, raw count and PID census/query status via existing `_update_owned(record_path, record)`. If the Job does not yet exist or the deadline/query is unavailable, explicitly persist null plus its reason; do not invent a count/census merely to satisfy a record shape. Store primary and evidence-query/persistence failures separately. A failed evidence write is sticky non-PASS and must not prevent required Job/handle cleanup or overwrite the primary exception; no filesystem can guarantee persistence when the filesystem itself is unavailable. No failure may be hidden by a later successful checkpoint.

Persist the initial post-wait snapshot **before** checking its acceptance predicates, and final normal-stage success snapshot before starting the tree probe. During drain keep first/latest observation, iteration count and errors in a bounded summary; persist it before any rejection/expiry. No unbounded sample history or new telemetry mode.

### 4. Observe both expected exits on pinned handles

Retain existing launcher `_wait_process` and its telemetry/containment callbacks, using the original deadline. Record its timeout, signaled observation and actual exit before any guard can raise. Require actual exit 7; the `nonzero-helper.json` marker remains corroboration of intent, never a substitute for GetExitCodeProcess.

Wait on the retained interpreter handle with recomputed remaining original time; use `_wait_process` or an equally bounded small private wrapper with the same timeout/error handling. Query actual exit on **that handle**; require signaled state and exit 7, matching the already authenticated identity/start marker. One process's exit is not copied into the other's field. No PID reopen is needed for completion. Preserve exact containment checks during bounded wait slices and take an explicit membership snapshot even if both waits returned immediately.

Expected normal processes can still be running while their bounded completion waits are in progress. After this stage claims both terminated, an unsignaled/live known member contradicts completion and is non-PASS. Unexpected live/unknown members are never granted a grace interval simply to disappear; incomplete/escaped/unavailable identity evidence is non-PASS. Query failures and timeout cannot become successful natural exit.

### 5. Release completed references, then bounded drain

After both expected process exits have been successfully recorded, close the interpreter and launcher handles exactly once, check CloseHandle success, remove their entries from `handles` and invalidate local handle ownership. Do not retain closed integers for later waits or final double-close. If a close fails, keep an explicitly owned cleanup entry and fail; never lose ownership while assuming close succeeded. Scalar PID/creation/image/exit evidence remains in the record.

Replace current single `_job_active_count != 0` assertion at 2326–2327 with the bounded snapshot/drain phase. It may wait only for already-proved terminated normal-pair accounting/membership to settle, with small slices such as `min(0.025, remaining_original_time)` and a deadline check around every query/sleep/persistence operation. No local `now+N` deadline, cap increase, unbounded busy loop or count subtraction.

Each observation classifies returned PIDs against the **authenticated normal-pair identities/history**. Any PID not in that pair is an unexpected member and fails; do not adopt it because it belongs to the Job or has a familiar executable. Never reopen a closed PID to manufacture proof that a reused process is the original. Residual known numeric IDs alone are not new liveness/identity proof: label them as unresolved residue, retain the already captured handle-based exits, and keep waiting only for complete emptiness. Any actual contradictory live/reused identity evidence is non-PASS, not a stale-count exception. Preserve current escaped-descendant checks without exempting S or any constant PID/count.

**Normal-stage acceptance:** both actual exits 7, authenticated identities/start marker, completed handle-release bookkeeping, no sticky failure, deadline still valid, and a successful snapshot with accounting count 0 **before and after** a complete empty PID enumeration. Unknown count, missing list, partial list, nonempty membership, missing exit or deadline expiry cannot satisfy it. No `TerminateJobObject`/forced cleanup is used to attain normal-stage PASS.

### 6. Keep later tree probe and final cleanup gates

Only after the persisted `normal-complete` checkpoint may the existing tree-root launch proceed. Keep its deliberate timeout, root/child marker/native identity/creation checks, exact Job membership, active-before requirement, forced termination confirmation, zero remainder, exit observation and original deadline checks unchanged. This plan does not preemptively alter that later test in anticipation of another possible defect.

Adjust `_selfcheck`'s scoped handle-finalization bookkeeping only as required to close the newly retained handle and avoid re-closing already released normal handles. Keep failure-time Job termination before final evidence operations, record final forced termination separately, and never promote BLOCKED to PASS because cleanup succeeded. Shared `_terminate_job`, `_job_active_count`, build/preflight modes and their acceptance semantics remain unchanged. Evidence/checkpoint failure must not bypass final cleanup. No arbitrary memory cap or unrelated process inspection feature.

## Independent static acceptance and review matrix

After separate implementation authorization, run affected S Ruff check/format and syntax/static gates only as authorized by coordinator; reuse unchanged W/H/P/interop evidence tied to the exact hashes above. Do not create tests/probe artifacts or execute/import S/H. Record exact commands, results, preliminary failures and final S/unchanged W/H/P/protected/evidence hashes.

A non-implementing Sol session must inspect actual S changes against this plan and the original evidence. Required cases:

| Criterion/case | Required static outcome |
| --- | --- |
| Launcher/interpreter identity and reuse | Distinct handles/creation/native/Job identities; interpreter acquired while authenticated, same-handle revalidation, no post-exit PID adoption. Only normal self-check opts into retained discovery. |
| Acquisition/verification exception | No leaked handle before transfer; caller owns transferred handle before next fallible step; incomplete identity recorded and cleanup reachable. |
| Expected exit versus marker | Both process handles yield observed signaled exits 7; marker-only, unknown, STILL_ACTIVE, timeout and wrong exit are non-PASS. |
| Complete membership | Strict query bounds/header counts/duplicate IDs and errors; no buffer overread, incomplete-as-empty or fabricated zero. Raw count and full-list status captured before rejection. |
| Retained terminated objects | Successful exit evidence captured, handles released once, known residue can drain under original deadline; no immediate unsupported assertion that any nonzero count is a live descendant. No false-positive claim about retry-2. |
| Unknown/live/escaped/unavailable member | Sticky non-PASS; no ignored IDs, subtraction, constant allowance, adoption or cleanup-to-PASS. |
| Zero/empty normal handoff | Raw zero counts enclosing complete empty list, before original deadline and persisted before tree launch; failure never reaches tree launch. |
| Handle/cleanup/error lifecycle | Proper ownership on every close failure/path; no wait on closed handle/double-close; primary/evidence/final-cleanup errors separated; mandatory cleanup cannot be blocked by logging. |
| Deliberate tree probe and scope | Existing behavior/gates/deadlines unchanged; no H/W/P/root/schema/command/dependency/other-mode change; protected old evidence and candidate/source/limits unchanged. |

Static PASS cannot demonstrate an actual Windows drain, timing, persistence or containment result. Independent review is a gate, not a new runtime authorization.

## Stop conditions and execution boundary

Stop before implementation without coordinator plan acceptance/release. Stop if safe same-handle interpreter identity/exit observation cannot be obtained within S's existing APIs/unchanged H behavior, complete census needs a broader architecture, access beyond the specified SYNCHRONIZE/query rights or another native API/external helper/schema/path/dependency is required, or a mandatory cleanup/evidence contract cannot be preserved. Return the exact prerequisite instead of relaxing identity, member emptiness, expected exit, containment or termination proof.

All work stays under the original inherited **10-second total QPC deadline**, with monotonic conversion already validated by `_handoff`; no reset after acquisition/import/wait/drain/evidence. If normal completion/drain leaves too little time for the unchanged later tree probe, return non-PASS and actual evidence, not a longer deadline or reduced probe. No 30-second runtime-profile fit claim is made.

Retry-2 is consumed/immutable. This code-only correction changes no fixed evidence paths and creates no directories/records. A separate exact fresh-root W/S/H path-binding plan, implementation/review and coordinator acceptance are required before one later wrapper self-check under disposition 64. One invocation per reviewed cycle; failure requires another defect-specific plan/review, no automatic rerun/reset.

No runtime collection/verification, manifests, GIS/numerical work, candidate build/reservation, serving/publication or browser action follows this plan or a future self-check PASS. Candidate remains NO-GO/unservable, build 3 unreserved; historical counters and all source/origin/domain/recipe/collision/numerical/product constraints unchanged. No commit/push/merge.

Planning comprised static source/document reads and hashing, reuse of the official references already read in the accepted diagnosis, and writing this one new plan. No code/evidence/other artifact edits, parser/linters/compiler/tests/imports, process inspection/probes, wrapper/self-check/preflight/runtime/collection, manifests, GIS/numerical/build or browser work occurred. Return to coordinator for narrow S-only dispatch; stop here.
