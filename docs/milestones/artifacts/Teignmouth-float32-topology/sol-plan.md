# Sol plan: bounded Float32 representation follow-on

Issue: `Teignmouth-float32-topology-representation-1`. Status: planning submission, 24 October 2026. Planner: `/root/beamng_corridor_plan`, Sol 6.1 medium. No implementation, tests, numerical diagnostics, builds, profiles or browser runs performed.

The user's “Continue” follows an explicit proposal for a separately bounded Float32 representation approach. The new [specification](spec.md) keeps the previous continuation exhausted and immutable. The [proposed ledger](attempt-ledger.json) starts at zero; planning does not reserve a diagnostic/build or activate implementation.

## Findings from actual code and prior evidence

1. `pipeline/torquay_pipeline/road_surface_topology.py:529–574` keys actual construction vertices with `_float32_bytes`, and rejects distinct exact coordinates sharing a key. Build 6 fails there, before a final mesh returns. This guard must remain unchanged.
2. `teignmouth_corridor_continuation.py:443–446` expects global coordinates and casts the returned topology to global Float32. Simply adding an origin later in the renderer cannot fix a collision that already happened during meshing, and recreating global Float32 buffers would reproduce the underlying loss.
3. The known X coordinates differ by approximately 5.67 micrometres. Around global magnitude164 the Float32 step is approximately15.26 micrometres; around local magnitude24 it is approximately1.91 micrometres. One fixed translation may help the reported pair, but evidence says nothing about all remaining pairs. No claim of a proven fix is warranted.
4. Installed `node_modules/three/src/renderers/shaders/ShaderChunk/project_vertex.glsl.js` uses `modelViewMatrix * mvPosition` directly. `worldpos_vertex.glsl.js` separately forms `modelMatrix * worldPosition` for enabled paths. `WebGLRenderer.js` composes the model-view matrix on the CPU. Local geometry must stay local through upload, with every enabled coordinate path audited; a global Float32 reconstruction is unsafe.
5. `affine_surface_overlay_extrema` consumes mesh X/Z as Float64, so a separately reconstructed world-space QA mesh is conceptually compatible. Its use with a new frame is not yet tested. The new frame adapter must never send reconstructed global coordinates back through the old global-Float32 key path.
6. The bound 21,336-sample diagnostic maximum6.397848390875038 m remains sampled-field evidence only. It neither proves the <6.5m final overlay gate nor any gradient, topology, building/road/walk or browser gate. The predecessor exception also discarded intermediate reports; durable stage evidence is a necessary new-run requirement.

## Execution sequence after coordinator acceptance

1. **Freeze inputs and roles.** Bind the active new spec/ledger, inherited field/config, limit decision, predecessor review/build6/chart buffers and diagnostic. Hash old issue ledgers/evidence without editing them. Record exact repository virtual environment and GIS-free imports. Use new files and fresh paths only.
2. **One minimal diagnostic.** Reserve diagnostic1 ≤120s. Inspect all construction vertices in the same constrained arrangement using only fixed origin `[-140,0,-95]`. Record global collision witnesses versus local stored-key results, serialized round-trip/error, constraints and registered-camera transform analysis. Enumerate all pairs, not just the known witness. Do not grade a full runtime candidate or sweep origins. If local collisions or contract contradictions remain, stop and ask for a scope decision; do not automatically tile or weaken the guard.
3. **Luna implementation if diagnostic permits.** Build the new local frame adapter/schema, full candidate assembly and staged validation. Reuse only compatible pure predecessor functions. Preserve the original road field, width, source coordinates and all current limits. Produce actual local buffers and world-Float64 reconstruction metadata. Keep old modules and product entry untouched.
4. **Offline acceptance first.** Run actual local-Float32 topology and exact perimeter/source-plane checks; final world-space source overlay/earthwork and gradients; actual sections; real influence-wide road/off-ground ownership and road reclip; complete building footprints/global controls; shared sampler/walk/frame tests. Failures preserve buffers and stage reports and block runtime. Numeric success of an earlier stage cannot substitute for missing later gates.
5. **Independent generation.** Only a fully passing candidate gets the reserved independent confirmation build. Compare ordered bytes/hashes from separately reconstructed outputs; copying or reserializing one witness is not independent generation.
6. **Isolated browser proof.** After all offline gates pass, use one common prototype frame for source and candidate, exact registered cameras and an explicitly frozen overhead view. Inspect screenshots and seam/contact views, camera/runtime/network evidence and fallbacks. Run applicable synthetic/historical/default/preview/share regressions with fresh output destinations. No source assets enter `public/` or product builds.
7. **Separate Sol review.** Reviewer checks actual diff, frame contract, raw witnesses, preservation, completed gates, screenshot content and counters. Missing mandatory checks prevent acceptance. If the planner implements a later Sol correction, a different Sol reviewer is required.

## Critical contract choices

Use one exact integer origin at the existing rectangle centre. Y stays unchanged. The stored Float32 local vertices are the candidate's identity; world reconstruction uses Float64 addition for QA and CPU sampling. New versioned metadata declares this coordinate convention. Preserve exact original global perimeter positions and Float32 heights. Source metadata stays immutable; display quantization is measured and must satisfy existing tolerances, not be disguised as new source coordinates.

Render base/patch/contact-dependent layers within one prototype display frame and identical transform chain. Verify that GPU uniform precision does not reintroduce cracks/contact errors; do not promise global or screen-space Float32 uniqueness at arbitrary views. A failure of this simple frame stops for another decision rather than authorizing custom high/low shaders or multiple patches.

## Budget recommendation

Fresh initial Luna submission + at most four independently reviewed Luna corrections; then at most one Sol correction for a specific remaining actionable finding. Two cause-specific diagnostics ≤120s; six implementation builds ≤180s; one final confirmation build ≤180s for a passing candidate. No sweep, automatic frame variations, arbitrary memory cap or old guardian. Stop sooner for contradictory contracts, unchanged repeated failure, preservation risk or absence of a concrete fix. New ledger is proposed/unreserved; predecessor budgets remain exhausted.

## Planning handback

Created only this plan, the new specification and proposed fresh ledger under `Teignmouth-float32-topology/`. No checkpoint, prior ledger, source code, package, data, test or browser state was changed. The next coordinator action is accept/revise the bounded contract and reserve diagnostic1; no implementation/build is authorized by this planning submission alone.
