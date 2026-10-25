# Teignmouth operational memory containment handback

**Status:** Implementation submitted for independent review; no collar trial or
profile has run.

## Problem this work enables

The road-alignment issue is that the source-draped road mesh can sit above or to
the side of the carriageway where the OSM centreline and coarse EA DTM disagree,
especially beside steep banks. The authorized next experiment explores a local
topology and refinement candidate while retaining the existing twelve numeric
and geographic acceptance gates. Removing allocation checks does not itself
move the road onto the right ground; it only lets the bounded candidate
experiment reach its existing validation gates.

The previous transport path had several separate fixed byte checks. Removing
one could still leave another rejecting a large request, transfer, result, or
construction estimate. Predictive full-tree allocation arithmetic also tried
to decide whether Python/NumPy/GEOS work would fit before running it, without a
complete defensible bound for those allocations. That was the source of the
repeated allocation work, rather than a change to the road geometry problem.

## Implementation

- Removed the fixed 64 MiB construction/transfer acceptance checks and 16 MiB
  envelope check from the guarded v2 path.
- Kept estimates as telemetry and removed their pre-assembly rejection. The
  aggregate Windows Job now contains the actual runner process tree under a
  page-rounded ceiling computed from current available physical/commit memory.
- Added exact canonical request/result envelope lengths and hashes, invocation
  bindings, sidecar manifests, exact file-set checks, streaming sidecar hashes,
  and rejection of missing, unexpected, truncated, grown or mismatched files.
- Kept the separate resident-geometry, runtime-asset, manifest, QA, topology,
  numeric, geographic and source gates unchanged.
- Kept one T0 and the 120/125/135-second timing policy, single-use permit path,
  captured before permit preflight, and explicit terminate/wait/confirmed-exit
  cleanup.

## Quality and authorization state

Commands run from `pipeline/`:

- `.\.venv\Scripts\python.exe -m pytest tests/test_teignmouth_validation_process.py tests/test_teignmouth_memory_admission.py tests/test_teignmouth_guardian.py tests/test_road_surface_validation_transition_v2.py tests/test_road_surface_validation_v2.py tests/test_teignmouth_complete_profile.py tests/test_teignmouth_cached_supervisor.py -q` — **135 passed**. This includes the native Windows Job membership, commit-limit and cleanup checks, plus a regression that T0 is captured before permit preflight.
- `ruff check` on the seven changed Python modules — **passed**.
- `ruff format --check` on the same modules — **7 files already formatted**.
- `git diff --check` — **passed**.
- Static extension/runtime binding checks ran within the passing pytest suite. The original approval/proposal hashes, legacy trial maps, 120/125/135 timing policy and disabled activation were independently checked and remain intact. Collar-05 directory and dispatch/consumed permit are absent.

The process source files and tests were already dirty when this task resumed, so
the earlier turn's exact source bytes could not be reconstructed as a fresh
pre-change copy. The pre-turn config, spec and checkpoint snapshots are preserved
under `.codex/history/2026-10-24-operational-memory/`; the final implementation
bytes and hashes are recorded in the submission manifest. This provenance limit
is disclosed for the independent reviewer.

An independent Sol review of the actual changed code is pending. The review may
not spend a correction: this implementation allowance is one submission and
zero corrections.

No collar-05 run, timing profile, candidate promotion, package change, browser
verification or publication happened during implementation. No receipt or
dispatch permit has been generated or consumed. The AOI remains pending, TQ1 4HN
is unchanged, and all source/package bytes remain untouched.

## Limits and known defects

The Job ceiling is a dynamic host guard, not unlimited memory and not a guarantee
that Windows will admit every allocation. It leaves half of the lesser fresh
physical/commit availability as policy reserve, does not reserve those bytes
against other applications, and may still surface an allocation error. A Job
commit limit does not by itself terminate the tree; the guardian explicitly
terminates and verifies cleanup. Unconfirmed termination, timeout, incomplete
output or any identity mismatch fails closed. The road-alignment experiment may
still fail its original gates or its existing time cutoff.
