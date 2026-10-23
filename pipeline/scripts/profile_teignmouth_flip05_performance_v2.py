"""Read-only performance profile for the consumed flip-05 witness.

The script reconstructs retained source/topology/Float32 bytes, runs the real
road/path clipping code, and assembles/validates package bytes in memory. It
does not run a solver, validate candidate acceptance, or write trial/candidate
assets. It writes one write-once JSON performance record only after protected
and consumed-trial identities match before and after the profile.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import runpy
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "pipeline/scripts"))

from torquay_pipeline import road_surface  # noqa: E402
from torquay_pipeline import road_surface_patch as patch  # noqa: E402
from torquay_pipeline.road_surface_validation_transition_v2 import (  # noqa: E402
    canonical_digest,
    file_digest,
)

TRIAL_ID = "flip-05"
RAW_ROOT = ROOT / ".codex/evidence/teignmouth-topology-study"
TRIAL_DIR = RAW_ROOT / TRIAL_ID
ROAD_TRIAL_DIR = RAW_ROOT / "road-05"
CONFIG_PATH = ROOT / "config/road-surface-teignmouth-topology-transition-v2.json"
BASE_CONFIG_PATH = ROOT / "config/road-surface-teignmouth-candidate.json"
STUDY_RUNNER_PATH = ROOT / "pipeline/scripts/run_teignmouth_topology_study.py"
OUTPUT_RELATIVE = Path(
    "docs/milestones/artifacts/Teignmouth-topology-validation-v2/"
    "flip-05-performance-profile-fix4.json"
)
EXPECTED_OUTPUT = ROOT / OUTPUT_RELATIVE


def _file_inventory(path: Path) -> dict[str, dict[str, Any]]:
    return {
        child.relative_to(path).as_posix(): {
            "sha256": file_digest(child),
            "byteLength": child.stat().st_size,
        }
        for child in sorted(path.rglob("*"))
        if child.is_file()
    }


def _protected_map(runner_globals: dict[str, Any], inputs: Any) -> dict[str, str]:
    return {
        **runner_globals["_protected_hash_snapshot"](ROOT, inputs),
        **runner_globals["_frozen_study_input_hashes"](ROOT),
    }


def _profile() -> dict[str, Any]:
    import run_teignmouth_topology_validation_v2 as wrapper

    if EXPECTED_OUTPUT != (ROOT / OUTPUT_RELATIVE) or OUTPUT_RELATIVE.is_absolute():
        raise RuntimeError("profile output path is not the fixed evidence location")
    road_surface._assert_no_reparse_components(EXPECTED_OUTPUT.parent)
    road_surface._assert_no_reparse_components(EXPECTED_OUTPUT)
    if not EXPECTED_OUTPUT.parent.is_dir() or EXPECTED_OUTPUT.exists():
        raise RuntimeError(
            "profile output directory is missing or write-once record already exists"
        )
    if not TRIAL_DIR.is_dir() or not ROAD_TRIAL_DIR.is_dir():
        raise RuntimeError("both consumed trial directories must remain present")
    if (ROOT / "public/worlds/torquay-road-surface-teignmouth-candidate").exists():
        raise RuntimeError("candidate output must remain absent for this read-only profile")

    config = wrapper._read_config(CONFIG_PATH)
    wrapper._validate_static_bindings(config)
    if config.get("activation", {}).get("enabled") is not False:
        raise RuntimeError("validation transition must remain disabled during this profile")

    trial_before = _file_inventory(TRIAL_DIR)
    road_before = _file_inventory(ROAD_TRIAL_DIR)
    attempt = json.loads((TRIAL_DIR / "attempt.json").read_text(encoding="utf-8"))
    topology = json.loads((TRIAL_DIR / "topology.json").read_text(encoding="utf-8"))
    solver = json.loads((TRIAL_DIR / "solver-phase.json").read_text(encoding="utf-8"))
    retained_aggregate = json.loads(
        (TRIAL_DIR / "offline-aggregate.json").read_text(encoding="utf-8")
    )
    road_aggregate = json.loads(
        (ROAD_TRIAL_DIR / "offline-aggregate.json").read_text(encoding="utf-8")
    )

    for relative, expected in attempt["codeHashes"].items():
        actual = file_digest(ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"retained flip-05 code input changed: {relative}")

    runner = runpy.run_path(str(STUDY_RUNNER_PATH))
    runner_globals = runner["run_one_trial"].__globals__
    _source_config, inputs, accepted, accepted_preview_hashes = patch.load_candidate_inputs(
        ROOT, BASE_CONFIG_PATH
    )
    protected_before = _protected_map(runner_globals, inputs)
    current_runtime_hashes = wrapper._runtime_code_hashes(config, ROOT)

    construction_started = time.perf_counter()
    influence, bounds, target_points, _cumulative = patch._target_part_and_bounds(inputs)
    mesh = patch.build_topology_study_mesh(
        bounds,
        accepted,
        inputs,
        influence,
        target_points,
        variant=TRIAL_ID,
    )
    candidate_bytes = (TRIAL_DIR / "candidate-heights.f32").read_bytes()
    candidate = np.frombuffer(candidate_bytes, dtype="<f4").copy()
    reconstruction_matches = {
        "topologyXzBytes": (
            mesh.vertices_xz.astype("<f8", copy=False).tobytes(order="C")
            == (TRIAL_DIR / "patch-vertices-xz.f64").read_bytes()
        ),
        "topologyBaseHeightBytes": (
            mesh.base_y.astype("<f4", copy=False).tobytes(order="C")
            == (TRIAL_DIR / "patch-base-heights.f32").read_bytes()
        ),
        "topologyTriangleBytes": (
            mesh.triangles.astype("<u4", copy=False).tobytes(order="C")
            == (TRIAL_DIR / "patch-triangles.u32").read_bytes()
        ),
        "candidateWitnessHash": (
            hashlib.sha256(candidate_bytes).hexdigest() == solver.get("candidateFloat32Sha256")
        ),
        "acceptedPreviewIdentity": accepted_preview_hashes == attempt.get("acceptedPreviewHashes"),
        "topologyIdentity": topology.get("trialId") == TRIAL_ID
        and topology.get("topologyVariant") == TRIAL_ID,
    }
    if not all(reconstruction_matches.values()):
        raise RuntimeError(f"retained flip-05 reconstruction mismatch: {reconstruction_matches}")
    surface = patch.CompositeSurface(mesh, inputs, accepted, candidate)
    reconstruction_seconds = time.perf_counter() - construction_started
    candidate_hash = hashlib.sha256(candidate_bytes).hexdigest()

    reclip_started = time.perf_counter()
    clipped = patch.reclip_affected_road_batches(surface)
    reclip_seconds = time.perf_counter() - reclip_started
    if clipped.get("passes") is not True:
        raise RuntimeError("retained flip-05 real road/path clipping did not pass")

    # The consumed flip trial never completed offline validation. These copied
    # road-05 fields and true flags exist only to exercise the package serializer;
    # they are explicitly non-acceptance performance inputs.
    assembly_report = copy.deepcopy(road_aggregate)
    assembly_report["passes"] = True
    assembly_report["gateNames"] = list(patch.PATCH_OFFLINE_GATE_NAMES)
    assembly_report["candidateFloat32Sha256"] = candidate_hash
    assembly_report["roadPathReclip"] = clipped
    for gate_name in patch.PATCH_OFFLINE_GATE_NAMES:
        gate = assembly_report.get(gate_name)
        if not isinstance(gate, dict):
            assembly_report[gate_name] = {"passes": True}
        else:
            gate["passes"] = True

    assembly_started = time.perf_counter()
    first_assets, second_assets, deterministic = patch.assemble_deterministic_candidate_assets(
        surface, clipped, assembly_report
    )
    assembly_and_internal_validation_seconds = time.perf_counter() - assembly_started

    from run_teignmouth_topology_study import _resource_report

    external_started = time.perf_counter()
    first_validation = patch.validate_candidate_patch_assets(
        first_assets, surface, candidate_hash, clipped
    )
    second_validation = patch.validate_candidate_patch_assets(
        second_assets, surface, candidate_hash, clipped
    )
    resources = _resource_report(mesh, clipped, first_assets, second_assets)
    first_hashes = {
        name: hashlib.sha256(payload).hexdigest() for name, payload in sorted(first_assets.items())
    }
    second_hashes = {
        name: hashlib.sha256(payload).hexdigest() for name, payload in sorted(second_assets.items())
    }
    hashes_equal = first_hashes == second_hashes and first_assets == second_assets
    external_validation_resource_determinism_seconds = time.perf_counter() - external_started
    if not (
        deterministic.get("passes") is True
        and first_validation.get("passes") is True
        and second_validation.get("passes") is True
        and resources.get("passes") is True
        and hashes_equal
    ):
        raise RuntimeError(
            "performance-only in-memory package path did not validate deterministically"
        )

    # Measure trace-supervisor dispatch cost separately from the real clipping
    # and assembly work. This is not a measure of tracing the full validator.
    supervisor_started = time.perf_counter()
    for _ in range(100):
        supervisor_t0 = time.monotonic()
        wrapper._run_validation_phase(
            lambda: None,
            (),
            {},
            deadlines=wrapper.TransitionDeadlines(invocation_start=supervisor_t0),
            clock=time.monotonic,
            label="profile-noop-supervisor-overhead",
        )
    supervisor_dispatch_100_seconds = time.perf_counter() - supervisor_started

    protected_after = _protected_map(runner_globals, inputs)
    runtime_hashes_after = wrapper._runtime_code_hashes(config, ROOT)
    trial_after = _file_inventory(TRIAL_DIR)
    road_after = _file_inventory(ROAD_TRIAL_DIR)
    candidate_output = ROOT / "public/worlds/torquay-road-surface-teignmouth-candidate"
    if protected_before != protected_after:
        raise RuntimeError("protected input map changed during performance-only profile")
    if current_runtime_hashes != runtime_hashes_after:
        raise RuntimeError("runtime code hash map changed during performance-only profile")
    if trial_before != trial_after or road_before != road_after:
        raise RuntimeError("consumed trial bytes changed during performance-only profile")
    if candidate_output.exists():
        raise RuntimeError("candidate output appeared during performance-only profile")

    group_summary = {
        name: {
            key: group.get(key)
            for key in (
                "affectedSourceFaceCount",
                "replacementFaceCount",
                "replacementVertexCount",
                "affectedSourceAreaM2",
                "replacementHorizontalAreaM2",
                "float32FootprintCoverageErrorM2",
                "maximumOwnerTriangleBarycentricViolation",
                "maximumRoadDrapeErrorM",
                "passes",
            )
        }
        for name, group in clipped["groups"].items()
    }
    assets_summary = {
        "assetCount": len(first_assets),
        "totalByteLength": sum(map(len, first_assets.values())),
        "firstHashes": first_hashes,
        "secondHashes": second_hashes,
        "hashesEqual": hashes_equal,
        "firstValidation": first_validation,
        "secondValidation": second_validation,
        "resourceLimitsPerformanceReport": resources,
    }
    return {
        "profileVersion": "flip-05-read-only-performance-v1",
        "classification": "timing_only_no_gate_acceptance",
        "candidateAcceptanceEvidence": False,
        "solverInvoked": False,
        "offlineAcceptanceValidationRun": False,
        "activationEnabled": False,
        "trialId": TRIAL_ID,
        "retainedTrialResult": {
            "finalClassification": retained_aggregate.get("finalClassification"),
            "passes": retained_aggregate.get("passes"),
            "solverConverged": solver.get("converged"),
            "solverIterations": solver.get("iterations"),
            "solverResidualM": solver.get("maximumConstraintResidualM"),
            "candidateFloat32Sha256": candidate_hash,
        },
        "inputIdentity": {
            "releaseId": inputs.release_id,
            "acceptedPreviewHashes": accepted_preview_hashes,
            "studyConfigSha256": attempt.get("studyConfigSha256"),
            "sourceManifestSha256": inputs.source_hashes.get("manifest.json", {}).get("sha256"),
            "candidateOutputAbsentBeforeAndAfter": True,
            "reconstructedTopologyChecks": reconstruction_matches,
            "runtimeCodeHashesSha256Before": canonical_digest(current_runtime_hashes),
            "runtimeCodeHashesSha256After": canonical_digest(runtime_hashes_after),
        },
        "rawInputIdentity": {
            "flip05FilesBefore": trial_before,
            "flip05FilesAfter": trial_after,
            "flip05BeforeSha256": canonical_digest(trial_before),
            "flip05AfterSha256": canonical_digest(trial_after),
            "road05FilesBefore": road_before,
            "road05FilesAfter": road_after,
            "road05BeforeSha256": canonical_digest(road_before),
            "road05AfterSha256": canonical_digest(road_after),
            "bothConsumedDirectoriesByteIdentical": True,
        },
        "protectedInputIdentity": {
            "before": protected_before,
            "after": protected_after,
            "beforeSha256": canonical_digest(protected_before),
            "afterSha256": canonical_digest(protected_after),
            "mapsIdentical": True,
        },
        "performanceOnlyReclip": {
            "passes": True,
            "elapsedSeconds": reclip_seconds,
            "affectedSourceAreaM2": clipped.get("affectedSourceAreaM2"),
            "replacementHorizontalAreaM2": clipped.get("replacementHorizontalAreaM2"),
            "float32HorizontalAreaDriftM2": clipped.get("float32HorizontalAreaDriftM2"),
            "float32FootprintCoverageErrorM2": clipped.get("float32FootprintCoverageErrorM2"),
            "float32OmittedAreaM2": clipped.get("float32OmittedAreaM2"),
            "quantizationSafeSharedEdgeAdjustmentCount": clipped.get(
                "quantizationSafeSharedEdgeAdjustmentCount"
            ),
            "groups": group_summary,
            "resourceReport": clipped.get("resourceReport"),
        },
        "performanceOnlyAssembly": {
            "elapsedAssemblyAndInternalValidationSeconds": (
                assembly_and_internal_validation_seconds
            ),
            "elapsedExternalValidationResourceDeterminismSeconds": (
                external_validation_resource_determinism_seconds
            ),
            "elapsedConditionalPathSeconds": (
                assembly_and_internal_validation_seconds
                + external_validation_resource_determinism_seconds
            ),
            "syntheticGateFlagsUsedToEnterAssembler": True,
            "qaValuesBorrowedFromRoad05AndNotValidatedForFlip05": True,
            "assetOutputsWritten": False,
            **assets_summary,
        },
        "supervisorDispatchOverhead": {
            "classification": "100 no-op calls through the real bounded trace wrapper",
            "elapsed100CallsSeconds": supervisor_dispatch_100_seconds,
            "meanCallSeconds": supervisor_dispatch_100_seconds / 100.0,
            "fullValidatorTracingOverheadMeasured": False,
        },
        "timings": {
            "topologyAndInputReconstructionSeconds": reconstruction_seconds,
            "realRoadReclipSeconds": reclip_seconds,
            "assemblyAndInternalValidationSeconds": assembly_and_internal_validation_seconds,
            "externalValidationResourceDeterminismSeconds": (
                external_validation_resource_determinism_seconds
            ),
            "supervisorDispatch100NoopCallsSeconds": supervisor_dispatch_100_seconds,
            "totalProfileSeconds": (
                reconstruction_seconds
                + reclip_seconds
                + assembly_and_internal_validation_seconds
                + external_validation_resource_determinism_seconds
                + supervisor_dispatch_100_seconds
            ),
        },
        "limitations": [
            "The retained flip-05 solver did not converge and has no complete offline "
            "acceptance report.",
            "This profile is not a solver trial, offline gate pass, or candidate "
            "acceptance result.",
            "The assembler received performance-only synthetic gate flags and road-05 "
            "QA values; only topology/witness identity, real clipped road groups, "
            "package structure, serialized bytes, and timing were exercised.",
        ],
    }


def main() -> int:
    profile = _profile()
    payload = (
        json.dumps(profile, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False).encode(
            "utf-8"
        )
        + b"\n"
    )
    road_surface._assert_no_reparse_components(EXPECTED_OUTPUT)
    with EXPECTED_OUTPUT.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    if EXPECTED_OUTPUT.read_bytes() != payload:
        raise RuntimeError("write-once profile record did not round-trip byte-for-byte")
    print(
        json.dumps(
            {
                "path": OUTPUT_RELATIVE.as_posix(),
                "byteLength": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "classification": profile["classification"],
                "elapsedConditionalPathSeconds": profile["timings"]["realRoadReclipSeconds"]
                + profile["timings"]["assemblyAndInternalValidationSeconds"]
                + profile["timings"]["externalValidationResourceDeterminismSeconds"],
                "candidateAcceptanceEvidence": profile["candidateAcceptanceEvidence"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
