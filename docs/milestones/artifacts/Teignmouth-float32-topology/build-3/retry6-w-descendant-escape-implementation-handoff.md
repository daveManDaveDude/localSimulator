# Retry-6 W descendant-evidence implementation handoff

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Coordinator disposition 113, W-only Luna implementation of the accepted retry-6 diagnostic plan. This handoff does not authorize a self-check, a retry-6 path, or root creation.

## Implementation and source hashes

Changed source: `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` (W) only. S/H/P, protected source/config/test files, and consumed evidence were not edited.

| File | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `dee858ce20851a306b157096d106ff79f6e9a6f89875f40dfee9d4b828bc9442` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

W remains UTF-8 without BOM, LF-only (zero CR bytes), with a final LF. W is 128,305 bytes. No `retry-6` or `retry6` path literal was added. The original self-check budget remains `10.0` seconds. No retry-6 path was selected and no root was created.

## Exact accepted-baseline and delta proof

The accepted retry-5 W baseline was reconstructed in memory from verified Git blob `a742ddc1aea8cf05b8059879d83bcf8230b1f005`. The raw blob is 107,254 bytes, SHA-256 `c8fcd7c3d4ae8b1535f930533c838bd7e1818624c83798961b388f90660ccb74`; its Git object framing SHA-1 recomputed to `a742ddc1aea8cf05b8059879d83bcf8230b1f005`.

In memory, the blob was transformed with only the recorded historical changes: two retry-1 parent paths to retry-4, `u` suffixes on the three `CreateFile` access literals (one `0x80000000`, two `0x40000000`), then two retry-4 parent paths to retry-5. The intermediate SHA-256 matched accepted retry-4 W `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b`; the final derived baseline matched accepted retry-5 W `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0`.

The exact inverse used the derived accepted retry-5 baseline spans for the modified `Get-DescendantProcessIds` / `Assert-OwnedJobTree` region, removed the one new script-local pending-state initialization, restored the baseline single `GetProcessRows` method in place of the two current overload lines, and removed the catch attachment block. The resulting in-memory SHA-256 was exactly `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0`. This proves there are no other byte differences outside those plan spans. The first manual inverse attempt omitted the new second C# overload line and failed; that was a proof-script omission, not a source change. The exact-span inverse then passed. No reconstructed baseline was written.

Line-level change groups against that exact baseline:

1. Current W lines 1009–1325 replace baseline lines 1009–1056. This adds the optional diagnostic sink to the existing ancestry walk, bounded row/duplicate/predecessor bookkeeping, private bounded chain/detail/serialization helpers, and first-successful-false-membership capture in `Assert-OwnedJobTree`. Snapshot QPC reads and all other added diagnostic bookkeeping are guarded by the self-check-only observation sink; default callers retain the original QPC behavior and one-argument native snapshot path. The original numeric descendant set and false-membership rejection remain in place.
2. Current W line 1466 initializes one script-local pending diagnostic value.
3. Current W lines 1553–1554 retain the baseline one-argument `GetProcessRows(long deadline)` body unchanged and add an `out int terminalError` overload. The diagnostic overload captures `Marshal.GetLastWin32Error()` immediately after `Process32Next` returns false and returns the same collected rows.
4. Current W lines 1925–1937 append the optional bounded JSON suffix to the existing primary error message after the catch's existing cleanup and clock observations, only when the exact primary message corresponds to the current assertion and caller persistence has not failed.

No algorithm replacement, membership exemption, later census, retry, new acceptance path, identity attestation, source path change, or caller schema field was added.

## Static gates

Only the disposition-authorized PowerShell AST parse and embedded C# compile-only gate ran. Neither invoked W nor called a native/C# method.

Exact command:

```powershell
$tokens=$null; $errors=$null; $path=(Resolve-Path 'pipeline/scripts/invoke_teignmouth_float32_build3.ps1').Path; $ast=[System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors); if($errors.Count){$errors|ForEach-Object{$_.ToString()};exit 1}; 'PowerShell AST parse passed'; $assignment=$ast.Find({param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left -is [System.Management.Automation.Language.VariableExpressionAst] -and $n.Left.VariablePath.UserPath -eq 'interop'},$true); if($null -eq $assignment){throw 'embedded interop assignment not found'}; $rhs=$assignment.Right.Extent.Text; if($rhs -notmatch '(?s)^@''\r?\n(.*)\r?\n''@$') {throw 'embedded C# here-string extraction failed'}; $source=$Matches[1]; Add-Type -TypeDefinition $source -Language CSharp -ErrorAction Stop; 'Embedded C# compile-only passed; no method invoked'
```

Exact output:

```text
PowerShell AST parse passed
Embedded C# compile-only passed; no method invoked
```

No tests, imports, Ruff, source invocation, wrapper, self-check, preflight, runtime or process probe ran. Syntax and compile success is not behavioral proof.

## Preserved evidence: all 53 prior files

Disposition 113 released comparison against the accepted full name/count/hash matrices: original root 2 + retry-1 2 + retry-2 11 + retry-3 11 + retry-4 11 + retry-5 16 = **53 files**. Read-only enumeration found exactly 53 files; all 53 names and hashes matched, with zero unlisted files. Retry-5's 16/16 hashes match and remain byte-identical.

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

## Six protected source/config/test hashes

All six hashes equal the accepted bindings; no mismatch was found.

| Protected file | SHA-256 |
| --- | --- |
| `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |

## Known static conformance finding and limits

The initial W draft had two diagnostic-only snapshot QPC reads on default callers. Under the coordinator's explicit correction instruction, both reads are now conditional on the self-check-only observation sink. The one-argument `GetProcessRows(long deadline)` body is also retained verbatim, so default callers take the original snapshot path. The exact inverse, AST parse, and compile-only check were rerun after this correction. Independent Sol review is still required; no implementation acceptance is claimed here.

The 20 ms opportunity and one-second reserve are best-effort checks around finite optional work. Native calls, PowerShell allocation and persistence are not preemptible by these checks, and actual API/cleanup/persistence timing is unmeasured. Snapshot PIDs and later same-handle creation/image observations do not prove that the handle represents the same process incarnation in the earlier snapshot ancestry. No parent incarnation, helper/conhost class, ownership, or mapped bytes are authenticated. Diagnostic fields never authorize success or excuse the original false-membership rejection. No behavioral test or runtime validation occurred.

Retry-1 through retry-5 remain consumed, immutable and non-PASS; retry-5 specifically remains 16/16 unchanged. Candidate remains **NO-GO and unservable**; build 3 remains unreserved. No commit, push or merge. Stop for independent Sol implementation review of these exact W bytes and the noted default-path clock issue. A fresh path plan/review and separate coordinator one-use gate remain mandatory before any future invocation.
