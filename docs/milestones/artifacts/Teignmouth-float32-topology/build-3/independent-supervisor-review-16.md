# Independent supervisor review 16 — guarded secondary reporting

2026-10-25. Independent non-implementing Sol reviewer `/root/sol_review_face_diag`, under dispositions 70–73 and the review dispatch. **PASS — static acceptance of the review-14/15 error-separation correction.** No actionable residual finding was identified in the reviewed correction. This report authorizes no self-check or subsequent runtime action.

Reviewed actual current S against the accepted nonzero-reaping plan (`833cf5af08a7eb1e0b6ff1b30c33557acb3b777d569d9e67762f25d7248f042b`), review 14/15 and dispositions 70–73.

## Exact revision and correction scope

Independently recalculated hashes:

| File | SHA-256 |
| --- | --- |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `9452b2b00f3c72b8bef5f9a2e5cab2992947d0072a71901710cac129057c0733` |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `3078e1df4bf89438208bbcfc09150dbce77f180259f847a84287892d26662989` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `e3cdadced5d90a669155002870636610e77df68b8a013deeef187893fbd65e78` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

A non-executing, in-memory reversal of only the newly nested reporting guard restores **`672838756b4183a14ffcf849671e2b90cc5828123dfb34cec92412d4ce9238b9`**, exactly review 15's S. Combined with that report's inverse proof to review 14's actual `45a7f343…` revision, this establishes the narrow error-handler changes across these reviewed revisions. No reconstructed source was written or executed.

The earlier implementer-reported S digest beginning **`957157…` remains unsaved/untraceable**. No new proof of that revision, complete historical delta from the original reaping baseline, or reliable Git index diff is claimed. Only the exact current source and the stated inverse-hash chain are accepted.

## Findings closed

- **Review 14 — PASS:** outer `_update_owned` is guarded at S **3102–3104**. Its failure no longer directly escapes instead of the original outer `exc`.
- **Review 15 — PASS:** the entire secondary reporting body, including dictionary construction, formatting, `exceptionPersistenceError` insertion and `evidenceCheckpointErrors` append, is inside a second `try/except Exception` (**3105–3116**). An ordinary reporting failure, including `MemoryError`, is suppressed as best-effort telemetry failure. On leaving both nested handlers, Python restores the active outer exception, and bare `raise` at **3117** re-raises it. This closes the specific reachable secondary-allocation path identified by review 15 without assuming malformed record state.
- **Sticky non-PASS / cleanup — PASS:** BLOCKED/exit 2 remain set at **3093–3100**. Secondary reporting cannot reach a success return. The unchanged `finally` at **3118–3138** remains reachable and attempts Job termination/close, owned-handle cleanup and separately guarded final evidence persistence. No claim is made that an unavailable filesystem can guarantee a durable error record.

The inverse proof establishes that the authenticated retained interpreter-handle acquisition, separate launcher/interpreter exit-7 observations, strict accounting/PID completeness checks, pre-rejection snapshots, handle release, deadline-bounded drain, persisted zero/empty/zero normal-complete gate and later tree-probe criteria are unchanged from their inspected review-14/15 logic. No identity, member-emptiness, ownership, expected exit, containment, handle, path/schema/mode/dependency or original 10-second deadline criterion is relaxed. No forced cleanup is promoted into normal-stage PASS.

## Preservation

All six protected candidate/helper/builder/test/fixture/configuration files were independently rehashed and match their complete accepted review-14 bindings. Original caller/pending remain **`e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e`** / **`78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75`**; retry-1 caller/handoff remain **`f992b356191d202a5e2357cffb1d64d90b4dd7f8ac54cd0b76ab2e0d7540dcf3`** / **`b73738fc81644b942ea4f84890146e1bdfc73d925005552cb34db1af05aadc79`**.

Every one of the eleven files under consumed retry-2 was rehashed and matches the full review-14/disposition-67 binding list, including caller **`4dbb3ff5f821edefe0a9d5fa1c822ef7cb0d296f346853013d620a3abaf5f00e`** and run invocation **`7b40f2f6f218e491034c6f621108faedf6d0137557379f80fa0802c2313ab592`**. Retry-2 remains immutable, consumed and non-PASS. No new evidence root or record was prepared.

Review used only static reads/searches, hashing and in-memory source-string/hash comparison, plus writing this report. No source, evidence, metadata or manifest was edited. No tests, imports, linters/parsers/compilers, probes/process inspection, wrapper/self-check/preflight/runtime/collection, manifest preparation, GIS/numerical/build or browser action ran. Coordinator/implementer-reported Ruff PASS results were not rerun. **Actual 10-second completion/drain behavior and 30-second runtime-profile fit remain unmeasured; no runtime evidence is created.**

Return static PASS to the coordinator. A separately accepted/reviewed exact fresh retry-3 path binding and coordinator gate remain necessary before any later self-check; this report neither authorizes nor executes one. Historical counters and source/origin/domain/recipe/collision/numerical constraints remain unchanged. Candidate remains **NO-GO and unservable**; build 3 remains **unreserved**.
