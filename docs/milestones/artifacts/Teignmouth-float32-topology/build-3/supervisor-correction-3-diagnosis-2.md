# Correction 3 — bounded diagnosis after Luna cycle 2

2026-10-25. Sol 6.1 medium, non-implementing `/root/sol_review17_plan`. Disposition 48 authorizes this one static diagnosis, maximum 120 seconds, before any cycle-3 dispatch.

**GO_FOR_LUNA_CYCLE3**, subject to coordinator reconciliation of the explicit archive-support amendment below and release of the exact W/S/P scope. All seven findings admit one coherent bounded correction; no additional user boundary decision is needed for this conservative refusal policy under disposition 48. This diagnosis is not implementation, reserves no attempt and does not dispatch anyone.

## Source reconciliation

Read review 6, accepted finite-profile addendum, dispositions 40/45/47/48 and actual W/S/P. Static SHA-256 hashing matches review 6/disposition 47:

| File | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `b3623911fcece373706af237e294c90411913f7715102eae6c2cd1d25a0fcbfc` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `7883669c05ec3ce165db6d0b0ff8d4832df931479bf10c63c1f0f049d7965d33` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `2ec7a76b448f2235133fa96a2819f4b65058fca498081857578af51ad390de91` |
| Disposition 48 | `b396a6b3c83427963b84d1519ba8e4b8b52add2b0ae6b17737e7fedc17f270c5` |

Review 6 source hash: `cec2f9dbff637f79025eecdf9b2f8c0221c68816bc9ed3374cab918232bde7b4`. Accepted addendum source hash: `e3e6578421cef97b20983955c8bba9622e148204cdbacb29a4e8aae12e8259aa`. Line references below identify the current inspected files, not a Git diff. Review 6 accepts P's RECORD normalization/owned-tree fix; preserve that logic and its honest inventory/progress predicates.

## Exact limited corrections and independent acceptance proof

### 1. Tagged customization alternatives — policy implementation defect

W 405/409 and S 1261–1278 must recognize customization alternatives before launch independently of a filename's final stem. Smallest safe rule: case-insensitively refuse a directory exactly named `sitecustomize` or `usercustomize`, and a file whose name starts with either exact customization name followed by `.` (or equals the name). Apply before extension/candidate classification and deduplication. This deliberately conservative rule covers plain modules, `.cp313-win_amd64.pyd`, legacy `.pyd`, `__pycache__/sitecustomize.cpython-313.pyc`, and other tagged alternatives without importing machinery to discover suffixes. Refuse the customization directory in child-directory enumeration even when that scan will not descend.

P's existing post-startup `sys.modules` refusal stays as detection. It does not replace W's gate. Independent review traces the same rule through W before S launch and S before P launch, using plain/tagged/cache/package and mixed-case hypothetical names. No plan amendment is needed: this implements the accepted present-customization refusal, with a conservative superset of names.

### 2. Case-distinct paths — prelaunch identity/evidence defect

Replace W's silent case-folded `visited.Add` skip at 379/416 and folded reconciliation at 432–459 with a folded-key-to-exact-canonical-spelling map, as S already approximates at 1215–1218. An already-seen **identical** canonical path may be deduplicated with accumulated roles. A different exact spelling under the same Windows-folded key is ambiguous and must fail, even if hashes agree. No file may disappear into a folded set before this comparison. Apply the same ambiguity check to directory/root identities encountered in scans so a case-distinct directory cannot hide descendants.

Reject case-distinct frozen repository references at W 510–511 and across the combined repository/external absolute-path namespace before any executable launch; reject duplicate bindings rather than silently overwrite. S/P must preserve/refuse equivalent ambiguous references and profile paths too. Exact overlapping scans of the same location remain legitimate; do not mistake identical overlap for a collision. No hardlink or path-alias equivalence is inferred from equal bytes.

Static proof: `Foo.py`/`foo.py`, case-distinct directories, folded duplicate manifest references, and repeated exact same-path scans. Both distinct files must be refused before W launches S; matching set counts alone are insufficient. No plan amendment is needed.

### 3. Native redirection — missing unsupported-configuration refusal

Use the accepted profile's **refusal** option rather than inventing an SxS/native-policy resolver. W's scan at 404–407 must check redirection names before its directory skip, and S's child-directory loop at 1265–1270 before suppressing descent. Refuse externally supplied `.local` redirection files **and directories**, and `.manifest`/`.config` sidecars in loader-relevant locations. Check launcher/base image sidecar candidates explicitly, whether or not directory enumeration would otherwise classify them; also inspect adjacent sidecars for executable/native images in the scanned profile. A directory named `python.exe.local` is not an ordinary directory to skip.

Conservative implementation may refuse every `.local`/`.manifest`/`.config` entry, file or directory, in the direct native search locations and package native trees. Scope this rule by loader role: an unrelated data configuration file deep in an ordinary package/data tree is not automatically a redirection source solely by suffix. Where sidecar applicability cannot be established safely, refuse rather than bind-and-assume. Do not silently exempt a relevant sidecar because it is frozen, Windows-owned or has valid XML. Embedded behavior in the pinned image/OS loader remains within the selected trust contract; this does not authorize new external redirected disk sources.

Apply W/S rules symmetrically in candidate observation and expected-set reconciliation. Keep partial/error context on refusal. Review cases: file and directory `.local`, launcher/base sidecars, native extension sidecar, bound sidecar with unknown target, direct-native directory scan without recursion, and unrelated inventoried data config. No plan amendment is needed: the addendum already requires resolution **or refusal** of unsupported redirection. If a required current executable actually needs one of these refused external mechanisms, stop for a concrete profile amendment; do not attempt resolution in this cycle.

### 4. `.pth` leading whitespace — pinned-semantics mismatch

Use one small supported ASCII grammar consistently in W 637–649, S 1091–1107 and P 687–701. Keep empty/whitespace-only lines ignored; comment lines are ignored only with `#` at column zero. For every other line, **reject leading whitespace** as unsupported rather than strip it into a different path or comment. Thus `  folder`, ` #comment`, and ` import x` cannot be accepted as `folder`, a comment or some normalized hook. Then reject column-zero `import ` / `import\t` executable lines. For accepted literal paths, remove trailing whitespace only, matching pinned `site.py`'s `rstrip` behavior. Retain ASCII/encoding, canonical/approved/directory checks and bound-hook requirements.

Review all three languages against the same cases: blank, spaces-only, column-zero comment, indented comment/path/import, trailing spaces, executable import with space/tab, and ordinary path. Rejecting noncanonical leading whitespace is expressly allowed by the addendum's restricted unambiguous syntax; no plan amendment is needed. Do not alter the actual `.pth` files or inherited environment.

### 5. Duplicate venv keys — ambiguous config validation

In W, factor the in-file config read into one deadline-aware validator used by **every** home/policy consumer: `Get-BaseInterpreter` at 754 onward, the first-home read at 610–614 and the dictionary policy parse at 303–305 must not retain different precedence. Parse keys with the same trimmed case-insensitive normalization, reject every repeated key including repeats with identical values, require explicit unique home/version/include-system-site-packages values, and reject malformed ambiguous key lines. Preserve ordinary unique installed `executable`/`command` metadata. Reuse validated values within the invocation only while the config hash remains unchanged.

S 989–994 uses the same duplicate/refusal policy. P should validate the same unique config policy at its actual-profile check rather than relying only on hashing the text in `_actual_identity` (826/842). No unverified shared repository helper/import is introduced. Pre/post config/hash checks remain mandatory. Static proof includes case-varied duplicate keys, whitespace-varied repeats, conflicting first/last home, identical duplicates, missing required key, and the ordinary current config. No plan amendment is needed: duplicate/conflicting keys are already explicitly unsupported.

### 6. Archive/member loaded census — supported feature mismatch

**Recommend a narrow plan amendment: archive imports are unsupported.** The addendum currently permits validated zip sources and whole-archive binding, but P 870–885 treats module/cache member paths as ordinary files. Rather than add loader/member provenance machinery in this correction, explicitly refuse active archive search sources before launch. This is a support restriction, not weaker binding or permission for a new source. Disposition 48 explicitly allows this recommendation. Coordinator must record it as an amendment when reconciling/releasing the correction; the accepted addendum is not edited by this diagnosis. No additional user boundary is necessary unless an actually required source depends on archive imports.

Exact effects:

- W rejects PYTHONPATH archive files, zip-plus-subpath forms and present `python313.zip`; S uses the same refusal before P; P rejects any actual archive search source or archive-backed module. `.pth` literals remain directories only. Retain positive observation of **absent** optional stdlib zip. CPython's default `sys.path` may contain that absent zip pathname: this is an explicitly absent optional source, not a loaded archive and not a reason to change command/environment.
- Remove the acceptance routes through W `Assert-FiniteProfileZip`/zip candidate loops (353/374–387) and S `_validate_profile_zip`/archive candidate paths (1052–1064/1419–1456), or make them unconditionally reject when reached. Update P's PYTHONPATH/expected-profile logic at 661–675 consistently. Reject unsupported archive source forms regardless of suffix; require any supported search entry to be an ordinary approved directory, except the known absent optional stdlib zip entry. No synthetically created archive-member manifest path.
- Passive zip/egg/wheel files used solely as ordinary data are not imported merely by existing in a scanned package directory. Keep their ordinary all-file/data inventory where applicable; do not label them successfully verified archive imports. Trusted code may not append or load them as executable sources under this profile. If actual census observes an archive loader/member, fail explicitly with archive/member context instead of hiding it as an absent bytecode cache. Keep normal filesystem-loaded file/cache census intact.
- The standard interpreter's unused `zipimporter` path hook may remain part of trusted default machinery; its mere presence is not an archive import. Do not change interpreter commands to remove it.

Static proof: archive PYTHONPATH file, archive/subdirectory form, present versus absent stdlib zip, passive data archive, actual zip-backed `__file__`/loader and virtual `__cached__`. Every active archive case is refused, never PASS. No current candidate use of an archive is inferred from code that previously offered zip support, and no runtime observation was made. If later required package/bootstrap code actually needs an archive source, stop and return that exact dependency for restored whole-archive/member-provenance design; do not delete/unpack files or sanitize environment to evade refusal.

### 7. W child-scope counters — false aggregate evidence

At W 379–465 replace scalar closure counters with a single explicitly shared mutable owned state (hashtable or equivalent), passed to every `& $scan` invocation. Keep visited/exact-path maps, candidate count, successfully hashed unique bytes, directory visits and current phase together. Update the shared properties directly; never rely on child-scope scalar increment propagation. Publish the same values into existing nested caller progress fields after each successful observation and on exceptions/expiry before rethrowing; do not reset counters for a later scan root. Final result and progress records derive from that same state.

Define counts honestly: candidateCount is unique successfully bound candidate files; bytesHashed is their unique verified byte total, not a claim to count every hashing pass in the whole supervisor; directoryCount is completed/started scan-directory visits with that convention stated in existing evidence fields/prose. Duplicated exact paths can accumulate roles without adding file count/bytes. Optional additional observed/attempted counters may stay in the existing nested record, with no schema identifier change. Partial record must distinguish attempted observation from successful hash; a failure cannot fabricate a complete count.

Static review traces at least two different scan roots, an overlapping exact path, a directory containing only noncandidates, failure during hash and deadline on the second root. Check final unique file count against exact visited map and independently reconciled expected set. No plan amendment is needed; this restores truthful existing evidence.

## Ordered cycle-3 scope and gates

1. Coordinator reconciles the archive-refusal amendment and exact source hashes, then separately releases/reserves cycle 3 if appropriate. No reservation follows this diagnosis automatically.
2. W: unify config parsing, strengthen exact-path/case registration, customization/redirection/`.pth` refusals, archive refusal and shared evidence state. Keep existing schema/mode/record names and process ownership code.
3. S: mirror those profile/config/refusal semantics before P and after termination; retain stronger existing exact-path checks and all referenced-file/pin checks. P: mirror `.pth`/unique-config/archive actual-state checks, preserve existing census except explicit truthful unsupported-archive handling. Preserve the accepted P inventory ownership fix unchanged except any necessary call-site consistency.
4. H, tests/candidate/config/source/GIS/product bytes, prepared records and historical evidence remain unchanged. No dependency/root/category/mode/phase/command/environment change is required. No new schema or manifest-member representation is proposed.
5. Later authorized implementation uses disposition 40's static gates and submits exact final W/S/P hashes to a separate non-implementing Sol reviewer. The reviewer must check all seven cases above and retained profile, reference closure, collection separation, strict reserved-build gates, one-use ownership, launcher/base identity, Jobs, termination, preservation and unchanged protected bytes/counters. Syntax PASS alone does not resolve these findings.

The full profile remains **deadline-bounded in acceptance**: every new parse/registry/file/directory/refusal check, hash chunk, counter publication and final completion predicate must use the original inherited deadline; no restarted clock, retry, second slot or reduced coverage. Filesystem/OS calls are not proven preemptible. A call returning late or incomplete observation must remain non-PASS. This diagnosis does **not** claim the full pre/post scans and execution fit 30 seconds. Preserve standalone 30 seconds total from W start, self-check 10 seconds, build 180 total/150 numerical cutoff.

## Stop rule and handback

Stop for an exact boundary decision if required actual startup/package behavior needs archives or native redirection refused above, any fix needs changed commands/environment/dependencies/schemas/roots/modes/phases/files, or coverage cannot be maintained under the fixed deadline. Do not reinterpret missing frozen preparation as success, change the finite trusted-code/OS-loader contract, claim universal confinement, or claim atomic protection from concurrent replacement.

Operational Luna cycles remain 2/4 consumed and zero reserved until coordinator action; this is not a Sol correction. Historical candidate diagnostics 2/2, candidate Luna corrections 4/4 and Sol correction 1/1 remain used; builds 2/6 used/zero reserved, confirmation 0/1 ineligible. Candidate NO-GO/unservable; build 3 unreserved. All numerical/source/product constraints remain unchanged.

Work was limited to static document/source reads/searches and SHA-256 hashing, plus writing this single report. No code, plan, checkpoint, ledger or other file was edited. No imports, tests, linters, parsers/compilers, scripts, runtime modes, GIS, candidate/numerical build, browser or other executable project phase was run. Browser evidence is inapplicable. Return to coordinator for reconciliation/release; stop here.
