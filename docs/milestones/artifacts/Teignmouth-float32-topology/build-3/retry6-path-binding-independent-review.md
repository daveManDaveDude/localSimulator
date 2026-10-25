# Independent actual-byte review — retry-6 path binding

2026-10-25. **PASS for static implementation and point-in-time path review only.** Issue `Teignmouth-float32-topology-representation-1`; separate non-implementing Sol reviewer `/root/sol_retry6_path_plan_review`, under disposition 127. No actionable finding remains within the authorized four-literal patch. This reviewer previously reviewed the plan but implemented none of the source changes. Actual model/effort telemetry is unavailable; no settings change is claimed.

Reviewed handoff SHA-256 `72c8363ee53b4c71a909a162f20513525fbcbf1c1bc1b5c11ffd5e1663bc17db`, independently rehashed and matching disposition 127. The accepted plan remains `7283aa5440cda0cf35308697e95362c77b28d0ada52d2a2ac0c486dbe972a66a`, independently reviewed in `retry-6-path-binding-plan-independent-review.md` (`b96b2e89c738f2e61a41410cb1775321a22c8da53e393a47e6dc854fae2e6bc3`). Dispositions 124–127 and the current checkpoint establish the current review boundary; older checkpoint baseline entries are historical, not the current source pins.

## Exact byte proof

Independently read each complete current file as bytes, verified UTF-8 decode/encode round-trip hashes, counted literal occurrences, reversed only the four specified path spans in memory and hashed the resulting complete byte arrays. No reconstructed source was written or executed.

| Source | Bytes | Current SHA-256 | Exact inverse SHA-256 |
| --- | ---: | --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | 132204 | `f600efc92fd040aa5b91cf543210be139ed50f895eba7d62c34175e73dc7dc8b` | `804ae8c42f6637a61505e53e825972d758b8ae2c1c2d0740ff5a076a0e703b45` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | 232527 | `1cee4b1dd7d7f083dd920ce12b9eb013318e2611b928a999cdd9d3b9358c9fff` | `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | 12419 | `75678b51d0e17d89862bf0a7ee3446014969ba73aae6cd31606288553b163e27` | `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | unchanged | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` | unchanged |

All current digests match the handoff/disposition 127; all inverse digests match disposition 124. This establishes that every byte outside the four literal spans, including encoding/newlines, is unchanged. It preserves accepted diagnostic W rather than reverting it to the earlier retry-5 W.

Static `rg` search across `pipeline/scripts`, `pipeline/tests` and `config` returned exactly W23 `baseEvidence`, W344 independent terminal-fallback `expectedRoot`, S39 `SELF_ROOT` and H17 `EVIDENCE`. New literal counts are **2/1/1**, old retry-5 counts **0/0/0**; no additional consumer appeared in that search. Each substitution changes only the final retry digit. P is unchanged.

W's parent and separate terminal failure allowlist now agree on retry-6. Caller/update/failure, handoff/update/consumed/start/stdio paths still derive from that parent. S's parent and exclusive leaf match H's leaf for helper authorization/consumption/start markers, nonzero/tree markers and logs. The invocation.pending replacement path, caller fallback and stderr-only failure route remain within the reviewed output vocabulary. No other path, schema, mode or producer/consumer behavior changed.

## Preservation and static evidence

Independently re-enumerated all prior evidence files recursively with Force and compared every relative name, count and SHA-256 against the 53-row matrix in the cycle-1 handoff, pinned at `4701ddc210ef755832a0bb8cebf3c561e51868ac961b499ddf97867fb3b25704`. Counts were original=2, retry-1=2, retry-2=11, retry-3=11, retry-4=11, retry-5=16: **53/53 matched, zero missing/changed/unlisted**. Every expected file was also checked present. No consumed evidence content was opened for diagnosis. Retries1–5 remain consumed, immutable and non-PASS.

Independently rehashed all six protected files and matched the accepted bindings:

| Protected file | SHA-256 |
| --- | --- |
| `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |

Inspected the hash-bound handoff's released Ruff check/format-check commands and their outputs: `All checks passed!` and `2 files already formatted`; W Parser.ParseFile success is recorded there. These implementer static results are reused, not claimed as independently rerun here. Their exact final source bindings match this review's independent byte proof. The unchanged embedded C# retains the compile-only evidence in accepted cycle-2 review `f465d1987338551da0d7f093db358eca05143c806591e933e27f6093c0b4279a`; it was not compiled or called in this review. No tests/imports were needed or run for the literal-only change.

## Independent point-in-time path checks

Read-only observations ran **2026-10-25T12:10:19.4834148+00:00 through 2026-10-25T12:10:19.6202297+00:00**. ErrorActionPreference/individual checks used Stop; inaccessible or failed checks were not accepted as absence.

| Check | Independently observed result |
| --- | --- |
| `C:\`, `C:\vibe`, `C:\vibe\localSimulator`, `C:\vibe\localSimulator\.codex` | Existing directories; GetFullPath and Resolve-Path.ProviderPath exactly agree; no ReparsePoint, LinkType or Target. |
| Fixed proposal `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-6` | Absent as Any/Leaf/Container. Force enumeration of .codex found zero case-insensitive equal names and zero equal names after trailing-space/dot normalization. |
| All 26 plan-listed root/output/leaf paths | Each exact absolute path is lexically canonical, within the canonical .codex prefix, and absent as Any/Leaf/Container. The absent safe parent establishes descendant absence; no nonexistent suffix was resolved or created. |
| `C:\vibe\localSimulator\data\generated\teignmouth-float32-topology` | Absent. All existing ancestors through the workspace are canonical directories without reparse/LinkType/Target; lexical workspace containment confirmed. |
| `C:\vibe\localSimulator\docs\milestones\artifacts\Teignmouth-float32-topology\build-3\run-1` | Absent. All existing ancestors through the workspace are canonical directories without reparse/LinkType/Target; lexical workspace containment confirmed. |

No root/probe/scratch path was created, selected, reserved, repaired, renamed, adopted or deleted. These observations do not reserve any path or eliminate races. Immediate coordinator source/path checks and W's unchanged runtime fresh-root/reparse/exclusive ownership checks remain mandatory. S alone may create run-1 after authenticated handoff; S/H one-use validators remain unchanged. Any new occupancy, alias, ambiguity, inaccessible check or drift is a stop, without cleanup or alternate-root authority.

## Preserved behavior, work and limits

Whole-file inverses preserve the accepted W diagnostic bounds/failure isolation, S/H/P ownership/default/rejection/cleanup behavior, exact outer rejection and startup/nonce/hash/creation/Job bindings. Normal helper exit7/7, complete zero/empty/zero normal-stage gate and deliberate tree containment/timeout/termination gates remain required. No conhost exemption, disappearance override, count subtraction, targeted termination or cleanup-to-PASS was introduced. Candidate-output presence still blocks self-check; it never authorizes deletion or a build.

The original **10-second total absolute QPC deadline**, inherited throughout S/H, remains unchanged, as do the 20 ms optional diagnostic opportunity, one-second reserve and one-close ownership. Native APIs, allocation and persistence remain non-preemptible; this static review proves no hard wall-time bound, runtime fit, containment efficacy, cleanup duration or durable telemetry. Historical outer exit1/internal2, retry-5 snapshot identity/incarnation/ancestry uncertainty and unsaved `957157…` provenance remain unresolved.

Work consisted of static document/source reads/searches, hashes and in-memory inverse calculations, full evidence filename/count/hash comparison, six protected hashes and the authorized read-only path/ancestor/alias checks, followed by this report write. One preliminary functions JavaScript orchestration attempt failed at JavaScript parsing before any nested shell command ran; the corrected orchestration completed successfully. No source/evidence/checkpoint/ledger edit, parser/compiler/linter/test/import, runtime/process inspection, invocation, cleanup, path creation/probe, candidate/GIS/numerical build, browser/publication, commit/push/merge occurred during review. Only this review artifact was written.

**Stop for coordinator decision.** This PASS is not the separate immediate one-use gate and authorizes no invocation. Retry-6 remains proposed/unselected/unreserved and unexecuted. All historical counters carry forward without reset. Candidate remains **NO-GO and unservable**, build 3 unreserved; pending AOI/product/geographic/source/synthetic constraints remain intact. A future invoked refusal/partial result/failure consumes that single attempt and remains non-PASS; no replay or automatic next root follows.
