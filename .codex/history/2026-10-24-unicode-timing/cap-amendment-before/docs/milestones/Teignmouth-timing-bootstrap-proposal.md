# Teignmouth timing qualification bootstrap — draft for user decision

**Status:** Proposal only; no approval, configuration change, trial, replay, solver or activation is authorized by this document.

## Why a bootstrap stage is needed

Phase 1 of `Teignmouth-unicode-timing.md` received independent safety PASS on 2026-10-24 (`docs/milestones/artifacts/Teignmouth-unicode-timing/independent-sol-review-phase1.json`, SHA-256 `ac5b8ea4653fd4bddccb54bd347942dfcedaaf225fcf5584436630c8b797193a`). The process containment evidence also passed its single replacement probe. The v2 validation transition remains disabled.

The repository contains no retained witness that passes all offline gates into successful `studyAssemblyAndResources`, and no exact production review/acceptance receipt pair for the current transition. Existing `flip-05` and `road-05` attempts are consumed and must not be retried. `collar-05` is the next unused trial identifier, but this does not authorize it. Current production verification expects a full enabled-config review/acceptance chain before trial execution, while the full timing qualification requires a successful path that the failed witnesses do not reach. Synthetic success flags, fabricated receipts and accepted-preview assets cannot close this gap.

## Existing receipt semantics and timing boundary (BP-1)

The existing receipt schemas **do not assert completed timing qualification**.
`_approval_payload()` contains only `transition_id`, config path/hash, spec path/hash,
full runtime code map and its canonical digest. The exact Sol dictionary adds
`schema="teignmouth-validation-v2-sol-review-v1"`, `reviewer="Sol 6.1"` and
`disposition="PASS"`; the coordinator dictionary adds
`schema="teignmouth-validation-v2-coordinator-acceptance-v1"`,
`disposition="ACCEPTED"` and the Sol artifact path/hash. There is no
`timing_qualified` field. Additional fields would fail the verifier's exact dictionary
comparison. Therefore a new readiness/PASS receipt schema is unnecessary: the genuine
existing pair can truthfully approve an exact implementation/config/spec for the
single evidence trial **if the user first approves that narrow bootstrap exception
and the signed specification explicitly records that timing remains unqualified**.
The review must genuinely pass that exact limited contract; signing cannot itself
invent permission or waive an existing unmet criterion.

The blockers in the unchanged current contract are specific. In
`ensure_transition_activated()`, `activation.enabled=false` immediately raises
"validation transition v2 is disabled pending exact Sol review and coordinator
receipt" before reading either receipt. The v2 specification's Remaining-trial
policy requires both <=125 s profiles; its Exact approval chain requires an enabled
review config before a future trial; its Evidence section says the transition stays
inactive until both profiles meet the limit and independent review passes. These
are activation/order and qualification prerequisites, not a timing assertion hidden
in the receipt schema. No existing unchanged route admits Stage B with live
activation=false. A narrowly authorized evidence-only entrypoint and bootstrap
exception to those trial-before-qualification prerequisites are still required.

Propose reusing the existing exact review/acceptance documents and extracting their
unchanged document/hash checks into one shared verifier. Ordinary
`ensure_transition_activated()` must retain its enabled-config and accepted-checkpoint
checks and continue refusing while live activation=false. The evidence-only entrypoint
uses the authentic pair plus a separate one-use user-authorized permit, with the
existing pending marker; it must not invoke or pretend to pass ordinary activation.
No new staged **receipt schema/semantics** or synthetic receipt is proposed.

Stage C times authentic existing receipt-document verification in that evidence-only
configuration, plus its permit admission. It does not measure the entire ordinary
enabled config/accepted-marker path. Stage D must report the precise facts:
`exact_receipt_document_verification_measured=true` only if actually measured,
`ordinary_enabled_preflight_measured=false` and `production_timing_qualified=false`.
No shared-helper or conservative-delta inference makes the later different enabled
config qualified. The original full production timing prerequisite remains open.

Later production must receive a separately authorized exact timing stage with genuine
receipts for its exact production config/spec/code/checkpoint, complete ordinary
preflight measurement and both full projected profiles <=125 s. Fresh review or
re-signing alone is insufficient. That stage is outside this budget; resolve its
exact admission/qualification order in an independently reviewed specification before
execution. Stages A-D grant neither production timing acceptance nor activation.

## Proposed stages

### Stage A — genuine existing approval pair and one evidence-only permit

After explicit user approval of the one-time trial-before-qualification exception,
implement a versioned `qualification_evidence_only` entrypoint. Keep ordinary
production/activation behavior unchanged and fail-closed. Its real documents are:

1. `docs/milestones/artifacts/Teignmouth-topology-validation-v2/independent-sol-review.json`:
   genuine independent PASS for the exact reviewed evidence-only implementation/config
   and approved specification. Use the existing schema/fields listed above, unchanged.
2. `docs/milestones/artifacts/Teignmouth-topology-validation-v2/coordinator-acceptance.json`:
   genuine exact coordinator ACCEPTED binding that pair's config/spec/runtime map and
   the Sol artifact byte hash, using the existing schema unchanged.
3. `docs/milestones/artifacts/Teignmouth-unicode-timing/bootstrap/coordinator-evidence-permit.json`:
   a separate one-use authorization record, not a replacement production receipt.
   Bind `scope="qualification_evidence_only"`, schema/purpose/disposition, exact approved
   bootstrap-spec/config/runtime hashes, source/release/preview maps below, frozen
   station/offset union, consumed-inventory and protected-map digests, the two genuine
   receipt hashes, `trial_id="collar-05"`, `maximum_attempts=1`, exact raw directory,
   all fixed timing/iteration/resource constants, `timing_qualified=false`,
   `production_timing_qualified=false` and `activation_allowed=false`. Include the
   actual user-authorization evidence reference/hash; the coordinator cannot create
   authorization by merely writing a permit.

The exact receipts bind the approved v2 specification with its explicit one-trial
bootstrap exception; no signer can silently reinterpret the unchanged current spec.
Live activation stays false and the pending checkpoint marker stays present; no
ordinary accepted marker is written. The shared receipt-document verifier checks
all original schemas/paths/hashes/maps. The evidence entrypoint then checks the
additional one-use permit, stage order and path guards before trial creation.
Ordinary execution still checks activation and its accepted marker as before.
Actual future implementation/config/pair/permit hashes do not exist yet; freeze and
independently review their real values before dispatch. Do not substitute placeholders.

Independent review must verify scope separation, exact one-use permit, existing
reconciled stage order/input transition, write-once and path guards, bounded cleanup,
unchanged solver/gates/resources, complete Stage B timestamp/reference instrumentation
and the disjoint Stage C accounting below. It must check representability of the
actual source-bound worker request within the unchanged 64 MiB accounting before
spending the trial: input source file sizes are not themselves a proof of transport
or construction feasibility. A readiness resource failure stops without changing a
limit. Ordinary production/activation paths must still refuse the false activation state;
the one-use permit never enables them.
Only after readiness PASS and an exact coordinator permit may Stage B begin.

### Stage B — one genuine evidence-only trial

If authorized and Stage A passes, run exactly one `collar-05` solver attempt in `.codex/evidence/teignmouth-topology-study/collar-05/` using its existing ten-file contract and an exclusive write-once marker. This is a candidate trial and solver run. It is included here solely to obtain a genuine successful witness for timing measurements; it cannot accept or activate a candidate.

The exact candidate scope and hash pins below are part of the proposed authorization;
"current settings" cannot substitute for them. Stage B must keep:

- One 84 x 82 m domain: 42 columns x 41 rows of original 2 m cells, first column
  409, first row 432; local X [-182,-98] m, Z [-136,-54] m. No expansion.
- Teignmouth Road OSM way 78455395, part 0, stations 140-155 m, full estimated
  6 m width; anchor station 148.15104603556912 m at local
  X/Z [-139.6017351396,-95.8223807515]. Preserve the original longitudinal hump.
- Same road-aligned core and deformation influence, conforming collar scales
  0.5 -> 1 -> 2 m, same exact accepted 2 m outer perimeter, source planes outside
  deformation, <=32 m shoulder transition measured from the ribbon edge and
  unchanged along-road fade. No removed station/offset samples or fixed nodes.
- Frozen <=1 m station union (source vertices, integer/control/fallback stations and
  anchor), full-width <=0.25 m offsets, all 439 severe-station controls, both Parkfield
  controls and seven full-way longitudinal profiles. Freeze the exact generated
  ordered union/offset values and digest before readiness/dispatch using the pinned
  `mandatory_corridor_station_union()` contract; the values/digest are not guessed
  here. Record complete source/accepted provenance; refinement is not new measured
  elevation data. All 3,613 complete building footprints remain included.
- Existing numeric arithmetic/headroom, not just rounded public limits: local lateral
  slope <=5%, span <=0.30 m, source centerline deviation <=0.10 m, signed grade change
  <=2 percentage points; strict source earthwork <5 m and positive added gradient
  <1 m/m; building p95 <=0.183 m, max <=2.424 m and Newton legacy +/-0.05 m;
  road drape <=1 mm with +0.05 m offset, barycentric tolerance <=1e-6 and unchanged
  area/Float32 ownership rules; walk clearance 1.70 +/-0.05 m. The pinned patch
  implementation's tighter numeric constants (e.g. 4.999 m, 0.999 m/m, 2.4239 m,
  0.0999 m, 0.0199 m/m and 0.2999 m) are unchanged. All twelve gates remain mandatory.
- At most 2,000 iterations, solver tolerance 0.00002 m, one unshifted monotonic T0:
  preparation/solver <T0+120 s; complete validation including assembly/hash/resources
  <T0+125 s; finalization <T0+135 s. Qualification still requires complete projected
  duration <=125 s; the 135 s window is not qualification headroom.
- One patch, replacement terrain-plus-road triangles <=250,000, vertices <=150,000,
  added draws <=4, assets <=8,388,608 bytes, manifest <=262,144 bytes,
  QA <=524,288 bytes, resident geometry <=16,777,216 bytes and construction buffers
  including transfer/temporary/replaced buffers <=67,108,864 bytes. Check before solve
  and after clipping. No automatic resource escalation.
- Existing `validate_reconciled_stage_order()` and the named v2 prior-input/inventory
  reconciliation, not a simplified directory-presence test. Prior flip-05 and road-05
  must retain their complete accepted failure classifications and frozen config/code/
  source maps through the approved exact metadata transitions. Neither may pass;
  collar-05, local-025 and local-0125 output directories must be absent before dispatch.
  Refuse unexpected files, traversal/aliases, reparse points, overlaps and races.
- Exact raw ten-file contract: `attempt.json`, `topology.json`, `constraints.json`,
  `candidate-heights.f32`, `patch-vertices-xz.f64`, `patch-base-heights.f32`,
  `patch-triangles.u32`, `solver-phase.json`, `offline-aggregate.json`,
  `certificate-verification.json`. Keep timing/reference sidecars outside that raw
  directory under the scoped durable bootstrap evidence directory.
- No retry after a dispatched failure/interruption/timeout. No candidate/public
  package, viewer integration, browser, publication or activation. Live activation
  stays false; no ordinary accepted-checkpoint marker is written.

A failed gate, incomplete report, preservation/resource mismatch, worker cleanup failure or timeout stops this proposal. `collar-05` is not guaranteed to pass. Do not proceed to any refinement or use another trial automatically.

### Stage C — complete same-witness evidence-only timing projections (BP-2)

Only a complete, genuinely successful Stage B result unlocks these two runs:

1. One implementer solver-free profile, externally capped at 135 seconds.
2. One independent solver-free profile, same frozen implementation/config/source and
   compatible pinned local machine/runtime/thread environment, also capped at 135 s.

**Required immutable Stage B reference, bound before either profile:** inventory
all ten actual collar-05 files by path/byte length/SHA-256; require the final aggregate's
all-twelve-gate success, `validationComplete=true`, successful independent assembly/
resource checks, exact before/after protected/code/config maps and no public output.
Reference the actual `offline-aggregate.json` and `solver-phase.json`, candidate Float32,
mesh XZ/base/triangles, topology, every constraint row and complete station/offset union.
Bind data-source manifest separately from release-terrain manifest, full release/
preview maps, environment, code/config/spec maps, exact review/acceptance/permit chain, timing ledger
and both independent output-asset hash maps. Profile gate reports compare canonical
bytes for each of the same twelve gates to this **successful collar-05 aggregate**;
flip-05, road-05 and their prior mixed proxies cannot be its substitute. Assembly
outputs must match the genuine Stage B independent output hashes. Do not synthesize
reference values from expected results.

These future hashes, output maps, station lists and measurements do not exist yet.
The exact immutable reference manifest path is proposed as
`docs/milestones/artifacts/Teignmouth-unicode-timing/bootstrap/stage-b-reference.json`;
its byte hash and all actual values must be sealed and independently verified after
Stage B success, before profile admission. Missing bindings stop, rather than become
null/zero timings. Any code/config/numeric/environment change after the reference is
sealed invalidates compatibility; no reusing measurements from another topology.

**Stage B recording boundaries:** retain one external complete invocation duration
`E_B` and actual phase/cutoff outcomes independently of the projections. In a durable
`bootstrap/stage-b-timing.json`, record monotonic timestamps `b0` (before any config/
receipt/input preflight), `bp` (start of target/influence/topology/constraint preparation,
after input/stage checks and exclusive attempt-marker creation), `bs` (immediately
on bounded solver return, before post-solver witness/report/certificate serialization),
`bv` (complete offline/assembly/resource/hash validation finished), and `bf` (final
preservation, aggregate fsync/no-overwrite commit and owned cleanup finished).
Record `E_B=bf-b0` plus external process elapsed separately; neither is a new profile.
The exact solver/preparation interval carried forward is `P_B=bs-bp`: it includes
all target preparation, topology/constraint construction/checks and their real
intermediate evidence IO, and the sole actual solve. It excludes source loading,
receipt/input preflight, attempt-marker creation and all post-solver serialization.
Instrumentation and its hash-bound ledger must be independently reviewed in Stage A;
existing elapsed fields alone may not supply these boundaries. Missing/ambiguous
recording stops Stage C.

**Each replay i uses a single disjoint timing ledger:**

- `A_i`: replay invocation to the restored solver-return boundary. Measure current
  config/exact-receipt-document/permit/path/stage/input/code/protected preflight, source/accepted
  loading and exclusive scratch attempt-record creation, then read/hash/restore the
  exact retained topology/constraints/witness. No target mesh construction or solver
  reruns. Restoring indexes/geometry from retained bytes is additional replay overhead
  charged here, never subtracted or disguised as a new numerical preparation run.
- `V_i`: from that boundary through genuine post-solver witness/mesh/solver-report/
  certificate serialization and checks, worker launch/import/transfer/reconstruction,
  all twelve complete gates, conditional two independent assemblies, both independent
  validations, resource/deterministic hash checks, return transfer and parent verification.
  Include all actual internal assembly validations too; do not invent a fixed call
  count when the production helper validates internally.
- `F_i`: final protected/code/config preservation checks, aggregate serialization,
  exact shared exclusive-write/fsync/no-overwrite commit in owned profile scratch,
  readback/status handling and all remaining owned-worker/scratch cleanup.

Every replay operation belongs to exactly one interval, with no unmeasured gaps.
Use the same production helpers/payload contracts, including a full successful
aggregate and all conditional work, with paths confined to new owned profile scratch;
never create/modify the consumed collar-05 trial. A cleanup operation that actually
occurs within V_i stays there, not counted again in F_i. Report any extra profiling
hash/readback/restore overhead in its real interval without subtracting it. Exclude
out-of-band publication of the profiling report only if it is solely profile machinery;
trial-equivalent aggregate serialization/commit/cleanup is mandatory in F_i.

The complete, explicitly **projected** evidence-only total is:

`E_i_projected = A_i + P_B + V_i + F_i`.

Thus input/preflight/attempt creation is measured only in A_i; historical preparation/
solve is counted only in P_B; all post-solver work is measured only in V_i/F_i.
This is a same-collar-witness, same-code/environment projection, not a newly measured
solve or an actual collar rerun. Reuse of P_B is the precise policy amendment proposed
for user approval; cross-topology/mixed-reference proxies and missing conditional
work remain forbidden. The actual complete Stage B E_B remains separately visible.
No historical road-05/flip-05 preparation or solver duration may replace P_B.

Enforce the original cutoffs on the projected timeline as well as the external cap:
`A_i + P_B <120 s`, `A_i + P_B + V_i <125 s`, finalization <135 s, and
`E_i_projected <=125 s`. A solver-free replay cannot claim the whole 125 s window
as remaining validation time: reserve P_B and already elapsed A_i before worker
admission. Record actual replay wall time and all four components; no shifting T0
or diagnostic cap extension may make a projected late result pass. Both profiles
must independently complete and compare all reports/output hashes. Stop after an
incomplete or >125 s implementer projection; do not spend the independent profile.
No replacement profile is included.

### Stage D — evidence-only qualification; production timing remains outstanding

If and only if both complete profiles pass, produce separate scoped artifacts:

- `independent-sol-qualification.json`: complete same-witness projected timing/equivalence PASS only for the exact evidence-only config, with both profile/reference hashes and `production_timing_qualified=false`.
- `coordinator-qualification-acceptance.json`: acceptance of that timing evidence only; it does not activate or publish.

This is not completion of the original ordinary-production timing prerequisite.
Later production needs separately authorized complete exact production timing
qualification, genuine production receipt verification and its own independent review
and coordinator acceptance, as specified in the scope boundary above. A later different
enabled config/verifier is not timing-qualified by this evidence-only result or by
receipt re-signing alone. Current production receipts and activation guards are
unchanged; no such later production execution or approval-sequence amendment is
included in this budget. Live activation remains false.

## Exact geographic/source/code pins inspected for this draft (BP-3)

Authoritative file SHA-256 values below were computed from actual bytes during this
proposal-only correction. They pin the present baseline, not unknown future bootstrap
implementation hashes. The Stage A review/permit must bind its eventual full extension
map explicitly and preserve all these frozen inputs.

| Exact path | SHA-256 |
| --- | --- |
| `docs/milestones/Teignmouth-topology-refinement-spec.md` | `03bc2ce6e5927307245aa0470cf8cc404838b5517efec5bf5e5db689e74416a1` |
| `docs/milestones/Road-surface-treatment-teignmouth-spec.md` | `12b7c60a827e464c5b02a3413a9c270a9c9909fcd32b0a5f484b8fc64a5c7d92` |
| `docs/milestones/Teignmouth-topology-validation-v2-spec.md` | `16358db4e1dd40349fb9d7550f80e80cbeac4489bb263e56aa7f38949af26b45` |
| `config/road-surface-teignmouth-topology-study.json` | `5c292d2afb43f6f67b83d34a663494a138506bee18ea00d33b61f88569a1a26d` |
| `config/road-surface-teignmouth-candidate.json` | `0616b0584cfc2d9043dd0b0e8c81926a45487e456855ab9375ce0878c6412140` |
| `config/road-surface-teignmouth-topology-transition-v2.json` | `6c685c1746e01786ebe19a027c51235abbfda71fe58e4bc959cb60604964ccf3` |
| `config/aoi.torquay.json` | `205aa50e58e807e0f54f7f74d9f546052da6fca627ae9c3411ec4af334a2a6e5` |
| `data/source-manifest.json` | `e2a5237d99fd8b0b0dd0174430ba18b58f2d778f498275c609c24bed5c3ccf8c` |
| `docs/milestones/artifacts/Road-surface-treatment/teignmouth-topology-study/profiles/consumed-trials-inventory-v2.json` | `9e9c9d083014dd2649fc2b4d284a235423358466b6e91b3d07959c2369f5d8d6` |
| `pipeline/scripts/run_teignmouth_topology_study.py` | `1f33704b6e9103a84429097b0f6c7d153647b7092dac2d7f6e49ec97c46a141f` |
| `pipeline/torquay_pipeline/road_surface_patch.py` | `fb153a57c845fc09bb3c4de4e38b5b713710399a1fb8e444640c223ed443e825` |
| `pipeline/torquay_pipeline/road_surface_study.py` | `e62cd3b1dd597cd67fe4f1dbdbac7613390da15ce67d81ce54cc79c07be24cce` |
| `pipeline/torquay_pipeline/road_surface_study_reconciliation.py` | `f60d62b9ddd95d43e7892c66864643689caa53888454a9eea000e012bc9e113e` |
| `public/worlds/torquay-poc-001-2km/ready.json` | `08399e71ba3a0c6d421982b5cd47973114a48060ddb4c0931378663faf07b3b4` |
| `public/worlds/torquay-poc-001-2km/releases/616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a/inventory.json` | `a66d56fdc38133e0243904dc842f6a79b08c5e3075d73b83515f7c4709c90cb0` |
| `public/worlds/torquay-poc-001-2km/releases/616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a/manifest.json` | `588cbcb682d7e723f915cf627c15c0e641e5adf019b60cfb4d0814caccb90b3a` |
| `public/worlds/torquay-poc-001-2km/releases/616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a/heightfield.f32` | `c61bd03d4172bffb07be596c4f63cc11a0681d0cacd884bb7dfcf3411be815af` |
| `public/worlds/torquay-poc-001-2km/releases/616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a/roads/manifest.json` | `ff6b46acc6ddb667e6d20a0c5d7cd88faebc754e7c7c8dfe76f33fcee5f0e8d6` |
| `public/worlds/torquay-poc-001-2km/releases/616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a/roads/roads.json` | `cd44d5c9aa4f8ef107176b31b86dbfe4ad5f98271ccbcbc5a05d677a38385986` |
| `public/worlds/torquay-poc-001-2km/releases/616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a/buildings/buildings.json` | `8c63da52a578207c2a11afa881fd56524df47e787bf6213d68c77b1784003a58` |
| `public/worlds/torquay-road-surface-preview/manifest.json` | `9a3cb6c08fb57a19f94e1215ac526b1baf28634d38be1ffc7d4ed61f2de7c6f7` |
| `public/worlds/torquay-road-surface-preview/heightfield.f32` | `037a74320557088135e0885386c24fdcdea6171469db1d6329c3e82997f5c1e9` |
| `public/worlds/torquay-road-surface-preview/qa.json` | `43d7058a339416d308be09292598949d3d97f4b764a147ccc2d5fb771d434f20` |

Release ID: `616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a`. The readiness pointer and inventory retain their
normal exact file-descriptor validation; source manifest and release terrain manifest
are distinct identities. The current raw consumed-trial inventory is 2,411 bytes;
recompute/compare every retained flip-05/road-05 file before permitting collar-05.
The whole protected source/raw-EA/current-and-historical-package/preview/default/Site
and accepted evidence-tree maps must be snapshotted and bound before/after the actual
Stage B attempt using the existing tested snapshot methods; future snapshot hashes
cannot be guessed in this draft. Only exact already-reviewed metadata transitions
are allowed; no arbitrary current-map refresh is permission to modify protected data.

The AOI stays `selected_pending_coverage` / `not_checked`, 2,000 x 2,000 m, with
TQ1 4HN centroid longitude -3.536013, latitude 50.477853 and BNG center
[291108.9018176432,65353.48350844931]. No changed source, geometry, coordinate
transform, new measured height claim, geographic approval or TVW-016 authority.


## Proposed finite budget

This bootstrap requires a fresh, separately authorized issue budget because the evidence-only entrypoint, policy sequence and trial are outside the Phase 1 safety fix:

- One initial Sol 6.1 / medium implementation and at most one Sol correction; zero Luna corrections.
- One independent Sol readiness review and one independent post-profile qualification review; keep the reviewer out of implementation.
- Exactly one `collar-05` evidence-only solver/trial attempt, max 2,000 iterations, write-once. No retry.
- At most one implementer profile and one independent profile, each <=135 seconds. No probes or replacement profiles; reuse the already reviewed containment evidence only if exact worker lifecycle bindings remain valid.
- Zero candidate promotion, activation, viewer/browser/publication or source/GIS changes.

This budget is proposed, not authorized. Phase 1's one initial implementation and reviewer PASS remain separate; previous failed issues/counters and consumed trials stay unchanged.

## User decision required

To proceed, the user must explicitly approve (a) the single collar-05 trial-before-
qualification exception and false-activation evidence-only admission path, (b) the
same-successful-collar historical P_B projection rule and the evidence-only timing
boundary, and (c) exactly one write-once trial plus the two bounded solver-free
profiles and proposed implementation/review allowance. No new readiness receipt
schema is required: use genuine existing exact PASS/ACCEPTED documents for the
approved limited spec, plus the one-use permit. No ordinary activation or production
qualification is authorized. If the exception or execution allowance is not approved,
stop after Phase 1. A supplied provenance-compatible successful witness/receipt
bundle would require a separately reviewed revision binding its actual identity;
this fixed collar-05 proposal does not silently admit another reference.
