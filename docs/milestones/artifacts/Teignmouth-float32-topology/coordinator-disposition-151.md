# Coordinator disposition 151 — one-use retry-7 self-check gate

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User's explicit continuing authorization for needed attempts; D150 preflight PASS; D149 final independent source review PASS.

## Bound state

- Final path handoff: `build-3/retry-7-path-binding-implementation-handoff.md`, SHA-256 `af6d8e923a9d86f2054a5e1174fd3db1e9d2404f55751d700c1bc791e248365b`.
- Final independent actual-byte review: `build-3/retry-7-path-binding-final-independent-review.md`, SHA-256 `655436f6b1009457a62fd26c6ec36798b5a6a2fcf1bdc56495c83f9103dfcb6f`.
- D150 immediate preflight result: `coordinator-disposition-150-preflight-result.md`, SHA-256 `7614c7829e8eb2f1c1127cc7e951a4ae077ed220f39db4d792095f9efa9169a5`; all source/path/alias/ancestor/refusal-target predicates passed. Target parent was absent and no root was created/reserved during preflight.
- Source hashes at preflight: W `842a599fda7d9082b56efb792b10154d3e9096af8ac755f16318777d1495eef8`; S `8f4dbda2346db49a0b9cead30b33a8515879f9955bbec59d64e23386615f5016`; H `f9f48f34198fe54eab800e8d2bc619631c11ce8ed44751a24a2c126e316ed373`; P `aa1b4bffa526ce7351a6558f71b52e231d8b1b6e23d8545dcebc5700c525d96b`.
- Exact reserved namespace for this one use: `C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck-retry-7`, leaf `run-1`.

## One-time authorization

Select/reserve retry7 for **exactly one** invocation of the accepted wrapper from `C:\vibe\localSimulator`:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File pipeline/scripts/invoke_teignmouth_float32_build3.ps1 -Mode self-check
```

No direct S/H invocation and no alternative mode/path. Execute the command once. Any invocation refusal, startup/partial failure, timeout, nonzero or non-PASS consumes retry7; preserve all created bytes and stop, with no replay or alternate root. Record actual outer exit, internal chosen/native/helper results, exact output inventory/hashes and all timeout/cleanup observations. Do not infer success from a partial record.

This does not authorize candidate building, GIS/numerical work, M1, TVW-016, serving/publication or product/AOI/source changes. Even a self-check PASS only returns for coordinator review; build3 remains unreserved and candidate remains NO-GO/unservable until a separate accepted build disposition.

Retries1–6 remain consumed/immutable/non-PASS; counters carry forward. This disposition's one-use authority expires immediately after the single wrapper invocation or any clear pre-invocation refusal. No second invocation is authorized.
