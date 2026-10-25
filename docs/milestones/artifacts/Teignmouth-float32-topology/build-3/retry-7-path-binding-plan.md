# Retry-7 self-check — exact path-binding plan only

2026-10-25. Issue `Teignmouth-float32-topology-representation-1`; D146. **Propose exactly four path-literal changes, preserving the statically accepted S correction.** Proposed parent is `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-7`; proposed leaf is `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-7\run-1`. Neither is selected/reserved/probed/created by this plan. No target-path absence is claimed.

## Actual baseline and exact replacements

Independently hashed current source bytes during planning:

| Source | Required future inverse SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `f600efc92fd040aa5b91cf543210be139ed50f895eba7d62c34175e73dc7dc8b` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `fda96d4edd66327e50c34ee1345d1a098aced4a7b58dcd1c088a4cd8c44c616f` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `75678b51d0e17d89862bf0a7ee3446014969ba73aae6cd31606288553b163e27` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py`, unchanged | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

These match D146's accepted state. Final S review: `retry6-s-wait-callback-correction-final-independent-review.md`, SHA-256 `e82bad72b08c05bcc354df9eb1ab66d0ff28c1ef19a2d2739da1a1e6868dde12`; final handoff bound there is `7cb7c2887d5d686baa8f0690889a1dc37af8cbc4659f52b0ae045dd07d305793`. Accepted prior path plan/review are `7283aa5440cda0cf35308697e95362c77b28d0ada52d2a2ac0c486dbe972a66a` / `b96b2e89c738f2e61a41410cb1775321a22c8da53e393a47e6dc854fae2e6bc3`; prior actual-byte path review is `c6e54bf9b26c945c9124e0cd6306f9b79b531ac0852a0084fb88e6cba66ebdbf`. Those prior path observations are historical and say nothing about retry-7 availability now.

Static source search identifies only these intended replacements:

| Exact current span | Old bytes within literal | Proposed bytes | Count |
| --- | --- | --- | ---: |
| W23 self-check `baseEvidence` | `.codex\build3-supervisor-selfcheck-retry-6` | `.codex\build3-supervisor-selfcheck-retry-7` |1|
| W344 independent terminal-fallback `expectedRoot` | `.codex\build3-supervisor-selfcheck-retry-6` | `.codex\build3-supervisor-selfcheck-retry-7` |1|
| S39 `SELF_ROOT` | `.codex/build3-supervisor-selfcheck-retry-6` | `.codex/build3-supervisor-selfcheck-retry-7` |1|
| H17 `EVIDENCE` | `.codex/build3-supervisor-selfcheck-retry-6/run-1` | `.codex/build3-supervisor-selfcheck-retry-7/run-1` |1|

P has zero such consumers and must not change. After separate release, replace only the final retry digit in these four spans. Keep every other byte, encoding/BOM/newline and formatting unchanged. Final counts must be W/S/H=2/1/1 proposed literals, zero active old retry-6 literals, P=0. Unexpected consumers, target/count mismatch or broader edit need is a stop, not authority to change more files.

Reverse only those proposed four spans **in memory** and require the complete baseline digests above, with unchanged file lengths. In particular, S must restore **final corrected `fda96d…`**, not historical pre-correction `1cee4b…`. No reconstructed file is written/executed; record actual final hashes and exact inverses at handback. No prospective final hash or executed inverse is claimed here.

## Fixed output vocabulary and return identity

All paths below expand under the exact proposed absolute parent/leaf above using existing separator conventions. Parent outputs remain: `caller-invocation.json`, `caller-invocation.json.update`, `caller-invocation.failure.json`, `self-check-handoff.json`, `self-check-handoff.json.update`, `self-check-handoff.consumed.json`, `supervisor-script-start.json`, `supervisor.stdout.log`, `supervisor.stderr.log`, and S-owned `run-1`.

Leaf outputs remain: `invocation.json`, `invocation.json.pending`, `nonzero-authorization.json`, `nonzero-authorization.consumed.json`, `nonzero-script-start.json`, `nonzero-helper.json`, `nonzero.stdout.log`, `nonzero.stderr.log`, `tree-root-authorization.json`, `tree-root-authorization.consumed.json`, `tree-root-script-start.json`, `tree-root-started.json`, `tree-child-started.json`, `tree.stdout.log`, `tree.stderr.log`. No additional file/schema/mode is introduced and not every file is promised to exist on failure.

W's two parent bindings must agree, including its separate failure-fallback allowlist. S's SELF_ROOT/SELF_RUN and H's EVIDENCE must agree on the same parent/leaf for handoff consumption, authorizations, starts, markers and logs. W exclusively creates the fresh parent during a later gated invocation; S alone creates `run-1` after authenticated handoff. Caller/Handoff ownership validators, exclusive create/update/refusal paths and stale `.update`/`.pending`/fallback/consumed refusal remain unchanged. No alias/environment redirect substitutes for the literal patch.

A future result must be bound to this exact retry-7 namespace: caller `mode=self-check`, phase `nonnumerical-self-check`, ten-second budget and correct handoff/consumed paths; handoff oneUse/nonce/QPC and expected supervisor script; S record `mode=self-check`, command pointing to the fixed venv launcher/S script with `--self-check`, and matching parent handoff/nonce/start identity. All script paths remain the same repository paths; only output roots change. Preserve fresh runtime process creation/image/hash/launcher/base identities, not copied historical facts. `treeProbeBoundary` must describe that future run under the unchanged strict proof, never imported retry-6 results. Record actual outer exit, chosen/native/S exit, clock and status separately. `deadlinePassed=true` retains W's existing meaning `currentQpc < deadlineQpc`; it is not a timeout declaration.

## Future path/ancestor/absence gates only

No path or retry-root inspection runs in this plan. After express release, repeat these read-only checks at implementation handback, independent actual-byte review and immediately before the separate one-use gate:

- Existing `C:\`, `C:\vibe`, `C:\vibe\localSimulator` and `C:\vibe\localSimulator\.codex` must be canonical directories with exact full/resolved spelling, safe containment and no reparse point/junction/symlink/unexpected LinkType/Target. Resolve existing ancestors only; create no probe.
- Proposed retry-7 parent must be absent as file and directory. Force-enumerate the safe existing parent for case-insensitive equal names and Windows trailing-dot/space-normalized aliases. Require all derived caller/update/fallback/handoff/consumed/start/log/leaf paths absent through the safe absent parent. Access error, ambiguity, missing ancestor, occupancy even if empty or stale output is refusal, never absence.
- Preserve self-check refusal if `C:\vibe\localSimulator\data\generated\teignmouth-float32-topology` or `C:\vibe\localSimulator\docs\milestones\artifacts\Teignmouth-float32-topology\build-3\run-1` exists; inspect their safe existing ancestors when later expressly authorized. No deletion/preparation/repair authority follows.

Observations are point-in-time, not reservations or race guarantees; preserve runtime fresh-root/reparse/exclusive ownership checks. Never adopt/rename/delete an occupied target, choose another number, reuse a consumed root or fall back to retry-6. Unsafe/unavailable premises stop for coordinator decision.

## Behavior and preservation

Raw-byte inverses must preserve W diagnostic failure isolation, same-handle limits,20ms opportunity/one-second reserve, single close and exact rejection. Preserve S strict opt-in false by default, private-last-error reset/immediate capture, terminal18 requirement in the same bounded snapshot,65536-row/64-pass/Job limits,16 periodic plus one final census, three-second wait horizon, inherited deadline-minus-one-second containment bound, late/unknown/error rejection and final proof before unchanged markers/identity/Job/termination/root-exit gates. Shared wait/default/normal/build/preflight callers are unchanged. Preserve H startup/authorization, normal actual7/7 and complete zero/empty/zero gate. No timeout waiver, PID31876/conhost exemption, count subtraction, later-disappearance override or cleanup-to-PASS. Snapshot-incarnation limitations remain.

Original/retry1–6 evidence remains immutable/consumed/non-PASS. Later expressly released full relative-name/count/hash comparison must cover **70 files**: original2 + retry1=2 + retry2=11 + retry3=11 + retry4=11 + retry5=16 + retry6=17. Use the accepted53-row matrix plus D129's17-row retry-6 inventory as metadata; no consumed evidence-content diagnosis or rewriting. Final accepted handoff/review preservation results are historical evidence only; this plan performs no comparison.

All six protected bindings remain:

| File | SHA-256 |
| --- | --- |
| `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` |`a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b`|
| `pipeline/torquay_pipeline/road_surface_topology.py` |`88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880`|
| `pipeline/scripts/build_teignmouth_float32_candidate.py` |`5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b`|
| `pipeline/tests/test_teignmouth_float32_candidate.py` |`34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8`|
| `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` |`4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea`|
| `config/road-surface-teignmouth-float32.json` |`e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228`|

## Separate release, review and one-use invocation

Required sequence: independent Sol plan PASS → coordinator acceptance and explicit four-literal/static/preservation release → Luna implementation/handback → independent Sol actual-byte/inverse/path/static/preservation PASS → immediate coordinator source/path checks and a **separate one-use gate**. No root creation during planning, patching or review. Proposed later static gates, only if released: affected S/H Ruff check and format-check, W AST parse without invocation, exact byte/count/inverse proof, unchanged P and70/6 preservation; unchanged C# compile-only evidence can be reused. No source import/test/process probe can be disguised as a static gate. Missing release/check, drift, inverse mismatch or failed gate stops; no further edit follows automatically.

Only a future immediate gate may select/reserve retry-7 and authorize exactly one command from `C:\vibe\localSimulator`:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File pipeline/scripts/invoke_teignmouth_float32_build3.ps1 -Mode self-check
```

Do not execute current retry-6-bound bytes or S/H directly. This proposed command is not authorization. Any eventual invoked refusal/startup failure/partial result/timeout/non-PASS consumes that one attempt; preserve all resulting files and stop without replay or automatic next root. The original10-second absolute QPC budget and all cleanup/termination/ownership rules remain, with no restart or enlargement. Native calls/allocation/persistence remain non-preemptible; no runtime fit, hard wall-time, cleanup-duration or durability guarantee is claimed. A self-check PASS would not authorize candidate build/readiness/serving/publication or resolve historical identity/provenance/outer-exit unknowns.

Historical budgets, reserved/used attempts and correction counters carry forward without reset; conflicting/paused/exhausted authority is a stop before invocation. Candidate stays NO-GO/unservable, build3 unreserved; pending AOI/geographic/source/product/synthetic constraints and unauthorized later issues remain unchanged.

## Planning handback

Only authorized non-consumed source/document reads/searches, current source hashes and this plan write occurred. No source/evidence/checkpoint/ledger edit, consumed evidence-content read or retry-root inspection, root/ancestor/alias/absence query/probe/creation/reservation, Ruff/check/test/import/parser/compiler/process/runtime/self-check/preflight/build/GIS/browser/publication/commit/push/merge occurred. No target-path absence is claimed. Stop for a separate independent Sol plan review and coordinator decision.
