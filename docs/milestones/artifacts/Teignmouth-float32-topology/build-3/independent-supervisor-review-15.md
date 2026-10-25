# Independent supervisor review 15 — primary exception preservation

2026-10-25. Independent non-implementing Sol reviewer `/root/sol_review_face_diag`, under disposition 70, against review 14 and the accepted nonzero-reaping plan (`833cf5af08a7eb1e0b6ff1b30c33557acb3b777d569d9e67762f25d7248f042b`). **FIX_REQUIRED — secondary in-memory recording can still replace the original exception.** No self-check or subsequent runtime action is authorized by this report.

## Reviewed bytes and scope proof

Independently verified current S SHA-256: **`672838756b4183a14ffcf849671e2b90cc5828123dfb34cec92412d4ce9238b9`**, matching the review dispatch. Only these current bytes are reviewed.

An in-memory, non-executing reversal of the added outer persistence guard restores SHA-256 **`45a7f343644f0fbdeeb66b982c572bf123dffba2f021e0db314060ae1d83b024`**, exactly the actual revision reviewed in review 14. No reconstructed source was written or executed. Thus the current change from that known revision is isolated to this outer exception-update guard; the retained-handle, strict snapshot, two-exit/release/drain/acceptance and later tree/cleanup logic are unchanged.

The earlier implementer-reported S digest beginning `957157` still has no saved/reconstructable bytes or reliable Git baseline. This new inverse proof does **not** resolve that earlier provenance limitation or establish an exact delta from the pre-reaping S baseline. No Git index diff is claimed.

## Concrete finding

S **3102–3104** now catches a secondary `_update_owned(record_path, record)` failure, resolving review 14's direct unguarded-write case when subsequent error recording succeeds. But the handler at **3105–3113** constructs a new dictionary, formats the exception message, assigns `record["exceptionPersistenceError"]`, and appends to `evidenceCheckpointErrors` **without another best-effort guard**. An exception from those secondary operations escapes before the intended bare `raise` at **3114**, replacing the original outer `exc`.

A reachable case does not require record corruption or an invented wrong-type value: `_update_owned` performs allocating JSON/file-update work and can fail with `MemoryError`; further allocation during secondary dictionary construction, new dictionary-key insertion or list growth can also raise `MemoryError`. The same applies if the original stage exception is different and a subsequent evidence allocation fails. The normal code initializes `evidenceCheckpointErrors` as a built-in list and retains that invariant; this review does **not** rely on assuming it arbitrarily became `None` or another type.

Disposition 70 explicitly requires secondary persistence errors be recorded **when possible** and **never replace** the original `exc`. The present nested failure path does not satisfy that requirement. Secondary in-memory reporting must itself remain best-effort so failure there cannot bypass the re-raise of the original stage exception. No error path was executed or reproduced here.

## Retained behavior

- Under ordinary successful in-memory recording, the new inner exception handler finishes and the bare raise at 3114 re-raises the original outer exception; a failed evidence write does not produce PASS.
- BLOCKED status and exit 2 are established at **3093–3100**. The residual reporting exception still propagates as non-PASS; this is primary-error masking, not a discovered false-success branch.
- Python finally cleanup remains reachable at **3115 onward** even if secondary recording raises: Job termination/close and owned handle cleanup precede the final guarded record write. No claim is made that an unavailable filesystem can guarantee durable reporting.
- All review-14 plan observations other than complete error separation carry forward through the exact inverse hash proof: authenticated retained interpreter handle, independent launcher/interpreter exit-7 observations, strict complete PID/accounting snapshots, pre-rejection checkpoints, release before bounded drain, persisted normal-complete gate and later unchanged tree probe. No wait, member-emptiness, identity, 10-second deadline or cleanup criterion was weakened by this patch.

## Preservation hashes

W/H/P independently remain:

| File | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `3078e1df4bf89438208bbcfc09150dbce77f180259f847a84287892d26662989` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `e3cdadced5d90a669155002870636610e77df68b8a013deeef187893fbd65e78` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

All eleven files beneath consumed retry-2 were rehashed and match the complete file-by-file hashes recorded in review 14/disposition 67, including caller `4dbb3ff5f821edefe0a9d5fa1c822ef7cb0d296f346853013d620a3abaf5f00e` and run invocation `7b40f2f6f218e491034c6f621108faedf6d0137557379f80fa0802c2313ab592`. Original caller/pending remain `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e` / `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75`; retry-1 caller/handoff remain `f992b356191d202a5e2357cffb1d64d90b4dd7f8ac54cd0b76ab2e0d7540dcf3` / `b73738fc81644b942ea4f84890146e1bdfc73d925005552cb34db1af05aadc79`. Retry-2 remains immutable, consumed and non-PASS; no new evidence root was prepared.

Only static reads/searches, file hashing and in-memory source-string/hash comparison occurred, plus writing this report. No source/evidence/metadata/manifest was altered; no tests, imports, linters/parsers/compilers, probes/process inspection, wrapper/self-check/preflight/runtime/collection, manifest preparation, GIS/numerical/build or browser work ran. Reported static checks were not rerun. **Actual 10-second completion/drain behavior and 30-second runtime-profile fit remain unmeasured; no runtime evidence is created.**

Return FIX_REQUIRED for the remaining error-separation predicate. This report grants no correction, self-check or later phase; the coordinator retains the gates, including separate fresh retry-3 path planning/review before any later wrapper call. Candidate remains **NO-GO and unservable**; build 3 remains **unreserved**.
