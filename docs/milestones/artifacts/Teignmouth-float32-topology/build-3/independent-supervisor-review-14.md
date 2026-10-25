# Independent supervisor review 14 — normal helper completion/reaping

2026-10-25. Independent non-implementing Sol reviewer `/root/sol_review_face_diag`, under disposition 69. **FIX_REQUIRED — primary normal-stage failures can still be replaced by a secondary evidence-write exception.** Reviewed actual current S against accepted `retry2-nonzero-reaping-plan.md` (independently verified SHA-256 `833cf5af08a7eb1e0b6ff1b30c33557acb3b777d569d9e67762f25d7248f042b`) and immutable retry-2 evidence. No runtime or self-check authorization follows.

## Reviewed revision and delta-proof limitation

Actual S `pipeline/scripts/run_teignmouth_float32_build3.py` independently hashes to **`45a7f343644f0fbdeeb66b982c572bf123dffba2f021e0db314060ae1d83b024`**. This is the only S revision reviewed here. Luna reported a different digest beginning `957157`; its bytes were not saved and cannot be reconstructed from a reliable Git baseline. The files are untracked, so no complete historical/index diff or exact mapping from that reported revision is claimed. Current source was inspected directly around acquisition/ownership, waits/exits, strict snapshots, error checkpoints, release/drain/acceptance and later tree/cleanup paths.

The coordinator reports Ruff check/format PASS on **this current S revision**. Those checks were not rerun by this reviewer; neither those results nor the implementer-reported different hash proves the required behavior or a minimal source delta.

Independently unchanged operational hashes:

| File | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `3078e1df4bf89438208bbcfc09150dbce77f180259f847a84287892d26662989` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `e3cdadced5d90a669155002870636610e77df68b8a013deeef187893fbd65e78` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

Candidate/shared-helper/builder/focused-test/fixture/configuration were also rehashed and match their full accepted review-13 bindings, respectively: `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b`, `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880`, `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b`, `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8`, `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea`, `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228`. No protected-byte change is evidenced.

## Concrete residual finding

**FIX_REQUIRED — S 3102 can mask the primary normal-helper exception after the guarded checkpoint.** The normal-stage exception path first invokes `checkpoint_normal_failure(exc)` at **3091–3092**. That helper correctly records the original type/message/phase and separately catches snapshot/persistence failures (**2608–2638**). However, the enclosing handler then performs an **unguarded** `_update_owned(record_path, record)` at **3102**, before its bare re-raise at **3103**.

Static failure case: normal exit validation, identity acquisition, strict census or drain raises its original error; the guarded checkpoint's persistence also fails; the unconditional second write at 3102 fails again (for example an unavailable destination or occupied pending file). This secondary write exception escapes instead of the original stage exception. Finally cleanup still runs, but the outer error report receives the persistence exception, contrary to the plan's requirement that primary/evidence/final-cleanup errors remain separate and a failed evidence write not overwrite the primary exception. Even if the guarded checkpoint succeeded, a failure of that second write can still replace the original exception.

This is a reporting/error-lifecycle defect, not a false normal-complete PASS or evidence that process cleanup is skipped. No failure was reproduced. The handler must preserve the original exception while recording secondary persistence failure without allowing it to replace that exception; the required cleanup and sticky non-PASS remain mandatory. This report implements or authorizes no correction.

## Static acceptance matrix

| Criterion | Assessment of current S |
| --- | --- |
| Pinned retained interpreter handle | **PASS:** 439–509 adds default-off retention; only normal self-check opts in (2704–2714). SYNCHRONIZE is added without new API/dependency. The original launcher handle creation time is checked; retained interpreter creation/image/hash and parent are revalidated on that handle, plus exact inner Job membership. Pre-transfer finally closes local handles; transferred ownership is added to caller handles immediately (2715–2724) before marker/evidence work. No post-exit PID reopen substitutes for completion. |
| Distinct actual waits/exits | **PASS:** launcher and interpreter use different retained handles; waits and actual GetExitCodeProcess observations are recorded separately (2745–2804). Unknown/STILL_ACTIVE/wrong exit/timeout cannot satisfy the explicit two-signaled-exits-7 gate (2818–2827). The helper marker is corroboration, not an exit substitute. |
| Strict accounting/PID snapshot | **PASS for inspected bounds/completeness logic:** 2048–2270 records before/after raw accounting statuses, complete versus unavailable/partial census, buffer capacity/bytes/header counts and errors. PID reads are bounded by capacity/allocated layout, positive/distinct/range checks, assigned/listed agreement and eight attempts/65536 ceiling. Query failures are not converted to an empty list; final success demands two observed zero counts enclosing a complete empty list. No fixed subtraction/allowance is added. |
| Pre-error evidence | **PARTIAL / FIX_REQUIRED:** initial post-wait snapshot is persisted before rejection (2806–2832); exception checkpoint captures primary context and null/unavailable observations as appropriate. The unguarded outer update at 3102 defeats complete primary-error preservation as detailed above. |
| Completed-handle release and drain | **PASS:** actual exits are gated before release. Successful closes remove owned handles and record released state; close failure stays owned/non-PASS (2834–2844). Drain uses the original deadline, bounded first/latest evidence and iteration count, rejects incomplete/unexpected PID observations, and accepts only raw zero/complete empty/zero before expiry (2848–2907). Known already-exited residue is allowed only to settle within that budget. Forced cleanup is not used to establish normal success. |
| Persisted normal-complete before tree | **PASS:** 2908–2935 persists both exits and final zero/empty acceptance before tree launch; a checkpoint/late completion failure prevents that launch and invalidates acceptance in the exception checkpoint. No clock reset or H sleep change. |
| Later tree probe and cleanup | **PASS for inspected current contracts, delta not byte-proven:** the later contained root/child probe, forced termination, zero accounting, observed root exit and deadline gates remain (2937 onward, 3048–3088). Finally still attempts Job termination/handle cleanup even if error persistence raises (3104–3124). These are static code observations, not actual containment/drain proof or an exact historical tree-block diff. Error separation remains the blocker above. |

## Immutable evidence verification

Rehashed every file currently under consumed retry-2. The eight nonempty bindings match disposition 67:

| Retry-2-relative file | SHA-256 |
| --- | --- |
| `caller-invocation.json` | `4dbb3ff5f821edefe0a9d5fa1c822ef7cb0d296f346853013d620a3abaf5f00e` |
| `self-check-handoff.consumed.json` | `bb773f7991eaa34c9f87ede7df8dd48d4eea899fbbd711eea009e3f7631abb0c` |
| `supervisor-script-start.json` | `8ecc5f87c87c90b3f1b73e9bf07814b7b6409a308971a6c83751be09c4f058d5` |
| `supervisor.stderr.log` | `92875c22d9084e2f791f53e02c09bc03d6b2bd16f28655fcffa3be5380c3ba51` |
| `run-1/invocation.json` | `7b40f2f6f218e491034c6f621108faedf6d0137557379f80fa0802c2313ab592` |
| `run-1/nonzero-authorization.consumed.json` | `e448045f4930ff8ab2c47341daeabb63bd0cef8008f5265b1d344167d53548f8` |
| `run-1/nonzero-helper.json` | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| `run-1/nonzero-script-start.json` | `767458b7ce651898f16c7bec8c2d3370eeaaff4d1d1802663edf3b77b7b86d24` |

The three empty supervisor/nonzero stdout/stderr files match SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. Original caller/pending and retry-1 caller/handoff also remain `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e`, `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75`, `f992b356191d202a5e2357cffb1d64d90b4dd7f8ac54cd0b76ab2e0d7540dcf3`, `b73738fc81644b942ea4f84890146e1bdfc73d925005552cb34db1af05aadc79`.

Retry-2 stays immutable, consumed and non-PASS. This review does not claim its previous observation was a false positive, or that handle-reference release caused that failure.

Only static reads/searches and hashing were performed, plus writing this report. No code/metadata/evidence/manifest was edited; no tests, linters/parsers/compilers, imports, process inspection/probes, wrapper/self-check/preflight/runtime/collection, manifest preparation, GIS/numerical/build or browser action ran. **10-second drain/containment behavior and 30-second runtime-profile fit remain unmeasured.** No runtime evidence is created.

Return FIX_REQUIRED for the narrow error-lifecycle correction and independent re-review under disposition 69; no operational call follows this report. A later fresh retry-3 path plan/review/gate remains separate, because retry-2 cannot be reused. Candidate remains **NO-GO and unservable**; build 3 remains **unreserved**, with source/origin/domain/recipe/collision/numerical constraints and historical counters unchanged.
