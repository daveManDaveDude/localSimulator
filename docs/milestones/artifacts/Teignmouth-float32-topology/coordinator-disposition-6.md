# Coordinator disposition 6 — reserve implementation build 1

Date: 2026-10-24

**Decision: GO for one bounded offline candidate build, ordinal 1, maximum 180 seconds.** Independent Sol review 3 approved build reservation after verifying all 193 correction-2 bindings and the corrected XYZ assembly regression. The coordinator independently reverified all 193 bindings; there were zero mismatches and the generated candidate output path was absent.

This authorizes only the isolated offline builder using the correction-2 manifest and current attempt ledger. Do not change code/config after reservation. Persist all candidate or partial outputs and evidence in the isolated generated root and build-1 evidence folder. Enforce the runner's watchdog, record elapsed/peak-memory telemetry and post-run protected-input verification. No viewer/product/browser/Site/public integration or serving is authorized. The candidate is not accepted by a passing build alone; all offline gates and separate review remain required.

Command:

```powershell
pipeline/.venv/Scripts/python.exe -B pipeline/scripts/build_teignmouth_float32_candidate.py `
  --input-manifest docs/milestones/artifacts/Teignmouth-float32-topology/correction-2/input-manifest.json `
  --attempt-ledger docs/milestones/artifacts/Teignmouth-float32-topology/attempt-ledger.json `
  --build-ordinal 1 `
  --evidence-dir docs/milestones/artifacts/Teignmouth-float32-topology/build-1
```

## Counters after reservation

- Initial Luna implementation: 1 used, 0 reserved.
- Luna correction cycles: 2 used, 0 reserved.
- Sol corrections: 0 used, 0 reserved; still ineligible before four Luna cycles are reviewed.
- Diagnostics: 1 used, 0 reserved.
- Implementation builds: 0 used, 1 reserved (build 1 of 6).
- Independent confirmation builds: 0 used, 0 reserved; eligible only if all offline gates pass.
- Candidate serving/runtime output: ineligible.
