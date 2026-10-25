# Self-check retry-2 — bounded fixed-path binding plan

2026-10-25. Sol 6.1 medium planner `/root/sol_review17_plan`. Read-only planning under disposition 64's serial self-check repair authorization, after review 12 accepted the CreateFile access-literal correction.

**Feasible: one exact new fixed root, four literal substitutions in W/S/H.** Proposed root: `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-2\`, with existing leaf name `run-1`. Static inspection found the new root absent and its existing `.codex` parent a directory. Keep the root and all descendants absent through implementation/review. No schema, record-name, mode, command/environment, dependency or runtime-root-category change is needed. This plan performs no implementation or execution; coordinator must reconcile the synchronized W/S/H scope before dispatch.

## Read sources, current hashes and protected consumed slots

Read disposition 64, review 12, current executable W/S/H references and derived paths, relevant original supervisor plan and subsequent path/ownership plans/dispositions, and all four prior caller/handoff evidence files. Search covered executable references across repository source (excluding dependency/data trees) and `pipeline/tests`, plus documentation/metadata references. Only W/S/H contain the active fixed self-check root literals. P and unrelated tests are not consumers of that root.

| Current operational file | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `98be856a85894bb7fec5e8863ba15023ff16d545e567e2dd0bd0c2b45df68d5e` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `17a7a347b175bfa3ad1a1dcbdc4167d3d4b1c8a73da0dc09d537ec1c6d4a8ef6` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `3419551b5c19e69c2487bb57c1bc49c102d4b7bfe1db1f93aea60cf038ebe05a` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` (unchanged) | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

These hashes were recalculated and match review 12. Preserve its exact accepted unsigned CreateFile masks, C# `uint access`, caller/handoff ownership fixes, frozen PREPARED handoff identity and five-field transition; no interop or persistence behavior edit accompanies this path binding.

| Immutable prior evidence | SHA-256 |
| --- | --- |
| Original `build3-supervisor-selfcheck/caller-invocation.json` | `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e` |
| Original `build3-supervisor-selfcheck/caller-invocation.json.update` | `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75` |
| Consumed `build3-supervisor-selfcheck-retry-1/caller-invocation.json` | `f992b356191d202a5e2357cffb1d64d90b4dd7f8ac54cd0b76ab2e0d7540dcf3` |
| Consumed `build3-supervisor-selfcheck-retry-1/self-check-handoff.json` | `b73738fc81644b942ea4f84890146e1bdfc73d925005552cb34db1af05aadc79` |

Prior-evidence paths are under `.codex/`; all four files were read and rehashed. Original directory contains only its 834-byte caller and 848-byte pending copy. Retry-1 contains only its 2730-byte caller and 1445-byte PREPARED handoff. Original caller persistence failure and retry-1's recorded UInt32 argument-conversion failure stay non-PASS. Retry-1 reports exit 2 and no launcher creation/assignment/resume; the unsigned fix's static PASS does not change those recorded outcomes or demonstrate a later successful native call.

Never delete, move, copy/promote over, edit, truncate, reset or reuse either old root or any evidence. Their continued existence is expected, not an obstacle to be removed. No replacement/automatic search across roots is permitted.

## Exact implementation scope: four synchronized path literals

| File/section, current line | Required change | What remains derived/unchanged |
| --- | --- | --- |
| W self-check `$baseEvidence` switch, 23 | `.codex\build3-supervisor-selfcheck-retry-1` → `.codex\build3-supervisor-selfcheck-retry-2` | Only self-check mode parent changes; build and runtime-preflight parents stay fixed. |
| W `Write-CallerTerminalFailure` `$expectedRoot`, 344 | Same retry-1 → retry-2 literal substitution | Essential independent fallback allowlist must equal the new self-check parent. Keep exact comparison, ownership/parent checks, filename and exclusive create unchanged. |
| S `SELF_ROOT`, 39 | `.codex/build3-supervisor-selfcheck-retry-1` → `.codex/build3-supervisor-selfcheck-retry-2` | `SELF_RUN = SELF_ROOT / "run-1"` remains unchanged. |
| H `EVIDENCE`, 17 | `.codex/build3-supervisor-selfcheck-retry-1/run-1` → `.codex/build3-supervisor-selfcheck-retry-2/run-1` | Auth/consumed/start/marker paths remain derived from that exact leaf. |

No other executable root literal was found. W's `Assert-OwnedHandoffDestination` selected-mode path at 277 is already derived from `$baseEvidence`; do not hardcode a second new path or weaken it. Caller destination validation likewise uses the fixed `$callerPath`. The root/parent refusal checks and all W/S/H producer-consumer derivations need **validation**, not source rewrites beyond these four substitutions.

No optional retry CLI argument, environment variable, automatic number selection, `run-2`, arbitrary directory, old-root fallback or list of accepted retry roots. This binds just one next slot. Future failure requires another bounded plan/review; disposition 64 does not justify making slot allocation automatic in this correction.

## Complete path/ownership agreement to inspect

The following paths must all resolve beneath the new parent/leaf, with their existing record names and schemas unchanged:

| Owner/consumer | Parent or leaf records and contract |
| --- | --- |
| W caller | Parent `caller-invocation.json`, exclusive `caller-invocation.json.update`, and fallback `caller-invocation.failure.json`. Exact Caller kind still requires literal caller schema, proposed/persisted wrapper PID/start/mode, validated owned parent and existing exact destination. Fallback stays self-check-only, exclusive, failure-only and never replaces caller/pending. |
| W → S handoff | Parent `self-check-handoff.json` and its exclusive `.update`; S consumes it to `self-check-handoff.consumed.json`. Separate Handoff kind/ownership remains; snapshot/hash and schema/mode/nonce/wrapper/QPC/path/hash/pin identity checks remain. Only verified suspended-launcher binding transition allowed before assignment/resume. |
| S → W start/stdio | Parent `supervisor-script-start.json`, `supervisor.stdout.log`, `supervisor.stderr.log`. S `_startup_record_path` and `_handoff` use SELF_ROOT; W reads the same parent marker. Do not move them into an initially absent run leaf. |
| S run ownership | S alone exclusively creates `run-1`; W checks it absent before launch. Leaf `invocation.json` and its existing `invocation.json.pending` updates stay S-owned. No precreation of leaf by W/implementer/reviewer. |
| S → H authorizations | Leaf `nonzero-authorization.json` and `tree-root-authorization.json`; H consumes each to its corresponding `*-authorization.consumed.json` only after inherited deadline/native ancestry/nonce authorization. S helper-start readers use the same SELF_RUN. |
| H → S helper evidence | Leaf `nonzero-script-start.json`, `tree-root-script-start.json`, `nonzero-helper.json`, `tree-root-started.json`, `tree-child-started.json`. Existing helper modes, marker content, authentication and fixed child command stay unchanged. Child uses H's same EVIDENCE constant. |
| S helper stdio | Leaf `nonzero.stdout.log`, `nonzero.stderr.log`, `tree.stdout.log`, `tree.stderr.log`. Existing commands/stream destinations remain fixed within that leaf. |

Existing schema identifiers remain unchanged: caller v2, parent handoff v2, script/helper-start records, selfcheck-helper authorization v1, S result/marker schemas as currently emitted. Existing payload path strings are generated from the new exact constants on the future invocation; do not modify any old JSON payload. Nonces, PIDs, timestamps, QPC start/deadline and newly created source hashes must be actual observations from that invocation, never copied from failed records. No input/external/runtime manifest or reservation snapshot is prepared here.

## One-use and absence contract

Keep W's initial safe-parent/no-reparse/lexical checks and explicit refusal if **retry-2 parent already exists**. Before preparation, check absence of caller, pending, fallback, handoff, handoff pending, consumed handoff, supervisor-start, stdout/stderr and run-1. An absent parent/leaf logically establishes absence of all fixed descendant helper paths; after that, exclusive creation/consumption checks still apply. Any stale record, unowned pending, reparse/alias/unsafe parent, inaccessible observation or race is refusal, never permission to clear/reuse the slot.

W may create the absent exact new parent only during the later authorized wrapper invocation. It then exclusively creates its caller and handoff, and S/H preserve their own exclusive creation/consumption ordering. Ownership flags become true only after successful owned creation; no existence-based adoption. Caller updates remain valid after handoff consumption and use their own validator. A record in retry-1/original root can never satisfy retry-2 caller/handoff/start/helper validation.

Keep the existing fixed candidate/build-output absence guards. Runtime-preflight roots, build parent/run/output, package/source roots and allowed categories remain unchanged. A storage-slot path revision is not a new runtime mode or source/geographic boundary.

## Tests/docs constraints and preservation

The repository search found no self-check root/script-specific assertions in `pipeline/tests`; unrelated road-surface evidence-path tests do not consume these W/S/H constants. No test changes or test runs are needed for four path-literal substitutions. If implementation discovers an additional executable/test consumer not found here, stop and reconcile its exact requirement rather than broaden the patch silently.

Historical `dispatch-supervision-plan.md` describes the original parent/leaf and one-shot hardcoded-helper contract. Later failure/path/ownership plans, dispositions, reviews, ledger and checkpoint preserve original/retry-1 facts. **Do not bulk-replace them** or invalidate frozen history. This new plan and the coordinator's next disposition record the new active slot; coordinator alone updates current metadata after dispatch/review. Preserve the parent-before-leaf ordering that earlier reviews required, the fixed nonnumerical helper modes and no arbitrary command/import/path options.

## Ordered static/review gates

1. Coordinator reconciles this exact W/S/H path-only scope under disposition 64; no implementation or attempt reservation follows this plan by itself. Luna edits the four literals only. Keep the retry-2 root absent and all prior evidence untouched.
2. Rehash final W/S/H and unchanged P/protected files/prior evidence. Run only affected authorized static gates: Ruff check/format for changed S/H (P evidence may be reused if its hash remains pinned), and PowerShell AST parse without W invocation. Unchanged C# compile-only evidence from the accepted literal correction may be reused with exact declarations unchanged; if compilation is repeated, call no interop methods. Do not test/evaluate operational paths, import scripts, create dummy evidence or execute W/S/H.
3. Independent non-implementing Sol review must inspect actual bytes and each path table row above, not just syntax. Strong minimal-delta proof: in-memory text-only reversal of W's two root substitutions and S/H's single substitutions must recover the three baseline hashes in this plan, without writing/executing reconstructed source. Verify P/protected/prior evidence unchanged and retry-2 absent.
4. Review refusal cases statically: W changed but fallback/S/H stale; old-root caller/handoff presented to new path; root already present; stale caller/pending/fallback/handoff/consumed/start/run; absent parent versus leaf ordering; exact destinations with unchanged schemas/nonce/native identity; arbitrary path/automatic slot selection. None may bypass refusal/ownership. Check all current CreateFile `u` suffixes and recent owner/handoff fixes remain byte-identical apart from necessary path strings.
5. Require independent PASS and coordinator gate acceptance before one self-check. FIX_REQUIRED returns to bounded correction/review under disposition 64; no operational run occurs until PASS. Static PASS is not evidence of timing/native/persistence/containment success.

## One-shot execution boundary and blockers

After plan implementation and independent PASS, disposition 64's serial authority permits exactly one wrapper-driven self-check for this bound slot through the existing reviewed W command/mode. Coordinator verifies absent/safe retry-2 and protected old evidence immediately before invocation. The existing W → approved venv launcher → base interpreter → S → H chain, suspended assign-before-resume, authenticated nonce/native PID/creation/image checks, inner/outer Jobs, cleanup/termination/exit recording and sticky persistence failure remain unchanged.

The fresh invocation has its own original **10-second total QPC budget from W start**, not extra time for a retry. Preserve self-check's fixed nonzero-helper and bounded contained tree probe behavior. Do not reset a clock, increase cap, ignore unavailable termination evidence, or infer a PASS from file presence. Native/OS scheduling, actual persistence and containment remain unmeasured by this plan. The separate 30-second runtime profile remains unmeasured and unauthorized.

There is no identified source/schema/path blocker beyond coordinator reconciliation of this minimal W/S/H scope and the required review. Stop if retry-2 is occupied/unsafe, another hardcoded executable consumer appears, any change beyond four path literals is needed, or the next actual self-check fails. Preserve all evidence and plan/review the next defect before another invocation; no new slot is inferred or created automatically. No code/evidence migration, cleanup or attempted reuse of consumed slots.

No collection/verification, manifest preparation, GIS/numerical work, candidate build/reservation, serving, publication or browser step follows even a self-check PASS without later user instruction. Candidate remains NO-GO/unservable, build 3 unreserved, all historical counters and product/source/geometry/recipe/numerical limits unchanged. No commit/push/merge.

Planning consisted only of static source/document/evidence reads, searches, directory/absence inspection and file hashing, plus writing this one new plan. No code/tests/metadata/evidence edits, parser/compiler/linters/tests/imports, wrapper/runtime/self-check, new evidence directory, manifests or candidate/GIS/numerical/build/browser work occurred. Return to coordinator for reconciliation and bounded Luna dispatch; stop here.
