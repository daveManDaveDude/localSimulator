# Coordinator disposition 67 — preserve retry-2 self-check failure and diagnose

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Dispositions 64–66 and the user's continuing authorization for as many repair attempts as needed to pass the supervisor self-check.

## Retry-2 result

The one wrapper-driven self-check authorized by disposition 66 ran at the fresh fixed retry-2 root and returned **exit 2**. It passed caller/handoff creation, native launcher creation, Job assignment, resume, supervisor start identity, and helper authorization/consumption. The helper wrote `{"exitCode":7,"status":"EXPECTED_NONZERO_HELPER"}`, which is the expected helper result. The supervisor then reported `RuntimeError: nonzero helper left a contained descendant running`.

Caller telemetry records `launcherCreated=true`, `launcherAssigned=true`, `launcherResumed=true`, `outerJobMembershipObserved=true`, `outerTerminationConfirmed=true`, `candidateBuildExecuted=false`, and `candidateEligibleForServing=false`. The S run record says `finallyTermination.terminationRequested=true`, `terminationConfirmed=true`, `activeProcessCountAfterRequest=0`, and elapsed wall time about 1.318 seconds. This does **not** turn the self-check into PASS: its assertion observed a descendant before final cleanup. It also does not establish numerical/GIS/build behavior.

Do not run another wrapper or runtime operation while diagnosing/planning. Keep retry-2 as consumed/non-PASS and all its evidence immutable.

## Key evidence hashes

- W/S/H/P: `3078e1df4bf89438208bbcfc09150dbce77f180259f847a84287892d26662989`, `2bae9a35ee91ca154bba19c0a3848b0bda2f46930f38e9090bd632ff5653300d`, `e3cdadced5d90a669155002870636610e77df68b8a013deeef187893fbd65e78`, `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`.
- Retry-2 root caller: `4dbb3ff5f821edefe0a9d5fa1c822ef7cb0d296f346853013d620a3abaf5f00e`.
- Retry-2 consumed handoff: `bb773f7991eaa34c9f87ede7df8dd48d4eea899fbbd711eea009e3f7631abb0c`.
- Retry-2 supervisor start: `8ecc5f87c87c90b3f1b73e9bf07814b7b6409a308971a6c83751be09c4f058d5`.
- Retry-2 supervisor stderr: `92875c22d9084e2f791f53e02c09bc03d6b2bd16f28655fcffa3be5380c3ba51`.
- Retry-2 run invocation: `7b40f2f6f218e491034c6f621108faedf6d0137557379f80fa0802c2313ab592`.
- Retry-2 nonzero auth consumed: `e448045f4930ff8ab2c47341daeabb63bd0cef8008f5265b1d344167d53548f8`.
- Retry-2 nonzero helper marker: `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2`.
- Retry-2 nonzero script start: `767458b7ce651898f16c7bec8c2d3370eeaaff4d1d1802663edf3b77b7b86d24`.
- Empty stdout/stderr logs: SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

Retry-1 and original records remain unchanged. Preserve retry-2 caller, consumed handoff, start marker, supervisor logs and run-1 descendants byte-for-byte.

## Next authorized work

Disposition 64 plus the user's repeated-attempt authorization permits Sol to perform a bounded read-only diagnosis of this specific descendant observation, then propose a concrete minimal fix or missing evidence. No implementation follows until coordinator accepts that diagnosis into a narrow plan. Candidate remains **NO-GO and unservable**, build 3 unreserved. No runtime identity collection, manifests, GIS/numerical work, candidate build, serving, publication or browser action is authorized.
