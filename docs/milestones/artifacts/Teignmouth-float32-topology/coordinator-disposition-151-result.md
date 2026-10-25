# Retry-7 one-use self-check result — coordinator record

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** D151, exactly one wrapper invocation.

## Command and outer result

Executed once from `C:\vibe\localSimulator`:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File pipeline/scripts/invoke_teignmouth_float32_build3.ps1 -Mode self-check
```

The command returned process exit code0 in5.146 seconds with no console output. It was not replayed. `caller-invocation.json` reports `CALLER_COMPLETED`, mode `self-check`, phase `nonnumerical-self-check`, chosen wrapper exit0, native launcher exit0, supervisor script exit0, 4.5417195 elapsed seconds within the10-second budget, and `deadlinePassed=true` (the current-before-deadline predicate passed). Outer termination was confirmed. The one-use handoff was consumed and bound to this invocation.

## Internal self-check result

`run-1/invocation.json` reports **`PASS_NONNUMERICAL_CONTAINMENT_SELFCHECK`**, outer command exit0, and4.5145251 seconds elapsed. The expected nonzero helper exited7 through both launcher and interpreter; its complete final Job accounting was0 before/0 after with an empty complete PID list and no unexpected process. Drain/evidence checkpoint errors are empty/null.

The tree wait reached its expected3-second horizon (`waitOutcome=expected-horizon`; `treeProbeTimedOut=true` is the expected wait-horizon observation). The new strict tree proof completed **12/12 periodic censuses** and one final census. Final proof status is complete, terminal `ERROR_NO_MORE_FILES`=18, rowCount356, and `finalComplete=true`; the last periodic proof was also complete, terminal18, rowCount356. Final census completed before the inherited deadline-minus-one-second containment cutoff and retained the one-second cleanup reserve. Tree termination was requested and confirmed, active processes after request=0, and the root's expected post-termination exit code was124. No timeout/deadline or termination failure is reported.

The records state `candidateBuilt=false`, `candidateOutputCreated=false`, `candidateEligibleForServing=false`, and `gisGeometryLoaded=false`. This run proves only the nonnumerical containment self-check; it does not build the candidate or authorize service/publication.

## Exact output inventory

The retry7 root contains two directories (`run-1` nested under the root) and exactly17 files. All SHA-256 values below were computed read-only after the invocation:

| Relative path | Bytes | SHA-256 |
| --- | ---: | --- |
| `caller-invocation.json` |3169|`d96848371f76b14dd6ff1ed772184c348ea3c658a9a9b72eeaf7176ce93d0060`|
| `run-1/invocation.json` |17816|`c9ad187bc080390c4593d805c62445a9c995c66f5175f34ff811d6efd9cd188f`|
| `run-1/nonzero-authorization.consumed.json` |1051|`0f8a070027e27aef59f947b40adec056e6733f5f5920dcc59c5e931e67bebc8c`|
| `run-1/nonzero-helper.json` |53|`7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2`|
| `run-1/nonzero-script-start.json` |700|`275d3235c48d25131fd585ca52cfa311f69c46bd280e79bc7dfd661ec0427f4d`|
| `run-1/nonzero.stderr.log` |0|`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`|
| `run-1/nonzero.stdout.log` |0|`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`|
| `run-1/tree-child-started.json` |585|`35e5753bb675564e668ec4fe8a6953888bdceff926d559e12258aa74c8f79de7`|
| `run-1/tree-root-authorization.consumed.json` |1053|`fcdb78ba69900e62a2453a233aaa93bc94c730434ac9695e9db00cf7677adac5`|
| `run-1/tree-root-script-start.json` |702|`1ca35e2a13e7c366b5ddf91d70d858b542005f7172a3ab0015cc61362579c80b`|
| `run-1/tree-root-started.json` |327|`f69ca2db502c9bf9a72202df4350d4442ea1c57ad22b52792c8acda2530dd7bf`|
| `run-1/tree.stderr.log` |0|`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`|
| `run-1/tree.stdout.log` |0|`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`|
| `self-check-handoff.consumed.json` |1602|`16e90ce6ad2da4e915e125e867403bb1afa01faebd2393b7ee7065482bac3233`|
| `supervisor-script-start.json` |1038|`341c2f814ae14fa37a3245c2477c5616f5cf3540d8800c41add8e3c5dbd0aa9f`|
| `supervisor.stderr.log` |0|`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`|
| `supervisor.stdout.log` |0|`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`|

No failure, pending, update, or unconsumed authorization record was present in the inventory. These files are preserved; no retry replay or path change follows.

## Coordinator disposition

Retry7 is consumed and records a self-check PASS. The corrected S implementation has its independent static PASS; the exact retry7 path patch has its final independent static PASS; all authorized Ruff/format/AST and70/6 preservation gates passed before invocation. The active narrow nonnumerical containment issue is accepted as **PASS**. Retry1–6 remain consumed, immutable and non-PASS. Candidate build3 remains unreserved and the candidate remains **NO-GO for serving/publication**. No GIS/numerical candidate build, browser work, M1, TVW-016 or future issue is authorized by this result.
