# Retry-4 unexpected member — bounded console-lifecycle diagnosis

2026-10-25. Sol 6.1 medium `/root/sol_review17_plan`, under disposition 89. Read-only diagnosis from saved evidence, current source and official references. **Retry-4 remains consumed, immutable and non-PASS.** No conhost allowance, another attempt, implementation or self-check is authorized by this report. Return to coordinator for a separate narrow plan decision.

## Exact current baseline and saved evidence

Read disposition 89, retry-4 caller/run records, consumed handoff, supervisor/helper starts, consumed nonzero authorization, marker and logs, relevant W/S/H launch/Job/nonzero paths and prior retry-3 diagnosis. Rehashed all eleven retry-4 files; each matches disposition 89.

| Current source | Recalculated SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `64bf2c4abf822ad55252789315d71731d2660d66bb5b6bc7d60f810f2de492c7` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| Disposition 89 | `98a634f7a3ba9cf1607124499df5c30eaf796541e2181814f3f011a7784d194a` |

| Immutable retry-4 file, relative to `.codex/build3-supervisor-selfcheck-retry-4/` | SHA-256 |
| --- | --- |
| `caller-invocation.json` | `127af0f90b23a5048e72eedf992080016491a3a9590f694ea63d15f3dd244fe9` |
| `self-check-handoff.consumed.json` | `842925a205014286e6d9a5b5cf1822cfe6f41499f4b0bf3a63c5d9831264631d` |
| `supervisor-script-start.json` | `72f9f46afadbd1199b5bffb091ed9dba06a23297c194f6de985f07a27e0d306d` |
| `supervisor.stderr.log` | `18d4873d35189bf11f26f2df45a60574330fde3c27bf02371542b37a4b46fea8` |
| `run-1/invocation.json` | `db81b0941a113733e5661005c5e1f99f89431a36701f5ae7a8b90acc95b720f4` |
| `run-1/nonzero-authorization.consumed.json` | `ca6e9da7f0bc10e4b49160c1d66ceba3fad31097e38548cbc3d0671179ea7627` |
| `run-1/nonzero-helper.json` | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| `run-1/nonzero-script-start.json` | `fc551dde8e2be7b93238561092d28e538402b7265e77d1fb2e7ebe6a32957ec2` |
| `supervisor.stdout.log`, `run-1/nonzero.stdout.log`, `run-1/nonzero.stderr.log` (each empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

The observed outer `pwsh` exit is **1**, while caller/run evidence records chosen/native-launcher/supervisor exits **2**. These are distinct facts. The discrepancy remains uninvestigated here; no fix to W/exit reporting is bundled with console diagnosis. The unsaved/untraceable historical S `957157…` limitation also remains.

## What retry-4 proves

W launcher assignment/resume/start authentication succeeded. Known nonzero helper launcher PID **7408** and interpreter **16992** were authenticated and both actual process handles yielded signaled exit **7**, without timeout. H's marker corroborates intended exit 7. H's nonzero branch writes the marker, sleeps at most 0.15 seconds and returns; its explicit Popen is in the unreached tree-root branch.

First post-wait primary snapshot at monotonic **305004.1212331–305004.1212835** is complete: accounting **1 before/1 after**, assigned/listed **1/1**, returned length 16, one PID **33552** outside the authenticated pair. This is not S's PID (22204), the outer launcher (5144), or a count of one of the known pair. The primary list format/counts are internally consistent. S correctly rejected it before handle release/drain/tree launch.

Subsequent same-handle diagnostic reads for numeric PID 33552 recorded:

- open at approximately 305004.1213000–305004.1213096; exact inner Job membership **true** before and after queries;
- one unchanged creation FILETIME **134373872580578089**;
- zero-time wait **258/WAIT_TIMEOUT**, observed nonsignaled around 305004.1213266–305004.1213280;
- raw exit value **0** from a separate slightly later query around 305004.1213292–305004.1213306;
- exit FILETIME changing from **0** at the earlier GetProcessTimes read to **134373872583509515** at the later read around 305004.1228988–305004.1229098;
- native raw/canonical path **`C:\Windows\System32\conhost.exe`**; disk SHA-256 **`c86146188b78e484f32cc29e2331689659943b47689a85570342044f499938ac`**;
- equal available device/file-ID/size/type/timestamp metadata before hash, after the same-path hash and after re-resolving the original raw path; successful diagnostic CloseHandle reported after these observations.

These facts establish a later observed process object with that native path and contemporaneous exact Job membership. Its wait/exit/time reads are separate time samples: they are consistent with a short-lived exit transition, not grounds to rewrite the earlier WAIT_TIMEOUT as signaled. No final signaled wait was captured for this diagnostic handle. Do not compress the sequence into “already exited throughout” or “still running throughout.”

The complete exception checkpoint at **305004.1254957–305004.1255506** is **0/empty/0**; final S cleanup later requested/confirmed termination, and W outer termination was confirmed. The empty exception checkpoint precedes S's final forced request; that later request cannot explain the earlier disappearance or retroactively pass the failed normal gate. No tree probe, candidate build, GIS or identity collection ran.

## What remains unproved

`censusIdentityAssociation=unproven` and parent/origin/class remain explicitly unestablished. The later handle's creation/path/membership observations do not by themselves attest to the exact incarnation at the earlier census instant. Holding that handle stabilizes the **later opened object**, not the preceding PID-to-object association. Do not look up PID 33552 now or infer continuity from numeric equality/final zero.

Disk-path metadata agreement and hashing are useful bounded observations. They do not establish mapped executable bytes, Microsoft signature/ownership, console association, which process caused the host, absence of same-metadata races, or complete process ancestry. `conhost.exe`/System32/hash is not a defensible allowlist rule. Membership true after an exit transition may still concern a retained process object; it is not evidence of executing user code at every read. No escape is observed by this record, and no benign-owner exemption is established.

The creation FILETIMEs order the later observed conhost object **after** known helper launcher creation (134373872580481919) and **before** helper interpreter creation (134373872580724306). That is consistent with host allocation at the native launcher-to-interpreter boundary. It is supporting context, not proof of parent/console ownership or original census association. Retry-3's earlier PID20712 has no image identity and cannot retrospectively be called the same class.

## Likely Windows/CPython mechanism, bounded to the sources

S `_launch_suspended` (1880 onward, CreateProcessW flags at 1920) creates each venv launcher using **CREATE_SUSPENDED | CREATE_NO_WINDOW**. It then assigns that launcher to the inner Job before resume. The Python helper itself has no explicit third-process creation in its nonzero branch.

The reference CPython **v3.13.7** venv redirector's `launch()` duplicates standard handles, creates its own nested Job and creates the actual interpreter with flags **0**, then waits for that child. It does not propagate S's CREATE_NO_WINDOW flag to the interpreter. This is reference-source support for an important second creation boundary, not new attestation of the installed binary or PID33552. [CPython v3.13.7 venvlauncher.c](https://github.com/python/cpython/blob/v3.13.7/PC/venvlauncher.c#L360-L434)

Microsoft documents that CREATE_NO_WINDOW leaves the console handle unset; normal console processes otherwise inherit their parent's console by default, with console creation governed by the actual creation context. Therefore a launcher made consoleless followed by a flags-zero console interpreter is a plausible source of a new console-host lifecycle. A newly created descendant/associated host may remain in the owned/nested Job after the authenticated Python pair exits while it completes teardown. [Process Creation Flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags), [Creation of a Console](https://learn.microsoft.com/en-us/windows/console/creation-of-a-console)

**Most likely mechanism:** console lifecycle at that redirector boundary, with an auxiliary host terminating just after its Python clients. Retry-4's conhost path, creation ordering, same-handle transition and later empty Job make this substantially better supported than retry-3's generic hypothesis. They still do not prove exact console ownership or authorize ignoring it. Nested membership includes child-Job processes; it does not imply every member was explicitly created by S. [Nested Jobs](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs)

## Smallest safe corrective direction for a separate next plan

Prefer **preventing an avoidable new helper console**, while retaining every unexpected-member rejection, over adding a conhost exemption. A narrow next plan can investigate/justify an **S-only, self-check-helper-specific console-inheritance launch policy**:

1. Establish that authenticated S is already attached to an existing console before opting into inheritance. A bounded query such as GetConsoleProcessList can report current-console clients; it is not a conhost-owner API or a replacement for Job membership. If such a new binding is chosen, its exact query-only scope, finite buffer handling and original-deadline use must be explicitly accepted in that next plan; no API is added/executed here. Absent/inaccessible/incomplete console evidence must fail closed, not allocate/attach a console or alter W. [GetConsoleProcessList](https://learn.microsoft.com/en-us/windows/console/getconsoleprocesslist)
2. Only after that precondition, consider a keyword-only launch policy in S `_launch_suspended` used solely by `_selfcheck`'s **normal and tree-root helper launches** (currently 3617 and 3878). For those two, preserve CREATE_SUSPENDED/assignment-before-resume and redirected NUL/log standard handles while permitting inheritance of the verified existing console, rather than forcing the venv launcher consoleless with CREATE_NO_WINDOW. Do not set CREATE_NEW_CONSOLE/DETACHED_PROCESS/AllocConsole/AttachConsole, create a visible window, remove Job assignment or bypass the approved venv→base chain.
3. Preserve `_launch_suspended`'s current flags/default for preflight/build callers (4205/4524/4622); no global removal of CREATE_NO_WINDOW. W/H/P remain behaviorally unchanged. The intended result is fewer avoidable helper-owned infrastructure processes, **not** broader admission of them. The strict complete Job census/identity/exit/empty-membership predicates remain the check on whether the hypothesis actually works.

This is a **proposed narrow behavior/launch-policy amendment**, beyond the previous evidence-only scope and previous fixed-flag contract. It is not an accepted implementation plan and must not be sent to Luna as already authorized. Coordinator must reconcile it and its current-console precondition first. If that amendment is inappropriate or cannot establish safe inheritance without a new window/unsupported API scope, keep the launch policy unchanged and return the missing console-association evidence/design requirement. Do not substitute a conhost allowlist or relax the original gate.

Changing only delays, releasing known-pair handles earlier, or waiting until the unknown PID disappears would not establish ownership and could make a real unexpected descendant disappear before rejection. Those are not recommended fixes. Another image-name/hash/parent-PID observation alone is also insufficient to justify admission. If the chosen design instead wants to admit an auxiliary process, it requires a separately specified authenticated ownership/console/lifecycle proof, not familiarity with this path.

## Exact acceptance checks for the later narrow plan/review

Before any Luna correction, the coordinator must accept an explicit plan covering the precise console precondition/API/flag amendment or an alternative bounded evidence step. Required acceptance:

- normal helper launcher/interpreter still authenticate exact native PID/creation/image/Job identities and each observed exit 7 on their pinned handles; no direct-base bypass;
- any inheritance branch is restricted to the two fixed self-check-helper calls, fails when S's console precondition is not established, does not create/attach/free a console or show a new window, and preserves redirected stdio and default flags for all other callers;
- CreateProcess remains suspended; assignment/authorization occur before resume; no breakaway/new job exemption or memory cap; nested Job/cleanup/handle ownership/deadline semantics unchanged;
- current unexpected-ID rejection remains sticky and unconditional, including any future conhost member. No allowlist, fixed subtraction, parent/name-based admission, later-empty override or normal cleanup-to-PASS;
- strict complete accounting/PID capture and **zero/empty/zero before the tree probe** remain, as do handle-release truthfulness, diagnostics' mandatory close/partial stability semantics, full deliberate tree-child membership/timeout/termination evidence and no candidate/GIS reachability;
- all queries, preconditions, launches, waits and persistence use the original inherited **10-second total**. No fit guarantee or native-call preemption claim; unavailable/late observations are non-PASS. No longer H sleep or new relative allowance;
- S-only behavioral delta, unchanged W/H/P/protected hashes, all consumed evidence immutable, and best-effort reporting cannot mask the primary error or prevent cleanup. Any next fresh-root path change is a separate exact W/S/H binding/review gate;
- independent non-implementing Sol review of actual source/delta and affected authorized static checks before any separately gated one-shot. Static source/API reasoning does not prove the hypothetical change removes hosts on this machine.

Stop if console attachment/inheritance cannot be established within the narrow API/visibility/deadline scope, another mode's flags must change, auxiliary membership must be exempted, or preserving strict identity/census/cleanup is impossible. Return the precise boundary; do not accumulate ungated attempts. If a later reviewed change still produces an unknown member, preserve non-PASS and its evidence rather than adding a new exception ad hoc.

## Status and handback

No source change is made or authorized here. Coordinator acceptance of this diagnosis and a concrete separate plan, Luna correction, independent review, a fresh unique fixed-root binding and a fresh coordinator gate are required before any further wrapper attempt. Retry-4 cannot be replayed. No self-check/run permission is granted or implied by the recommendation.

Outer exit1/internal2 and unsaved `957157…` history remain separate unresolved facts. All previous evidence/counters, source/recipe/geometry/numerical/product/geographic constraints remain unchanged. Candidate NO-GO/unservable, build 3 unreserved. No collection/verification/manifests/GIS/numerical/build/serving/publication/browser/commit/push/merge work.

Work consisted only of immutable evidence/source/document reads/searches, file hashing and official static reference retrieval, plus saving this requested diagnosis report. No source/evidence/checkpoint/ledger edits, live process lookup, tests/imports/parsers/linters/compilers, probes, wrapper/self-check/preflight/runtime or other operational action occurred. Return report hash for coordinator decision; stop here.
