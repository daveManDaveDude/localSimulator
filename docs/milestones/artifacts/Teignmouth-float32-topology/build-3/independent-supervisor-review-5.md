# Independent supervisor review 5 — Luna cycle 1

Date: 2026-10-24. Independent reviewer: `/root/sol_review_face_diag`, non-implementing Sol session. Authority: coordinator disposition 41, under dispositions 40 and the accepted `supervisor-correction-3-plan.md` (SHA-256 `3e564b7ee6f099b54062794e7fb3468d08748f35c21a931abfae189634aa1c3a`). Compared actual current W/S/P source and call order with review 17 (`independent-supervisor-review-4.md`) and that plan. Applied the current Torquay skill and agent workflow. **FIX REQUIRED. Cycle 1 has been independently reviewed; neither review-17 finding is fully closed.**

The operational files were already untracked before submission. There is no reliable Git index diff for them, and none is claimed as evidence. Line references below are one-based references to the exact current files, not historical revisions.

## Verified submission and protected hashes

All four submitted SHA-256 values match disposition 41 and the ledger:

| File, relative to repository root | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `ab351b89aca3eb24231e946308c09d25e1165aaf03efeefc998987e194a75128` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `9c502bf827250d74e6d1ba3c6fde02595e7cd46f725599a693f700bca4310332` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `086dafa5a59d68904c937d7d85ba3c8945294fd8effa08af5159e197ca383416` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `9fc73a8ed7aca3b4e223d3f23a7bd676f48011aa0abe98eb864f9e98a5191d20` |

H is byte-for-byte unchanged against the reviewed baseline. Independently rehashed protected files also match their accepted bindings:

| Protected file | SHA-256 |
| --- | --- |
| `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |

The configuration's observed SHA-256 is `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228`. The protected implementation/provenance hashes provide evidence that this submission did not change candidate arithmetic, fixture provenance, historical helper, builder or focused tests. Disposition 41 abbreviates the builder digest in one prose sentence; the complete digest above matches the ledger.

## Actionable findings

### 1. Required independent package-tree census is not viable with the actual installed metadata

**FIX REQUIRED — behavior defect, inventory coverage criterion.** P lines 939–945 unconditionally require nonempty `top_level.txt` before reaching any independent tree traversal at 948–1023. Static directory inspection shows that the installed `numpy-2.5.4.dist-info` and `shapely-2.2.0.dist-info` have no such file; many other installed distributions also lack it. Their declared inventories can identify owned package trees, but these packages instead raise and skip the independent traversal via 1030–1032. Thus required NumPy/Shapely package/native trees are not independently searched for files omitted from metadata.

There is a second concrete obstruction in the same ownership derivation. P 918–922 treats every non-metadata first path component as a package name, including `..`. The actual NumPy RECORD begins with `../../Scripts/f2py.exe` and `../../Scripts/numpy-config.exe`; PyProj RECORD begins with `../../Scripts/pyproj.exe`. P 925 passes these installed metadata paths directly to `observe_file`, where 798–801 rejects a lexical path containing parent components rather than safely normalizing a distribution-relative declaration first. Such observations become errors at 845–846. For distributions that do have `top_level.txt`, the accumulated `..` is then also considered a package-tree root at 950–959. A venv Scripts launcher entry is not ownership of the site-packages parent tree.

The failure is conservative: 1024–1045 and 1162–1167 keep completeness false, so this does not fabricate successful coverage. Nevertheless it leaves the requested complete inventory unobtainable for ordinary files already installed here, before timing feasibility is considered. Correct the ownership discovery within the approved roots: distinguish distribution-relative declared file paths from owned package/module trees, resolve and validate the former safely, and use available declared/tree ownership without making optional `top_level.txt` the only gateway. Preserve real missing/unavailable required inventory errors and partial evidence. Do not broaden traversal to a parent installation tree or relax reparse/root checks.

### 2. W's startup/search audit does not close executable import sources before launch

**FIX REQUIRED — missing pre-import closure enforcement.** W 182–193 accepts any existing search path under the repository or an approved external root; it does not establish that executable sources reachable from that directory are frozen-bound. W 311–320 applies that containment-only check to `PYTHONPATH` and native search paths. The same check admits non-executable `.pth` path targets at 363–368. Being inside an allowed root is not a file binding.

The startup scan at W 340–373 only inspects direct files in three fixed directories, recognizing `.pth`, `sitecustomize.py` and `usercustomize.py`. It does not resolve startup customization packages or sourceless bytecode, customization on admitted PYTHONPATH targets, transitive executable imports from a bound customization module, or shadow modules/caches on the script directory and other admitted import paths. W then launches the inherited environment with the existing `-B` arguments (49–52, 718–720). S immediately imports standard-library modules at 5–18; P does so at 5–16 before its own validator. An unbound shadow/startup source on an admitted search path is therefore not refused before it can execute. This is a static reachable case, not a claim that such an extra file currently exists or that verification was run.

The new checks correctly hash every *referenced* file and reject some hooks, but they do not prove completeness of the executable startup/import closure. P's later strict loaded census cannot repair that ordering gap. Complete the accepted plan's startup/search/cache resolution, or fail closed for a source/search configuration that cannot be established from existing frozen bindings before launch. Keep existing commands/environment, roots and schemas; unsupported closure must stop rather than gain a new isolation flag, mode or manifest contract.

## Plan acceptance matrix

| Criterion | Decision and static evidence |
| --- | --- |
| Suffix-independent declared files plus independent owned trees | **FIX REQUIRED:** suffix filter is gone and all declared file types are considered, but finding 1 prevents required independent trees from completing. |
| Honest missing/None/empty/error/partial handling | **PASS, static:** P 758–846, 906–938, 1025–1039 records contextual errors and partial progress; unavailable/empty declared inventories do not silently succeed. Unreadable/reparse/escaping/changing files and deadline expiry remain errors. |
| Completion predicate and error propagation | **PASS, static:** P 1040–1045 requires no errors, all distribution rows complete and final deadline check; 1153–1167 merges inventory errors and requires both loaded and proposed inventories complete. Finding 1 causes honest incompleteness, not false completeness. |
| Prelaunch bootstrap closure | **FIX REQUIRED:** finding 2. Control/reference hashing alone is insufficient to close actual startup/search resolution. |
| Explicit verification-before-third-party/repository-import order | **PASS for explicit imports; overall closure blocked by finding 2:** W 641–659 precedes native launch; S 1813–1847 precedes P launch at 1885; P 1108–1111 precedes path insertion/imports at 1113–1120. Failure has no explicit import fallback; P is not imported into S. |
| All referenced controls/files and before/after pins | **PASS, static:** W 196–309 and 377–380; S 727–850, 876 onward, 1813–1847 and 1935–1976; P 527–564, 1228–1238. Standalone only changes mandatory reservation requirements, not checking of entries actually supplied. Counts and complete verification gate acceptance. |
| Collection/verification/self-check/build separation | **PASS, static:** P collection remains status `RUNTIME_IDENTITY_COLLECTION_ONLY`, null match, proposed-only files and exit 2 (1170–1206, 1329). S standalone only dispatches P. Reserved build still requires snapshot/reservation and repeated repository/external preflight before builder dispatch (2101–2143, 2249–2273). H unchanged. No new schema, root category, mode or phase was introduced. |
| Process ownership, deadlines, archival and truthful evidence | **PASS for inspected static contract, runtime unproven:** W retains original QPC deadlines 180/10/30 (8–15), suspended outer-Job assignment before resume (695–748), native identities/exits and failure cleanup (756–919). S retains 180 total/150 numerical constants (41–44), inherited handoffs, inner Job launch/containment, bounded waits/termination (1399–1416), fixed safe output archival (1419 onward), and post-termination preservation. New hash/inventory loops inherit the deadline. No arbitrary memory cap or zero-as-measured substitution was added. |
| Scope/protected state/counters | **PASS for verified bytes and recorded state:** hashes above match; H/candidate/helper/builder/test/fixture unchanged. Ledger reports new operational Luna cycle 1 used, none reserved; candidate historical counters remain diagnostics 2/2, Luna 4/4, Sol 1/1, builds 2 used/zero reserved, confirmation 0/1 ineligible. No counter was changed by this review. |

## Prerequisites, limitations and disposition

The three named build-3 input/external/runtime records remain absent, as do build-3 `run-1`, `invocation.json`, both standalone/self-check run leaves and the candidate output directory. Missing records cause verification to stop before executable launch (W 642–649), and reserved build lacks its required preparation. This is safe failure, not a successful gate or permission to add schemas/phases. Future preparation of the existing named records still needs its separate disposition and independent manifest review; a complete safe freeze/verification cannot be approved from this submission while findings 1–2 remain.

The checkpoint's “Current hashes” bullet still contains the prior submission while its latest-review/next-action bullets point at disposition 41. This review uses the exact matching disposition-41/ledger/current-file hashes, not that stale bullet; coordinator-owned metadata was not edited. Absence of execution leaves and disposition/ledger statements corroborate the reported no-runtime state, but file absence alone cannot prove historical non-execution.

Only static reads, directory/metadata inspection, searches and SHA-256 hashing were performed, plus writing this report. **No Python imports/execution, tests, Ruff, parser/compiler, PowerShell wrapper, self-check, runtime collection/verification, diagnostic, GIS, numerical/build or browser work was run by this reviewer.** Implementer-reported Ruff/format/PowerShell AST/C# compile-only PASS is recorded in disposition 41; it was not rerun and cannot prove these behavior criteria. One `rg` command used an unsupported Windows glob path and returned a read error; direct metadata reads supplied the cited RECORD evidence. No source, manifest, ledger or checkpoint was edited.

Static inspection cannot demonstrate actual Windows nested Job behavior, venv-launcher ancestry races, exit/timing observations, complete closure fitting the 30-second slot, native blocking-call preemption or measured memory. No new runtime proof is inferred. Existing hashing also does not establish atomic immutability against hostile concurrent replacement. Source/origin/domain/recipe/collision guards, all numerical limits and strict nonempty source-plane-zero remain protected; candidate serving remains **NO-GO**. Build 3 remains **unreserved**. Further action belongs to the coordinator within disposition 40's allowance; this report authorizes no runtime mode or candidate build.
