# Coordinator disposition 94 — bounded correction for stdio release accounting

**Date:** 2026-10-25  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Authority:** User's continuing authorization for as many bounded attempts as needed, with independent review and separate one-use self-check gates.

## Review finding accepted

Accept independent review `docs/milestones/artifacts/Teignmouth-float32-topology/build-3/selfcheck-console-inheritance-code-independent-review.md`, SHA-256 `d46ec3ca18f2465ec5093109b4eb39b4e1f1353c8bfc6bf870cec6226923b34f`, as **FIX REQUIRED**. The only actionable finding is S's new stdio-close loop (current lines 2013–2020): it ignores `CloseHandle`'s false return and suppresses exceptions, so successful launch can continue without confirmed handle release. No actual close failure was reproduced. Review independently inversed the change to accepted S baseline and found no unrelated S edits; W/H/P remain at their pinned hashes.

## Correction authority

Authorize Luna to make one narrowly scoped S-only correction, reusing the accepted console-inheritance plan, to satisfy the review:

- For each owned stdio handle, record exactly one close attempt and distinguish successful BOOL true from false, raised exception or otherwise unconfirmed release. Capture `GetLastError` immediately on a false BOOL. Continue attempting the remaining handles; never retry or double-close.
- If a query or CreateProcess error already exists, preserve it as primary and retain close failures as secondary diagnostics/notes.
- If CreateProcess succeeded but any stdio release is unconfirmed, do not authorize/resume or report success. Route the new failure through the existing created-process ownership/cleanup path so its suspended process is terminated/observed and process/thread handles are closed without an unassigned suspended orphan.
- Preserve every other accepted behavior, exact S-only scope, console check, launch flags, Job and identity chain, deadlines, strict census gates and persistence/cleanup semantics.

Run only the two previously accepted Ruff check/format gates and static source/diff review. Save a correction report. No tests/imports, process probes, wrapper/self-check, retry root, runtime, preflight, evidence mutation, W/H/P edit, GIS/numerical/build/serving/publication/browser work. Submit changed S for a fresh independent Sol review. This disposition authorizes no self-check.

## Preserved status

Retry-1 through retry-4 remain consumed, immutable and non-PASS. Candidate remains **NO-GO and unservable**; build 3 unreserved. Outer exit 1/internal exit 2 and unsaved `957157…` hash remain separate unresolved facts. A fresh-root path plan/review and one-use coordinator gate remain mandatory after code review PASS.
