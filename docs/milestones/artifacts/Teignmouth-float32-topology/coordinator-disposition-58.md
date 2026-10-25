# Coordinator disposition 58 — submit Sol correction for independent review

Date: 2026-10-25

**Decision: CONSUME the single operational Sol correction and submit its exact W/S/H revision for independent Sol review 9 only.** No further operational correction allowance remains. No self-check retry, runtime, preflight, collection/verification, manifest preparation, candidate reservation/build, GIS/numerical work, serving or browser action is authorized by this disposition.

The Sol correction follows disposition 57 and diagnosis `build-3/supervisor-selfcheck-failure-diagnosis.md` (SHA-256 `685dbb46ec755910a93dcd7b9525b9f2dda1c6e0a0f14de85551f60456bb303f`). Coordinator independently rehashed and matched Sol's reported W/S/H hashes:

- W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`: `1ef041092e304a6a7f270d0886e4529caeba615bf14a3fb654f92b9873a61604`
- S `pipeline/scripts/run_teignmouth_float32_build3.py`: `17a7a347b175bfa3ad1a1dcbdc4167d3d4b1c8a73da0dc09d537ec1c6d4a8ef6`
- H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py`: `3419551b5c19e69c2487bb57c1bc49c102d4b7bfe1db1f93aea60cf038ebe05a`
- P unchanged `pipeline/scripts/teignmouth_build3_runtime_preflight.py`: `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`

Protected candidate/helper/builder/test/fixture/config hashes remain unchanged. Original failed caller and `.update` evidence remains byte-identical at `e88b0527b5f44f4f34ed7448a00b3ea4cb1706b929a18f339ef83fde6dd4442e` and `78e7bb547fc718b57c9ab286afb92d37436b68bb894e0a22df02914936703b75`. The proposed fresh retry root `.codex/build3-supervisor-selfcheck-retry-1/` and its checked caller/fallback/pending/handoff/start/run paths are absent. Targeted Git status provides no baseline diff for these untracked files; reviewer must inspect exact current implementations.

Sol reports Ruff check/format PASS for S/P/H, PowerShell AST parse PASS without wrapper invocation, and embedded C# compile-only PASS without method invocation. Preliminary/final command details are in the implementer handback; coordinator did not rerun gates. No test, source/runtime reproduction or operational command was run during this correction. The File.Move API choice was checked against Microsoft documentation: the overwrite overload is available on .NET Core 3.0+; no crash-atomicity or power-loss durability claim is made. Runtime fit remains unmeasured.

Independent review 9 must inspect W/S/H path synchronization to the new fixed retry root, existing-destination ownership checks, exclusive pending/fallback creation, error preservation and cleanup behavior, the correction's fixed one-shot retry design, and preservation of the original failed evidence and all existing process/deadline gates. It must verify all exact submitted/protected hashes and return PASS or actionable FIX_REQUIRED. Static PASS or this submission does not authorize a retry.

Operational Luna cycles remain 4/4 used/reviewed; the sole operational Sol correction is now used 1/1 and pending review. Historical candidate budgets remain unchanged: diagnostics 2/2, candidate Luna corrections 4/4, candidate Sol correction 1/1, implementation builds 2/6 used with none reserved, confirmation 0/1 ineligible. Candidate remains **NO-GO and unservable**; build 3 remains **unreserved**.
