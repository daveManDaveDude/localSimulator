# Coordinator disposition 57 — reserve the operational Sol correction

Date: 2026-10-25

**Decision: GO for the single unused operational Sol correction, based on the bounded diagnosis, after all four Luna cycles have passed independent review.** This is the only operational Sol correction authorized by disposition 40. It is separate from the already-consumed candidate Sol correction budget. Stop after this correction if independent review finds FIX_REQUIRED; no new Luna/Sol retries are granted.

Diagnosis: `build-3/supervisor-selfcheck-failure-diagnosis.md`, SHA-256 `685dbb46ec755910a93dcd7b9525b9f2dda1c6e0a0f14de85551f60456bb303f`. Coordinator rehashes immediately before this reservation match: W `c707ebbda14c562083fb2485854b4d4d515bc809987d13136479f7cd5d597b06`; S `73345c89e9ec49c4c092a00a93b47c4642b32f7deecd7108c018b04910c3717c`; P `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`; H `9fc73a8ed7aca3b4e223d3f23a7bd676f48011aa0abe98eb864f9e98a5191d20`. Failed caller evidence remains byte-identical: caller record `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e`, `.update` `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75`. The exact exception remains unknown; do not claim a particular replacement error.

## Authorized files and correction

The Sol implementer may edit only these three existing files:

- W: `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`
- S: `pipeline/scripts/run_teignmouth_float32_build3.py`
- H: `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py`

P, candidate/source/test/config/GIS/product files, ledgers other than coordinator metadata, historical evidence and the original failed self-check evidence must remain unchanged.

1. In W, fix owned caller-record replacement with one explicit supported same-directory .NET replacement operation after the exclusive pending file has been fully written, flushed and closed. The chosen operation must require the already-owned canonical destination to exist and pass current parent/reparse/ownership checks; missing destination or stale/unowned pending file is refusal. Do not delete first, truncate in place, retry through another replacement method, or overwrite the original failed evidence. Microsoft documents `File.Move(String,String,Boolean)` as the overwrite-capable overload for .NET Core 3.0+; W requires PowerShell 7.4+. This authorization does not claim crash atomicity or power-loss durability.
2. Preserve structured primary and secondary persistence errors plus launcher-created/assigned/resumed state without recursive persistence masking the initial failure. Keep evidence/clock operations from preventing required process/Job cleanup. Any persistence/fallback failure is sticky non-PASS and exit 2; unavailable exit/termination telemetry stays null.
3. Add exactly one terminal fallback filename `caller-invocation.failure.json` under the fresh retry root only, created exclusively and flushed/closed, used only when normal terminal caller persistence fails. It carries the existing caller schema and error fields, never overrides the primary/pending record and never satisfies a gate. If fallback fails, preserve exit 2 and emit diagnostics safely; do not claim durable error telemetry.
4. Keep the original failed evidence root `.codex/build3-supervisor-selfcheck/` immutable. For one future retry only, synchronize W/S/H to the new fixed root `.codex/build3-supervisor-selfcheck-retry-1/` with its own `run-1` records. Do not add automatic path search, arbitrary path/CLI/environment selection, reuse/reset of the old root, or more retry slots. The new root and every owned caller/fallback/pending/handoff/consumed/start/log/run/helper path must be checked absent before retry preparation. The exact retry is not authorized by this disposition.
5. Keep the reviewed W → venv launcher → base interpreter → S → H chain, authenticated nonce/one-use protocol, suspended assignment before resume, nested Jobs, cleanup/termination behavior and original 10-second self-check deadline. No mode, schema, command contract, import behavior, root category, dependency, candidate policy, numerical limit, product/data byte or trust boundary change.

Static gates only after correction: Ruff check/format for S/P/H, PowerShell AST parse without wrapper invocation, and embedded C# compile-only without calling interop methods. No tests, repro, runtime/self-check, preflight, collection/verification, manifest preparation, GIS/numerical/build, browser or serving. Submit final hashes and exact command/results for independent review by `/root/sol_review_face_diag`, a different Sol session from the implementer. The reviewer must preserve the original failed evidence and verify only the exact new retry root for its static path agreement; no retry-path records are created during implementation/review.

After independent PASS, a separate coordinator disposition may authorize exactly one wrapper-driven self-check attempt using the new fixed root, with a fresh 10-second QPC start. It must preserve the original failed invocation permanently. Runtime collection and all later phases remain gated. Candidate remains NO-GO/unservable, build 3 unreserved, runtime fit unmeasured, and historical candidate counters unchanged.

## API reference

The Microsoft .NET `File.Move` documentation lists `Move(String, String, Boolean)` as replacing an existing destination when `overwrite` is true, and applies it to .NET Core 3.0 and later: [File.Move Method](https://learn.microsoft.com/en-us/dotnet/api/system.io.file.move).
