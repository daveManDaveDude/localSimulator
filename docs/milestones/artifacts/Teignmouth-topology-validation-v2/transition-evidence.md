# Teignmouth topology validation transition v2 evidence

Status: implementation submitted for independent Sol review. The transition remains disabled. This report profiles the retained `road-05` witness only; it does not convert the failed topology trial into a passing candidate or authorize a later trial.

## Retained-witness profile

Command, from `pipeline`:

```powershell
& '.venv/Scripts/python.exe' scripts/profile_teignmouth_validation_v2.py
```

The profile reconstructed the exact retained road-05 topology and Float32 candidate in memory, invoked no solver, wrote no trial record, and left all ten retained `road-05` files byte-identical. The complete machine-readable output is [retained-road-05-profile.json](retained-road-05-profile.json), SHA-256 `7bd00eaffe376ff1fd9f732dc688aeec1fd2718410ed425226baf58a356b3fa1`.

Measured profile components:

- Reconstruction and input preparation: 15.782591 s.
- Validation-context setup: 0.012866 s.
- V2 gate validation: 61.969730 s; total validation with context: 61.982596 s.
- The largest measured gates were all 3,613 building-footprint reports at 38.843 s, accepted-plane refinement at 10.148 s, earthwork overlay at 6.203 s and source-triangle ownership at 4.127 s. The profile records every gate time and cache counter.
- Retained road-05 timing: 16.082548 s pre-solver preparation, 26.048782 s solver, 80.517233 s legacy validation and 5.625867 s finalization/other residual; total 128.274431 s. That run exceeded its original 120 s cap and remains a consumed, failed trial.
- Projected end-to-end using retained preparation, solver and finalization components plus the measured v2 validation: 109.739793 s. This is 15.260207 s below the transition's 125 s qualification limit. It is a single implementer profile; the independent Sol timing profile is still required before any transition activation.

The v2 report is byte-equivalent to the retained aggregate for all twelve gate reports, all report identity fields, all 3,613 building records, and the aggregate pass/fail result. The original road-05 aggregate remains failed. `candidateOutputStillAbsent=true`. This measures validator equivalence and a projected future timing opportunity; it is not a topology or offline-candidate PASS.

## Input and code identity transition

The old Road-surface-treatment evidence-tree digest is `a83f7f30ebd3fba437364a570ee3349e72bec7b62e5bc9304708b1d50512c688`; the current digest is `4413d4fc79adcf846d578e51fa2d65ee46b674721b1e1e61759fae1a0214f94a`. The exact 2,411-byte consumed-trial inventory, SHA-256 `9e9c9d083014dd2649fc2b4d284a235423358466b6e91b3d07959c2369f5d8d6`, is the only excluded file when reconstructing the old tree. The profile independently validated both consumed directories against all ten inventory files per trial.

The implementation-start checkpoint baseline is `5b0cfb793f3780b9ee2af6087d643a22cde32b43c9b7442ed9940306b09a17a6`. Retained consumed-trial records bind the legacy post-run checkpoint `a75afe6f29d99e35e78f58bbc70ffe005d1245823ad643cbc90d453a1cfe3e75`; flip-05's invocation checkpoint is `eb5a4ddac059abdbfff1dd9006412e07396028362e5cd9ced4185f173154bf7f`. The profile's live protected-input snapshot had 36 entries, digest `7b34d00479b01d096cbffd60939f663192c93fd929f1a086e300a680a6f6add2`, and checkpoint digest `74ac9db846f73074f0f7e09d8bbb6a5c12cd556a6bbaf7709f32f9c7875106cf`. The final checkpoint after recording these results is `871a226730ae9ed15f388e227e450f17cd30e64183c51f315a26a3d8f811d6c3`. After that checkpoint update, a fresh read-only preflight rebuilt the full 36-entry current map and passed both transition validators: current snapshot SHA-256 `d7287a3ea0ff21722e8fcfa0d3049ae52222ecaddbc648fd04f3abb4019db580`; the two consumed maps differ only at the named checkpoint and evidence-tree entries. A future trial must capture its own complete stable before/after snapshot.

The consumed flip-05 code map remains its original 12 entries (canonical map SHA-256 `173e8573f59e83a32d9beb8782d92fbcd58ee7ae9f7c52c1f8068b0e9a1c5a95`). The road-05 map remains its original 15 entries (canonical map SHA-256 `b1b1216d0f9ede377bb55419829afe09f905019034300c5d17402b8124465efc`). Seven additive v2 code/spec/test files are pinned by the config extension map (canonical map SHA-256 `4ff1bf9df2f9f12d77d3c918f6c9f19ced665e2e54e929171453e0e3679fdfde`). The transition config is `config/road-surface-teignmouth-topology-transition-v2.json`, SHA-256 `eeeb53e2562d8502ca92af388cd9407a3becd0563afd4f6a898df7f355b84948`; activation is false and Sol review is pending. The final checkpoint hash is recorded here rather than embedded in itself or the config.

## Checks and limits

Focused Python command:

```powershell
& '.venv/Scripts/python.exe' -m pytest tests/test_road_surface_validation_v1.py tests/test_road_surface_validation_v2.py tests/test_road_surface_validation_transition_v2.py -q
```

Result: 27 passed. Ruff check and format-check passed for the six v2 validator, wrapper, profile and test files. `git diff --check` passed. The transition preserves 2,000 iterations and the absolute 120/125/135 second windows; timeouts remain write-once and are not retried. No trial/solver invocation, candidate output, public/runtime integration, or browser work was performed. The independent Sol profile and review remain outstanding.
