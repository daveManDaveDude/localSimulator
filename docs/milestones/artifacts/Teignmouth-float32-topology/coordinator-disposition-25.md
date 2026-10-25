# Coordinator disposition 25 — submit dispatch code for independent Sol review

Date: 2026-10-24

**Decision: Luna's three build-3 operational scripts are submitted for independent Sol code review. The conditional 10-second nonnumerical self-check is not yet run. Runtime preflight and candidate build remain unauthorized. Candidate remains NO-GO.**

Submitted files and SHA-256:
- pipeline/scripts/run_teignmouth_float32_build3.py: 6755594b4335dd4de7f2208904a00d61e95772e81ae645de148d3e6e69de39b4
- pipeline/scripts/teignmouth_build3_runtime_preflight.py: ab99f92e796ec699c81edac1067269daf210a638b5cbd64264a8001fa741c431
- pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py: a9df90e3b680e4fc249171f5b63d92546f21532cd2d0577b265afe8b4603f7f3

Luna reports Ruff check passed and three files formatted. No self-check, runtime preflight, candidate build, diagnostic, browser check or numerical data load was run.

Review the fixed Windows launch and Job lifecycle; fail-closed assignment; one-shot paths; absolute 180-second clock and 150-second numerical cutoff; all wait/termination/active-process accounting; output archival safety; actual exits; identity and external runtime validation; self-check mode isolation from the candidate builder/GIS; standalone preflight authorization; and absence of arbitrary command/parameter inputs. Check deadline coverage from supervisor entry and caller-observed process exit. Verify no candidate/build/diagnostic counters changed.

Only after PASS may the previously authorized one-shot 10-second nonnumerical supervisor self-check run. Runtime-preflight-only mode remains unauthorized until a later disposition. Build 3 stays unreserved pending runtime closure, final protected-input manifest, independent manifest/dispatch review and another coordinator disposition.

## Counters

- Diagnostics: 2/2 used.
- Luna correction cycles: 4/4 used; Sol correction: 1/1 used.
- Candidate implementation builds: 2/6 used; none reserved.
- Confirmation build: 0/1; ineligible.
- Candidate serving/runtime output: ineligible.
