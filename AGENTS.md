# Project instructions

TVW-004 through TVW-015 are complete and independently reviewed; M0, M1 and the M3 terrain-only issue are complete. The combined M5 exit gate was accepted by the coordinator after TVW-012's independent review on 2026-10-19; M6 was accepted after TVW-013's fix-1 independent review on 2026-10-19; M7/TVW-014 was accepted after its final independent review on 2026-10-19; the TVW-015 street-label slice of M8 was accepted after its final independent review on 2026-10-19. The M8 minimap and TVW-016 and later remain unauthorized. Mapped feature counts do not prove completeness; remaining-feature coverage checks are outstanding. Keep the AOI pending and do not call it approved or frozen. Preserve the TQ1 4HN centroid and the `selected_pending_coverage` / `not_checked` status.

## Working protocol

1. Work on **one milestone and one focused issue** at a time. M0, M1 and TVW-008/M3 are complete and independently reviewed. TVW-008 preserved the pending overall AOI status and synthetic worlds. TVW-009/M4 import, height policy and QA, TVW-010 browser building rendering, TVW-011 optional road rendering, TVW-012 independent map comparison, TVW-013 ground-following walk mode, TVW-014 clean-clone smoke, source-regeneration evidence and profiling, and TVW-015 optional street-name labels passed independent review. The combined M5, M6, M7 and TVW-015 issue gates are complete. The M8 minimap and TVW-016 and later remain unauthorized without separate instruction.
2. Start with an implementation plan, concrete files touched, tests and proof of completion.
3. Keep geographic calculations in tested Python modules and typed, documented asset contracts. No ad-hoc coordinate transforms scattered across React/Three.js render logic.
4. Maintain a **fully functioning synthetic world** at all times.
5. Do not fabricate geographic coordinates, downloaded files, measured building heights or successfully run tests.
6. Do not silently add a paid service, large dependency, API key, authentication system, container orchestration or hosted backend.
7. Use official publisher documentation and source metadata when dataset shape, CRS or licence is uncertain.
8. For each change: run quality gates, confirm local browser experience where possible, attach screenshot/observation, record blockers, and update milestone checklist.
9. Do not claim visual tests passed unless an actual browser run occurred. If Computer Use/browser access is unavailable, say so and provide precise local verification steps.
10. Keep source data separate from generated assets; preserve provenance and repeatability.
11. If a source is missing, implement a clear fallback **without pretending fake data is real**.
12. Ask for user intervention only for things Codex cannot reasonably obtain (e.g., an account-gated manual download). Continue with synthetic work rather than blocking every milestone.
13. Make small commits with meaningful messages; do not push or merge without configured repository/user permission.
14. Finish every milestone with a handback: summary, commands run, test results, screenshot links where available, known defects, and next proposed issue.
