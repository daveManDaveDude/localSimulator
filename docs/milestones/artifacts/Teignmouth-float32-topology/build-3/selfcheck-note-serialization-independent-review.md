# Independent review — secondary-note serialization

2026-10-25. Independent Sol reviewer `/root/sol_review_face_diag`, disposition 97. **FIX REQUIRED:** the new message-unavailable fallback can itself fail outside a guard and replace the primary exception. The earlier deterministic omission of notes is otherwise closed. This report authorizes no correction or operation.

Reviewed actual current S against prior S, accepted console-inheritance plan, dispositions 92–97 and finding report SHA-256 `1cd46eb6654ca8f9c070bdc1fab347910d7d7767043432a8dcf36ed89bb4dd24`. Coordinator-reported Ruff exit-0 checks were read, not rerun.

## Exact bindings and scope

| Artifact | Independently recalculated SHA-256 |
| --- | --- |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `a0ebfebbde4eabdba0dc3946d0222070b3ee8b28b8f8aa3a2d69234c01538e1e` |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| `selfcheck-note-serialization-correction-handoff.md` | `236b87a78f3a2ec00a32c4daa993056d8b3a42745cd0f1c5a1590e5bce5448f0` |

An in-memory inverse removed only `_exception_message_with_notes`, restored `str(primary)` and restored the prior outer error dictionary formatting/`str(exc)`. Result SHA-256: `f50cbb07a0d745eb87d4d4c8e357e0168801507aae2de28f915e3d7ae30e4a55`, exactly the accepted previous S. No reconstructed source was written or executed. All remaining S bytes are unchanged; W/H/P match their pinned bindings. No reliable Git index baseline is claimed for the untracked operational files.

## Concrete residual

**1. Unguarded fallback formatting can mask the original exception — S 3597–3602, reached at 3703 and 4192.** `str(exc)` is caught by `except BaseException`, but its handler then executes `message = f"{type(exc).__name__}: message unavailable"` at **3601** outside another guard. This still performs attribute lookup/formatting/string allocation. For example, if primary exception string conversion fails under memory pressure, a second allocation failure in this fallback escapes the helper instead of returning a safe fallback. The later notes try at 3602 does not guard this earlier handler.

At normal failure checkpoint line 3703, the helper runs before that checkpoint's guarded persistence block; an escaping fallback failure interrupts checkpointing and the remainder of the outer error handler. At outer error line 4192, it similarly interrupts constructing BLOCKED_SELFCHECK's error record. The surrounding finally remains reachable, but the newly raised secondary formatting error replaces the original query/CreateProcess/cleanup exception in propagation and can prevent the intended blocked-error persistence. No resource failure was induced or measured; this is a concrete reachable exception path in the new code.

Disposition 96 explicitly requires best-effort extraction/formatting that cannot mask the primary or block cleanup. Its success-path prefix requirement does not require formatting a type name when the primary's string conversion is itself unavailable. **Concrete remedy for a separately authorized correction:** make that failure fallback independently safe, for example by retaining a fixed pre-existing literal instead of performing a second unguarded formatting/allocation operation, while preserving the exact original `str(exc)` prefix whenever available. Keep all optional note extraction, JSON serialization and final concatenation within the existing guard; preserve both call sites and all launch/cleanup behavior. This report does not authorize or implement the change.

## Criteria otherwise satisfied

| Criterion | Static assessment |
| --- | --- |
| Both persisted paths actually use helper | **PASS.** `checkpoint_normal_failure` stores `_exception_message_with_notes(primary)` in existing `primaryError.message` at 3700–3705 before persistence. Outer self-check stores `_exception_message_with_notes(exc)` in existing `error.message` at 4187–4200. Type/phase fields and bare re-raise remain. No schema field/version or artifact was added. |
| Bounded JSON-safe notes | **PASS when extraction succeeds.** 3603–3610 accepts only a list, samples at most its first four entries, retains string notes capped to 512 characters each, and JSON-encodes with ASCII escaping. The exact available primary message is the prefix. Non-string notes are ignored; no unbounded traversal/exception rendering is added. Optional extraction, JSON encoding and appended-message construction are guarded by 3602–3612 and fall back to the original message. Finding 1 concerns only the preceding unavailable-message fallback. |
| Query/CreateProcess plus failed close | **PASS for ordinary saved-note path.** `_launch_suspended` retains the primary and attaches close details before propagation at 2037–2048. Both serializers now include those notes; `str(exception)` alone no longer silently drops them on successful serialization/persistence. Optional add_note failure remains best-effort rather than fabricated evidence. |
| Successful creation/unconfirmed release | **PASS for preserved control and ordinary saved-note path.** 2051–2052 fails before assignment/authorization/resume; 2086–2110 directly terminates, bounded-waits/observes and closes the suspended unassigned process/thread. Release and cleanup notes are attached before the caller serializers, so they reach the normal and/or outer error message when available. No close failure can return launch success. |
| Close API/ownership | **PASS, unchanged by inverse.** Each of the three stdio handles receives one attempt; true/false/raised outcomes remain distinct; false captures native last error immediately before another native call/clock. No retry/double-close or transfer is added. All-confirmed paths retain assignment-before-authorization/resume and ownership. Native API success itself remains unmeasured. |
| Console/two opt-ins/defaults | **PASS, unchanged.** Lazy bounded console query at 1880–1948, original deadline, existing native PID binding, 32/4/4096 bounds and fail-closed semantics remain. Normal/tree helper calls at 3768/4030 alone opt in. Standalone preflight, build preflight and numerical runner at 4361/4680/4778 remain defaults with CREATE_NO_WINDOW; all remain suspended. No attachment/new-window API or policy expansion exists. |
| Strict acceptance/deadlines | **PASS, unchanged.** Exact inverse binds retained identities/exits/reaping, complete authoritative census, unconditional unexpected-member rejection, zero/empty/zero before tree, diagnostic-only member details, Jobs, cleanup, reporting guards and original numerical/self-check/runtime gates. No source/class exemption, timeout reset or candidate path was added. |

## Limits and status

Work was static source/document reading/searching, hashing, in-memory inverse comparison and this new report. No source/checkpoint/disposition/manifest/evidence edit, retry-root access, root creation, tests/imports/scripts/linters/parsers/compilers, process inspection/probes, wrapper/self-check/preflight/runtime/collection, GIS/numerical/build or browser operation occurred. No static check was rerun and no runtime evidence was created.

10-second timing, native cleanup/console efficacy/persistence and **30-second runtime-profile fit remain unmeasured**. Outer exit1/internal2, historical census association and unsaved `957157…` provenance remain unresolved. Consumed roots/counters remain intact. FIX REQUIRED grants no next action. Candidate remains **NO-GO and unservable**, build 3 **unreserved**; separate coordinator gates remain necessary.
