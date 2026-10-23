"""Read-only exact-equivalence benchmark for the versioned Teignmouth validator."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from torquay_pipeline import road_surface_patch as patch  # noqa: E402
from torquay_pipeline.road_surface_validation_v1 import (  # noqa: E402
    VALIDATOR_VERSION,
    ValidationContextV1,
    validate_offline_candidate_v1,
)

TRIAL_ID = "road-05"
TRIAL_DIR = ROOT / ".codex/evidence/teignmouth-topology-study" / TRIAL_ID
BASE_CONFIG = ROOT / "config/road-surface-teignmouth-candidate.json"
RECORDED_TRIAL_SECONDS = 128.2744305
LEGACY_PROFILED_VALIDATION_SECONDS = 80.517233


def _tree_hashes(path: Path) -> list[tuple[str, str, int]]:
    return [
        (
            child.relative_to(path).as_posix(),
            hashlib.sha256(child.read_bytes()).hexdigest(),
            child.stat().st_size,
        )
        for child in sorted(path.rglob("*"))
        if child.is_file()
    ]


def _same_report(first: Any, second: Any) -> bool:
    return patch.serialize_offline_report({"report": first}) == patch.serialize_offline_report(
        {"report": second}
    )


def run() -> dict[str, Any]:
    before = _tree_hashes(TRIAL_DIR)
    attempt = json.loads((TRIAL_DIR / "attempt.json").read_text(encoding="utf-8"))
    topology = json.loads((TRIAL_DIR / "topology.json").read_text(encoding="utf-8"))
    solver = json.loads((TRIAL_DIR / "solver-phase.json").read_text(encoding="utf-8"))
    old_aggregate = json.loads((TRIAL_DIR / "offline-aggregate.json").read_text(encoding="utf-8"))
    constraints_record = json.loads((TRIAL_DIR / "constraints.json").read_text(encoding="utf-8"))

    for relative in (
        "pipeline/torquay_pipeline/road_surface.py",
        "pipeline/torquay_pipeline/road_surface_patch.py",
        "pipeline/torquay_pipeline/road_surface_topology.py",
        "pipeline/torquay_pipeline/road_surface_study.py",
    ):
        current = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if attempt.get("codeHashes", {}).get(relative) != current:
            raise RuntimeError(f"retained road-05 code binding changed: {relative}")

    preparation_started = time.perf_counter()
    config, inputs, accepted, preview_hashes = patch.load_candidate_inputs(ROOT, BASE_CONFIG)
    influence, bounds, target_points, _cumulative = patch._target_part_and_bounds(inputs)
    mesh = patch.build_topology_study_mesh(
        bounds, accepted, inputs, influence, target_points, variant=TRIAL_ID
    )
    candidate_bytes = (TRIAL_DIR / "candidate-heights.f32").read_bytes()
    candidate = np.frombuffer(candidate_bytes, dtype="<f4").copy()
    saved_xz = (TRIAL_DIR / "patch-vertices-xz.f64").read_bytes()
    saved_base = (TRIAL_DIR / "patch-base-heights.f32").read_bytes()
    saved_triangles = (TRIAL_DIR / "patch-triangles.u32").read_bytes()
    if mesh.vertices_xz.astype("<f8", copy=False).tobytes(order="C") != saved_xz:
        raise RuntimeError("reconstructed road-05 XZ buffer differs from retained topology")
    if mesh.base_y.astype("<f4", copy=False).tobytes(order="C") != saved_base:
        raise RuntimeError("reconstructed road-05 base buffer differs from retained topology")
    if mesh.triangles.astype("<u4", copy=False).tobytes(order="C") != saved_triangles:
        raise RuntimeError("reconstructed road-05 triangles differ from retained topology")
    candidate_hash = hashlib.sha256(candidate_bytes).hexdigest()
    if candidate_hash != solver.get("candidateFloat32Sha256"):
        raise RuntimeError("retained road-05 Float32 witness hash mismatch")
    if topology.get("trialId") != TRIAL_ID or topology.get("topologyVariant") != TRIAL_ID:
        raise RuntimeError("retained road-05 topology identity mismatch")
    if preview_hashes != attempt.get("acceptedPreviewHashes"):
        raise RuntimeError("accepted preview hashes differ from road-05 attempt")
    surface = patch.CompositeSurface(mesh, inputs, accepted, candidate)
    preparation_seconds = time.perf_counter() - preparation_started

    context_started = time.perf_counter()
    context = ValidationContextV1(surface)
    context_seconds = time.perf_counter() - context_started
    validation_started = time.perf_counter()
    report, context = validate_offline_candidate_v1(
        surface,
        influence,
        constraints_record["rows"],
        solver,
        preview_hashes,
        context=context,
    )
    validation_seconds = time.perf_counter() - validation_started
    validation_with_context_seconds = context_seconds + validation_seconds

    exact_sections = {}
    for name in patch.PATCH_OFFLINE_GATE_NAMES:
        exact_sections[name] = _same_report(report.get(name), old_aggregate.get(name))
    if not all(exact_sections.values()):
        mismatched = sorted(name for name, same in exact_sections.items() if not same)
        raise RuntimeError(
            f"versioned validation reports differ from retained road-05: {mismatched}"
        )
    if report.get("passes") != old_aggregate.get("passes"):
        raise RuntimeError("versioned validator changed the aggregate pass/fail result")
    if report.get("candidateFloat32Sha256") != old_aggregate.get("candidateFloat32Sha256"):
        raise RuntimeError("versioned validator changed the candidate witness identity")

    after = _tree_hashes(TRIAL_DIR)
    if before != after:
        raise RuntimeError("read-only validation benchmark modified the road-05 trial directory")

    pre_solver = float(solver["trialElapsedSecondsBeforeSolver"])
    solver_seconds = float(solver["elapsedSeconds"])
    finalization_residual = (
        RECORDED_TRIAL_SECONDS - pre_solver - solver_seconds - LEGACY_PROFILED_VALIDATION_SECONDS
    )
    projected_total = RECORDED_TRIAL_SECONDS + (
        validation_with_context_seconds - LEGACY_PROFILED_VALIDATION_SECONDS
    )
    return {
        "validatorVersion": VALIDATOR_VERSION,
        "trialId": TRIAL_ID,
        "candidateFloat32Sha256": candidate_hash,
        "retainedTopologyExact": True,
        "releaseId": inputs.release_id,
        "acceptedPreviewHashes": preview_hashes,
        "inputAndMeshPreparationSeconds": preparation_seconds,
        "validatorContextSetupSeconds": context_seconds,
        "optimizedOfflineValidationSeconds": validation_seconds,
        "optimizedOfflineValidationWithContextSeconds": validation_with_context_seconds,
        "optimizedGateSeconds": context.gate_seconds,
        "cacheAndRejectionStats": context.stats,
        "cacheSizes": {
            "baselineCoarsePolygon": len(context.baseline_coarse_polygons),
            "acceptedCoarsePolygon": len(context.accepted_coarse_polygons),
            "patchFacePolygon": len(context.patch_face_polygons),
            "patchFaceBounds": len(context.patch_face_bounds),
            "triangleCoordinateArrayBytes": int(context.triangle_xz.nbytes),
            "triangleHeightArrayBytes": int(context.triangle_y.nbytes),
        },
        "reportByteEquivalentToRetainedLegacy": exact_sections,
        "aggregatePassesUnchanged": report["passes"] == old_aggregate["passes"],
        "aggregatePasses": report["passes"],
        "gatePasses": {name: report[name]["passes"] for name in patch.PATCH_OFFLINE_GATE_NAMES},
        "historicalTrialElapsedSeconds": RECORDED_TRIAL_SECONDS,
        "historicalLegacyProfiledValidationSeconds": LEGACY_PROFILED_VALIDATION_SECONDS,
        "historicalCompleteBuildingGateSeconds": 54.430,
        "historicalEarthworkGateSeconds": 10.103,
        "retainedTrialPreSolverSeconds": pre_solver,
        "retainedTrialSolverSeconds": solver_seconds,
        "historicalFinalizationResidualSeconds": finalization_residual,
        "projectedEquivalentTotalSeconds": projected_total,
        "projectedMarginTo120Seconds": 120.0 - projected_total,
        "projectedMarginTo110Seconds": 110.0 - projected_total,
        "trialDirectoryByteIdentical": True,
        "retainedAggregateSha256": hashlib.sha256(
            (TRIAL_DIR / "offline-aggregate.json").read_bytes()
        ).hexdigest(),
        "retainedAggregatePasses": old_aggregate["passes"],
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))
