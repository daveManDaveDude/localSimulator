# Coordinator disposition 120 — correct H hash metadata and finish cycle-2 handoff

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User's continuing authorization for bounded attempts; disposition 119; coordinator read-only hash verification.

## H hash metadata correction

Disposition 119 contains a transcription error in the expected H hash. The actual current H file `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` hashes to `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf`. This matches the established retry-5 implementation handoff/review and the cycle-2 Sol diagnosis. The different value `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3f1c1db5299e25560bf` in disposition 119 was never an accepted source hash. Disposition 119 is preserved unchanged; this disposition supersedes only its incorrect H hash value.

Luna correctly stopped before handoff when its H check did not match the mistaken value. Coordinator's read-only `Get-FileHash` result confirms actual H is unchanged; no H or other source bytes changed.

## Bounded Luna authority — finish existing handoff

Resume the cycle-2 handoff under dispositions 117/119 with **no source or evidence edits**. Re-run only the already-authorized checks to record a complete durable result: exact seven-span in-memory inverse to W `d7351a1…` (134,567 bytes) and documented cycle-1 inverse to accepted W `e9a0794…`; PowerShell AST parse; embedded C# compile-only with no method invoked; 53-file evidence hash matrix; six protected source/config/test hashes; and S/H/P hashes. Require H exactly `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf`, with S `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` and P `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`.

Write the complete cycle-2 handoff with exact results and identify disposition 119's expected H value as a coordinator metadata transcription error. If any check fails or any value is unexpected, stop without edits. Stop after handoff for a separate coordinator decision on Sol implementation review.

No tests/imports/linter, runtime/process probe, source invocation, wrapper, self-check, preflight, path selection, retry-6 root creation, GIS/numerical/candidate build, reservation, browser/publication work, commit, push or merge. Retries 1–5 remain consumed, immutable and non-PASS; retry-6 remains absent and unselected; candidate **NO-GO and unservable**; build 3 unreserved; 10-second QPC deadline unchanged.
