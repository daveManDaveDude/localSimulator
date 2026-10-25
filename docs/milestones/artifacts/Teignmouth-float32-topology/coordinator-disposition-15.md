# Coordinator disposition 15 — corrected diagnostic harness pending Sol re-review

Date: 2026-10-24

**Decision: Luna's diagnostic harness preparation is complete and submitted for independent Sol re-review. No diagnostic is reserved or run.** The harness correction addressed independent review 8; the updated plan now binds a Python external supervisor and exact target-way extraction. Candidate serving remains NO-GO.

## Frozen preparation revisions

- Plan: `docs/milestones/artifacts/Teignmouth-float32-topology/diagnostic-2/plan.md` — SHA-256 `017d81efdce6f2a6e8f28d29b3fb7b5fef34f8d0ff84e16c9bca5447bd9a219a`.
- Diagnostic runner: `pipeline/scripts/diagnose_teignmouth_overlay_face.py` — SHA-256 `298f5865fc0cc3262e6e36ecde7383f01cd5ba91dd3e37199c16b5f573a7ff5c`.
- External supervisor: `pipeline/scripts/run_teignmouth_overlay_face_diagnostic.py` — SHA-256 `a35a474e05c7efc4aa001ad261ea93ba3431a513ff9fb056189b3fcfb3be9dc4`.
- Runtime-identity schema: `pipeline/scripts/teignmouth_overlay_diagnostic_runtime_identity.schema.json` — SHA-256 `7096ef9a9f6cf47ebe7d4b54a7edcdebf9e26ecd2d2ce75d63e286c52f8f804a`.

The coordinator confirmed these hashes match Luna's handoff. At this disposition, `diagnostic-2/run-1/` and `diagnostic-2/invocation.json` are absent; no script was executed or imported, no tests/compilation were run, and no numerical work occurred. Review 8 is recorded at `independent-review-8.md`; the new independent review is pending.

## Counters (unchanged)

- Initial Luna implementation: 1 used, 0 reserved.
- Luna candidate correction cycles: 3/4 used, 0 reserved.
- Sol candidate corrections: 0/1 used, 0 reserved.
- Diagnostics: 1/2 used, 0 reserved.
- Candidate implementation builds: 2/6 used, 0 reserved.
- Confirmation builds: 0/1 used, only after every offline gate passes.
- Candidate serving/runtime output: ineligible.

Next: accept or correct the harness only after independent Sol review. Then freeze the full diagnostic manifest, reserve diagnostic 2 once, and invoke only through the reviewed external supervisor with its 120-second bound.
