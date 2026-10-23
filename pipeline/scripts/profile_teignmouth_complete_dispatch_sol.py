"""Timing-only replay of retained flip-05 through the complete traced v2 dispatch.

No trial, solver, activation, publisher or candidate file write is invoked. The
diagnostic trace deadline is deliberately separate from (and does not qualify)
the unchanged 120/125/135 trial policy. All package bytes remain in memory.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import platform
import runpy
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "pipeline/scripts"))

import numpy as np  # noqa: E402
import run_teignmouth_topology_validation_v2 as wrapper  # noqa: E402
import shapely  # noqa: E402

from torquay_pipeline import road_surface  # noqa: E402
from torquay_pipeline import road_surface_patch as patch  # noqa: E402
from torquay_pipeline.road_surface_validation_transition_v2 import file_digest  # noqa: E402
from torquay_pipeline.road_surface_validation_v2 import (  # noqa: E402
    validate_offline_candidate_v2,
)

EVIDENCE = ROOT / "docs/milestones/artifacts/Teignmouth-topology-validation-v2"
OUTPUT = EVIDENCE / "flip-05-complete-traced-profile-sol.json"
REPORT_OUTPUT = EVIDENCE / "flip-05-complete-traced-report-sol.json"
CONFIG = ROOT / "config/road-surface-teignmouth-topology-transition-v2.json"
BASE_CONFIG = ROOT / "config/road-surface-teignmouth-candidate.json"
RAW = ROOT / ".codex/evidence/teignmouth-topology-study"
LEGACY_PROFILE = EVIDENCE / "flip-05-performance-profile-fix4.json"
STUDY_RUNNER = ROOT / "pipeline/scripts/run_teignmouth_topology_study.py"
DIAGNOSTIC_TRACE_SECONDS = 1800.0


def _inventory(directory: Path) -> dict[str, Any]:
    road_surface._assert_no_reparse_components(directory)
    result = {}
    for path in sorted(directory.rglob("*")):
        road_surface._assert_no_reparse_components(path)
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = {
                "byteLength": path.stat().st_size,
                "sha256": file_digest(path),
            }
    return result


def _bytes(value: Any) -> bytes:
    return patch.serialize_offline_report(value)


def _write_once(path: Path, payload: bytes) -> None:
    if path not in (OUTPUT, REPORT_OUTPUT):
        raise RuntimeError("profile write is outside the exact output allowlist")
    road_surface._assert_no_reparse_components(path)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != payload:
        raise RuntimeError("profile output failed byte-exact readback")


def _project(components: dict[str, float]) -> dict[str, Any]:
    if any(not np.isfinite(value) or value < 0 for value in components.values()):
        raise ValueError("projection components must be finite nonnegative durations")
    return {
        "componentsSeconds": components,
        "sumSeconds": sum(components.values()),
        "classification": "retained-road-preparation-and-solver-plus-measured-flip-path-proxy",
        "actualCollarEndToEndMeasured": False,
        "qualifiesCurrentPolicy": False,
    }


def _source_identities(inputs: Any) -> dict[str, Any]:
    return {
        "dataSourceManifestPath": "data/source-manifest.json",
        "dataSourceManifestSha256": file_digest(ROOT / "data/source-manifest.json"),
        "releaseTerrainManifestSha256": inputs.source_hashes["manifest.json"]["sha256"],
        "legacyProfileFieldCorrection": {
            "path": LEGACY_PROFILE.relative_to(ROOT).as_posix(),
            "sha256": file_digest(LEGACY_PROFILE),
            "oldField": "inputIdentity.sourceManifestSha256",
            "actualMeaning": "release terrain manifest, not data/source-manifest.json",
            "oldProfilePreserved": True,
        },
    }


def main() -> int:
    profile_started = time.perf_counter()
    for path in (OUTPUT, REPORT_OUTPUT):
        road_surface._assert_no_reparse_components(path)
        if path.exists() or not path.parent.is_dir():
            raise RuntimeError("profile outputs must be absent with existing safe parent")
    candidate_path = ROOT / "public/worlds/torquay-road-surface-teignmouth-candidate"
    if candidate_path.exists():
        raise RuntimeError("candidate directory must remain absent")
    config = wrapper._read_config(CONFIG)
    wrapper._validate_static_bindings(config)
    if config["activation"]["enabled"] is not False:
        raise RuntimeError("v2 activation must remain disabled")
    runtime_before = wrapper._runtime_code_hashes(config, ROOT)
    script_hash = file_digest(Path(__file__).resolve())
    config_hash = file_digest(CONFIG)
    old_profile_hash = file_digest(LEGACY_PROFILE)
    raw_before = {name: _inventory(RAW / name) for name in ("flip-05", "road-05")}
    retained_solver = json.loads((RAW / "flip-05/solver-phase.json").read_bytes())
    retained_road = json.loads((RAW / "road-05/offline-aggregate.json").read_bytes())
    constraints = json.loads((RAW / "flip-05/constraints.json").read_bytes())["rows"]
    for row in constraints:
        row["indices"] = np.asarray(row["indices"], dtype=np.int64)
        row["coefficients"] = np.asarray(row["coefficients"], dtype=np.float64)
    runner = runpy.run_path(str(STUDY_RUNNER))
    namespace = runner["run_one_trial"].__globals__
    protected_snapshot = namespace["_protected_hash_snapshot"]
    frozen_snapshot = namespace["_frozen_study_input_hashes"]
    started = time.perf_counter()
    _config, inputs, accepted, preview_hashes = patch.load_candidate_inputs(ROOT, BASE_CONFIG)
    load_seconds = time.perf_counter() - started
    protected_before = {**protected_snapshot(ROOT, inputs), **frozen_snapshot(ROOT)}
    started = time.perf_counter()
    influence, bounds, target, _cumulative = patch._target_part_and_bounds(inputs)
    mesh = patch.build_topology_study_mesh(
        bounds, accepted, inputs, influence, target, variant="flip-05"
    )
    for name, payload in (
        ("patch-vertices-xz.f64", mesh.vertices_xz.astype("<f8").tobytes()),
        ("patch-base-heights.f32", mesh.base_y.astype("<f4").tobytes()),
        ("patch-triangles.u32", mesh.triangles.astype("<u4").tobytes()),
    ):
        if payload != (RAW / "flip-05" / name).read_bytes():
            raise RuntimeError(f"retained mesh reconstruction mismatch: {name}")
    witness = (RAW / "flip-05/candidate-heights.f32").read_bytes()
    if hashlib.sha256(witness).hexdigest() != retained_solver["candidateFloat32Sha256"]:
        raise RuntimeError("retained witness hash mismatch")
    surface = patch.CompositeSurface(mesh, inputs, accepted, np.frombuffer(witness, "<f4").copy())
    reconstruction_seconds = time.perf_counter() - started
    # A future diagnostic T0 gives the existing, UNCHANGED line-trace supervisor
    # room to measure completion. This is not a real trial or timing qualification.
    diagnostic_start = time.monotonic()
    state = wrapper._patch_runner(
        runner,
        config,
        invocation_start=diagnostic_start + DIAGNOSTIC_TRACE_SECONDS - 125.0,
    )
    started = time.perf_counter()
    traced_report = namespace["validate_offline_candidate"](
        surface, influence, constraints, retained_solver, preview_hashes
    )
    traced_seconds = time.perf_counter() - started
    traced_gate_seconds = traced_report["validationTransition"]["gateSeconds"]
    # Pair a direct complete replay with the supervised execution to measure the
    # actual elapsed difference, not 100 no-op calls. Order/cache bias is disclosed.
    started = time.perf_counter()
    direct_report, direct_context = validate_offline_candidate_v2(
        surface, influence, constraints, retained_solver, preview_hashes
    )
    direct_seconds = time.perf_counter() - started
    equal = {
        name: _bytes(traced_report[name]) == _bytes(direct_report[name])
        for name in patch.PATCH_OFFLINE_GATE_NAMES
    }
    full_validation = bool(
        traced_report.get("validationComplete")
        and direct_report.get("validationComplete")
        and all(equal.values())
    )
    assembly = {"available": False, "reason": "complete real clipping unavailable"}
    assembly_seconds = 0.0
    roads = traced_report.get("roadPathReclip", {})
    if full_validation and roads.get("passes") is True:
        # Exact flip report/roads, with synthetic TRUE flags solely to exercise
        # conditional serialization. Failed original gate results remain intact.
        synthetic = copy.deepcopy(traced_report)
        synthetic["passes"] = True
        for name in patch.PATCH_OFFLINE_GATE_NAMES:
            synthetic[name]["passes"] = True
        started = time.perf_counter()
        first, second, determinism = namespace["assemble_deterministic_candidate_assets"](
            surface, roads, synthetic
        )
        internal_seconds = time.perf_counter() - started
        started = time.perf_counter()
        validations = [
            namespace["validate_candidate_patch_assets"](
                assets, surface, traced_report["candidateFloat32Sha256"], roads
            )
            for assets in (first, second)
        ]
        resources = namespace["_resource_report"](mesh, roads, first, second)
        hashes = [
            {name: namespace["_digest"](payload) for name, payload in sorted(a.items())}
            for a in (first, second)
        ]
        external_seconds = time.perf_counter() - started
        assembly_seconds = internal_seconds + external_seconds
        assembly = {
            "available": True,
            "timingOnly": True,
            "syntheticGateFlags": True,
            "borrowedRoad05QA": False,
            "assetsWritten": False,
            "internalAssemblyValidationSeconds": internal_seconds,
            "externalValidationResourcesHashesSeconds": external_seconds,
            "structuralValidations": validations,
            "resources": resources,
            "determinism": determinism,
            "hashes": hashes,
        }
        del first, second, synthetic
    started = time.perf_counter()
    protected_after = {**protected_snapshot(ROOT, inputs), **frozen_snapshot(ROOT)}
    runtime_after = wrapper._runtime_code_hashes(config, ROOT)
    raw_after = {name: _inventory(RAW / name) for name in raw_before}
    if (
        protected_before != protected_after
        or runtime_before != runtime_after
        or raw_before != raw_after
        or file_digest(CONFIG) != config_hash
        or file_digest(LEGACY_PROFILE) != old_profile_hash
        or file_digest(Path(__file__).resolve()) != script_hash
        or candidate_path.exists()
    ):
        raise RuntimeError("read-only profile preservation check failed")
    preservation_seconds = time.perf_counter() - started
    identities = _source_identities(inputs)
    report_payload = _bytes(traced_report)
    started = time.perf_counter()
    _write_once(REPORT_OUTPUT, report_payload)
    report_finalization_seconds = time.perf_counter() - started
    retained_prepare = retained_road["solver"]["trialElapsedSecondsBeforeSolver"]
    retained_solve = retained_road["solver"]["elapsedSeconds"]
    components = {
        "retainedRoad05Preparation": retained_prepare,
        "retainedRoad05Solver": retained_solve,
        "measuredFlip05TracedCompleteValidationIncludingContext": traced_seconds,
        "measuredFlip05TracedConditionalAssembly": assembly_seconds,
        "measuredPreservationAndRuntimeRawHashChecks": preservation_seconds,
        "measuredCompleteReportWriteAndReadback": report_finalization_seconds,
    }
    profile = {
        "profileVersion": "flip-05-complete-traced-dispatch-sol-v1",
        "classification": "timing_only_no_gate_acceptance",
        "candidateAcceptanceEvidence": False,
        "solverInvoked": False,
        "trialInvoked": False,
        "activationEnabled": False,
        "candidateAssetsWritten": False,
        "currentPolicyUnchanged": True,
        "diagnosticTraceBudgetSeconds": DIAGNOSTIC_TRACE_SECONDS,
        "diagnosticShiftedT0IsNotTrialInvocation": True,
        "supervisorPolicyOffsetsUnchanged": wrapper._timing_record(state["deadlines"]),
        "supervisorTraceMetrics": state["trace_metrics"],
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "shapely": shapely.__version__,
            "geos": shapely.geos_version_string,
            "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS"),
        },
        "scriptSha256": script_hash,
        "configSha256BeforeAndAfter": config_hash,
        "runtimeHashesBefore": runtime_before,
        "runtimeHashesAfter": runtime_after,
        "inputIdentity": identities,
        "protectedBefore": protected_before,
        "protectedAfter": protected_after,
        "rawBefore": raw_before,
        "rawAfter": raw_after,
        "candidateOutputAbsentBeforeAndAfter": True,
        "completeReportPath": REPORT_OUTPUT.relative_to(ROOT).as_posix(),
        "completeReportSha256": hashlib.sha256(report_payload).hexdigest(),
        "completeDispatchMeasured": full_validation,
        "reportByteEquivalence": equal,
        "measuredTimings": {
            "sourceLoadingSeconds": load_seconds,
            "flipTopologyReconstructionSeconds": reconstruction_seconds,
            "tracedDispatchIncludingContextSeconds": traced_seconds,
            "directDispatchIncludingContextSeconds": direct_seconds,
            "pairedElapsedTracingDifferenceSeconds": traced_seconds - direct_seconds,
            "tracedGateSeconds": traced_gate_seconds,
            "directGateSeconds": direct_context.gate_seconds,
            "tracedContextAndDispatchOverheadSeconds": traced_seconds
            - sum(traced_gate_seconds.values()),
            "preservationSeconds": preservation_seconds,
        },
        "timingOnlyConditionalAssembly": assembly,
        "projection": _project(components),
        "capRecommendation": None,
        "unmeasured": [
            "actual collar-05 topology/preparation and solver duration",
            "actual collar-05 validation, clipping, assembly and geometry sizes",
            "production activation receipt preflight (activation remains disabled)",
            "trial finalization payload/fsync cost; measured profile report is only a proxy",
            "native-call preemption; line tracer cannot interrupt GEOS/NumPy mid-call",
        ],
        "limitations": [
            "No-op dispatch timings are not substituted for complete tracing.",
            "Paired trace difference includes run order, cache and host-load effects.",
            "Conditional assembly uses synthetic pass flags and is not acceptance evidence.",
            "Projection is a mixed retained/measured proxy, not a complete actual collar trial.",
        ],
    }
    profile["profileElapsedBeforeFinalRecordSeconds"] = time.perf_counter() - profile_started
    _write_once(OUTPUT, _bytes(profile))
    print(
        json.dumps(
            {
                "path": OUTPUT.relative_to(ROOT).as_posix(),
                "sha256": file_digest(OUTPUT),
                "completeDispatchMeasured": full_validation,
                "tracedSeconds": traced_seconds,
                "directSeconds": direct_seconds,
                "proxySeconds": profile["projection"]["sumSeconds"],
                "capRecommendation": None,
            },
            sort_keys=True,
        )
    )
    return 0 if full_validation else 2


if __name__ == "__main__":
    raise SystemExit(main())
