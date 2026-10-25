# Coordinator limit decision 1 — candidate-local terrain change

**Date:** 2026-10-24  
**Scope:** `Teignmouth-corridor-prototype-continuation-1` only  
**Authority:** The user explicitly reset the continuation's counters and delegated candidate-limit choices: “Now reset all attempt counters, and continue and I give you permissions to limits as you see fit.”

## Decision

Change only the continuation candidate's strict absolute source-relative terrain-change cap from `<6.0 m` to `<6.5 m`. Keep every other candidate limit, source, chart, recipe, AOI, package, and product behavior unchanged.

## Evidence and rationale

The build-5 report stopped on the first violating sample, so it did not reveal the complete sample maximum. Sol's bounded diagnostic 1 continued the exact build-5 preflight calculation across all **21,336 unique required samples** without changing the recipe or threshold. It found:

- Maximum sampled absolute change: **6.3978483909 m** (cut), at station **145.59737995 m**, lateral **−4.68870057 m**, X/Z **`[-144,-98]`**.
- Maximum sampled fill: **+3.1074350717 m**.
- **49 samples** exceed the former strict `<6.0 m` cap.
- The diagnostic reproduces build 5's first failing sample and is bound to the build-5 inputs; see [diagnostic evidence](diagnostic-1/full-field-earthwork.json).

The new cap leaves about **0.102 m** above the required-sample maximum so the same frozen recipe can proceed to final Float32-mesh and source/patch overlay-extrema checks. That margin is a selected cap allowance; it is not evidence that the unsampled field or mesh error is 0.102 m or less. The final mesh and overlay extrema must independently satisfy `<6.5 m`.

The measured recipe-sample maximum is below the earlier topology run's reported **6.460917 m**, but the new 6.5 m cap itself is slightly above that historical value. Do not claim that the cap guarantees lower earthwork than the earlier topology. This is not a safety certification, a surveyed-road claim, or a global terrain-policy change.

## Required validation

Use the one eligible Sol correction to update the candidate-only cap, related tests/evidence text and ledger bindings. Run fresh implementation build ordinal 6 once, using the established pipeline virtual environment. Preserve build 5 and diagnostic 1. Continue only to observe the existing offline validations; do not bypass any gate. Browser/product integration remains blocked until every required offline gate passes. One independent confirmation build remains reserved for a passing candidate.
