# Project instructions

TVW-004, TVW-005, TVW-006 and TVW-007 are complete and independently reviewed; M0 and M1 are complete. The user authorized TVW-008/M3 on 2026-10-17; it is the current issue. The TVW-007 EA DTM threshold passes, but OSM/OS building and road feature counts remain unchecked, so do not call the AOI approved or frozen. Do not begin TVW-009 or later without separate user instruction. Preserve the TQ1 4HN centroid and the `selected_pending_coverage` / `not_checked` status.

## Working protocol

1. Work on **one milestone and one focused issue** at a time. M0 and M1 are complete. The 1,000 m AOI revision and TVW-007 passed independent review; the user has separately authorized TVW-008/M3 only. TVW-008 must preserve the pending overall AOI status and synthetic worlds. Do not begin TVW-009 or later without separate authorization.
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
