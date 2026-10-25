# Independent supervisor review 20 — retry-4 path binding

2026-10-25. Independent Sol reviewer `/root/sol_review_face_diag`. **PASS for the four-literal retry-4 path binding only.** Reviewed actual W/S/H/P against dispositions 86–87, accepted `retry-4-path-binding-plan.md` (independently verified SHA-256 `249ebefbca3a6ffa4a65245e5c543ad12aab506876b7e4be910883a8d2a6e74b`) and accepted review 19. No self-check or other operation is authorized by this report.

## Exact byte proof

Independently recalculated current file hashes, counted the new/old root literals, and reversed only the new root strings in memory. No reconstructed file was written or executed.

| File | Current SHA-256 | New/old occurrences | Inverse SHA-256 |
| --- | --- | --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b` | 2 / 0 | `c3f1f49cb574793c1cdbc2d905fd3d36f646b6f32ffb7c200a96c9792d5ce84f` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `64bf2c4abf822ad55252789315d71731d2660d66bb5b6bc7d60f810f2de492c7` | 1 / 0 | `886280c5c5aeaf519929a5b6b1fa3c78c72a9f7a6874fbd8c4d60f09abdbb7e6` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501` | 1 / 0 | `cf1145b33397066559b89c11aa1cb0ebcf4d6d4d470f6521d96fe9e1f4ecccab` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` | 0 / 0 | Unchanged |

All three inverse hashes equal the exact accepted baselines. This proves exactly the two W literals (lines 23 and 344), S `SELF_ROOT` (39) and H `EVIDENCE` (17) changed, with no other byte/encoding/newline change. A search of executable scripts, tests and configuration found only those four active retry-root consumers and no remaining active retry-3 literal. Operational files remain untracked; no reliable Git index diff is claimed. The historical unsaved/untraceable `957157…` S digest remains unresolved; this inverse supplies no missing history.

## Cross-file and safety criteria

| Criterion | Static finding |
| --- | --- |
| Fixed parent, leaf and fallback | **PASS.** W 21–49 derives retry-4 parent caller/update, separate failure fallback, handoff/update/consumed/start and supervisor logs. W 344–356 independently restricts terminal fallback to that same exact retry-4 parent and failure filename, with exclusive write and sticky chosen exit 2. S 39–40 and H 17 agree on the parent and `run-1` leaf. No old-root fallback, alternate slot, run-2 or arbitrary path was added. |
| Parent-before-leaf and repeat refusal | **PASS.** W 1203–1225 checks canonical/non-reparse ancestors, refuses even an already-existing empty retry parent, checks fixed descendants, creates parent without adoption, and retains one-use record checks. S 570–591 consumes the same parent-level handoff and uses the matching parent-level startup marker; 647–651 refuses a pre-existing leaf before supervisor-owned creation. S 3465–3475 exclusively creates only its matching `run-1` and refuses candidate build/evidence output. Existing exclusive creation and owned updates remain necessary against races. |
| Caller/Handoff ownership | **PASS.** W 181–205 retains disjoint record kinds and exact proposed/persisted Caller schema/PID/start/mode binding; 274 onward retains exact selected-mode Handoff path, exclusive PREPARED ownership, immutable identity/hash/nonce, and verified suspended-launcher transition. Both derive from the changed fixed parent. Same-owned-destination/pending validation and same-directory File.Move semantics remain byte-identical. Neither old caller nor handoff can authenticate the new slot. No atomicity/durability claim is added. |
| S ↔ H helper paths | **PASS.** S 524–527 derives matching nonzero/tree startup markers. S 3585–3592 writes helper authorization in `SELF_RUN`; H 161–202 consumes the identical authorization/consumed paths and writes its startup marker there. S nonzero stdio (3622–3623), tree stdio (3883–3884), root/child markers (3916–3917), and H marker writer (224–225) all use the same leaf. Existing native launcher/interpreter/creation/nonce/QPC authority is unchanged. |
| Path observation at review | **PASS, point in time.** `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-4` is absent. Force enumeration of `.codex` found zero case-insensitive name collisions. `C:\`, `C:\vibe`, workspace and `.codex` are directories without ReparsePoint, and Resolve-Path returned their exact expected spellings. No inaccessible/ambiguous observation was treated as absence. The fixed canonical child is within the inspected workspace; no root or descendant was created. These observations do not guarantee against future concurrent changes and must be repeated at the separately authorized invocation gate. |
| Accepted diagnostics and original gates | **PASS by exact inverse plus inspected consumers.** S restores the full review-19 bytes, preserving the direct one-attempt CloseHandle before optional telemetry, three comparable file-metadata endpoints, provisional digest promotion, changed/unverified/late partial behavior and all endpoint/atomicity/mapped-image limits. Original census/unexpected-ID rejection, same-handle observations, reporting isolation, nonzero exit/reaping/zero-empty-zero proof, later tree gate, Jobs, process identities, cleanup and 10-second absolute self-check deadline are unchanged. Build/runtime gates and their 180/150/30-second bounds are unchanged. |

## Preservation and limits

Rehashed all six protected files; all match accepted bindings:

| Protected file | SHA-256 |
| --- | --- |
| `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |

Enumerated and rehashed every existing file under the original and retry-1/2/3 evidence roots: **2 + 2 + 11 + 11 = 26 files**. Every hash matches the complete accepted preservation matrices used in review 19, including pending/consumed records, markers, stdout/stderr and empty logs. Original caller/pending remain `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e` / `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75`; retry-3 caller/invocation remain `f1bf3a880a821626daef625f60459d037a8aa9509246e401a06f9440cb8134d6` / `dcf98d8471df615acbaa74d3eece7f8a774e86cac22b0864931e556f2ae627e5`. All old roots remain immutable, consumed and non-PASS. No evidence was edited, promoted, copied into retry-4, deleted or reused.

Disposition 87 reports two preliminary Luna command errors (AST quoting and evidence/hash command from the wrong working directory), subsequently corrected, plus a coordinator preliminary Get-FileHash argument error corrected with explicit paths. Those are retained as reported command history, not rerun or erased by this review. Implementation-reported Ruff check/format and PowerShell AST results were not rerun. Static inverse/path PASS does not establish native behavior, persistence, diagnostic coverage, actual 10-second fit or **30-second runtime-profile fit, which remains unmeasured**. No runtime evidence was created.

Review work was limited to static reads/searches, hashing, in-memory inverse comparison, existing directory/alias/ancestor inspection and this new report. No source/ledger/checkpoint/manifest/prior evidence edit, root creation, tests/imports/probes/process inspection, parser/compiler/linter, wrapper/self-check/preflight/runtime/collection, manifest preparation, GIS/numerical/build or browser operation occurred.

No residual static path-binding blocker was found. The historical outer command exit **1** versus recorded internal exit **2**, unidentified historical PID 20712 and missing `957157…` provenance remain unresolved. PASS grants **no self-check authorization** and no other operation. A separate coordinator gate is required before any single retry-4 invocation. Candidate remains **NO-GO and unservable**, build 3 **unreserved**; source/origin/domain/recipe/collision/numerical/geographic limits, pending AOI status and historical counters remain unchanged.
