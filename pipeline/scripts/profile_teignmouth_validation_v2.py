"""Read-only exact-equivalence and timing profile for retained road-05 bytes."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import runpy
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from torquay_pipeline import road_surface_patch as patch  # noqa: E402
from torquay_pipeline.road_surface_validation_transition_v2 import (  # noqa: E402
    canonical_digest,
    file_digest,
    validate_prior_input_transition,
    validate_transition_inputs,
)
from torquay_pipeline.road_surface_validation_v2 import (  # noqa: E402
    VALIDATOR_VERSION,
    ValidationContextV2,
    validate_offline_candidate_v2,
)

TRIAL_ID = "road-05"
RAW_ROOT = ROOT / ".codex/evidence/teignmouth-topology-study"
TRIAL_DIR = RAW_ROOT / TRIAL_ID
CONFIG_PATH = ROOT / "config/road-surface-teignmouth-topology-transition-v2.json"
STUDY_RUNNER = ROOT / "pipeline/scripts/run_teignmouth_topology_study.py"
BASE_CONFIG = ROOT / "config/road-surface-teignmouth-candidate.json"
PROFILE_RELATIVE = Path(
    "docs/milestones/artifacts/Teignmouth-topology-validation-v2/retained-road-05-profile-fix3-harness.json"
)
RECORDED_TRIAL_SECONDS = 128.2744305
LEGACY_VALIDATION_SECONDS = 80.517233


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


def _serialized_equal(first: Any, second: Any) -> bool:
    return patch.serialize_offline_report({"report": first}) == patch.serialize_offline_report(
        {"report": second}
    )


def _current_protected_map(runner: dict[str, Any], inputs: Any) -> dict[str, str]:
    return {
        **runner["_protected_hash_snapshot"](ROOT, inputs),
        **runner["_frozen_study_input_hashes"](ROOT),
    }


def _synthetic_approval_check_seconds(config: dict[str, Any], wrapper: Any) -> float:
    """Time the exact artifact-validation shape without writing into the repository."""
    with tempfile.TemporaryDirectory(prefix="teignmouth-v2-approval-profile-") as temporary:
        root = Path(temporary)
        activated = json.loads(json.dumps(config))
        activated["activation"] = {"enabled": True, "status": "approval_chain_required"}
        config_path = root / "config/road-surface-teignmouth-topology-transition-v2.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(
            json.dumps(activated, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        code_paths = set(activated["legacy_road05_code_hashes"]) | set(
            activated["extension_code_hashes"]
        )
        code_paths.discard("config/road-surface-teignmouth-topology-transition-v2.json")
        for relative in code_paths:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        approval_root = root / wrapper.APPROVAL_ROOT
        approval_root.mkdir(parents=True)
        review_path = root / wrapper.SOL_REVIEW_PATH
        receipt_path = root / wrapper.COORDINATOR_RECEIPT_PATH
        bound = wrapper._approval_payload(activated, config_path, root)
        review = {
            "schema": "teignmouth-validation-v2-sol-review-v1",
            "reviewer": "Sol 6.1",
            "disposition": "PASS",
            **bound,
        }
        review_path.write_text(
            json.dumps(review, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        receipt = {
            "schema": "teignmouth-validation-v2-coordinator-acceptance-v1",
            "disposition": "ACCEPTED",
            **bound,
            "independent_sol_review_path": wrapper.SOL_REVIEW_PATH,
            "independent_sol_review_sha256": file_digest(review_path),
        }
        receipt_path.write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        checkpoint = root / activated["input_state_transition"]["checkpoint_path"]
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_text(
            wrapper.ACCEPTED_CHECKPOINT_PREFIX + file_digest(receipt_path) + "\n",
            encoding="utf-8",
        )
        started = time.perf_counter()
        wrapper.ensure_transition_activated(activated, root=root, config_path=config_path)
        return time.perf_counter() - started


def _performance_only_reclip_harness(surface: Any, report: dict[str, Any]) -> dict[str, Any]:
    """Build structural road buffers from real affected source faces for timing only.

    The synthetic groups deliberately do not claim to be the failed exact road reclip.
    They preserve the real release road-face counts in the configured replacement cells,
    but use a valid replacement triangle owner only to exercise in-memory asset assembly.
    """
    mesh = surface.mesh
    batch_map = surface.inputs.road_payload["surfaceBatches"]
    groups: dict[str, dict[str, np.ndarray]] = {}
    affected_face_counts: dict[str, int] = {}
    for name in ("vehicular", "cycleway", "path"):
        batch = batch_map[name]
        vertices = np.asarray(batch["verticesXZ"], dtype=np.float64).reshape(-1, 2)
        faces = np.asarray(batch["indices"], dtype=np.int64).reshape(-1, 3)
        source_owners = np.asarray(batch["terrainTriangles"], dtype=np.int64).reshape(-1, 3)
        in_patch = (
            (source_owners[:, 0] >= mesh.bounds.first_row)
            & (source_owners[:, 0] < mesh.bounds.last_row)
            & (source_owners[:, 1] >= mesh.bounds.first_column)
            & (source_owners[:, 1] < mesh.bounds.last_column)
        )
        selected_faces = faces[in_patch]
        selected_owners = source_owners[in_patch]
        affected_face_counts[name] = int(len(selected_faces))
        if len(selected_faces):
            used_vertices, inverse = np.unique(selected_faces.reshape(-1), return_inverse=True)
            selected_vertices = vertices[used_vertices]
            selected_indices = inverse.reshape(-1, 3).astype(np.uint32)
            replacement_owners: list[int] = []
            for row, column, half in selected_owners:
                replacement_faces = mesh.cell_half_triangles[(int(row), int(column), int(half))]
                if not replacement_faces:
                    raise RuntimeError(
                        "performance harness found a source cell without replacement faces"
                    )
                replacement_owners.append(int(replacement_faces[0]))
            owner_ids = np.asarray(replacement_owners, dtype=np.uint32)
        else:
            selected_vertices = np.empty((0, 2), dtype=np.float64)
            selected_indices = np.empty((0, 3), dtype=np.uint32)
            owner_ids = np.empty(0, dtype=np.uint32)
        groups[name] = {
            "verticesXZ": selected_vertices,
            "indices": selected_indices,
            "terrainTriangles": owner_ids,
        }

    topology = report["topology"]
    clipped = {
        "passes": True,
        "groups": groups,
        "affectedSourceAreaM2": 0.0,
        "replacementHorizontalAreaM2": 0.0,
        "float32HorizontalAreaDriftM2": 0.0,
        "float32FootprintCoverageErrorM2": 0.0,
        "float32OmittedAreaM2": 0.0,
        "quantizationSafeSharedEdgeAdjustmentCount": 0,
        "resourceReport": {
            "incrementalTriangles": int(topology["netTerrainTriangleIncrease"]),
            "incrementalVertices": int(topology["netTerrainVertexIncreaseUpperBound"]),
        },
    }
    synthetic_report = copy.deepcopy(report)
    synthetic_report["passes"] = True
    for gate_name in patch.PATCH_OFFLINE_GATE_NAMES:
        gate = synthetic_report.get(gate_name)
        if not isinstance(gate, dict):
            raise RuntimeError(f"performance harness missing offline report field {gate_name}")
        gate["passes"] = True
    synthetic_report["gateNames"] = list(patch.PATCH_OFFLINE_GATE_NAMES)
    synthetic_report["roadPathReclip"] = clipped
    return {
        "roadReport": clipped,
        "offlineReport": synthetic_report,
        "affectedSourceFaceCounts": affected_face_counts,
        "syntheticOwnerMapping": (
            "each selected real source face is assigned to the first replacement triangle "
            "in its source-owned coarse cell; this is not clipped road geometry"
        ),
    }


def profile() -> dict[str, Any]:
    import run_teignmouth_topology_validation_v2 as wrapper
    from run_teignmouth_topology_validation_v2 import _read_config, _validate_static_bindings

    before = _tree_hashes(TRIAL_DIR)
    attempt = json.loads((TRIAL_DIR / "attempt.json").read_text(encoding="utf-8"))
    topology = json.loads((TRIAL_DIR / "topology.json").read_text(encoding="utf-8"))
    solver = json.loads((TRIAL_DIR / "solver-phase.json").read_text(encoding="utf-8"))
    constraints = json.loads((TRIAL_DIR / "constraints.json").read_text(encoding="utf-8"))
    legacy = json.loads((TRIAL_DIR / "offline-aggregate.json").read_text(encoding="utf-8"))
    config_preflight_started = time.perf_counter()
    config = _read_config(CONFIG_PATH)
    _validate_static_bindings(config)
    static_preflight_seconds = time.perf_counter() - config_preflight_started

    for relative, expected in attempt["codeHashes"].items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"retained road-05 code binding changed: {relative}")

    preparation_started = time.perf_counter()
    runner = runpy.run_path(str(STUDY_RUNNER))
    runner_globals = runner["run_one_trial"].__globals__
    wrapper_state = wrapper._patch_runner(runner, config, invocation_start=time.monotonic())
    trial_code_hashes = runner_globals["_code_hashes"]
    code_hash_before_started = time.perf_counter()
    trial_code_hashes(ROOT)
    code_hash_pass_seconds = time.perf_counter() - code_hash_before_started
    _study, study_digest, _base_digest = runner_globals["_load_frozen_configs"]()
    source_config, inputs, accepted, preview_hashes = patch.load_candidate_inputs(ROOT, BASE_CONFIG)
    influence, bounds, target_points, _cumulative = patch._target_part_and_bounds(inputs)
    mesh = patch.build_topology_study_mesh(
        bounds, accepted, inputs, influence, target_points, variant=TRIAL_ID
    )
    candidate_bytes = (TRIAL_DIR / "candidate-heights.f32").read_bytes()
    candidate = np.frombuffer(candidate_bytes, dtype="<f4").copy()
    if (
        mesh.vertices_xz.astype("<f8", copy=False).tobytes(order="C")
        != (TRIAL_DIR / "patch-vertices-xz.f64").read_bytes()
    ):
        raise RuntimeError("reconstructed road-05 Float64 XZ buffer differs from retained topology")
    if (
        mesh.base_y.astype("<f4", copy=False).tobytes(order="C")
        != (TRIAL_DIR / "patch-base-heights.f32").read_bytes()
    ):
        raise RuntimeError(
            "reconstructed road-05 Float32 base buffer differs from retained topology"
        )
    if (
        mesh.triangles.astype("<u4", copy=False).tobytes(order="C")
        != (TRIAL_DIR / "patch-triangles.u32").read_bytes()
    ):
        raise RuntimeError("reconstructed road-05 triangle buffer differs from retained topology")
    candidate_hash = hashlib.sha256(candidate_bytes).hexdigest()
    if candidate_hash != solver.get("candidateFloat32Sha256"):
        raise RuntimeError("retained road-05 Float32 witness hash mismatch")
    if topology.get("trialId") != TRIAL_ID or topology.get("topologyVariant") != TRIAL_ID:
        raise RuntimeError("retained road-05 topology identity mismatch")
    if preview_hashes != attempt.get("acceptedPreviewHashes"):
        raise RuntimeError("accepted-preview hashes differ from road-05 attempt")
    if study_digest != attempt.get("studyConfigSha256"):
        raise RuntimeError("frozen study config differs from road-05 attempt")
    surface = patch.CompositeSurface(mesh, inputs, accepted, candidate)
    preparation_seconds = time.perf_counter() - preparation_started

    transition_preflight_started = time.perf_counter()
    current_map = _current_protected_map(runner_globals, inputs)
    transition_inputs = validate_transition_inputs(ROOT, current_map, config=config)
    prior_transitions = validate_prior_input_transition(
        RAW_ROOT,
        "collar-05",
        current_map,
        canonical_digest(current_map),
        config=config,
    )
    transition_input_preflight_seconds = time.perf_counter() - transition_preflight_started
    approval_check_seconds = _synthetic_approval_check_seconds(config, wrapper)

    context_started = time.perf_counter()
    context = ValidationContextV2(surface)
    context_seconds = time.perf_counter() - context_started
    validation_started = time.perf_counter()
    report, context = validate_offline_candidate_v2(
        surface,
        influence,
        constraints["rows"],
        solver,
        preview_hashes,
        context=context,
    )
    validation_seconds = time.perf_counter() - validation_started
    validation_with_context = context_seconds + validation_seconds

    road_report = report.get("roadPathReclip")
    conditional_assembly_profile: dict[str, Any] = {
        "available": False,
        "reason": "retained road-05 reclip did not produce valid candidate road groups",
        "passes": None,
    }
    if (
        isinstance(road_report, dict)
        and road_report.get("passes") is True
        and isinstance(road_report.get("groups"), dict)
    ):
        wrapper_state["post_solver_gates_active"] = True
        assembly_started = time.perf_counter()
        first_assets, second_assets, deterministic = runner_globals[
            "assemble_deterministic_candidate_assets"
        ](surface, road_report, report)
        first_validation = runner_globals["validate_candidate_patch_assets"](
            first_assets,
            surface,
            report["candidateFloat32Sha256"],
            road_report,
        )
        second_validation = runner_globals["validate_candidate_patch_assets"](
            second_assets,
            surface,
            report["candidateFloat32Sha256"],
            road_report,
        )
        resources = runner_globals["_resource_report"](
            mesh, road_report, first_assets, second_assets
        )
        asset_hashes = {
            "first": {
                name: runner_globals["_digest"](payload)
                for name, payload in sorted(first_assets.items())
            },
            "second": {
                name: runner_globals["_digest"](payload)
                for name, payload in sorted(second_assets.items())
            },
        }
        conditional_assembly_profile = {
            "available": True,
            "performanceOnly": True,
            "assemblyAndTwoIndependentValidationsResourceDeterminismHashSeconds": (
                time.perf_counter() - assembly_started
            ),
            "deterministic": bool(
                deterministic["passes"]
                and first_validation["passes"]
                and second_validation["passes"]
                and resources["passes"]
                and first_assets == second_assets
                and asset_hashes["first"] == asset_hashes["second"]
            ),
            "firstValidation": first_validation,
            "secondValidation": second_validation,
            "resourceLimits": resources,
            "independentAssetHashes": asset_hashes,
        }

    performance_harness_profile: dict[str, Any] = {
        "available": False,
        "performanceOnly": True,
        "candidateAcceptanceEvidence": False,
        "reason": "not run because exact retained road groups were available",
    }
    if not conditional_assembly_profile["available"]:
        try:
            harness = _performance_only_reclip_harness(surface, report)
            harness_started = time.perf_counter()
            first_assets, second_assets, deterministic = (
                patch.assemble_deterministic_candidate_assets(
                    surface, harness["roadReport"], harness["offlineReport"]
                )
            )
            internal_assembly_seconds = time.perf_counter() - harness_started
            external_started = time.perf_counter()
            first_validation = patch.validate_candidate_patch_assets(
                first_assets,
                surface,
                report["candidateFloat32Sha256"],
                harness["roadReport"],
            )
            second_validation = patch.validate_candidate_patch_assets(
                second_assets,
                surface,
                report["candidateFloat32Sha256"],
                harness["roadReport"],
            )
            resources = runner_globals["_resource_report"](
                mesh, harness["roadReport"], first_assets, second_assets
            )
            asset_hashes = {
                "first": {
                    name: runner_globals["_digest"](payload)
                    for name, payload in sorted(first_assets.items())
                },
                "second": {
                    name: runner_globals["_digest"](payload)
                    for name, payload in sorted(second_assets.items())
                },
            }
            external_validation_resource_determinism_seconds = (
                time.perf_counter() - external_started
            )
            performance_harness_profile = {
                "available": True,
                "performanceOnly": True,
                "candidateAcceptanceEvidence": False,
                "exactRoadReclipEquivalent": False,
                "syntheticOwnerMapping": harness["syntheticOwnerMapping"],
                "affectedRealSourceFaceCounts": harness["affectedSourceFaceCounts"],
                "assemblyAndInternalValidationsSeconds": internal_assembly_seconds,
                "externalTwoValidationsResourceAndDeterminismHashSeconds": (
                    external_validation_resource_determinism_seconds
                ),
                "totalConditionalPathSeconds": (
                    internal_assembly_seconds + external_validation_resource_determinism_seconds
                ),
                "deterministic": bool(
                    deterministic["passes"]
                    and first_validation["passes"]
                    and second_validation["passes"]
                    and first_assets == second_assets
                    and asset_hashes["first"] == asset_hashes["second"]
                ),
                "structuralAssetValidations": [first_validation, second_validation],
                "resourceReport": resources,
                "independentInMemoryAssetHashes": asset_hashes,
                "allOutputsDiscardedInMemory": True,
            }
        except Exception as exc:
            performance_harness_profile = {
                **performance_harness_profile,
                "reason": f"performance-only synthetic harness could not traverse: {exc}",
            }

    equivalent_names = list(patch.PATCH_OFFLINE_GATE_NAMES) + ["inputBindings", "solverWitness"]
    equivalence = {
        name: _serialized_equal(report.get(name), legacy.get(name)) for name in equivalent_names
    }
    equivalence["passes"] = report.get("passes") == legacy.get("passes")
    equivalence["gateNames"] = report.get("gateNames") == legacy.get("gateNames")
    equivalence["candidateFloat32Sha256"] = report.get("candidateFloat32Sha256") == legacy.get(
        "candidateFloat32Sha256"
    )
    finalization_snapshot_started = time.perf_counter()
    after_map = _current_protected_map(runner_globals, inputs)
    trial_code_hashes(ROOT)
    finalization_snapshot_seconds = time.perf_counter() - finalization_snapshot_started
    finalization_probe = {
        **report,
        "trialId": TRIAL_ID,
        "protectedHashesBefore": current_map,
        "protectedHashesAfter": after_map,
        "protectedHashesMatch": current_map == after_map,
        "trialElapsedSeconds": 0.0,
        "transitionInputState": transition_inputs,
        "trialCodeHashCount": len(trial_code_hashes(ROOT)),
    }
    runner_globals["_final_classification"](
        finalization_probe,
        report.get("topology"),
        solver,
        json.loads((TRIAL_DIR / "certificate-verification.json").read_text(encoding="utf-8")),
    )
    serialization_started = time.perf_counter()
    finalization_bytes = runner_globals["serialize_offline_report"](finalization_probe)
    transition_serialization_seconds = time.perf_counter() - serialization_started
    bounded_write_started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="teignmouth-v2-finalizer-profile-") as temporary:
        isolated_final_path = Path(temporary) / "offline-aggregate.json"
        runner_globals["_exclusive_write"](isolated_final_path, finalization_bytes)
        if isolated_final_path.read_bytes() != finalization_bytes:
            raise RuntimeError("isolated bounded finalizer write differs from serialized bytes")
    bounded_write_seconds = time.perf_counter() - bounded_write_started
    transition_finalization_seconds = (
        finalization_snapshot_seconds + transition_serialization_seconds + bounded_write_seconds
    )
    after = _tree_hashes(TRIAL_DIR)
    raw_unchanged = before == after

    pre_solver = float(solver["trialElapsedSecondsBeforeSolver"])
    solver_seconds = float(solver["elapsedSeconds"])
    finalization_residual = (
        RECORDED_TRIAL_SECONDS - pre_solver - solver_seconds - LEGACY_VALIDATION_SECONDS
    )
    extra_preflight_seconds = (
        static_preflight_seconds
        + transition_input_preflight_seconds
        + 3.0 * code_hash_pass_seconds
        + 4.0 * approval_check_seconds
    )
    complete_finalization_seconds = max(finalization_residual, transition_finalization_seconds)
    serialization_write_margin_seconds = 0.5
    projected_end_to_end_lower_bound = (
        pre_solver
        + solver_seconds
        + validation_with_context
        + extra_preflight_seconds
        + complete_finalization_seconds
        + serialization_write_margin_seconds
    )
    all_equivalent = all(equivalence.values())
    report_passes = bool(report.get("passes") == legacy.get("passes"))
    protected_maps_match = current_map == after_map
    protected_maps_pass = bool(protected_maps_match and transition_inputs.get("passed"))
    projected_end_to_end = (
        projected_end_to_end_lower_bound
        + conditional_assembly_profile[
            "assemblyAndTwoIndependentValidationsResourceDeterminismHashSeconds"
        ]
        if conditional_assembly_profile["available"]
        else None
    )
    qualification_limit = config["timing_policy"]["qualification_projected_end_to_end_seconds"]
    return {
        "transitionId": config["transition_id"],
        "validatorVersion": VALIDATOR_VERSION,
        "trialId": TRIAL_ID,
        "profileMode": "read-only retained witness; no solver invocation",
        "releaseId": inputs.release_id,
        "studyConfigSha256": study_digest,
        "acceptedPreviewHashes": preview_hashes,
        "candidateFloat32Sha256": candidate_hash,
        "retainedTopologyExact": True,
        "preparationSeconds": preparation_seconds,
        "transitionStaticPreflightSeconds": static_preflight_seconds,
        "transitionInputInventoryAndPriorMapValidationSeconds": transition_input_preflight_seconds,
        "transitionTrialCodeHashPassSeconds": code_hash_pass_seconds,
        "transitionSyntheticApprovalArtifactValidationSeconds": approval_check_seconds,
        "transitionFinalizationTotalSeconds": transition_finalization_seconds,
        "transitionFinalizationSnapshotSeconds": finalization_snapshot_seconds,
        "transitionFinalizationSerializationSeconds": transition_serialization_seconds,
        "transitionBoundedWriteProbeSeconds": bounded_write_seconds,
        "conditionalAssemblyProfile": conditional_assembly_profile,
        "performanceOnlyAssemblyHarness": performance_harness_profile,
        "transitionFinalizationProjectionSeconds": complete_finalization_seconds,
        "transitionSerializationAndWriteSafetyMarginSeconds": serialization_write_margin_seconds,
        "additionalPreflightProjectionSeconds": extra_preflight_seconds,
        "syntheticApprovalChainProfileOnly": True,
        "finalizationProbeByteLength": len(finalization_bytes),
        "wrapperStateKeys": sorted(wrapper_state),
        "contextSetupSeconds": context_seconds,
        "validationSeconds": validation_seconds,
        "validationWithContextSeconds": validation_with_context,
        "gateSeconds": context.gate_seconds,
        "cacheAndRejectionStats": context.stats,
        "cacheSizes": {
            "baselineCoarsePolygon": len(context.baseline_coarse_polygons),
            "acceptedCoarsePolygon": len(context.accepted_coarse_polygons),
            "patchFacePolygon": len(context.patch_face_polygons),
            "patchFaceBounds": len(context.patch_face_bounds),
            "triangleCoordinateArrayBytes": int(context.triangle_xz.nbytes),
            "triangleHeightArrayBytes": int(context.triangle_y.nbytes),
        },
        "reportByteEquivalentToRetainedRoad05": equivalence,
        "allTwelveGateReportsEquivalent": all(
            equivalence[name] for name in patch.PATCH_OFFLINE_GATE_NAMES
        ),
        "allReportIdentityFieldsEquivalent": all_equivalent,
        "aggregatePassFailPreserved": report_passes,
        "retainedRoad05OfflineGatePasses": report.get("passes"),
        "candidateOutputStillAbsent": not (
            ROOT / "public/worlds/torquay-road-surface-teignmouth-candidate"
        ).exists(),
        "protectedCurrentMapSha256": canonical_digest(current_map),
        "protectedMapBeforeSha256": canonical_digest(current_map),
        "protectedMapAfterSha256": canonical_digest(after_map),
        "protectedHashesBeforeAfterMatch": protected_maps_match,
        "protectedMapTransitionInputPass": transition_inputs.get("passed"),
        "protectedMapPasses": protected_maps_pass,
        "transitionInputValidation": transition_inputs,
        "consumedTrialTransitions": prior_transitions,
        "rawTrialDirectoryBefore": before,
        "rawTrialDirectoryAfter": after,
        "rawTrialDirectoryByteIdentical": raw_unchanged,
        "retainedAggregateSha256": file_digest(TRIAL_DIR / "offline-aggregate.json"),
        "historical": {
            "trialElapsedSeconds": RECORDED_TRIAL_SECONDS,
            "preSolverPreparationSeconds": pre_solver,
            "solverSeconds": solver_seconds,
            "legacyValidationProfileSeconds": LEGACY_VALIDATION_SECONDS,
            "finalizationAndOtherResidualSeconds": finalization_residual,
        },
        "projectedEndToEndLowerBoundSeconds": projected_end_to_end_lower_bound,
        "projectionIncludesConditionalAssemblyPath": conditional_assembly_profile["available"],
        "unmeasuredAcceptanceTimeBudgetSeconds": (
            None
            if conditional_assembly_profile["available"]
            else max(0.0, qualification_limit - projected_end_to_end_lower_bound)
        ),
        "projectedEndToEndSeconds": projected_end_to_end,
        "qualificationLimitSeconds": qualification_limit,
        "qualificationMarginSeconds": (
            qualification_limit - projected_end_to_end if projected_end_to_end is not None else None
        ),
        "qualifiesForNextTrialTiming": bool(
            projected_end_to_end is not None and projected_end_to_end <= qualification_limit
        ),
        "independentSolProfile": {"status": "pending", "requiredBeforeActivation": True},
        "passes": bool(all_equivalent and report_passes and raw_unchanged and protected_maps_pass),
    }


def main() -> int:
    from torquay_pipeline import road_surface

    output = ROOT / PROFILE_RELATIVE
    road_surface._assert_no_reparse_components(output.parent)
    if output.exists():
        raise RuntimeError(f"refusing to overwrite profile evidence: {output}")
    result = profile()
    payload = (json.dumps(result, sort_keys=True, indent=2) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    road_surface._assert_no_reparse_components(output.parent)
    with output.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"output": PROFILE_RELATIVE.as_posix(), **result}, sort_keys=True))
    return 0 if result["passes"] and result["qualifiesForNextTrialTiming"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
