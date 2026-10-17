# Project instructions

TVW-004, TVW-005, and TVW-006 are complete and independently reviewed; M0 and M1 are complete. The user authorized a 1,000 m × 1,000 m AOI revision followed by TVW-007, and the size revision passed independent review. TVW-007's initial EA DTM inspection has an EA-only 1% threshold pass and is pending independent review. OSM/OS building and road feature counts remain unchecked, so do not call the AOI approved or frozen. TVW-007 is the current issue; do not begin TVW-008 or later without separate user instruction. Preserve the TQ1 4HN centroid and the `selected_pending_coverage` status.

## Working protocol

1. Work on **one milestone and one focused issue** at a time. M0 and M1 are complete. The 1,000 m AOI revision passed independent review; TVW-007 is authorized and current. Its initial implementation reports a passing EA DTM threshold result, but overall AOI coverage remains pending until planned OSM/OS feature checks are complete and the work is reviewed. Do not begin TVW-008 or later without separate authorization.
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
