# Coordinator disposition 32 — submit replacement implementation for independent review

Date: 2026-10-24

**Decision: The one operational replacement implementation submission is complete and consumed. Submit the four exact files for independent Sol review only. No executable mode is authorized. Candidate remains NO-GO; build 3 is unreserved.**

Governed by the user's explicit authorization and disposition 31, against Sol's accepted replacement plan. Verified SHA-256 values:

- `pipeline/scripts/run_teignmouth_float32_build3.py`: `a1792181a798b650e7692fa0d6a540b87b15a691a64c182310460c9a6beb295d`
- `pipeline/scripts/teignmouth_build3_runtime_preflight.py`: `6ab5dc1961364254582a0b8f581b497bb8d6cc74649a7daba648aa4765ba1cf7`
- `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py`: `9e25a189efea6c76272310c5ee438ccbef4cf2554260b00347d5334c87824070`
- `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`: `97d710885e68966c1cadaaa114983b9f6ad2eef6604c7013039f570d89de58005`

Implementer-reported static checks:

- Ruff check and format check passed on the three Python files.
- PowerShell AST parse passed without invoking the wrapper.
- Embedded C# declarations compiled without invoking any methods.
- Preliminary Ruff formatting/undefined-name findings and a PowerShell-regex extraction issue were corrected before the final reported passes.

Coordinator rehashed all four submitted files and confirmed unchanged accepted hashes for the candidate module, shared topology helper, builder, focused test and fixture. No other implementation paths were reported edited by this submission.

No script was imported or executed. No wrapper, self-check, runtime preflight, diagnostic, GIS load, candidate build or browser action occurred. Standalone runtime collection/verification remains gated on separately reviewed preparation-manifest bindings; runtime-preflight-only execution still needs a later disposition.

## Unchanged budgets and gates

- Candidate diagnostics 2/2, Luna corrections 4/4, Sol correction 1/1.
- Candidate implementation builds 2/6 used, zero reserved; confirmation 0/1 and ineligible.
- Prior operational correction 1/1 remains failed/consumed. Replacement submission 1/1 is separately consumed and changes no candidate counter.
- The conditional self-check gate has not been restored. Do not run it before independent PASS and a future explicit disposition.
