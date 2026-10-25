# Retry-6 W diagnostic correction cycle 2 handoff

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Dispositions 117, 119, 120 and 122. This handoff completes the existing cycle-2 verification only; it grants no self-check, path selection, root creation or runtime authority.

## Source bindings and inverse chain

| File/state | SHA-256 | Bytes |
| --- | --- | ---: |
| Current W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `804ae8c42f6637a61505e53e825972d758b8ae2c1c2d0740ff5a076a0e703b45` | 132,204 |
| Exact cycle-2 inverse W | `d7351a1cdcd9e8f6ea2c554400ff34d4f281a8c15086c87b32a132d806e549cd` | 134,567 |
| Accepted retry-5 W baseline, cycle-1 inverse target | `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0` | 107,257 |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` | — |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf` | — |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` | — |

The exact seven-span in-memory inverse was rerun. The seven replacements reproduced the previously reported candidate `ce7f6d2aa366c260a2b803165507c5cca53b1214507ab22b4c661cd3d47707de` at 134,568 bytes. As documented in the accepted Sol diagnosis [retry6-correction2-inverse-mismatch-diagnosis.md](retry6-correction2-inverse-mismatch-diagnosis.md), the candidate contains one duplicated `0A` at byte offset 83656 at the minimal-status serialization removal boundary. Removing only that diagnosed byte in memory, with no separator or normalization, gave the exact 134,567-byte inverse `d7351a1cdcd9e8f6ea2c554400ff34d4f281a8c15086c87b32a132d806e549cd`. No source file or reconstructed baseline was written.

The prior independently verified cycle-1 inverse edge is bound by [the correction-1 handoff](retry6-w-descendant-escape-correction-1-handoff.md), SHA-256 `4701ddc210ef755832a0bb8cebf3c561e51868ac961b499ddf97867fb3b25704`, and [its independent review](retry6-w-descendant-escape-correction-1-independent-review.md), SHA-256 `6ab1b80d82a6aaccad3e93ef4fa63b5016c62f8d0fa8f2844a1e5b4b4d4ce49f`. Both artifact hashes were rechecked. Those artifacts independently bind `d7351a1… → e9a0794…`; the edge composes with this handoff's exact cycle-2 inverse. The cycle-1 review was FIX REQUIRED for three behavioral corrections; its inverse verification is cited only as the prior accepted-baseline proof, not as an implementation PASS.

The earlier cycle-1 handoff's H digest was a transcription error. Disposition 119 then supplied another incorrect expected H value; disposition 120 supersedes only that H metadata with the actual unchanged H hash shown above. No prior handoff, disposition, source or evidence was edited. A later in-memory attempt to locate the pending-diagnostic initialization anchor failed before comparing a whole-file hash. Disposition 122 records that the cause is unknown and directs reliance on the already independently verified cycle-1 inverse edge; this handoff does not claim the failed anchor search completed.

## Authorized static gates

Only the authorized PowerShell AST parse and embedded C# compile-only check ran. No C# method was invoked and W was not invoked.

Command:

```powershell
$tokens=$null; $errors=$null; $path=(Resolve-Path 'pipeline/scripts/invoke_teignmouth_float32_build3.ps1').Path; $ast=[System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors); if($errors.Count){$errors|ForEach-Object{$_.ToString()};exit 1}; 'PowerShell AST parse passed'; $assignment=$ast.Find({param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left -is [System.Management.Automation.Language.VariableExpressionAst] -and $n.Left.VariablePath.UserPath -eq 'interop'},$true); if($null -eq $assignment){throw 'embedded interop assignment not found'}; $rhs=$assignment.Right.Extent.Text; if($rhs -notmatch '(?s)^@''\r?\n(.*)\r?\n''@$') {throw 'embedded C# here-string extraction failed'}; $source=$Matches[1]; Add-Type -TypeDefinition $source -Language CSharp -ErrorAction Stop; 'Embedded C# compile-only passed; no method invoked'
```

Exact output:

```text
PowerShell AST parse passed
Embedded C# compile-only passed; no method invoked
```

## Preservation checks

The accepted evidence matrix in the correction-1 handoff (SHA-256 above) was re-read as metadata and compared to read-only SHA-256 results. Exactly 53 prior evidence files were enumerated; all 53 relative names and hashes matched, with no missing, changed or unlisted files. Retry-5 remained 16/16 unchanged. Consumed evidence contents were not opened or used.

All six protected source/config/test files matched the accepted values:

| Protected file | SHA-256 |
| --- | --- |
| `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |

Current W and unchanged S/H/P all matched the expected hashes in disposition 120. The H value is `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf`.

## Scope and handback

No source or evidence bytes changed. No tests, imports, linter, runtime, process probes, source invocation, wrapper, self-check, preflight, path selection, retry-6 root creation, candidate/GIS/numerical build, reservation, browser/publication work, commit, push or merge occurred. The original 10-second QPC deadline and all correction-1 behavior remain unchanged.

Retries 1–5 remain consumed, immutable and non-PASS. Retry-6 remains absent, unselected and unreserved. The candidate remains **NO-GO and unservable**; build 3 remains unreserved. Stop for a separate coordinator decision on independent Sol implementation review.
