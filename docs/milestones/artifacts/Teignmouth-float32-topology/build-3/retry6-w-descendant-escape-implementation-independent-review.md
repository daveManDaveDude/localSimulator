# Independent implementation review — W descendant evidence

2026-10-25. **FIX REQUIRED.** Issue `Teignmouth-float32-topology-representation-1`; review only under disposition 114. The static/preservation gates pass, but the actual implementation does not yet implement the accepted diagnostic plan or preserve every required failure path. No implementation acceptance or invocation authority follows from this report.

## Exact reviewed bindings

| Binding | Actual SHA-256 |
| --- | --- |
| Current W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `dee858ce20851a306b157096d106ff79f6e9a6f89875f40dfee9d4b828bc9442` |
| S | `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` |
| H | `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf` |
| P | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| Accepted plan | `b99f339316ab10d29dcb3346b7b05e2d75b48684acecafc6e24951dc50de83ed` |
| Independent plan review | `4b8dcda9d0a879a8350a29201915a7cedb6ae799492e482f5e3707e73bf5e7df` |
| Luna implementation handoff | `b31eb3c81cb1ee8c9a56211ade221e38b7fbfe9518b03e101ac2dd23b1ede84e` |
| Accepted retry-5 W baseline, independently reconstructed | `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0` |

## Actionable findings

### 1. Capture-time helper reads a field that is never initialized (P1)

W1086 compares current QPC against `$Observation.cutoffQpc`. Both constructors put the cutoff only at `$Observation.capture.cutoffQpc` (W1155,1165); no top-level cutoff is set. In the ordinary hashtable lookup this is null, cast to zero, so capture-time checks fail for normal positive QPC values. Consequently W1180,1182,1194 skip the chain and both intended same-handle detail queries even when reserve exists. This defeats the central missing-evidence correction on the normal path. Use the same initialized cutoff field consistently and trace every caller statically; preserve no-reserve/expired behavior.

### 2. The reserve branch discards the original roots (P1)

W1160 initializes `roots=@()` and `rootsCapped=false`, and W1172–1177 copies only Job-query metadata. It never copies `$Snapshot.roots` or `$Snapshot.rootsCapped`. `Set-DiagnosticChain` therefore builds an empty root set at W1104–1105, cannot recognize the original terminal root, and serializes empty roots even though ancestry used one or two supplied roots. Copy the bounded original roots/cap flag into the actual observation before chain reconstruction. Preserve incomplete/capped/ambiguous semantics; on a stored chain capped at 64, the currently populated terminal root at W1126 also contradicts the `capped-root-unknown` status and plan's explicit unknown stored root connection. Make those fields agree without claiming authentication.

### 3. Optional telemetry can replace the original query/rejection failure (P1)

At W1279–1285, the added end-QPC query runs before the native membership result is checked or a successful false result is added to `uncontained`. If that optional clock call fails, the established false result is lost and the primary failure becomes the clock exception. A native membership API failure also receives no immediate last-error capture before the QPC native call. The accepted fixed API order requires saving BOOL/member/error immediately and establishing the rejection independently of diagnostics. Added start/end Job and snapshot clock calls, observation construction and bookkeeping writes at W1011–1040,1057–1060,1258–1267 are likewise outside optional failure guards; allocation or telemetry failures can become primary exceptions. Retain existing mandatory deadline/census failures, but isolate optional observation failures, save native error before other native/clock work, and commit the successful false result before fallible supplemental telemetry. Also guard later optional updates at W1293 and W1318 so they cannot replace an already determined rejection.

### 4. Close exception behavior changed for default callers (P2)

Baseline `Assert-OwnedJobTree` finally directly called `CloseHandle`; an invocation exception propagated. Current W1298–1303 catches and suppresses it unconditionally, including build/runtime-preflight, true-member paths and absent diagnostic observations. The plan permits secondary close evidence on an established false-membership path while requiring default non-diagnostic behavior unchanged. Limit secondary suppression to the authorized established rejection case and retain the original behavior elsewhere. Keep exactly one close attempt as the first finally operation and do not introduce retries or handle transfer.

### 5. No-reserve capture still builds details before closing; chain work exceeds the stated 64-edge design (P2)

W1140–1156 handles insufficient reserve by running pipelines and constructing a large nested observation before returning to finally. The plan explicitly requires skipping details and closing immediately when reserve is insufficient. With reserve, W1107–1123 can build a 65536-element reverse chain before retaining 64 edges; the accepted budget description specifies finite 64-edge work. There are also metadata allocations/copies at W1158–1178 without renewed cutoff checks, and W1122–1128 has no final cutoff check before promoting chain completion. After correcting finding 1, these paths must still honor the specified cutoff and omission semantics. Retain only bounded necessary chain storage/work consistent with the plan (or return a concrete scope blocker), close before no-reserve detail construction, and do not label work completed after cutoff as observed/complete. Native-call latency remains non-preemptible; no hard 20 ms guarantee is requested or implied.

### 6. Capped Job counts and minimal-fallback attempts are not truthful to the contract (P2)

In the no-reserve branch, `$jobIds` at W1142 is the same PowerShell variable as parameter `$JobIds` (case-insensitive). Replacing it with the first 64 values makes W1146 and W1155 report the truncated count as `originalIdCount` and can incorrectly set `idsComplete=true`/`idsCapped=false`. Save the original count and use a distinctly named bounded list. Separately, if the over-limit path's minimal serialization at W1239 throws, catch W1244–1249 attempts that minimal serialization again; the plan allows only one minimal attempt. Use a single bounded fallback path/attempt with truthful omitted status. Preserve valid JSON and the existing 16384/1024 UTF-8 limits.

## Independently completed static and preservation checks

The historical Git blob `a742ddc1aea8cf05b8059879d83bcf8230b1f005` was read without executing project code. Applying only the documented retry-1 to retry-4 parent substitutions, three unsigned `CreateFile` literal suffixes and retry-4 to retry-5 substitutions produced the accepted baseline hash above. Independently replacing the current ancestry/assertion/helper region with that baseline region, removing the single pending-state initialization, removing the second native overload line and removing the catch attachment produced **exact byte-string equality** to that baseline and SHA-256 `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0`. No reconstructed baseline was written. No unplanned byte delta exists outside these planned spans. The current W is 128305 bytes, zero CR bytes, no UTF-8 BOM, with the preserved source path literals.

The earlier default snapshot-QPC defect is corrected at W1011/1018: both added reads are sink-conditional. Default callers use the original one-argument `GetProcessRows` body verbatim, and skip diagnostic dictionary/predecessor construction; the numerical ancestry predicates remain the same. This limited conformance does not resolve findings 3 and 4. The diagnostic overload retains the original snapshot/first/row/deadline/close algorithm and immediately captures terminal `Process32Next` last error. Error 18 and convergence are distinguished from other terminal errors. Duplicate/cycle/cap statuses and the explicit `snapshot-incarnation-unproven` limitation remain present; no code consumes diagnostic fields for acceptance.

Reran only the authorized static gates using `System.Management.Automation.Language.Parser.ParseFile`, AST extraction of the literal `interop` here-string, and `Add-Type -TypeDefinition $source -Language CSharp -ErrorAction Stop`; no W statement or compiled method was invoked. Output:

```text
PowerShell AST parse passed
Embedded C# compile-only passed; no method invoked
```

Read-only enumeration and hashing independently found exactly original=2, retry-1=2, retry-2=11, retry-3=11, retry-4=11, retry-5=16, total **53**. Every full filename and hash matched the pinned handoff's complete matrix, with zero unlisted files. Its hashes also independently agree with accepted dispositions 56/63/67/78/89/110, respectively. Retry-5 remains 16/16 byte-identical. No consumed evidence contents were loaded for diagnosis or modified.

All six protected files independently match both the handoff matrix and accepted disposition 47 bindings:

| File | SHA-256 |
| --- | --- |
| `pipeline/torquay_pipeline/teignmouth_float32_candidate.py` | `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b` |
| `pipeline/torquay_pipeline/road_surface_topology.py` | `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880` |
| `pipeline/scripts/build_teignmouth_float32_candidate.py` | `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b` |
| `pipeline/tests/test_teignmouth_float32_candidate.py` | `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8` |
| `pipeline/tests/fixtures/teignmouth_overlay_face_19669.json` | `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea` |
| `config/road-surface-teignmouth-float32.json` | `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228` |

The self-check budget remains 10.0 seconds. The catch attachment is after the existing mandatory termination/wait/member/clock observations and skips caller-persistence failures; exact inverse proves those original cleanup statements unchanged. Payload projection and UTF-8 byte checks remain bounded, subject to findings above. Static success establishes neither runtime fit nor behavioral correctness. Existing native/PowerShell/persistence operations are not preemptible by the QPC checks; no complete cleanup or durable evidence timing guarantee is claimed.

There are zero `retry-6`/`retry6` source literals and `.codex/build3-supervisor-selfcheck-retry-6` is absent. No path selection/reservation/root creation occurred.

## Handback

Stop for coordinator disposition and authorized Luna correction. No source, evidence or checkpoint edits; no tests/imports/project execution/process probes/self-check/runtime/GIS/build/browser work occurred. Only this review artifact was written. Retries 1–5 remain consumed, immutable and non-PASS; candidate NO-GO/unservable and build 3 unreserved. Fresh path planning, independent actual-byte review and a separate immediate one-use coordinator gate remain mandatory before any future invocation. The outer exit discrepancy and unsaved `957157…` history remain unresolved.
