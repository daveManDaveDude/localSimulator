# Teignmouth Unicode safety and timing qualification

**Status:** Fresh issue authorized 2026-10-24. Phase 1 Unicode safety implementation is ready to dispatch. Phase 2 timing qualification is gated on a legitimate evidence and approval sequence; no trial or activation authority is implied.

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