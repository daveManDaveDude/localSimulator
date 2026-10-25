# S tree wait/census correction — revised plan v2

2026-10-25. Issue `Teignmouth-float32-topology-representation-1`; **PLAN ONLY** under disposition 132. This new artifact supersedes the proposed implementation design in v1; v1 and its FIX REQUIRED review remain unchanged. F1 is resolved in this design by verifying terminal status in the **same** bounded Toolhelp enumeration, before using its rows for ancestry/membership proof. No source edit, check execution, process query or further attempt is authorized here.

## Exact baseline and planned spans

| Source | Required baseline SHA-256 |
| --- | --- |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff` |
| W, unchanged | `f600efc92fd040aa5b91cf543210be139ed50f895eba7d62c34175e73dc7dc8b` |
| H, unchanged | `75678b51d0e17d89862bf0a7ee3446014969ba73aae6cd31606288553b163e27` |
| P, unchanged | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

Accepted diagnosis: `retry6-qpc-deadline-diagnosis.md`, SHA-256 `60070d106c7e81ea492e05591c3db16bbe3d25300466b9bce34072859c3ad220`. V1 review/F1: `retry6-s-wait-callback-correction-plan-independent-review.md`, SHA-256 `15e309662c714efc684d86896d4037a452892c7419d4be5446eacc1bcfa0a062`.

After separate plan PASS/coordinator implementation release, change only S:

1. `_assert_tree_contained`, pinned **391–436**: add a keyword-only opt-in `require_complete_snapshot=False`; alter the enumeration's false-result handling only when opted in; return a fixed bounded proof object only on strict successful completion. Preserve default return `None`, algorithm, counts, ordering and behavior. Narrow changed subspans are the declaration391, enumeration400–408 and strict-only success return after436; remaining predicates/checks/handle ownership stay unchanged.
2. Self-check tree wait block **4059–4068**: local deadline/counter/diagnostic closure, opt into strict proof, keep the three-second wait, add mandatory final proof before unchanged marker code4069 onward.

No `_api`/binding/import/shared `_wait_process` edit is proposed. All normal/build/preflight calls retain omitted/default false mode. No W/H/P, path literal, marker, identity, termination, schema-version or output-file change. If actual bytes require a wider edit or loader assumption fails, stop for coordinator decision.

## Actual last-error plumbing and call-site analysis

Static source establishes the required facility already exists:

- `_api()` constructs `ctypes.WinDLL("kernel32", use_last_error=True)` at195, sets `Process32FirstW`/`Process32NextW` argument types and BOOL results at281–284, and returns that kernel at291. No overriding `errcheck` or replacement Process32 binding was found in the inspected source.
- `_selfcheck()` obtains this kernel from `_api()` at3733 and supplies it to its normal callbacks3845/3875 and tree callback4065. The proposed strict tree closure uses that same configured kernel, not another loader.
- Runtime-preflight calls4388/4393 and build calls4707/4721/4826 also use this shared helper. They, and normal-stage callbacks3845/3875, must retain their existing call text and default behavior. `_parent_pid`'s separate enumeration366–388 is outside scope.

Python documents that `use_last_error=True` swaps the Windows error value with ctypes' thread-local private copy around foreign calls, and that `ctypes.get_last_error()`/`set_last_error()` read/write that private copy. This suffices without a new `GetLastError` binding, new DLL, prototype or Win32 API. Do not substitute direct `ctypes.GetLastError()` for the captured private value. [Python 3.13 ctypes documentation](https://docs.python.org/3.13/library/ctypes.html#loading-shared-libraries).

Microsoft documents FALSE from `Process32NextW` and `ERROR_NO_MORE_FILES` for exhausted/absent snapshot process information; the error-code table assigns18. With a successful first entry in this process snapshot, false Next plus18 is the accepted enumeration terminator. Other false outcomes are not completion. [Process32NextW](https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/nf-tlhelp32-process32nextw), [Windows error codes](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-).

**No binding change is required by this analysis.** If later inspection finds the actual call uses a loader without private-last-error capture, stop. The smallest possible alternative to return for a new coordinator decision would be an S-local last-error-enabled binding of the already used Process32NextW with the same HANDLE/PROCESSENTRY32W/BOOL contract; do not implement or assume authority for that alternative under this plan.

## Verified completion of the same census

In strict mode, preserve the one snapshot and original bounded row loop. Snapshot creation failure and unsuccessful `Process32FirstW` continue to raise; even first-false/error18 is not accepted as an empty complete process table. Initialize terminal status to unknown, never success.

For each existing Next operation in strict mode:

1. After the current row is recorded and before the existing `Process32NextW`, call `ctypes.set_last_error(0)` on the existing private mechanism. This prevents a stale18 from a previous operation being mistaken for a newly reported normal terminator. Setter failure blocks before the native call; no retry.
2. Call `Process32NextW` exactly once for that existing iteration. On FALSE, make **`terminal_error = ctypes.get_last_error()` the first operation in that false branch**: no clock read, CloseHandle, telemetry/record assignment, error formatting or other foreign call first. Accessor failure or non-integer/unavailable status blocks as unknown. Retain that local numeric value before finally-close can alter last error.
3. Accept terminal enumeration status **only when it is exactly18**. Zero (the reset sentinel), any other code, inaccessible capture or unknown state raises a fail-closed enumeration error before ancestry/Job comparison uses the prefix. Use the captured code for the error, never reread it after cleanup; no retry or permissive `FALSE=complete` interpretation. Strictly truthful status logging must not replace the primary exception.
4. TRUE means another entry exists, not completion; ignore its error code. If65536 rows are exhausted without verified normal termination, preserve the existing fixed-bound failure. Exactly65536 rows followed by FALSE/18 may finish within the existing loop; a TRUE following the65536th row remains overflow. Keep existing deadline checks and snapshot finally-close.

After verified terminal18 only, run the existing same-row numeric ancestry expansion, convergence/depth/time checks, bounded exact Job census and membership comparison unchanged. No second Toolhelp snapshot, backfill, prefix acceptance or substitute scan is introduced to establish completion. Existing `_process_list` is the separate existing Job census, not a replacement process snapshot. Periodic and final strict calls are separate temporal observations required below; none repeats another scan merely to discover its lost terminal status.

Default mode takes the original Next false/break path and return None, without set/get-last-error calls or strict proof allocation; no default error-interpretation change. Strict mode returns only after all existing checks return normally, with a fixed proof object containing `snapshotComplete=true`, `terminalError=18`, `rowCount` in1..65536, `ancestryComplete=true` and `comparisonComplete=true`. Missing/malformed/false fields never count as proof. A proof-object allocation failure blocks. Wrapper pre/post clocks below additionally reject late return; helper normal return alone is no longer called complete.

## Wait horizon, containment deadline and final gate

Keep shared `_wait_process`3427–3499 byte-identical. In the tree-only replacement:

1. From the already authenticated inherited `deadline`, set `containment_deadline=deadline-1.0`, `tree_wait_started=time.monotonic()` and `tree_cutoff=tree_wait_started+3.0`. Require strict `tree_cutoff < containment_deadline`; otherwise BLOCKED for insufficient full probe/reserve opportunity. No shortened successful probe, budget restart/increase or new clock domain.
2. A self-check-local mandatory closure takes periodic/final role, checks current time strictly before containment_deadline, calls `_assert_tree_contained(..., containment_deadline, require_complete_snapshot=True)`, validates the fixed strict proof, then checks time strictly before the same bound again. It records completion in mandatory local state only after all checks. Every incomplete/error/unknown/late result raises; no blanket TimeoutError catch to continue, retry or override an earlier failure.
3. Call `_wait_process` with tree_cutoff for its wait horizon, this closure for periodic containment and the same containment_deadline for this call site's optional sample lambda. Only this self-check call changes. `_wait_process` may call containment after WAIT_TIMEOUT crosses tree_cutoff; that census can finish after the wait horizon if it finishes before its separately supplied containment bound. Expiration of the wait is not a census failure; expiration/error/incompleteness of the census is always a blocker.
4. Preserve `tree_timeout=false` early-exit rejection. A true return is only a wait outcome. Require a fresh clock at/after tree_cutoff and strictly before containment_deadline. If the existing sub-ms rounding returns before the actual horizon, block rather than sleep/spin/assume the horizon.
5. Invoke exactly one separate **mandatory final strict closure** after the observed horizon and before marker processing. It must prove terminal18, complete existing ancestry/Job comparison and timely return. Missing/zero periodic completions or wait-only true cannot substitute for that final proof; a previous error prevents reaching it. Only then continue the byte-identical marker/identity/Job/termination/root-exit/output-absence checks4069 onward.

## Bounds, recording and fail-closed outcomes

Permit at most16 periodic closures and exactly one final closure. Count periodic attempts before opening a snapshot; exceeding16 or attempting a second final call blocks. Each census retains65536 rows,64 ancestry passes and existing bounded Job query. No retained row arrays or per-iteration histories are added to diagnostics. Native latency/allocation cannot be preempted; the reserve means at least1s remained at successful final census completion, not a guarantee that later unchanged proof/cleanup finishes in1s. Those later operations keep the original ten-second global deadline/finally rules.

Retain v1's explicit additive fixed `treeProbeBoundary` group in the existing S invocation record: global deadline, reserve1.0, containment deadline, wait start/horizon/outcome, bounded attempt/completion counts, last periodic and final start/end/status, final-complete boolean. Add last/final snapshot terminalError and rowCount from successful strict proof. Status vocabulary is fixed (`not-started`, `running`, `complete`, `failed`, `late`, `unavailable`, plus wait early-exit/expected-horizon); null is unknown, never success. No arbitrary new stack/message/row array or new file/schema version.

Use mandatory local proof/state independently of record assignments. Initial bounded record allocation failure blocks before wait. Any best-effort status update while handling an error must be nested so it cannot replace that error; bare-rethrow the primary, never admit a failed census. Failure may omit detailed terminal telemetry but must not label the operation complete. The unchanged existing catch/finally persists BLOCKED/error/termination or PASS. No new persistence before mandatory cleanup. PID31876 remains unidentified; no process-class exception or count subtraction.

## Independent review/acceptance cases

| Case | Required result |
| --- | --- |
| Next FALSE/18 after successful first and all bounded checks | Enumeration may be complete; final acceptance still needs ancestry, exact Job comparison and timely wrapper completion. |
| Next FALSE/0, other code, missing/unreadable last error | BLOCKED before using prefix; no fallback scan or retry. |
| Prior private error18, reset0, false Next does not report an error | Captured0 remains unknown/failure; never stale-success. |
| First/snapshot error, bound overflow, convergence failure, deadline crossing | Existing/fail-closed exception; no proof flag. |
| 65536th row then FALSE/18 versus TRUE | First may complete; second is fixed-bound failure. |
| Wait crosses local3s while strict census finishes before containment bound | Periodic completion may count; mandatory post-horizon final census still required. |
| Final proof unknown/malformed/incomplete, returns late, or time/cleanup reserve absent | BLOCKED, never expected-timeout-to-PASS. |
| Early root exit or sub-ms early wait return | Existing early-exit/fail-closed horizon rejection; no delay or assumed observation. |
| Later marker/identity/Job/termination/root-exit failure | Existing rejection; final census/cleanup cannot repair it. |
| Default/normal/build/preflight caller | Default parameter false; original loader, enumeration behavior, returnNone, wait/deadline/acceptance unchanged. |
| Error-record allocation/assignment/persistence failure | Preserve existing primary and mandatory cleanup; unavailable telemetry is not acceptance. |

## Reusable evidence, checks and stops

Reuse the accepted diagnosis and retry-6 normal7/7 zero/empty/zero evidence only for historical diagnosis/unchanged-branch review, never a future final proof. Reuse unchanged W/H/P/path review and W AST/C# compile-only evidence. The70 immutable evidence files (53 original/retry1–5 plus17 retry6) and six protected source/config/test bindings remain unchanged; a later expressly released read-only full-name/count/hash gate must match their accepted matrices. No retry1–5 evidence contents are read in this plan.

After independent plan PASS and coordinator release only: Luna implements these two S regions; record tight raw-byte diff, final S hash and exact in-memory inverse to full baseline `1cee4b…`; verify unchanged W/H/P/path literals. Proposed later gates are expressly authorized S Ruff check/format-check and independent actual-byte/branch/hash/inverse/preservation review. No test/import/project invocation is authorized by proposing those future static gates. Default call sites and `_api` must be traced independently from actual bytes; verify immediate error capture ordering and no stale18/native call before capture. No broad reformatting or proof-script-driven source normalization.

Stop for baseline drift, absent last-error plumbing, new binding/API/import/right need, default/shared behavior change, unverified terminal status, duplicate/broadened scan, weakened bounds/acceptance, failed inverse/preservation, or inability to preserve primary error/cleanup. Any smallest alternative binding option needs a new coordinator decision before implementation. No accepted-path, source-data, GIS/numerical/product/pending-AOI or synthetic behavior change is included.

Current retry-6 literals remain consumed and non-invocable. No retry-7 path is proposed/probed/selected/reserved/created. Historical counters/budgets carry forward unchanged. Candidate remains NO-GO/unservable, build3 unreserved; no preflight/build/serving/publication authority follows.

## Planning boundary

Only authorized disposition/review/source reads/searches, official publisher documentation reads and this new plan artifact write occurred. No source/evidence/checkpoint change, parser/compiler/linter/test/import, runtime/process inspection, probe/path/root work or invocation occurred. No static gate or runtime fit/behavior PASS is claimed. Stop for separate independent Sol plan review and coordinator decision.
