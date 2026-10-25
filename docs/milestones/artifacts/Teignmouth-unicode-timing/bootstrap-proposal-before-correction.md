# Teignmouth timing qualification bootstrap — draft for user decision

**Status:** Proposal only; no approval, configuration change, trial, replay, solver or activation is authorized by this document.

## Why a bootstrap stage is needed

Phase 1 of `Teignmouth-unicode-timing.md` received independent safety PASS on 2026-10-24 (`docs/milestones/artifacts/Teignmouth-unicode-timing/independent-sol-review-phase1.json`, SHA-256 `ac5b8ea4653fd4bddccb54bd347942dfcedaaf225fcf5584436630c8b797193a`). The process containment evidence also passed its single replacement probe. The v2 validation transition remains disabled.

The repository contains no retained witness that passes all offline gates into successful `studyAssemblyAndResources`, and no exact production review/acceptance receipt pair for the current transition. Existing `flip-05` and `road-05` attempts are consumed and must not be retried. `collar-05` is the next unused trial identifier, but this does not authorize it. Current production verification expects a full enabled-config review/acceptance chain before trial execution, while the full timing qualification requires a successful path that the failed witnesses do not reach. Synthetic success flags, fabricated receipts and accepted-preview assets cannot close this gap.

## Proposed stages

### Stage A — readiness review and one evidence-only permit

After explicit user approval of this proposal, implement a separate versioned `qualification_evidence_only` mode. Keep ordinary production trial/activation verification unchanged and fail-closed. The new mode accepts only these truthful, scope-limited documents:

1. `independent-sol-readiness.json`: independent PASS on the exact evidence-only implementation/config/runtime map and its safety controls. It states `timing_qualified=false` and `activation_allowed=false`.
2. `coordinator-evidence-permit.json`: coordinator authorization for exactly `trial_id="collar-05"`, one attempt, the exact evidence directory, source/release identities and immutable config/spec/code hashes. It references the readiness artifact hash. It states `timing_qualified=false` and `activation_allowed=false`.

A dedicated verifier must validate those schemas and exact bindings only for the evidence-only entrypoint. It must not turn either document into the existing full `independent-sol-review.json` or `coordinator-acceptance.json`, accept them for activation, promote outputs to public/candidate paths, or modify the accepted default viewer. No full success receipt is issued before timing exists.

Independent review of the evidence-only implementation must verify the separate scope, exact one-use permit, stage order, write-once attempt marker, cleanup, unchanged solver/gates/resources, and refusal by all ordinary production/activation paths without full receipts. Only after that PASS and an exact coordinator permit may the evidence-only attempt begin.

### Stage B — one genuine evidence-only trial

If authorized and Stage A passes, run exactly one `collar-05` solver attempt in `.codex/evidence/teignmouth-topology-study/collar-05/` using its existing ten-file contract and an exclusive write-once marker. This is a candidate trial and solver run. It is included here solely to obtain a genuine successful witness for timing measurements; it cannot accept or activate a candidate.

Keep the existing limits unchanged:

- At most 2,000 iterations; existing 120/125/135-second phase windows.
- Existing geometry/solver/gate semantics and all twelve validation gates.
- Existing output/resource ceilings, including 64 MiB construction buffers.
- No retry if the attempt fails, is interrupted, or times out. The identifier is consumed at dispatch.
- No candidate/public package, viewer integration, browser, publication or activation.

A failed gate, incomplete report, preservation/resource mismatch, worker cleanup failure or timeout stops this proposal. `collar-05` is not guaranteed to pass. Do not proceed to any refinement or use another trial automatically.

### Stage C — complete timing profiles

Only if Stage B yields a complete, genuine all-gates-successful immutable witness, run:

1. One implementer retained profile, solver-free and externally capped at 135 seconds.
2. One independent retained profile of the exact same reviewed implementation/config/environment, solver-free and externally capped at 135 seconds.

Each profile uses the actual worker and shared production helpers, and includes complete preflight, receipt verification for the exact evidence-only scope, source/input loading, worker start/transfer/reconstruction, all twelve gates, conditional double assembly, independent asset validations, resource/hash checks, preservation, serialization/fsync/commit and cleanup. Compare all twelve reports byte-for-byte against a compatible immutable reference. No forced passes or mixed proxies.

Both profiles must have complete projected end-to-end time <=125 seconds under the unchanged policy. If the implementer profile is incomplete or exceeds 125 seconds, stop before the independent profile. No replacement profile is included.

### Stage D — qualification then ordinary production review

If and only if both complete profiles pass, produce separate scoped artifacts:

- `independent-sol-qualification.json`: complete timing/equivalence PASS for the exact evidence-only config.
- `coordinator-qualification-acceptance.json`: acceptance of that timing evidence only; it does not activate or publish.

Later candidate acceptance/activation still needs a fresh exact production review/config/coordinator receipt chain and an explicit user authorization. Existing ordinary production paths continue requiring their current full receipts. Timing qualification alone never enables activation.

## Proposed finite budget

This bootstrap requires a fresh, separately authorized issue budget because the evidence-only entrypoint, policy sequence and trial are outside the Phase 1 safety fix:

- One initial Sol 6.1 / medium implementation and at most one Sol correction; zero Luna corrections.
- One independent Sol readiness review and one independent post-profile qualification review; keep the reviewer out of implementation.
- Exactly one `collar-05` evidence-only solver/trial attempt, max 2,000 iterations, write-once. No retry.
- At most one implementer profile and one independent profile, each <=135 seconds. No probes or replacement profiles; reuse the already reviewed containment evidence only if exact worker lifecycle bindings remain valid.
- Zero candidate promotion, activation, viewer/browser/publication or source/GIS changes.

This budget is proposed, not authorized. Phase 1's one initial implementation and reviewer PASS remain separate; previous failed issues/counters and consumed trials stay unchanged.

## User decision required

To proceed with this sequence, the user must explicitly approve both the staged receipt semantics (readiness permit before timing, scoped qualification receipt after timing, full production activation receipts later) and the single write-once `collar-05` evidence-only trial with the stated execution limits. If that policy change or trial is not approved, stop after Phase 1; timing remains unqualified. Alternatively, supply a provenance-compatible successful witness and genuine scoped preflight receipts if they already exist; verify hashes/provenance before use.