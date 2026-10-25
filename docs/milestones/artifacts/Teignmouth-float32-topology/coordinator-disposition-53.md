# Coordinator disposition 53 — submit supervisor correction cycle 4 for review

Date: 2026-10-25

**Decision: CONSUME operational Luna cycle 4/4 and submit its W/S-only revision for independent Sol static review 8.** This disposition does not authorize runtime execution, manifest preparation, candidate building, GIS/numerical work, serving, or product changes. All four Luna operational cycles are now consumed; no further Luna attempt is authorized within this allowance. The existing Sol correction is not reserved and remains ineligible until all four cycles have been independently reviewed.

## Coordinator hash reconciliation

The coordinator independently rehashed the submitted files, unchanged P/H, and all previously protected candidate/helper/builder/test/fixture/config files. All hashes match the cycle-4 report and prior protected values:

- W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`: `c707ebbda14c562083fb2485854b4d4d515bc809987d13136479f7cd5d597b06`
- S `pipeline/scripts/run_teignmouth_float32_build3.py`: `73345c89e9ec49c4c092a00a93b47c4642b32f7deecd7108c018b04910c3717c`
- P unchanged `pipeline/scripts/teignmouth_build3_runtime_preflight.py`: `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`
- H unchanged `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py`: `9fc73a8ed7aca3b4e223d3f23a7bd676f48011aa0abe98eb864f9e98a5191d20`
- Candidate `a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b`; topology helper `88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880`; builder `5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b`; focused test `34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8`; fixture `4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea`; config `e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228`.

Targeted Git status shows these operational/candidate files are untracked in the current checkout and cannot provide a reliable before/after diff. The independent reviewer must inspect the full final W/S contents against review 7, diagnosis 3 and disposition 52. P is byte-identical to cycle 3. The candidate and protected files remain byte-identical to recorded hashes.

## Reported static checks

Luna reports Ruff check and format PASS from `pipeline/`:

```powershell
.venv/Scripts/python.exe -m ruff check scripts/run_teignmouth_float32_build3.py scripts/teignmouth_build3_runtime_preflight.py scripts/teignmouth_build3_supervisor_selfcheck.py
.venv/Scripts/python.exe -m ruff format --check scripts/run_teignmouth_float32_build3.py scripts/teignmouth_build3_runtime_preflight.py scripts/teignmouth_build3_supervisor_selfcheck.py
```

PowerShell AST parsing passed without wrapper invocation, and embedded C# declarations compiled without any interop method invocation. Exact commands are recorded in Luna's cycle-4 handback and were reviewed for provenance. Preliminary Ruff import-order/unused-local/format issues were corrected before the final reported PASS. The coordinator did not rerun static gates. No tests, imports, operational scripts, self-check, preflight, runtime collection/verification, diagnostic, GIS, candidate build, numerical work, serving, or browser action occurred. The 30-second runtime fit remains unmeasured.

The build-3 input manifest, external-runtime manifest, runtime identity, and reserved-ledger snapshot remain absent; candidate output remains absent. Candidate is still **NO-GO and unservable**, and build 3 remains **unreserved**. Candidate counters are unchanged.
