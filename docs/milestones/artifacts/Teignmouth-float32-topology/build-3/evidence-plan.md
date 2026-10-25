# Build 3 proposal — corrected prototype-local overlay

Date: 2026-10-24. Prepared by `/root/sol_review_face_diag` under coordinator disposition 23.

## Disposition

**PROPOSAL ONLY: BUILD 3 IS UNRESERVED. Candidate remains NO-GO and unservable.** Propose exactly one offline build, ordinal 3, with an absolute external **180-second maximum**, using the accepted cycle-4 implementation and independently reviewed Sol fixture/test correction. No build, test, import smoke, diagnostic or browser action is performed or authorized here. A separate Sol review of the final manifest, runtime/dispatch contract and fresh paths must precede any later coordinator reservation.

The numerical intent is to determine which unchanged gates the corrected serialized candidate passes or fails. Expect the exact source-plane-zero gate to remain strict: diagnostic 2 measured nonzero differences around 1.5e-7 to 2.8e-7 m on the saved face. Those values are not zero and must not be rounded, hidden by tiny-fragment filtering or accepted using a new tolerance. An accounting correction can expose another genuine failure. No outcome is pre-accepted.

## Actual inspected state and recipe

The existing runner is `pipeline/scripts/build_teignmouth_float32_candidate.py`, SHA-256 `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b`. It accepts an input manifest, live ledger, evidence directory and build ordinal, uses a spawned worker, persists construction/serialization buffers and gate files, propagates logical worker exit, samples one worker PID, and archives non-PASS output. It fixes its generated output to `data/generated/teignmouth-float32-topology` and refuses existing output/evidence paths.

Proposed inner command, **not executed**:

```powershell
pipeline/.venv/Scripts/python.exe -B pipeline/scripts/build_teignmouth_float32_candidate.py --input-manifest docs/milestones/artifacts/Teignmouth-float32-topology/build-3/input-manifest.json --attempt-ledger docs/milestones/artifacts/Teignmouth-float32-topology/attempt-ledger.json --build-ordinal 3 --evidence-dir docs/milestones/artifacts/Teignmouth-float32-topology/build-3/run-1
```

`build-3/run-1`, `build-3/input-manifest.json`, `build-3/invocation.json` and the fixed generated candidate output were absent at planning inspection. This document creates only the parent proposal directory/file. Only the existing build runner may create the execution leaf; do not precreate it for manifests/logs. A parent invocation record and external logs may live directly under `build-3/`. Recheck absence immediately before reservation/invocation and refuse overwrite or retry.

Accepted implementation SHA-256: `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b`; test module: `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8`; fixture: `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea`. Historical shared helper remains `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880`.

## Complete protected-input closure

Prepare a fresh build-3 manifest in the parent, then independently verify every byte length/hash and enumerate absent/empty directories separately. Do not rewrite an older manifest or replace historical evidence.

1. Carry forward every protected path from the 291-entry diagnostic-2 manifest, preserving current bytes. The two expressly accepted changed paths are the current candidate module and focused test module; record their old/new binding relationship. All other inherited current-file bindings must remain identical. Preserve the historical manifests themselves byte-for-byte; do not pretend their old implementation/test hashes describe the newly accepted code.
2. Include every file beneath build 1, build 2, diagnostic 1 and diagnostic 2, including binary buffers, archived partial-output contents, zero-byte logs, invocation/supervisor reports and all preservation records. Bind all existing correction-4 and Sol-correction-1 summaries/handbacks, fixture and its five provenance sources, Sol plan correction 4, reviews 10–13, coordinator dispositions through 23, current spec/limit decisions and this proposal. Recursively inventory these evidence trees so no failed-build or diagnostic file is omitted. Record empty directories explicitly rather than treating an empty archive as missing evidence.
3. Include the build runner, every directly/transitively imported local helper, fixed configs/frame/domain/recipe definitions, relevant focused tests, project dependency contracts/lockfiles and exact release readiness/inventory/manifests/source assets. Preserve the accepted 2 km and historical 1 km packages and product/synthetic/preview bindings already protected; no new source acquisition. Declare actual build source-read scope: unlike the one-face diagnostic, the existing builder loads its full required release inputs, including roads/buildings/heightfield. Hashing preservation files is distinct from reloading GIS geometry.
4. Freeze an immutable **pre-reservation** ledger snapshot with used/reserved counters and a separate live-ledger identity. The live ledger is named mutable coordinator metadata, not an immutable protected input: the later authorized reservation must intentionally change it. Before dispatch, record the reserved-ledger hash, require issue identity, exactly one ordinal-3 reservation, used builds=2, limit=180 seconds and all unchanged budget maxima. The reservation must not be created by the worker. If a post-reservation immutable snapshot is wanted, freeze it as separate metadata and review that exact addition before dispatch.
5. Bind the exact external dispatch/supervision recipe and runtime identity record described below. Exclude only the fresh owned build-3 execution outputs/parent invocation/logs and specifically named coordinator metadata. Explicitly pin the manifest's own SHA before/after; do not rely on rereading a changed manifest as a new authority.

## Runtime identity and supervision prerequisites

Use exactly `pipeline/.venv/Scripts/python.exe`. Bind its SHA, `pyvenv.cfg`, package metadata and the existing full environment-preflight record, plus a build-3 runtime identity contract with full `sys.version`, implementation, resolved executable, NumPy/Shapely/GEOS/PyProj identities and relevant native-runtime identities. Existing evidence records CPython `3.13.7 (tags/v3.13.7:bcee1c3, Aug 14 2025, 14:15:11) [MSC v.1944 64 bit (AMD64)]`, NumPy 2.5.4, Shapely 2.2.0/GEOS 3.14.1 and PyProj 3.8.0. These are recorded identities, not a freshly executed verification. `pyvenv.cfg` points to base Python `C:\Python313\python.exe`; account for that base/native runtime explicitly rather than claiming the venv launcher hash identifies every executable dependency. Any out-of-repository runtime file must have an explicit external-runtime binding contract; the current repository-only runner verifier cannot accept such paths as ordinary `files` entries. No package installation/update is proposed.

The inspected runner alone does **not** establish the required end-to-end bound. Its timer begins after import/preflight/evidence creation (line 379), covers worker polling, then uses an unbounded `process.join()` (445) and unbounded post-run hashing. It kills the numerical worker PID, not an independently contained process tree. It records actual child exit and chosen runner exit but leaves caller-observed outer exit null. It also does not enforce the full frozen runtime record. The diagnostic-2 supervisor is hardcoded to diagnostic 2 and cannot be invoked for this build.

Consequently the proposal is **not ready for reservation** until an exact external dispatch recipe is supplied and independently reviewed. This document neither edits a runner/supervisor nor authorizes a code correction. The recipe must:

- Persist parent invocation/preflight identity before launching anything; enforce one invocation/no retry.
- Establish OS process-tree containment with kill-on-close before the runner can execute, failing closed if assignment/configuration fails. Include every numerical descendant and the multiprocessing worker. No memory cap is imposed.
- Own one absolute 180-second deadline from invocation start. Reserve a bounded tail for termination, preservation and evidence retention; an earlier numerical stop is acceptable, an extended numerical deadline is not. Clamp every explicit wait, including launch-failure cleanup, to remaining time. No numerical child may survive timeout or supervisor failure. A tool's yielding/session timeout is not a process-killing deadline.
- Verify runtime/source/input identities before numerical work and before/after preservation. Record partial checked counts/errors if the deadline prevents a complete pass; never claim preservation success from a directory inventory alone. Preserve primary worker/gate results if telemetry fails.
- Capture actual worker and runner process exits separately from logical/chosen exit values; refresh exits after confirmed termination. Have the calling command capture the actual external-supervisor exit, UTC timing and wall elapsed independently. Missing evidence is explicitly unavailable, not inferred success.

If an acceptable dispatch contract cannot be supplied within authorized scope, stop with this documented blocker. Do not consume a build merely to discover a known supervision deficiency. No draft manifest is supplied here because the exact external supervision/runtime bindings are not yet complete; presenting one as frozen would overstate readiness.

## Gates, resource evidence and stop behavior

Preserve the existing gate sequence and exact pass/fail definitions. Construction/chart/support and stored-local-topology evidence is already written incrementally by the candidate module; serialization buffers and gate files must survive any later failure. Source-perimeter/planes, full source overlay/gradients, actual stored sections, road ownership, complete building contact, shared road/building/walk surface and independent confirmation keep their truthful states. Unreached gates remain NOT_EVALUATED/UNAVAILABLE with reasons. A failed exact-zero gate must be persisted as failure, not merely an exception without its completed observations. The build's final report is not written at every stage, so external timeout handling must preserve existing progress/gate/buffer files and label an absent final result accurately; it cannot invent later passes. Independent deterministic confirmation is not performed implicitly by build 3.

Measure peak working set if available and label precisely which PID/process is sampled, whether it is the numerical worker or launcher, sampling interval and unavailable/partial scope. The existing runner samples `multiprocessing.Process.pid` with Windows `GetProcessMemoryInfo`; do not call that a process-tree peak without actual tree measurements. Diagnostic 2's 4,927,488-byte launcher/PID sample is not a reliable numerical-workload peak and must not become a cap or baseline acceptance number. No profiling-only rerun is proposed. Record elapsed time, termination confirmation and resource telemetry independently of candidate success.

Stop on mismatched input/runtime/source identity, invalid/nonfinite geometry or planes, collision/constraint/topology failure, unchanged gate failure, deadline, preservation mismatch or unexpected output state. Never change source/domain/origin/recipe/precision/filter/tolerance/guard/limits to obtain a pass. No parameter sweep or automatic retry follows. Keep exact-zero source-plane preservation strict; no absolute epsilon or area-based exemption for a nonempty region.

## Output retention and handback

The only generated output target is the existing ignored fixed candidate directory, not public/product assets. On non-PASS, the runner normally moves that directory to `build-3/run-1/partial-candidate-output` and records it. On externally interrupted runs, retain every partial byte: after numerical termination, move only the resolved, verified exact candidate path into the absent exact archive path, using one shell/native filesystem API and confirming both stay within the intended workspace. Never delete or overwrite an existing archive. If archival fails, record the failure and leave the original output intact, unservable and blocking another invocation. Do not erase failed output as cleanup.

If offline PASS occurs unexpectedly, retain candidate bytes as quarantined evidence without integrating/serving them. Candidate status remains NO-GO pending independent review and all remaining existing gates/confirmation. Hash saved output/evidence and protect historical trees before/after. Handback must include invocation/commands, actual exits, UTC/elapsed timing, preservation counts/mismatches, memory scope, completed/failed/unavailable gates, archived-output identity, blockers and counters. No browser, screenshot, Site, publication, push or merge follows this proposal.

## Fixed constraints and counters

Preserve release/source bytes, origin `[-140,0,-95]`, domain `[-182,-136,-98,-54]`, stations 140–155, default 35 m buffer, chart/recipe, decoded stored-Float32 surface contract, collision/constraint/winding/seam guards, strict terrain change <6.5 m, positive added gradient <1.0 m/m, cross slope <=5%, full-width span <=0.30 m, centerline deviation <=2.0 m, absolute longitudinal grade <=10%, exact source-plane-zero and every inherited limit including unchanged area tolerance. Preserve pending/not-checked AOI, TQ1 4HN centroid, historical package, synthetic fallback and accepted viewer/preview.

Current effective counters: diagnostics 2/2 used; Luna corrections 4/4 used/reviewed; Sol corrections 1/1 used/reviewed; implementation builds 2/6 used, **zero reserved**, four remaining; confirmation 0/1 and ineligible until all offline gates pass; total full builds 2/7 used. Proposed build 3 would consume one implementation-build attempt once invoked, including timeout/failure. No extra correction/diagnostic budget is available or created. No reservation or ledger/checkpoint change is made here.

## Planning boundary

Prepared by static inspection and file hashing of current code, runtime records, dispositions and accepted evidence. No code/test/build/diagnostic/browser changes or execution occurred. Only this proposal document was written. Independent Sol manifest/dispatch review and a later coordinator disposition remain required before any executable action.
