# Post-review-9 bounded W caller/handoff ownership plan

2026-10-25. Sol 6.1 medium planner `/root/sol_review17_plan`. Read-only planning under disposition 60, following the user's authorization of exactly one bounded correction, independent Sol review, and one fresh wrapper self-check attempt if review passes.

**Feasible in W only.** Review 9 is correct: the previous correction overlooked the retained distinct handoff update call. Preserve the secure caller-only checks and give W's separately created handoff its own exact ownership/state-transition contract. This plan performs/authorizes no implementation or execution and creates no retry evidence. Return to coordinator for reconciliation and Luna implementation dispatch under disposition 60.

## Exact inspected baseline and preservation

The following SHA-256 values were recalculated from actual files:

| File | SHA-256 |
| --- | --- |
| Disposition 60 | `da34dd10f591f3158b500b4046f62e9bcecb4049e3a4f0c05498998ea50d40d8` |
| `build-3/independent-supervisor-review-9.md` | `e603b86ff5c1baff29af17f4084ff916dfe155f77cbbed4f8f64287a8ac9044a` |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `1ef041092e304a6a7f270d0886e4529caeba615bf14a3fb654f92b9873a61604` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `17a7a347b175bfa3ad1a1dcbdc4167d3d4b1c8a73da0dc09d537ec1c6d4a8ef6` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `3419551b5c19e69c2487bb57c1bc49c102d4b7bfe1db1f93aea60cf038ebe05a` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| Original failed caller | `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e` |
| Original failed `.update` | `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75` |

Disposition/review paths are under `docs/milestones/artifacts/Teignmouth-float32-topology/`. Original failed files remain under `.codex/build3-supervisor-selfcheck/`, byte-identical and immutable. Static absence inspection found `.codex/build3-supervisor-selfcheck-retry-1/` absent; no descendant evidence can exist there. Keep it absent through planning, implementation and review.

Only W may change. S/H/P, candidate/source/test/configuration/GIS/product bytes, original evidence, schemas/modes/commands/environment and prior artifacts remain unchanged. Historical operational Luna 4/4 and Sol 1/1 remain consumed; disposition 60 supplies exactly one new bounded Luna correction, not a reset or extra Sol correction. A failed independent review ends that allowance.

## Current call-site defect and allowed destinations

Current `Update-OwnedJson` (118 onward) invokes `Assert-OwnedCallerDestination` at 121 and 153. Caller save at 955 correctly targets `$callerPath`; handoff update at 1255 targets distinct `$handoffPath` after the suspended launcher is created but before Job assignment/resume. Caller-only validation must continue to reject the handoff. Dispatch it to a different validator; do not relax that validator to accept two unrelated schemas or arbitrary files.

Give `Update-OwnedJson` an explicit mandatory internal record kind restricted to **Caller** or **Handoff**. Call sites must name the kind; do not infer authority solely from the submitted record's schema/path. A small dispatcher invokes the corresponding validator both before exclusive pending creation and immediately before `File.Move(source,destination,true)`. Unknown kind/path combinations are refused. Path must match the exact canonical selected-mode constant using exact spelling, not merely containment, suffix or a path supplied by the record.

| Kind | Only destination in the selected existing mode | Allowed caller |
| --- | --- | --- |
| Caller | Existing `$callerPath`, from fixed mode parent plus `caller-invocation.json`; self-check is exactly `.codex/build3-supervisor-selfcheck-retry-1/caller-invocation.json` | `Save-Caller`, retaining caller ownership, deadline, error/fallback behavior |
| Handoff | Existing `$handoffPath`, from the existing fixed switch: build `dispatch-handoff.json`, self-check `self-check-handoff.json`, standalone `runtime-preflight-handoff.json` | The single suspended-launcher binding transition at current 1255 |

Selecting a mode does not authorize executing it. No validator may accept a different mode's fixed path, `.update`, consumed record, start marker, fallback filename, arbitrary sibling, original failed root, missing destination, or merely same-schema file. Existing terminal fallback remains exclusive and is never passed through the replacement dispatcher.

## Caller ownership contract — retained and explicit

For Caller, keep all current `Assert-OwnedCallerDestination` checks: `$callerRecordOwned` and `$callerParentValidated`, exact fixed canonical destination, safe existing parent/path with no reparse, existing regular file, parsed invocation ownership matching current schema/wrapper PID/start QPC/mode. Require the literal existing caller schema `teignmouth-build3-caller-record-v2` in both supplied and persisted records, rather than permitting a supplied record to redefine the expected schema. Do not weaken checks for the handoff use case. Supplied caller record still belongs to the current wrapper/start/mode; legitimate evolving caller telemetry/status fields remain permitted.

Retain exclusive initial caller creation before ownership becomes true; no adoption of an existing caller or pending file. Preserve final non-PASS/error/fallback behavior, including the fixed exclusive `caller-invocation.failure.json` path only in the existing self-check retry root. Caller saves after handoff consumption must not require the handoff to remain present: their authorities are separate.

## Handoff ownership contract — exact prepared identity and one transition

1. Initialize separate `$handoffRecordOwned=false` and `$handoffLauncherBound=false` before any setup. On successful exclusive `Write-ExclusiveJson $handoffPath $handoffRecord` at current 1202, acquire handoff ownership only after full write/flush/close completes. Keep a **separate immutable in-memory copy** of the prepared scalar record, not an alias to `$handoffRecord`, which later mutates. All current handoff fields are scalar; clone/copy that exact key/value set. Compute/retain the prepared file's SHA-256 through the existing inherited-deadline-aware hash function, checking its parsed identity against the trusted prepared copy. This creates no new record or schema.
2. The Handoff validator requires handoff ownership, validated parent, exact `$handoffPath` for current mode, canonical existing regular destination/no reparse ancestors, and an absent consumed handoff and supervisor-start marker. It must not use `$callerRecordOwned` as a substitute for handoff ownership, though caller ownership remains a required overall invocation prerequisite. A matching nonce in an old file alone grants no ownership.
3. Parse the persisted handoff and require its exact expected key set and values to equal W's trusted **PREPARED** snapshot. Require prepared status, `oneUse=true`, existing schema `teignmouth-build3-parent-handoff-v2`, and all four prepared launcher-observation fields null. Reject extra/missing/malformed fields and type/coercion ambiguity; compare strings exactly and integral clock/PID values without lossy numeric conversions. Hash the persisted file against the captured prepared SHA before/after reading; changed bytes, parse failure, missing/unreadable identity or expiry refuse replacement. Repeat this full check immediately before move, not merely once at entry.
4. Immutable identity fields which must match the snapshot **and their corresponding trusted W locals/constants**, in both persisted and proposed records, are:

   - schema, selected mode, phase, `oneUse`, nonce; `clockDomain=windows-qpc`, QPC frequency, original start/deadline, exact mode budget;
   - wrapper PID, wrapper creation FILETIME, wrapper native image canonical path and SHA-256 from W's already checked native identity;
   - exact expected S script path; venv launcher canonical path/SHA-256; authenticated base-interpreter canonical path/SHA-256;
   - input/external/runtime/snapshot/standalone-authorization digest fields and standalone purpose, preserving exact current mode-specific values, including **null** where required. Null cannot become an empty string or arbitrary digest to satisfy comparison.

5. Validate the **proposed** record separately from the persisted prepared record. Only these five values may change: status to `LAUNCHER_BOUND_BEFORE_RESUME`, launcher PID, launcher creation FILETIME, launcher image path and image SHA-256. It retains exactly the same full key set and every immutable field above. Require `$handoffLauncherBound=false`, `$launcherCreated=true`, `$launcherAssigned=false`, `$launcherResumed=false`; proposed PID equals the just-created suspended process's PID, creation/image identity equals W's verified `$launcherIdentity`, image path equals approved venv launcher and image hash equals the previously pinned launcher hash. No field may be accepted solely because the proposed record says it is valid.
6. The fixed pending path is exactly `<handoffPath>.update`, with its own exclusive creation/flush/close and no stale/adopted pending file. Include it in W's existing initial one-use absence checks as well as checking immediately before creation. Revalidate parent/destination/pending canonical/no-reparse checks before move, and retain positive pending-file ownership from the successful exclusive open. A pending failure never grants destination authority or permission to delete/reuse it.
7. Use the same existing supported same-directory `File.Move(pending,destination,true)` operation, not another method, delete-first or in-place update. Mark `$handoffLauncherBound=true` only after successful move. Deadline expiry or persistence failure blocks Job assignment/resume and reaches existing direct termination of the created unassigned suspended launcher. Do not advance merely because a pending record was successfully written. No second handoff transition/update is allowed, including an identical repeat.

The before-move identity check compares the destination to **prepared** state, while the pending payload is the **proposed bound** state; comparing the destination to the already-mutated proposed record would recreate a deterministic refusal. No persisted control should be silently rehashed/adopted as a new baseline. This protocol is observational ownership validation, not atomic exclusion of hostile concurrent replacement or a crash-durability guarantee.

## Minimal ordered W changes and error handling

1. Add the explicit two-kind dispatcher and separate fixed Handoff validator; preserve caller validation as above. Change exactly the two update call sites to specify their distinct kind.
2. Add/reset handoff ownership/transition flags and immutable prepared snapshot/digest around the existing exclusive handoff creation. Add fixed handoff-pending absence to current one-use refusal. No path changes or evidence preparation during implementation.
3. Preserve structured primary/secondary persistence errors for either kind: error context must name the actual destination/pending/kind and original stage. The direct handoff call currently bypasses `Save-Caller`'s recording wrapper; wrap that call with the existing equivalent structured-failure capture pattern (including secondary close failure), marking the shared persistence-failed state and caller non-PASS before rethrowing into existing cleanup. Reset per-operation stage/close context before each update, so stale caller-close metadata cannot be attributed to handoff. Do not duplicate a primary error or overwrite the first failure with final-save noise. No new error record/fallback filename.
4. Retain `Save-Caller`'s original clock/finalization rules and exclusive terminal fallback. Handoff failure occurs before assign/resume: inspect the existing catch/finally flow all the way through direct termination, exit observation, handles, caller error persistence and fallback. Do not loosen cleanup/termination truthfulness or allow a successful final caller save to erase earlier handoff persistence failure.

All new identity/hash/parse/loop operations use the original inherited deadline; no fresh timeout or retry. Self-check remains 10 seconds total, standalone 30 seconds and build 180 total/150 numerical cutoff. Expiry/partial/unavailable observation remains non-PASS. Runtime fit remains unmeasured. The existing launcher/base identity, nonce/one-use, suspended assign-before-resume, nested Jobs, archive/profile, preservation and reserved-build gates remain unchanged.

## Independent review and acceptance proof

Luna may run only disposition 60's existing static gates after implementation: Ruff check/format S/P/H, PowerShell AST parse without invoking W, and embedded C# compile-only without methods. Report exact commands/results, preliminary failures, final W hash, unchanged S/H/P and failed-evidence hashes, and absent retry root. No tests, executable probes or self-check during implementation/review.

Independent Sol review 10 must inspect actual final W, both call sites and every before/after ownership check. Required static cases:

| Case | Required outcome |
| --- | --- |
| Owned caller → exact caller | Current legitimate update remains possible; literal caller schema and current owner/path required. |
| Caller kind → handoff, Handoff kind → caller, unknown kind/arbitrary path/consumed/fallback destination | Refusal before pending creation/replacement; no broadened caller guard. |
| Exclusively owned exact PREPARED handoff → verified suspended-launcher-bound payload | Both destination validations succeed against immutable prepared identity; only five permitted fields differ; move precedes assign/resume. |
| No ownership; failed exclusive creation; old valid-looking nonce; missing destination; stale pending; altered prepared bytes/fields | Refusal; no adoption, deletion, silent hash refresh or launch progression. |
| Altered schema/mode/phase/oneUse/nonce/wrapper/start/deadline/paths/hashes/pins/purpose; null-to-empty substitution | Refusal, even when another identity component matches. |
| Proposed wrong launcher PID/creation/image/hash; already assigned/resumed or repeated transition | Refusal; no weakening of native identity or one-use semantics. |
| Serialization/write/close/hash/parse/move failure or expiry | Actual kind/path/stage and primary/secondary failures preserved; sticky exit 2; direct unassigned-launcher cleanup remains reachable; fallback remains caller-only. |
| Exact fixed self-check path and protected records | S/H/P hashes unchanged; original failed files immutable; retry root and all descendants remain absent. No schema/mode/command/environment/root/dependency change. |

A syntax PASS alone is insufficient. A failed review ends this new bounded allowance; return to user, no further correction inferred. The planner does not provide an independent PASS of its own plan or implementation.

## Execution boundary and handback

Disposition 60 provides the limited correction/review sequence and, **only after independent PASS**, exactly one wrapper-driven self-check at the already fixed fresh retry root. This plan does not issue execution permission or a command to run now. Coordinator must confirm the required PASS and preserve the self-check's actual result/evidence with a fresh original 10-second clock, no reuse/reset/retry. **No collection, identity verification, manifest preparation, candidate/GIS/numerical build, serving or browser action follows self-check without later user instruction**, regardless of its result. Candidate remains NO-GO/unservable and build 3 unreserved; historical counters and source/recipe/geometry/numeric limits remain unchanged.

Planning performed only static document/source/evidence reads, searches and hashing/absence inspection, plus writing this single new plan. No code or other file was edited, no evidence deleted/promoted, and no retry path created. No tests, parsers/linters/compilers, imports, operational scripts/runtime/self-check, manifests, collection, candidate/GIS/numerical/build or browser work ran. Browser evidence is inapplicable. Return to coordinator for the one W-only implementation and independent review; stop here.
