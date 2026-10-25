# Retry-6 W diagnostic correction cycle 1 handoff

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Coordinator disposition 115. This is Luna correction cycle 1 for the six findings in the independent FIX REQUIRED review. It grants no self-check, path selection, root creation, or runtime authority.

## Source hashes and preservation

| File | SHA-256 |
| --- | --- |
| Current W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `d7351a1cdcd9e8f6ea2c554400ff34d4f281a8c15086c87b32a132d806e549cd` |
| Pre-correction W, disposition 114 review binding | `dee858ce20851a306b157096d106ff79f6e9a6f89875f40dfee9d4b828bc9442` |
| Accepted retry-5 W baseline | `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1c1db5299e25560bf` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

W is 134,567 bytes, UTF-8 without BOM, LF-only (zero CR bytes), final LF retained. No S/H/P or path literal changed. The original 10-second total QPC deadline remains. No retry-6 path or root was selected or created.

## Exact source delta and inverse proofs

The correction changed only W's diagnostic region from `function Get-DescendantProcessIds` up to (but not including) `function Get-PyvenvPolicy`. No bytes outside that W region changed during correction. The exact inverse replaces that one region with the same region from a read-only pre-correction W snapshot whose SHA-256 was verified as `dee858ce20851a306b157096d106ff79f6e9a6f89875f40dfee9d4b828bc9442`; the reconstructed whole-file SHA-256 matched `dee858ce20851a306b157096d106ff79f6e9a6f89875f40dfee9d4b828bc9442` exactly.

The accepted-baseline inverse was also rerun. The accepted `e9a079…` baseline was derived from verified Git blob `a742ddc1aea8cf05b8059879d83bcf8230b1f005` using the documented historical path/access-literal substitutions. Replacing the diagnostic region with the accepted-baseline region, removing the one pending-state initialization, the added `GetProcessRows(..., out int terminalError)` overload, and the catch attachment block restored the whole W hash to `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0`. No reconstructed baseline was written.

The six review findings were corrected within that region:

1. `Test-DiagnosticCaptureTime` now reads the initialized `capture.cutoffQpc`. Both reserve and skipped/late payload construction paths carry that same cutoff.
2. Snapshot bookkeeping copies the supplied roots into a bounded UInt32 array and records `rootsCapped`. The emitted observation retains those values. Chain reconstruction visits no more than 64 edges, checks the cutoff while walking/storing and immediately before completion, and leaves `terminalRoot` null for a capped, late, ambiguous, or otherwise incomplete chain. The existing ancestry scan keeps its original `foreach` row iteration and first-discovery predicate.
3. Optional snapshot/Job/membership clocks, dictionary construction, root/predecessor bookkeeping, serialization, and later diagnostic count/message updates are guarded. A failed `IsProcessInJob` captures `Marshal.GetLastWin32Error()` immediately in diagnostic mode, then raises the existing primary error without a post-query clock. A successful false result is added to the existing uncontained list before any post-query QPC or diagnostic allocation. Optional failures cannot replace that committed rejection.
4. In `finally`, the only close call is the first native operation. Build/preflight and non-rejection paths retain the original direct `CloseHandle` behavior, including propagation of a raised close call. On an established self-check false-membership rejection, a raised/false close is recorded as secondary/unconfirmed and cannot replace the primary failure. There is no retry or second close.
5. When the one-second reserve or 20 ms cutoff is unavailable, the capture helper returns a small skipped/late summary without copying Job IDs, allocating a chain, or issuing either extra process query; control proceeds directly to the one close. Chain work and storage are each capped at 64 edges, with cutoff checks before promotion to complete.
6. The original Job ID count is captured before any bounded copy. The full-detail branch copies at most the first 64 IDs into a distinct array; no-reserve/late branches report the saved original count and an explicit skipped/late status. Serialization now makes at most one minimal fallback attempt, whether the full payload is over 16,384 UTF-8 bytes or full serialization fails; fallback remains capped at 1,024 bytes.

The payload continues to label association `snapshot-incarnation-unproven`. Creation time and image path from the retained query handle do not authenticate the earlier snapshot PID, parent incarnations, helper/conhost class, ownership, or mapped bytes. Diagnostic fields do not alter acceptance. Native calls and PowerShell allocation remain non-preemptible; the 20 ms/one-second checks do not promise hard timing or guaranteed cleanup duration.

## Authorized static gates

Only the disposition-authorized PowerShell AST parse and embedded C# compile-only check ran. The interop type was compiled, but no type method was called and W was not invoked.

Exact PowerShell AST and C# compile-only command:

```powershell
$tokens=$null; $errors=$null; $path=(Resolve-Path 'pipeline/scripts/invoke_teignmouth_float32_build3.ps1').Path; $ast=[System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors); if($errors.Count){$errors|ForEach-Object{$_.ToString()};exit 1}; 'PowerShell AST parse passed'; $assignment=$ast.Find({param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left -is [System.Management.Automation.Language.VariableExpressionAst] -and $n.Left.VariablePath.UserPath -eq 'interop'},$true); if($null -eq $assignment){throw 'embedded interop assignment not found'}; $rhs=$assignment.Right.Extent.Text; if($rhs -notmatch '(?s)^@''\r?\n(.*)\r?\n''@$') {throw 'embedded C# here-string extraction failed'}; $source=$Matches[1]; Add-Type -TypeDefinition $source -Language CSharp -ErrorAction Stop; 'Embedded C# compile-only passed; no method invoked'
```

Exact output:

```text
PowerShell AST parse passed
Embedded C# compile-only passed; no method invoked
```

No tests, imports, Ruff, runtime, source invocation, wrapper, self-check, preflight, or process probe ran. Syntax and compile success is not behavioral proof.

## Protected source/config/test hashes

Read-only final recheck matched all six accepted values:

| Protected file | SHA-256 |
| --- | --- |
| `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |

## Immutable prior evidence: 53/53

Disposition 115 recheck compared exact relative names, counts, and SHA-256 against the accepted matrices from the retry-5 implementation handoff and disposition 110. Enumeration returned 53 files, with zero missing, changed, or unlisted files. Retry-5 remains 16/16 unchanged. This repeats the full prior matrix in [the implementation handoff](retry6-w-descendant-escape-implementation-handoff.md); below are the full verified names and hashes for this correction boundary.

| Evidence path | SHA-256 |
| --- | --- |
| `.codex/build3-supervisor-selfcheck/caller-invocation.json` | `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e` |
| `.codex/build3-supervisor-selfcheck/caller-invocation.json.update` | `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75` |
| `.codex/build3-supervisor-selfcheck-retry-1/caller-invocation.json` | `f992b356191d202a5e2357cffb1d64d90b4dd7f8ac54cd0b76ab2e0d7540dcf3` |
| `.codex/build3-supervisor-selfcheck-retry-1/self-check-handoff.json` | `b73738fc81644b942ea4f84890146e1bdfc73d925005552cb34db1af05aadc79` |
| `.codex/build3-supervisor-selfcheck-retry-2/caller-invocation.json` | `4dbb3ff5f821edefe0a9d5fa1c822ef7cb0d296f346853013d620a3abaf5f00e` |
| `.codex/build3-supervisor-selfcheck-retry-2/self-check-handoff.consumed.json` | `bb773f7991eaa34c9f87ede7df8dd48d4eea899fbbd711eea009e3f7631abb0c` |
| `.codex/build3-supervisor-selfcheck-retry-2/supervisor-script-start.json` | `8ecc5f87c87c90b3f1b73e9bf07814b7b6409a308971a6c83751be09c4f058d5` |
| `.codex/build3-supervisor-selfcheck-retry-2/supervisor.stderr.log` | `92875c22d9084e2f791f53e02c09bc03d6b2bd16f28655fcffa3be5380c3ba51` |
| `.codex/build3-supervisor-selfcheck-retry-2/supervisor.stdout.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-2/run-1/invocation.json` | `7b40f2f6f218e491034c6f621108faedf6d0137557379f80fa0802c2313ab592` |
| `.codex/build3-supervisor-selfcheck-retry-2/run-1/nonzero-authorization.consumed.json` | `e448045f4930ff8ab2c47341daeabb63bd0cef8008f5265b1d344167d53548f8` |
| `.codex/build3-supervisor-selfcheck-retry-2/run-1/nonzero-helper.json` | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| `.codex/build3-supervisor-selfcheck-retry-2/run-1/nonzero-script-start.json` | `767458b7ce651898f16c7bec8c2d3370eeaaff4d1d1802663edf3b77b7b86d24` |
| `.codex/build3-supervisor-selfcheck-retry-2/run-1/nonzero.stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-2/run-1/nonzero.stdout.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-3/caller-invocation.json` | `f1bf3a880a821626daef625f60459d037a8aa9509246e401a06f9440cb8134d6` |
| `.codex/build3-supervisor-selfcheck-retry-3/self-check-handoff.consumed.json` | `dd82b4bd6cdfafa76fd5be2505cf438125f9deb70d37f73dbaf03a7f719d93b6` |
| `.codex/build3-supervisor-selfcheck-retry-3/supervisor-script-start.json` | `bf0f5eed47455f27a037dea7fbeca068bf4ac2d9a72598e70c21c90b7c835a90` |
| `.codex/build3-supervisor-selfcheck-retry-3/supervisor.stderr.log` | `18d4873d35189bf11f26f2df45a60574330fde3c27bf02371542b37a4b46fea8` |
| `.codex/build3-supervisor-selfcheck-retry-3/supervisor.stdout.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-3/run-1/invocation.json` | `dcf98d8471df615acbaa74d3eece7f8a774e86cac22b0864931e556f2ae627e5` |
| `.codex/build3-supervisor-selfcheck-retry-3/run-1/nonzero-authorization.consumed.json` | `0b64cd4ffc826e052423ab501f55da267675ee8f5c345c4c7613b6076b283d3a` |
| `.codex/build3-supervisor-selfcheck-retry-3/run-1/nonzero-helper.json` | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| `.codex/build3-supervisor-selfcheck-retry-3/run-1/nonzero-script-start.json` | `0da552f3943a321f31e5bceac24fe74471e6a1c75367a852430f2e2d3ae0ffa3` |
| `.codex/build3-supervisor-selfcheck-retry-3/run-1/nonzero.stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-3/run-1/nonzero.stdout.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-4/caller-invocation.json` | `127af0f90b23a5048e72eedf992080016491a3a9590f694ea63d15f3dd244fe9` |
| `.codex/build3-supervisor-selfcheck-retry-4/self-check-handoff.consumed.json` | `842925a205014286e6d9a5b5cf1822cfe6f41499f4b0bf3a63c5d9831264631d` |
| `.codex/build3-supervisor-selfcheck-retry-4/supervisor-script-start.json` | `72f9f46afadbd1199b5bffb091ed9dba06a23297c194f6de985f07a27e0d306d` |
| `.codex/build3-supervisor-selfcheck-retry-4/supervisor.stderr.log` | `18d4873d35189bf11f26f2df45a60574330fde3c27bf02371542b37a4b46fea8` |
| `.codex/build3-supervisor-selfcheck-retry-4/supervisor.stdout.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-4/run-1/invocation.json` | `db81b0941a113733e5661005c5e1f99f89431a36701f5ae7a8b90acc95b720f4` |
| `.codex/build3-supervisor-selfcheck-retry-4/run-1/nonzero-authorization.consumed.json` | `ca6e9da7f0bc10e4b49160c1d66ceba3fad31097e38548cbc3d0671179ea7627` |
| `.codex/build3-supervisor-selfcheck-retry-4/run-1/nonzero-helper.json` | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| `.codex/build3-supervisor-selfcheck-retry-4/run-1/nonzero-script-start.json` | `fc551dde8e2be7b93238561092d28e538402b7265e77d1fb2e7ebe6a32957ec2` |
| `.codex/build3-supervisor-selfcheck-retry-4/run-1/nonzero.stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-4/run-1/nonzero.stdout.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-5/caller-invocation.json` | `87adbe38bcbf779eb7e41cd0ba70e6ebe0d395d15cb6e62721a9b2d0b1034906` |
| `.codex/build3-supervisor-selfcheck-retry-5/supervisor-script-start.json` | `0c75e56e765756b30ed06f8204a145a8c8d82ee2844009f385b7460bc26f86c0` |
| `.codex/build3-supervisor-selfcheck-retry-5/supervisor.stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-5/supervisor.stdout.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-5/self-check-handoff.consumed.json` | `cafc18f3965daf968dfff056367d8bb7f8011654e16eba30c3a3679d16115d36` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/invocation.json` | `e87a0e404117ce1ef552c14ff66634df57bc2d895aa1cada9aba020e7b22651a` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/nonzero-authorization.consumed.json` | `b3d40f91b26186a46577f27813886bacbb3f534a8ce010a0f20c3fff475ba098` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/nonzero-helper.json` | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/nonzero-script-start.json` | `60b0388b1c6dd733771b16abd78aec9e3ba839111396690d8b9ddf5173e57dc4` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/nonzero.stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/nonzero.stdout.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/tree-root-authorization.consumed.json` | `b9d35fb31fd6677d1cec2d40fb869d79348a98ba57828c7c12845f86a5baea0d` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/tree-root-script-start.json` | `5f1e7db08802fd76a68bc1ac985ea3995cbedd0097218525eaeb01b3fe9e188e` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/tree-root-started.json` | `630e0b7d264d07c61dd4d8cf0aba8f9bf77a0ab376d43fe857b1c942e39b2e25` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/tree.stderr.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.codex/build3-supervisor-selfcheck-retry-5/run-1/tree.stdout.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## Handback

All six disposition-115 findings have a bounded W-only correction. The inverse to pre-correction W and the inverse chain to accepted `e9a079…` both pass. AST/C# compile-only, 53-file preservation, six protected hashes, and unchanged S/H/P pass. No tests, imports, source invocation, process probes, self-check, retry-6 path/root work, candidate build, or publication occurred. Retries 1–5 remain consumed, immutable and non-PASS; candidate remains **NO-GO and unservable** and build 3 unreserved. Stop for independent Sol implementation review of these exact W bytes.
