# Coordinator disposition 83 — accept close/image-stability correction plan

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Dispositions 64, 78–82 and the user's authorization for as many attempts as needed to pass the supervisor self-check.

## Plan accepted

Accept Sol's minimal correction plan `docs/milestones/artifacts/Teignmouth-float32-topology/build-3/review18-member-diagnostics-correction-plan.md`, SHA-256 `27b83760ab1a7791f1edc86667a9a0bfd9a379b1f384b55faad36d7f0a6c621a`. Coordinator recalculated the plan hash. Current S baseline remains `81fcdc0b199497d92d17c09c758a62b8861e7fcb7b41bb6a1c1663a1f76256af`; W/H/P are pinned by the plan.

Reserve a Luna S-only correction for both review-18 findings:

1. In diagnostic `finally`, make exactly one direct `CloseHandle` attempt before any optional timestamp/error construction, formatting, dict/list update or other telemetry. Guard all post-attempt close reporting as best-effort; unknown/missing telemetry stays partial.
2. Before promoting an executable image digest to observed, compare same-raw-path resolution and same-canonical-file metadata before and after the existing `_sha256` call. Require comparable regular-file metadata (`st_dev`, meaningful `st_ino`, `st_size`, nanosecond modification/change times, `st_mode`, and available Windows attributes/birthtime); mark change, missing, unsafe, unsupported, late or unverified state partial. Do not alter shared `_sha256`, add APIs/rights/dependencies, claim atomicity/mapped-image attestation, or change acceptance.

The complete original Job census, unexpected-PID rejection, eight-ID cap, same-handle diagnostics, original 10-second deadline, W/H/P, schemas/paths, roots, modes, commands, candidate behavior, retry evidence and all other gates remain unchanged. PID 20712 stays unidentified and rejected; the outer exit discrepancy and `957157…` history remain unresolved.

## Reserved static gates and independent review

Luna may run only S Ruff check/format and accepted-plan-authorized non-operational static syntax checks. No tests/imports/probes/process inspection/wrapper/self-check/preflight/runtime/evidence/root changes. Preserve retry-3 and all prior evidence byte-for-byte. Independent Sol review is required for exact close-attempt ordering, same-path/file metadata comparability, partial outcomes, no-false-observed digest, sticky rejection, all prior plan criteria and preservation.

No self-check is authorized. Retry-3 is consumed; a later attempt requires a separately planned/reviewed fresh retry-4 path and a coordinator execution gate. Candidate remains **NO-GO and unservable**, build 3 unreserved. No runtime collection, manifests, GIS/numerical/build, serving/publication or browser action. No commit, push or merge.
