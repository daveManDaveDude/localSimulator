# Independent Sol review 2 — correction 1

Date: 2026-10-24

## Decision

**NO-GO for implementation build ordinal 1.** Correction 1 addresses the first review findings in substantial part, but has two blocking coordinate-order defects. Do not reserve or run the candidate build.

## Scope and verification

Recomputed the byte lengths and SHA-256 values for all 188 files in `correction-1/input-manifest.json`; every binding matched. Candidate output is absent. No file was edited, and the reviewer ran no tests, diagnostic, source load, or candidate build.

## Blocking findings

1. **Serialized positions are in the wrong axis order.** In `_serialize_candidate`, `np.column_stack((world_xz, candidate_y_f32))` produces `[X, Z, Y]`, but `Float32LocalFrame.store_xyz` expects `[X, Y, Z]`. This swaps height and Z, and normally fails the subsequent local X/Z byte invariant. Construct positions explicitly in XYZ order and add an assembly-level regression that checks stored X/Y/Z and decoded world X/Y/Z.
2. **The displacement baseline repeats the same axis-order mistake.** The baseline `[constructionX, constructionZ, unroundedY]` is subtracted from decoded `[X, Y, Z]`, so vertical and Z displacement values are invalid. Use `[constructionX, unroundedY, constructionZ]` consistently and test known horizontal and vertical quantization errors.

## Other findings

Section QA now uses decoded Float64 world positions from stored local Float32; the known collision regression exists. Chart, construction, serialized buffers and completed gates are persisted incrementally. The runner uses a supervised 180-second worker, has no CLI bypass, verifies inputs before/after, reports elapsed/memory and archives failed partial output. Outside-source-plane checking uses a clipped final-mesh/source-triangle overlay. Fixed origin, limits and provenance remain unchanged; incomplete contact/shared-surface/confirmation gates remain false; no browser/product integration was found.

The Windows memory API/watchdog have only been compiled/static-checked, not exercised by a candidate run. Luna disclosed that the first pytest collection from repository root failed, followed by 12 passing tests from `pipeline/`; those tests did not cover the actual assembly order defect.

## Evidence

- `docs/milestones/artifacts/Teignmouth-float32-topology/correction-1/input-manifest.json`
- `docs/milestones/artifacts/Teignmouth-float32-topology/correction-1/evidence-plan.md`
- Candidate output absent; build 1 remains unreserved.
