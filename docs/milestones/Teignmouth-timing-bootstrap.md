# Teignmouth road alignment and timing work

## Current state - 24 October 2026

The product problem remains the local Teignmouth roads that appear to float or
sit slightly on a steep bank in the 3D view. The working explanation is a
possible mismatch between mapped road geometry and terrain elevations, plus the
fact that the viewer drapes mapped road geometry over terrain rather than using
a surveyed carriageway surface. This is a hypothesis to test, not a confirmed
cause for each road.

The authorized next geometry experiment is to try a different local mesh topology
and then refinement, retaining all current numeric, geographic, source and
timing limits. This work removes memory-based barriers to reaching that
experiment; it does not alter geometry or guarantee the road will align.

The repeated allocation discussion came from independent fixed checks in the
transport path: a 64 MiB construction/transfer ceiling, a 16 MiB envelope
ceiling, and predictive estimates used before assembly. Removing just one left
another reason for the same candidate to stop. The new bounded implementation
removes those fixed checks and makes the Windows Job the actual process-tree
memory guard. That is a finite dynamic ceiling based on fresh PC headroom, not
unrestricted memory. The previous Stage A stop record below is historical; the
new implementation is awaiting independent review. No trial, timing profile or
candidate has run under the new guard.

Detailed implementation state:
`Teignmouth-operational-memory-handback.md`.

## Historical Stage A handback - guarded memory amendment stopped

Status: **STOPPED: complete full-tree execution allocation admission unavailable**.

Detailed handback:
`artifacts/Teignmouth-unicode-timing/bootstrap/cap-removal/implementation-handback.md`.
The complete source bound now exists and native outer-Job tests passed, but the
complete future B/P ledger remains unbounded. Live cap-removal integration is
incomplete: 64 MiB/16 MiB live transaction guards remain. No Stage A readiness PASS,
trial, receipt, permit, profile, candidate, activation or production timing claim.
All original proposal/approval and historical issue evidence bytes remain intact.

The sole cleanup correction passed independent review. This verifies cleanup
failure handling only; it does not establish allocation admission or remove the
live caps. The assessment records and original checks remain unchanged.

The earlier source-bound stop handback is preserved exactly at
`.codex/history/2026-10-24-unicode-timing/cap-amendment-before/docs/milestones/Teignmouth-timing-bootstrap.md`.
Current exact commands, observations, checks, preservation and hash transitions are
in the cap-removal evidence directory above. The independent review result is at
`artifacts/Teignmouth-unicode-timing/bootstrap/cap-removal/correction/independent-review-result.md`.
Next: wait for user direction on a new bounded proposal for the missing full-tree
Python/native/GEOS allocation ledger. No dependent execution automatically follows.
