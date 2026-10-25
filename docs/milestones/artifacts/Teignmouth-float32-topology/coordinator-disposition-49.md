# Coordinator disposition 49 — accept archive refusal and release Luna cycle 3

Date: 2026-10-25

**Decision: GO for Luna cycle 3 within the existing finite trusted profile and four-cycle allowance.** Reconcile the Sol diagnosis and make its narrow archive-refusal amendment explicit.

Diagnosis: build-3/supervisor-correction-3-diagnosis-2.md, SHA-256 a718dfae49b9915d66ff2c5e0d49bfbc32f5ac14722ae80d6a37571352370b05. It gives a concrete bounded correction for all seven review-6 findings. The inventory ownership fix from cycle 2 is accepted by the reviewer; preserve it.

## Profile amendment

Active Python zip/archive search/import sources are unsupported by the finite profile and must fail closed before process launch or at the earliest actual-state check. This includes PYTHONPATH archives and archive-plus-subpath forms, a present optional stdlib zip, and any observed archive-backed import/member path. The known optional stdlib zip path may be positively recorded absent. Passive archive files in package/data trees remain ordinary inventoried data unless code attempts to use them as executable/import sources. No member-manifest representation, unpacking, file deletion, environment sanitization or command change is authorized. This conservatively narrows the supported finite profile; the diagnosis found no evidence that the current candidate requires archive imports. If a required package/source actually depends on one, stop for a new profile decision.

## Cycle-3 implementation

Reserve Luna cycle 3 (cycles used 2/4, cycle 3 reserved 1) to change only W/S/P, addressing the seven exact findings: tagged customization alternatives; case-distinct candidate/reference collisions; refusal of relevant native .local/.manifest/.config redirection; consistent pinned .pth handling with leading whitespace refused; single duplicate-detecting pyvenv policy parser; archive refusal integrated through P's actual/loaded census; and truthful shared W scan counters/progress.

Preserve exact commands/environment, roots/categories, existing records/schema IDs/modes/dependencies, one-use/process/identity/Job/cleanup gates, the 30-second original standalone deadline, 10-second self-check and 180/150-second build limits. Unknown or unsupported configurations, incomplete observation or deadline expiry remain non-PASS. Do not claim the profile fits 30 seconds; runtime fit remains unmeasured. H, tests, candidate code/config, manifests during this implementation, source/GIS/product bytes and historical evidence remain unchanged.

After implementation, run only the static gates authorized in disposition 40 and submit exact hashes for independent Sol review. No self-check, manifest preparation, runtime collection/verification, diagnostic, GIS, numerical work, candidate build or browser action is authorized at this stage. If cycle 3 review is FIX REQUIRED, follow the one remaining Luna cycle and the existing post-four-cycle Sol rule; no attempt reset occurs.

Candidate counters remain diagnostics 2/2, candidate Luna corrections 4/4, candidate Sol correction 1/1, candidate builds 2/6 used with none reserved, confirmation 0/1 ineligible. Candidate stays NO-GO and unservable; build 3 stays unreserved.
