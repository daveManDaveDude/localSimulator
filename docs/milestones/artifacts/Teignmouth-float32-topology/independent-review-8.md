# Independent Sol review 8 — diagnostic 2 harness

Date: 2026-10-24. Reviewer: `/root/sol_review_face_diag`, independent non-implementing Sol session.

## Decision

**FIX REQUIRED. Do not freeze inputs or invoke this version. Candidate serving remains NO-GO regardless of harness status.**

The review compared `pipeline/scripts/diagnose_teignmouth_overlay_face.py` with `diagnostic-2/plan.md`, `independent-review-7.md` and root `AGENTS.md`. All line references below refer to the reviewed diagnostic script.

## Concrete findings

1. **Runner cannot start successfully — lines 1217, 1249, 1296, 1312.** `_verify_inputs` returns three values (line 161), but line 1217 unpacks two. After correcting that, `before` and `after` still receive tuples rather than preservation dictionaries, and `after["passes"]` fails. Unpack all three consistently and enforce preservation success before leaf creation and worker launch.

2. **Clip reconstruction cannot execute — lines 472, 479, 749, 839.** The caller passes the `_line_point_tangent` function, while `_target_geometry` dereferences `helper._line_point_tangent`. Pass the module or call the supplied function directly. The intended stations, source-break inclusion, buffer default and difference ordering otherwise match production.

3. **Frozen integrity is incomplete — lines 109–161, 755–779, 816–833, 880–892.** Verification merely returns hash failures; the parent does not reject them. Installed Python/NumPy/Shapely/GEOS identities are reported but never compared with frozen identities. Required release manifest/inventory/readiness bindings and their build-2 identities are not enforced. Binding build-2's manifest alone does not verify its referenced protected inputs. Require the agreed protected-input closure, environment identities and exact release metadata before numerical work. Also compare the manifest's own hash between pre/post verification; currently each verification accepts whichever manifest is present.

4. **Zero-area contacts disappear from the extrema report — lines 386–390, 936–939, 1011–1018.** `_plane_witnesses` contains contact reporting, but receives only positive-area fragments. Pass every production result and separately process polygon vertices and zero-area contacts, including contacts inside mixed collections.

5. **Invalid/nonfinite overlay results do not enforce the required stop — lines 338–346, 921–960, 975–1007.** `_geometry_record` records validity without rejecting invalid geometry. There are no explicit validity/finite checks on reconstructed influence/outside clips, source intersections, alternative ordering or aggregate differences. A result can therefore reach `COMPLETE_DIAGNOSTIC_OBSERVATION` despite invalid intermediate geometry. Validate these results and stop inconclusively with durable evidence.

6. **Source-partition "excess" is misleading — lines 983–990, 1046–1050.** `source_union_in_face.difference(face_clip)` necessarily includes the ordinary face area inside the influence region. It is not excess of the source partition within the expected clip. Persist the union of original queried source triangles and compute the independently associated clip/union comparisons explicitly; label any full-face remainder accurately.

7. **Error handling can erase the primary result and process evidence — lines 1296–1297, 1312–1335, 1348–1373.** A post-verification/reporting exception enters the broad handler and overwrites `report.json` with a new error, dropping the worker result, actual exit, timeout state, peak measurement and before-preservation evidence. Preserve the existing primary report and append runner/preservation errors. Ensure timeout status supersedes a partial worker status.

8. **Deadline and outer-exit evidence need a concrete supervision contract — lines 1251–1291, 1319–1322.** The child is killed at approximately 112 seconds from runner start, but pre/post hashing and cleanup have no enforced outer 120-second deadline. Outer exit remains a placeholder. Specify the external supervisor and its durable exit capture before execution; ensure its timeout cannot leave the numerical worker running.

## Scope observations and freeze disposition

The one-face buffer reads and local source-cell enumeration are bounded; triangle IDs, vertex order and source-node heights match the inspected production construction. Fragment JSONL persistence, inclusive area filtering, union/sum measurements and alternative operation ordering are substantially present. No direct candidate, product or ledger mutation calls were found; writes target the diagnostic evidence leaf.

Inputs are safe to freeze only after these changes receive another independent static review and the coordinator prepares the complete manifest and unique reservation. At review time, `diagnostic-2/` contained only the plan; no frozen manifest or reservation snapshot was present. This review authorizes no execution or correction attempt and changes no budget.

## Review boundary

The assessment was read-only. The harness, imports, numerical work, tests and candidate builds were not executed. Existing code, documents and saved-artifact presence were inspected through read-only file commands. No code, source, product, candidate, ledger or test files were edited. This document is the subsequent authorized persistence of the completed assessment; its SHA-256 is calculated for handback without repeating the review or executing the harness.
