# Independent review — W diagnostic correction cycle 1

2026-10-25. **FIX REQUIRED.** Issue `Teignmouth-float32-topology-representation-1`; independent implementation review under disposition 116. This review grants no source correction, self-check or path authority.

## Exact bindings

| Binding | Independently verified SHA-256 |
| --- | --- |
| Current W | `d7351a1cdcd9e8f6ea2c554400ff34d4f281a8c15086c87b32a132d806e549cd` |
| Pre-correction W | `dee858ce20851a306b157096d106ff79f6e9a6f89875f40dfee9d4b828bc9442` |
| Accepted retry-5 W | `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0` |
| S | `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` |
| H | `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf` |
| P | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| Correction-1 handoff | `4701ddc210ef755832a0bb8cebf3c561e51868ac961b499ddf97867fb3b25704` |
| Accepted plan | `b99f339316ab10d29dcb3346b7b05e2d75b48684acecafc6e24951dc50de83ed` |
| Plan independent review | `4b8dcda9d0a879a8350a29201915a7cedb6ae799492e482f5e3707e73bf5e7df` |
| Initial implementation independent review | `3ab8e4d9ec1bf785b45c665907451a34890985e5ad57efa99cc8c2f3a1bb39d6` |

The H hash printed in the correction handoff contains a transcription error (`...caf3cf1c1db...`). Actual H matches the accepted full hash above. Correct that handoff binding in the next authorized handoff; no H source change is needed.

## Remaining actionable findings

### 1. Default callers still perform diagnostic row-index bookkeeping (P2)

W1067 initializes `$rowIndex` and W1085 increments it for every row on every ancestry pass even when `$Observation` is null. That index exists solely for optional predecessor row references at W1077. Although the overload and added QPC/dictionary work are now properly sink-guarded, this remaining diagnostic bookkeeping changes the default path contrary to the accepted plan and dispositions 113/115. Guard the index initialization/increment on an actual observation sink (or a ready diagnostic sink) while retaining the original census predicates, ordering, mandatory checks and default `foreach` walk.

### 2. A failed optional membership-start clock becomes a fabricated numeric timestamp (P2)

W1362–1363 deliberately leaves `$membershipStart=$null` when optional QPC fails, then still permits useful same-handle evidence if the later clock succeeds. Both the no-reserve payload W1207 and full-detail payload W1237 cast that missing start to `[long]`, yielding zero. They emit it alongside the observed end timestamp without an unavailable start-clock status. This defeats the fixed-field contract's explicit unknown/failed status requirement and reports a QPC observation that did not occur. Preserve null for unavailable start QPC and mark its availability truthfully; retain the committed false rejection and useful remaining evidence. The late-summary branch W1223 already preserves the raw nullable value.

### 3. No-reserve/expired paths still construct a detailed payload before the mandatory close (P2)

W1197–1212 and W1214–1228 still construct the multi-group observation, including separate Job, membership, times, image, close and capture hashtables plus chain/snapshot metadata, while the process handle is held. The first branch is entered specifically because the one-second reserve/20 ms opportunity is unavailable; the second has explicitly crossed the cutoff. Removing the old bounded-copy pipelines and omitting the extra queries is an improvement, but the original finding was also the large payload allocation before closure. The accepted plan says to close immediately when reserve is insufficient and stop optional storage at cutoff. Return only a minimal skipped/late token needed to preserve status, close, and construct any expanded summary after close/mandatory catch cleanup, or omit the diagnostic. Do not perform the existing multi-group allocation after the budget check has failed. Preserve one-close ownership and primary rejection throughout.

## Six initial findings: correction assessment

1. **Cutoff field fixed:** W1118 now reads initialized `capture.cutoffQpc` consistently. The missing-key defect that skipped normal capture is resolved.
2. **Roots/capped root fixed:** W1029–1032 retains at most two original UInt32 roots and the cap flag; all observation branches reference them. Chain output leaves terminalRoot null unless complete, including capped/ambiguous/late cases (W1182–1185). Snapshot-incarnation association remains explicitly unproven.
3. **Primary-query/false-rejection isolation substantially fixed:** optional snapshot/Job/start/end clocks and dictionary/predecessor writes are guarded. W1366 captures membership API last error before any post-query clock, preserving the original error text. W1370 commits a successful false result before end-QPC and detail allocation. Later pending count/message updates are guarded. Existing mandatory deadline/census failure behavior remains. The inaccurate unavailable-clock representation in finding 2 remains.
4. **Default close semantics fixed:** W1387–1404 has mutually exclusive single close paths; the native close attempt precedes optional close telemetry. Default callers use the original direct call, including raised-close propagation. Established self-check rejection paths make close failure secondary. No handle is reopened, retried, transferred or stored globally. API query rights remain `0x1000` and both optional process queries use the exact membership-query handle.
5. **Chain work bound fixed; no-reserve allocation remains:** W1140 caps reconstruction at 64 edges, checks cutoff during reconstruction and storage, and checks again before completion. Output is target-nearest edges ordered toward target, with unknown omitted root connection. No additional Toolhelp snapshot is used. Finding 3 remains for skipped/late payload construction before close. Native calls/allocations remain non-preemptible and no hard 20 ms or guaranteed cleanup duration is claimed.
6. **Original Job count and single fallback fixed:** W1340 saves the original count, W1231–1236 uses a distinct bounded array and that original count, and the skipped branches retain the original count. W1287–1328 has a single minimal-fallback block, invoked at most once after full serialization failure or over-limit output. Compact full/minimal JSON limits remain 16384/1024 UTF-8 bytes, with depth bounds, omission on failure and no byte truncation.

## Independently rerun permitted gates

Read-only rehash of the existing snapshot `C:\Users\david\AppData\Local\Temp\codex-retry6-precorrection-b2631441c60d42e585d3707f180db6f1.ps1` matched `dee858ce20851a306b157096d106ff79f6e9a6f89875f40dfee9d4b828bc9442`. Replacing only the current `Get-DescendantProcessIds` through pre-`Get-PyvenvPolicy` region with that snapshot's region gave exact string/UTF-8 byte equality to the snapshot and that same hash. Thus this correction has no byte delta outside the approved region. No snapshot or reconstructed file was written.

Independently derived the accepted retry-5 baseline from Git blob `a742ddc1aea8cf05b8059879d83bcf8230b1f005` using the documented path/access-literal substitutions. Replacing the current diagnostic region with that baseline region, removing the pending initialization, added native overload and catch attachment produced exact equality and SHA-256 `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0`. The current W is 134567 bytes, LF-only, no UTF-8 BOM, final LF. Source path literals and the original 10.0-second self-check budget remain unchanged. Existing catch cleanup and post-cleanup attachment statements remain unchanged, as established by both inverse proofs.

Reran the authorized PowerShell `Parser.ParseFile` AST gate and literal `interop` here-string extraction followed by `Add-Type -TypeDefinition $source -Language CSharp -ErrorAction Stop`. No W statement or compiled method was invoked. Exact output:

```text
PowerShell AST parse passed
Embedded C# compile-only passed; no method invoked
```

Independently enumerated and rehashed all prior evidence: original=2, retry-1=2, retry-2=11, retry-3=11, retry-4=11, retry-5=16, total **53/53**, no missing/changed/unlisted files. All full relative paths and digests match the handoff matrix and the previously independently verified matrix; all digests also match accepted dispositions 56/63/67/78/89/110. Retry-5 remains 16/16 unchanged. No consumed evidence contents were used for a new diagnosis.

All six protected source/config/test files independently match the complete hashes in the handoff and accepted disposition 47: candidate `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b`; topology helper `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880`; builder `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b`; test `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8`; fixture `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea`; config `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228`.

Zero `retry-6`/`retry6` literals exist in W and `.codex/build3-supervisor-selfcheck-retry-6` remains absent. No path was selected or reserved. Syntax/compile success and preservation are not behavioral or runtime-fit proof. Numeric snapshot ancestry is not incarnation-authenticated; later handle creation/image facts cannot establish that association or parent/helper/conhost identity. Diagnostic fields do not admit a false member or create acceptance.

## Handback

Stop for coordinator disposition and authorized correction. Only this review artifact was written. No source/evidence/checkpoint edit, tests/imports/project execution/process probes/path/root work or invocation occurred. Retries 1–5 remain consumed, immutable and non-PASS; candidate NO-GO/unservable, build 3 unreserved. No self-check is authorized. The outer exit discrepancy and unsaved `957157…` history remain unresolved.
