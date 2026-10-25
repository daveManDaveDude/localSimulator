# Independent review — W diagnostic correction cycle 2

2026-10-25. **PASS (implementation review only).** Issue `Teignmouth-float32-topology-representation-1`; independent Sol review under disposition 123. The three cycle-2 findings are resolved in the exact current bytes, and no actionable finding remains within the accepted W diagnostic scope. This PASS grants no self-check, path selection, root reservation or runtime authority.

## Exact bindings

| File/state | Independently bound SHA-256 |
| --- | --- |
| Current W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`, 132204 bytes | `804ae8c42f6637a61505e53e825972d758b8ae2c1c2d0740ff5a076a0e703b45` |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `ba39cb95c0317765b35bdff4cce4aaae84065db626399be0ab7a3332e6fe2a69` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `bec312ae4a625d8bb337e267e1cc63ae8282238349caf3cf1cdb5299e25560bf` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| Cycle-2 handoff | `b625ed67be46820210227aa03ab0a1bd91e51262b966fe3fcef646edbf4faa3f` |
| Exact cycle-2 inverse target, 134567 bytes | `d7351a1cdcd9e8f6ea2c554400ff34d4f281a8c15086c87b32a132d806e549cd` |
| Accepted retry-5 W baseline, 107257 bytes | `e9a0794a4b80f717e51a7c7dc6c82d4d65cdb4e290bed0fb8ad676174303f4c0` |
| Cycle-2 inverse mismatch diagnosis | `f239554ccc7caef0a51f9e3f4cd996338a70b95bbad50b646a2038c430f3611a` |
| Cycle-1 inverse anchor diagnosis | `6e8205b56b4e352278ba11c03ac5b51a9ce84c4aae08b2c7dbbf7c74f242968e` |

Current W/S/H/P, handoff and both diagnoses were rehashed during this review and match these bindings. The accepted plan remains `b99f339316ab10d29dcb3346b7b05e2d75b48684acecafc6e24951dc50de83ed`, with plan review `4b8dcda9d0a879a8350a29201915a7cedb6ae799492e482f5e3707e73bf5e7df`.

## Three findings resolved

1. **Default ancestry bookkeeping:** W1067/1085 now guard both diagnostic row-index initialization and increment on a non-null observation sink. The original `foreach` row iteration, row order, numeric PID/parent predicates, mandatory deadline checks and descendant additions remain. Default callers take the unchanged one-argument native enumeration and skip added diagnostic QPC/dictionary/predecessor work.
2. **Unavailable membership-start QPC:** W1200–1201,1208–1209 and1220 preserve null when the optional start clock was unavailable and emit explicit `unavailable` status. Successful values are cast only inside the non-null branch. The false native result is still committed to the original uncontained list before end-clock/detail work; failure of optional telemetry cannot reinterpret it or create success.
3. **No-reserve/expired allocation:** W1197–1212 returns only a flat bounded minimal-status token. These branches construct no detailed Job/snapshot/chain/times/image/close groups, copy no arrays and make neither optional process query while the handle remains open. The original per-descendant finally makes one close attempt before optional close telemetry; W1394 skips that telemetry for a token. The token is serialized only in `Convert-FalseMembershipObservation` (W1273–1287), reached through the existing catch attachment after mandatory termination/wait/member/clock cleanup (W2014–2024). Its JSON is capped at 1024 UTF-8 bytes, with omission on failure/expired deadline and explicit `detailsOmitted=true`. No handle is stored or reopened.

## Preserved cycle-1 contracts

The initialized nested cutoff is still used. Original bounded roots and original Job count are retained; Job output stores at most 64 IDs. Toolhelp terminal error is captured immediately by the diagnostic overload; complete snapshot status requires verified end-of-enumeration and convergence, and other terminal errors/unknown clock/bookkeeping states are not promoted to complete.

First-discovery predecessor edges remain tied to the original row collection. Chain work and output remain capped at 64 edges, with cutoff checks and explicit duplicate/cycle/incomplete/capped/late semantics. Capped or otherwise incomplete chains do not claim a terminal root. No later snapshot or alternative ancestry search is introduced.

The original `OpenProcess(0x1000,false,id)` and exact outer-Job membership predicate remain. Membership API failure captures last error before subsequent native clock work in diagnostic mode and retains its original distinct primary error. A successful false result is added before optional detail allocation. At most the first false PID receives detail; subsequent false PIDs retain the original rejection. The optional sequence uses that exact retained handle, at most one `GetProcessTimes` and one fixed-1024-character `QueryFullProcessImageName`, with no growth/retry or extra rights. Default/non-rejection close behavior remains direct; close failure on an established self-check rejection remains secondary. There is one close attempt per opened handle.

Full JSON remains compact/depth-bounded, capped at 16384 UTF-8 bytes with one possible 1024-byte minimal fallback, never invalid byte truncation. New token serialization takes its own single bounded branch and cannot fall through into another fallback. Pending evidence remains per assertion, handle-free and matched to the original rejection text; caller-persistence failures bypass attachment. Error type/stage/errorId and mandatory cleanup remain unchanged. No diagnostic field feeds acceptance.

The original 10.0-second total QPC deadline, 20 ms diagnostic opportunity and one-second reserve remain. Added checks cannot preempt a native call, allocation or persistence operation. No hard timing, guaranteed cleanup duration, measured runtime fit or durable telemetry claim is made. Association remains `snapshot-incarnation-unproven`; later same-handle creation/image observations do not authenticate earlier snapshot PID or parent incarnations, helper/conhost class, ownership or mapped bytes.

## Scope and inverse proof

The current hash is the same exact input independently diagnosed under disposition 118. That diagnosis reconstructed the full bound `d7351a1…` baseline by reversing only seven current spans: W1067,1085,1197–1204,1205–1212,1220,1273–1287 and1394. It also exactly reproduced the failed inverse digest `ce7f6…` by adding one LF at byte offset 83656, proving the extra byte was an inverse-concatenation boundary error. No source normalization or restoration was needed.

The cycle-1 handoff `4701ddc210ef755832a0bb8cebf3c561e51868ac961b499ddf97867fb3b25704` and independent review `6ab1b80d82a6aaccad3e93ef4fa63b5016c62f8d0fa8f2844a1e5b4b4d4ce49f` independently establish the exact `d7351a1… → e9a0794…` edge. The bound proof therefore composes **`804ae8… → d7351a1… → e9a0794…`**. This review relies transparently on those prior independently verified inverse steps, re-bound to current source; it does not claim the failed initialization-anchor script completed or that the inverse was newly reconstructed again during this review. The current delta is confined to the three authorized findings and preserves all earlier approved spans outside them. The handoff correctly distinguishes its prior inverse proof from a prior implementation PASS and records the historical H metadata corrections.

## Independently rerun permitted gates

Reran only PowerShell `Parser.ParseFile`, AST extraction of the literal `interop` here-string, and embedded C# `Add-Type -TypeDefinition $source -Language CSharp -ErrorAction Stop`. No W statement or compiled method was invoked. Output:

```text
PowerShell AST parse passed
Embedded C# compile-only passed; no method invoked
```

Independently re-enumerated and rehashed all **53** prior evidence files against the pinned cycle-1 handoff full-path/hash matrix: original=2, retry-1=2, retry-2=11, retry-3=11, retry-4=11, retry-5=16. No missing, changed or unlisted file exists. All digests also match accepted dispositions 56/63/67/78/89/110. Retry-5 remains 16/16 unchanged. Consumed evidence contents were not opened for diagnosis.

All six protected source/config/test files independently match the complete accepted disposition-47 and handoff bindings: candidate `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b`; topology helper `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880`; builder `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b`; focused test `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8`; fixture `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea`; config `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228`.

W has zero `retry-6`/`retry6` literals; `.codex/build3-supervisor-selfcheck-retry-6` is absent. No path/root was selected or reserved.

## Handback and limits

This is static implementation PASS, not behavioral validation. Only this review artifact was written. No source/evidence changes, tests/imports/linter, runtime/process probes, self-check/preflight, path/root work, build/GIS/browser/publication, commit/push/merge occurred. Stop for coordinator decision. A separate fresh path plan/review and immediate one-use coordinator gate remain mandatory before invocation. Retries 1–5 remain consumed/immutable/non-PASS; retry-6 absent/unselected/unreserved; candidate NO-GO/unservable and build 3 unreserved. The outer exit discrepancy and unsaved `957157…` history remain unresolved.
