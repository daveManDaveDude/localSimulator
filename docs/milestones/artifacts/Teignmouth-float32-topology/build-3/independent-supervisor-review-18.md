# Independent supervisor review 18 — unexpected-member diagnostics

2026-10-25. Independent non-implementing Sol reviewer `/root/sol_review_face_diag`, under dispositions 78/80/81. **FIX_REQUIRED — fallible diagnostic timestamping precedes the mandatory handle-close attempt.** Reviewed actual S, accepted diagnosis and `retry3-unexpected-member-evidence-plan.md` (independently verified SHA-256 `1e3bdb230ca7a1c2f7cbcea9ebe0c1dc6b1d9d960a51502adf5e5d40f46afbe4`). No operation is authorized by this report.

## Exact revision/scope

Independently verified:

| Source | SHA-256 |
| --- | --- |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `81fcdc0b199497d92d17c09c758a62b8861e7fcb7b41bb6a1c1663a1f76256af` |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `c3f1f49cb574793c1cdbc2d905fd3d36f646b6f32ffb7c200a96c9792d5ce84f` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `cf1145b33397066559b89c11aa1cb0ebcf4d6d4d470f6521d96fe9e1f4ecccab` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |

An in-memory, non-executing removal of the new diagnostic helper and guarded snapshot-tail attachment, restoring the original direct snapshot return, hashes to **`d498bc294390d8645c6acc59773ba50f417493926d8bbfb3564d34504e8a407a`**, exactly the accepted pre-change S baseline. No reconstructed source was written/executed. This proves the original census/rejection/normal-pair/reaping/tree/cleanup code and other module bytes remain unchanged outside the accepted additions. The earlier unsaved/untraceable **`957157…`** S-digest limitation remains unresolved; this inverse proof does not recover that history or create a Git baseline.

## Concrete blocker

**FIX_REQUIRED — S 2522 can prevent CloseHandle at 2526.** Every successful diagnostic OpenProcess enters the ownership `try/finally` at **2157/2521**, but the finally block starts with unguarded `close_started = time.monotonic()` at **2522**, before reaching `kernel.CloseHandle(handle)` at **2526**. Creating that timestamp's Python float can raise `MemoryError`. That exception exits the finally before the required single native close attempt, leaving the diagnostic handle outside the normal owned-handle list and without a close attempt by this helper.

This is directly within the accepted failure model, which explicitly requires one close attempt regardless of query/serialization/allocation failure and says native handle closure belongs before/outside fallible telemetry construction. It does not require malformed record state or live execution to identify the path. The outer guarded diagnostic attachment preserves the original primary snapshot and its BLOCKED rejection, but cannot retrospectively close the helper's lost local handle. Eventual OS resource release at S exit is not an observed CloseHandle success.

The close attempt must not depend on successful timestamp/error-record allocation; optional close telemetry must be best-effort around the independently guaranteed attempt. No correction is implemented or authorized here. No leak was reproduced or measured.

## Other required criteria

| Criterion | Static assessment |
| --- | --- |
| Original capture/rejection | **PASS:** inverse hash proves unchanged accounting-before → strict PID census → accounting-after sequence. The snapshot and original end time/complete/unexpected set are built at 2782–2799 before details. Existing post-wait/drain unexpected-ID rejection remains unconditional; later disappearance/familiar image/exit/final zero cannot reach the tree gate. |
| Immediate scope and cap | **PASS:** enrichment attaches at 2800–2825 before original return/persistence/rejection, only for complete nonempty unexpected IDs. The helper sorts that exact list and selects at most eight, with one open attempt each and no whole-host lookup, requery retry, sleep or extra in-interval census (2055–2056, 2077–2122). Primary census coverage is never truncated. |
| Same-handle API/rights | **PASS:** existing query/query-limited/SYNCHRONIZE rights and APIs only. Creation/exit times, exact Job membership, zero-time wait, raw exit and image query all use the one opened handle; before/after creation/membership are recorded. No PID reopen/adoption or new parent/class probe. |
| Unknown/partial semantics | **PASS for inspected diagnostic interpretation:** census association remains explicitly unproven and origin/class unestablished (2086–2102, 2516–2520). Open failure/disappearance/false contemporaneous membership is not classified as benign, escaped or a proven historical incarnation. Query/hash failures preserve partial fields; raw 259 is retained with ambiguous liveness rather than overriding a wait observation. No diagnostic result is admission authority. |
| Original deadline | **PASS, static acceptance bound:** before-call and between-field checks use the inherited absolute deadline, zero-time waits and bounded image buffer/hash. Capped/omitted/deadline fields remain separate from primary capture completeness. No runtime-fit or native-call-preemption proof is inferred. |
| Close ownership | **FIX_REQUIRED:** normal path has one local finally-close and reports false/error as release-unconfirmed, with no normal-handle transfer/retry. But the pre-close timestamp exception path above violates the required unconditional attempt. |
| Best-effort isolation | **PASS for primary snapshot/rejection isolation:** helper call, result attachment and fallback reporting are guarded (2800–2824), including secondary allocation/formatting failures. These cannot edit/reclassify the primary set or mask its rejection; normal final cleanup remains reachable. This does not repair the local handle-close gap. |

## Preservation

Rehashed all six protected candidate/shared-helper/builder/test/fixture/configuration files; all match their accepted full review-17 bindings. Rehashed **every file** in original, retry-1, retry-2 and retry-3 evidence trees (26 files total): all match their accepted binding matrices. In particular all eleven retry-3 files match disposition 78:

| Retry-3 file | SHA-256 |
| --- | --- |
| `caller-invocation.json` | `f1bf3a880a821626daef625f60459d037a8aa9509246e401a06f9440cb8134d6` |
| `self-check-handoff.consumed.json` | `dd82b4bd6cdfafa76fd5be2505cf438125f9deb70d37f73dbaf03a7f719d93b6` |
| `supervisor-script-start.json` | `bf0f5eed47455f27a037dea7fbeca068bf4ac2d9a72598e70c21c90b7c835a90` |
| `supervisor.stderr.log` | `18d4873d35189bf11f26f2df45a60574330fde3c27bf02371542b37a4b46fea8` |
| `run-1/invocation.json` | `dcf98d8471df615acbaa74d3eece7f8a774e86cac22b0864931e556f2ae627e5` |
| `run-1/nonzero-authorization.consumed.json` | `0b64cd4ffc826e052423ab501f55da267675ee8f5c345c4c7613b6076b283d3a` |
| `run-1/nonzero-helper.json` | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| `run-1/nonzero-script-start.json` | `0da552f3943a321f31e5bceac24fe74471e6a1c75367a852430f2e2d3ae0ffa3` |
| `supervisor.stdout.log`, `run-1/nonzero.stdout.log`, `run-1/nonzero.stderr.log` (three empty files) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Retry-3 remains consumed, immutable and non-PASS. The outer `pwsh` exit **1** versus retained launcher/supervisor exit **2** remains explicitly unresolved. No process identity is inferred for historical PID 20712; no live lookup was performed.

Only static reads/searches, file hashing and in-memory source/hash comparison occurred, plus writing this report. No source/evidence/metadata/manifest was edited; no tests/imports, linters/parsers/compilers, probes/process inspection, wrapper/self-check/preflight/runtime/collection, manifest preparation, GIS/numerical/build or browser action ran. Reported static checks were not rerun. Diagnostic coverage, native persistence/containment, 10-second timing and **30-second runtime-profile fit remain unmeasured**; no runtime evidence was created.

Return FIX_REQUIRED for the narrow mandatory-close ordering defect. This report grants no correction or operation. Any later self-check requires the separate fresh retry-4 plan/review/coordinator gate; no consumed slot may be reused. Candidate remains **NO-GO and unservable**; build 3 remains **unreserved**, with historical counters and geographic/source/origin/domain/recipe/collision/numerical limits unchanged.
