"""Run one bounded, write-once Teignmouth topology-study trial.

This offline-only command records a local candidate and its aggregate QA under
``.codex/evidence``. It never writes the reserved public candidate package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import shapely

from torquay_pipeline import road_surface
from torquay_pipeline.road_surface_patch import (
    ACCEPTED_PREVIEW_HASHES,
    PATCH_MAX_ASSET_BYTES,
    PATCH_MAX_BUILDING_BASE,
    PATCH_MAX_BUILDING_P95,
    PATCH_MAX_MANIFEST_BYTES,
    PATCH_MAX_PEAK_CONSTRUCTION_BYTES,
    PATCH_MAX_QA_BYTES,
    PATCH_MAX_RESIDENT_GEOMETRY_BYTES,
    PATCH_MAX_TRIANGLES,
    PATCH_MAX_VERTICES,
    PATCH_OFFLINE_GATE_NAMES,
    CompositeSurface,
    RoadSurfacePatchError,
    _protected_hash_snapshot,
    _target_part_and_bounds,
    assemble_deterministic_candidate_assets,
    build_local_phase_one_constraints,
    build_topology_study_mesh,
    load_candidate_inputs,
    patch_topology_report,
    serialize_offline_report,
    solve_local_phase_one,
    validate_candidate_patch_assets,
    validate_offline_candidate,
)
from torquay_pipeline.road_surface_study import (
    PREVIOUS_EVIDENCE,
    RAW_TRIAL_FILES,
    STUDY_INPUTS,
    TRIAL_ORDER,
    preflight_study_trial_paths,
    validate_study_stage_order,
)

ROOT = Path(__file__).resolve().parents[2]
STUDY_CONFIG_PATH = ROOT / "config/road-surface-teignmouth-topology-study.json"
BASE_CONFIG_PATH = ROOT / "config/road-surface-teignmouth-candidate.json"
FROZEN_STUDY_CONFIG_SHA256 = "5c292d2afb43f6f67b83d34a663494a138506bee18ea00d33b61f88569a1a26d"
FROZEN_BASE_CONFIG_SHA256 = "0616b0584cfc2d9043dd0b0e8c81926a45487e456855ab9375ce0878c6412140"
MAXIMUM_ITERATIONS = 2_000
MAXIMUM_WALL_SECONDS = 120.0


class TrialDeadlineExceeded(RoadSurfacePatchError):
    """The single trial budget expired before its next expensive phase."""


def _remaining_trial_seconds(deadline: float, phase: str, *, now: float | None = None) -> float:
    current = time.monotonic() if now is None else now
    remaining = deadline - current
    if remaining <= 0:
        raise TrialDeadlineExceeded(f"trial wall-time cap expired before {phase}")
    return remaining


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_digest(value: Any) -> str:
    return _digest(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )


def _exclusive_write(path: Path, payload: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def _code_hashes(root: Path) -> dict[str, str]:
    paths = (
        "pipeline/torquay_pipeline/road_surface.py",
        "pipeline/torquay_pipeline/road_surface_patch.py",
        "pipeline/torquay_pipeline/road_surface_topology.py",
        "pipeline/torquay_pipeline/road_surface_study.py",
        "pipeline/scripts/run_teignmouth_topology_study.py",
        "pipeline/tests/test_road_surface_patch.py",
        "pipeline/tests/test_road_surface_topology.py",
        "pipeline/tests/test_road_surface_study.py",
        "config/road-surface-teignmouth-topology-study.json",
        "config/road-surface-teignmouth-candidate.json",
        "docs/milestones/Teignmouth-topology-refinement-spec.md",
        ".gitignore",
    )
    output = {}
    for relative in paths:
        path = root / relative
        road_surface._assert_no_reparse_components(path)
        output[relative] = _digest(path.read_bytes())
    return output


def _frozen_study_input_hashes(root: Path) -> dict[str, str]:
    """Bind study policy and every pre-existing Road-surface-treatment artifact."""
    snapshot: dict[str, str] = {}
    for relative in STUDY_INPUTS:
        path = root / relative
        road_surface._assert_no_reparse_components(path)
        if not path.is_file():
            raise RoadSurfacePatchError(f"frozen study input is missing: {relative.as_posix()}")
        snapshot[f"studyInput:{relative.as_posix()}"] = _file_digest(path)

    evidence_root = root / PREVIOUS_EVIDENCE
    road_surface._assert_no_reparse_components(evidence_root)
    if not evidence_root.exists():
        snapshot[f"studyEvidenceTree:{PREVIOUS_EVIDENCE.as_posix()}"] = "absent"
        return snapshot
    tree_digest = hashlib.sha256()
    for current, child_dirs, filenames in os.walk(evidence_root, followlinks=False):
        current_path = Path(current)
        for name in sorted(child_dirs):
            child = current_path / name
            if road_surface._is_reparse_point(child):
                raise RoadSurfacePatchError(f"prior evidence contains a reparse directory: {child}")
        for name in sorted(filenames):
            child = current_path / name
            if road_surface._is_reparse_point(child):
                raise RoadSurfacePatchError(f"prior evidence contains a reparse file: {child}")
            relative_child = child.relative_to(evidence_root).as_posix()
            payload_digest = _file_digest(child)
            tree_digest.update(relative_child.encode("utf-8"))
            tree_digest.update(b"\0")
            tree_digest.update(str(child.stat().st_size).encode("ascii"))
            tree_digest.update(b"\0")
            tree_digest.update(payload_digest.encode("ascii"))
            tree_digest.update(b"\n")
    snapshot[f"studyEvidenceTree:{PREVIOUS_EVIDENCE.as_posix()}"] = tree_digest.hexdigest()
    return snapshot


def _environment() -> dict[str, str]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": np.__version__,
        "shapely": shapely.__version__,
        "geos": shapely.geos_version_string,
    }


def _load_frozen_configs() -> tuple[dict[str, Any], str, str]:
    study_bytes = STUDY_CONFIG_PATH.read_bytes()
    base_bytes = BASE_CONFIG_PATH.read_bytes()
    study_digest = _digest(study_bytes)
    base_digest = _digest(base_bytes)
    if study_digest != FROZEN_STUDY_CONFIG_SHA256:
        raise RoadSurfacePatchError(
            f"frozen study config digest changed: {study_digest}; expected "
            f"{FROZEN_STUDY_CONFIG_SHA256}"
        )
    if base_digest != FROZEN_BASE_CONFIG_SHA256:
        raise RoadSurfacePatchError(
            f"pinned base candidate config changed: {base_digest}; expected "
            f"{FROZEN_BASE_CONFIG_SHA256}"
        )
    try:
        study = json.loads(study_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoadSurfacePatchError("frozen topology study config is invalid JSON") from exc
    if study.get("candidate_base_config") != {
        "path": "config/road-surface-teignmouth-candidate.json",
        "sha256": FROZEN_BASE_CONFIG_SHA256,
    }:
        raise RoadSurfacePatchError("study config does not match the pinned base config identity")
    if tuple(item.get("trial_id") for item in study.get("topology_variants", [])) != TRIAL_ORDER:
        raise RoadSurfacePatchError("study config trial order differs from the frozen trial list")
    policy = study.get("run_policy", {})
    if (
        policy.get("maximum_iterations") != MAXIMUM_ITERATIONS
        or policy.get("maximum_wall_seconds") != MAXIMUM_WALL_SECONDS
        or policy.get("retry_allowed") is not False
        or policy.get("write_once") is not True
    ):
        raise RoadSurfacePatchError("study run policy differs from the frozen resource limits")
    if study.get("accepted_preview") != ACCEPTED_PREVIEW_HASHES:
        raise RoadSurfacePatchError(
            "study config accepted-preview hashes differ from the pinned base"
        )
    if set(study.get("raw_trial_files", [])) != RAW_TRIAL_FILES:
        raise RoadSurfacePatchError(
            "study config raw trial file allowlist is incomplete or changed"
        )
    return study, study_digest, base_digest


def _select_refinement_base(raw_root: Path) -> tuple[str, dict[str, Any]]:
    """Select the road-aligned 0.5 m result with the lowest normalized gate ratio."""
    candidates = []
    for trial_id in ("road-05", "collar-05"):
        aggregate_path = raw_root / trial_id / "offline-aggregate.json"
        attempt_path = raw_root / trial_id / "attempt.json"
        try:
            aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
            attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RoadSurfacePatchError(
                f"cannot select local refinement base; completed {trial_id} report is missing"
            ) from exc
        local = aggregate.get("localCorridorLongitudinal", {}).get("teignmouthLocal", {})
        terrain = aggregate.get("compositeTerrain", {})
        buildings = aggregate.get("completeBuildingFootprints", {})
        ratios = [
            float(local.get("maximumLocalLateralSlopePercent", float("inf"))) / 5.0,
            float(local.get("maximumEndpointSpanM", float("inf"))) / 0.30,
            float(local.get("maximumAbsoluteCenterlineDeviationM", float("inf"))) / 0.10,
            float(local.get("maximumAbsoluteSignedGradeChangePercentagePoints", float("inf")))
            / 2.0,
            float(terrain.get("maximumAbsoluteChangeFromSourceM", float("inf"))) / 5.0,
            float(terrain.get("maximumPositiveAddedGradientMPerM", float("inf"))) / 1.0,
            float(buildings.get("baseDisplacementMaximumAbsoluteM", float("inf")))
            / PATCH_MAX_BUILDING_BASE,
            float(buildings.get("baseDisplacementP95AbsoluteM", float("inf")))
            / PATCH_MAX_BUILDING_P95,
        ]
        finite = [value for value in ratios if np.isfinite(value)]
        score = max(finite) if len(finite) == len(ratios) else float("inf")
        candidates.append(
            (
                score,
                0 if trial_id == "road-05" else 1,
                trial_id,
                {
                    "trialId": trial_id,
                    "maximumNormalizedGateRatio": score,
                    "candidateFloat32Sha256": aggregate.get("candidateFloat32Sha256"),
                    "aggregateSha256": _digest(aggregate_path.read_bytes()),
                    "inputSnapshotSha256": attempt.get("inputSnapshotSha256"),
                },
            )
        )
    _score, _tie_order, trial_id, record = min(candidates, key=lambda item: item[:3])
    if not np.isfinite(_score):
        raise RoadSurfacePatchError(
            "no completed road-aligned topology has finite normalized gate metrics for refinement"
        )
    return trial_id, record


def _constraint_bytes(constraints: list[dict[str, Any]], summary: dict[str, Any]) -> bytes:
    return serialize_offline_report(
        {
            "summary": summary,
            "rows": [
                {
                    "indices": row["indices"],
                    "coefficients": row["coefficients"],
                    "limitM": row["limitM"],
                    "label": row["label"],
                }
                for row in constraints
            ],
        }
    )


def _verify_local_certificate(solver_report: dict[str, Any] | None) -> dict[str, Any]:
    """Recheck any bounded local Farkas certificate using exact rational decimals."""
    from fractions import Fraction

    local = (solver_report or {}).get("boundedLocalFeasibility") or {}
    certificate = local.get("infeasibilityCertificate")
    if not isinstance(certificate, dict):
        return {
            "status": "not_emitted",
            "verified": None,
            "reason": "the bounded solver did not emit an infeasibility certificate",
        }
    rows = local.get("rows", [])
    weights_raw = certificate.get("nonnegativeRowWeights", [])
    lower = local.get("lowerBoundsM", [])
    upper = local.get("upperBoundsM", [])
    if len(rows) != len(weights_raw) or len(lower) != len(upper):
        return {"status": "invalid", "verified": False, "reason": "certificate dimensions differ"}
    try:
        weights = [Fraction(str(value)) for value in weights_raw]
        if any(value < 0 for value in weights) or not weights or sum(weights) <= 0:
            raise ValueError("weights must be nonnegative and have positive total")
        coefficients = [Fraction(0) for _ in lower]
        weighted_limit = Fraction(0)
        for weight, row in zip(weights, rows, strict=True):
            weighted_limit += weight * Fraction(str(row["actualLimitM"]))
            for index, value in zip(row["nodeIndices"], row["coefficients"], strict=True):
                coefficients[int(index)] += weight * Fraction(str(value))
        minimum = Fraction(0)
        for coefficient, lo, hi in zip(coefficients, lower, upper, strict=True):
            bound = Fraction(str(lo)) if coefficient >= 0 else Fraction(str(hi))
            minimum += coefficient * bound
        gap = minimum - weighted_limit
        verified = gap > 0
        return {
            "status": "verified" if verified else "invalid",
            "verified": verified,
            "arithmetic": (
                "exact rational arithmetic over round-trip serialized decimal rows/weights"
            ),
            "weightTotal": str(sum(weights)),
            "minimumCombinedValueOverBoundsM": str(minimum),
            "weightedUpperLimitM": str(weighted_limit),
            "contradictionGapM": str(gap),
            "floatReportedGapM": certificate.get("contradictionGapM"),
            "passes": verified,
        }
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        return {"status": "invalid", "verified": False, "reason": str(exc), "passes": False}


def _array_buffer_bytes(value: Any, seen: set[int] | None = None) -> int:
    """Count distinct NumPy/byte buffers retained by a road clipping report."""
    if seen is None:
        seen = set()
    identity = id(value)
    if identity in seen:
        return 0
    if isinstance(value, np.ndarray):
        seen.add(identity)
        return int(value.nbytes)
    if isinstance(value, bytes):
        seen.add(identity)
        return len(value)
    if isinstance(value, dict):
        seen.add(identity)
        return sum(_array_buffer_bytes(item, seen) for item in value.values())
    if isinstance(value, (list, tuple)):
        seen.add(identity)
        return sum(_array_buffer_bytes(item, seen) for item in value)
    return 0


def _resource_report(
    mesh: Any,
    clipped_roads: dict[str, Any],
    first_assets: dict[str, bytes],
    second_assets: dict[str, bytes],
) -> dict[str, Any]:
    runtime_bytes = sum(map(len, first_assets.values()))
    geometry_files = {
        "terrain-vertices.f32",
        "terrain-indices.u32",
        "road-vertices.f32",
        "road-indices.u32",
        "road-terrain-triangles.u32",
    }
    resident_bytes = sum(len(first_assets[name]) for name in geometry_files)
    resources = clipped_roads["resourceReport"]
    groups = clipped_roads["groups"]
    added_draw_calls = 1 + sum(1 for group in groups.values() if len(group.get("indices", [])) > 0)
    working_buffers = (
        mesh.vertices_xz.nbytes
        + mesh.base_y.nbytes
        + mesh.triangles.nbytes
        + _array_buffer_bytes(groups)
    )
    independent_output_buffers = sum(map(len, first_assets.values())) + sum(
        map(len, second_assets.values())
    )
    peak = working_buffers + independent_output_buffers
    report = {
        "replacementTriangleCount": resources["incrementalTriangles"],
        "replacementTriangleLimit": PATCH_MAX_TRIANGLES,
        "replacementVertexCount": resources["incrementalVertices"],
        "replacementVertexLimit": PATCH_MAX_VERTICES,
        "addedDrawCalls": added_draw_calls,
        "addedDrawCallLimit": 4,
        "runtimeAssetBytes": runtime_bytes,
        "runtimeAssetByteLimit": PATCH_MAX_ASSET_BYTES,
        "manifestBytes": len(first_assets["manifest.json"]),
        "manifestByteLimit": PATCH_MAX_MANIFEST_BYTES,
        "qaBytes": len(first_assets["qa.json"]),
        "qaByteLimit": PATCH_MAX_QA_BYTES,
        "addedResidentGeometryBytes": resident_bytes,
        "addedResidentGeometryByteLimit": PATCH_MAX_RESIDENT_GEOMETRY_BYTES,
        "peakConstructionBufferBytes": peak,
        "peakConstructionBufferByteLimit": PATCH_MAX_PEAK_CONSTRUCTION_BYTES,
        "peakEstimateComponents": {
            "meshVertexAndIndexBuffers": int(
                mesh.vertices_xz.nbytes + mesh.base_y.nbytes + mesh.triangles.nbytes
            ),
            "roadClippingNumPyBuffers": _array_buffer_bytes(groups),
            "twoIndependentSerializedOutputs": independent_output_buffers,
        },
    }
    report["passes"] = bool(
        report["replacementTriangleCount"] <= PATCH_MAX_TRIANGLES
        and report["replacementVertexCount"] <= PATCH_MAX_VERTICES
        and report["addedDrawCalls"] <= 4
        and report["runtimeAssetBytes"] <= PATCH_MAX_ASSET_BYTES
        and report["manifestBytes"] <= PATCH_MAX_MANIFEST_BYTES
        and report["qaBytes"] <= PATCH_MAX_QA_BYTES
        and report["addedResidentGeometryBytes"] <= PATCH_MAX_RESIDENT_GEOMETRY_BYTES
        and report["peakConstructionBufferBytes"] <= PATCH_MAX_PEAK_CONSTRUCTION_BYTES
    )
    return report


def _refinement_base_for_trial(
    trial_id: str,
    raw_root: Path,
) -> tuple[str | None, dict[str, Any] | None]:
    if trial_id not in {"local-025", "local-0125"}:
        return None, None
    base_id, record = _select_refinement_base(raw_root)
    if trial_id == "local-0125":
        previous = json.loads((raw_root / "local-025" / "attempt.json").read_text(encoding="utf-8"))
        previous_base = previous.get("refinementBase", {})
        if previous_base.get("trialId") != base_id:
            raise RoadSurfacePatchError(
                "local-0125 base differs from completed local-025 selection"
            )
        return base_id, record
    return base_id, record


def _final_classification(
    aggregate: dict[str, Any],
    topology: dict[str, Any] | None,
    solver_report: dict[str, Any] | None,
    certificate: dict[str, Any],
) -> str:
    if aggregate.get("passes") is True:
        return "offline_pass"
    if topology is not None and topology.get("passes") is False:
        return "failed_topology_or_resource_gate"
    local_phase = (solver_report or {}).get("boundedLocalFeasibility") or {}
    if local_phase.get("status") == "certified_infeasible" and certificate.get("verified") is True:
        return "certified_infeasible"
    if solver_report is not None and not solver_report.get("converged"):
        return "unresolved_numerical_result"
    return "failed_offline_gate"


def run_one_trial(trial_id: str) -> tuple[int, dict[str, Any]]:
    """Preflight, solve and fully aggregate exactly one registered trial."""
    trial_started_monotonic = time.monotonic()
    deadline = trial_started_monotonic + MAXIMUM_WALL_SECONDS
    study, study_digest, base_digest = _load_frozen_configs()
    _remaining_trial_seconds(deadline, "path preflight")
    paths = preflight_study_trial_paths(ROOT, trial_id, study_config=study)
    validate_study_stage_order(paths.raw_root, trial_id)

    # Load/validate all immutable inputs before creating the one-shot directory.
    _remaining_trial_seconds(deadline, "pinned input loading")
    config, inputs, accepted, accepted_preview_hashes = load_candidate_inputs(
        ROOT, BASE_CONFIG_PATH
    )
    _remaining_trial_seconds(deadline, "protected-input snapshot")
    protected_before = {
        **_protected_hash_snapshot(ROOT, inputs),
        **_frozen_study_input_hashes(ROOT),
    }
    input_snapshot_digest = _canonical_digest(protected_before)
    code_before = _code_hashes(ROOT)
    _remaining_trial_seconds(deadline, "stage identity validation")
    validate_study_stage_order(
        paths.raw_root,
        trial_id,
        expected_study_config_sha256=study_digest,
        expected_input_snapshot_sha256=input_snapshot_digest,
        expected_code_hashes=code_before,
    )
    refinement_base, refinement_base_record = _refinement_base_for_trial(trial_id, paths.raw_root)
    _remaining_trial_seconds(deadline, "one-shot record creation")

    attempt = {
        "studyId": study["study_id"],
        "trialId": trial_id,
        "trialOrderIndex": TRIAL_ORDER.index(trial_id),
        "startedUnixSeconds": time.time(),
        "studyConfigSha256": study_digest,
        "baseCandidateConfigSha256": base_digest,
        "codeHashes": code_before,
        "environment": _environment(),
        "releaseId": inputs.release_id,
        "releaseSourceHashes": inputs.source_hashes,
        "acceptedPreviewHashes": accepted_preview_hashes,
        "protectedHashesBefore": protected_before,
        "inputSnapshotSha256": input_snapshot_digest,
        "solverLimits": {
            "maximumIterations": MAXIMUM_ITERATIONS,
            "maximumWallSeconds": MAXIMUM_WALL_SECONDS,
            "wallClockIncludesInputAndPreparation": True,
            "deadlineStartsAtTrialInvocation": True,
        },
        "refinementBase": refinement_base_record,
        "candidatePublicOutputWritten": False,
    }

    if paths.trial.exists():
        raise RoadSurfacePatchError(
            "study output appeared after preflight; refusing a race collision"
        )
    road_surface._assert_no_reparse_components(paths.raw_root)
    if not paths.raw_root.exists():
        paths.raw_root.mkdir(parents=False, exist_ok=False)
    road_surface._assert_no_reparse_components(paths.raw_root)
    paths.trial.mkdir(parents=False, exist_ok=False)
    road_surface._assert_no_reparse_components(paths.trial)
    _exclusive_write(paths.trial / "attempt.json", serialize_offline_report(attempt))

    influence = None
    mesh = None
    topology = None
    constraints = None
    constraint_summary = None
    candidate = None
    solver_report = None
    aggregate: dict[str, Any] = {
        "trialId": trial_id,
        "passes": False,
        "phase": "input-ready",
        "candidatePublicOutputWritten": False,
    }
    certificate: dict[str, Any] = {
        "status": "not_emitted",
        "verified": None,
        "reason": "solver did not run",
    }
    topology_report: dict[str, Any] | None = None
    try:
        _remaining_trial_seconds(deadline, "target influence preparation")
        influence, bounds, target_points, target_cumulative = _target_part_and_bounds(inputs)
        _remaining_trial_seconds(deadline, "topology mesh construction")
        candidate_variant = trial_id
        if refinement_base:
            candidate_variant = trial_id
        mesh = build_topology_study_mesh(
            bounds,
            accepted,
            inputs,
            influence,
            target_points,
            variant=candidate_variant,
            refinement_base_variant=refinement_base,
        )
        _remaining_trial_seconds(deadline, "topology validation")
        topology = patch_topology_report(mesh, inputs.spacing_m)
        _remaining_trial_seconds(deadline, "topology report generation")
        topology_report = {
            **topology,
            "trialId": trial_id,
            "topologyVariant": mesh.topology_variant,
            "refinementBaseTrialId": refinement_base,
            "patchBounds": bounds.__dict__,
            "targetSegmentPointsXZ": target_points,
            "targetPartCumulativeStationsM": target_cumulative,
            "influenceAreaM2": float(influence.area),
            "sourceOverlapIndex": (
                "STRtree complete patch-face/source-triangle intersection partition"
            ),
        }
        _exclusive_write(paths.trial / "topology.json", serialize_offline_report(topology_report))
        if not topology["passes"]:
            aggregate.update({"phase": "topology", "topology": topology_report})
            raise RoadSurfacePatchError("topology/resource gate failed before solve")

        _remaining_trial_seconds(deadline, "constraint preparation")
        constraints, constraint_summary = build_local_phase_one_constraints(mesh, inputs, accepted)
        constraints_report = {
            "summary": constraint_summary,
            "rows": [
                {
                    "indices": row["indices"],
                    "coefficients": row["coefficients"],
                    "limitM": row["limitM"],
                    "label": row["label"],
                }
                for row in constraints
            ],
        }
        _exclusive_write(
            paths.trial / "constraints.json",
            serialize_offline_report(constraints_report),
        )

        solver_budget_seconds = _remaining_trial_seconds(deadline, "bounded solver")
        candidate, solver_report = solve_local_phase_one(
            mesh,
            inputs,
            constraints,
            influence=influence,
            maximum_iterations=MAXIMUM_ITERATIONS,
            tolerance_m=2e-5,
            maximum_wall_seconds=solver_budget_seconds,
        )
        _remaining_trial_seconds(deadline, "solver result validation")
        candidate_bytes = candidate.astype("<f4", copy=False).tobytes(order="C")
        _exclusive_write(paths.trial / "candidate-heights.f32", candidate_bytes)
        _exclusive_write(
            paths.trial / "patch-vertices-xz.f64",
            mesh.vertices_xz.astype("<f8", copy=False).tobytes(order="C"),
        )
        _exclusive_write(
            paths.trial / "patch-base-heights.f32",
            mesh.base_y.astype("<f4", copy=False).tobytes(order="C"),
        )
        _exclusive_write(
            paths.trial / "patch-triangles.u32",
            mesh.triangles.astype("<u4", copy=False).tobytes(order="C"),
        )
        solver_report = {
            **solver_report,
            "trialWallBudgetSecondsAtSolverStart": solver_budget_seconds,
            "trialElapsedSecondsBeforeSolver": MAXIMUM_WALL_SECONDS - solver_budget_seconds,
            "candidateFloat32Sha256": _digest(candidate_bytes),
            "candidateFloat32ByteLength": len(candidate_bytes),
            "topologyVariant": mesh.topology_variant,
            "constraintSummary": constraint_summary,
            "patchBounds": bounds.__dict__,
        }
        certificate = _verify_local_certificate(solver_report)
        _exclusive_write(
            paths.trial / "solver-phase.json",
            serialize_offline_report(solver_report),
        )
        _exclusive_write(
            paths.trial / "certificate-verification.json",
            serialize_offline_report(certificate),
        )
        surface = CompositeSurface(mesh, inputs, accepted, candidate)
        aggregate = validate_offline_candidate(
            surface,
            influence,
            constraints,
            solver_report,
            accepted_preview_hashes,
        )
        _remaining_trial_seconds(deadline, "offline aggregate validation")
        aggregate.update(
            {
                "phase": "complete-offline-aggregate",
                "trialId": trial_id,
                "topologyVariant": mesh.topology_variant,
                "refinementBaseTrialId": refinement_base,
                "patchTopology": topology_report,
                "constraintSummary": constraint_summary,
                "solver": solver_report,
                "certificateVerification": certificate,
                "candidatePublicOutputWritten": False,
                "candidateFloat32Sha256": _digest(candidate_bytes),
                "candidateFloat32ByteLength": len(candidate_bytes),
            }
        )

        if aggregate.get("passes") is True:
            _remaining_trial_seconds(deadline, "independent asset assembly")
            first_assets, second_assets, deterministic = assemble_deterministic_candidate_assets(
                surface,
                aggregate["roadPathReclip"],
                aggregate,
            )
            first_validation = validate_candidate_patch_assets(
                first_assets,
                surface,
                aggregate["candidateFloat32Sha256"],
                aggregate["roadPathReclip"],
            )
            second_validation = validate_candidate_patch_assets(
                second_assets,
                surface,
                aggregate["candidateFloat32Sha256"],
                aggregate["roadPathReclip"],
            )
            resources = _resource_report(
                mesh, aggregate["roadPathReclip"], first_assets, second_assets
            )
            _remaining_trial_seconds(deadline, "resource and determinism validation")
            deterministic_hashes = {
                "first": {name: _digest(payload) for name, payload in sorted(first_assets.items())},
                "second": {
                    name: _digest(payload) for name, payload in sorted(second_assets.items())
                },
            }
            deterministic_pass = bool(
                deterministic["passes"]
                and first_validation["passes"]
                and second_validation["passes"]
                and first_assets is not second_assets
                and first_assets == second_assets
                and deterministic_hashes["first"] == deterministic_hashes["second"]
            )
            aggregate["studyAssemblyAndResources"] = {
                "passes": deterministic_pass and resources["passes"],
                "deterministicAssets": deterministic_pass,
                "firstIndependentValidation": first_validation,
                "secondIndependentValidation": second_validation,
                "independentAssetHashes": deterministic_hashes,
                "resourceLimits": resources,
                "publicOutputWritten": False,
            }
            aggregate["passes"] = bool(
                aggregate["passes"] and aggregate["studyAssemblyAndResources"]["passes"]
            )

        aggregate["finalClassification"] = _final_classification(
            aggregate, topology_report, solver_report, certificate
        )
    except Exception as exc:  # Preserve one-shot diagnostics after the trial marker exists.
        aggregate["passes"] = False
        aggregate["error"] = f"{type(exc).__name__}: {exc}"
        if isinstance(exc, TrialDeadlineExceeded):
            aggregate["phase"] = "deadline-exceeded"
            aggregate["deadlineExceededDuringPhase"] = str(exc)
            aggregate["finalClassification"] = "unresolved_numerical_result"
        aggregate.setdefault("phase", "exception")
        if topology_report is not None:
            aggregate.setdefault("patchTopology", topology_report)
        if constraint_summary is not None:
            aggregate.setdefault("constraintSummary", constraint_summary)
        if solver_report is not None:
            aggregate.setdefault("solver", solver_report)
        aggregate.setdefault(
            "finalClassification",
            _final_classification(aggregate, topology_report, solver_report, certificate),
        )

    if time.monotonic() >= deadline:
        aggregate["passes"] = False
        aggregate["deadlineExceededDuringPhase"] = aggregate.get(
            "deadlineExceededDuringPhase", "protected-input after-snapshot/finalization"
        )
        aggregate["finalClassification"] = "unresolved_numerical_result"
    protected_after = {
        **_protected_hash_snapshot(ROOT, inputs),
        **_frozen_study_input_hashes(ROOT),
    }
    code_after = _code_hashes(ROOT)
    study_after = _digest(STUDY_CONFIG_PATH.read_bytes())
    base_after = _digest(BASE_CONFIG_PATH.read_bytes())
    candidate_still_absent = not paths.candidate.exists()
    aggregate.update(
        {
            "protectedHashesBefore": protected_before,
            "protectedHashesAfter": protected_after,
            "protectedHashesMatch": protected_before == protected_after,
            "inputSnapshotSha256": input_snapshot_digest,
            "protectedSnapshotSha256After": _canonical_digest(protected_after),
            "codeHashesBefore": code_before,
            "codeHashesAfter": code_after,
            "codeUnchangedDuringTrial": code_before == code_after,
            "studyConfigSha256Before": study_digest,
            "studyConfigSha256After": study_after,
            "baseCandidateConfigSha256Before": base_digest,
            "baseCandidateConfigSha256After": base_after,
            "configsUnchangedDuringTrial": study_digest == study_after
            and base_digest == base_after,
            "candidateOutputStillAbsent": candidate_still_absent,
            "candidatePublicOutputWritten": False,
            "trialElapsedSeconds": time.monotonic() - trial_started_monotonic,
            "trialDeadlineMonotonicSeconds": deadline,
            "trialMaximumWallSeconds": MAXIMUM_WALL_SECONDS,
            "evidencePath": paths.trial.relative_to(ROOT).as_posix(),
        }
    )
    if not aggregate["protectedHashesMatch"] or not aggregate["codeUnchangedDuringTrial"]:
        aggregate["passes"] = False
        aggregate["finalClassification"] = "failed_offline_gate"
    if not aggregate["configsUnchangedDuringTrial"] or not candidate_still_absent:
        aggregate["passes"] = False
        aggregate["finalClassification"] = "failed_offline_gate"
    if time.monotonic() >= deadline:
        aggregate["passes"] = False
        aggregate["deadlineExceededDuringPhase"] = aggregate.get(
            "deadlineExceededDuringPhase", "final preservation/configuration verification"
        )
        aggregate["finalClassification"] = "unresolved_numerical_result"

    if set(path.name for path in paths.trial.iterdir()) - RAW_TRIAL_FILES:
        aggregate["passes"] = False
        aggregate["finalClassification"] = "failed_offline_gate"
        aggregate["unexpectedOutputFiles"] = sorted(
            set(path.name for path in paths.trial.iterdir()) - RAW_TRIAL_FILES
        )
    if not (paths.trial / "offline-aggregate.json").exists():
        _exclusive_write(
            paths.trial / "offline-aggregate.json",
            serialize_offline_report(aggregate),
        )
    result = {
        "trialId": trial_id,
        "passes": aggregate.get("passes") is True,
        "finalClassification": aggregate.get("finalClassification"),
        "candidateFloat32Sha256": aggregate.get("candidateFloat32Sha256"),
        "solverStatus": (aggregate.get("solver") or {}).get("converged"),
        "gateResults": {
            name: (aggregate.get(name) or {}).get("passes") for name in PATCH_OFFLINE_GATE_NAMES
        },
        "candidateOutputStillAbsent": aggregate.get("candidateOutputStillAbsent"),
        "protectedHashesMatch": aggregate.get("protectedHashesMatch"),
        "studyConfigSha256": study_digest,
        "inputSnapshotSha256": input_snapshot_digest,
        "evidencePath": paths.trial.relative_to(ROOT).as_posix(),
    }
    print(serialize_offline_report(result).decode("utf-8"), flush=True)
    return (0 if result["passes"] else 2), aggregate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--trial", required=True, choices=TRIAL_ORDER)
    args = parser.parse_args()
    requested_config = args.config if args.config.is_absolute() else ROOT / args.config
    if os.path.normcase(str(requested_config.resolve(strict=False))) != os.path.normcase(
        str(STUDY_CONFIG_PATH.resolve(strict=True))
    ):
        raise RoadSurfacePatchError("--config must name the exact frozen topology-study config")
    status, _aggregate = run_one_trial(args.trial)
    return status


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RoadSurfacePatchError as exc:
        print(json.dumps({"passes": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2) from exc
