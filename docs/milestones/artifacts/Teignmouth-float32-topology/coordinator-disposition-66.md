# Coordinator disposition 66 — accept retry-2 path gate for one self-check

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Dispositions 64–65 and the user's authorization to continue with as many attempts as needed to pass the supervisor self-check.

## Coordinator gate

Independent Sol review 13 is **PASS** for the exact four fixed-path substitutions in W/S/H. Report SHA-256: `aea8ae115c91d42b14182b292873449ecf32b2d3d107f44291d6792ad4f4cede`. The full current hashes are W `3078e1df4bf89438208bbcfc09150dbce77f180259f847a84287892d26662989`, S `2bae9a35ee91ca154bba19c0a3848b0bda2f46930f38e9090bd632ff5653300d`, H `e3cdadced5d90a669155002870636610e77df68b8a013deeef187893fbd65e78`, and unchanged P `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`. Review 13's inverse hashes restore the exact accepted pre-path source hashes; old roots/evidence match and retry-2 was absent at coordinator gate.

The review explicitly noticed a checkpoint W-hash transcription typo. The coordinator corrected the checkpoint to the full independently verified W digest above before this gate. No source change followed review.

## Authorized single operation

Run exactly once through the W wrapper in self-check mode, using the accepted exact new fixed root `.codex/build3-supervisor-selfcheck-retry-2/` and existing 10-second total QPC limit:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File pipeline/scripts/invoke_teignmouth_float32_build3.ps1 -Mode self-check
```

This gate does not authorize a second retry-2 invocation or any subsequent runtime identity collection/verification, manifests, candidate build/reservation, GIS/numerical work, serving, publication or browser action. Preserve every output/evidence byte-for-byte. After capturing the one actual result, stop and reconcile under disposition 64 before the next cycle.

Candidate remains **NO-GO and unservable**; build 3 remains unreserved. No changes to historical attempt counters or protected data/geometry/recipe/numerical limits.
