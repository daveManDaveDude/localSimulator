# Retry-5 outer descendant rejection — bounded diagnosis

2026-10-25. Sol read-only diagnosis under disposition 110, SHA-256 `25692cbef37ab821039338f38f7a3d06bec8e1f44fbf83ea9db3232db7ba599c`. **Retry-5 remains consumed, immutable and non-PASS.** The precise rejection branch is identifiable; the rejected process's identity and authenticated lineage are not recoverable from saved evidence. No behavior fix or another invocation is justified as already gated.

## Exact source and evidence bindings

Recalculated actual current source hashes:

| File | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf` |
| P, unchanged | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

Read accepted retry-5 plan/review and implementation review; rehashed them to `1983a1559598766bb280c67546af1b4350e6959039c2cdf0c0edd36b98a5db0e`, `0ca9c416765f681639b1a3f9fe9e9a5bd4992199e1a4bd1fd152996c11c81467`, and `ffa1b68a0fa05d8452386537c63f3ad2d31bccc84eeebf0fae08c5eb6654447a`. These are static path/preservation acceptance, not proof of runtime containment. Read retry-4's accepted conhost diagnosis only; no older retry evidence was reopened.

Read/rehashed all sixteen retry-5 files listed by disposition 110. All match that inventory. Relative to `.codex/build3-supervisor-selfcheck-retry-5/`:

| File | SHA-256 |
| --- | --- |
| `caller-invocation.json` | `87adbe38bcbf779eb7e41cd0ba70e6ebe0d395d15cb6e62721a9b2d0b1034906` |
| `supervisor-script-start.json` | `0c75e56e765756b30ed06f8204a145a8c8d82ee2844009f385b7460bc26f86c0` |
| `self-check-handoff.consumed.json` | `cafc18f3965daf968dfff056367d8bb7f8011654e16eba30c3a3679d16115d36` |
| `run-1/invocation.json` | `e87a0e404117ce1ef552c14ff66634df57bc2d895aa1cada9aba020e7b22651a` |
| `run-1/nonzero-authorization.consumed.json` | `b3d40f91b26186a46577f27813886bacbb3f534a8ce010a0f20c3fff475ba098` |
| `run-1/nonzero-helper.json` | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| `run-1/nonzero-script-start.json` | `60b0388b1c6dd733771b16abd78aec9e3ba839111396690d8b9ddf5173e57dc4` |
| `run-1/tree-root-authorization.consumed.json` | `b9d35fb31fd6677d1cec2d40fb869d79348a98ba57828c7c12845f86a5baea0d` |
| `run-1/tree-root-script-start.json` | `5f1e7db08802fd76a68bc1ac985ea3995cbedd0097218525eaeb01b3fe9e188e` |
| `run-1/tree-root-started.json` | `630e0b7d264d07c61dd4d8cf0aba8f9bf77a0ab376d43fe857b1c942e39b2e25` |
| `supervisor.stderr.log`, `supervisor.stdout.log`, `run-1/nonzero.stderr.log`, `run-1/nonzero.stdout.log`, `run-1/tree.stderr.log`, `run-1/tree.stdout.log` — each empty | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## Exact control flow and meaning of the rejection

The literal error is thrown only by W `Assert-OwnedJobTree` at **1053**. It is not S's inner unexpected-member error and not H's startup-identity validation. W's sequence (1009–1055) is:

1. Query current outer Job process IDs using native `GetJobProcessIds`; the returned list is not used to decide the escape predicate.
2. `Get-DescendantProcessIds` obtains a separate Toolhelp process table through `GetProcessRows`, then computes a numeric PID/parent-PID transitive closure from supplied roots (65536 rows, 64 levels, original deadline).
3. For each derived numeric descendant, `OpenProcess(0x1000, false, id)`; a failed open is skipped. On a successful handle, call `IsProcessInJob(handle, exact outer Job, out member)`. API failure throws a different error. A successful false result adds the PID to `uncontained`; handle closes in finally.
4. Any collected PID causes the saved escaped-descendant error. No wait, process creation time, image identity or original ancestry rows are recorded with that error.

The failing call is the **main outer monitoring loop at W 1548**, with roots outer venv launcher **20700** and authenticated S interpreter **3204**. W also calls the function at 1507 during startup and 1538 immediately after S authentication. However the caller record contains `supervisorLauncherIdentity`, `supervisorScriptIdentity` and `outerJobMembershipObserved=true`; these are assigned only after the 1538 call succeeds. There are no other later calls producing this literal. Thus this is post-authentication outer supervision, not failure to discover S or initial helper authorization.

The code path plus saved message establishes that a subsequently opened object for numeric **32560** was reported nonmember of the exact outer Job, after numeric ancestry expansion included that PID. It is stronger than merely comparing two asynchronous PID lists: W queried membership on a handle. It is weaker than proving the opened object was the same incarnation in the earlier snapshot, or that every parent-PID link belongs to the authenticated ancestry. Those linkage observations were discarded. Neither the snapshot chain nor creation/image/liveness for 32560 was persisted. Searching the sixteen files finds that number only in the caller's error/message/errorId.

W catch (1594 onward) marks setup-or-supervision failure, sets chosen exit 2 and terminates the owned outer Job; its cleanup records zero remaining outer members. **Zero owned members does not demonstrate termination of a genuinely outside-Job object.** No targeted termination or exit observation for 32560 is recorded. Consequently “forced containment confirmed” cannot be expanded into “PID 32560 was killed” or “nothing escaped.” The native launcher exit 2 is read after forced cleanup, not proof S independently returned terminal 2. `supervisorScriptExitCode` is null. Outer pwsh exit 1 versus recorded chosen/native 2 remains a separate unresolved discrepancy.

## What the inner evidence proves, and does not

The normal helper launcher **40928** / base interpreter **36128** authenticated, both retained handles signaled with actual exit **7**, and both were released. Primary snapshot at **308603.7869175–308603.786963** was complete zero/empty/zero; a later drain snapshot at **308603.7891698–308603.7892123** was again complete zero/empty/zero. `finalAcceptance.accepted=true`, phase `normal-complete`, with no primary/checkpoint error. This proves that stage completed in retry-5, unlike retry-4's inner unexpected member. It does not prove the previous console-host hypothesis universally resolved or prove the later tree.

The normal checkpoint is written before S launches the tree (S 4030). Saved records then show:

- Tree venv launcher **29244**, creation FILETIME **134373908580209321**, authorized by S3204 with the same nonce/deadline.
- H tree-root base interpreter **41316**, creation **134373908580366216**, matching approved base path/hash, its launcher29244 and supervisor3204. H consumed the one-use authorization and wrote the script-start marker through `_consume_startup` (H161–221), which checks its own launcher/base/supervisor identity chain.
- H `--tree-root` then used `subprocess.Popen` (H247 onward) for `--tree-child`; `tree-root-started.json` records child **launcher36784**, creation **134373908581523985**, root41316/parent29244 and nonce. `CHILD_STARTED` here means Popen returned and H observed that launcher's native identity.

**There is no saved `tree-child-started.json` in the authoritative inventory.** Do not confuse the root's child-launch marker with the child's own startup/identity marker. No child base-interpreter PID/image/creation/parent identity was saved, and 32560 equals none of the recorded IDs above. It might have been a child interpreter, another descendant or a misassociated process; this record cannot choose among them.

H's published startup facts do not prove S had completed its subsequent `_contained_interpreter_child` (4042), `_verify_helper_start` (4050), or tree wait/containment callback (4065) before W interrupted it. H startup checks identities but does not query S's exact inner Job. S performs those membership checks independently. The final tree-root/child markers are validated by S only later (4079 onward). No saved mismatch from those branches exists. The normal checkpoint leaves top-level `INVOCATION_STARTED` until a later terminal update; outer termination can end S without running Python catch/finally. This is consistent with the saved partial record and empty logs, not evidence S failed to execute required terminal persistence voluntarily.

## Classification and minimum next requirement

**Precise blocker: a real successful false-membership observation is reported, but authenticated descendant identity/lineage is missing.** Retain non-PASS. Evidence cannot establish a genuine escape by the intended tree-child, a benign infrastructure process, a stale parent/PID association, or a startup/identity/census defect. In particular, it does not justify calling the alarm false positive. PID/parent snapshot expansion is not creation-identity authentication; PID reuse/stale numeric lineage and snapshot-to-open races remain possibilities, not diagnosed causes. There is no evidence to attribute 32560 to conhost or to inherit retry-4's classification. No allowlist, delay, later disappearance override or policy relaxation is defensible.

The smallest useful next **separately planned** change is W-only failure-evidence retention around `Get-DescendantProcessIds`/`Assert-OwnedJobTree` and its existing caller error serialization, with no acceptance change:

- Retain the exact original roots, already-observed outer Job IDs, relevant original Toolhelp PID/parent rows and exact ancestry edges used to reach the failing PID; capture QPC operation intervals/status/completeness. Do not replace the failing snapshot with a later census.
- Before closing the very handle on which membership was false, make bounded best-effort creation/exit-time and image-path observations using W's existing GetProcessTimes/QueryFullProcessImageName APIs and current query rights; retain the actual false query outcome and error statuses. Reopening by PID through `Get-NativeIdentity` would describe a later object and cannot authenticate the first query. Any post-query identity still explicitly lacks original snapshot-incarnation association.
- Record known retained launcher/S creation identities, relevant chain creation ordering only where actually observed, and whether the new facts match saved authorized tree/root/child markers. Unknown/inaccessible/disappeared/partial/late associations remain unknown, never admitted. Do not identify the process from a filename or a later marker alone. No new liveness rights/waits, hash scan, broad process probe, termination target or console API is justified by this diagnosis.
- Persist a strictly bounded diagnostic through the existing caller failure message/record contract, preserving the exact primary failure and cleanup. A concrete plan must specify caps, API/error ordering, one-close ownership, best-effort failure isolation and how mandatory containment/cleanup remains timely within the **original 10-second total QPC deadline**. Do not spend a fresh relative budget on diagnostics or let reporting prevent cleanup. S/H/P and all launch/identity/census acceptance rules remain unchanged.

This is a missing-evidence recommendation, **not** a released implementation plan or proof the proposed instrumentation is already correct. A future diagnosed genuine helper escape would need a different explicit containment/launch correction; a future proven stale lineage would need an authenticated ancestry design. Neither may be selected from this evidence. If exact same-handle/chain evidence cannot be added within the existing APIs/record/deadline/cleanup boundary, return the precise scope decision instead of guessing a repair.

Required later review criteria: same original predicate and failure retained; original snapshot distinguished from later handle facts; unknown associations explicit; exact-handle observations and closure; bounded reporting; no new flags/exemptions or successful cleanup-to-PASS; unchanged S/H/P and consumed evidence; independent review and all fresh-path/coordinator gates remain separate. Stop on missing authority, any inferred identity, baseline drift, unbounded capture, new rights/API/schema/acceptance need or inability to preserve cleanup. No retry-6 path is proposed or selected here.

## Handback and limits

All sixteen saved files match disposition 110. Read-only source/evidence/document inspection and hashing plus this report were the only work. No source/evidence/checkpoint/disposition edit, old consumed evidence access beyond retry-4's diagnosis document, parser/linter/compiler/test/import/source execution, process inspection/probe, wrapper/self-check/preflight/runtime/collection/manifests, root creation, GIS/numerical/candidate build or browser action occurred. No runtime fit or complete tree PASS is claimed. Retry-1 through retry-5 remain immutable/consumed/non-PASS, candidate NO-GO/unservable, build 3 unreserved. Historical unsaved `957157…` and outer/internal exit discrepancy remain unresolved. Return report SHA-256 and stop for coordinator acceptance and a separate plan decision.
