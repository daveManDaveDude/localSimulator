# Retry-7 immediate source/path preflight result

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Disposition:** D150. Preflight only; no invocation authorized here.

## Source bindings

Read-only PowerShell `Get-FileHash -Algorithm SHA256` results:

| File | Observed SHA-256 | D150 required | Result |
| --- | --- | --- | --- |
| W `pipeline/scripts/invoke_teignmouth_float32_build3.ps1` | `842a599fda7d9082b56efb792b10154d3e9096af8ac755f16318777d1495eef8` | same | PASS |
| S `pipeline/scripts/run_teignmouth_float32_build3.py` | `8f4dbda2346db49a0b9cead30b33a8515879f9955bbec59d64e23386615f5016` | same | PASS |
| H `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py` | `f9f48f34198fe54eab800e8d2bc619631c11ce8ed44751a24a2c126e316ed373` | same | PASS |
| P `pipeline/scripts/teignmouth_build3_runtime_preflight.py` | `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b` | same | PASS |

Read-only fixed-string counts: W retry7=2/retry6=0; S retry7=1/retry6=0; H retry7=1/retry6=0; P retry7=0. All exact required counts passed.

## Path and ancestor observations

`Get-Item -LiteralPath -Force` confirmed `C:\`, `C:\vibe`, `C:\vibe\localSimulator`, and `.codex` are ordinary directories without the ReparsePoint attribute. The additional existing refusal-target ancestors `data`, `data\generated`, `docs`, `docs\milestones`, `docs\milestones\artifacts`, the topology artifact directory, and its `build-3` directory are ordinary directories without ReparsePoint. No required ancestor was missing.

`Test-Path`, `File.Exists` and `Directory.Exists` report the proposed parent `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-7` absent as both file and directory. `Get-ChildItem -LiteralPath C:\vibe\localSimulator\.codex -Force` enumerated immediate names; none equals `build3-supervisor-selfcheck-retry-7` using ordinal case-insensitive comparison after trimming trailing Windows dot/space characters.

The protected refusal targets are absent as files/directories and no normalized alias was found in the existing immediate parent:

- `C:\vibe\localSimulator\data\generated\teignmouth-float32-topology`
- `C:\vibe\localSimulator\docs\milestones\artifacts\Teignmouth-float32-topology\build-3\run-1`

The same normalized immediate-parent comparison was used for each existing parent. The proposed retry-7 parent and all derived outputs therefore remain absent at the time of this preflight. This is point-in-time evidence, not a reservation or race guarantee.

## Exact command/method summary and result

Executed read-only PowerShell operations in `C:\vibe\localSimulator`: SHA-256 each W/S/H/P file; read those four sources to count exact retry6/retry7 literals; `Get-Item` and inspect `PSIsContainer` plus `Attributes -band [IO.FileAttributes]::ReparsePoint` on existing ancestors; test exact proposed paths with `Test-Path`, `File.Exists`, and `Directory.Exists`; enumerate the safe immediate parents with `Get-ChildItem -Force`; normalize each child name with `TrimEnd([char[]]@('.', ' '))` and compare using `StringComparison.OrdinalIgnoreCase`.

Exact final console line: `D150 PREFLIGHT PASS; no root created, reserved or invoked` (with a follow-up confirming all seven existing ancestors on the refusal-target chains are safe). No retry1–6 root was inspected. No file/source/evidence was changed; no path was created or reserved; no runtime, process, self-check, preflight or build command was run.

**Result:** All D150 predicates passed. A separate one-use coordinator disposition is still required before exactly one retry-7 wrapper invocation.
