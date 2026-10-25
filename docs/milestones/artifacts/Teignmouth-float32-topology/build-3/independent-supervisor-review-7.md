# Independent supervisor review 7 — Luna cycle 3

2026-10-25. Independent non-implementing Sol reviewer `/root/sol_review_face_diag`. Authority: coordinator disposition 50 and the review dispatch, under disposition 49. **FIX_REQUIRED.** Cycle 3 has been independently reviewed. Six review-6 findings are resolved in the inspected static logic; the native-source classification/refusal finding remains partially unresolved.

Reviewed actual current W/S/P source and call ordering against review 6, `supervisor-correction-3-diagnosis-2.md` (SHA-256 `a718dfae49b9915d66ff2c5e0d49bfbc32f5ac14722ae80d6a37571352370b05`), the accepted finite-profile addendum and disposition 49. This review applies the user-selected finite trusted startup/import profile, trusting pinned CPython/OS-loader behavior and reviewed frozen code. Active archive imports are now unsupported; passive archives remain ordinary data. No universal confinement or atomic load-confinement claim is imposed. Existing untracked/modified workspace files do not supply a reliable Git index baseline; no index diff is claimed.

## Independently verified hashes

All submitted and protected SHA-256 values match disposition 50:

| File relative to repository root | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `01c14c589359367e67e92f44699e8868af4deddd5eff2c499c4d3b3df7da2bf3` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `919066815bf6cafb5ff207cd8326271899d75c6fa134630d3812a2c009313887` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `9fc73a8ed7aca3b4e223d3f23a7bd676f48011aa0abe98eb864f9e98a5191d20` |
| Candidate `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| Shared helper `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| Builder `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| Test `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| Fixture `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| Configuration `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |

H and all protected files remain byte-identical. No candidate/provenance/test/configuration/numerical correction follows this operational submission.

## Remaining concrete blocker

**FIX_REQUIRED — classify native images by contents before suffix exemptions, and apply native refusal rules to that classification.**

W **409** skips `.zip`, `.egg` and `.whl` files before its MZ-header inspection at **411–414** whenever `AllFiles` is false. S **1394–1397** does likewise, and its expected-set reconciliation **1466–1467** repeats the skip. Thus an *unlisted* file named `renamed.zip` containing an MZ/PE image in the fixed CWD, a PATH directory or a Python root outside the all-files data trees can be omitted without either validator checking its binding. W's expected-set loop iterates only supplied bindings, so it cannot recover that unlisted candidate; S excludes the archive suffix from both sets. The validators can reach their successful set reconciliation despite that omitted native candidate. This is a static reachable refusal case, not a claim that such a file currently exists or was loaded.

The archive-refusal amendment permits passive **archive data**; it does not exempt executable images that merely have archive-like names. The still-accepted finite profile explicitly includes every PE/MZ candidate, including renamed/extensionless files. This is a false-completeness branch within that finite claim, rather than a demand to analyze arbitrary trusted-code behavior.

The same native classification must govern redirection checks. W **423–428** and S **1411–1412** run adjacent-sidecar refusal only for known native suffixes. A PE discovered through MZ contents under a Python/data tree with a different suffix therefore lacks that adjacent-sidecar check. For example, a PE `module.bin` beneath a Python root outside the data/native-root passes, accompanied by an unlisted `module.bin.local` directory, is bound as a candidate but does not receive the required native sidecar refusal. W **400–407/442** and S **1370–1393/1416–1417** do not mark that Python traversal loader-relevant. Merely binding the image does not establish or refuse its external redirection source. Existing direct-native/package-native redirection scans fix the original `.local` directory case in those roles, but do not close this content-classified native-image case.

Use one consistent candidate classification in discovery and expected-set reconciliation: inspect the header before deciding a file is passive archive data; treat every content-identified native image as native for binding and applicable adjacent-sidecar refusal, regardless of suffix. Preserve the existing role-specific treatment of unrelated data configuration files and all original deadlines/root/refusal rules. Neither runtime execution nor a broader loader model is needed to identify this bounded correction.

## Review-6 finding disposition

| Review-6 finding | Static result and current evidence |
| --- | --- |
| 1. Tagged customizations | **PASS:** W 398–406 and S 1313–1317/1366–1389 refuse names equal to or beginning with customization-name-plus-dot, including tagged extensions/cache forms and child directories before descent suppression. P retains post-startup detection. |
| 2. Case-distinct identities/references | **PASS for the inspected correction:** W exact-spelling maps 376–391/417–421, folded-reference checks 534–625 and reconciliation 478–480 replace silent merging; S registers directory spellings and retains exact candidate comparisons (1288–1327). P adds exact actual-sys.path comparison (818–825) and reference ambiguity checks. Identical overlapping scans deduplicate; distinct spelling is refused. |
| 3. Native redirection | **FIX_REQUIRED, partially corrected:** role-specific file/directory `.local/.manifest/.config` refusal and suffix-native adjacent checks are present (W 400–428; S 1329–1412). Content-classified native images and archive-suffix bypass remain as detailed above. |
| 4. `.pth` semantics | **PASS:** W 678–686, S 1153–1160 and P 775–782 consistently ignore blank/column-zero comments, refuse leading whitespace and executable import lines, and remove trailing whitespace only. Existing ASCII/root/directory/binding checks remain. |
| 5. Unique pyvenv policy | **PASS:** W's shared in-file `Get-PyvenvPolicy` 799–835 is used by home/policy consumers, rejects duplicate/unsupported/malformed keys, requires explicit pinned policy and rechecks hashes. S 916–949 and P 73–108 mirror duplicate detection and required policy. |
| 6. Archive import handling | **PASS under disposition 49's amendment:** W 345–372 and S 1103–1127 refuse active archives/present stdlib zip; P 740–761 requires directory entries and absent optional stdlib zip. P 970–1014 explicitly records/refuses archive-backed modules/caches, rather than hiding them as absent ordinary files. Default unused zip hook and absent optional zip path remain permitted. Passive-data classification must still satisfy the native blocker above. |
| 7. W counters/progress | **PASS:** shared mutable `scanState` 378/392/432–435 replaces scalar child-scope counters; the finally publication 447–451 and result 485–489 use the same aggregates. Unique successfully bound files/bytes are counted once; directory visits accumulate across scans, and failures retain partial totals. |

## Retained gates and proof limits

The accepted P RECORD normalization, optional hint, independent all-file package/native/data traversal, ancestor checks and honest error/completion predicates remain (P 1136 onward, 1305, 1362 onward, 1496 onward). No runtime-complete inventory is claimed.

W still validates referenced frozen controls/files and profile before reserved-build/standalone-verify launch. S repeats profile/closure checks before P and after confirmed termination; P validates closure/profile before explicit third-party/repository imports and retains strict loaded census and post-binding checks (P 1565–1592, 1711 onward). Collection remains observational/null-match/exit 2 and `frozenProfileVerified=False` (P 1649–1682); verification remains identity-only. Reserved build still requires its snapshot/reservation and repeated pre-numerical gates. No standalone builder or GIS execution path was added.

Inspected process paths retain authenticated one-use QPC handoff (S 509 onward), fixed launcher/base interpreter identities, suspended assignment before resume (W 1088–1118; S 1804–1833), direct cleanup of an unassigned created launcher (S 1839–1868; W 1217–1235), nested kill-on-close Jobs, bounded remaining-time waits (S 2019–2117), observed exits/termination predicates, fixed safe archival and unavailable-memory semantics. Self-check remains 10 seconds; standalone remains 30 seconds from W start; builds retain 180 seconds total/150 numerical cutoff. This is static contract evidence, not measured Windows containment or timing proof.

The four build-3 manifest/identity/snapshot files, run/invocation, both operational run leaves and candidate output remain absent. Missing preparation safely fails closed; it is not PASS, permission to prepare manifests or authority to add records/schemas/phases. Disposition 50 records operational cycles 3/4 used and none reserved; historical candidate counters remain unchanged and no candidate build is reserved.

**30-second runtime fit is unmeasured. No runtime evidence is created by this review.** Enumeration/hash/pre/post work may expire and must remain non-PASS. Native/OS calls are not proven preemptible; concurrent replacement is outside the selected atomicity claim. No measured exits, memory, GIS, numerical results or browser observations are inferred.

Work consisted only of static document/source/config/metadata reads, searches, directory checks and SHA-256 hashing, plus writing this report. No source, ledger, checkpoint, manifest or protected file was edited. No tests, imports, linters, parsers/compilers, scripts/wrapper, self-check/preflight/runtime, diagnostic/GIS/numerical/candidate build, manifest preparation or browser action ran. Implementer-reported static PASS results in disposition 50 were read, not rerun.

The safest bounded next action is one focused Sol diagnosis of the single native-classification/refusal inconsistency above, tracing renamed PE versus genuine passive archive and adjacent-sidecar cases through W/S discovery and reconciliation. Keep it within W/S/P, preserve the accepted inventory and all existing limits; no executable probe, new manifest, changed trust boundary or candidate correction is needed. The coordinator must decide any cycle-4 release under the existing allowance. This review authorizes no implementation or runtime phase. Candidate remains **NO-GO and unservable**; build 3 remains **unreserved**.
