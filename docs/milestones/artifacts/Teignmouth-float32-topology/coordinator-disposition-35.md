# Coordinator disposition 35 — accept correction plan and release one Luna submission

Date: 2026-10-24

**Decision: The Sol remediation plan satisfies disposition 34's exact four-file and no-execution boundaries. Release the single already-authorized Luna operational correction 2/2 for implementation. No candidate budget changes.**

Accepted plan: `build-3/supervisor-correction-2-plan.md`, SHA-256 `b7e550295a7944d06bd830a6a971ae2a3826bc0f7fb6f673d3b98e029490af92`.

Authorize Luna to change only the four existing files named in disposition 34. Address the plan's review-16 fixes, including PowerShell automatic-variable naming, coherent parent handoff/start-record paths, exclusive caller-record ownership, safe termination of an unassigned suspended launcher, single-owner cleanup, deadline propagation/recomputation, and honest collection-versus-verification behavior using existing modes and records.

Static checks after implementation remain exactly those in disposition 34: Ruff check/format for the three Python files; PowerShell AST parse without invocation; and interop compile-only without method invocation if available. Then submit exact hashes/results for independent Sol review. A FIX REQUIRED result ends this authorization; no further automatic correction is allowed.

No script/wrapper execution, runtime collection/verification, self-check, diagnostic, GIS load, candidate build or browser action is authorized. Build 3 remains unreserved and candidate remains NO-GO. All candidate counters and prior failed submissions remain unchanged.
