# Retry-7 path-literal implementation handoff

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** D148, accepted retry-7 path-binding plan SHA-256 `ea4527b3f0824adb8349d7dfc511d150d98ab8792d953490a257ccf6c589f935`, independent plan PASS SHA-256 `4d53a66c09807ba22df426478c860a7dbe0c6b978845d572e2c9ff8947be4c80`.

This handoff records only the four authorized source literal changes and static/preservation gates. It does not inspect, select, reserve, or probe a retry-7 path or root, and authorizes no invocation.

## Baselines and final source hashes

Pre-edit hashes and byte lengths matched D148 before writing:

| File | Pre-edit SHA-256 | Final SHA-256 | Bytes |
| --- | --- | --- | ---: |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `f600efc92fd040aa5b91cf543210be139ed50f895eba7d62c34175e73dc7dc8b` | `842a599fda7d9082b56efb792b10154d3e9096af8ac755f16318777d1495eef8` | 132204 |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `fda96d4edd66327e50c34ee1345d1a098aced4a7b58dcd1c088a4cd8c44c616f` | `8f4dbda2346db49a0b9cead30b33a8515879f9955bbec59d64e23386615f5016` | 239737 |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `75678b51d0e17d89862bf0a7ee3446014969ba73aae6cd31606288553b163e27` | `f9f48f34198fe54eab800e8d2bc619631c11ce8ed44751a24a2c126e316ed373` | 12419 |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` | unchanged `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` | 83851 |

## Exact byte delta and inverse proof

Only the final ASCII digit changed from `6` (`0x36`) to `7` (`0x37`) in these four plan-authorized spans:

| File/span | Literal changed | Byte offset of literal (zero-based) | Changed digit byte offset |
| --- | --- | ---: | ---: |
| W23 `baseEvidence` | `.codex\build3-supervisor-selfcheck-retry-6` → `.codex\build3-supervisor-selfcheck-retry-7` | 891 | 932 |
| W344 `expectedRoot` | `.codex\build3-supervisor-selfcheck-retry-6` → `.codex\build3-supervisor-selfcheck-retry-7` | 17036 | 17077 |
| S39 `SELF_ROOT` | `.codex/build3-supervisor-selfcheck-retry-6` → `.codex/build3-supervisor-selfcheck-retry-7` | 1428 | 1469 |
| H17 `EVIDENCE` | `.codex/build3-supervisor-selfcheck-retry-6/run-1` → `.codex/build3-supervisor-selfcheck-retry-7/run-1` | 344 | 385 |

The patch read raw bytes, verified every pre-edit SHA and exact occurrence count, constructed the new byte arrays, reversed the four substitutions in memory before writing, and required exact baseline SHA and equal file length. A post-write inverse independently produced the same results:

- W final → exact D148 baseline `f600efc92fd040aa5b91cf543210be139ed50f895eba7d62c34175e73dc7dc8b`, 132204 bytes.
- S final → exact corrected D148 baseline `fda96d4edd66327e50c34ee1345d1a098aced4a7b58dcd1c088a4cd8c44c616f`, 239737 bytes.
- H final → exact D148 baseline `75678b51d0e17d89862bf0a7ee3446014969ba73aae6cd31606288553b163e27`, 12419 bytes.
- P remained byte-identical at `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`, 83851 bytes.

Equal lengths and whole-file inverse hashes establish that all non-literal bytes, including encoding and newline bytes, were preserved. The raw-byte editing and inverse scripts were in-memory PowerShell commands; no baseline or reconstructed source was written.

## Literal counts and scoped consumer search

Final retry-7 literal counts are W=2, S=1, H=1, P=0. Retry-6 literal counts in W/S/H/P are all zero. A fixed-string recursive search of `pipeline/scripts`, `pipeline/tests`, and `config` found exactly the four new source consumers below and no old retry-6 consumers or additional retry-7 consumer:

```text
pipeline/scripts\invoke_teignmouth_float32_build3.ps1:23:    'self-check' { Join-Path $root '.codex\build3-supervisor-selfcheck-retry-7' }
pipeline/scripts\invoke_teignmouth_float32_build3.ps1:344:    $expectedRoot = Join-Path $root '.codex\build3-supervisor-selfcheck-retry-7'
pipeline/scripts\run_teignmouth_float32_build3.py:39:SELF_ROOT = ROOT / ".codex/build3-supervisor-selfcheck-retry-7"
pipeline/scripts\teignmouth_build3_supervisor_selfcheck.py:17:EVIDENCE = ROOT / ".codex/build3-supervisor-selfcheck-retry-7/run-1"
```

P has no matching consumer. No strict/default/cleanup or launch behavior was edited; their full source bytes return exactly to the accepted D148 hashes under the inverse proof.

## Authorized static gates

Commands run:

```powershell
& 'pipeline\.venv\Scripts\python.exe' -m ruff check 'pipeline/scripts/run_teignmouth_float32_build3.py' 'pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py'
& 'pipeline\.venv\Scripts\python.exe' -m ruff format --check 'pipeline/scripts/run_teignmouth_float32_build3.py' 'pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py'
```

Exact output:

```text
All checks passed!
2 files already formatted
```

W-only PowerShell AST parse command:

```powershell
$tokens=$null; $errors=$null; $path=(Resolve-Path 'pipeline/scripts/invoke_teignmouth_float32_build3.ps1').Path; [System.Management.Automation.Language.Parser]::ParseFile($path,[ref]$tokens,[ref]$errors) > $null; if($errors.Count){$errors|ForEach-Object{$_.ToString()}; exit 1}; 'PowerShell AST parse passed; W was not invoked'
```

Exact output: `PowerShell AST parse passed; W was not invoked`. No W function or script was invoked.

## Immutable evidence and protected hashes

The read-only preservation command parsed the accepted 53-row matrix from `retry6-w-descendant-escape-correction-1-handoff.md` and the 17-row retry-6 inventory from `coordinator-disposition-129.md`, formed the 70 expected relative-name/SHA pairs, enumerated files only under the seven documented prior evidence roots, and hashed each expected prior file. It did not open consumed evidence for content diagnosis. Exact output:

```text
Accepted matrix rows: 53; D129 retry-6 inventory rows: 17; total expected: 70
Actual prior-evidence file count: 70
Missing=0; unlisted=0; changed hashes=0
70/70 exact names/counts/hashes PASS; retry-5 16/16 unchanged
```

All six protected hashes matched:

| Protected file | SHA-256 |
| --- | --- |
| `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |

Exact output concluded `6/6 protected hashes PASS`. No prior evidence file was changed. Retry-1 through retry-6 remain consumed, immutable and non-PASS; retry-5's 16 files remain unchanged.

## Limits and handoff

No retry-7 path/root/ancestor/alias/absence inspection, creation or reservation occurred. No process inspection, test, import, direct S/H invocation, self-check, preflight, build, runtime, GIS/numerical work, serving/publication, commit, push or merge occurred. The one-use retry-7 gate remains separate and mandatory. This is an implementation handoff, not independent actual-byte review or a runtime result. Stop for independent Sol actual-byte review; no next execution is authorized by this report.
