# Coordinator disposition 16 — reserve diagnostic 2 once

Date: 2026-10-24

**Decision: GO for one bounded, read-only saved-artifact diagnostic (ordinal 2), maximum 120 seconds, after the frozen manifest passes coordinator and independent Sol verification.** Independent Sol review 9 passed the corrected diagnostic runner/supervisor statically; the harness and exact plan hashes are recorded below. This is not a candidate correction or build and does not make the candidate servable.

The diagnostic answers only whether source-intersection fragments discarded at `<=1e-12 m²` explain build-2 face 19669's `1.1028883815799223e-12 m²` expected outside-influence clip, or whether a source-partition/clipping issue exists. It may stream only the target way 78455395 part 0 from the already frozen roads payload, use exact bound code/config to reconstruct the clip, and memory-map only intersecting heightfield nodes. Stop on any mismatch; do not alter tolerance, source, origin, domain, collision guard or limits.

Reviewed preparation hashes:
- Plan `017d81efdce6f2a6e8f28d29b3fb7b5fef34f8d0ff84e16c9bca5447bd9a219a` (`diagnostic-2/plan.md`).
- Runner `298f5865fc0cc3262e6e36ecde7383f01cd5ba91dd3e37199c16b5f573a7ff5c` (`pipeline/scripts/diagnose_teignmouth_overlay_face.py`).
- External supervisor `9f1d20086f0e2b26cd972101bda1b3d224f53e176c2f57e480e3dacb4ca7a17a` (`pipeline/scripts/run_teignmouth_overlay_face_diagnostic.py`).
- Runtime identity schema `7096ef9a9f6cf47ebe7d4b54a7edcdebf9e26ecd2d2ce75d63e286c52f8f804a`.
- Independent Sol review 9 `51d9c9b9056bbf8dd81872b346e9ea03121d810359af9d34c511282663268461`.

Invoke only through:

```powershell
pipeline/.venv/Scripts/python.exe -B pipeline/scripts/run_teignmouth_overlay_face_diagnostic.py
```

The supervisor verifies the bound manifest, starts the runner suspended, assigns it to a kill-on-close Win32 Job Object, and enforces the 120-second total wall bound. It writes a durable parent invocation record and post-stop preservation results; only the runner may create the absent `diagnostic-2/run-1/` leaf. Before invocation, the coordinator will verify the complete build-2 protected-binding closure, all pre-run input hashes, exact runtime identity and absence of output paths. No retry is allowed. Candidate serving, another build, browser/product integration and publication remain unauthorized.

## Counters after reservation

- Initial Luna implementation: 1 used, 0 reserved.
- Luna candidate correction cycles: 3/4 used, 0 reserved.
- Sol candidate corrections: 0/1 used, 0 reserved.
- Diagnostics: 1 used, 1 reserved (diagnostic 2 of 2).
- Candidate implementation builds: 2/6 used, 0 reserved.
- Confirmation builds: 0/1 used, available only after all offline gates pass.
- Candidate serving/runtime output: ineligible.
