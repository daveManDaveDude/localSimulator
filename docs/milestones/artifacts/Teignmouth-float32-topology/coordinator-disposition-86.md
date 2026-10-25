# Coordinator disposition 86 — accept exact retry-4 path plan

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Dispositions 64, 85 and the user's authorization for as many attempts as needed to pass the supervisor self-check.

## Plan accepted

Accept Sol's read-only plan `docs/milestones/artifacts/Teignmouth-float32-topology/build-3/retry-4-path-binding-plan.md`, SHA-256 `249ebefbca3a6ffa4a65245e5c543ad12aab506876b7e4be910883a8d2a6e74b`. Coordinator recalculated its hash and the disposition-85 hash.

Reserve one Luna implementation cycle for exactly four path-literal substitutions across W/S/H: W's two retry root literals, S's `SELF_ROOT`, and H's `EVIDENCE` leaf, changing retry-3 to `.codex/build3-supervisor-selfcheck-retry-4/` and `run-1`. Current inverse baselines are W `c3f1f49cb574793c1cdbc2d905fd3d36f646b6f32ffb7c200a96c9792d5ce84f`, S `886280c5c5aeaf519929a5b6b1fa3c78c72a9f7a6874fbd8c4d60f09abdbb7e6`, H `cf1145b33397066559b89c11aa1cb0ebcf4d6d4d470f6521d96fe9e1f4ecccab`; P stays `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`.

Coordinator rechecked retry-4 parent absence and case-insensitive alias absence. `C:\`, `C:\vibe`, workspace root and `.codex` are canonical directories without reparse attributes. These are point-in-time checks; repeat them at implementation/review handback and before any later invocation. Keep retry-4 absent through implementation and independent review. Preserve all 26 original/retry-1/2/3 evidence files byte-for-byte.

## Reserved implementation and gates

Luna may make only the four accepted literals and run plan-authorized static gates: Ruff check/format on changed S/H, PowerShell AST parse without invoking W, and exact in-memory inverse byte/hash proof to the pinned baselines. No tests/imports/probes/process inspection/wrapper/self-check/preflight/runtime/evidence/root edits. Independent Sol review must pass the complete W↔S↔H path contract, root safety, inverse hashes and preservation matrix. A separate coordinator execution gate is required before exactly one retry-4 wrapper self-check. A future result may not repair/alter any historical root.

Retry-3 remains consumed/non-PASS. The outer exit discrepancy (1 versus internal 2) and historical `957157…` S digest remain unresolved. Candidate remains **NO-GO and unservable**, build 3 unreserved. No runtime collection, manifests, GIS/numerical/build, serving/publication or browser action. No commit, push or merge.
