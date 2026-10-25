# Teignmouth Unicode safety and timing qualification

**Status:** Phase 1 initial implementation submitted for independent safety review on 2026-10-24. Checks pass; Phase 2 is stopped because legitimate successful-path and receipt/approval prerequisites remain absent. Activation remains false.

## Authorization and preserved baseline

The user explicitly authorized resetting the retry budget in a new issue to fix the Unicode allocation bound and resolve timing. This new issue does not rewrite or replenish counters/reports from prior issues. Preserve the 2 km viewer, source data, current preview/default, AOI pending status and TQ1 4HN center; preserve all consumed trial inventories and the disabled transition. No geographic/source changes, candidate trial, activation, publication or browser work is authorized by this specification.

Keep the v2 deadlines (T0+120 s input/preparation/solver, T0+125 s complete offline validation, T0+135 s finalization), the complete projected threshold <=125 s, 2,000 iterations, all twelve gate calculations, 64 MiB memory ceiling, source provenance, resource/numeric/geographic constraints and trial order unchanged.

## Phase 1 — Unicode allocation-bound safety fix

The correction review found that `value_bound()` reserves six bytes per Unicode code point, while canonical JSON with `ensure_ascii=True` encodes a non-BMP code point as two six-byte surrogate escapes. The estimate can therefore understate an admitted source/OSM string. No actual memory overrun was observed; the memory bound is simply unproven.

Keep canonical JSON serialization and its 64 MiB ceiling unchanged. Use an allocation-free bound of 12 bytes for each non-BMP code point and six bytes for every other code point, including quotes/escaping allowances and structural overhead. Apply it consistently to strings, Paths, mapping keys and nested values. Keep `ensure_ascii=True` explicit. Reject an over-budget envelope before canonical encoding, decoding, process launch or asset allocation.

Expected files:

- `pipeline/torquay_pipeline/road_surface_validation_process_v1.py`
- `pipeline/tests/test_teignmouth_validation_process.py`
- `config/road-surface-teignmouth-topology-transition-v2.json` (current extension hash pins only)
- this issue specification and `.codex/torquay-plan-implementation.md`
- new immutable test/preservation/review records under `docs/milestones/artifacts/Teignmouth-unicode-timing/`

Tests cover ASCII, JSON controls and quoting, BMP, combining sequences, non-BMP emoji and U+10FFFF, lone surrogates, nested arrays/maps, mixed key types and Paths. For bounded small fixtures, compare the estimate against the exact canonical byte count. Include a 64 MiB boundary regression with non-BMP input proving rejection before encoding/decoding/backend launch. Do not relax other per-field, transfer or peak-memory limits.

Acceptance: focused process protocol/lifecycle and transition tests pass; Ruff check/format, static code-map pins and `git diff --check` pass; preservation records show no source/release/preview/consumed-trial changes; independent Sol safety review PASS. Existing replacement containment evidence may be reused only after hash-bound confirmation that process lifecycle and probe implementation are unchanged. No new probe or retained replay is part of Phase 1.

## Phase 2 — legitimate timing qualification prerequisites

The current repository has no retained witness that passes the gates into `studyAssemblyAndResources`, and no exact production review/acceptance receipts for the new configuration. Existing retained witnesses fail the offline gates. Thus there is no legitimate successful assembly/validation/finalization path or successful production receipt-preflight input to time.

A retry-budget reset does not create those inputs or change approval/trial order. Do not fabricate receipts, force a gate pass, use a synthetic/accepted-preview fixture as a production candidate, or retry a consumed trial. Do not build a full replay harness until the following are resolved through a separately reviewed bootstrap specification:

1. A legitimate successful witness with compatible source, mesh and solver provenance, obtained without retrying consumed trials.
2. An authentic, accurately scoped review/acceptance receipt that can be verified before activation without being mislabeled as the full qualification PASS receipt.
3. A staged approval sequence that breaks the receipt/qualification cycle while preserving trial order, write-once controls and activation=false.
4. A separately explicit execution budget for any solver/trial/replay required to produce this evidence.

The Sol plan found none of the above currently exists. If an existing compatible witness/receipt bundle is supplied or found through read-only inspection, review its provenance and exact hashes before defining any replay. If not, ask the user to approve the bootstrap sequence and its exact execution allowance before implementation or trial dispatch.

Only after all prerequisites pass may a later authorized stage run at most one implementer and one independent retained profile, each externally capped at 135 s. Require exact all-twelve-gate reference equivalence, genuine double assembly and independent asset validation, resource/hash/preservation/serialization/fsync/finalization accounting, real receipt-preflight cost, and complete projected end-to-end duration <=125 s in both environments. A timeout, incomplete gate, preservation/resource/protocol mismatch or duration >125 s stops the issue. No candidate acceptance or activation follows automatically.

## Fresh finite budget and roles

- Phase 1: one initial Sol 6.1 / medium implementation and at most one Sol correction; zero Luna corrections; one independent Sol review per submission. The user reset applies only to this new issue. Preserve the previous issue's spent counts.
- Phase 1 uses zero containment probes, solver runs, candidate trials, retained profiles/replays, activation or browser runs. Reuse the previously passing containment probe only if lifecycle bytes are unchanged and verified against its artifact hashes.
- Phase 2 has no execution budget yet. The one implementer and one independent profile ceilings above are proposed only for a future explicitly authorized stage; no probe/trial/solver allowance is presently granted.
- Independent reviewer: `/root/review_sol_escalation`, which did not implement the prior issues. Actual runtime model/effort is unknown unless exposed.

If Phase 1 correction review fails after its single correction, stop with NEEDS_USER_DECISION. If Phase 1 passes but Phase 2 prerequisites remain absent, stop after the safety fix and present the exact bootstrap decision/artifacts needed. Activation remains disabled throughout.

## Phase 1 initial implementation handback — 24 October 2026

The initial implementation fixes the known non-BMP bound. `json_string_bound()`
counts six bytes per BMP code point (including lone surrogates), twelve per
supplementary code point, and two enclosing quotes, without constructing an escaped
buffer. Strings, Paths, dictionary keys/nested values and dataclass field names all
use the bound while retaining structural/tag overhead. `canonical()` explicitly
sets `ensure_ascii=True`; its serialized bytes are unchanged. The 64 MiB ceiling,
all numeric/geographic/source gates, timing offsets and trial order are unchanged.

Targeted regressions cover ASCII, controls/quoting/backslashes, BMP/combining text,
non-BMP emoji, U+10FFFF, lone surrogates, mixed-key/nested structures, Paths and
an actual allowlisted mesh record. Small fixtures compare the bound with canonical
encoded bytes. The production-ceiling boundary test constructs only a roughly
5.4 MiB source string: the old six-byte estimate would fit, while the corrected
four-envelope reservation exceeds 64 MiB. Spies fail if canonical/codec encoding,
decoding, sidecar transport, asset assembly or backend launch occurs before rejection.
No large escaped JSON or worker allocation is produced by that regression.

Actual checks: **129 passed, 1 skipped in 3.46 s**. The skip is the unchanged Windows
directory-symlink privilege limitation, WinError 1314. Ruff check/format passed for
both changed code/test files; diff check passed with the existing checkpoint
LF/CRLF warning. `quality-checks-phase1-initial.json` records exact commands/cwd,
outputs, durations, exit codes and environment. Requested model/effort is
`gpt-6.1-sol` / `medium`; actual runtime settings are not exposed and are unknown.
Issue usage is unavailable.

The passing replacement containment report is reused, not rerun.
`containment-evidence-reuse.json` verifies byte-identical `ProcessStartupError`,
`WindowsJob`, `wait_worker` and `supervise` source regions, the exact probe script
hash recorded in its attempt artifact, and the reviewed passing report hash.
The whole process-module hash changes because the estimator changed; no claim is
made that the old whole-module hash matches current bytes. Probe/lifecycle identity
and new Unicode safety tests support separate, explicit evidence reuse.

Only the process module, its test file, current transition extension pins, this
new issue document and checkpoint changed. Exact before-images and hashes for all
five files are in `.codex/history/2026-10-24-unicode-timing/initial-before/manifest.json`.
The old issue and its evidence/history remain byte-for-byte unchanged. One static
pin was already stale before this implementation: the old issue document's appended
correction review changed it from `8af0f4a0495280575e77227f2a75e80031134971755c31cdcdcc452c9233f1b6`
to `c338472a4889808bb00017575035d264f673c5fd5eddcb27496ce2936138ac20`.
`preexisting-pin-drift.json` preserves that observation. The current extension map
explicitly binds those existing current metadata bytes alongside the two new code/test
hashes; no old config snapshot, old document or historical evidence was rewritten.

New immutable evidence lives in `artifacts/Teignmouth-unicode-timing/`:
`quality-checks-phase1-initial.json`, `containment-evidence-reuse.json`,
`phase2-prerequisites.json`, `preservation-phase1.json` and `phase1-manifest.json`.
Static maps and protected-source/release/preview/consumed/old-issue preservation
checks are recorded there. No source/GIS/package bytes were changed.

Read-only inspection found all five retained offline aggregates fail and lack
successful assembly. Both exact production approval receipt files remain absent.
Therefore Phase 2 is not executable: a genuine compatible all-gates-successful
witness, real successful assembly/validation/finalization evidence, authentic
preflight receipt artifacts, and a separately reviewed staged approval sequence
with explicit execution allowance are still missing. No bootstrap/receipt amendment
or replay harness was implemented. No probe, solver, trial, retained replay/profile,
candidate build, activation, browser/publication or commit ran.

- [x] Archive exact five-file before-images.
- [x] Implement Unicode sizing and targeted preallocation regressions.
- [x] Run affected quality gates and verify hash-bound containment evidence reuse.
- [ ] Obtain independent Sol Phase 1 safety PASS.
- [ ] Resolve Phase 2 legitimate witness/receipt/authorization prerequisites.

Initial implementation submitted; zero Luna corrections, `sol_fix_used=false`,
`sol_fix_reserved=false`; at most one Sol correction remains in this fresh issue.
Prior issues' spent budgets and reviews remain historical. Next action: independent
read-only safety review by `/root/review_sol_escalation`; stop before Phase 2.
Browser not run: this is an offline safety fix, with product bytes preserved.

## Phase 1 independent review — 24 October 2026

**PASS for Unicode safety only.** Independent artifact:
`artifacts/Teignmouth-unicode-timing/independent-sol-review-phase1.json`, SHA-256
`ac5b8ea4653fd4bddccb54bd347942dfcedaaf225fcf5584436630c8b797193a`. Review
verified the non-BMP bounds, pre-allocation rejection order, unchanged 64 MiB/timing
limits and pins, preservation, and reuse of containment evidence against unchanged
lifecycle/probe bytes. The recorded focused suite passed 129 tests with one existing
Windows privilege skip; no tests or probes were rerun by the reviewer.

This PASS does not qualify Phase 2 timing. The five retained witnesses fail offline
gates; no exact production receipts or successful assembly/finalization evidence is
available. The next action is a read-only Sol proposal for a legitimate staged
approval/evidence sequence. No bootstrap implementation, replay, trial, solver or
activation is authorized until the required sequence and exact execution budget are
reviewed and explicitly authorized.