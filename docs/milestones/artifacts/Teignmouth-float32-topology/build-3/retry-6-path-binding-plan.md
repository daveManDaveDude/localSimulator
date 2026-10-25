# Retry-6 self-check — exact fixed-path plan

2026-10-25. Issue `Teignmouth-float32-topology-representation-1`; **PLAN ONLY** under disposition 124. Proposed future root: `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6`; proposed leaf: `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1`. These are proposals, not selected/reserved/created/probed paths. No invocation or source edit is authorized by this artifact.

## Accepted bytes and prerequisite path-only change

The currently accepted sources still bind to consumed retry-5. They must not be invoked unchanged. A later separately released path-only implementation is necessary before a retry-6 one-use gate; it must preserve all accepted behavior while changing exactly four literal spans:

| Source / required inverse baseline | SHA-256 |
| --- | --- |
| W `C:\vibe\localSimulator\pipeline\scripts\invoke_teignmouth_float32_build3.ps1` | `804ae8c42f6637a61505e53e825972d758b8ae2c1c2d0740ff5a076a0e703b45` |
| S `C:\vibe\localSimulator\pipeline\scripts\run_teignmouth_float32_build3.py` | `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` |
| H `C:\vibe\localSimulator\pipeline\scripts\teignmouth_build3_supervisor_selfcheck.py` | `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf` |
| P `C:\vibe\localSimulator\pipeline\scripts\teignmouth_build3_runtime_preflight.py`, unchanged | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

These are the disposition-124 accepted bindings, not newly executed checks in this plan. W's static implementation PASS is `retry6-w-descendant-escape-correction-2-independent-review.md`, SHA-256 `f465d1987338551da0d7f093db358eca05143c806591e933e27f6093c0b4279a`. Preserve its diagnostic bounds, failure isolation and identity limitations. Historical H transcription errors are superseded by the full actual H binding above.

| Exact span in pinned source | Old literal | Proposed literal | Count |
| --- | --- | --- | ---: |
| W23 self-check `baseEvidence` | `.codex\build3-supervisor-selfcheck-retry-5` | `.codex\build3-supervisor-selfcheck-retry-6` | 1 |
| W344 independent terminal-fallback `expectedRoot` | `.codex\build3-supervisor-selfcheck-retry-5` | `.codex\build3-supervisor-selfcheck-retry-6` | 1 |
| S39 `SELF_ROOT` | `.codex/build3-supervisor-selfcheck-retry-5` | `.codex/build3-supervisor-selfcheck-retry-6` | 1 |
| H17 `EVIDENCE` | `.codex/build3-supervisor-selfcheck-retry-5/run-1` | `.codex/build3-supervisor-selfcheck-retry-6/run-1` | 1 |

After independent plan PASS and coordinator implementation release, Luna may change only these spans, preserving encoding/newlines and every other byte. P, tests/configuration, historical records and evidence remain unchanged. Final static count proof must show 2/1/1 proposed literals and zero active retry-5 root literals in W/S/H. Search active consumers statically; an additional consumer or needed behavior change is a stop, not authority for further edits. Reverse only the four spans in memory and require exact W/S/H baseline hashes above; record actual final hashes. No prospective final hash is asserted. No reconstructed source is written or executed.

## Proposed exact output paths and ownership

All entries below are proposed under the same canonical workspace. No path existence/alias/ancestor probe was performed in this planning turn.

| Absolute proposed path | Producer/role |
| --- | --- |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6` | W creates this parent only during the future one-use invocation, using existing fresh-root refusal/creation checks. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\caller-invocation.json` | W-owned caller record. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\caller-invocation.json.update` | Existing owned caller update; stale/unowned update refuses. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\caller-invocation.failure.json` | Existing exclusive terminal failure fallback; W344 allowlist must match W23. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\self-check-handoff.json` | W → S one-use parent handoff. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\self-check-handoff.json.update` | Existing separately validated owned handoff update. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\self-check-handoff.consumed.json` | S's authenticated one-use handoff consumption. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\supervisor-script-start.json` | S native startup identity, same parent. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\supervisor.stdout.log` | W's exclusive supervisor stdout destination. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\supervisor.stderr.log` | W's exclusive supervisor stderr destination. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1` | S alone creates this leaf after authenticated handoff; never pre-create it. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1\invocation.json` | S's unchanged self-check record/checkpoints/terminal result. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1\invocation.json.pending` | Existing S-owned checkpoint replacement staging. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1\nonzero-authorization.json` | S's fresh nonzero helper authorization. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1\nonzero-authorization.consumed.json` | H's one-use consumption. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1\nonzero-script-start.json` | H startup identity marker. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1\nonzero-helper.json` | Expected nonzero helper marker. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1\nonzero.stdout.log` | S nonzero helper stdout. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1\nonzero.stderr.log` | S nonzero helper stderr. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1\tree-root-authorization.json` | S's fresh tree-root helper authorization. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1\tree-root-authorization.consumed.json` | H's one-use consumption. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1\tree-root-script-start.json` | H startup identity marker. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1\tree-root-started.json` | Root's child-launch observation; not the child's own startup proof. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1\tree-child-started.json` | Child's separate marker, when actually reached. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1\tree.stdout.log` | S tree helper stdout. |
| `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6\run-1\tree.stderr.log` | S tree helper stderr. |

This is the existing possible-output vocabulary, not a prediction that all outputs will exist or that partial output is success. No new record/schema/filename/mode/phase is proposed. Fresh nonces, process identities, hashes and absolute QPC bindings are produced only by existing code during a separately authorized invocation; never copy old records or identity facts. W descendants' bounded diagnostics remain optional suffixes in the existing caller message, not new files.

## Read-only preconditions for later release

After implementation authority, repeat these checks at implementation handback, independent actual-byte review and immediately before a separate one-use coordinator gate. None runs in this plan:

- Verify expected W/S/H/P actual hashes, exact four-span inverse, accepted diagnostics and all cross-file producer/consumer paths. P stays unchanged; no alias configuration or environment redirect may substitute for the literal change.
- Require retry-6 parent absent as both file and directory. Force-enumerate its existing `.codex` parent for case-insensitive equal names and names equal after Windows trailing-space/dot normalization; refuse ambiguous aliases. Inspect canonical absolute paths, drive spelling and component types for `C:\`, `C:\vibe`, `C:\vibe\localSimulator` and `C:\vibe\localSimulator\.codex`; require existing directories with exact canonical resolution, no reparse point/junction/symlink, unexpected LinkType/Target or ambiguous/escaped containment. Resolve only existing ancestors; do not create a probe. Verify all proposed descendants are absent through the absent parent and refuse any observed stale/pending/fallback/consumed path.
- A missing/inaccessible/ambiguous ancestor, occupied root even if empty, unsafe alias, hash drift, unavailable check or changed premise is a refusal. Do not adopt, clean, delete, rename, repair, reuse retry-5, choose an alternate number or fall back to an older root. Read-only observations cannot reserve a path or remove races; retain W's existing runtime reparse/fresh-path/exclusive ownership checks and S/H one-use validators. If accepted premises cannot safely resolve, stop for coordinator decision.
- Keep `C:\vibe\localSimulator\data\generated\teignmouth-float32-topology` and `C:\vibe\localSimulator\docs\milestones\artifacts\Teignmouth-float32-topology\build-3\run-1` absent under S's existing self-check refusal checks. Do not prepare build outputs, ledger snapshots, manifests, preflight or runtime identity files. Their presence blocks; it does not authorize deletion.

## Preservation and static gates

Original and retry-1 through retry-5 evidence remain consumed, immutable and non-PASS. The complete accepted inventories total **53 files**: original2 + retry1=2 + retry2=11 + retry3=11 + retry4=11 + retry5=16. Use the pinned cycle-1 handoff matrix (`4701ddc210ef755832a0bb8cebf3c561e51868ac961b499ddf97867fb3b25704`) and accepted dispositions 56/63/67/78/89/110 for full relative-name/count/hash comparison during later expressly authorized preservation gates. Retry-5 must remain 16/16 unchanged. No evidence-content diagnosis, replay, cleanup, overwrite, retrospective PASS or counter reset follows from preservation access. If the coordinator does not release the required comparison, report that missing gate and stop before invocation.

The six protected candidate/topology/builder/test/fixture/config files retain the exact accepted bindings in the cycle-2 independent review. Preserve pending AOI/product/geographic/source constraints, candidate output bytes and synthetic behavior. No numerical/GIS/build authority follows from a self-check.

After separate release, proposed static gates are: exact byte counts/span counts/in-memory inverse; affected S/H Ruff check and format-check using the existing pipeline venv (only if expressly released as static gates); W PowerShell AST parse without invocation. The embedded C# is unchanged by four path literals, so reuse the pinned compile-only evidence; compile again only if separately authorized. Do not import S/H, invoke W/H/S/P, run tests or use a process probe as a static check. Record exact commands, actual final hashes, every preliminary failure, authorized full preservation results and time-stamped path observations in the handoff. Do not broaden formatting or fix unrelated findings. Independent Sol must review actual final bytes, inverse hashes, unchanged P/protected files, all paths including the separate fallback allowlist, ownership/default/rejection/cleanup behavior and point-in-time path checks. Implementer self-approval is insufficient.

## Separate one-use flow, timing and stops

Required sequence: **this proposed plan → separate independent Sol plan review → coordinator acceptance and explicit four-span implementation/static/preservation release → Luna implementation/handoff → independent Sol actual-byte implementation PASS → coordinator repeats source/path preconditions and records an immediate separate one-use gate**. No root is created during planning, patching or review. Only that final gate may authorize W's existing root creation and one invocation from `C:\vibe\localSimulator`:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File pipeline/scripts/invoke_teignmouth_float32_build3.ps1 -Mode self-check
```

This is a future command, not permission to run it now. Never invoke S/H directly, build mode, preflight, a second wrapper, or a previously consumed path. W creates the fresh parent; S authenticates the handoff and exclusively creates `run-1`; H consumes fresh S-bound authorizations. Preserve native launcher/base/creation/hash/nonce identities, suspended assignment-before-resume, Job membership, exact outer rejection, both helper exit7 observations, complete zero/empty/zero normal-stage gate and deliberate tree containment/timeout/termination gates. No console-host exemption, later-disappearance override, count subtraction, targeted termination or cleanup-to-PASS is allowed.

The original **10-second total absolute QPC deadline** starts at W entry and is inherited throughout S/H; do not restart it or add diagnostic time. Preserve the 20 ms optional diagnostic opportunity/one-second reserve, one-close ownership, termination/waits and existing outer-watchdog behavior. Native API, allocation and persistence operations are not preemptible; static checks do not prove a hard wall-time bound, cleanup duration or evidence durability. No sleeps/retries/new watchdog or timeout allowance is proposed.

Record the actual outer exit, internal chosen/native/S outcomes, elapsed/QPC and persisted states separately. A refusal, partial result, timeout, failure or incomplete persistence remains non-PASS. Preserve every resulting file, including empty logs and pending/fallback files, and consume the one-use attempt after its single invocation; stop without replay or automatic next root. Cleanup uses the existing owned Jobs/handles only; do not delete evidence or claim zero owned members proves an outside-Job process was terminated. New details never authenticate the earlier snapshot incarnation by implication. Historical outer exit1/internal2 discrepancy and unsaved `957157…` history remain unresolved.

All historical issue budgets, reserved/used attempts and correction counts carry forward; this plan resets none and reserves no new candidate build. A gate must reconcile actual checkpoint/disposition state before granting one attempt; conflicting/paused/exhausted authority is a stop, not additional permission. A self-check PASS, if later observed, is only its existing supervisor gate and cannot make the candidate ready/servable, build it, alter GIS/numerical outputs, publish or authorize later issues.

## Planning handback

Only static authorized document/source reads/searches and this plan artifact write occurred. No root/alias/ancestor/absence probe, source/evidence/checkpoint/ledger edit, preservation gate, parser/compiler/linter/test/import, runtime/process probe, self-check/preflight, path creation/reservation, build/browser/publication, commit/push/merge occurred. Stop for separate independent Sol plan review and coordinator decision. Candidate remains **NO-GO/unservable**, build 3 unreserved, retries1–5 consumed/non-PASS, retry-6 proposed only and unexecuted. No current absence or successful-check result is claimed by this plan.
