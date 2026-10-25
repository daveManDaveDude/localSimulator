# Independent Sol review — Teignmouth corridor prototype

Verdict: **FIX REQUIRED — objective incomplete; safety stop was correct.** The one Sol correction remains unused. This review did not edit implementation files or rerun numerical/browser work.

## Findings

1. **Safety failure (behavior/formulation conflict):** The implementation correctly stops at `pipeline/torquay_pipeline/teignmouth_corridor_prototype.py:246–261`: maximum source-relative change is 6.4609168 m against strict `<5 m`; maximum positive added gradient is 2.3475946 m/m against strict `<1 m/m`. Reported worst-edge coordinates/elevations support the gradient calculation. Do not integrate or render this recipe. It fails as measured; this does not prove all corridor-grading methods infeasible.
2. **Failed geometry is not independently certifiable (missing evidence):** the builder persists geometry only after the safety gate, so failed X/Z/Y/index buffers are absent. The topology and geometry hashes are builder-reported evidence; this reviewer cannot independently certify their contents without reconstruction. Do not rerun solely to recreate this failed mesh.
3. **Prototype comparison incomplete (missing evidence):** no candidate directory, DEV harness, composite road/building/walk integration or paired screenshots exist. Junction ownership, bridge/tunnel policy across surrounding roads, affected building contact, road reclip/agreement and walk clearance remain unverified. Their absence correctly follows the safety stop.

## Preservation and verification

- All 10 submission-manifest entries match current file sizes and SHA-256 hashes.
- Before/after preservation snapshots are identical. Reviewer independently rehashed all 868 listed paths with zero mismatches. The scan does not cover every ignored raw GIS file or prove every byte from before implementation began.
- Reported focused suite: 123 passed, 1 skipped; Ruff and format checks passed. Reviewer inspected records and tests but did not rerun them. These do not establish geographic/browser acceptance.
- No arbitrary byte cap was added; measured memory/buffer sizes remain measurements.
- No public/default output or accepted-preview change is evidenced.

## Disposition

The recorded failure and stop are valid. The remaining correction could clarify evidence wording/future witness retention, but review found no demonstrated bounded fix for the measured safety violations under the frozen recipe. Another recipe trial/build/browser comparison requires a coordinator/user disposition consistent with the active stop condition. Teignmouth v2 remains separate, exhausted, FIX REQUIRED and inactive.
