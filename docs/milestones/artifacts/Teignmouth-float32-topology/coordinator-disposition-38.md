# Coordinator disposition 38 — authorize a new bounded plan only

Date: 2026-10-24

**Decision: GO for one independent Sol remediation plan only, explicitly authorized by the user's latest “I authorise” in response to the request for a new bounded plan.** The plan is limited to the two findings in review 17 and must inspect the current four supervisor files. This disposition authorizes no implementation, correction attempt, static gate, script invocation, runtime phase, diagnostic, GIS work, build, browser check, dependency change, metadata execution phase, or budget reset.

Source: build-3/independent-supervisor-review-4.md, SHA-256 31868114ce73d72b4351f9d680d17fb89a1a081ec5b5019f33e35b55b439298a. Existing accepted operational baseline: build-3/supervisor-correction-2-plan.md. Previous correction 2/2 remains consumed and FIX REQUIRED; this is a planning authorization, not a new correction allowance.

The Sol plan must address only:

1. Complete and truthful proposed dependency/data inventory: include required runtime data independent of suffix, including PyProj data; mark absent, unreadable, unavailable, or deadline-truncated inventories incomplete; preserve loaded versus proposed-only distinctions and the fixed deadline.
2. Verify-before-import for standalone verification: validate expected frozen repository/external/runtime bindings and complete referenced file closure before imports that could execute supposedly frozen modules; preserve the separate observational collection mode and existing build-dispatch gate.

The plan may identify affected files and an implementation approach within the existing four operational files only. If either finding cannot be safely closed within those files, existing records/modes/roots/deadlines and no-new-dependency constraints, the plan must stop and identify the minimum boundary decision needed. No solution may weaken the pre-existing identity, process containment, deadline, manifest, or candidate gates.

After the plan, return to coordinator/user for an explicit implementation disposition. Candidate remains NO-GO and unservable; build 3 is unreserved. Candidate budgets remain diagnostics 2/2, Luna corrections 4/4, candidate Sol correction 1/1, builds 2/6 used and zero reserved, confirmation 0/1 ineligible. Operational correction 2/2 remains failed and consumed. This plan consumes no candidate or correction counter and creates no runtime permission.
