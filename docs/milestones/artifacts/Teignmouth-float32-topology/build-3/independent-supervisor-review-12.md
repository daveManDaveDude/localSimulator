# Independent supervisor review 12 — CreateFile access literal types

2026-10-25. Independent non-implementing Sol reviewer `/root/sol_review_face_diag`, under disposition 64. **PASS — static acceptance of the exact three-literal W correction.** No actionable residual finding was identified in this scope. This review authorizes no self-check or other execution.

Read dispositions 63/64, the actual disposition-63 failed caller/handoff evidence, current W and accepted `createfile-access-type-plan.md`; independently verified plan SHA-256 `b88a6f9dd036a940fd939b3738f2168d04121661439483e845712f9081a65ec6`.

## Exact change and static proof

Current W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` SHA-256 is **`98be856a85894bb7fec5e8863ba15023ff16d545e567e2dd0bd0c2b45df68d5e`**.

The three actual calls at W **1437–1439** now use `0x80000000u` for NUL input and `0x40000000u` for stdout/stderr. The unsigned spelling retains the requested read/write bit patterns while avoiding the signed high-bit Int32 value recorded in the failure. The C# declaration at **1274** still uses `uint access`. Destinations, share/security/inheritance, creation dispositions, flags and handle ownership remain unchanged. The positive OpenProcess masks were not altered.

To establish the entire byte delta without relying on untracked Git files, review performed an **in-memory text-only reversal** of those three suffixes and hashed the reconstructed UTF-8 bytes, without writing or executing the reconstructed source. Exactly three corrected mask occurrences were found. The reconstructed SHA-256 is **`c8fcd7c3d4ae8b1535f930533c838bd7e1818624c83798961b388f90660ccb74`**, exactly the accepted review-11/disposition-63 W baseline. Thus the current W differs from that baseline only by the three intended `u` suffixes, including unchanged line endings/other source bytes. No runtime literal-evaluation or interop probe was performed.

This also preserves the accepted caller/handoff ownership validators, exclusive pending/replacement/fallback behavior, exact fixed paths, immutable PREPARED identity and five-field launcher transition, sticky errors/direct cleanup, nonce/native identities, suspended Job assignment before resume, all deadlines and all other W semantics. No API declaration/access-rights expansion or unrelated cleanup is present.

## Independently verified preservation hashes

| File relative to repository root | SHA-256 |
| --- | --- |
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
| Consumed retry-1 `caller-invocation.json` | `f992b356191d202a5e2357cffb1d64d90b4dd7f8ac54cd0b76ab2e0d7540dcf3` |
| Consumed retry-1 `self-check-handoff.json` | `b73738fc81644b942ea4f84890146e1bdfc73d925005552cb34db1af05aadc79` |

All match their accepted bindings. The retry-1 directory still contains the two preserved JSON records. Its caller reports the original argument-conversion exception, exit 2, false launcher-created/assigned/resumed/native-launch/candidate-build fields and null child exits. This review neither changes that failure nor infers a Windows access-denial/containment/GIS result from it.

Review used static document/source/evidence reads, searches, directory inspection, file hashing and the in-memory source-byte comparison above, plus writing this report. No source/evidence/ledger/checkpoint/manifest was edited. No parsers, linters, compilers, tests, imports, wrapper/self-check/preflight/runtime/collection, manifest preparation, GIS/numerical/build or browser action ran. Implementation-reported static checks were not rerun. Static PASS does not demonstrate a successful native call, persistence, containment or self-check; **30-second runtime fit remains unmeasured**.

**Retry-1 is consumed and must not be reused.** The accepted numeric correction leaves its fixed one-shot refusal intact. A separate exact fresh-root plan and independent review are required before any later wrapper invocation; this report does not authorize or execute that invocation. Historical evidence/counters and candidate source/origin/domain/recipe/collision/numerical constraints remain unchanged. Candidate remains **NO-GO and unservable**; build 3 remains **unreserved**.
