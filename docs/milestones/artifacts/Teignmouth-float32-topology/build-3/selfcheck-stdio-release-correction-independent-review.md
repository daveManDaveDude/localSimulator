# Independent review — stdio-release correction

2026-10-25. Independent Sol reviewer `/root/sol_review_face_diag`, under disposition 95. **FIX REQUIRED: secondary stdio-release failures are not serialized into self-check checkpoint evidence.** The correction closes the earlier silent-success control-flow gap, but does not complete the requested persisted evidence contract. No operation or correction is authorized by this review.

Reviewed actual current S against the accepted console-inheritance plan, its independent plan PASS, dispositions 92–95 and prior implementation review SHA-256 `d46ec3ca18f2465ec5093109b4eb39b4e1f1353c8bfc6bf870cec6226923b34f`. Coordinator-reported Ruff check/format exit-0 results were read, not rerun.

## Exact source and scope

| Artifact | Independently recalculated SHA-256 |
| --- | --- |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `f50cbb07a0d745eb87d4d4c8e357e0168801507aae2de28f915e3d7ae30e4a55` |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| Correction handoff | `09436b0c03a9de7d6bce387c23b5a5d0f8a6348bd6aa177e6aba3028741cf5c3` |

An exact in-memory inverse of only the new outcome slots, creation-failure propagation, close loop and suspended-child guard/secondary-note block restores S SHA-256 `107e60ec49a929e83511e832db4858884ac4c60327110d4fb7a085fd731bfd0d`, the accepted previous submission. No reconstructed source was written or executed. This proves no other S bytes changed; W/H/P independently match unchanged bindings. No Git-index proof is claimed for these untracked operational files. The handoff's printed S digest contains a typo (`...1507aa2de...`); actual bytes match disposition 95's `...1507aae2de...`, as recorded above. This is a handoff metadata discrepancy, not additional source drift.

## Concrete residual and remedy

**1. `add_note` secondary details are omitted from persisted failure records — S 2037–2048, 2071–2082, 3681–3686 and 4165–4178.** The local per-handle confirmed/error slots are not attached to a returned record or exception attribute. On a pre-existing query/CreateProcess exception, the only close-failure indication is `primary_error.add_note(...)` at 2046. `checkpoint_normal_failure` saves only `type`, `str(primary)` and phase (3682–3686); the outer self-check error similarly saves only type and `str(exc)` (4171). `str(exception)` excludes its notes. No `__notes__` serialization exists in S. Consequently, even when these writes succeed normally, a console-query/native creation failure plus one or more false/raised CloseHandle outcomes produces persisted invocation/checkpoint errors indistinguishable from the same primary failure with all closes confirmed.

On successful CreateProcess followed by unconfirmed close, the RuntimeError message does preserve the generic release failure, but its per-role/native error detail and bounded child-cleanup observations are also note-only (2080, 2106). A traceback in stderr may render notes; that does not satisfy the requested self-check checkpoint serialization contract. This is a deterministic serialization omission, not a claim of actual runtime failure or unsuccessful disk persistence.

**Concrete remedy for a separately authorized correction:** retain close failure details in an explicit bounded, JSON-safe secondary representation that the existing self-check failure checkpoint/outer error serialization actually includes, or deliberately serialize the exception notes there. Preserve primary type/message/phase and original exception identity; make optional secondary extraction/formatting best-effort so it cannot mask the primary or prevent cleanup. Cover both the normal-helper checkpoint and tree-helper outer-failure path. Keep role/error/release-unconfirmed meaning truthful and preserve suspended-child cleanup observations. No new artifact/mode or runtime operation is needed to close this predicate. This report does not implement or authorize that remedy.

## Other required criteria

| Criterion | Static finding |
| --- | --- |
| False BOOL and raised close outcomes | **PASS.** S 2020–2036 distinguishes true from false/raised outcomes in fixed slots. A false result captures ctypes' native last-error copy at 2030 without an intervening clock/other native API; error-retrieval failure itself stays unconfirmed. Raised close exceptions are recorded as unconfirmed. Each stdout/stderr/stdin is attempted once, with no retry or transfer; one close exception does not skip later handles. |
| Earlier primary error | **PASS for propagation, FIX REQUIRED for saved secondary detail.** Query/CreateProcess exceptions traverse finally; false CreateProcess captures its code before cleanup and immediately raises the corresponding WinError (2013–2015). `sys.exception()` retains that active primary; optional add_note construction is guarded. No close failure replaces the earlier exception. The persistence omission is finding 1. |
| Created but release-unconfirmed child | **PASS for ordinary inspected Win32 paths.** 2049–2052 enters the existing created-process ownership try and raises before Job assignment, authorization or ResumeThread. `assigned` remains false, so 2086–2108 directly terminates the still-suspended process, performs a deadline-bounded wait (at most 2000ms and remaining original time), observes exit if signaled and closes its process handle; thread finally closes at 2109–2110. No successful return or false PASS from this branch exists. Termination failure/unconfirmed wait remains exceptional; static review does not guarantee native termination or handle API success. Cleanup observations currently remain note-only, as above. |
| All-confirmed path | **PASS.** Three true outcomes leave failure false. Exact Job assignment at 2053, deadline enforcement, creation identity and callback at 2059–2061 precede ResumeThread at 2062; process-handle transfer/thread closure are unchanged. Redirected stdio/command/environment/CWD are unchanged. |
| Console API, timing and finite work | **PASS, unchanged by exact inverse.** Lazy GetConsoleProcessList helper remains at 1880–1948, using the existing DWORD GetCurrentProcessId binding and WinDLL use_last_error behavior. Four calls/4096 DWORD bound, current-PID matching, oversized/zero/malformed/refused/late cases and original inherited deadline remain as previously reviewed. No console attachment/window API, reset or fallback was added. |
| Two opt-ins and default callers | **PASS.** Normal 3749–3759 and tree-root 4011–4021 alone opt in. Standalone preflight 4339, build preflight 4658 and numerical runner 4756 remain defaults. CREATE_SUSPENDED is always retained; CREATE_NO_WINDOW remains on default paths. Each opt-in rechecks immediately before creation; authenticated handoff remains earlier. |
| Strict acceptance and scope | **PASS, unchanged by exact inverse.** Actual launcher/interpreter exit7/7, retained identities/reaping, original complete census, unconditional unexpected-ID rejection, zero/empty/zero gate before the unchanged tree probe, diagnostic-only member observations, Jobs/deadlines/error guards and final cleanup remain unchanged. No helper/source/profile/acceptance exemption or path change was introduced. |

## Review limits and status

Work comprised static source/document reads/searches, file hashes, in-memory inverse comparison and writing this report. No code, checkpoint, disposition, manifest or prior evidence was edited. Retry evidence roots were not accessed or independently rehashed. No tests/imports/scripts/linters/parsers/compilers, process inspection/probes, wrapper/self-check/preflight/runtime/collection, roots, GIS/numerical/build or browser operations ran. Coordinator-reported static checks were not rerun; no runtime efficacy or induced failure is claimed.

Actual API/persistence/containment behavior, 10-second fit and **30-second runtime-profile fit remain unmeasured**. Outer exit1/internal2, historical census-association uncertainty and unsaved `957157…` provenance remain unresolved. Consumed roots/counters remain intact. FIX REQUIRED authorizes no next action or self-check. Candidate remains **NO-GO and unservable**, build 3 **unreserved**; a separate coordinator decision is required.
