# Independent Sol review 5 — correction 3

Date: 2026-10-24

## Decision

**GO on correction-3 code; NO-GO for build-2 reservation using the current 199-file manifest.** The implementation meets the correction-3 plan. Before a build, freeze a fresh manifest that also binds every file in build-1 evidence. This is coordinator evidence preparation, not a Luna correction.

## Verification

All 199 correction-3 bindings match. Chart validation is pinned to station 108–187 m and lateral ±16 m. Vertices outside the influence and inside the influence but outside validated chart support retain source heights with witnesses; owner gaps within expected support and missing required ±4 m target coverage hard-fail. Source-plane overlays cover both outside-influence and inside-influence/outside-chart regions. Previous XYZ ordering, Float64 section sampling, durable failure evidence, guarded runner and fixed numeric limits remain intact.

Worker logical status/result, actual child exit, runner-selected exit and uncaptured external exit are separated. Synthetic tests cover logical return 2 and handled launch failures propagating nonzero. Candidate remains unservable; real numerical/offline gates remain unmeasured.

The correction-3 manifest omits this issue's `build-1/` evidence. Sol rehashed the build report and supervisor report against ledger hashes; both match, but the full buffer/evidence set is not bound for a future pre/post run check. Add all files under `build-1/` to a new build-2 input manifest before reservation, and reverify that manifest. Preserve correction-3 and all earlier manifests immutably.

## Limitations

Luna reports 18 focused tests passed after two synthetic-fixture failures were corrected. The reviewer ran no tests, source load, diagnostic, build, or edits. The watchdog timeout-termination path remains unexercised. No browser or screenshot evidence exists.
