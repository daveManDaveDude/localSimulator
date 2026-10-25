# Independent supervisor review 13 — retry-2 path binding

2026-10-25. Independent non-implementing Sol reviewer `/root/sol_review_face_diag`, under disposition 65. **PASS — static acceptance of exactly four fixed-path substitutions.** Read disposition 65, the accepted plan (`a48d9a075b6330860f2c00ed886ed74ca78e0e966c65503368e232a7cad33883`), current checkpoint, actual W/S/H derivations and preserved disposition-63 evidence. No actionable implementation finding remains in this scope. This report authorizes no self-check or subsequent action.

## Exact source boundary proof

Independently counted the new root string and reversed it **in memory only** from `build3-supervisor-selfcheck-retry-2` to `build3-supervisor-selfcheck-retry-1`, then hashed reconstructed UTF-8 bytes without writing or executing source:

| File | Current SHA-256 | Substitutions | Inverse SHA-256 — accepted baseline |
| --- | --- | --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `3078e1df4bf89438208bbcfc09150dbce77f180259f847a84287892d26662989` | 2 | `98be856a85894bb7fec5e8863ba15023ff16d545e567e2dd0bd0c2b45df68d5e` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `2bae9a35ee91ca154bba19c0a3848b0bda2f46930f38e9090bd632ff5653300d` | 1 | `17a7a347b175bfa3ad1a1dcbdc4167d3d4b1c8a73da0dc09d537ec1c6d4a8ef6` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `e3cdadced5d90a669155002870636610e77df68b8a013deeef187893fbd65e78` | 1 | `3419551b5c19e69c2487bb57c1bc49c102d4b7bfe1db1f93aea60cf038ebe05a` |

All inverse hashes exactly restore review-12/pre-path-change baselines. This establishes that the only W/S/H byte changes are the four accepted path strings: W **23** self-check parent, W **344** fallback allowlist, S **39** SELF_ROOT, H **17** EVIDENCE. No other code, command, mode, schema, deadline, record name or behavior changed; accepted unsigned CreateFile literals and owner/handoff guards are preserved. No Git index diff is claimed for the untracked operational files.

The checkpoint's W digest omits a character; the full independently calculated W digest is recorded above. The coordinator acknowledged this as a metadata transcription typo and will reconcile its metadata separately. It is not a W/S/H implementation defect; this reviewer did not edit the checkpoint.

## Cross-file path contract — PASS

- W **21–49** derives its caller, caller pending/fallback, handoff/pending/consumed, supervisor-start and supervisor stdout/stderr paths from the retry-2 parent for self-check only. Build and runtime-preflight roots remain unchanged. The handoff's selected-mode validator derives the same exact parent/path, preserving separate caller/handoff ownership.
- W **343–356** independently restricts terminal fallback to the retry-2 parent and fixed `caller-invocation.failure.json`, retaining exclusive creation, self-check-only ownership, failure-only status and exit 2. Neither prior root is admitted by that allowlist.
- W **1203–1242** validates the existing safe parent, refuses any occupied retry-2 root, checks caller/pending/fallback/handoff/pending/consumed/start/log/run absence, then creates only its parent and exclusively owned parent records. S receives/consumes the matching parent handoff (**510–520**), publishes its startup marker under SELF_ROOT (**502–506**), and refuses a pre-existing leaf (**580–584**).
- S alone exclusively creates `SELF_RUN = SELF_ROOT / "run-1"` (**39–40**, **2232–2250**). W's start/stdio remain in the parent, so no absent-leaf dependency is introduced before S starts. S invocation/pending, helper authorizations, helper-start readers, helper stdout/stderr and root/child marker readers all derive from SELF_RUN.
- H **17**, **161–225** consumes the corresponding leaf authorizations and writes start/helper/root/child markers beneath the same retry-2/run-1. Its fixed child command invokes the same H script; the child uses the same EVIDENCE constant (**244 onward**, **277 onward**). No path argument, environment override, auto-numbering, run-2, old-root fallback or additional consumer was introduced.

Thus a stale original/retry-1 record cannot satisfy retry-2 ownership, handoff/start or helper validation. Occupied/unsafe/reparse paths and unowned pending records retain refusal behavior; no consumed evidence is adopted or cleared. An absent retry-2 parent establishes all fixed descendant absence, while later exclusive creation/consumption still applies. Existing native identity/nonce/QPC/Job/cleanup/preservation gates remain byte-identical apart from the accepted fixed path values.

## Preservation and absence

P remains `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`. Independently rehashed candidate/helper/builder/test/fixture/configuration files all match their full accepted review-12 bindings: respectively `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b`, `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880`, `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b`, `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8`, `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea`, `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228`.

All four prior evidence hashes match:

| Evidence under `.codex/` | SHA-256 |
| --- | --- |
| Original caller | `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e` |
| Original caller `.update` | `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75` |
| Retry-1 caller | `f992b356191d202a5e2357cffb1d64d90b4dd7f8ac54cd0b76ab2e0d7540dcf3` |
| Retry-1 PREPARED handoff | `b73738fc81644b942ea4f84890146e1bdfc73d925005552cb34db1af05aadc79` |

Retry-1 remains consumed/non-PASS and its records unchanged. Retry-2 remains **absent**; its existing `.codex` parent was observed as a directory without a reparse attribute. No retry-2 directory or descendant was created by this review.

Only static document/source/evidence reads, searches, directory/absence inspection, hashing and in-memory string/hash comparison occurred, plus writing this report. No code/metadata/evidence/manifest was edited. No scripts, parsers, linters, compilers, tests, imports, wrapper/self-check/preflight/runtime/collection, manifest preparation, GIS/numerical/build or browser action ran. Luna-reported static PASS checks were not rerun. This proves the path-only source boundary and inspected agreement, not successful native calls, actual persistence/containment or timing. Self-check retains 10 seconds from original W QPC start; **30-second runtime profile fit remains unmeasured**.

Return static PASS to the coordinator for its separate gate of exactly one retry-2 invocation under disposition 65. This report neither runs nor authorizes that call, any additional retry, or any later phase. Historical counters and source/origin/domain/recipe/collision/numerical limits remain unchanged. Candidate remains **NO-GO and unservable**; build 3 remains **unreserved**.
