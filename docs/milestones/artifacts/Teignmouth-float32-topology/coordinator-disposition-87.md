# Coordinator disposition 87 — submit retry-4 path patch for review 20

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Dispositions 64, 85–86 and the user's authorization for as many attempts as needed to pass the supervisor self-check.

## Implementation/static handoff

Luna reports exactly four path substitutions: W's retry-4 parent and fallback allowlist, S `SELF_ROOT`, and H's `EVIDENCE` leaf. Coordinator independently verified literal counts W/S/H `2/1/1`, zero active retry-3 literals, and exact in-memory inverse hashes to the accepted W/S/H baselines. P is unchanged. Retry-4 is absent and alias-free; the inspected ancestors remain safe canonical directories.

Coordinator-calculated final hashes:

| File | SHA-256 |
| --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `64bf2c4abf822ad55252789315d71731d2660d66bb5b6bc7d60f810f2de492c7` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

Luna reports Ruff check/format and PowerShell AST parse passed; exact inverse proof and all-26-file evidence comparison passed. Two preliminary command errors were corrected: a PowerShell AST quoting issue and an evidence/hash check run from the wrong working directory. Coordinator also had one preliminary `Get-FileHash` invocation whose hashtable-array argument was interpreted as one invalid path; the corrected explicit `-Path` call successfully hashed all four files. No code changed after these corrections. No tests/imports/probes/process inspection/wrapper/self-check/preflight/runtime/evidence writes ran.

## Independent review gate

Submit exact W/S/H/P bytes to independent Sol review 20 for the complete retry-4 cross-file path, four-literal inverse proof, root safety, ownership/fallback, unchanged review-19 diagnostics, and preservation of all 26 old evidence files and protected source/config/test files. Keep retry-4 absent through review. No self-check is authorized by this disposition.

Retry-3 remains consumed/non-PASS. The outer `pwsh` exit 1 versus recorded internal exit 2 and the historical unsaved `957157…` S digest remain unresolved. A separate coordinator gate is required before one later retry-4 self-check. Candidate remains **NO-GO and unservable**, build 3 unreserved. No runtime collection, manifests, GIS/numerical/build, serving/publication or browser action. No commit, push or merge.
