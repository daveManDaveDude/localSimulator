# Coordinator disposition 78 — retry-3 result and bounded diagnosis

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** Disposition 77 and the user's authorization for as many attempts as needed to pass the supervisor self-check.

## One authorized result — consumed and non-PASS

The single W-driven retry-3 invocation authorized by disposition 77 ran once:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File pipeline/scripts/invoke_teignmouth_float32_build3.ps1 -Mode self-check
```

The outer `pwsh` command returned exit code 1 with no console output. The retained caller/run records report `supervisorScriptExitCode=2`, `nativeLauncherExitCode=2`, and `BLOCKED_SELFCHECK`. Preserve this exact observed difference; no inference about the outer exit-code discrepancy is made yet.

The wrapper completed launcher assignment/resume, authenticated the supervisor, consumed the handoff and authorized the nonzero helper. H's marker is `EXPECTED_NONZERO_HELPER` with exit code 7. The run record confirms both launcher and interpreter exited with code 7, with no timeout. The first complete post-wait inner Job snapshot reported accounting **1 before and after** a complete one-PID census, PID `20712`, not one of the authenticated normal launcher/interpreter pair (`27240`, `37428`); S correctly rejected it as unexpected. Exception-checkpoint evidence later recorded complete empty membership and accounting zero, and finally cleanup confirmed termination. That later cleanup cannot retroactively satisfy the normal-stage gate. The deliberate tree probe was not reached. `candidateBuilt=false`, `candidateEligibleForServing=false`.

Retry-3 is now **consumed, immutable and non-PASS**. Its exact 11 files and hashes:

| Evidence file | SHA-256 |
| --- | --- |
| `caller-invocation.json` | `f1bf3a880a821626daef625f60459d037a8aa9509246e401a06f9440cb8134d6` |
| `self-check-handoff.consumed.json` | `dd82b4bd6cdfafa76fd5be2505cf438125f9deb70d37f73dbaf03a7f719d93b6` |
| `supervisor-script-start.json` | `bf0f5eed47455f27a037dea7fbeca068bf4ac2d9a72598e70c21c90b7c835a90` |
| `supervisor.stderr.log` | `18d4873d35189bf11f26f2df45a60574330fde3c27bf02371542b37a4b46fea8` |
| `supervisor.stdout.log` (empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run-1/invocation.json` | `dcf98d8471df615acbaa74d3eece7f8a774e86cac22b0864931e556f2ae627e5` |
| `run-1/nonzero-authorization.consumed.json` | `0b64cd4ffc826e052423ab501f55da267675ee8f5c345c4c7613b6076b283d3a` |
| `run-1/nonzero-helper.json` | `7aebecbb904d4a9d878efb2032ba9375550098417e7fa4213cb495d39358fbe2` |
| `run-1/nonzero-script-start.json` | `0da552f3943a321f31e5bceac24fe74471e6a1c75367a852430f2e2d3ae0ffa3` |
| `run-1/nonzero.stderr.log` (empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run-1/nonzero.stdout.log` (empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

No retry-3 evidence was moved, rewritten or deleted. Retry-1, retry-2 and original evidence also remain untouched. No candidate output was created.

## Next authorized action: read-only diagnosis

Request Sol to diagnose how the unexpected inner Job member could be present in the first complete post-wait census and absent in the exception checkpoint, using only the captured retry-3 evidence and static source/document review. Identify the exact launch/accounting path and whether the behavior is a real descendant, transient retained object, or another class only where evidence supports that distinction; do not guess identity from PID or final zero. Recommend a narrow code/evidence correction under the accepted reaping plan, without relaxing complete census, authenticated membership, exit, containment, original deadline or non-PASS gates. No tests/imports/probes/process inspection or operational action during diagnosis. Coordinator must accept a concrete next plan before implementation.

Do not reuse retry-3 or invoke the wrapper again. No runtime preflight/identity collection, manifests, GIS/numerical/build, serving/publication or browser action. Candidate remains **NO-GO and unservable**; build 3 unreserved. Preserve historical counters and the unsaved/untraceable `957157…` S digest limitation. No commit, push or merge.
