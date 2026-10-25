# Independent supervisor review 9 — single operational Sol correction

2026-10-25. Independent non-implementing Sol reviewer `/root/sol_review_face_diag`; implementer was the different Sol session `/root/sol_review17_plan`. Authority: disposition 58 and the review dispatch, against the accepted self-check failure diagnosis (`685dbb46ec755910a93dcd7b9525b9f2dda1c6e0a0f14de85551f60456bb303f`) and dispositions 56–58. **FIX_REQUIRED. The correction is not complete: a caller-only ownership validator breaks the retained handoff update call.**

This is a static review of current W/S/H code and unchanged P/protected bytes. The operational files have no reliable Git baseline because they are untracked; no before/after index diff is claimed. Reported W/S/H-only scope is consistent with the submitted hashes and independently unchanged P/protected hashes, not proof that every unrelated workspace file is unchanged.

## Independently verified SHA-256 values

All match disposition 58 and its referenced protected bindings:

| File relative to repository root | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `1ef041092e304a6a7f270d0886e4529caeba615bf14a3fb654f92b9873a61604` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `17a7a347b175bfa3ad1a1dcbdc4167d3d4b1c8a73da0dc09d537ec1c6d4a8ef6` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `3419551b5c19e69c2487bb57c1bc49c102d4b7bfe1db1f93aea60cf038ebe05a` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| Candidate `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| Shared helper `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| Builder `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| Focused test `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| Fixture `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| Configuration `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |
| Original `.codex/build3-supervisor-selfcheck/caller-invocation.json` | `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e` |
| Original `.codex/build3-supervisor-selfcheck/caller-invocation.json.update` | `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75` |

P, candidate/helper/builder/test/fixture/configuration and both original failed evidence files remain byte-identical. The exact new `.codex/build3-supervisor-selfcheck-retry-1/` root remains absent; this review created none of its descendants. The original failed caller/pending evidence was not edited, promoted, deleted or treated as a successful self-check.

## Blocking finding

**FIX_REQUIRED — W's retained handoff call cannot pass the new caller-only update ownership contract.**

W **1255** still calls `Update-OwnedJson $handoffPath $handoffRecord`. `Update-OwnedJson` now unconditionally invokes `Assert-OwnedCallerDestination` at **121**, and again at **153**. That validator at **163–165** requires the canonical requested path to equal `$callerPath`; it also checks caller invocation ownership at **169–173**. The handoff and caller paths are distinct by construction (W **31–41**). Therefore the first validation necessarily throws at this retained handoff call, without reaching the move.

The call occurs after native `CreateProcess` succeeds and the launcher PID/creation/image fields are set (W **1239–1254**), but **before** Job assignment at **1256** and thread resume at **1269**. Every mode reaching this point is blocked, including the fixed self-check retry: the created launcher remains suspended, `launcherAssigned=false`, and the existing catch must terminate it directly. This is a deterministic source-level call-order defect, not a reproduced runtime result or a claim of an escaped process.

The caller ownership restriction itself is appropriate. The retained handoff needs its own exact already-owned destination/record validation and exclusive pending replacement path, or another separately reviewed ownership-aware design; it cannot call a helper restricted to the caller destination. Do not weaken the caller checks to admit arbitrary paths. No such fix is implemented or authorized here. Because this is the sole operational Sol correction and it fails review, dispositions 57–58 require stopping further correction/dependent dispatch for coordinator/user decision.

## Other criteria and inspected limits

| Criterion | Static disposition and evidence |
| --- | --- |
| Supported overwrite operation | **PASS for caller update mechanism:** W 125–158 exclusively creates same-directory `.update`, writes/flushes it, closes it, revalidates the existing owned caller destination/pending path, then calls explicit `File.Move(source,destination,true)`. No delete-first, in-place truncation or alternate replacement-method retry is present. Overall retained call-site compatibility is FIX_REQUIRED above. |
| Existing destination and pending ownership | **PASS for caller path:** W 162–174 requires owned/validated parent, exact canonical caller destination, no reparse, existing regular destination and matching schema/wrapper/start/mode. Stale pending is refused (122–125); failed pending evidence is not removed. These checks do not provide atomic exclusion of hostile concurrent replacement. |
| Primary/secondary persistence errors | **PASS, static:** write/flush and close failures are separated at 126–151; Save-Caller records operation/path/stage and secondary close errors at 946–975. New-CallerFailure 177–189 captures structured exception and created/assigned/resumed state. Catch preserves primary error before cleanup (1365–1371). No specific historical replacement exception is inferred from the old evidence. |
| Exclusive terminal fallback and sticky failure | **PASS, static design:** W 192–205 restricts fallback to the exact owned self-check retry root and fixed failure filename, using exclusive Write-ExclusiveJson (99–115), flush/close, existing schema and exit 2. It neither replaces caller/pending bytes nor satisfies a gate. Final terminal-save/fallback errors at 1474–1493 preserve non-PASS; fallback failure emits guarded diagnostics and does not claim durable telemetry. |
| Cleanup before fallible final evidence | **PASS for inspected cleanup structure:** W 1372–1408 attempts direct termination of an unassigned launcher or Job termination before clock telemetry. Finally 1426–1448 closes owned handles before final clock/save/fallback work. Per-operation reporting is guarded; unavailable exits remain null rather than invented success. The blocking handoff path specifically reaches the direct unassigned-launcher cleanup branch. Actual cleanup/exit observations are unmeasured here. |
| W/S/H fixed path agreement | **PASS, static:** W 23/28/31–49, S SELF_ROOT/SELF_RUN 39–40 and H EVIDENCE 17 agree on `.codex/build3-supervisor-selfcheck-retry-1/` and its `run-1`. S handoff/start/auth/log/tree-marker paths and H consumed authorization/markers derive from that root. No arbitrary path option, environment override or old-root fallback is added. |
| One-shot retry refusal | **PASS, static path design:** W 1023–1031 refuses an existing retry root and checks caller/update/fallback/handoff/consumed/start/log/run paths before preparation. Absent run-1 implies absent helper descendants; S/H retain exclusive owned run/auth consumption. Original root is not selected for new writes. This is a future fixed slot, not permission to use it. |
| Identity, containment, clocks and reserved build gates | **Retained static structure, but launch progression FAILS at the finding:** fixed W → venv launcher → base → S → H identities/nonce/one-use checks and suspended assign-before-resume remain in the source; S/H use inherited deadlines. W retains 10-second self-check, 30-second standalone and 180-second build; S retains 150-second numerical cutoff. P/profile/collection separation and reserved-build controls remain protected. No build/runtime success follows. |

## API reference and evidence boundary

Inspected the supplied official [Microsoft File.Move documentation](https://learn.microsoft.com/en-us/dotnet/api/system.io.file.move?view=net-9.0): the Boolean overload permits replacement of an existing destination and is documented for .NET Core 3.0+. W requires PowerShell 7.4+. The API itself does not supply invocation ownership or a destination-must-already-exist contract; W adds those checks. Neither that reference nor this static inspection establishes crash atomicity, directory-metadata persistence or power-loss durability. W's explicit comment at 157 appropriately makes no such claim.

Implementation-reported Ruff check/format, PowerShell AST and embedded C# compile-only PASS results in disposition 58 **were not rerun**. They do not establish retained call-site compatibility. **30-second profile fit remains unmeasured; no runtime evidence is created by this review.** The retry's real persistence, 10-second containment/exit behavior and filesystem failure paths remain untested. Filesystem/OS calls are not proven preemptible.

Review used static document/source/evidence reads, searches, directory/absence checks and SHA-256 hashing, plus reading the specifically supplied Microsoft API page and writing this report. No implementation/ledger/checkpoint/manifest/evidence file was edited. No tests, parsers/compilers/linters, imports, scripts/wrapper/self-check/preflight/runtime/collection, manifest preparation, GIS/numerical/build or browser application/product check ran. One initial diagnosis filename lookup failed; the actual diagnosis named in dispositions 57–58 was then read.

**Stop: operational allowance is exhausted (Luna 4/4 reviewed; Sol 1/1 used and FIX_REQUIRED). No retry, further correction or dependent runtime/build dispatch follows this report.** Preserve original failed evidence and the still-absent fresh retry root. Return the concrete caller-versus-handoff ownership defect for coordinator/user direction; do not reset counters or broaden scope. Historical candidate budgets and all source/origin/domain/recipe/collision/numerical constraints remain unchanged. Candidate remains **NO-GO and unservable**; build 3 remains **unreserved**.
