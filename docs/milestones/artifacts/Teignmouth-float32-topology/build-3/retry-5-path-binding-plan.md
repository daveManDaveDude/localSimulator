# Retry-5 self-check — exact fixed-path binding plan

2026-10-25. Sol plan only under coordinator disposition 102, existing issue `Teignmouth-float32-topology-representation-1`. **Feasible: exactly four literal substitutions in W/S/H.** Proposed sole root is `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-5\`, with fixed `run-1` leaf. Neither is created here. This artifact grants no implementation, reservation or invocation.

## Accepted baseline and authority

Read accepted retry-4 path plan/review, dispositions 88–102, current W/S/H/P and disposition 102's accepted S implementation review. Recalculated current source hashes:

| File | Current SHA-256; required future inverse baseline |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `28c92cc60e38ae23dcf58874eca67b8308b22772eee03b36d69471624fcdb089` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py`, unchanged | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

Disposition 102 SHA-256: `482cb723abd0b36dfc4f3453d263796beba53e8870a45492ce1f705e3f4575e1`. Rehashed reusable retry-4 plan `249ebefbca3a6ffa4a65245e5c543ad12aab506876b7e4be910883a8d2a6e74b` and independent review 20 `960d85541339265c7b952f3d9e8bddf905ca755e707839a992120da56a551630`. Disposition 102 accepts the later S implementation review `selfcheck-direct-fallback-independent-review.md`, reported SHA-256 `bd74dc0b7fe5bfa82df604bc7ee3b5b3c57554be3a2cc02e3a6802faabc7131d`; that review and current source were read. Its PASS covers static console/stdio/error behavior, not operational efficacy or runtime fit.

The S inverse must restore **this current S**, including disposition 92's console policy, dispositions 94–95's confirmed stdio release/suspended-child cleanup, dispositions 96–101's bounded secondary-note persistence and immediate fixed fallback. It must not restore retry-4's pre-correction S `64bf…` or another older hash. Historical unsaved/untraceable `957157…` S remains unresolved; the new inverse does not reconstruct it. Outer observed exit 1 versus internal recorded exit 2 remains separate and unchanged.

## Point-in-time path observations and future refusals

Read-only observations in this turn:

- `Test-Path -LiteralPath` returned false for the exact retry-5 parent.
- Force enumeration of `.codex` found zero case-insensitive equal names and zero equal names after trailing-space/dot normalization. No matching retry-5 file/directory was found. With the parent absent, its fixed descendants are absent through that parent.
- `C:\`, `C:\vibe`, `C:\vibe\localSimulator` and `.codex` are existing directories without ReparsePoint; LinkType/Target were empty. Resolve-Path returned exactly their expected canonical spellings. The fixed proposed child is within the inspected workspace `.codex` directory.

These observations neither reserve a path nor guarantee against replacement. Repeat exact absence, force case-insensitive/normalized alias checks, canonical containment and ancestor directory/reparse checks at implementation handback, independent review and immediately before any later separately authorized invocation. Access errors, ambiguous aliases, changed ancestors, reparse points, unexpected file types, an occupied root (even empty), stale pending/fallback/consumed files or unreadable checks are refusal. No adoption, deletion, cleanup, automatic next number, alternate slot or old-root fallback.

No directory is pre-created during planning, implementation or review. Only the later one-use coordinator-gated W invocation may perform its existing exclusive parent creation. S alone exclusively creates `run-1` after authenticated handoff and leaf-absence checks. Preserve W's existing fixed-parent/descendant checks (1203–1225), reparse validation, exclusive caller/stdio/hand-off creation and ownership checks; exclusive creation remains necessary against races. Root creation is not itself a separate preparation phase.

## Four changes, counts and inverse proof

Search of current executable scripts/tests/configuration found exactly these active retry-4 root literals. No test/config or P edit is required.

| Exact consumer | Old literal | New literal | Count |
| --- | --- | --- | --- |
| W line 23, self-check `$baseEvidence` | `.codex\build3-supervisor-selfcheck-retry-4` | `.codex\build3-supervisor-selfcheck-retry-5` | 1 |
| W line 344, independent fallback `$expectedRoot` | `.codex\build3-supervisor-selfcheck-retry-4` | `.codex\build3-supervisor-selfcheck-retry-5` | 1 |
| S line 39, `SELF_ROOT` | `.codex/build3-supervisor-selfcheck-retry-4` | `.codex/build3-supervisor-selfcheck-retry-5` | 1 |
| H line 17, `EVIDENCE` | `.codex/build3-supervisor-selfcheck-retry-4/run-1` | `.codex/build3-supervisor-selfcheck-retry-5/run-1` | 1 |

After separate plan PASS, coordinator acceptance and implementation release, replace only those four spans, preserving all other bytes, encoding/BOM/newlines and formatting. Final occurrence proof: two new parent literals in W, one new parent literal in S, one new full leaf literal in H; zero active retry-4 root literals in these files. P remains byte-identical. Search executable/test/config consumers again; unexpected additional consumers are a stop, not permission to edit more files. Historical docs/evidence retain historical literals.

For independent proof, reverse only those new exact byte spans **in memory**, without writing or executing reconstructed files. Required inverse W/S/H hashes are the first three complete hashes in the baseline table; unchanged P must retain its fourth hash. The inverse proves preservation of current accepted behavior, rather than relying on an unavailable Git index baseline for untracked operational files. No prospective final hash is claimed by this plan. Handback records actual final/inverse hashes, old/new counts and exact changed spans.

## Producer/consumer contract

| Fixed authority/path after substitution | Required agreement and unchanged checks |
| --- | --- |
| W parent caller | Retry-5 `caller-invocation.json`, owned `.update`; fixed caller schema/mode/wrapper PID/start identity, regular canonical destination, same-directory replacement, stale/unowned update refusal. |
| W terminal failure fallback | Retry-5 `caller-invocation.failure.json`; the separate line-344 allowlist must agree with line 23. Exclusive failure-only terminal write; no overwrite/adoption, no persistence failure to PASS. |
| W → S handoff | Parent `self-check-handoff.json`, `.update`, then `self-check-handoff.consumed.json`; unchanged separate Handoff validator, PREPARED snapshot/hash, mode/path/nonce/wrapper/start/deadline/launcher identity and verified suspended-launcher transition. Caller restrictions remain caller-only. |
| Parent startup/stdio | Parent `supervisor-script-start.json`, `supervisor.stdout.log`, `supervisor.stderr.log`; W and S `_startup_record_path`/`_handoff` derive the same parent. Handoff/start precede initially absent leaf creation. |
| S-owned leaf and persistence | `SELF_RUN = SELF_ROOT / "run-1"`; S `_selfcheck` (3616 onward) creates it exclusively. Existing `invocation.json` and `.pending`, normal completion/census/member diagnostics/checkpoints/errors retain names/schema/ownership. |
| S ↔ H authorizations | Leaf nonzero/tree-root authorization files and matching `.consumed.json` files; native launcher/interpreter/creation/hash/nonce/QPC bindings and H consumption remain exact and one-use. |
| Helper starts/markers/logs | Same leaf for nonzero/tree-root script-start, nonzero-helper, tree-root-started/tree-child-started and fixed nonzero/tree stdout/stderr files. H's EVIDENCE agrees with all S SELF_RUN derivatives. |

Generate fresh nonces, identities, absolute clock bindings and payload paths only during a later authorized invocation using existing code. Do not copy old records, hashes, timestamps, authorizations or outcomes into retry-5. No manifest/identity collection, reservation snapshot or new record/schema/filename/mode/phase is added.

## Preservation

Preserve all bytes under `.codex/build3-supervisor-selfcheck/` and retry-1/2/3/4: records, updates/pending, consumed authorizations/handoffs, starts, markers and logs (including empty files). No replay, reset, repair, copying, promotion, deletion or retrospective PASS. The accepted inventories contain **2 + 2 + 11 + 11 + 11 = 37 files**, referenced by original/retry-1 matrices in dispositions 56/63 and review 19; retry-2 disposition 67/review 19; retry-3 disposition 78/review 19; retry-4 disposition 89's complete eleven-file matrix. This turn did not open, enumerate recursively or rehash old-root contents and makes no new claim that their contents were independently reverified. Preserve the accepted matrices as immutable source records.

The inherited path-plan preservation gate requires a complete all-file name/count/hash comparison against those accepted matrices at the later implementation handback and independent review, **if expressly included in coordinator's release**. It is read-only preservation verification, never permission to create/modify evidence. If that comparison is not authorized, report the missing gate and stop before invocation; do not imply an unperformed comparison passed. Anchor hashes alone cannot replace the full matrix. No old-root content hashing was needed to establish retry-5 absence or four literal counts in this planning turn.

Keep protected candidate/topology/builder/test/fixture/config bytes at their accepted bindings in review 20; no code outside the four path spans changes. Preserve W unsigned access DWORDs, caller-versus-handoff ownership, native process identity, suspended Job assignment-before-resume, one-use/cleanup/deadlines, secondary persistence errors/fallbacks. Preserve current S's two console-inheritance opt-ins (normal 3768/3777 and tree 4030/4039), lazy fail-closed finite current-console query, three default callers (4361/4680/4778), stdio close confirmation, suspended-child cleanup, bounded message-note serializer and immediate literal return on failed `str(exc)`.

Retain authenticated actual exit7/7, authoritative complete accounting/PID capture, unconditional sticky unexpected-member rejection including conhost, diagnostic-only retained-handle facts, complete zero/empty/zero before deliberate tree probe, all tree containment/timeout/termination gates and original total deadline. No conhost allowlist, disappearance override, count subtraction, late/forced-cleanup-to-PASS, new native policy or atomicity/mapped-image claim. Runtime console efficacy, cleanup/persistence, 10-second fit and 30-second runtime-profile fit remain unmeasured. Source/origin/domain/recipe/geometry/numerical/geographic/product constraints, synthetic behavior and pending AOI status remain unchanged.

## Static gates and independent reviews

Nothing below is executed in this plan. After independent plan PASS and coordinator release, Luna performs only the four path edits and approved static checks:

- From `pipeline/`, existing `.venv/Scripts/python.exe -m ruff check scripts/run_teignmouth_float32_build3.py scripts/teignmouth_build3_supervisor_selfcheck.py` and corresponding `-m ruff format --check` for these two files. No unrelated reformatting.
- PowerShell AST parse of W only, using `System.Management.Automation.Language.Parser.ParseFile` and checking its parse-error output; never dot-source, invoke W or call its methods. Record the exact parser command/executable/results. An unchanged embedded C# block needs no new compilation; reuse pinned evidence.
- Static byte-count/in-memory inverse proof, cross-file derived-path review and protected-source/evidence preservation comparison under the explicit release; repeat root/alias/ancestor absence checks without creating a probe file.

Handback reports exact final W/S/H/P hashes, inverse W/S/H hashes, counts/spans, exact commands/results and preliminary failures, protected bindings, complete authorized preservation matrix result and point-in-time root checks. No tests/imports, wrappers, operational scripts, process probes or runtime actions are part of these gates. A Ruff command is a specifically released static tool gate, not authorization to import S/H or execute their modes.

| Independent non-implementing Sol review criterion | Required proof |
| --- | --- |
| Plan authority | Disposition 102/current baseline, exact retry-5 only, independent plan PASS and coordinator implementation release; no implied run authority. |
| Exact delta | Four spans only; 2/1/1 new literal counts, no active retry-4 literal, exact baseline inverse hashes, unchanged P/protected files and no changed behavior. |
| Paths/ownership | Every producer/consumer row traced; fallback independent allowlist updated; fixed parent-before-leaf handoff/start, disjoint Caller/Handoff validation, owned update and exclusive terminal fallback intact. |
| One-use/safety | Retry-5 and all observed aliases absent; canonical directory ancestors/no reparse; occupancy/stale/unsafe/inaccessible path refuses; no adoption or alternate numbering; no root created during patch/review. |
| Current accepted semantics | Console/stdio/error implementation from disposition 102 unchanged; suspended native chain/Jobs/deadline/cleanup strict; no unexpected-member exemption or relaxed zero/empty/zero/tree gate. |
| Preservation/static evidence | Required affected Ruff/AST/inverse checks pass against final bytes; full authorized 37-file comparison and protected hashes match accepted matrices; no evidence edits or fabricated checks. |
| Invocation separation | Review PASS remains static only; fresh coordinator one-use gate required; original 10s total QPC deadline; no downstream build/collection authority. |

Plan reviewer and later code reviewer inspect actual bytes/evidence independently; the implementer cannot approve its own patch. Stop for any review finding, baseline drift, more than four required edits, inverse mismatch, unaccounted consumer, protected/evidence mismatch, unavailable preservation check, alias/collision/ancestor ambiguity, or a needed behavior/schema/command/environment/API/deadline change. Do not broaden the path correction or select retry-6 automatically.

## Separate eventual one-shot boundary

Required sequence: independent Sol plan review → coordinator acceptance/release → Luna four-span implementation/static handback → independent Sol path implementation PASS → coordinator repeats exact source/root safety checks and records a **separate one-use gate**. Only that future gate may authorize W's fixed self-check invocation and its exclusive creation of retry-5, with S's own `run-1`. No root creation or wrapper execution occurs before that gate.

Any eventual self-check retains the original inherited **10-second total QPC** deadline, exact reviewed commands/environment, Jobs, cleanup and persistence semantics. One invocation only; preserve actual outer/internal results and all generated evidence, including refusal/non-PASS, consume the slot, then stop. A future result cannot retroactively pass retry-4 or resolve prior unknown PID ownership or outer exit/provenance discrepancies. Any further defect requires a bounded plan/review/gate; this document authorizes none now.

No collection/verification/preflight/runtime identity/manifests/GIS/numerical/candidate build/reservation, serving/publication/browser, commit/push/merge or dependent phase before or after a self-check follows from this plan. Candidate stays NO-GO/unservable; build 3 unreserved. All historical used/consumed counters persist.

Planning work consisted only of static document/source reads/searches, source/document hashing and parent directory/path/alias/ancestor inspection, plus writing this single artifact. No source/tests/evidence/checkpoint/ledger edit, root creation, old-root content hashing, parser/linter/compiler/test/import, process inspection/probe, wrapper/self-check/runtime or operational script was run. Return plan SHA-256 and stop for independent plan review/coordinator acceptance.
