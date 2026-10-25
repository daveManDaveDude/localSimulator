# Coordinator disposition 80 — accept unexpected-member diagnostic plan

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Dispositions 64, 78–79 and the user's authorization for as many attempts as needed to pass the supervisor self-check.

## Plan accepted

Accept Sol's S-only plan `docs/milestones/artifacts/Teignmouth-float32-topology/build-3/retry3-unexpected-member-evidence-plan.md`, SHA-256 `1e3bdb230ca7a1c2f7cbcea9ebe0c1dc6b1d9d960a51502adf5e5d40f46afbe4`. Coordinator recalculated the plan and disposition-79 hashes; both match their recorded values. Current S baseline is `d498bc294390d8645c6acc59773ba50f417493926d8bbfb3564d34504e8a407a`; W/H/P and consumed retry-3 evidence are pinned by the plan and disposition 78.

The purpose is diagnostic evidence only. Preserve the complete primary inner-Job census unchanged and enrich it immediately with bounded same-handle detail for at most eight unexpected PIDs from that exact complete snapshot. Unknown, inaccessible, late, disappeared, mismatched, reused or partially observed identities remain unknown. Any original unexpected PID stays sticky BLOCKED regardless of later disappearance, signaled state, familiar image or final zero. No in-interval census is added because spare time/fit is unproved. No acceptance/rejection, deadline, launch flag, Job, exit, containment, tree probe, schema ID, path, mode, dependency, W/H/P or candidate/data behavior changes.

## Reserved implementation and review gates

Reserve one Luna implementation cycle in S only. Add only the existing-record diagnostic fields/helper described in the accepted plan, using existing APIs/rights, exact owned-Job IDs and the original deadline. Preserve per-field partial errors, one acquired handle/one CloseHandle attempt, PID-reuse uncertainty and separation of diagnostics from the complete primary snapshot. Reporting failures must not mask primary capture/rejection/cleanup. Keep retry-3, retry-2, retry-1 and original evidence byte-for-byte unchanged.

Luna may run only S Ruff check/format and plan-authorized static syntax checks. No tests, imports, probes, process inspection, wrapper/self-check/preflight/runtime, or evidence/root writes. Independent Sol review is required; a separate fresh retry-4 fixed-path plan/review and coordinator execution gate would be necessary before any later one-shot self-check. Retry-3 cannot be reused. This disposition authorizes no operation.

Preserve the outer command exit 1 versus recorded supervisor/launcher exit 2 discrepancy as unresolved. The unsaved/untraceable `957157…` S hash remains unresolved. Candidate remains **NO-GO and unservable**, build 3 unreserved. No runtime collection, manifests, GIS/numerical/build, serving/publication or browser action. No commit, push or merge.
