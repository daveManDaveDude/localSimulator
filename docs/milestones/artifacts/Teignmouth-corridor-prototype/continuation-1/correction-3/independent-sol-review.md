# Independent Sol review — correction 3

**Verdict: FIX REQUIRED — launch procedure failed; geometry remains untested.**

The interpreter correction is evidenced in `preflight.json`: it records the exact repository virtual-environment executable, Python 3.13.7, prefix and a successful GIS-free import smoke. The runner enforces that executable. Sol inspected these records and did not rerun them.

The stale guard is corrected. The runner consistently requires fresh `correction-3/build-4`; its `evidence.exists()` check rejects a precreated output directory before configuration/source loading or geometry. Preserve this guard.

Build 4 is spent. `implementation-stop.json` records the failed invocation, command and `STOP_BEFORE_BUILD` disposition. It claims no geometry, candidate buffers or browser run. It is a supplementary implementation record, not a runner-generated report.

The preservation evidence is appropriately qualified. The ledger says changed paths were not measured because the pre-build guard exited before before/after snapshots. `preservation-at-stop.json` is a post-stop inventory of 920 paths, not proof of unchanged bytes during the invocation. Do not promote it to a preservation pass.

The ledger already records three Luna corrections and four builds as used. Finalize correction 3 as reviewed/consumed without counting it twice. Counters after this review are: four builds consumed, three Luna corrections consumed, zero diagnostics and zero Sol corrections. No attempts are charged for this review.

## Required bounded correction

Use Luna correction cycle 4 and fresh build ordinal 5, with a 180-second maximum:

1. Preserve `correction-3/build-4` and all earlier evidence unchanged.
2. Change only the next exact output guard, corresponding preservation exclusion and invocation records.
3. Put preparatory metadata in the correction parent, outside the build output leaf.
4. Confirm the new `correction-4/build-5` leaf is absent; reserve the invocation, then let the runner create it.
5. Use the same repository virtual-environment command. Do not delete/reuse build 4 or weaken the existence guard.

This is a bounded procedural correction; no new numerical diagnostic or threshold change is justified. All geometry/source-loading acceptance gates remain untested. Road/building/walk coherence is unavailable and serving remains blocked. The separate topology-validation v2 issue remains inactive.

No edits, tests, builders, diagnostics, profiles, browser runs or executable verification checks were performed during this review.
