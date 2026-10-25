# Coordinator disposition 14 — accept diagnostic plan, no run reserved

Date: 2026-10-24

**Decision: accept the Sol diagnostic-2 plan for preparation only. Do not run it yet.** The plan now permits a standard-library streaming extraction of only OSM way 78455395 part 0 from the already manifest-bound roads payload, solely because the saved build artifacts do not contain exact clip provenance. It requires exact reconstruction with the existing helper/config and default Shapely buffer, a face-area reproduction check, and a hard stop on mismatch. The source heightfield access remains limited to memory-mapped nodes for intersecting cells.

The plan is at `docs/milestones/artifacts/Teignmouth-float32-topology/diagnostic-2/plan.md` (SHA-256 `396ef28bfe38fd1c693aeda38f8538cfd166f6ac6b52e450977ef1dee8d019df`). Independent review 8 found FIX REQUIRED in Luna's diagnostic harness; see `independent-review-8.md`. Luna is preparing the harness corrections. No diagnostic slot is reserved or consumed; the candidate remains unservable. After script and wrapper review, coordinator must freeze the manifest, reserve diagnostic 2 once, and invoke within 120 seconds. No candidate build or serving follows automatically from diagnosis.

## Counters

- Initial Luna implementation: 1 used, 0 reserved.
- Luna candidate correction cycles: 3/4 used, 0 reserved.
- Sol candidate corrections: 0/1 used, 0 reserved.
- Diagnostics: 1/2 used, 0 reserved.
- Candidate implementation builds: 2/6 used, 0 reserved.
- Confirmation builds: 0/1 used, available only after every offline gate passes.
- Candidate serving/runtime output: ineligible.
