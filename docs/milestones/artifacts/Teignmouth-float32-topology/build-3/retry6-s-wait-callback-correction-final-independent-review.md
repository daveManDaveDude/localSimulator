# Independent actual-byte review — final S wait/census correction

2026-10-25. **PASS for static implementation review only.** Issue `Teignmouth-float32-topology-representation-1`; independent non-implementing reviewer `/root/sol_retry6_path_plan_review`, under D145. No actionable finding remains within D134/v2, D137 and the two accepted formatting plans. Actual model/effort telemetry is **unknown**. This reviewer implemented none of the current source changes. Stop for coordinator decision; this report grants no path or invocation authority.

## Exact bindings and inverse proof

Independently hashed the actual final handoff and W/S/H/P:

| Artifact | SHA-256 |
| --- | --- |
| Final implementation handoff | `7cb7c2887d5d686baa8f0690889a1dc37af8cbc4659f52b0ae045dd07d305793` |
| S,239737 bytes | `fda96d4edd66327e50c34ee1345d1a098aced4a7b58dcd1c088a4cd8c44c616f` |
| W | `f600efc92fd040aa5b91cf543210be139ed50f895eba7d62c34175e73dc7dc8b` |
| H | `75678b51d0e17d89862bf0a7ee3446014969ba73aae6cd31606288553b163e27` |
| P | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

All match D145/the handoff. Independently rehashed v2 plan `d44d4133875c8b5d378335ee176a01637961980846ad76521f69743245e67e05`, its independent plan review `e8e7c30ba8622e80ed604385c146fdc277a60356dc507211df77ef4978d5a404` and D137 proof report `e424848a43bc48503b04a5ec15da550506907dd12ff3169e0575508b41edadef`; all match accepted bindings. Accepted E501 plan/review and lambda plan/review remain those reviewed earlier in this same independent session.

Performed the exact source inverses anew entirely in memory, without executing/reconstructing a file on disk:

| Independent inverse result | Bytes | SHA-256 |
| --- | ---: | --- |
| Reverse only the unique one-line sampling lambda collapse |239775| `7a1c38fe72ea274777538135154200c03cd5de8eeb6f4cd3d8d0b89b169228cc` |
| Reverse only the two TimeoutError call wraps |239683| `96daa955ce2ebe7a6315c000c99f174189d26bcf8941684541703ef688d921c7` |
| Reverse only the two D134 S regions, retaining their exact baseline LF ownership |232527| `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff` |

The final reconstruction restored the original helper declaration/body by removing only its strict additions and restored the original ten-line tree wait block, with baseline separator ownership. Its full digest independently proves all bytes outside the authorized regions unchanged, including shared wait/default call-site text, `_api`, paths, normal stage and downstream identity/termination/catch/finally code. No source normalization was performed. D137's separately bound failed-candidate90c3e9…/232525 and A-end/B-end two-LF seam result are reused as historical proof; that finite seam search was not repeated here. The independent full baseline restoration above does not rely on mere byte-count agreement.

## Actual branch and contract review

| Criterion | Actual-byte assessment |
| --- | --- |
| Strict terminal error and same snapshot | **PASS.** S397 defaults the keyword-only option false. The existing65536-row snapshot loop records a row, then strict mode calls set_last_error(0) before its existing Next operation. On a false Next, S421 only tests the local strict option before S422 immediately captures get_last_error; no native call, clock, telemetry or close intervenes. Exact-int18 is required before breaking. Other/unknown/error status raises inside the snapshot try; no collected prefix reaches ancestry or Job comparison. Capture precedes finally-close, and errors use the retained numeric value. |
| Bounds and proof | **PASS.** Snapshot/first failure still raises; strict first-empty is not promoted. Row65536 followed by false18 can complete; true exhausts the loop and raises. Existing64-pass ancestry/deadline/convergence and bounded Job membership comparison remain unchanged. Strict-only fixed proof allocation follows all those checks; default returnsNone. Wrapper requires three exact true flags, exact-int18 and exact-int rowCount1..65536, then a successful post-clock. Error or allocation failure cannot yield a completion. Proof means completion of the accepted algorithms, not new snapshot-incarnation authentication or a broader membership predicate. |
| Default/normal/build/preflight | **PASS.** S3876/3906,4552/4557,4871/4885/4990 keep omitted/default false calls. Only S4156 passes strict true. Default mode performs no added set/get-last-error or proof allocation and keeps original Next-false handling, membership rejection and returnNone. The helper has a harmless local terminal-error initialization and explicit None return; no default acceptance behavior changed. Loader/prototypes and separate parent enumeration are inverse-proven unchanged. |
| Deadline and wait | **PASS.** Tree-only containment bound is inherited deadline-1.0; wait horizon is monotonic start+3.0 and must be strictly earlier. Shared `_wait_process` is unchanged. Periodic strict closure and optional sample receive the containment bound; native WAIT_TIMEOUT may cross only the shorter wait horizon without automatically expiring the census bound. Closure checks time before census and after valid proof; equality/late completion raises. No budget reset/increase, sleep/retry or added watchdog exists. |
| Final gate/rounding/early exit | **PASS.** Wait false rejects early process exit. Wait true requires fresh observed time at/after cutoff and strictly before containment deadline; sub-ms early true rejects. One final strict census follows before markers, guarded by finalAttempted, with downstream mandatory local finalComplete assertion. Periodic success or wait-only true cannot replace it. Prior callback errors propagate immediately and prevent final admission. |
| Counts and records | **PASS.** Periodic attempts cap16 before snapshot; finalAttempted prevents another final call. Fixed scalar treeProbeBoundary is additive in the existing record; local tree_state controls acceptance. No rows/history/new file/schema version/persistence call was added. Successful completion flags follow proof and post-clock. Initial diagnostic allocation/assignment failure blocks, and later diagnostic failure propagates rather than admits a result. Field assignment cannot rescue rejected mandatory state. |
| Error preservation | **PASS.** Closure and wait error-status updates use nested best-effort BaseException handling followed by bare raise, preserving the existing primary. Clock/proof/census failures are never converted to expected timeout or retried. A late status remains late; other failures become failed when record mutation is available. Missing final proof cannot be recovered by later cleanup. Existing S outer error serializer/persistence/finally code is inverse-proven unchanged. |
| Identity/Job/cleanup | **PASS.** Unchanged marker, launcher/interpreter native ancestry/creation/hash, exact child/launcher Job membership, active count, termination-confirmed/zero, root exit/deadline and output-absence gates follow the final proof. Snapshot close stays finally-owned; no extra process API/right/termination target was introduced. Normal exit7/7 and complete zero/empty/zero gate remains unchanged. No PID31876/conhost exemption, count subtraction, disappearing-PID override or cleanup-to-PASS route exists. |
| Formatting/path confinement | **PASS.** Both exception wraps preserve full strings/classes and branch placement; the collapsed lambda preserves argument order/deferred invocation. Inverse restoration matches each accepted intermediate digest. All four retry-6 literal bindings and unchanged W/H/P bytes remain bound; no retry7 substitution or other path change occurred. |

## Static and preservation gate evidence

Reviewed the exact final handoff's two pipeline-venv commands and D144 outputs:

```text
python -m ruff check pipeline/scripts/run_teignmouth_float32_build3.py
All checks passed!
python -m ruff format --check pipeline/scripts/run_teignmouth_float32_build3.py
1 file already formatted
```

The handoff records these at the same actual final S digest independently verified above. It retains the earlier two E501 failures and subsequent format-requested lambda collapse; it does not promote either preliminary failed gate to PASS. D145 required a corrected typed-signature marker assertion, not a source change or rerun. Its recorded twelve corrected checks match the actual typed signature/strict call/proof/final/cleanup branches inspected here. The earlier untyped-signature and exploratory final_snapshot/cleanup matcher errors are recorded as verification-script mistakes, not source findings or successful gates. The handoff's earlier reference to13 markers is superseded by its explicit twelve-item exact corrected output and causes no source or required-proof ambiguity.

Preservation evidence is the D144 full filename/count/hash result carried in the hash-bound final handoff under D145: original2 + retry1=2 + retry2=11 + retry3=11 + retry4=11 + retry5=16 + retry6=17 = **70/70**, zero missing/changed/duplicate/unlisted. The accepted cycle-1 53-file matrix and D129's full17-row retry6 metadata inventory supply the bound populations; the D129 inventory was inspected as report metadata, not consumed contents. Handoff's six protected bindings match the accepted values:

| Protected binding | SHA-256 |
| --- | --- |
| Candidate | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| Topology helper | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| Builder | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| Focused test | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| Fixture | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| Config | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |

These Ruff/preservation outcomes are reviewed recorded gate evidence, reused exactly as D145 requires; they were **not independently rerun or re-traversed** here. No current protected/evidence filesystem rehash is claimed. The handoff states no source/evidence change after D144; current independently checked source digests match that run. Static gate PASS is not runtime proof.

## Work, limits and stop

Only static source/document/report/matrix reads/searches, listed source/report hashes, source-byte inverse arithmetic and this review write occurred. No consumed retry1–6 evidence contents were read. No tests/imports/parsers/compiler, gate rerun, preservation traversal, process/path/ancestor/alias/root/runtime/self-check/preflight/build, browser/publication, commit/push/merge or source/evidence/checkpoint edit occurred. Only this review artifact was written.

The total ten-second inherited QPC budget,20ms W diagnostic opportunity/one-second reserve and accepted ownership/cleanup limitations remain. Native calls/allocation/scheduling/persistence cannot be preempted by these checks. This review establishes no runtime efficacy, census latency, hard wall-time, cleanup-duration, durable persistence, outside-Job termination or snapshot-incarnation authentication. Historical outer exit1/internal2, PID31876 identity/ownership and unsaved957157… provenance remain unresolved.

Retries1–6 remain consumed/immutable/non-PASS, all counters carry forward; current retry6 literals remain non-invocable. Retry7 remains unselected/unreserved. Candidate remains **NO-GO/unservable**, build3 unreserved; pending AOI/product/geographic/source/synthetic constraints remain intact. **Stop for coordinator decision.** A future path plan/review, actual-byte acceptance and separate immediate one-use gate are still required before any new invocation.
