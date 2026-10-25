# Coordinator disposition 81 — submit unexpected-member evidence change for review 18

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Dispositions 64, 78–80 and the user's authorization for as many attempts as needed to pass the supervisor self-check.

## Implementation handoff

Luna implemented the accepted S-only unexpected-member diagnostic enrichment in `_observe_selfcheck_unexpected_members` and the tail of `_selfcheck_job_snapshot`. The original complete census and `unexpectedPids` remain authoritative; detail is diagnostic, capped at eight, and PID-to-census identity remains unproven. Retry-3 evidence is still consumed/non-PASS and unchanged.

Coordinator recalculated hashes:

| File | SHA-256 |
| --- | --- |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `81fcdc0b199497d92d17c09c758a62b8861e7fcb7b41bb6a1c1663a1f76256af` |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `c3f1f49cb574793c1cdbc2d905fd3d36f646b6f32ffb7c200a96c9792d5ce84f` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `cf1145b33397066559b89c11aa1cb0ebcf4d6d4d470f6521d96fe9e1f4ecccab` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

Coordinator rehashed all eleven retry-3 files; each still matches disposition 78. Luna reports all original/retry-1/retry-2 evidence trees unchanged as well.

Luna reports the authorized final checks from `pipeline/` passed:

- `.venv/Scripts/python.exe -m ruff check scripts/run_teignmouth_float32_build3.py` — `All checks passed!`
- `.venv/Scripts/python.exe -m ruff format --check scripts/run_teignmouth_float32_build3.py` — `1 file already formatted`

The first Ruff check had five findings: E501 at the OpenProcess WinError record, B023 closure references in `observe_membership`, and E501 in the final generator expression. The first format-check requested four collapses (two snapshot timestamp gets, the IsProcessInJob call, and omitted-detail max). Ruff format was run, followed by the passing final gates. No tests, imports, probes, live process inspection, wrapper/self-check/preflight/runtime or evidence writes were run. Outer command exit 1 versus internal exit 2 remains unresolved; the `957157…` prior S digest remains unsaved/untraceable.

## Independent review gate

Submit actual S hash above for independent Sol review 18 against the accepted diagnostic plan and retry-3 diagnosis. Verify exact primary census preservation and sticky rejection; immediate bounded same-handle details; creation/membership/wait/exit/image partial semantics; PID reuse/disappearance unknown; eight-row and deadline bounds; one close attempt; best-effort diagnostics cannot mask primary failure/cleanup; and all other gates, W/H/P and original/retry evidence remain unchanged. Review must not execute anything. Keep all consumed roots immutable.

No self-check is authorized by this disposition. Retry-3 is consumed; any later self-check requires a separately planned/reviewed fresh retry-4 path and a coordinator execution gate. Candidate remains **NO-GO and unservable**, build 3 unreserved. No runtime collection, manifests, GIS/numerical/build, serving/publication or browser action. No commit, push or merge.
