# Coordinator disposition 3 — correction 1 submitted

Date: 2026-10-24

Luna correction cycle 1 is complete and is counted as **1 used, 0 reserved**. The corrected code and focused evidence are forwarded for distinct independent Sol re-review. This disposition does not accept the candidate, reserve a build, or authorize a source-load diagnostic.

The fresh correction manifest binds 188 files and the coordinator independently rehashed every listed binding with no mismatches. Candidate output is absent. Luna reports 12 focused tests, Ruff check/format, `py_compile` and GIS-free import smoke passed; the first pytest invocation from repository root failed package discovery and the rerun from `pipeline/` passed. The watchdog and Windows memory API were compiled/static-checked, not exercised in a candidate run.

The four findings in independent review 1 are claimed addressed in the correction evidence plan. The independent reviewer must verify the changes before any build decision. Keep fixed origin, collision guard, source, recipe and all limits unchanged. Build ordinal 1 stays unreserved; candidate remains unservable.

Evidence: `docs/milestones/artifacts/Teignmouth-float32-topology/correction-1/input-manifest.json` and `correction-1/evidence-plan.md`.
