# Project instructions

TVW-004, TVW-005 and the original 500 m TVW-006 scope are complete and independently reviewed; M0 and M1 are complete. On 2026-10-17 the user explicitly authorized a 1,000 m × 1,000 m AOI revision followed by TVW-007 EA DTM inspection. The size revision is in progress and must pass independent review before TVW-007 begins. Do not begin TVW-007 before that review or TVW-008 and later without separate user instruction. Preserve the TQ1 4HN centroid and keep the candidate `selected_pending_coverage` until actual coverage checks pass.

## Working protocol

1. Work on **one milestone and one focused issue** at a time. M0 and M1 are complete. Complete the authorized 1,000 m AOI revision and independent review, then TVW-007; do not start TVW-007 before review or begin TVW-008 or later without separate authorization.
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
