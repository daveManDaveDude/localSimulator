# Self-check existing-console inheritance — S-only plan

2026-10-25. Sol planning under coordinator disposition 90. This artifact proposes a bounded implementation; it authorizes neither an edit nor an invocation. Independent Sol plan review and coordinator acceptance must precede any implementation release. The existing issue is `Teignmouth-float32-topology-representation-1`; consumed roots and counters remain intact.

## Baseline and purpose

Recalculated current SHA-256 values:

| File | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `64bf2c4abf822ad55252789315d71731d2660d66bb5b6bc7d60f810f2de492c7` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| Disposition 90 | `42b195cb8c0f8222d572cd149e404ba44d290d50a9c600bd9d12daa1d305a737` |
| Accepted `retry4-conhost-lifecycle-diagnosis.md` | `c17894b5a1bbdd251b3b3005a8d90ef220edaed66d1782cc04313b2826811a26` |

Retry-4 correctly rejected an unexpected Job PID. Its later retained-handle diagnostics support a console-host lifecycle hypothesis, without proving the census-to-handle association or host ownership. The proposed change prevents an avoidable new helper console where the supervisor already has a console. It does not admit any auxiliary member or reinterpret previous evidence. Static reasoning cannot establish that it will remove the observed failure on this machine.

Scope: S only. W/H/P, helpers' commands, environment, CWD, standard-handle destinations, schemas, roots, filenames, modes, dependencies, manifests, identity/profile rules and all numerical/source/product constraints stay unchanged. No retry root is selected or created by this correction. Original and retry-1/2/3/4 evidence remain byte-identical. Candidate remains NO-GO/unservable; build 3 unreserved.

## Technical basis and limits

[Microsoft GetConsoleProcessList](https://learn.microsoft.com/en-us/windows/console/getconsoleprocesslist) returns PIDs attached to the caller's current console. Its buffer must be non-NULL with positive element capacity. A zero result is failure; capture GetLastError immediately. A result exceeding capacity is the required capacity and supplies no usable identifiers. Only a positive result fitting the buffer is complete for that call. These semantics require bounded resizing and refusal of truncated output. This API establishes caller attachment, not console-host identity, parentage, ownership, visibility or Job membership.

[Microsoft Process Creation Flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags) defines CREATE_NO_WINDOW as consoleless execution with the console handle unset; CREATE_SUSPENDED requires explicit resume. [Creation of a Console](https://learn.microsoft.com/en-us/windows/console/creation-of-a-console) documents default inheritance of the parent's console. Retaining an existing console avoids requesting a new one. This plan does not allocate, attach, free, display or hide a console/window, or establish a new console association.

The reference [CPython v3.13.7 venv redirector launch function](https://github.com/python/cpython/blob/v3.13.7/PC/venvlauncher.c#L360-L434) duplicates standard handles, uses its own Job, and launches the actual interpreter with creation flags zero. It does not propagate S's CREATE_NO_WINDOW. Keeping the venv launcher attached to S's existing console therefore provides a plausible inheritance chain to the interpreter. This is reference-source reasoning, not attestation of the installed launcher, actual console ownership or a guaranteed runtime result. Existing pinned launcher/base authentication and exact nested Job checks remain essential.

The current process is already authenticated through `_handoff("self-check")` before `_selfcheck` invokes helpers. Checking its own native PID against `os.getpid()` and finding that PID in its current-console result uses the existing authenticated S identity; it requires no OpenProcess, ancestry scan or process probe. The process cannot reuse its own PID while executing this check. Other listed PIDs confer no permission or trust and need not be opened or classified.

## Ordered implementation specification

Source line numbers below refer to the pinned S baseline; use function/call identity after insertion.

1. Add one private query helper immediately before `_launch_suspended` (currently line 1880), proposed name `_require_current_console(kernel, deadline) -> None`. Bind only `kernel.GetConsoleProcessList.argtypes = [ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]` and `.restype = wintypes.DWORD` inside this helper. Existing `_api` (192–291) and its return shape remain unchanged. Binding is lazy, so other launch modes do not acquire a new API requirement or execute this query. Missing symbol/binding/allocation/query failures raise through existing launch/self-check error handling. No new DLL, rights, handle or dependency is required.

   Check the inherited `time.monotonic()` deadline before and after binding, allocation, each native call and PID validation. Read `GetCurrentProcessId` using its existing DWORD binding and require it to equal the positive `os.getpid()`. Do not query other processes. Use a local DWORD array starting at **32 elements**, at most **4 native list calls**, maximum **4096 elements**. Never call with NULL/zero capacity. For each attempt:

   - Allocate `(wintypes.DWORD * capacity)()` only after the deadline check; allocation failure is non-PASS.
   - Invoke GetConsoleProcessList, save the integer return, and on zero capture `ctypes.get_last_error()` immediately, before clocks/telemetry or another native call. Raise the captured WinError; even error zero is a failure, not an empty console.
   - Check completion time before using any result. If expired, raise TimeoutError irrespective of success/error or available PIDs.
   - When return exceeds capacity, ignore the buffer entirely. If another call remains, resize to `max(capacity * 2, returned_count)` only if at most 4096. Otherwise raise an explicit incomplete/bound-exceeded error. No sleep, spin-until-stable or allocation from an unchecked DWORD.
   - For a fitting positive count, read exactly that many entries with deadline checks; reject zero IDs, duplicates, or an absent/non-unique current PID as ambiguous/unavailable evidence. Do not inspect unused array slots. A complete result containing S exactly once satisfies this precondition; arbitrary peer PIDs are neither authenticated nor admitted to the Job.
   - Check the deadline again before successful return. Four exhausted attempts or any malformed/incomplete/unavailable/late result raises; there is no fallback to consoleless launch.

   These fixed bounds limit work, not the number of permissible processes in a new acceptance policy. Over-limit consoles simply cannot establish this precondition. A single complete API result is a point-in-time attachment observation, not an atomic snapshot across subsequent CreateProcess.

2. Extend `_launch_suspended`'s signature (1880–1889) with a **keyword-only** `inherit_current_console: bool = False` after the existing `before_resume` parameter. No arbitrary flags parameter. Compute flags as CREATE_SUSPENDED plus CREATE_NO_WINDOW for the default; for the opt-in use CREATE_SUSPENDED alone, only after `_require_current_console` succeeds. Reject non-boolean policy values rather than accepting truthy arbitrary objects. Retain argv, executable, command quoting, NULL environment, CWD, inheritable redirected log/NUL handles, STARTF_USESTDHANDLES and all existing startup settings.

   Place the opt-in query **immediately before CreateProcessW** (currently 1914), after standard handles/command buffer are prepared, within a narrow `try/finally` that closes the three already owned stdio handles whether the query fails, CreateProcess raises, or creation returns. The current unconditional three post-CreateProcess CloseHandle calls move into that finally; do not close any twice. Keep earlier partial-acquisition cleanup as-is. Check the deadline before querying and immediately before creation; on opt-in expiry do not create a process. Capture a false CreateProcess return's native error immediately, before CloseHandle operations, and raise that saved error afterward. This small ownership refactor is necessary to avoid leaking handles on the new pre-creation failure path; it must not swallow the primary failure or move process-handle ownership/cleanup out of its existing path.

   The default path must retain its exact creation flags and skip the console helper entirely. The post-create success path must still assign to the exact inner Job before callback and ResumeThread. Preserve post-creation deadline enforcement, creation FILETIME acquisition, before-resume helper authorization, suspended-process failure termination, confirmed waits, thread closure, process-handle handoff and cleanup error notes (currently 1931–1978). No CREATE_NEW_CONSOLE, DETACHED_PROCESS, CREATE_BREAKAWAY_FROM_JOB, new-process-group or alternative startup policy.

3. Set `inherit_current_console=True` at exactly two existing `_selfcheck` calls: `normal` at 3617 (fixed venv `-B` H `--nonzero`) and `tree` at 3878 (same fixed chain, `--tree-root`). Each launch independently rechecks S's current attachment; the tree launch cannot reuse the normal check. Preserve callbacks and all arguments byte-for-byte apart from the new keyword. Do not cache a success token. `_selfcheck` already calls authenticated `_handoff` before either launch. No call from an unauthenticated entry point may opt in.

4. Leave all three other call sites (4205 preflight-only, 4524 build preflight, 4622 build child) without the keyword and with their current defaults. Leave H's tree-child Popen and W's suspended S launch unchanged. Preserve normal expected actual exits **7/7** on authenticated retained launcher/interpreter handles; the strict unexpected-member failure, authoritative complete census, diagnostic-only details, zero/empty/zero prerequisite and later deliberate child/grandchild timeout/termination probe are untouched.

5. Route new exceptions through existing `_selfcheck` outer catch/finally (approximately 4043–4100). Normal failure stays in its existing launch phase and checkpoint; tree-precondition failure occurs after normal acceptance but must set overall BLOCKED_SELFCHECK, never final PASS. Use existing error type/message fields; do not add a schema, success field, filename or separate diagnostic mode. Query failures need a precise finite error message (phase/count/capacity/bound or captured native error), with no broad process enumeration. Preserve primary-versus-secondary persistence errors and termination failures. New query code owns no native handles. Stdio cleanup must run before propagating pre-creation failure; exact inner Job cleanup and all existing retained-handle closure remain mandatory.

## Deadline and safety claim

Use the original handoff-derived **10-second total QPC/monotonic deadline** everywhere; no relative allowance, reset, added wait, changed helper sleep or retry delay. At most eight list calls across the two helpers, with at most 4096 DWORDs per allocation. Late completion is failure. A native API is not preempted by a Python deadline check; W's existing outer deadline/Job controls remain required. No measured runtime fit is claimed.

S's trusted reviewed code must contain no console attachment/detachment mutation between query and launch. There is still an observation-to-creation interval and OS lifecycle behavior; the query is not an atomic console pin, host attestation or universal guarantee against a new host. If strict prevention requires an atomic association or API beyond this scope, stop for a boundary decision. Existing unexpected-member rejection remains the guard against an unsuccessful hypothesis. No post-launch disappearance, conhost name/path/hash, later empty Job, final forced cleanup or count subtraction can turn an unexpected census into PASS.

## Focused checks for a later implementation release

This planning turn executes none of these. After separate acceptance/release, the minimal affected static gates are `ruff check pipeline/scripts/run_teignmouth_float32_build3.py` and `ruff format --check pipeline/scripts/run_teignmouth_float32_build3.py`, using the coordinator's existing approved Ruff executable. Formatting, if necessary, must not cause unrelated edits. Report exact executable/commands/results and preliminary failures. S-only Python change requires no PowerShell AST or embedded C# compilation; unchanged evidence may be reused. No imports, executable tests, process probes or wrapper/self-check are implied by these requirements.

Static branch testing/review must trace: complete count 1 containing S; count 32 exactly fitting; too-small result then fitting resize; growth on every call; count >4096; zero/native error; binding/allocation failure; zero/duplicate/absent S; expiration before call, after call, while reading and before creation; first helper success but second precondition failure; default call skipping the API; query/CreateProcess exception with all stdio handles closed; successful create still assigned before resume. This is a review scenario matrix, not a claim those tests ran. If the independent reviewer requires executable mocks/tests, obtain separate authorization and a test-file scope decision; do not silently add tests or run S.

Handback must include exact final S hash, unchanged W/H/P hashes, a tightly bounded actual-byte diff against this baseline, all five call-site arguments/flags, all failure/cleanup paths and protected evidence preservation. No inverse root substitution is needed: this correction changes no path. No new evidence directory may be created during implementation/static review. Fresh fixed-root planning/review is a separate subsequent gate, even if the code review passes.

## Independent Sol review matrix

| Criterion | Required review proof |
| --- | --- |
| Authority/baseline | Exact pinned baseline, disposition 90 and accepted diagnosis; only authorized S spans changed; plan independently reviewed before implementation release. |
| Query semantics | Correct DWORD pointer/result signature; lazy query-only binding; non-NULL positive finite buffer; zero error captured immediately; oversized buffer never read; 4-call/4096 bounds; current S exactly once. |
| Scope | Exactly the normal/tree-root calls opt in; other three callers retain CREATE_SUSPENDED\|CREATE_NO_WINDOW and do not query; no H/W/P behavior or fixed-path delta. |
| Launch ordering | Redirected handles unchanged, query before creation, CREATE_SUSPENDED retained, exact Job assignment and authorization before resume; venv-to-base identity chain retained. |
| Failure ownership | Stdio handles closed exactly once on new failure paths; captured primary errors survive cleanup; retained process/thread/Job ownership and existing persistence/termination semantics preserved. |
| Acceptance | Actual exit7/7 and original authoritative census required; every unexpected member remains sticky BLOCKED; complete zero/empty/zero before unchanged deliberate tree probe; no conhost or disappearance exemption. |
| Deadline | Original 10s absolute deadline in both calls; bounded work; unavailable/incomplete/late never creates an opt-in child or supports PASS; no runtime fit claim. |
| Preservation | All consumed evidence immutable, no new root/files/schema/modes/dependencies; candidate/GIS/build inaccessible; separate unresolved exit/provenance facts remain. |
| Evidence | Required affected static gates pass against final bytes; review scenarios explicitly covered; no fabricated runtime or console/host-ownership claim. |

## Stop conditions and handback

Stop before implementation if independent plan review fails, baseline differs, or coordinator has not separately released the precise patch. Stop implementation/review if the change requires W/H/P, broader process/console APIs, allocation/attachment of a console, a new window, unsupported error/handle behavior, a weaker unexpected-member rule, another deadline, or changes to other launch defaults. Do not expand the query into console-host ownership or live process probes. Unavailable/oversized/incomplete/ambiguous/late attachment evidence is an ordinary non-PASS, not authority to broaden the patch.

A subsequent independently reviewed correction still needs separate fresh-root path binding/review and coordinator one-use authorization before any wrapper call. If a later authorized self-check still observes an unexpected member, preserve rejection and immutable evidence and obtain a bounded diagnosis; do not add a conhost allowlist. The plan grants no invocation, reservation or dependent collection/build authority.

Outer observed pwsh exit 1 versus internal recorded exit 2 and unsaved/untraceable historical `957157…` S remain separate unresolved matters. All consumed counters persist. No source, evidence, ledger/checkpoint, test or configuration edits occurred here. Work was static document/source reading/searching, file hashing and official-reference retrieval, plus this one requested plan artifact. No code/scripts, imports, parsers/linters/compilers/tests, live process inspection/probes, wrapper/self-check/preflight/runtime, manifests, GIS/numerical/build or browser work was executed. Return plan hash and stop for independent plan review/coordinator acceptance.
