# Coordinator disposition 27 — submit supervision correction for independent review

Date: 2026-10-24

**Decision: The sole operational-preparation correction submission is complete and consumed. Submit the four exact files below for independent Sol review only. The self-check remains unrun; runtime preflight and build 3 remain unauthorized/unreserved. Candidate remains NO-GO.**

Disposition 26 and its bounded plan governed this correction. Exact current SHA-256 values:

- `pipeline/scripts/run_teignmouth_float32_build3.py`: `225d39476d3df0a40c39b18d22c5cab270e1d57777acbf441fab117bb91b1038`
- `pipeline/scripts/teignmouth_build3_runtime_preflight.py`: `f4b31ba14ce20c1f4471dd09fb751cbfb79f1d60bfa3e957188c4b722f277ff0`
- `pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py`: `8ee478c15a8d5c7fd02fc371663ea3edbf4615d0bb63a64727c9a3501693dfae`
- `pipeline/scripts/invoke_teignmouth_float32_build3.ps1`: `71cc049002e3457f82d77c2314bfd6ea3419af63bd50aba720908a8a391eeed0`

Final authorized static checks, run from `pipeline/`:

- Ruff check on the three Python files: PASS, exit 0 (`All checks passed!`).
- Ruff format check on the three Python files: PASS, exit 0 (`3 files already formatted`).
- Ruff cannot parse/validate PowerShell. The first Ruff check attempt included the `.ps1` file and failed with PowerShell-as-Python syntax diagnostics; this was a tool mismatch, not a script execution. A repository-root format invocation also used an invalid venv-relative executable path and failed to start; rerun from `pipeline/` passed.

No scripts were imported or executed. No self-check, runtime preflight, build, diagnostic, GIS load or browser check occurred. No candidate/geometry/test/fixture/builder/source/product file changed. Preservation hashes match accepted values for the candidate module, shared topology helper, focused tests, fixture and existing candidate builder. The PowerShell wrapper still requires static independent review.

## Unchanged counters and gates

- Diagnostics: 2/2 used; Luna candidate corrections: 4/4; candidate Sol correction: 1/1.
- Candidate implementation builds: 2/6 used; zero reserved; confirmation: 0/1 and ineligible.
- The one separate dispatch-preparation correction is consumed by this submission. It does not change candidate counters.
- Review all nine findings in review 14 and the exact wrapper/PowerShell path before any self-check. The existing 10-second self-check authorization remains conditional on independent PASS. Runtime-preflight-only requires a later disposition; build 3 requires another independently reviewed manifest/runtime closure and explicit reservation.
