# Blocked wrapper self-check — bounded static failure diagnosis

2026-10-25. Sol 6.1 medium, non-implementing `/root/sol_review17_plan`. Authority: disposition 56, one read-only diagnosis, maximum 120 seconds. No reproduction or correction.

**A bounded persistence/error-record correction is justified for coordinator consideration of the one unused Sol allowance.** All four operational Luna cycles have completed independent review. This is an actual newly observed non-PASS gate failure, not permission to reset those cycles. A retry is supportable under disposition 40 only after separate correction/review and explicit authorization of a fresh fixed evidence path. Neither correction nor retry is authorized by this report. Candidate remains NO-GO/unservable; build 3 remains unreserved.

## Preserved evidence and exact scope of inference

Statically read and hashed both evidence files; hashes match disposition 56:

| File | SHA-256 |
| --- | --- |
| `.codex/build3-supervisor-selfcheck/caller-invocation.json` | `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e` |
| `.codex/build3-supervisor-selfcheck/caller-invocation.json.update` | `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75` |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `c707ebbda14c562083fb2485854b4d4d515bc809987d13136479f7cd5d597b06` |
| Disposition 56 | `b2e0df3ba61188c270b1c01c8dbecc3dd55c0815c67687a3f77a65afb97855d3` |

Both caller copies have mode `self-check`, status `CALLER_SETUP_STARTED`, wrapper PID 41760, original QPC start/deadline 2939227575196/2939327575196 at frequency 10000000 (10 seconds), `nativeProcessLaunched=false`, and null chosen/native/script exits. The main copy has null wrapper creation time; the pending copy contains 134373761782256416. Directory inspection found just these two files. Disposition 56 records the invoking tool's observed exit 2 and absence of handoff/start/log/run/helper/candidate output; no success or contained self-check result can be inferred.

The reviewed actual entrypoint was disposition 55's wrapper command: `pwsh -NoProfile -ExecutionPolicy Bypass -File pipeline/scripts/invoke_teignmouth_float32_build3.ps1 -Mode self-check`. The earlier rejected direct Python command was not the contained self-check. A retry must preserve the wrapper/launcher/base/S/H chain, not bypass it.

## Likely failure point, with uncertainty retained

W 950–951 exclusively creates the initial caller record and acquires ownership. W 997–1008 compiles/initializes its interop, checks QPC frequency and reads wrapper creation time; at 1009 it calls `Save-Caller` for the first updated state. The pending copy's populated creation time is consistent with reaching that save, before launcher/config hashing, handoff creation or `CreateProcess` at 1131.

`Update-OwnedJson` at 117–141 exclusively opens fixed `<caller>.update`, serializes/writes/flushes it, disposes the stream, then uses `[IO.File]::Replace($pendingPath,$Path,$null)` when the existing caller destination is present. The two complete JSON copies are consistent with failure during finalization/replacement of that first update. They do **not** establish a recorded exception type/message or prove a specific OS error. In particular, a write/flush/dispose failure after bytes reached the file is not disproved by readable JSON.

One concrete code-level suspect is PowerShell argument binding of `$null` to the string backup-path parameter of `File.Replace`; a null-to-empty-string conversion can make a no-backup replacement call invalid. This is a hypothesis, not the observed exception. Filesystem replacement permissions/sharing or a final stream error remain possible. Do not claim an exception such as “empty backup filename” actually occurred here; there is no durable exception evidence and no runtime repro was authorized.

The **certain reporting weakness** is independent of that hypothesis: the failed replacement leaves fixed `.update` occupied. Outer catch at 1257 onward records the original exception in memory, sets failure/exit 2 and performs applicable cleanup. Finally at 1332–1334 calls `Save-Caller` again; `CreateNew` of the same pending path can fail before any terminal state is written. That final catch only sets `$finalExit=2`, losing the secondary persistence exception. The durable main and pending copies then both retain setup state. A leftover pending file must not be deleted/promoted to resolve this retrospectively.

## Minimum safe correction to propose separately

Change W's persistence and error reporting only, plus the explicitly reviewed self-check path synchronization below. Keep the failed evidence byte-for-byte immutable.

1. Remove the nullable-string replacement ambiguity. A minimal supported .NET call is same-directory `[IO.File]::Move($pendingPath,$Path,$true)` using an explicit Boolean overwrite overload, after flushed/closed exclusive pending creation and only for the owned existing destination. Alternatively use a strongly typed method with a literal C# null inside the existing interop for `File.Replace`; that option needs an independent pre-interop failure path. Choose **one** implementation in the correction, not a catch-and-try-another replacement loop. Do not claim power-loss durability or atomic replacement from static inspection alone. Never delete destination first or fall back to in-place truncation.
2. `Update-OwnedJson` must require the already-owned canonical expected caller destination to remain present and safe; a missing destination is failure, not permission to adopt/create a replacement record at an unowned path. Preserve exclusive pending creation and all parent/reparse/ownership checks. An existing unowned/stale `.update` is a refusal condition, not something to remove. No mutation of original failed evidence.
3. Preserve structured error information before cleanup/persistence can obscure it: original exception type/message, failing persistence stage/operation, pending/destination paths, primary-versus-secondary failure, and true launcher-created/assigned/resumed state. Keep null exits/termination when unavailable. A failing save is sticky non-PASS, stops progression to native launch and cannot be converted into success merely by writing another record.
4. Add one explicit terminal fallback record **inside the fresh retry root only**, e.g. `caller-invocation.failure.json`, written via ordinary .NET exclusive creation and flushed/closed without relying on interop, atomic replacement or the occupied `.update`. Use the existing caller-record schema with failure/persistence fields, not a new schema/mode/phase. This is a narrowly disclosed new fixed evidence filename that the coordinator must expressly include in the correction/retry plan; it is not implied permission to add arbitrary records. It is written only when terminal caller persistence fails, preserves both errors, and cannot satisfy a gate or overwrite caller/pending bytes. Check its absence before initial ownership acquisition. If fallback also fails, keep exit 2 and emit both failures to the invoking tool's stderr using an error path that cannot recursively throw under `$ErrorActionPreference='Stop'`; report durable error telemetry unavailable. No logging scheme can guarantee a write on an unavailable filesystem.
5. Keep cleanup before terminal evidence where required, but guard evidence/clock operations separately so they cannot mask the primary failure or interrupt Job/handle cleanup. Mark original absolute-clock expiry/telemetry unavailability truthfully. There is no extra runtime budget for replacement attempts or fallback; fail late/non-PASS if evidence work overruns. Any blocking filesystem call remains unproven preemptible.

The fallback filename is the smallest explicit record-boundary addition needed for independent terminal persistence after a fixed pending file survives. If the coordinator declines that addition, do not promise durable terminal evidence using the same failed replacement path; return the limitation before implementation. Do not write a fallback into the original failed directory now.

## Fresh fixed retry path, not reuse/reset

Disposition 56 says the original caller path is consumed even though no native child started. Disposition 40 permits serial gate retries but not silently cleaning/reusing one-shot evidence. A single fresh fixed path can be supported, proposed as `.codex/build3-supervisor-selfcheck-retry-1/`, with its own absent caller/fallback/pending/handoff/consumed/start/log/run/helper paths. No automatic numeric search, arbitrary user-selected directory, `run-2`, deletion or resurrection of the original slot. The exact retry path must be explicitly selected by coordinator disposition after review; its name here is a proposal only.

This **requires synchronized W/S/H changes**, not W alone:

- W's self-check `baseEvidence` at 23 and all derived caller/handoff/consumed/start/log/run paths use the new fixed parent.
- S's `SELF_ROOT`/`SELF_RUN` at 39–40 and `_handoff`/startup/self-check derived paths use exactly that parent; retain exclusive S-owned run-leaf creation and authenticated one-use path/nonce/PID/creation-time/deadline contract.
- H's fixed `EVIDENCE` at 17 uses the same new `run-1`; startup authorization, consumed files, markers, tree-root/child records all derive from it. Leave helper behavior/commands/modes unchanged. P and runtime-preflight/build evidence roots stay unchanged.

H has so far been protected unchanged; therefore this path-only H change is a **necessary explicit narrow amendment** to the prior W/S/P-only correction boundary, still within the original four operational files. It must be accepted before a Sol implementation. Do not use an environment variable, new command-line path selector or fallback to the old root to avoid that decision. The fixed retry storage location changes; geographic/runtime allowed root categories, product/source/GIS paths and native trust boundary do not.

Before retry release, independently confirm original evidence hashes unchanged and all new fixed retry paths absent/safe; do not create them during diagnosis/review. A retry gets its own original 10-second QPC clock at invocation and exactly one use. Original failed attempt retains its exit 2/blocked status and its consumed slot permanently. Do not extend the failed attempt's deadline, count failure evidence as self-check proof or run runtime collection/build first.

## Sol allowance and required independent review

Use of the unused **operational** Sol correction is justified for coordinator consideration: four Luna submissions are complete/reviewed, and the actual gate now exposes a concrete persistence/reporting defect. This does not consume or reset the separate already-used candidate Sol correction, candidate diagnostics or build counters. Only a separate disposition may reserve/release the operational Sol attempt and accept the H/path/fallback amendments; this diagnosis is not that attempt.

A **different Sol session from the Sol implementer** must independently inspect final W/S/H bytes/hashes and the exact original failed evidence. Required review:

- replacement call's actual overload/null/ownership behavior; initial and repeated successful updates versus write/flush/dispose/replace failures; stale pending/refused repeated invocation; missing destination; no delete/truncate/adoption of unowned records;
- original exception retained through cleanup and secondary/final-save/fallback failures; fallback exclusive/owned and never PASS; all failures sticky exit 2, unavailable child exits remain null;
- W/S/H exact path agreement through handoff/consumption/start/run/authorization/root-child markers and actual reviewed wrapper entrypoint; original root never selected/written, no arbitrary path/mode/command/environment change;
- original process/launcher/base identities, suspended assignment before resume, nested Jobs, termination confirmation/handle cleanup, 10-second original clock and other fixed deadlines, plus unchanged P/candidate/source/config/test/product bytes and counters.

Perform only separately authorized static syntax/format/interop checks at implementation time; no runtime repro or retry during correction/review. Static PASS does not establish actual persistence, self-check containment or timing. After PASS and coordinator acceptance, a **separate** disposition may authorize exactly one wrapper retry at the new fixed path under disposition 40. Preserve every resulting record/exit, including another non-PASS. No self-check success, runtime profile 30-second fit, identity collection, manifest readiness or build eligibility is claimed here.

## Work boundary and handback

Only static reads/searches, directory inspection and SHA-256 hashing occurred, plus writing this single report. Original evidence hashes were verified; neither file was modified, deleted or promoted. No source, other plan, checkpoint, ledger, manifest or output was edited. No code/runtime reproduction, tests, linters/parsers/compilers, imports, operational scripts/self-check/preflight/collection, GIS/numerical/candidate/build or browser work ran. Browser evidence is inapplicable.

Return to coordinator for the narrowly defined persistence/error-record and W/S/H retry-path decisions, unused-Sol-attempt disposition and subsequent different-session review. Stop before any implementation, retry-path preparation or runtime action. Candidate remains NO-GO/unservable; no build is authorized.
