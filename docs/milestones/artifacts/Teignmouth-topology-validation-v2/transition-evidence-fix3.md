# Teignmouth validation transition v2 — Luna fix 3 evidence

Date: 2026-10-23  
Status: submitted for independent Sol review. Transition remains disabled. No
topology trial, solver, candidate publication, runtime integration or browser
work occurred in this correction.

## Correction summary

- `road_surface_validation_v1.py` remains included in the additive extension
  code-hash map. Static validation binds the exact transition policy, config,
  spec, runtime code and limits; it rejects a changed qualification limit.
- Activation requires the actual PASS Sol JSON, an exact coordinator acceptance
  receipt bound to that review, and the matching accepted checkpoint marker.
  `activation.enabled` alone or a digest alone is insufficient. No real Sol
  review/receipt exists for this candidate; the config remains disabled.
- One unshifted monotonic T0 controls preparation/solver at +120 s, every
  post-solver gate through asset assembly/resource/determinism at +125 s, and
  bounded preservation/serialization/aggregate finalization at +135 s. Late or
  incomplete work stays failed/unavailable and cannot be promoted to PASS.
- Preservation now requires actual before == after == expected protected maps.
  Final aggregate commit rechecks the hard cutoff and uses an exclusive
  temporary plus no-overwrite commit.
- The 36 focused tests cover policy tampering, approval/checkpoint tampering,
  immutable v1 hash binding, late clocks, protected-source mutation, incomplete
  gates at both cutoffs, deadline during temporary write, and output collision.

The workspace line-trace deadline interrupts Python validation at its next
workspace line and each validator also checks deadlines inside its loops. A
single in-flight C-extension call cannot be preempted by Python tracing; when it
returns the post-check rejects late work. No late result is committed as a pass.

## Retained road-05 result (performance profile only)

The authoritative read-only profile is
[`retained-road-05-profile-fix3-harness.json`](retained-road-05-profile-fix3-harness.json)
(SHA-256 `615fcf3fff9353703b95f91a9ee7d321794ef2e7ac274d3271a8ff2290fa08a2`).
The preceding protected-map audit is
[`retained-road-05-profile-fix3-audit.json`](retained-road-05-profile-fix3-audit.json)
(SHA-256 `3f5555863a7c9b4f47054936afe79eb6aa645399731e3cb1653222e66dd17965`).
Both use the retained real road-05 Float32 witness
`a6251101e907f4dc1179fd15c07795078b10768386633405e06ed88109b413a8` and do not
invoke the solver. In the profile JSON, `passes=true` means only report
equivalence and preservation passed; `retainedRoad05OfflineGatePasses=false`
means the actual candidate remains a failed offline result.

All 12 gate reports and their identity fields match the retained
`.codex/evidence/teignmouth-topology-study/road-05/offline-aggregate.json`
byte-for-byte, including all 3,613 building records. The raw trial tree before
and after is byte-identical. The retained aggregate SHA-256 is
`a956204c7734ccd75eb50befd7dca2e3819bc003acff5253d9dd88e1712e9352`.

| Retained offline gate | Result |
| --- | --- |
| Input bindings | pass |
| Solver witness | fail: nonconverged at 2,000 iterations; max constraint residual 0.0032190127 m |
| Float32 final validation | fail |
| Topology and topology resource limits | pass |
| Source triangle ownership | pass |
| Earthwork overlay | pass |
| Accepted plane refinement | pass; max deviation 9.5367443e-7 m |
| Composite terrain | fail; maximum positive added gradient 1.003964901 m/m, above the unchanged 1.0 m/m limit |
| Local corridor/longitudinal | pass in the retained report; Teignmouth local max lateral slope 4.9600286%, endpoint span 0.0162803 m, centerline deviation 0.0056685 m, signed-grade change 1.0075951 percentage points |
| Complete building footprints | pass; all 3,613 recalculated, p95 0.0897713 m, maximum 0.8704638 m |
| Road/path reclip | fail before producing groups; exact shared-owner Float32 check at `[-112.91286872324073, -128.0]` has barycentric violation `1.40730204e-5`, exceeding the unchanged `1e-6` limit |
| Walk clearance | fail closed: no reclipped road vertices, so road-clearance coverage is unavailable; displayed-ground clearance itself is 1.7 m |

The road/path failure means the real conditional candidate path could not be
measured: exact road-group assembly, its two independent validations, the
candidate asset resource report, and exact deterministic asset hashes are
unavailable. No substitute is reported as that gate.

### Performance-only assembly harness

To measure the conditional code path without claiming acceptance, the profile
also assembles and validates two byte packages in memory using the retained real
release, building inputs, road inputs, patch mesh and Float32 witness. It selects
the 1,058 real vehicular source faces owned by cells in the patch (0 cycleway,
0 path) and maps each face to the first replacement triangle in its coarse cell
solely to provide structurally valid arrays for timing. This is **not** the exact
road reclip: XZ coverage/drape/width is not validated by this harness. A deep
copy of the failed aggregate has passing flags only inside this isolated
performance fixture so the normal asset assembler can be timed; the real
aggregate and all thresholds remain unchanged. Every generated byte string is
discarded in memory and none is written to the repository or candidate path.

Measured fixture path:

| Operation | Seconds |
| --- | ---: |
| Two independent assemblies plus their internal validations | 0.139580 |
| Two wrapper-level validations, resource check and deterministic hash compare | 0.060014 |
| Total synthetic conditional path | 0.199593 |

Both fixture assemblies had identical per-file hashes and structural
validations passed. The fixture resource report was 1,110,758 runtime bytes,
1,103,508 resident geometry bytes, 3,571,576 peak construction bytes, 56,534
replacement triangles, 30,073 vertices and two draw calls; these are harness
measurements, not candidate resource acceptance. Exact hashes and full detail
are in the profile JSON under `performanceOnlyAssemblyHarness`.

## Timing and qualification

The retained road-05 total was 128.2744305 s, exceeding its original 120 s
window. Its recorded preparation, solver and legacy validation were
16.0825479 s, 26.0487822 s and 80.517233 s, leaving a 5.6258674 s
finalization/other residual.

The final profile measures v2 validation plus context at 62.6854270 s. It also
measures static preflight (0.017191 s), inventory/prior-map validation
(0.831863 s), one code-hash pass (0.013686 s), synthetic approval-artifact
validation (0.033845 s), and finalization snapshot/serialization/bounded write
(0.581163 s total). Its projection repeats code-hash and synthetic approval
checks conservatively, uses the larger retained finalization residual, and
includes a 0.5 s serialization/write margin:

`16.0825479 + 26.0487822 + 62.6854270 + 1.0254919 + 5.6258674 + 0.5 = 111.9681164 s`.

The exact road-group conditional path is unavailable, so the 125 s qualification
projection is **incomplete**. The profile leaves 13.0318836 s unmeasured,
records `projectedEndToEndSeconds=null`, `qualificationMarginSeconds=null`, and
`qualifiesForNextTrialTiming=false`. Adding the 0.1995934 s synthetic harness
would yield 112.1677098 s for that fixture only; it does not establish a
conservative bound for exact road clipping. No timing qualification is claimed.

## Preservation and identities

At the final profile run, protected-map before and after SHA-256 were both
`e2ce6dfd26b69fc60db55fd1b0afb879fd4a970359aab588a709e6584e3417e4`; transition
input validation passed. The run-time checkpoint SHA-256 was
`83c734c06760708b6b5ea737f861a234b3b46833aeec55c2a3abe609c0532814`. This is
the checkpoint snapshot before this handback's administrative counter update;
the implementation-start baseline remains pinned as
`5b0cfb793f3780b9ee2af6087d643a22cde32b43c9b7442ed9940306b09a17a6`.

The transition input validation recorded the 2,411-byte consumed-trial
inventory SHA-256 `9e9c9d083014dd2649fc2b4d284a235423358466b6e91b3d07959c2369f5d8d6`,
the current Road-surface-treatment evidence-tree digest
`4413d4fc79adcf846d578e51fa2d65ee46b674721b1e1e61759fae1a0214f94a`, and the
legacy tree reconstructed by excluding only that inventory file
(`a83f7f30ebd3fba437364a570ee3349e72bec7b62e5bc9304708b1d50512c688`).

The pinned current release ID is
`616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a`. Source
manifest SHA-256 is
`e2a5237d99fd8b0b0dd0174430ba18b58f2d778f498275c609c24bed5c3ccf8c`. Accepted
preview hashes are `heightfield.f32`
`037a74320557088135e0885386c24fdcdea6171469db1d6329c3e82997f5c1e9`,
`manifest.json`
`9a3cb6c08fb57a19f94e1215ac526b1baf28634d38be1ffc7d4ed61f2de7c6f7`, and
`qa.json` `43d7058a339416d308be09292598949d3d97f4b764a147ccc2d5fb771d434f20`.
No source/release/accepted-preview bytes were changed. The reserved candidate
directory remains absent.

The audit profile was captured while the handback text carried transition-spec
SHA-256 `a4b3a2ca69f56e76095bf317678b420d7de7067a512d8bd2fe6a22d74124d14f`.
The later edit to the spec Evidence paragraph is documentation-only and the
current pin/hash was refreshed to
`82e636a66c649908880e8b4be6c314419c34c1810d8e653c579af86b759b8c0f`; timing
policy, source inputs, limits and executable code did not change after the
profile. The final config SHA-256 is
`e74c4426d8d7ddea958082df9d2a6071ffc52d5d2fe6fa9806e057cc1c28a4f6`.

## Commands and outcome

From `pipeline/`:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_road_surface_validation_transition_v2.py tests/test_road_surface_validation_v2.py -q
.venv/Scripts/ruff.exe check scripts/profile_teignmouth_validation_v2.py scripts/run_teignmouth_topology_validation_v2.py torquay_pipeline/road_surface_validation_transition_v2.py tests/test_road_surface_validation_transition_v2.py
.venv/Scripts/ruff.exe format --check scripts/profile_teignmouth_validation_v2.py scripts/run_teignmouth_topology_validation_v2.py torquay_pipeline/road_surface_validation_transition_v2.py tests/test_road_surface_validation_transition_v2.py
.venv/Scripts/python.exe scripts/profile_teignmouth_validation_v2.py
```

The focused suite passed **36/36**, Ruff check passed, and Ruff format check
passed. The read-only profile command exited 2 by design because qualification
is false; it wrote the fresh profile with exclusive-create semantics. A final
`git diff --check` is recorded in the implementation handback. No trial or
candidate output was created, and activation remains disabled pending
independent review.
