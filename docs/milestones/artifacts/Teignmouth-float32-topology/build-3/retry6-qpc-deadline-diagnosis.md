# Retry-6 deadline diagnosis — bounded read-only report

2026-10-25. Issue `Teignmouth-float32-topology-representation-1`; disposition 129. **The saved result is consistent with expiration of the deliberate tree probe's shorter deadline, while the inherited ten-second deadline remained unexpired. `caller.deadlinePassed=true` means the deadline check passed, not that the deadline elapsed. The evidence does not require a QPC domain/accounting mismatch to explain the result.** Retry-6 remains consumed and non-PASS.

## Exact source/evidence bindings

Independently rehashed current reviewed sources:

| Source | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `f600efc92fd040aa5b91cf543210be139ed50f895eba7d62c34175e73dc7dc8b` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `75678b51d0e17d89862bf0a7ee3446014969ba73aae6cd31606288553b163e27` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

All **17** retry-6 filenames, byte lengths and hashes match disposition 129's full inventory. Relevant records below are relative to `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\`:

| Record | SHA-256 |
| --- | --- |
| `caller-invocation.json` | `988078a897590bc8a83fe84f8a6110563d3a3741e599a50219bcaf9172bb8dfc` |
| `self-check-handoff.consumed.json` | `293d079848fac2f889ead51335409b783f0173bd1cf79d45252ff6451f64962f` |
| `run-1/invocation.json` | `83886601f972d4534ad8127ae4631c992ee5710bfe1d02db5c8aed1b9fc1883a` |
| `supervisor.stderr.log` | `367bffd2196476a7b0f35648c8f87ab74e290683a9a4efbdf1e32f1e9dc1c437` |
| `run-1/tree-root-script-start.json` | `65d4e5b4d8032360fd6970de579becea90b6c17a19ffba51c4483874ce208def` |
| `run-1/tree-root-started.json` | `725a8d1651aaef3d9475cb225a36408e1946c81e1347e22496f9b21b736ac550` |
| `run-1/tree-child-started.json` | `51e767bce84e1b1fc0fdb733c5b7942942ac2f884226462176a69150bdeaf3df` |

## What the two deadline reports mean

W1942 and W2061 assign `deadlinePassed = currentQpc < deadlineQpc`. W2062–2065 treats **false** as global deadline failure. Thus the saved **true** means within the global deadline. Its name is ambiguous in ordinary English, but its comparison and acceptance use are consistent. It does not report a ten-second timeout.

The consumed handoff and caller agree on start `3220509045148`, deadline `3220609045148`, frequency `10000000`: precisely ten seconds. S632–633 converts them to `322050.9045148` and `322060.9045148`. `run-1/invocation.json` records those same monotonic values. Both elapsed fields use the inherited wrapper start, not a fresh supervisor-start budget: S4194 is `time.monotonic() - started`; W2060 is `(finalQpc-startQpc)/frequency`. Despite its label, S's `elapsedWallSeconds` is this monotonic delta. S's separate `startedUtc` is populated at record construction (S3575), not an alternate start for that delta.

Arithmetic on saved fields gives:

| Observation | Inferred counter-seconds at observation | Remaining global budget |
| --- | ---: | ---: |
| S error record, elapsed `4.737420600024052` | `322055.6419354` | `5.262579399975948s` |
| W final clock, elapsed `4.7642439` | `322055.6687587` | `5.2357561s` |

These derived values are consistent with `deadlinePassed=true` and S's `finallyTermination.deadlineReached=false`/3000-ms wait budget. They do not show global budget exhaustion. S637–644 also checks native QPC frequency and agreement with `time.monotonic()` within 0.25s during authenticated handoff. Reaching the later stage establishes that check passed then; it is not continuous clock attestation. No saved field demonstrates a subsequent clock discontinuity/domain mismatch, and none is needed for the observed result.

## Why a census timeout can occur around 4.7 seconds

The normal stage is saved as `normalHelperCompletion.phase=normal-complete`, `finalAcceptance.accepted=true`, launcher/interpreter exit7/7, complete empty PID census and accounting0/0. Tree-root and child markers follow. In that later self-check stage, **S4059 deliberately sets `tree_cutoff = min(deadline, time.monotonic() + 3.0)`**. S4060–4065 passes this shorter cutoff both to `_wait_process` and its `_assert_tree_contained` callback. It does not pass the inherited ten-second deadline to that census.

The exact saved error string occurs at S402–403, when the bounded Toolhelp row census finds `time.monotonic() >=` its supplied deadline. Earlier normal-stage containment callbacks use the inherited deadline and completed before the accepted normal stage. The later tree callback uses `tree_cutoff`. This control flow and the saved normal completion identify the tree-probe containment callback as the supported failing stage. A three-second local horizon established after roughly 1.7 seconds of startup/normal work explains a failure near total4.7 seconds without clock inconsistency.

There is a concrete boundary hazard: `_wait_process` checks remaining time **before** `WaitForSingleObject` (S3442–3449), but after `WAIT_TIMEOUT` it invokes containment without rechecking the horizon (S3450–3456). A final native wait can reach/cross the short horizon; the callback then raises a census `TimeoutError` before the loop can return its intended `timed_out=true`. A census begun shortly before the horizon can also cross it during enumeration. The saved error proves that deadline guard fired; it does **not** prove the census itself took three seconds, that the global ten seconds elapsed, or that the tree escaped.

The exact `tree_cutoff`, callback entry/exit times, triggering row/iteration and native wait interval are not persisted. The evidence therefore cannot choose between those precise scheduling paths or quantify census latency. This is an actual timeout under the callback's supplied local bound, combined with a wait-horizon/containment-deadline boundary issue; it must not be relabeled successful containment. S's catch records BLOCKED and finally terminates the owned inner Job. Its saved zero/confirmed inner cleanup cannot satisfy the uncompleted normal tree acceptance path (S4067 onward), including subsequent marker/identity/membership validations.

## PID 31876 remains unidentified

Searching all retry-6 records finds `31876` only in `caller-invocation.json.unexpectedOuterJobProcesses`. W1922–1927 queries the outer Job PID list after the launcher wait, records a nonempty list, sets `STOP_OUTER_DESCENDANTS_REMAINED` and requests outer Job termination. This is not the W successful-false-membership exception path; the new same-handle descendant diagnostic suffix is consequently absent.

Saved identities are wrapper33604, S launcher27132/base4092, normal launcher2604/base35560, tree launcher1348/base3928 and child launcher40660/base4380. None identifies 31876. The child marker's `CONTAINED_CHILD_STARTED` text is not itself S's later exact inner-Job membership validation, which was not reached. No saved creation time, image, handle identity or authenticated ancestry binds 31876. Do not call it conhost, intended helper, benign residue or an outside-Job escape. Inner `finallyTermination.activeProcessCountAfterRequest=0` describes the inner Job, not the identity or fate of that outer residual PID; the caller records an outer termination request, not a saved authenticated termination observation for 31876.

## Minimal next action

Stop with this diagnosis for coordinator acceptance. The evidence supports a **separately planned focused S self-check wait/callback-boundary correction**, distinguishing the deliberate three-second wait horizon from the inherited ten-second containment/cleanup deadline and requiring explicit completed containment evidence. Define/review what may happen when the wait or census crosses the local horizon before implementation. Preserve fail-closed incomplete/error census behavior, exact identity/Job/marker checks, all later tree proof and cleanup, default/build/preflight callers and the original total budget. Do not blanket-catch `TimeoutError`, convert an incomplete census to PASS, enlarge the total budget, exempt PID31876 or change W based on the misleading field-name interpretation. This diagnosis grants no correction or further attempt.

Only authorized static source/document/record reads, source and retry-6 inventory hashing, search and in-memory arithmetic occurred. Only this diagnosis artifact was written. No retry1–5 evidence contents were read; no parser/compiler/linter/test/import/runtime/process probe, source/evidence edit, path/root work or invocation occurred. Retry-6 remains consumed/immutable/non-PASS, retry-7 unselected/unreserved, candidate NO-GO/unservable and build3 unreserved. No counters reset; the historical outer exit1/internal2 discrepancy remains separate and unresolved.
