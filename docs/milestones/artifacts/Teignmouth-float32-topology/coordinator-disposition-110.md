# Coordinator disposition 110 — preserve retry-5 supervision failure

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Disposition 109's one-use gate and the user's continuing authorization for as many bounded attempts as needed.

## Exact consumed result

Disposition 109 authorized one invocation. The exact command was `pwsh -NoProfile -ExecutionPolicy Bypass -File pipeline/scripts/invoke_teignmouth_float32_build3.ps1 -Mode self-check`, run from `C:\vibe\localSimulator`. The process completed in 2.107 seconds with outer exit code **1** and an empty outer console output. No replay is allowed for this consumed slot.

Caller record `CALLER_SETUP_OR_SUPERVISION_FAILURE` reports `Descendants escaped the owned Job Object: 32560.` It records native launcher exit 2, wrapper chosen exit 2, elapsed 1.5190315 seconds against the 10-second QPC budget, deadlinePassed true, forced containment/cleanup confirmed, zero outer processes after cleanup and `candidateBuildExecuted=false`. Candidate bytes were not built.

The inner run record `run-1/invocation.json` is still `INVOCATION_STARTED`, with no terminal supervisor result recorded. Its normal nonzero helper phase did complete with launcher/interpreter exit 7/7, complete census zero, accounting 0/0 and accepted final census. Evidence then records the tree-root authorization consumed, its script-start identity and `tree-root-started.json` with child PID/launcher PID. The caller's escaped PID is 32560; the evidence does not itself prove which process identity that PID had at census. Do not infer ownership or apply an exemption.

## Immutable retry-5 evidence inventory

Do not edit, clean, adopt or regenerate these files:

| Relative path | SHA-256 |
| --- | --- |
| `.codex/build3-supervisor-selfcheck-retry-5/caller-invocation.json` | `87adbe38bcbf779eb7e41cd0ba70e6ebe0d395d15cb6e62721a9b2d0b1034906` |
| `.codex/build3-supervisor-selfcheck-retry-5/supervisor-script-start.json` | `0c75e56e765756b30ed06f8204a145a8c8d82ee2844009f385b7460bc26f86c0` |
| `.codex/build3-supervisor-selfcheck-retry-5/supervisor.stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-5/supervisor.stdout.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-5/self-check-handoff.consumed.json` | `cafc18f3965daf968dfff056367d8bb7f8011654e16eba30c3a3679d16115d36` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/invocation.json` | `e87a0e404117ce1ef552c14ff66634df57bc2d895aa1cada9aba020e7b22651a` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/nonzero-authorization.consumed.json` | `b3d40f91b26186a46577f27813886bacbb3f534a8ce010a0f20c3fff475ba098` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/nonzero-helper.json` | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/nonzero-script-start.json` | `60b0388b1c6dd733771b16abd78aec9e3ba839111396690d8b9ddf5173e57dc4` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/nonzero.stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/nonzero.stdout.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/tree-root-authorization.consumed.json` | `b9d35fb31fd6677d1cec2d40fb869d79348a98ba57828c7c12845f86a5baea0d` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/tree-root-script-start.json` | `5f1e7db08802fd76a68bc1ac985ea3995cbedd0097218525eaeb01b3fe9e188e` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/tree-root-started.json` | `630e0b7d264d07c61dd4d8cf0aba8f9bf77a0ab376d43fe857b1c942e39b2e25` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/tree.stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/tree.stdout.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## Next authorized action — read-only Sol diagnosis

Authorize Sol to inspect only the current accepted W/S/H source, retry-5 evidence above, relevant accepted plans/reviews and prior retry-4 diagnosis. Determine the exact control-flow stage that raises the escaped-descendant error, whether PID 32560 is authenticated by any recorded identity (do not use live-process inspection), why the tree-root helper's launched pair does or does not meet the wrapper's authenticated Job census, and the smallest scope-preserving correction or precise blocker. Compare retry-5 to retry-4 without reopening unrelated old evidence. Do not edit, execute, import, parse, test, invoke, probe processes, read other consumed evidence contents, create retry-6 or alter this inventory. Produce a bounded report and stop for a new plan/review/coordinator gate.

## Preserved status

Retry-1 through retry-5 are now immutable, consumed and non-PASS. Retry-5 root exists and contains only the listed evidence; it is not a path for reuse. No retry-6 root/plan/gate exists. Candidate remains **NO-GO and unservable**; build 3 unreserved. No preflight, numerical/GIS/candidate build, reservation, runtime profile, publication or browser work. No commit, push or merge.
