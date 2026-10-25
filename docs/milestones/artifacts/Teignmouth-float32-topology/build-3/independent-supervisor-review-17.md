# Independent supervisor review 17 — retry-3 fixed path

2026-10-25. Independent non-implementing Sol reviewer `/root/sol_review_face_diag`, under dispositions 75/76. **PASS — static acceptance of exactly four retry-3 path substitutions.** Reviewed actual W/S/H/P against accepted `retry-3-path-binding-plan.md`, independently hashed as `3bdc636d8b260a4e9ab9c0b99aed3b8e08f502366cf2c3597e66b855a4ebf011`. No actionable implementation finding was identified. This report neither runs nor authorizes a self-check.

## Exact revisions and inverse proof

| Source | Independently verified current SHA-256 | New/old active root counts | In-memory inverse SHA-256 |
| --- | --- | --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `c3f1f49cb574793c1cdbc2d905fd3d36f646b6f32ffb7c200a96c9792d5ce84f` | 2 / 0 | `3078e1df4bf89438208bbcfc09150dbce77f180259f847a84287892d26662989` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `d498bc294390d8645c6acc59773ba50f417493926d8bbfb3564d34504e8a407a` | 1 / 0 | `9452b2b00f3c72b8bef5f9a2e5cab2992947d0072a71901710cac129057c0733` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `cf1145b33397066559b89c11aa1cb0ebcf4d6d4d470f6521d96fe9e1f4ecccab` | 1 / 0 | `e3cdadced5d90a669155002870636610e77df68b8a013deeef187893fbd65e78` |

Read exact current bytes, reversed only the four new retry-3 strings to retry-2 **in memory**, and hashed without writing/executing reconstructed source. The inverse hashes exactly match the plan's current accepted baselines. Literal locations are W **23** self-check parent, W **344** independent fallback allowlist, S **39** SELF_ROOT, H **17** EVIDENCE/run-1. There are no unintended byte/encoding/newline changes. P remains wholly unchanged at `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`.

No reliable Git index baseline is claimed. The earlier S digest beginning **`957157…` remains unsaved/untraceable**; this proof establishes the path delta from review 16's actual accepted S, not missing historical provenance or an exact original reaping delta.

## Path, ownership and safety matrix

| Criterion | Static assessment |
| --- | --- |
| W caller/fallback | **PASS:** W 21–49 derives caller/update/failure, handoff/update/consumed, supervisor-start and parent stdio from retry-3 only for self-check. Independent fallback allowlist at 343–356 names the same exact retry-3 parent and fixed failure filename; existing exclusive failure-only ownership and sticky exit 2 remain. |
| W ↔ S parent protocol | **PASS:** W selected-mode Handoff validator derives its exact path from baseEvidence; S 569–587 derives the same parent start/handoff/consumed paths from SELF_ROOT. Literal schema/proposed-and-persisted caller owners, separate PREPARED snapshot/digest authority, only-five-fields bound-launcher transition, nonce/native identity and both replacement validations are byte-identical outside the path spans. Neither consumed root supplies authority to the new one. |
| Parent before leaf | **PASS:** W 1203–1242 refuses occupied parent or stale caller/pending/fallback/handoff/pending/consumed/start/log/run paths, then may create only the parent and exclusive W records during a later authorized invocation. S authenticates the parent handoff, refuses a pre-existing SELF_RUN and exclusively creates run-1 at self-check entry. Parent start/stdio do not require that leaf beforehand. |
| S ↔ H leaf protocol | **PASS:** SELF_RUN remains SELF_ROOT/run-1; S invocation/pending and normal-completion/error checkpoints use its existing invocation file. S helper authorization, start readers, stdio and root/child marker readers all derive from SELF_RUN. H 161–225 consumes matching auth files and writes markers under EVIDENCE; the fixed child command uses the same H constant. No extra path consumer/selector was introduced. |
| Collision/old-root refusal | **PASS for current observations and retained protocol:** retry-3 is absent; direct forced listing of `.codex` found no case-insensitive same-name file/directory. Existing C:\, C:\vibe, workspace and .codex were observed at their canonical full paths as directories with no ReparsePoint attribute. Occupied parent (even empty), stale descendants, unowned pending, wrong fixed destination and unsafe/reparse ancestry remain refusal cases, not adoption/cleanup. The coordinator must repeat required absence/alias/ancestor checks before any later call; these observations do not exclude concurrent changes. |
| No root reuse or widening | **PASS:** zero active retry-2 strings remain in W/S/H. Original/retry-1/retry-2 roots remain historical consumed evidence, not fallback destinations. Build/runtime-preflight roots, run-1 name, schema/mode/command/environment/category, dependencies and user-selectable options are unchanged. No automatic root search, numbering or second retry-3 slot exists. |
| Accepted behavior retained | **PASS by exact inverse boundary and inspected derivations:** unsigned CreateFile masks, caller/handoff guards/persistence, retained normal interpreter identity/handle/actual exit-7 observations, strict complete zero/empty/zero normal gate, guarded secondary reporting, later tree probe/Jobs/cleanup and original 10-second inherited deadline remain byte-identical to accepted baselines. No forced cleanup-to-normal-PASS, count subtraction, timeout reset or extra runtime budget. |

## Every prior evidence binding verified

All 15 files presently in original/retry-1/retry-2 were independently rehashed; every value matches the accepted plan:

| Evidence (relative to its `.codex/` root) | SHA-256 |
| --- | --- |
| Original caller | `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e` |
| Original caller `.update` | `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75` |
| Retry-1 caller | `f992b356191d202a5e2357cffb1d64d90b4dd7f8ac54cd0b76ab2e0d7540dcf3` |
| Retry-1 PREPARED handoff | `b73738fc81644b942ea4f84890146e1bdfc73d925005552cb34db1af05aadc79` |
| Retry-2 caller | `4dbb3ff5f821edefe0a9d5fa1c822ef7cb0d296f346853013d620a3abaf5f00e` |
| Retry-2 consumed handoff | `bb773f7991eaa34c9f87ede7df8dd48d4eea899fbbd711eea009e3f7631abb0c` |
| Retry-2 supervisor-start | `8ecc5f87c87c90b3f1b73e9bf07814b7b6409a308971a6c83751be09c4f058d5` |
| Retry-2 supervisor.stderr.log | `92875c22d9084e2f791f53e02c09bc03d6b2bd16f28655fcffa3be5380c3ba51` |
| Retry-2 run-1/invocation.json | `7b40f2f6f218e491034c6f621108faedf6d0137557379f80fa0802c2313ab592` |
| Retry-2 consumed nonzero authorization | `e448045f4930ff8ab2c47341daeabb63bd0cef8008f5265b1d344167d53548f8` |
| Retry-2 nonzero-helper.json | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| Retry-2 nonzero-script-start.json | `767458b7ce651898f16c7bec8c2d3370eeaaff4d1d1802663edf3b77b7b86d24` |
| Retry-2 supervisor.stdout.log, nonzero.stdout.log, nonzero.stderr.log (three empty files) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Protected candidate/shared-helper/builder/test/fixture/configuration files were independently rehashed and match accepted full digests, respectively: `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b`, `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880`, `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b`, `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8`, `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea`, `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228`. Historical results and counters were not changed; retry-2 remains non-PASS.

## Boundary

Only static reads/searches, file hashing, ancestor/directory/absence inspection and in-memory byte/string hash comparison occurred, plus writing this report. No source, metadata, evidence or manifest was edited; no root/record was created. No tests/imports, linters/parsers/compilers, probes/process inspection, wrapper/self-check/preflight/runtime/collection, manifest preparation, GIS/numerical/build or browser work ran. Luna-reported static gates were not rerun. Actual 10-second completion/reaping/containment/persistence and **30-second runtime-profile fit remain unmeasured**; no runtime evidence is created.

Return static PASS to the coordinator. Dispositions 75/76 still require a **separate coordinator execution gate** before exactly one retry-3 call; this report does not authorize or execute it or any later phase. Candidate remains **NO-GO and unservable**; build 3 remains **unreserved**, with geographic/source/origin/domain/recipe/collision/numerical limits unchanged.
