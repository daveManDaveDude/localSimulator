# Retry-3 unexpected inner Job member — read-only diagnosis

2026-10-25. Sol 6.1 medium `/root/sol_review17_plan`, under disposition 78. Diagnosis only, using saved retry-3 evidence and static source/official references. **Retry-3 remains consumed, immutable and non-PASS.** The evidence now proves a complete unexpected-member observation, but does not identify that process or its liveness. Recommend narrow S-only member-detail evidence, retaining rejection, rather than an acceptance relaxation. Stop for coordinator acceptance and a separate next plan before implementation.

## Exact current revision and evidence

Read disposition 78 and the complete retry-3 caller, consumed handoff, supervisor-start/logs, run invocation, consumed nonzero authorization, helper/start markers and empty helper logs. Rehashed all eleven saved files; all match disposition 78. No live-process inspection or runtime probe was performed.

| Current source | SHA-256, recalculated |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `c3f1f49cb574793c1cdbc2d905fd3d36f646b6f32ffb7c200a96c9792d5ce84f` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `d498bc294390d8645c6acc59773ba50f417493926d8bbfb3564d34504e8a407a` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `cf1145b33397066559b89c11aa1cb0ebcf4d6d4d470f6521d96fe9e1f4ecccab` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| Disposition 78 | `861d5c6405d148d99581cd9815017d67327a7efe26bbc3995ca32066af9f0432` |

| Retry-3 file, relative to `.codex/build3-supervisor-selfcheck-retry-3/` | SHA-256 |
| --- | --- |
| `caller-invocation.json` | `f1bf3a880a821626daef625f60459d037a8aa9509246e401a06f9440cb8134d6` |
| `self-check-handoff.consumed.json` | `dd82b4bd6cdfafa76fd5be2505cf438125f9deb70d37f73dbaf03a7f719d93b6` |
| `supervisor-script-start.json` | `bf0f5eed47455f27a037dea7fbeca068bf4ac2d9a72598e70c21c90b7c835a90` |
| `supervisor.stderr.log` | `18d4873d35189bf11f26f2df45a60574330fde3c27bf02371542b37a4b46fea8` |
| `run-1/invocation.json` | `dcf98d8471df615acbaa74d3eece7f8a774e86cac22b0864931e556f2ae627e5` |
| `run-1/nonzero-authorization.consumed.json` | `0b64cd4ffc826e052423ab501f55da267675ee8f5c345c4c7613b6076b283d3a` |
| `run-1/nonzero-helper.json` | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| `run-1/nonzero-script-start.json` | `0da552f3943a321f31e5bceac24fe74471e6a1c75367a852430f2e2d3ae0ffa3` |
| `supervisor.stdout.log`, `run-1/nonzero.stdout.log`, `run-1/nonzero.stderr.log` (each empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

W caller/run records report exit 2; disposition 78 separately records the invoking `pwsh` command returning **1**, without console output. Preserve that difference. This diagnosis does not identify or correct its cause, nor treat recorded exit 2 as the observed outer command exit.

## Exact observed sequence

The authenticated chain is W PID 2192 → S venv launcher 12416 → S base interpreter 20272 → normal-helper venv launcher 27240 → H base interpreter 37428. Helper nonce is `433443b23fa041118b4d1843a9990e52`. Known helper creation FILETIMEs are 134373848192829551 (launcher) and 134373848193074866 (interpreter). These are observations, not future constants.

The inherited QPC start/deadline is 3025640591884/3025740591884 at frequency 10000000: 10 seconds total. Both known helper handles were observed signaled, without timeout, and both actual exits were 7. The marker corroborates intended exit 7. Both owned handles were still retained at first snapshot; handle release/drain had not run (`drainIterations=0`).

At monotonic 302565.3557816–302565.3558296, `firstSnapshot` phase `post-wait` recorded:

- accounting before **1**, accounting after **1**, each observed without error;
- successful complete PID census, assigned/listed **1/1**, returned bytes **16**, buffer capacity 32/264 bytes, one attempt;
- only member **20712**, not in authenticated known set `{27240,37428}`;
- no identity/image/creation/parent/wait/exit detail for 20712.

S 2822–2832 persisted that snapshot and correctly raised `post-wait inner Job snapshot contains an unexpected process`. The error's primary phase is `drain-inner-job`; the later zero checkpoint did not erase it or advance into the tree test.

At 302565.3580242–302565.3580789, `latestSnapshot` phase `exception-checkpoint` recorded complete **0/empty/0**, about 2.2 milliseconds after the first snapshot. This checkpoint is captured by the normal-stage exception handler **before** the outer finally's Job termination. Thus the unexpected membership disappeared before S's recorded final forced-cleanup request; it cannot be attributed specifically to that later request. Another actor's exit/termination or object/Job bookkeeping completion in between is not identified by the records.

Finally S reported termination requested/confirmed with zero active processes; W recorded outer termination confirmed. No tree-root auth/marker/log exists; no deliberate tree probe was reached. Candidate-built/execution/serving fields remain false. These final observations preserve non-PASS and do not establish normal-stage acceptance.

## How the observed member can enter the measured set

S `_create_job` (1855 onward) creates a fresh unnamed inner Job, sets only its existing kill-on-close flag, and does not assign S itself to it. S `_launch_suspended` (1880 onward) creates the requested launcher suspended/no-window and explicitly assigns **that process handle**, whose returned PID is 27240, before resume. Its authorization and retained native identity are bound to that same launcher. No S call explicitly assigns numeric PID 20712, and the Job handle is not a generic path-selected/shared named Job.

The normal helper's interpreter is discovered/authenticated as child PID 37428 and a member of that inner Job. H's `nonzero` mode writes its marker, waits at most 0.15 seconds and returns 7. Its only explicit `subprocess.Popen` is in the **other**, later `tree-root` branch, beyond that return. S has not launched that branch. The evidence does not support claiming PID 20712 was H's intentional tree child, a third S-launched helper, the wrapper or S itself.

A member can also arrive by inherited membership of a created descendant or a nested child Job, rather than another explicit S assignment. Microsoft's nested-Job model makes the child's member set a subset of its ancestors and aggregates child membership/accounting upward. Parent-Job peers are not automatically inserted downward into S's inner Job. [Nested Jobs](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs)

The pinned-version **reference** CPython v3.13.7 redirector source supplies an additional relevant launch boundary outside H's Python branch: `launch()` creates a Job, sets kill-on-close/silent-breakaway on that private Job, duplicates standard handles, creates the base interpreter with creation flags **0**, assigns it to the private Job, then waits and returns its exit. S's launcher creation flags therefore do not describe every downstream native creation call. This is static reference-source behavior, not attestation of PID 20712 or a binary-build provenance proof. The existing S inner no-breakaway gate must not be changed because of that reference. [CPython v3.13.7 venvlauncher.c, launch](https://github.com/python/cpython/blob/v3.13.7/PC/venvlauncher.c#L360-L434)

Windows distinguishes no-window, inherited-console and new-console creation behavior. Downstream interpreter/runtime/OS infrastructure could therefore be relevant to an additional short-lived process even though H's nonzero branch has no Popen. **A console host or other OS/runtime auxiliary is a hypothesis only**; no saved image/parent evidence identifies 20712 as one. Do not change console/creation flags or allowlist a guessed class in this correction. [Process Creation Flags](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags)

The strict census uses the documented two-DWORD header then pointer-sized IDs. Its observed 8-byte header plus one 8-byte PID fits returned length 16, with assigned/listed equal and no query error. No recorded capacity/truncation/invalid-ID evidence supports dismissing 20712 as buffer garbage. The API includes nested child-Job members, not only processes explicitly created by S. [JOBOBJECT_BASIC_PROCESS_ID_LIST](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_process_id_list)

## Classification supported by evidence

**Supported:** 20712 was a different numeric member reported by a complete inner-Job query during the first accounting envelope, and was absent from the next complete checkpoint. S rejected it before releasing the expected pair or starting the tree probe. This is stronger evidence than retry-2's bare accounting count and cannot be reduced to “one of our retained known processes” by subtracting one.

**Not supported:** its executable/class, creation time, parent/ancestor, whether it was runnable/signaled/terminated at the query, whether its process object was retained, exactly when/how it entered/exited the Job, or whether a later same numeric PID would represent it. Job membership is not a per-handle liveness observation. The two expected process exits do not prove all descendants/infrastructure have disappeared. Final zero does not identify a process or prove historical benignness.

There is no recorded escaped-descendant observation: 20712 was **inside** the queried Job set. No saved ancestry/liveness observation establishes an escape elsewhere. Equally, no native identity exists to declare it a harmless OS auxiliary or false positive. Possible short-lived contained execution, terminating/retained object membership or runtime/OS-managed process remain unresolved classes. A future PID lookup now would not reconstruct its historical identity and is prohibited by this diagnosis.

## Minimal next recommendation: missing identity evidence, not relaxed acceptance

Recommend a narrow **S-only evidence improvement** in `_selfcheck_job_snapshot` and the normal-stage capture call sites, under the accepted reaping plan's requirement to preserve unexpected-member identities/liveness. This report is not that implementation plan or dispatch. W/H/P behavior, actual command/flags/Job setup and current rejection predicates do not need to change to obtain the missing information.

On observing an unexpected census PID, collect member detail **immediately after reading the complete census and before slow JSON checkpoint persistence or deliberate rejection**. Use existing native APIs and the same original deadline, only for PIDs just enumerated from this exact owned inner Job:

- best-effort open one query/SYNCHRONIZE handle; record open error/status if the process disappears or is inaccessible, never treat that as proof of natural exit;
- on the same acquired handle observe exact Job membership, creation FILETIME, canonical native image/path/hash, nonblocking wait and actual exit code/availability, with timestamps and individual query errors;
- do not equate the acquired handle's PID with the earlier census incarnation automatically. Record acquisition timing and exact membership; creation/membership mismatch, PID reuse or disappearance stays unknown/non-PASS. No reopening to fabricate historical authentication;
- record parent/ancestor evidence only when collected with creation-time-aware identities during the relevant interval. A raw current PPID, familiar basename, signature or System32 location alone is not a trusted origin/class exemption;
- close every acquired observation handle exactly once and record unavailable detail separately from the census's original completeness. These diagnostic handles may affect object lifetimes; mark observation ordering rather than claiming an untouched lifetime experiment.

Add one bounded membership observation while the authenticated normal pair is still present (e.g. immediately after helper-start authentication) to improve the chance of recording short-lived auxiliary identities, without polling the entire host or creating a new diagnostic executable/mode. Keep first post-wait snapshot and exception-checkpoint meanings distinct; do not overwrite the original observation with latest zero. If an unexpected PID is observed earlier, its rejection remains sticky; do not wait for disappearance to erase it. First/latest member details and bounded counts in the existing invocation schema are sufficient; no new record filename.

If native path/hash work cannot complete before a member vanishes, retain partial identity, creation/wait/membership/query statuses. No inability to identify 20712 authorizes adopting it. Preserve primary error through secondary evidence failures and final cleanup; the previously accepted nested reporting guards must remain intact.

Keep the exact accepted invariants: authenticated expected launcher/interpreter, actual exits 7, no PID-reuse substitution, complete census, zero/empty/zero normal-complete gate, strict containment, original 10-second deadline, unchanged later tree probe and no normal-stage forced-cleanup-to-PASS. The current **unexpected-PID rejection is correct**; removing it, delaying it until an empty checkpoint, excluding a guessed console host, subtracting counts, changing native flags or trusting a process by basename would exceed this recommendation.

## Static criteria and stop boundary

A later concrete plan must name the S additions and touch only these evidence paths, with independent review of same-handle identity, bounded exact-Job scope, acquisition/disappearance/PID-reuse semantics, per-query unavailable states, no handle leak/double-close, and unchanged sticky rejection/empty-membership/deadline/cleanup gates. No changes to `_launch_suspended`'s process flags, default APIs/permissions beyond the existing specified query/wait rights, H's behavior, schemas, source trust/roots or candidate logic are inferred.

Stop if a missing native API/dependency/schema/runtime mode or wider process-inspection capability is needed, if identities cannot be acquired within the original budget, or if the desired solution is to permit a newly identified auxiliary class. The latter requires actual captured identity/origin evidence plus a separate narrowly justified plan/trust-profile decision; this diagnosis supplies neither a class identification nor acceptance authority.

The outer exit **1 versus recorded 2** discrepancy is preserved as a separate uninvestigated fact, not silently repaired or diagnosed by this membership evidence recommendation. Runtime self-check completion and the 30-second runtime profile remain unmeasured. Original/retry-1/retry-2/retry-3 evidence is immutable; the `957157…` historical S digest remains unsaved/untraceable. No current-source inspection repairs that history.

Coordinator must accept this diagnosis, obtain a separate narrow plan/implementation/independent review, and reconcile a fresh fixed-path gate before any later one-shot wrapper attempt. Do not reuse retry-3, create a new evidence root now or authorize collection/verification/manifests/GIS/numerical/candidate build/reservation/serving/browser. Candidate remains NO-GO/unservable; build 3 unreserved; counters/geometry/recipe/numerical/source/product constraints unchanged. No commit/push/merge.

Work comprised only saved-evidence/source/document reads/searches, file hashing and official reference-source/document retrieval, plus writing this diagnosis artifact. No code/evidence/checkpoint/ledger edits, operational evidence writes, new root, tests/imports/linters/parsers/compilers, probes/process inspection, wrapper/self-check/preflight/runtime, GIS/numerical/build or browser application work occurred. Return report hash for coordinator acceptance; stop here.
