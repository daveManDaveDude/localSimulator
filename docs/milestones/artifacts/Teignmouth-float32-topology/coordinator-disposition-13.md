# Coordinator disposition 13 — consume build 2 failure and hold for diagnosis

Date: 2026-10-24

**Decision: build 2 is consumed as `BLOCKED_EXCEPTION`; candidate serving remains NO-GO.** The runner persisted a consistent failure report after 33.1976 seconds, with measured peak working set 609,505,280 bytes and no timeout. Pre- and post-run preservation passed for all 225 bound files. Four gates passed (`storedLocalTopology`, `chartSupportCompleteness`, `requiredTreatmentSupport`, `treatmentSupportClassification`); seven later gates are unavailable after serialization failed.

The failure occurred in source overlay validation for patch face 19669: face area `0.020639419555664062 m²`, expected clipped area `1.1028883815799223e-12 m²`, and accumulated covered area 0. The runner reports logical/child/runner exits 2. Luna reported that the external exec captured exit 1, while the build report explicitly records the external exit as uncaptured; retain that distinction. Failed partial output is archived at `build-2/run-1/partial-candidate-output`; generated candidate output is absent.

Independent Sol review 7 found a plausible coverage-accounting edge case: the overlay helper discards each source intersection at or below `1e-12 m²` before coverage and extrema accumulation, so multiple small pieces may exceed the expected area while contributing zero. The captured failure does not establish whether this is the cause, a clipping arithmetic discrepancy, or a real partition gap. Sol recommends one saved-artifact face-level diagnostic before correction. No build retry or serving is authorized by this disposition.

## Counters after consuming build 2

- Initial Luna implementation: 1 used, 0 reserved.
- Luna correction cycles: 3 used, 0 reserved (one remains).
- Sol corrections: 0 used, 0 reserved.
- Diagnostics: 1 used, 0 reserved (one remains).
- Implementation builds: 2 used, 0 reserved (four remain under the six-build ceiling).
- Independent confirmation builds: 0 used, 0 reserved; available only if every offline gate passes.
- Candidate serving/runtime output: ineligible.

The next action is to freeze a diagnostic-2 plan and input manifest, then separately reserve at most one read-only diagnostic bounded to 120 seconds. Keep the fixed origin, input source, domain, collision guard and all numerical limits unchanged.
