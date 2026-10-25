# Minimal supervisor remediation plan

Date: 2026-10-24. Sol planning only, following `independent-supervisor-review.md` (SHA-256 `79f6169bf35c9d20c6edbea89df77895bb851dcee4e42e76a95c35d578aceaa2`). **No implementation or execution authorization. Candidate remains NO-GO; build 3 remains unreserved.**

## Exact proposed file set

Correct only the three submitted operational files:

- `pipeline/scripts/run_teignmouth_float32_build3.py` (S).
- `pipeline/scripts/teignmouth_build3_runtime_preflight.py` (P).
- `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` (H), only to supply fixed descendant-start/identity evidence needed by the self-check.

Add **one fixed caller wrapper**, `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` (W). It is needed to cover Python startup/import time and observe the supervisor's actual native process exit. This fourth code path requires explicit coordinator scope authorization; dispositions 24–25 authorized only three files. No other implementation/test file is proposed. Supporting manifests, authorization/handoff records and caller/result records are coordinator/owned execution metadata, not candidate code.

W accepts only fixed mutually exclusive self-check/runtime-preflight modes or fixed build dispatch, with no arbitrary commands, paths or durations. Launch hidden. Start the absolute clock before process launch/setup, establish outer kill-on-close containment for supervisor/descendants, and pass a fixed parent-owned one-use handoff containing mode/start/deadline/process identity. S validates that handoff and uses the same Windows monotonic clock domain; it must not restart the budget after imports. W preserves actual supervisor process exit separately from chosen wrapper exit. The invoking tool/caller separately records W's actual exit. W's nested containment must not permit breakaway or introduce a memory cap.

## Findings 1–9: minimum changes and proof

| Finding | Concrete remediation | Required evidence |
| --- | --- | --- |
| 1. Deadline/setup/loops | W owns the full invocation clock; S propagates its absolute deadline. Bound process-list retries/sampling loops and every wait to remaining time; never round a wait beyond the remaining budget. Preserve total build **180 s**, absolute numerical cutoff **150 s**, self-check **10 s** and existing standalone-preflight **30 s**. | Static trace of every launch/wait/cleanup path, then only the conditionally authorized nonnumerical self-check with caller elapsed/timeout records. No candidate timing experiment. |
| 2. False self-check PASS | S requires actual descendant-start evidence from H, successful root/child identity checks, active count zero, confirmed root exit and completion within 10 s. Deadline exhaustion/unconfirmed termination is non-PASS. Persist correct mode-specific budgets. | Static isolation/conditions review; once PASS, one bounded self-check records expected exit 7, descendant marker/PIDs, deliberate timeout and confirmed cleanup. |
| 3. Handle/error cleanup | S assigns each handle a single owner; remove duplicate thread close. Put API/job setup inside durable error handling. Close jobs in finally even if termination/accounting fails; record uncertainty and never claim clean termination without evidence. | Static success and each launch/configure/assign/resume/error cleanup path, plus the bounded self-check. No new broad test suite. |
| 4. Descendants failure becomes PASS | S makes forced termination/unexpected remaining descendants sticky non-PASS, excluded from every PASS promotion. | Static status-transition table; self-check timeout status remains distinct from normal numerical acceptance. |
| 5. Exit-role/standalone PASS errors | S stores preflight, builder runner and numerical-worker exits by role/PID/creation identity. Capture actual exit after confirmed termination; otherwise unavailable. Standalone preflight PASS requires clean job completion and no forced cleanup. | Static branch review; self-check exit records. Runtime evidence waits for separate preflight authorization. |
| 6. Cache census | P distinguishes missing `__cached__` metadata from an existing eligible bytecode file; record absent paths without calling them loaded files. Validate existing cache/source/native/data/startup inputs against the approved closure. No package changes. | Static census review. Actual import/module census only in the later authorized runtime preflight. |
| 7. Control bindings/authorization | S/P reject duplicates/empty required sets and enforce fixed schema/counts plus mandatory supervisor/wrapper/preflight/helper/builder/config/identity/external-manifest/reserved-snapshot bindings. Final independent manifest review checks full historical/source closure. Internal build-dispatch preflight requires a parent-issued one-use handoff bound to invocation/reservation/contained process; direct unguarded mode fails. Standalone retains separate coordinator authorization. | Static negative-path inspection; later independent manifest/hash review. Coordinator supplies authorization/reservation metadata; scripts do not create permission or alter counters. |
| 8. Partial preservation/telemetry | S returns/persists checked count and accumulated mismatches immediately on timeout/error, without scanning beyond deadline or replacing partial counts with zero. Sampling failures become unavailable observations; containment failures remain fatal. Key process samples by PID plus creation identity and label partial scope. | Static error-path audit; bounded self-check may show process identities. Full preservation/memory observations only during separately reserved execution. |
| 9. Paths/archive/caller exit | S validates lexical fixed paths and resolved ancestry, including exact run leaf under build-3 and junction policy, immediately before any move. After confirmed termination, normal and exception paths either safely archive to an absent owned target or explicitly retain output unservable at its exact path. W supplies concrete native supervisor-exit capture. | Static path/status review; final fresh-path metadata and wrapper hash independently reviewed. No candidate output created merely to test archival. |

## Metadata versus code

Coordinator-owned prerequisites: authorization for W and this bounded operational correction; final code hashes; exact external-runtime allowlist/identity; standalone-preflight authorization; later complete protected-input manifest; later post-reservation snapshot; fresh-path checks; and actual caller-exit evidence. S/P/W validate these records but cannot manufacture authorization, infer runtime equality or reset budgets. The external runtime contract must identify the base Python/native/module/data closure outside the workspace, separately from repository bindings; the venv shim hash is insufficient.

Do not edit frozen diagnostic scripts/evidence, existing builder, candidate implementation, shared helper, fixture/test modules, package installations, source data, product or geometry algorithms. Preserve all source/origin/domain/recipe/collision guards/numerical limits and strict nonempty exact source-plane-zero. No memory cap, tolerance change or parameter sweep.

## Sequence and stop conditions

1. Coordinator explicitly authorizes the exact operational file set, including W; implement without executing probes/builds.
2. Independent Sol statically reviews corrected hashes and isolation against all nine findings. Static Ruff/format remains limited to separately authorized operational preparation.
3. Only after PASS may the already conditional one-shot **10 s nonnumerical self-check** run. Do not delete an existing self-check leaf or retry without explicit direction; a failure remains preserved and blocking.
4. Review its actual records. Runtime-preflight-only execution still requires a later separate disposition and complete planned identity/closure inputs. No automatic transition to numerical work.
5. Independently review runtime closure, final build manifest, wrapper/handoff, reserved snapshot and absent output paths. Build 3 requires its own subsequent reservation/disposition; none is created here.

Stop on scope expansion, altered protected bytes, unmet authorization, missing closure/identity, unconfirmed process termination, deadline overrun, preservation mismatch or unsafe/existing output. No automatic correction loop or numerical retry. Diagnostics 2/2, Luna corrections 4/4 and Sol correction 1/1 stay consumed; builds remain 2/6 used, zero reserved. Operational preparation classification grants no extra candidate attempts.

Planning boundary: no implementation, script import, self-check, runtime preflight, test, build, diagnostic, GIS load, browser action or ledger/checkpoint edit occurred. Only this requested plan was written; its SHA-256 is calculated for handback.
