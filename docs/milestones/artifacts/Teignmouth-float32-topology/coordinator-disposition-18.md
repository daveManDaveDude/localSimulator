# Coordinator disposition 18 — consume diagnostic 2 and scope correction plan

Date: 2026-10-24

**Decision: diagnostic 2 is consumed once and completed within its 120-second limit. Candidate remains NO-GO. Sol is authorized to prepare a bounded plan for the remaining Luna correction cycle; this disposition does not authorize implementation, tests, a candidate build, serving, browser integration, or publication.**

Independent Sol review 11 confirms the saved build-2 face failure is explained by per-fragment area filtering: two positive production fragments of 9.50339172070107e-13 m² and 1.5254924997951674e-13 m² were each removed by the frozen <=1e-12 m² filter. Their aggregate 1.1028884220496237e-12 m² covers the expected clip of 1.1028883815799223e-12 m², subject to tiny saved clipping arithmetic residuals. The source gap is empty and positive-area source-triangle overlap count is zero. Do not change source, origin, domain, recipe, collision guards, tolerance or any numerical limit.

The report's automatic source-gap/overlap classification is not supported by its explicit saved geometries. report.json also retains stale stageStatus=IN_PROGRESS although the progress record and worker status show completion. The reported 4,927,488-byte peak samples only the launcher process and is not process-tree memory evidence. Preserve these artifacts unchanged; do not rerun diagnostic 2 to repair its reporting.

The invocation completed with worker and chosen outer exit codes 0, child termination confirmed, no timeout and external elapsed 63.2658 s. Pre/post preservation checked 291 bindings with zero changes, including all 225 protected build-2 bindings. The frozen manifest SHA-256 is 6e9b1b77b5451e40ea12be0787db3c025ff591d628a3fce7f99a55ea1c7e7b9e. The exact run hashes and detailed findings are recorded in the ledger and independent-review-11.md (SHA-256 13e1efe92dddf5b0d67949382a3266b6d320312eaeefb4a4f49c309bf5b5c3bb).

Sol may prepare only a prototype-local accounting correction plan and regression plan. Keep every discarded positive fragment available to aggregate coverage and extrema accounting before classifying the aggregate against the unchanged tolerance. The plan must account for complete and empty overlays, real missing coverage, actual positive-area overlap and clipping-order arithmetic. Preserve the historical shared helper. After Sol returns, coordinator review and explicit reservation are still required before the remaining Luna correction cycle or any tests/builds begin.

## Counters after diagnostic 2

- Initial implementation: 1 used.
- Luna correction cycles: 3/4 used; no cycle reserved.
- Sol correction: 0/1 used.
- Diagnostics: 2/2 used; none reserved.
- Candidate implementation builds: 2/6 used; none reserved.
- Independent confirmation builds: 0/1 used; unavailable until offline gates pass.
- Candidate serving/runtime output: ineligible.
