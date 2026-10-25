# Coordinator disposition 119 — resume cycle-2 W handoff after exact inverse diagnosis

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User's continuing authorization for as many bounded attempts as needed; disposition 117 cycle-2 W correction release; disposition 118 read-only diagnosis; independent Sol diagnosis below.

## Diagnosis accepted

Accept `build-3/retry6-correction2-inverse-mismatch-diagnosis.md`, SHA-256 `f239554ccc7caef0a51f9e3f4cd996338a70b95bbad50b646a2038c430f3611a`, as a read-only exact-inverse diagnosis. It independently reproduced that the failed inverse hash `ce7f6d2…` is the exact bound pre-correction W `d7351a1…` plus one `0A` at byte offset 83656, introduced by the inverse operation at the inserted minimal-status serialization boundary. The exact seven-span inverse, without that extra separator, restores the 134,567-byte W and its complete `d7351a1…` digest. The current W's bounded delta remains limited to the seven spans addressing disposition 117's three findings. The source remains unchanged at W `804ae8c42f6637a61505e53e825972d758b8ae2c1c2d0740ff5a076a0e703b45`; S/H/P remain `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69`, `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3f1c1db5299e25560bf`, and `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`.

This resolves the inverse-proof discrepancy only. It is not a behavioral finding or implementation PASS.

## Bounded Luna authority — complete cycle-2 handoff only

Authorize Luna to resume **without changing any source bytes** and finish the cycle-2 implementation handoff for current W `804ae8c42f6637a61505e53e825972d758b8ae2c1c2d0740ff5a076a0e703b45`:

1. Recompute the tight inverse in memory using only the seven exact spans from the Sol diagnosis and concatenate without adding a separator at the minimal-status-serialization removal boundary. Require length 134,567 and hash `d7351a1cdcd9e8f6ea2c554400ff34d4f281a8c15086c87b32a132d806e549cd`. Then use the already documented, exact cycle-1 inverse to verify the accepted W hash `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0`; no general normalization, trim, restore, or source rewrite.
2. Run only the previously authorized PowerShell AST parse and embedded C# compile-only gates. No method invocation.
3. Recheck only the previously authorized 53-file immutable evidence matrix, six protected source/config/test hashes, and unchanged S/H/P. Do not read consumed evidence contents.
4. Write a complete cycle-2 handoff naming the exact current W hash, inverse hashes/lengths, gate output, preservation results, and corrected unchanged H hash `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3f1c1db5299e25560bf`. Record that the prior failed inverse added a separator during reconstruction; do not edit the old handoff or any evidence.

Stop if any exact digest or protected value does not match, or if any correction-2 issue remains. No further source edit is authorized by this disposition. Stop after the handoff for a separate coordinator decision on independent Sol implementation review.

## Prohibited work and preserved status

No tests/imports/linter, runtime/process probe, W invocation, wrapper, self-check, preflight, path selection, retry-6 root creation, candidate/GIS/numerical build, reservation, browser/publication work, commit, push or merge. Retries 1–5 remain consumed, immutable and non-PASS; retry-6 remains unselected, unreserved and absent. Candidate remains **NO-GO and unservable**; build 3 remains unreserved. The 10-second QPC deadline is unchanged.
