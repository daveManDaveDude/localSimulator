# Coordinator disposition 17 — invoke diagnostic 2 once

Date: 2026-10-24

**Decision: GO for exactly one invocation of the reviewed face-only diagnostic under the reserved 120-second limit.** The immutable diagnostic manifest SHA-256 is `6e9b1b77b5451e40ea12be0787db3c025ff591d628a3fce7f99a55ea1c7e7b9e` with 291 file bindings; coordinator rehash found no mismatches and all 225 build-2 protected bindings match. Independent Sol review 10 passed the manifest and runtime identity (review SHA-256 `3bcad2f41731cadadfda2731a19ba5626e11b971a517fa8449500884519c54fd`). The active ledger equals the frozen reservation snapshot and records diagnostic 2 reserved once. The execution leaf, invocation record and candidate output were absent immediately before authorization.

Run only:

```powershell
pipeline/.venv/Scripts/python.exe -B pipeline/scripts/run_teignmouth_overlay_face_diagnostic.py
```

This runs a saved-artifact investigation of face 19669 only. It may extract the one bound target road feature and memory-map only intersecting source cells. The supervisor enforces the total wall deadline and process-tree containment. The result does not authorize a candidate correction, build, serving or browser/product integration; those require separate review and coordinator disposition. No retry is allowed.

The external command's actual exit code must be captured from the coordinator execution tool and reconciled separately from the runner's chosen exit.
