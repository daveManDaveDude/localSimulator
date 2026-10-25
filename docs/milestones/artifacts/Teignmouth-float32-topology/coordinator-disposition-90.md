# Coordinator disposition 90 — accept retry-4 diagnosis; request a bounded plan

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User authorized as many attempts as needed. This preserves all used/consumed counters and requires serial independent gates.

## Diagnosis accepted

Accept Sol's read-only report `docs/milestones/artifacts/Teignmouth-float32-topology/build-3/retry4-conhost-lifecycle-diagnosis.md`, SHA-256 `c17894b5a1bbdd251b3b3005a8d90ef220edaed66d1782cc04313b2826811a26`, as the bounded diagnosis of retry-4. Its evidence supports—but does not prove—a console-host lifecycle at the CPython venv redirector boundary: S creates a consoleless launcher with `CREATE_NO_WINDOW`; the redirector's reference behavior creates its interpreter with flags zero; the unexpected `conhost.exe` creation time falls between those known process creations; and the observed Job later emptied. The census-to-detail process association and exact console ownership remain unproved. The retry-4 rejection remains correct. No conhost allowlist or historical PID reinterpretation is accepted.

## Plan-only scope

Request a concrete Sol plan for the smallest **S-only self-check helper launch** change that could prevent creation of an avoidable new console while keeping the unexpected-member rule strict. The plan may assess a bounded current-console precondition such as `GetConsoleProcessList`, restricted to proving that authenticated S is attached to an existing console before any inheritance branch. It must specify exact API semantics, finite buffer and deadline behavior, fail-closed cases, and the two fixed helper launch call sites.

Any proposed inheritance policy is limited to `_selfcheck`'s normal-helper and tree-root helper launches. It must preserve redirected standard handles, suspended creation, Job assignment before resume, authenticated venv-to-base process chain, the exact unexpected-member rejection, complete zero/empty/zero gate before tree probing, existing 10-second QPC deadline, handle ownership/cleanup and primary-error reporting. The default launch flags for every other caller must remain unchanged. No conhost exemption, wait-for-disappearance override, count subtraction, new console/window, detached process, breakaway, bypass, wider preflight/build change, or changed acceptance threshold is acceptable.

The Sol deliverable at this disposition is a **plan only**: exact source locations, feasible implementation and technical references, failure behavior, focused static/test requirements, independent review criteria, and stop conditions. It is not authority for a Luna edit or another wrapper call. A separate independent Sol review must pass the plan before coordinator can authorize implementation; implementation then needs independent review and its own fresh-root path/review/coordinator gates before any one-shot self-check.

## Preserved boundary

Retry-1 through retry-4 remain consumed, immutable and non-PASS; retry-4 evidence/hashes remain under disposition 89. No self-check, process probe, runtime, preflight, test execution, GIS/numerical/candidate build, reservation, serving/publication, browser action, commit, push or merge is authorized here. The outer exit 1 versus recorded internal exit 2 and the historical unsaved `957157…` digest remain separate unresolved facts. Candidate remains **NO-GO and unservable**; build 3 unreserved.
