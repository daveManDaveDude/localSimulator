# Coordinator disposition 126 — release four-literal retry-6 path-only implementation

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User's continuing authorization; dispositions 124/125; Sol path plan and independent PASS.

## Plan review accepted

Accept `build-3/retry-6-path-binding-plan-independent-review.md`, SHA-256 `b96b2e89c738f2e61a41410cb1775321a22c8da53e393a47e6dc854fae2e6bc3`, as **PASS for the plan only**. The exact proposed retry-6 root and leaf, four current retry-5 consumers, producer/fallback paths, future Windows path/alias/reparse/containment checks, blocking output paths, evidence matrix, preserved semantics and one-use sequencing are consistent with the accepted plan. No current path absence or safe-ancestor state has been verified.

## Bounded Luna authority — path-only source patch and handoff

Authorize Luna to change exactly the four accepted literal spans, and no other source bytes:

| File and location | Exact old literal | Exact replacement |
| --- | --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`, `baseEvidence` at W23 | `.codex\build3-supervisor-selfcheck-retry-5` | `.codex\build3-supervisor-selfcheck-retry-6` |
| W, independent terminal-fallback `expectedRoot` at W344 | `.codex\build3-supervisor-selfcheck-retry-5` | `.codex\build3-supervisor-selfcheck-retry-6` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py`, `SELF_ROOT` at S39 | `.codex/build3-supervisor-selfcheck-retry-5` | `.codex/build3-supervisor-selfcheck-retry-6` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py`, `EVIDENCE` at H17 | `.codex/build3-supervisor-selfcheck-retry-5/run-1` | `.codex/build3-supervisor-selfcheck-retry-6/run-1` |

Keep P unchanged at `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`. Preserve UTF-8/LF/encoding and all other bytes. Require the exact 2/1/1 span counts, zero active retry-5 root literals in W/S/H, static consumer search with no additional path consumers, actual final hashes, and exact in-memory inverses to W `804ae8c42f6637a61505e53e825972d758b8ae2c1c2d0740ff5a076a0e703b45`, S `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69`, H `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf`. No reconstructed file may be written or invoked.

Release these implementation-handoff gates only: affected S/H Ruff and format checks with the existing pipeline virtual environment; W PowerShell AST parse without invocation; exact byte/span/inverse and consumer checks; unchanged P and six protected-file hashes; the full 53-file immutable evidence name/count/hash comparison without reading consumed evidence contents. C# is unchanged, so reuse pinned compile-only evidence. No Python imports or tests.

At implementation handoff, also perform the plan-required point-in-time **read-only** path checks against the exact proposed root and ancestors: canonical workspace/drive/ancestor directory types and resolution; no reparse/junction/symlink or escaped containment; case-insensitive and trailing-dot/space normalized alias absence; retry-6 root absent as file and directory with all proposed descendants consequently absent; and both candidate-output blocking paths absent. Do not create a probe, reserve, create, adopt, rename, repair or delete any path. An occupied/ambiguous/missing/inaccessible path, alias, unsafe ancestor, unavailable check, changed source premise or output blocker is a stop; no alternate retry number or fallback is authorized.

Write a complete path-only handoff with exact source hashes/diff/inverses, actual command output, preservation results and time-stamped path observations. Stop after handoff for a separate independent Sol actual-byte review and coordinator decision. This authority does not select/reserve the path for execution and grants no runtime or self-check permission.

## Prohibited work and preserved status

No C# compile rerun, tests/imports beyond the expressly released static Ruff/format gates, process/runtime probe, invocation, W/S/H/P operational execution, self-check/preflight, retry-6 root creation, candidate/GIS/numerical build, reservation, browser/publication, commit, push or merge. Retries1–5 remain consumed, immutable and non-PASS; issue counters are unchanged. Retry-6 remains proposed, unselected and unreserved. Candidate remains **NO-GO and unservable**; build 3 unreserved; 10-second QPC deadline unchanged.
