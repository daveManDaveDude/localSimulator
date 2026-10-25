# Coordinator disposition 1 — diagnostic 1 GO

**Date:** 2026-10-24  
**Issue:** `Teignmouth-float32-topology-representation-1`  
**Decision:** Reserve Luna's initial implementation. This is a GO for implementing the fixed-frame contract, not a candidate/build/browser acceptance.

## Reviewed diagnostic evidence

Diagnostic 1 completed once in **35.977 seconds** with 179 input hashes unchanged. The unmodified global-coordinate mesher reproduced the predecessor collision and recorded three global collision groups and six triangles invalid after Float32 conversion. In the single prescribed local frame `[-140, 0, -95]`, the exact noded/triangulated census and unchanged mesher oracle agree on the full arrangement: **64,765 vertices**, **129,362 triangles**, and **136,656 constraint edges**. The local frame has no collision groups, no raw/Float32-degenerate or winding-changed triangles, no missing constraint edges, and exact vertex/triangle-multiset/constraint-edge equivalence to the mesher oracle.

All **166** decoded Float32 boundary edges reconstruct to the original global perimeter coordinates exactly. Maximum stored local X/Z round-trip error is about **1.91 μm**. The registered-camera CPU/Float32 emulation reports maximum view-space axis error of about **14.03 μm**, below the existing 1 mm tolerance.

## Limits of this GO

The diagnostic constructs X/Z topology only. It does not build candidate heights, a final terrain/road mesh, or any runtime asset. Global and translated GEOS arrangements are separately noded; the evidence does not establish continuous equivalence. Camera probes use a Y=0 plane and sequential Float32 emulation, not actual GPU rendering, real candidate heights, material paths, seam/contact behavior, shadows or browser capture. The optional shader `worldPosition` path requires fresh implementation/material-path review and must not feed topology identity or CPU surface QA through global Float32 vertices.

## Authorized next stage

Authorize Luna's initial Python implementation of the versioned local-frame contract and candidate builder exactly as defined by `spec.md`. Keep the fixed origin, frozen recipe and all inherited limits (including strict candidate-only `<6.5 m` earthwork). Keep `road_surface_topology.py` collision logic intact; run it on the actual stored local Float32 coordinates. Reconstruct global coordinates in Float64 for QA. Preserve exact source-perimeter X/Z/Y, source planes, and one shared frame for all consumers. Do not create product/browser prototype files or serve a candidate until all eight offline acceptance gates pass.

No implementation build is reserved by this decision. After focused tests/static checks and a complete pre-build input freeze, the coordinator may reserve fresh build ordinal 1 once. Any collision, lost constraint, perimeter change, remaining offline gate failure, incompatible runtime path or preservation mismatch is a stop; no tolerance or limit change is implied.

The predecessor continuation remains exhausted, immutable and unservable. No old diagnostic/build/correction budget is transferred.
