# Correction 3 — bounded native-classification diagnosis after cycle 3

2026-10-25. Non-implementing Sol 6.1 medium `/root/sol_review17_plan`. Authority: disposition 51; one focused static diagnosis, maximum 120 seconds. Read review 7 and current W/S/P; no correction or execution is performed.

**A bounded Luna cycle-4 correction is feasible within W/S, with P unchanged.** The defect is classification/order consistency, not a new loader model or trust-boundary question. Return this scope to the coordinator for a separate cycle-4 release; this report neither authorizes nor reserves that cycle. Candidate remains NO-GO/unservable, build 3 unreserved, no runtime/build authorized.

## Exact baseline

The following source hashes were recalculated statically and match review 7:

| Source | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `01c14c589359367e67e92f44699e8868af4deddd5eff2c499c4d3b3df7da2bf3` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `919066815bf6cafb5ff207cd8326271899d75c6fa134630d3812a2c009313887` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| Disposition 51 | `f42c042d16ca0314da0424f9a3409e1b31fbdd3338258ac73d7a50bcce06135e` |

Review 7's recorded SHA-256 is `dbde8f8a79bc55bbaef6bb655225a1beb1339620f5c11490aa839688ce5fe88c`. It accepts the other six cycle-3 findings and P's independent inventory fix. Preserve that acceptance and its exact protected-source bindings; do not reopen those changes.

## Diagnosis

W 409 and S 1394–1397 skip archive suffixes before examining content. W 410–414 and S 1398–1405 also avoid the header when `AllFiles` or a Python suffix already makes the file a candidate. Consequently candidate status and native status are conflated: a file may be inventoried as data/Python without becoming native for sidecar checks. W 423–428 and S 1411–1412 check adjacent redirection only for known native suffixes. S 1466–1475 repeats the archive exemption in reconciliation; W 470–474 has another independent candidate predicate, including a broader config rule than discovery.

An MZ-marked `renamed.zip`, `module.bin` or even a Python-suffixed file must be classified as a native candidate independently of its filename and its existing all-file/data membership. A genuine ordinary archive is not automatically native. Active Python archive import refusal is a different policy and stays unchanged.

## Smallest coherent correction

1. Add one small in-file regular-file classifier in W and one equivalent in S; no shared helper file/import, dependency or PE parser. Both discovery and expected-set reconciliation **call that same local classifier**, instead of duplicating suffix predicates. Pass the effective scan roles explicitly: Python-source membership, all-file/data membership, and loader-relevant membership. Roles must be their union across overlapping roots: recursive Python/data/package-native membership and direct fixed/PATH native-directory membership. Do not let the first encountered role erase a later native role.
2. After existing canonical-path/type/reparse checks, read the first two bytes of **every inspected regular file** before any archive-suffix exemption or candidate short circuit. Use a bounded stream read with guaranteed close and deadline checks before/after open/read. Empty/one-byte files yield `hasMZ=False`, not an error; unreadability/unstable observation/expiry is a non-PASS error, never passive classification. Existing hash-time stability/preservation checks remain. A full PE parse is unnecessary: the accepted profile conservatively calls MZ-marked files executable candidates, even if their later PE structure would be invalid.
3. Derive independent booleans: `isNative = knownNativeSuffix OR hasMZ`; `isPassiveArchive = archiveSuffix AND NOT isNative`; `isCandidate = allFilesRole OR isNative OR (pythonRole AND pythonSourceSuffix)`. The known suffix sets remain those already accepted. A passive archive outside all-file/data inventory is not an executable candidate; one inside it remains ordinary bound data. Its suffix never overrides `hasMZ`. This same decision must be used for each referenced file when reconstructing the expected candidate set. Config sidecar refusal is a separate policy, not an unconditional executable-candidate suffix rule.
4. Preserve existing customization and loader-role `.local/.manifest/.config` file/directory refusals before suppressing directory descent. For **every** `isNative=True` image in any role, run the existing adjacent-sidecar refusal, regardless of suffix: appended and extension-replacement `.local`, `.manifest`, `.config` alternatives. Refuse file or directory sidecars; absence must be positively observed, access/query failure must not be converted into absence. Keep deadline checks on these observations. A renamed native image discovered only beneath a Python/data tree therefore gets the same checks as a `.dll`.
5. Run native sidecar refusal before candidate deduplication returns, or retain enough verified native/sidecar state to prove it already ran successfully for that exact unchanged file. The simplest safe form is to perform the cheap refusal checks on every native encounter, then deduplicate the binding/hash/count work. Expected-set reconciliation applies the same classification and native sidecar refusal. Repeated observations do not imply atomic protection from mutation.
6. Remove W 409/S 1394/S 1466 early archive skips and replace W 410–414/470–474, S 1398–1405/1468–1479 and suffix-only adjacent checks with the classifier/policy calls. Keep the exact-spelling collision maps, mandatory reference verification and candidate-set equality checks. Preserve role-specific config treatment: unrelated package/data `.config` files remain ordinary data under all-file inventory, not automatically refused or native merely by suffix. A config file with MZ content is native and gets image-sidecar checks; loader-relevant external sidecars remain unsupported even if frozen.

P needs no correction for this finding. Its actual-profile gate and strict native/Python loaded-file census already validate file bindings; archive-backed module/cache refusal at 970–1014 concerns actual Python archive loaders/member paths. Do not weaken it or reinterpret an MZ archive-named disk image as permitted archive import. Retain P byte-for-byte if no concrete classification call-site defect is found there. If a P change proves necessary, stop for coordinator reconciliation rather than expand this diagnosis's minimum W/S patch silently.

## Independent static acceptance matrix

No executable probe or test file is required under this diagnosis. A separate non-implementing Sol reviewer must inspect exact final W/S hashes and trace these hypothetical inputs through both discovery and expected-set reconstruction, before W launches S and before S launches P:

| Case | Required result |
| --- | --- |
| Unlisted MZ `renamed.zip`, `.egg`, `.whl` in fixed CWD/PATH directory or Python root outside data inventory | Native executable candidate; missing exact binding fails before launch. No archive suffix skip. |
| Bound MZ `module.bin`, extensionless image, `.py`-suffixed image or archive-named image in Python/data/native role | Native classification independent of candidate short circuit; exact binding required and adjacent sidecars refused. |
| Bound renamed MZ plus `module.bin.local` directory or appended/replaced manifest/config sidecar | Refusal in discovery/reconciliation even where traversal has no loader-relevant role. Check before deduplication can return. |
| Genuine non-MZ passive zip/egg/wheel | Remains ordinary data: inventoried where all files are required, otherwise no executable-candidate promotion solely by archive suffix. Does not become an allowed Python search/import source. |
| Active archive PYTHONPATH, present optional stdlib zip, archive-backed module/cache | Existing explicit archive-import refusal remains; absent optional stdlib zip/default unused hook behavior unchanged. |
| Zero/one-byte file; short read; unreadable or changing header/image; expiry during read/sidecar check | Defined non-MZ result for short ordinary files; actual read/error/change/expiry keeps partial evidence and non-PASS. No unavailable observation becomes a passive archive. |
| Overlapping roots, identical path repeated, case-distinct aliases, different scan order | Same effective classification/roles and expected set; native sidecars checked; unique successful file/byte counters increment once; ambiguous identities refused. |
| Unrelated data config versus loader-role config | Accepted existing data inventory treatment retained; unsupported loader redirection refused. Discovery and expected-set classification do not disagree merely because suffix is `.config`. |

Reviewer also confirms P/H and protected candidate/source/test/configuration hashes remain unchanged, all six accepted cycle-3 fixes remain, and no reference is skipped. Exact counts come from shared owned scan state; header/sidecar observations are not falsely added as full-file successfully hashed bytes. Failures preserve original partial counts and cannot set completion true.

## Boundary, timing and residual risks

No new supported source, archive mode, root/category, binding/schema/record, dependency, command/environment change or phase is necessary. This implements the existing PE/MZ rule and sidecar refusal more faithfully; no plan/trust-boundary amendment is required. Preserve passive archives as data, all-file inventory, role-specific policy and active archive-import refusal.

The extra header/sidecar work uses the same inherited deadline, including all loops, expected-set calls and final success check. **30-second standalone fit is unmeasured.** Acceptance remains deadline-bounded: incomplete, late, unavailable or mismatched observations are non-PASS. Nonpreemptible filesystem/OS operations may return late; they must not gain success or a new clock. Preserve self-check 10 seconds and build 180 total/150 numerical cutoff; no retries/second slot/cap increase or reduced coverage.

MZ recognition is intentionally conservative: a self-extracting/archive polyglot beginning with MZ is native for this profile; a malformed MZ file may be overclassified, not omitted. Exotic executable formats not recognized by the pinned reviewed CPython/Windows/trusted-code contract are not newly supported. This is not universal confinement or atomic replacement protection. A need to expand formats, resolve sidecars instead of refuse them, change a supported role or restore archive imports is a stop for coordinator/user boundary direction.

Preserve all one-use ownership, original process/native identity/launcher ancestry, suspended assign-before-resume, nested Job membership/cleanup/termination/exit, archive/preservation, truthful unavailable telemetry and reserved-build gates. No source/recipe/geometry/limit or product-policy change. Operational Luna cycles stay 3/4 consumed, cycle 4 unreserved until separate release; no Sol correction is used here. Historical candidate diagnostics/correction/build/confirmation counters remain unchanged. Candidate NO-GO/unservable, build 3 unreserved, no runtime/build authorized.

Work consisted only of static source/document reads/searches and SHA-256 hashing, plus writing this one diagnosis report. No source/plan/ledger/checkpoint/manifest or other file was edited. No tests, imports, linters/parsers/compilers, operational scripts/runtime, manifest preparation, candidate/GIS/numerical/build or browser work was run. Browser evidence is inapplicable. Return this feasible limited correction to the coordinator; stop before implementation or cycle reservation.
