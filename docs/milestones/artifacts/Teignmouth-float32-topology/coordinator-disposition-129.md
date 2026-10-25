# Coordinator disposition 129 — freeze retry-6 result for bounded Sol diagnosis

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** One-use gate 128. The command was attempted exactly once; the attempt is consumed.

## Result recorded — non-PASS

The authorized command was run once from `C:\vibe\localSimulator`:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File pipeline/scripts/invoke_teignmouth_float32_build3.ps1 -Mode self-check
```

The outer `pwsh` process returned exit code **1** with zero console output. Persisted caller record `caller-invocation.json` reports `STOP_OUTER_DESCENDANTS_REMAINED`, wrapper/native-launcher/supervisor chosen exit **2**, candidateBuildExecuted=false, candidateEligibleForServing=false, elapsed wall `4.7642439s`, and unexpected numeric outer Job PID **31876**. The saved records do not authenticate PID 31876's identity/incarnation/ancestry; do not infer a process class or inspect the live process table.

The one-use handoff was consumed. The self-check record is **BLOCKED_SELFCHECK** with `TimeoutError: deadline during bounded descendant containment census`, `outerCommandExitCode=2`, elapsed wall `4.737420600024052s`, and no candidate build. The normal helper stage was accepted: interpreter and launcher both exited 7, complete zero-member accounting before and after, complete empty PID census, no unexpected PIDs. The tree-root authorization was consumed and a contained child-start record exists; the bounded descendant containment gate did not complete. Its finally-termination record says termination requested and confirmed, `activeProcessCountAfterRequest=0`, `deadlineReached=false`. This is not a PASS and does not establish outside-Job termination.

The original QPC budget is 10.0s: saved QPC start `3220509045148`, deadline `3220609045148`, frequency `10,000,000`. The record's deadline-related error and `caller.deadlinePassed=true` coexist with approximately 4.7 seconds of recorded wall elapsed. Record this discrepancy without presuming clock failure, a source defect, or an exact wall/QPC cause. Supervisor stderr contains the same TimeoutError JSON; supervisor stdout and all helper/tree stdout/stderr logs are empty.

## Immutable retry-6 evidence inventory

The created root is now consumed. Preserve every file byte-for-byte; do not rerun or clean it. Read-only inventory at handback:

| Relative path | Bytes | SHA-256 |
| --- | ---: | --- |
| `caller-invocation.json` | 3228 | `988078a897590bc8a83fe84f8a6110563d3a3741e599a50219bcaf9172bb8dfc` |
| `run-1/invocation.json` | 15129 | `83886601f972d4534ad8127ae4631c992ee5710bfe1d02db5c8aed1b9fc1883a` |
| `run-1/nonzero-authorization.consumed.json` | 1049 | `5e48c88820629f3c260365f12df0a426c470847ee36a5e02286efa4f1ccdf871` |
| `run-1/nonzero-helper.json` | 53 | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| `run-1/nonzero-script-start.json` | 698 | `c7389703290f57b5a599e817a67f0aab8ac875ff82ba6f71ea5de1a7f7be8157` |
| `run-1/nonzero.stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run-1/nonzero.stdout.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run-1/tree-child-started.json` | 584 | `51e767bce84e1b1fc0fdb733c5b7942942ac2f884226462176a69150bdeaf3df` |
| `run-1/tree-root-authorization.consumed.json` | 1051 | `9301fa3972f67592cb98efe332dbb842762fdfbaef07df9f3b21ce3016ba610e` |
| `run-1/tree-root-script-start.json` | 699 | `65d4e5b4d8032360fd6970de579becea90b6c17a19ffba51c4483874ce208def` |
| `run-1/tree-root-started.json` | 325 | `725a8d1651aaef3d9475cb225a36408e1946c81e1347e22496f9b21b736ac550` |
| `run-1/tree.stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run-1/tree.stdout.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `self-check-handoff.consumed.json` | 1602 | `293d079848fac2f889ead51335409b783f0173bd1cf79d45252ff6451f64962f` |
| `supervisor-script-start.json` | 1037 | `213c02f98c601deb50ca73b19b66c89b8ac39ea1e2198cc83091121a748ca921` |
| `supervisor.stderr.log` | 120 | `367bffd2196476a7b0f35648c8f87ab74e290683a9a4efbdf1e32f1e9dc1c437` |
| `supervisor.stdout.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

No file was deleted, rewritten, or replayed. No live process inspection occurred. Retry-1 through retry-5 remain consumed, immutable and non-PASS. Retry-6 is also consumed and non-PASS; no retry-7 path is selected or reserved.

## Read-only Sol diagnosis only

Authorize Sol 6.1 to inspect the current reviewed W/S/H/P source, the accepted retry-6 path plan/reviews, and only the newly generated retry-6 records above. Do not read consumed retry-1–5 evidence contents. Diagnose the specific question: **Why did the saved self-check report `deadline during bounded descendant containment census` and the caller report `deadlinePassed=true` while the two wall-elapsed records are about 4.7 seconds for a 10-second QPC budget?** Determine which timing domain/status fields support a cause, whether the stage result is a genuine bounded census timeout or an accounting/diagnostic inconsistency, and what minimal next action (source correction, additional non-executing diagnosis, or stop) the evidence supports. Separately state that PID 31876 identity is or is not established from saved retry-6 records; do not infer it.

This is one read-only diagnosis, bounded to the retry-6 evidence and current source, with no new execution. No source/evidence edits, normalization, parser/compiler/linter/test/import, runtime/process-table inspection, path creation, retry-7 planning/root selection, self-check, preflight, candidate/GIS/numerical build, reservation, browser/publication, commit, push or merge. Record exact evidence references and stop for coordinator decision.

## Preserved status

The retry-6 root remains present and immutable. Its one-use authorization is exhausted. Candidate remains **NO-GO and unservable**; build 3 unreserved; 10-second QPC deadline unchanged. No attempt counters reset. No further code change or retry is authorized until the bounded Sol diagnosis and a new coordinator disposition.
