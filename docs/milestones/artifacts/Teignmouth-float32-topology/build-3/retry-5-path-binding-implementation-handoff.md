# Retry-5 path-binding implementation handoff

Date: 2026-10-25. Implemented under coordinator disposition 104 and the two-span W recovery authorized by disposition 107. Plan SHA-256: `1983a1559598766bb280c67546af1b4350e6959039c2cdf0c0edd36b98a5db0e`; plan review PASS: `0ca9c416765f681639b1a3f9fe9e9a5bd4992199e1a4bd1fd152996c11c81467`.

## Exact source changes and hashes

Changed exactly four parent/leaf path literals in W/S/H and the two authorized W indentation spans. No other source bytes or files were changed. W line 23 leading ASCII spaces changed 8→4 and line 344 0→4 to recover exact W bytes; source was updated by byte-preserving span edit, not template or Git restoration.

| File | Final SHA-256 | New path occurrences | Old retry-4 occurrences | In-memory inverse SHA-256 |
| --- | --- | ---: | ---: | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0` | 2 | 0 | `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` | 1 | 0 | `28c92cc60e38ae23dcf58874eca67b8308b22772eee03b36d69471624fcdb089` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf` | 1 | 0 | `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py`, unchanged | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` | 0 | 0 | unchanged |

The exact consumers are W `self-check` parent (line 23), W independent fallback allowlist (line 344), S `SELF_ROOT` (line 39), and H `EVIDENCE` fixed `run-1` leaf (line 17). Static `rg` search under `pipeline/scripts`, `pipeline/tests`, and `config` returned exactly these four retry-5 matches and no retry-4 matches. The PowerShell byte-level inverse changed only each literal span in memory and matched all three required inverse hashes. The projected W after the two indentation corrections also matched `e9a079…` before writing. The earlier failed W inverse check is reconciled by disposition 107 as exactly the two indentation spans; the corrected final inverse now passes.

## Retry-5 path observations

Before and after editing, `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-5` was absent. `.codex` force enumeration found zero case-insensitive or trailing-dot/space-normalized aliases. `C:\`, `C:\vibe`, workspace, and `.codex` were directories without ReparsePoint; resolved paths matched their expected canonical spellings. No retry-5 root or leaf was created or inspected.

## Prior evidence preservation

The complete read-only comparison checked 37 existing files against accepted matrices: 2 original + 2 retry-1 + 11 retry-2 + 11 retry-3 + 11 retry-4. All 37 relative paths/counts and SHA-256 values matched. The authoritative retry-4 supervisor-start digest is `72f9f46afadbd1199b5bffb091ed9dba06a23297c194f6de985f07a27e0d306d`; an earlier `...b5bfbb...` comparison value was a transcription error reconciled by disposition 105.

| Preserved evidence path | SHA-256 |
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

All consumed evidence remains unchanged. No retry-5 root or evidence was created.

## Protected source/config/test hashes

| Protected file | SHA-256 |
| --- | --- |
| `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |

## Exact authorized checks

Run from `pipeline/`:

- `.venv/Scripts/python.exe -m ruff check scripts/run_teignmouth_float32_build3.py scripts/teignmouth_build3_supervisor_selfcheck.py` — exit 0, `All checks passed!`
- `.venv/Scripts/python.exe -m ruff format --check scripts/run_teignmouth_float32_build3.py scripts/teignmouth_build3_supervisor_selfcheck.py` — exit 0, `2 files already formatted`
- `$tokens=$null; $errors=$null; [System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path 'scripts/invoke_teignmouth_float32_build3.ps1'),[ref]$tokens,[ref]$errors) > $null; if($errors.Count){$errors|ForEach-Object{$_.ToString()};exit 1}; 'PowerShell AST parse passed'` — exit 0, `PowerShell AST parse passed`; parse-only, W was not dot-sourced or invoked.
- Static byte proof compared the final W/S/H bytes, counted 2/1/1 new retry-5 literals, confirmed zero old retry-4 literals, reversed only those path bytes in memory and matched the three baseline hashes above. No reconstructed source was written or executed.
- Static `rg` search for retry-5 across `pipeline/scripts pipeline/tests config` produced exactly the four W/S/H lines listed above. The corresponding retry-4 search produced no matches (rg exit 1 for no matches).
- PowerShell preservation comparison enumerated the five old evidence roots and compared every relative path/count/hash against the accepted matrices: `37 files, 37 matched, PASS`. The table above lists each result.

No tests/imports/operational scripts/process probes/wrapper/self-check/preflight/runtime/build/browser work ran. Candidate remains **NO-GO and unservable**; retry-5 remains absent and unconsumed. Fresh independent Sol implementation review and a separate coordinator one-use gate are still required. No self-check is authorized here.

