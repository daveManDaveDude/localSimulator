# Coordinator disposition 117 — authorize Luna correction cycle 2 for W diagnostics

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User's continuing authorization for as many bounded attempts as needed; disposition 116 implementation review and correction cycle 1.

## Independent review finding accepted

Accept `build-3/retry6-w-descendant-escape-correction-1-independent-review.md`, SHA-256 `6ab1b80d82a6aaccad3e93ef4fa63b5016c62f8d0fa8f2844a1e5b4b4d4ce49f`, as **FIX REQUIRED** for correction-1 W hash `d7351a1cdcd9e8f6ea2c554400ff34d4f281a8c15086c87b32a132d806e549cd`. The reviewer independently verified both W inverse chains, authorized AST/C# compile-only, all 53 evidence files, six protected hashes and unchanged S/H/P. It confirms the six initial findings were fixed, and identifies three remaining issues:

1. Diagnostic row-index initialization/increment still runs when the observation sink is null, altering the default caller path.
2. If the optional membership-start QPC read is unavailable, the output casts null to zero and fabricates a timestamp; preserve null and mark it unavailable while keeping later same-handle evidence and the rejection.
3. No-reserve/expired branches still allocate a multi-group payload while the process handle is open. Retain only a minimal skipped/late token before the one close and expand it after close/cleanup, or omit that diagnostic; do not construct the detailed payload before closing.

The correction-1 handoff also transcribed H's SHA-256 incorrectly. The actual unchanged H hash is `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3f1cdb5299e25560bf`. Do not edit the prior handoff or H source; use the correct value in the next handoff and record this metadata discrepancy.

## Bounded Luna correction authority — cycle 2

Authorize Luna to correct only the three findings in W (`pipeline/scripts/invoke_teignmouth_float32_build3.ps1`). Keep source behavior, S/H/P, path literals, retries 1–5, numeric ancestry/census and rejection semantics unchanged. Guard rowIndex initialization and increments on an actual diagnostic observation sink, without changing the default `foreach` walk/order/predicates. Emit unavailable start QPC as null with an explicit unavailable status; never coerce missing telemetry to 0, and allow successful false membership/rejection to survive. In reserve-unavailable or cutoff-expired cases, do no detailed payload/group/chain copying while the query handle remains open; keep only the smallest bounded status token needed, close exactly once first in finally, and either expand later in existing post-cleanup serialization or omit it. Preserve all cycle-1 fixes and the accepted 10-second QPC/cleanup limits.

Verify tight inverse to current W `d7351a1cdcd9e8f6ea2c554400ff34d4f281a8c15086c87b32a132d806e549cd` by reversing only cycle-2 spans, then inverse to accepted W `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0`. Keep S/H/P unchanged at `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69`, `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3f1cdb5299e25560bf`, and `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`. Preserve all 53 old evidence files, retry-5's 16 files and six protected hashes. Run only PowerShell AST and embedded C# compile-only gates. No tests/imports/project execution/process probes/path change/root creation/self-check. Produce a full correction-2 handoff with corrected H hash and exact results for independent Sol review. If any finding cannot be fixed within the plan, stop and report.

This is Luna correction cycle 2 for this W-only diagnostic implementation; no previous counters are reset. No invocation is authorized.

## Preserved status

Retries 1–5 remain immutable, consumed and non-PASS; retry-6 remains absent and unselected. Candidate remains **NO-GO and unservable**; build 3 unreserved. No preflight, runtime profile, GIS/numerical/candidate build, reservation, serving/publication/browser work; no commit, push or merge.
