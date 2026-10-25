# Independent Sol review 1 — Float32 topology implementation

Date: 2026-10-24

## Decision

**NO-GO for implementation build ordinal 1.** Coordinator must not reserve or invoke a candidate build until the blockers below are corrected and independently reviewed.

## Scope and verification

Reviewed the new frame adapter, candidate pipeline, build runner, configuration, focused tests, prebuild manifest and evidence plan against the accepted issue specification. Recomputed the byte lengths and SHA-256 values for all 184 files listed by `prebuild-1/input-manifest.json`; every binding matched. No files were edited, no tests were run by the reviewer, no GIS source was loaded, and no candidate build was run.

## Blocking findings

1. **Global Float32 quantization is reintroduced by section QA.** `teignmouth_float32_candidate.py` calls the inherited `target_section_gates`; that path calls `sample_float32_mesh`, which casts reconstructed world X/Z back to global `np.float32`. It therefore checks a potentially collapsed surface rather than the decoded local-Float32 surface. Use the decoded Float64 world sampler for section stations and width offsets, and add a regression covering the known global collision pair.
2. **Failure evidence is delayed until assembly completes.** Candidate buffers are persisted only after overlay, section, road and building evaluation returns. An exception during those gates loses already available geometry and gate results. Persist construction and serialized buffers immediately at their completed stages; persist each completed gate before continuing; on failure, retain typed error details and explicit unavailable gates.
3. **Build safeguards and resource evidence are incomplete.** The runner does not enforce the 180-second execution bound, measure elapsed/peak-memory evidence, or reverify protected inputs after the run. Add an enforced bounded execution path and durable timeout, resource, and post-run preservation reporting before reserving the build.
4. **Source-plane and displacement claims exceed the measurements.** `outsideInfluenceSourcePlanesPreserved` compares only vertex heights, not complete outside triangle/source planes. The reported serialization displacement re-encodes already-decoded coordinates and measures against the wrong baseline. Check outside triangle/source overlay reproduction and compare reconstructed stored coordinates to the original pre-serialization construction coordinates.

## Accepted aspects

The fixed local origin, unchanged Float32 collision guard and candidate-only limit values are coherently represented. No product, public package, default viewer, accepted preview, AOI or browser integration was found. Road reclip/drape, building contact metrics, shared-surface/walk clearance and deterministic confirmation remain false or unevaluated; preserve those gates as blocked.

## Evidence

- Prebuild manifest: `docs/milestones/artifacts/Teignmouth-float32-topology/prebuild-1/input-manifest.json`
- Implementation: `pipeline/torquay_pipeline/road_surface_float32_frame.py`, `pipeline/torquay_pipeline/teignmouth_float32_candidate.py`, `pipeline/scripts/build_teignmouth_float32_candidate.py`
- Candidate output absent and build ordinal 1 unreserved at review time.
