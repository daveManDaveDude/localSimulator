# Project instructions

TVW-004 through TVW-008 are complete and independently reviewed; M0, M1 and the M3 terrain-only issue are complete. The user separately authorized TVW-009/M4 on 2026-10-17; its initial implementation and QA evidence are ready for independent review. The TVW-007 EA DTM threshold passes, and TVW-009 has measured OSM building footprints, but mapped feature counts do not prove completeness and road/remaining feature checks are outstanding. Keep the AOI pending and do not call it approved or frozen. Do not begin TVW-010 or later until TVW-009 review and separate authorization. Preserve the TQ1 4HN centroid and the `selected_pending_coverage` / `not_checked` status.

## Working protocol

1. Work on **one milestone and one focused issue** at a time. M0, M1 and TVW-008/M3 are complete and independently reviewed. TVW-008 preserved the pending overall AOI status and synthetic worlds. The user separately authorized TVW-009/M4 for building footprints only; its initial implementation is awaiting independent review. Do not begin TVW-010 or later until that review passes and separate authorization is given.
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
