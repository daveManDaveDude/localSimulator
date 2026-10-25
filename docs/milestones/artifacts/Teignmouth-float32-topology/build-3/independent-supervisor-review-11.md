# Independent supervisor review 11 — caller owner predicate

2026-10-25. Independent non-implementing Sol reviewer `/root/sol_review_face_diag`, under disposition 62. **PASS — static acceptance of the narrow caller-owner correction.** Review 10's concrete finding is closed. This report authorizes no self-check or other subsequent action.

Inspected actual current W against review 10 and disposition 62. W **198–203** now requires both proposed and persisted Caller records to carry the literal `teignmouth-build3-caller-record-v2` schema and match the current wrapper PID, QPC start and selected mode. Proposed mode uses an exact case-sensitive comparison. The dispatcher calls this validator both **before exclusive pending creation** (**136**, creation at **140**) and **before replacement** (**170**, move at **176**). A changed proposed PID/start/mode can no longer pass merely because the existing file belongs to the current invocation. Legitimate evolving telemetry/status fields remain unrestricted by these ownership predicates.

Exact canonical caller-path/owned-parent/existing-file/no-reparse checks at **189–196** remain. Caller/handoff/unknown-kind dispatch at **181–186** is unchanged in meaning; no arbitrary path, consumed record or fallback can acquire replacement authority.

The accepted review-10 handoff findings remain intact: exact current-mode destination, exclusive PREPARED ownership, immutable snapshot and captured prepared digest, exact keys/typed values and trusted-W identity checks (**274–302**); only the five launcher-binding fields may change, tied to the verified created/suspended/unassigned/unresumed launcher (**303–324**). The handoff call explicitly selects Handoff (**1474**), checks the original deadline and precedes Job assignment (**1484**) and resume (**1497**). Pending exclusivity, flush/close, both ownership validations and supported same-directory File.Move overwrite remain at **130–178**. Structured sticky failures, direct unassigned-launcher cleanup, final caller fallback and original one-use/process/identity/Job/deadline gates remain as accepted in review 10. No crash-atomicity, power-loss durability or atomic hostile-replacement protection is claimed.

## Independently calculated SHA-256 values

| File relative to repository root | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `c8fcd7c3d4ae8b1535f930533c838bd7e1818624c83798961b388f90660ccb74` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `17a7a347b175bfa3ad1a1dcbdc4167d3d4b1c8a73da0dc09d537ec1c6d4a8ef6` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `3419551b5c19e69c2487bb57c1bc49c102d4b7bfe1db1f93aea60cf038ebe05a` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| Candidate `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| Shared helper `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| Builder `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| Focused test `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| Fixture `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| Configuration `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |
| Original failed `.codex/build3-supervisor-selfcheck/caller-invocation.json` | `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e` |
| Original failed `.codex/build3-supervisor-selfcheck/caller-invocation.json.update` | `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75` |

S/H/P, protected candidate/helper/builder/test/fixture/configuration and original failed evidence match review 10 byte-for-byte. The exact `.codex/build3-supervisor-selfcheck-retry-1/` root remains absent; therefore its descendants are absent. W-only scope is consistent with these independently verified bindings and inspected current source. Untracked operational files provide no reliable Git baseline; no exhaustive unrelated-workspace preservation proof is claimed.

Review used only static document/source reads and file hashing/absence inspection, plus writing this report. No implementation/ledger/checkpoint/manifest/original evidence was edited. No parsers, linters, compilers, tests, imports, wrapper/runtime/preflight/self-check/collection, manifest preparation, GIS/numerical/build or browser action ran. Implementation static checks were not rerun. **30-second fit remains unmeasured**, and no runtime/persistence/containment/exit/timing evidence is created.

No actionable residual finding was identified within this narrow correction. Return PASS to the coordinator for its gate decision under disposition 62; this review neither authorizes nor executes the conditional self-check. Historical counters and source/origin/domain/recipe/collision/numerical constraints remain unchanged. Candidate remains **NO-GO and unservable**; build 3 remains **unreserved**.
