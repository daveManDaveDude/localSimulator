# Independent review — immediate fixed fallback

2026-10-25. Independent Sol reviewer `/root/sol_review_face_diag`, under disposition 101. **PASS for this S-only correction and the previously reviewed console/stdio implementation's static acceptance.** The direct-return finding is closed. This is not an operational PASS or authorization for any next action.

Reviewed actual current S against prior finding report SHA-256 `fa2e03204a91ce6637fef40279eb788e70222cbedf9938b5154945e751fdb23c`, dispositions 92–101, accepted console-inheritance plan and the previous review chain. Coordinator-reported approved Ruff check/format exit-0 results were read, not rerun.

## Verified hashes and exact delta

| Artifact | Independently recalculated SHA-256 |
| --- | --- |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `28c92cc60e38ae23dcf58874eca67b8308b22772eee03b36d69471624fcdb089` |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `6ed89a17b769b15069c9ee47ca85f1bf72adf36e43b362772b0bf7749906049b` |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `13188dc1bfb10c5e7e3e92da91274f1529b7771ea735e8675df8caff5ad4b501` |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` |
| `selfcheck-fixed-fallback-correction-handoff.md` | `828e204fd362819189faf3c548ccd5179427189592feb7b6df1373833237a68f` |

There is exactly one matching direct-return line. Reversing only that line in memory to the prior literal assignment restores exact previous S SHA-256 `376187f474f4e91739d732ba064ec1db39be5863cfd5ce746250d0863c35a997`. Every other S byte is unchanged; W/H/P match pinned unchanged bindings. No reconstructed source was written or executed. The operational files are untracked; no reliable Git index history is claimed.

## Required criteria

| Criterion | Static assessment |
| --- | --- |
| Failed string conversion | **PASS.** S 3598–3601 catches failure of `str(exc)` and immediately returns the fixed literal `"exception message unavailable"`. That branch performs no type lookup, formatting, secondary extraction or dynamically constructed fallback. It cannot fall through into notes. This meets dispositions 98/100 and closes the precise prior finding. |
| Successful primary message and notes | **PASS.** Only successful string conversion reaches 3602–3613. Its exact text remains the prefix. At most the first four list entries are sampled, string notes are capped to 512 characters and encoded with JSON ASCII escaping. Extraction, slicing, serialization and appended-message construction remain within the best-effort BaseException guard, falling back to the original message on secondary failure. |
| Actual persistence paths | **PASS.** Normal failure `primaryError.message` calls the helper at 3703; outer self-check `error.message` calls it at 4192 before the existing writes. Available stdio-release and suspended-child-cleanup notes therefore reach both applicable saved message paths on successful conversion. Primary type, phase, original exception identity and bare propagation are unchanged. A failed primary conversion deliberately returns only the fixed literal, as authorized; no notes are fabricated. |
| Stdio close accounting | **PASS, unchanged.** S 2020–2036 attempts each of three owned stdio handles once, distinguishes true from false/raised/unconfirmed release and captures false-return native error before another native API/clock. Optional notes preserve an earlier query/CreateProcess primary. No retry or double-close is added. |
| Created-but-unconfirmed release | **PASS, unchanged.** 2051–2052 fails before assignment/authorization/resume; existing unassigned suspended-process cleanup at 2086–2110 directly terminates, bounded-waits/observes and closes process/thread handles. Notes precede caller serialization. The all-confirmed path retains exact Job assignment before callback/resume. Native API success itself is not proven by static inspection. |
| Console policy and call scope | **PASS, unchanged.** Lazy finite console query, existing native PID binding, four-call/4096-DWORD bounds and original deadline remain. Normal/tree calls at 3768/4030 alone opt in; standalone preflight/build preflight/numerical runner at 4361/4680/4778 remain default. Suspended creation, redirected stdio and CREATE_NO_WINDOW default behavior are preserved; no console attachment/window API or host exemption exists. |
| Strict gates and cleanup | **PASS, unchanged by exact inverse and prior scope proofs.** Retained identity/exit7/7/reaping, complete authoritative census, unconditional unexpected-ID rejection (3924/3967), zero/empty/zero before the unchanged deliberate tree probe, diagnostic-only member facts, Jobs, inherited deadlines and error/persistence/final-cleanup gates remain. No source/profile/geometry/numerical/acceptance or path change exists. |

No residual blocker was found in this static correction scope. The previously reviewed secondary-note omission, unguarded fallback formatting and non-direct fallback findings are closed; no claim is made that every conceivable resource/API failure guarantees durable evidence.

## Limits and authority

Work was static source/document reads/searches, hashes, in-memory inverse comparison and this report. No source/checkpoint/disposition/manifest/evidence edit, retry-root access, new root, tests/imports/scripts/linters/parsers/compilers, process inspection/probes, wrapper/self-check/preflight/runtime/collection, GIS/numerical/build or browser operation occurred. Prior evidence was not independently rehashed here; no runtime evidence was created. Reported static gates were not rerun.

Actual native cleanup/console efficacy/persistence, 10-second fit and **30-second runtime-profile fit remain unmeasured**. Outer exit1/internal2, historical census association uncertainty and unsaved `957157…` provenance remain unresolved. All consumed roots/counters remain intact. PASS grants no correction, invocation, self-check or downstream authority. A separate fresh-root plan/review and one-use coordinator gate remain mandatory. Candidate remains **NO-GO and unservable**, build 3 **unreserved**.
