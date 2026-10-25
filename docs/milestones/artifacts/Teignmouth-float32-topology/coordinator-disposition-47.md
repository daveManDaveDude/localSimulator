# Coordinator disposition 47 — submit Luna cycle 2 for independent Sol review

Date: 2026-10-25

**Decision: Luna cycle 2 is complete. Submit exact W/S/P for independent Sol review only. No runtime, self-check, manifest preparation, diagnostic, GIS, candidate build, numerical or browser action is authorized before independent review and later gates.**

Implementation was completed under dispositions 40, 45 and 46 against the accepted correction-3 plan plus finite-profile addendum. Exact hashes independently rechecked by the coordinator:

- W pipeline/scripts/invoke_teignmouth_float32_build3.ps1: b3623911fcece373706af237e294c90411913f7715102eae6c2cd1d25a0fcbfc
- S pipeline/scripts/run_teignmouth_float32_build3.py: 7883669c05ec3ce165db6d0b0ff8d4832df931479bf10c63c1f0f049d7965d33
- P pipeline/scripts/teignmouth_build3_runtime_preflight.py: 2ec7a76b448f2235133fa96a2819f4b65058fca498081857578af51ad390de91
- H pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py unchanged: 9fc73a8ed7aca3b4e223d3f23a7bd676f48011aa0abe98eb864f9e98a5191d20

Luna reports final static gates PASS: Ruff check; Ruff format check (3 Python files already formatted); PowerShell AST parse without wrapper invocation; embedded C# compile-only without method invocation. Earlier Ruff/style findings, including a duplicate conditional, were fixed before final static checks. No tests, imports, project code, wrapper or operational scripts, runtime mode, self-check, GIS, numerical work, candidate build or browser check were run.

Protected hashes verified unchanged: candidate module a6ecafc012efb425b04d36826f744db925cf47f07fc4b5c2498f2884b77fa61b; topology helper 88196f11ec0c46a31ddff9c342a89dec9b808407cd8018b968eecfdb7eed4880; builder 5c72a2bc7f51fee50c976f3e4dc28c38c24427649b8dcc9d76ecbd391cd24e3b; focused test 34415a55d81ecaa754e189ccf63864d84f2e699918598d13592414b012d3f4e8; fixture 4add13e5201edb5cd9115175eea49a5ae980d55c99f9294a347226cf08e15fea; candidate configuration e0e264a40f6b9dee334cb90b0ff76d366159bf49a0ca8bcdf3e4e65328f58228.

The finite profile's ability to finish within 30 seconds is unmeasured. It must fail closed on expiry; no deadline increase is proposed or inferred. The operational files remain untracked in Git as before this series, so no index diff is claimed; independent review must inspect actual current contents against review 5, the diagnosis, plan and profile addendum.

Cycle 2 is consumed and submitted for review; cycles used 2/4, reserved 0. The reviewer must assess RECORD path/tree ownership, complete prelaunch profile coverage and fail-closed semantics, W/S/P ordering and postchecks, timing/error propagation, and all retained process/identity/build gates. If FIX REQUIRED, one more bounded Sol diagnosis precedes Luna cycle 3. Candidate budgets remain diagnostics 2/2, candidate corrections 4/4 Luna and 1/1 Sol, builds 2/6 used with none reserved, and confirmation 0/1 ineligible. Candidate remains NO-GO and unservable; build 3 remains unreserved.
