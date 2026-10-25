# Coordinator disposition 20 — accept Luna cycle-4 handback for Sol review only

Date: 2026-10-24

**Decision: Luna correction cycle 4 is consumed. The implementation and its authorized focused checks are ready for independent Sol review. No candidate build is authorized by this disposition. Candidate remains NO-GO and unservable.**

The implementation summary is correction-4/implementation-summary.json, SHA-256 e45f1a859fc6f309fd458e5eeb5a12870a63332e381610b1db14d113b5f9534a. It records three authorized changed paths and hashes, successful exact-environment focused pytest (27 passed), Ruff check and format checks, and the earlier wrong-working-directory collection failure. The historical shared helper is unchanged and still matches its diagnostic-manifest SHA. Review the full handback in correction-4/handback.md.

Independent Sol review should check aggregate positive-fragment accounting; genuine missing coverage and actual overlap rejection, including a gap/overlap cancellation case; clipping-order sensitivity without bitwise equality assumptions; all positive-fragment ring extrema; explicit empty handling; prototype-only call-site isolation; preserved exact-zero plane checks; numeric/source/domain constraints; test scope; and whether a fresh candidate-build manifest can be planned. A failure must remain a failure. The nonzero source-plane extrema in diagnostic 2 may remain a separate blocker; no limit can be relaxed here.

No full build, browser validation, product edit, diagnostic rerun, serving or commit is authorized. After independent Sol review, the coordinator will decide whether to prepare and review a separate bounded build-3 manifest. Serving remains prohibited.

## Counters after cycle 4

- Diagnostics: 2/2 used.
- Luna correction cycles: 4/4 used; none reserved.
- Sol correction: 0/1 used; eligibility requires all four Luna cycles to be independently reviewed and an actionable issue remains.
- Candidate implementation builds: 2/6 used; none reserved.
- Independent confirmation builds: 0/1 used; unavailable until all offline gates pass.
- Candidate serving/runtime output: ineligible.
