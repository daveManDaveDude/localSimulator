# Independent supervisor review 8 — Luna operational cycle 4

2026-10-25. Independent non-implementing Sol reviewer `/root/sol_review_face_diag`. Authority: disposition 53 and the review dispatch, under disposition 52. **PASS — static acceptance of the cycle-4 correction.** Review-7's remaining native classification/refusal blocker is resolved in the inspected current W/S logic. No actionable residual correction finding was identified within this review's scope.

Inspected current W/S source and call paths against review 7, diagnosis 3 (SHA-256 `0051daa983c4a9e251bad68979da19bc5c14d0095522133b779f054246a9d691`) and disposition 52. The accepted claim remains a finite trusted startup/import profile, trusting pinned CPython/OS-loader behavior and reviewed frozen code, binding profile candidates and refusing unsupported configurations. Active Python archive sources remain unsupported. This is neither universal confinement nor atomic protection against concurrent replacement.

## Exact independently verified hashes

All values match disposition 53:

| File relative to repository root | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `c707ebbda14c562083fb2485854b4d4d515bc809987d13136479f7cd5d597b06` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `73345c89e9ec49c4c092a00a93b47c4642b32f7deecd7108c018b04910c3717c` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `9fc73a8ed7aca3b4e223d3f23a7bd676f48011aa0abe98eb864f9e98a5191d20` |
| Candidate `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| Shared helper `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| Builder `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| Focused test `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| Fixture `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| Configuration `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |

P is byte-identical to cycle 3; H and all protected candidate/helper/builder/test/fixture/configuration files match their accepted bindings. This supports the reported W/S-only correction scope. The operational files are untracked in the existing workspace, so there is no reliable Git index baseline or complete historical diff. No such diff, or proof that every unrelated workspace file is unchanged, is claimed. Current source inspection plus exact unchanged protected hashes are the available scope evidence.

## Static acceptance matrix

Line references identify the exact current W/S hashes above.

| Requirement | Result and evidence |
| --- | --- |
| One shared local classifier for discovery/reconciliation | **PASS:** W `classifyFile` 382–407 is called by discovery 448 and expected-set reconstruction 515; S `classify_profile_file` 1348–1385 is called at 1436–1441 and 1510–1515. No helper import or new file is used. |
| MZ overrides archive/Python/data suffix shortcuts | **PASS:** both classifiers inspect the first two bytes before computing independent native/passive-archive/candidate booleans (W 387–406; S 1357–1384). MZ `.zip/.egg/.whl`, `.py`, renamed and extensionless files are native candidates regardless of all-file membership. No early archive skip remains in these discovery/reconciliation paths. An unlisted such image reaches the mandatory binding check. |
| Genuine passive archive | **PASS:** non-MZ archive suffixes are passive, not promoted to executable candidates solely by suffix; all-file/data roles still bind them as ordinary files. This does not enable archive imports. Existing active PYTHONPATH/present stdlib archive refusal and unchanged P's actual/archive-backed module/cache refusals remain. |
| Native sidecars before deduplication | **PASS:** W 408–421 checks appended/replaced `.local/.manifest/.config` alternatives for files or directories, and discovery invokes it at 451 before visited-map return 454–456. S 1332–1346 performs explicit lstat observations and discovery invokes it at 1448–1449 before `inspect` can deduplicate. Every content-identified native file receives the check, independent of suffix. Reconciliation repeats it (W 518; S 1519–1520). Permission/query errors propagate; only explicit not-found cases become absence. |
| Overlapping-root role union / scan ordering | **PASS:** discovery repeats each applicable Python/native/package-native/data traversal (W 470–473; S 1460–1484). Candidate promotion is effectively the union of those roles; sidecar/loader policy checks precede hash/count deduplication on every encounter, so an earlier Python/data visit cannot suppress a later loader role. Reconciliation independently computes the union, including recursive package-native membership (W 490–518; S 1502–1520). Matching unique sets are required. |
| Config-role treatment | **PASS:** loader-relevant file/directory redirection refusals remain separate from executable classification (W 441–451/517; S 1420–1449/1516–1520). Ordinary unrelated data config is bound under its all-file role, not promoted by a general config suffix predicate. If its contents identify a native image, native policy applies. |
| Short/unreadable/unstable/late observations | **PASS, static logic:** header reads are bounded to two bytes with guaranteed close, metadata comparison and inherited-deadline checks (W 384–401; S 1355–1376). Empty/one-byte ordinary files classify non-MZ; suffix-native policy still applies independently. Open/read/stat errors or observed metadata changes cannot become passive success. Sidecar checks and final completion also check the same deadline. No execution of any case is claimed. |
| Exact bindings/collisions and set equality | **PASS:** current exact-spelling/Windows-folded reference and directory/candidate collision checks remain. Candidate binding/hash work follows classification; reconciliation uses the same classifier and demands discovered/expected identity sets agree (W 515–526; S 1510–1527). Bound data cannot substitute for a missing native candidate binding. |
| Truthful counters and partial progress | **PASS:** shared W scanState counts only unique successfully bound candidate files/bytes after verification (458–464), with finally publication across failures/expiry (475–479) and final result from the same object (527–532). Repeated header/sidecar checks do not inflate successfully hashed unique bytes. S's candidate count/bytes remain associated with unique verified `inspect` work. |
| Earlier accepted fixes | **PASS retained:** tagged customization refusal, exact-case identity checks, restricted matching `.pth` grammar, duplicate-detecting pinned pyvenv policy, archive-import refusal and unchanged P inventory/census logic remain. P's cycle-3 hash is unchanged, so its accepted RECORD normalization, independent package/native/data inventory and honest error/completeness behavior are preserved. |

## Retained supervision and build gates

Current source retains original W QPC start/deadline, authenticated one-use handoffs and exact launcher/base interpreter ancestry/image/hash/PID/creation identities. Suspended creation, outer Job assignment/membership before resume remain at W 1131–1161; S's inner launch remains suspended and assign-before-resume at 1847–1875. Unassigned-process cleanup, single handle ownership, kill-on-close containment, bounded remaining-time waits, confirmed termination and native exit capture remain separate conjunctive gates. W's caller records still capture actual launcher/script exits and termination state rather than inferring them.

S retains self-check 10 seconds, standalone 30 seconds, build 180 seconds total and 150-second numerical cutoff (43–46), bounded wait/termination paths (2062 onward, 2144 onward), safe fixed output archival, truthful unavailable-memory fields and post-stop preservation. No cap, retry slot, clock reset or command/environment change was introduced by the inspected correction.

W still verifies the frozen reference closure/profile before reserved-build or standalone-verify launch. S repeats profile/closure checks before P and after termination; unchanged P retains pre-import binding/profile checks, strict loaded census and postchecks. Collection stays observational with null identity match/exit 2; verification stays identity-only. Reserved build continues to require exact ledger/snapshot equality and the single ordinal-3 reservation (S 1748–1784), then repeats closure/reservation gates before numerical dispatch. This report reserves no build and does not satisfy these preparation/runtime gates.

## Limitations and disposition

**30-second runtime fit remains unmeasured.** Full enumeration, header/hash/refusal work, P execution, pre/post checks and termination evidence must fit W's original deadline; expiry/incomplete observation must remain non-PASS. Static review does not measure native API preemption, actual nested Job/launcher behavior, exit timing, working set, filesystem races or candidate geometry. The finite trust claim excludes malicious trusted code/compromised OS and atomic replacement protection; it has not expanded.

Luna's Ruff check/format, PowerShell AST and embedded C# declaration compilation PASS results are **reported in disposition 53, not rerun by this reviewer**. No runtime evidence is created. Review consisted only of static reads/searches, directory/absence checks and SHA-256 hashing, plus writing this report. No tests, imports, linters, parsers/compilers, script/wrapper invocation, self-check/preflight/runtime, manifest preparation, diagnostic, GIS/numerical/candidate build, browser or serving action occurred. No source, ledger, checkpoint, manifest or protected file was edited.

The four named build-3 input/external/runtime/snapshot files, run/invocation, both operational run leaves and candidate output remain absent. Their absence safely blocks unprepared verification/build; it does not constitute successful preparation or runtime proof. Absence corroborates the recorded state but is not proof of all historical non-execution.

All four operational Luna cycles have now been independently reviewed; no residual actionable finding from review 7 remains, so an operational Sol correction is not needed for this static correction acceptance. Historical candidate counters and all source/origin/domain/recipe/collision guards/numerical limits remain protected. Return this PASS to the coordinator for its separate gate decision. **No runtime, manifest preparation or candidate build is authorized by this review. Candidate remains NO-GO and unservable; build 3 remains unreserved.**
