# Coordinator disposition 118 — freeze cycle-2 W inverse mismatch for Sol diagnosis

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Disposition 117 cycle-2 W correction release. This disposition stops edits pending a read-only diagnosis.

## Observed stop

Luna applied seven exact replacement spans in W during correction cycle 2. Its in-memory inverse hash was `ce7f6d2aa366c260a2b803165507c5cca53b1214507ab22b4c661cd3d47707de`, length 134,568 bytes, rather than the bound pre-correction W `d7351a1cdcd9e8f6ea2c554400ff34d4f281a8c15086c87b32a132d806e549cd`, length 134,567. It stopped before any further edit, static/preservation checks or handoff.

Coordinator independently confirms current W hash `804ae8c42f6637a61505e53e825972d758b8ae2c1c2d0740ff5a076a0e703b45`; S/H/P remain `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69`, `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3f1cdb5299e25560bf`, and `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`. Retry-6 remains absent. Current W bytes are frozen pending diagnosis; no other current files were changed or rehashed here.

## Read-only Sol diagnosis only

Authorize a non-implementing Sol to inspect current W, cycle-2 correction context, disposition 117, cycle-1 handoff/review, the accepted plan and existing baseline/recovery records. Determine exactly why reversing the seven claimed spans adds one byte and misses the bound `d7351a1…` hash, whether the current delta is limited to the three authorized findings, and whether the pre-correction bytes can be reconstructed exactly in memory or from an existing read-only snapshot. Return a minimal exact-span recovery or blocker. No source edits, normalization, restore, line-ending changes, evidence reads/changes, tests/imports/parser/linter/compiler, runtime/process inspection, wrapper/self-check/preflight, retry-6 path/root creation or invocation. Do not broaden or recast the baseline. Stop for coordinator decision after the report.

## Preserved status

Retries 1–5 remain immutable, consumed and non-PASS. Retry-6 remains unselected, unreserved and absent. Candidate remains **NO-GO and unservable**; build 3 unreserved. No further W edits or invocation are authorized pending diagnosis and a new coordinator decision.
