# Coordinator disposition 19 — reserve Luna correction cycle 4

Date: 2026-10-24

**Decision: GO for one implementation-only correction, Luna correction cycle 4 of 4, following Sol plan review. This reserves no candidate build. Candidate remains NO-GO and unservable.**

Accepted plan: sol-plan-correction-4.md, SHA-256 9d8b2671632a222d16641b83439e5717916eb5517432a26a9305c6c671a922b3, authored by the independent Sol planner/reviewer after diagnostic-2 review 11. The plan confines the change to a prototype-local affine surface overlay helper in pipeline/torquay_pipeline/teignmouth_float32_candidate.py and focused tests in pipeline/tests/test_teignmouth_float32_candidate.py, optionally with a small provenance-bound fixture. It retains every strictly positive finite polygon fragment, aggregates coverage before applying the existing unchanged area tolerance, and evaluates extrema over all vertices of retained positive fragments. Empty regions must be represented explicitly; genuine gaps and positive-area overlaps above the existing tolerance must fail, while a rounding-only sum-minus-union residual must not be mislabeled as physical overlap. The correction must preserve tiny nonzero plane extrema and all exact-zero checks.

Keep the historical shared helper unchanged. Preserve source, origin [-140,0,-95], domain [-182,-136,-98,-54], stations 140–155, default 35 m influence buffer, recipe, chart, source geometry, stored Float32 decoding contract, collision/constraint/winding/seam guards, all thresholds and all remaining numeric limits. No product/browser edits, GIS acquisition, diagnostic/supervisor changes, memory telemetry, stale report bookkeeping, tolerance increases, coordinate snapping or parameter sweeps.

Authorized correction checks are limited to the exact-environment focused tests and lint/format checks proposed in the Sol plan. Do not run a candidate build, browser validation or serving. Record changed-file hashes, exact commands and outcomes. After implementation, independent Sol review must determine whether the correction is safe and whether a build 3 should be considered separately. The plan warns that unchanged exact source-plane-zero checks may expose another genuine blocker after accounting is repaired; do not relax them or describe the candidate as accepted.

## Counters after reservation

- Diagnostics: 2/2 used; none remaining.
- Luna correction cycles: 4/4 reserved (3 previously used; this reservation is cycle 4).
- Sol correction: 0/1 used.
- Candidate implementation builds: 2/6 used; none reserved.
- Independent confirmation builds: 0/1 used; not yet eligible.
- Candidate serving/runtime output: ineligible.
