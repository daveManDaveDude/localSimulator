# Teignmouth operational memory containment amendment

**Date:** 24 October 2026  
**Status:** Implementation submission complete; independent review pending; no correction allowance.

## Decision

The fixed construction/transport byte ceilings are replaced in the opt-in v2
transition by a finite, operating-system-enforced memory ceiling around the full
computation process tree. This supersedes only the predictive full-tree B/P
ledger requirement and fixed 64 MiB construction/transport and 16 MiB envelope
checks from the earlier guarded-memory amendment. It does not remove the host
memory ceiling.

The prior approved bootstrap proposal, its user-approval artifact, the earlier
memory amendment, source-only assessment, and cleanup-correction review remain
historical records. They are not rewritten. This amendment does not reset any
trial, correction, or profile budget.

## Runtime memory policy

At process entry, before permit preflight, numerical imports or source loading,
the lightweight guardian records one monotonic T0 and queries fresh Windows
`GlobalMemoryStatusEx` values for `ullAvailPhys` and `ullAvailPageFile`. The latter
is recorded as current-process commit availability, not physical memory or an OS
reservation. It computes half the lesser availability and rounds the result down
to the Windows page size.

The guardian creates the actual v2 runner suspended, assigns it to a named
Windows Job with that aggregate commit limit and kill-on-close, queries the
effective limits and confirms membership, then resumes it. Breakaway is not
enabled. Imports, data loading, topology, solver, validation, serialization and
finalization all run inside this Job. Nested validation workers must be verified
in both their inner Job and the named outer Job. Direct execution of the v2
runner without guardian bindings is refused before NumPy/Shapely imports.

This is containment, not guaranteed capacity: availability can change after the
snapshot, Job commit denial does not itself end every worker, and Windows
termination can fail to finish inside a fixed interval. Allocation failure,
abnormal exit, timeout, incomplete output, binding mismatch or unconfirmed tree
cleanup fails closed and cannot yield a passing candidate. The guardian
explicitly terminates and waits; an unconfirmed Job remains owned until process
exit closes its kill-on-close handle.

## Transport and resource gates

The v2 process transport removes fixed 64 MiB construction/transfer checks and
the fixed 16 MiB envelope check. It preserves typed allowlists, supported array
types and shapes, finite-number checks, canonical JSON, exact sidecar lengths,
SHA-256 bindings, invocation identity, and rejection of aliases, truncated or
grown files, and unexpected files. Byte and construction estimates remain
telemetry; they are not process-memory bounds.

Request and response envelopes record exact byte lengths and SHA-256 values with
protocol, invocation and exact sidecar manifests. Each manifest is compared with
the files actually present; unexpected files and mismatches fail closed. The
former fixed 64 MiB transfer/construction and 16 MiB envelope ceilings are absent
from this v2 path. A one-megabyte streaming hash buffer is only an I/O chunk size,
not a maximum file or process-memory allowance.

For v2, retain `peakConstructionBufferBytes` as a measured estimate but remove
that estimate's 64 MiB acceptance predicate. All other numeric, geographic,
source, geometry and output resource gates remain unchanged, including the
separate 16 MiB resident-geometry limit, 8 MiB runtime asset limit, 256 KiB
manifest, 512 KiB QA, triangle/vertex/draw limits, and all twelve numeric gates.
The frozen legacy runner and historical hashes remain unchanged; the v2 worker
uses an explicit adapter that applies the same resource checks except the retired
construction estimate predicate.

## One-use dispatch and scope

The guardian accepts only `collar-05`. Before creating a computational process,
it verifies and atomically consumes
`.codex/evidence/teignmouth-topology-study/collar-05-dispatch-permit.json` by
creating a no-overwrite consumed link and removing the source permit. The permit
binds the exact transition config, spec, runtime code map, independent Sol
review, coordinator acceptance, and a unique permit ID. A consumed permit is
never restored, including after startup failure. Missing, malformed, stale, or
already consumed permit means no launch.

No solver, trial, timing profile, candidate or browser work has been run during
this implementation amendment. After this submission passes independent Sol review,
the coordinator may create the exact one-use permit for the previously
authorized `collar-05` attempt, subject to the existing exact receipt and input
checks. The attempt remains write-once. No replacement, retry, candidate
promotion, activation, public package, or production timing claim is authorized.

Retain 2,000 solver iterations, the T0+120 solver cutoff, T0+125 validation
cutoff, T0+135 maximum finalization bound, and both <=125-second profile gates.
The guardian reserves the final second inside T0+135 for bounded termination and
confirmation if the computation is still running. The AOI, TQ1 4HN center,
source bytes, synthetic fallback, and pending coverage status are unchanged.

## Required evidence

The completed implementation submission includes tests for dynamic page-rounded Job
limits, suspended-before-resume containment, outer and nested membership,
allocation denial and failure cleanup, exact-length/hash transport above the old
ceilings, single-T0 propagation, direct-runner refusal, one-use permit consumption,
and no candidate publication. Preserve exact before-images and record all
changed extension hashes. Run the focused Python suite, Ruff, formatting, static
binding checks and preservation checks. Do not run the collar trial or any
profile during implementation/review.
