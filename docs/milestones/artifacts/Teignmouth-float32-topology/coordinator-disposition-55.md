# Coordinator disposition 55 — correct the self-check entrypoint

Date: 2026-10-25

Disposition 54's listed direct Python command was rejected before the authorized self-check because it bypassed the required PowerShell wrapper. Observed command result: exit code 2, `FileNotFoundError: fixed path component missing: C:\vibe\localSimulator\.codex\build3-supervisor-selfcheck`. Static call-order inspection confirms S requires a one-use parent handoff created by W. The rejected direct invocation did not create `.codex/build3-supervisor-selfcheck`, a caller record, handoff, supervisor-start marker, run-1 leaf, self-check child/descendant, build-3 invocation, or candidate output. It did not enter the contained self-check body or GIS/numerical/build code. Therefore the authorized self-check one-shot evidence slot remains unused; this is not a successful self-check and no gate is claimed passed.

**Decision: GO for the first actual authorized one-shot self-check via the reviewed W wrapper only**, retaining the same exact mode and 10-second total deadline from disposition 54. Use:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File pipeline/scripts/invoke_teignmouth_float32_build3.ps1 -Mode self-check
```

The execution-policy override is process-scoped and permits invoking the local script without changing the user's persistent policy. W creates/authenticates the handoff, assigns the launcher to the outer Job before resume, and S then runs only its fixed nonnumerical helper under its inner Job. No retry is authorized once that wrapper-driven one-shot invocation creates its records or starts the contained self-check. Preserve all outputs, errors and exit/termination evidence.

No source change, runtime collection/verification, manifest preparation, candidate reservation/build, GIS/numerical work, serving, browser action or product change is authorized by this command correction. The review-8 PASS and disposition-40 serial-continuation authorization remain in effect. Candidate remains NO-GO/unservable; build 3 remains unreserved; candidate counters are unchanged. Runtime fit within 30 seconds remains unmeasured.
