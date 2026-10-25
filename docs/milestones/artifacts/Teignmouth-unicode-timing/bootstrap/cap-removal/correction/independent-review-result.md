# Independent re-review result

Date: 2026-10-24

## Verdict

**PASS for the sole cleanup correction only.** The overall Stage A submission remains
stopped and does not establish safe cap-removal readiness.

## Verified correction

- Memory observations are optional telemetry and their failures no longer skip
  process termination or the bounded exit wait.
- The guardian closes the Job only after confirmed exit. Unconfirmed exit or close
  failure retains ownership and records the cleanup error.
- Seven synthetic regressions cover telemetry, termination, wait, close and
  ownership-retention failure paths.
- The recorded correction suite passed 122 tests, with one native test deselected.
  The reviewer ran no checks, assessment or trial.
- Correction hashes/pins and 8,163 protected records match. The source assessment,
  command and original checks are byte-identical. The checkpoint is valid UTF-8;
  its malformed-byte before-image is preserved.

## Remaining stop

The production protocol still enforces `MAX_BYTES = 64 MiB` and
`MAX_ENVELOPE = 16 MiB` in
`pipeline/torquay_pipeline/road_surface_validation_process_v1.py`; the fixed
64 MiB construction acceptance predicate also remains in
`pipeline/torquay_pipeline/road_surface_patch.py` and
`pipeline/scripts/run_teignmouth_topology_study.py`.

The assessment has no complete request bound and records `B`, `P` and `H` as null.
Observed memory peaks do not prove a future bound. Python object, native/GEOS,
clipping, transport and finalization allocations still lack a justified full-tree
ledger. Consequently there is no readiness PASS, timing qualification, trial
dispatch or candidate promotion. Activation remains false.
