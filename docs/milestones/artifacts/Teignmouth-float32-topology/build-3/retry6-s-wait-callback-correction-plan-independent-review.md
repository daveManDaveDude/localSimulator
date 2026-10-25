# Independent plan review — S tree wait/callback correction

2026-10-25. **FIX REQUIRED.** Issue `Teignmouth-float32-topology-representation-1`; non-implementing Sol reviewer `/root/sol_retry6_path_plan_review`, under disposition 131. One specification/scope contradiction prevents plan PASS. This is a plan review, not implementation authority or a runtime result. Stop for coordinator decision.

## Exact reviewed bindings

Independently rehashed the existing plan, diagnosis and current W/S/H/P files:

| Artifact | SHA-256 |
| --- | --- |
| S correction plan | `aea258794780a4d2c7daeea69d472500e87ecb0ae7fce43e21dde6bc357259d6` |
| Accepted retry-6 diagnosis | `60070d106c7e81ea492e05591c3db16bbe3d25300466b9bce34072859c3ad220` |
| S | `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff` |
| W | `f600efc92fd040aa5b91cf543210be139ed50f895eba7d62c34175e73dc7dc8b` |
| H | `75678b51d0e17d89862bf0a7ee3446014969ba73aae6cd31606288553b163e27` |
| P | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

All match the plan and current accepted source bindings. Read dispositions 130/131, the current checkpoint and the accepted diagnosis; inspected source text for `_assert_tree_contained`, `_wait_process`, `_process_list`, clock/handoff validation, the self-check tree block and downstream identity/termination/record paths. Earlier hash-bound diagnostic and path-binding reviews remain applicable to unchanged bytes. No consumed evidence contents were read, and no claim about a saved record beyond the authorized diagnosis references was newly established. Actual host model/effort telemetry is unavailable.

## Actionable finding

**F1 — The unchanged census helper cannot establish the plan's required complete final census.** This is a specification contradiction/missing proof mechanism, not a newly observed runtime failure.

The plan's sequence steps 3 and 5, resource/failure section and acceptance matrix require a complete final containment census, rejection of incomplete/error census, and a final completion flag only after that proof. Yet S405–406 in the pinned `_assert_tree_contained` is simply:

```python
if not kernel.Process32NextW(snapshot, ctypes.byref(entry)):
    break
```

It does not capture or validate why enumeration stopped, and returns no completeness status to the proposed local closure. The following ancestry and Job comparisons operate on whatever prefix of rows was collected. Therefore the helper can return normally after an enumeration failure; strict pre/post clocks and a periodic/final call counter cannot distinguish that return from a verified complete enumeration. A second/final invocation can repeat the same missing-proof condition. The wrapper could then mark `final complete` and proceed to the unchanged downstream checks even though the stated final completeness criterion was never established. Specific intended-child identity/membership checks do not prove that the omitted remainder of the process enumeration was checked.

This limitation already exists in the baseline; the proposed correction did not create it. It nevertheless blocks the new plan's explicit completeness/fail-closed promise. The permitted S4059–4068 replacement and prohibition on changing `_assert_tree_contained` or introducing another scan cannot supply the absent termination proof. Prior acceptance of unchanged code and the retry-6 diagnosis cannot substitute for that proof or silently redefine `complete` to mean only `returned without raising`.

**Required resolution:** return to the coordinator for an explicitly bounded S-only scope decision and revised plan that can establish verified enumeration completion and reject unknown/error termination before a final success flag. Preserve default/build/preflight behavior and all existing identity/Job/cleanup/deadline rules, or explicitly identify any strictly necessary authorized adjustment. Do not implement a shared-helper change, duplicate scan, new API, permissive error interpretation or acceptance waiver under this plan. Do not resolve this by deleting the incomplete-census stop condition. The revised plan needs independent review before implementation release.

## Remaining criteria

| Criterion | Assessment |
| --- | --- |
| Proposed source scope | The ten-line S self-check tree wait block is clearly bounded and can host local closure/state/diagnostic wiring without changing shared callers. W/H/P, paths, normal stage and downstream S4069 onward are explicitly preserved. **Blocked only by F1's incompatible completeness requirement**, which cannot be silently addressed outside this scope. |
| Clock domain and budget | Sound design: inherited authenticated `deadline`, current `time.monotonic`, `deadline-1.0` containment bound and strict `tree_wait_started+3.0 < containment_deadline`; equality/insufficient opportunity rejects. No ten-second budget restart/increase or new clock domain. Pre/post closure checks reject at/equal containment deadline. Existing native/API/allocation non-preemption and no cleanup-duration guarantee are candidly retained. |
| WAIT_TIMEOUT and horizon crossing | Sound separation: shared `_wait_process` can invoke containment after a timeout crosses only the local horizon; closure work remains under the distinct inherited containment bound. A census crossing the wait horizon may finish within that bound but cannot replace the mandatory final call. Explicit errors propagate. No blanket TimeoutError catch or conversion to expected timeout is permitted. |
| Early exit and rounding | `tree_timeout=false` keeps the existing early-exit rejection. A true return must be accompanied by a fresh clock at/after the actual horizon and before containment deadline; the shared sub-ms early timeout cannot pass on assumption. No sleep/spin/shortened successful probe is proposed. |
| Counts and final gate | Sixteen periodic calls plus one separate final call bound the added work. Count-before-snapshot and second-final-call refusal are explicit. Zero periodic completion or a wait-only return cannot replace the post-horizon final proof. Native error, bound exhaustion, failed/late final call rejects immediately; **successful complete proof still requires F1 to be resolved**. |
| Existing Job/identity/termination | Marker processing, launcher/interpreter ancestry/creation/hash verification, exact child and launcher membership, active count, owned Job termination, zero active count, root exit/deadline and output-absence gates remain byte-identical after the replacement. Finally cleanup cannot repair a missing gate or turn rejection into PASS. No PID31876/conhost exemption or outside-process cleanup is introduced. |
| Fixed diagnostic addition | An additive `treeProbeBoundary` group is compatible with the existing dictionary record construction and update/serialization route inspected here: no strict unknown-key consumer was found in the inspected W/S path. Fixed scalar keys/status enums, no row/iteration arrays or arbitrary error strings, null/unavailable handling and independent mandatory local state bound its role. It must not label unverified enumeration `complete` (F1). No new file/schema version or pre-termination persistence is proposed. |
| Primary exception/status handling | Plan requires best-effort status updates within handling that cannot replace the original API/clock/census exception, followed by bare rethrow. Initial allocation failure blocks proof startup; success-path record failures cannot create proof. Existing S catch/finally persistence remains unchanged. Independent actual-byte review must check the nested exception structure and mandatory-state ordering; prose does not establish a future implementation passed. |
| Preservation and later review | Exact S inverse must restore `1cee4b…`; W/H/P and all consumed retry-6 path literals remain unchanged. Expressly released later S Ruff check/format-check plus diff/hash/inverse/branch review, full 70-file name/count/hash comparison (53 prior + 17 consumed retry-6), six protected hashes and independent actual-byte acceptance are mandatory. Missing permission/check or drift stops; no present preservation gate is claimed. Reused diagnosis/normal-stage evidence cannot supply future final-census/runtime proof. |
| Authority | No retry-7 path/root or execution is proposed. All prior attempts/correction counters carry forward. Candidate stays NO-GO/unservable, build 3 unreserved. Geographic/source/pending-AOI/product/synthetic constraints, no GIS/numerical build/serving/publication and separate future path plan/review/one-use gate requirements remain intact. |

## Work and limitations

Only static document/source reads/excerpts/searches and hashing of the explicitly listed existing plan/diagnosis/source files occurred, followed by writing this review. No source/evidence/checkpoint/ledger edit, retry1–6 evidence-content read, parser/compiler/linter/test/import, runtime/process inspection, path/ancestor/absence/alias/root operation or invocation occurred. No preservation comparison or runtime measurement was run. No efficacy, scheduling, census duration, hard wall-time, cleanup or durability claim follows. Historical outer exit1/internal2 and residual PID31876 identity/ownership remain unresolved.

Stop for coordinator decision on F1. No source correction, fresh path, attempt, build or invocation is authorized by this report.
