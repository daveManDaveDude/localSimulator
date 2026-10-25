"""Opt-in runner for the reviewed Teignmouth validation transition v2.

The transition remains disabled until the coordinator records independent Sol
approval in its config. This wrapper never edits the frozen study runner.
"""

from __future__ import annotations

import argparse
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

from torquay_pipeline import road_surface  # noqa: E402
from torquay_pipeline.road_surface_patch import (  # noqa: E402
    PATCH_OFFLINE_GATE_NAMES,
    RoadSurfacePatchError,
)
from torquay_pipeline.road_surface_study_reconciliation import (  # noqa: E402
    validate_reconciled_stage_order,
)
from torquay_pipeline.road_surface_validation_process_v1 import (  # noqa: E402
    ProcessValidationError,
    supervise,
)
from torquay_pipeline.road_surface_validation_transition_v2 import (  # noqa: E402
    ELIGIBLE_TRIALS,
    FINALIZATION_CUTOFF_SECONDS,
    FINALIZATION_RESERVE_SECONDS,
    MAXIMUM_ITERATIONS,
    PREPARATION_SOLVER_SECONDS,
    QUALIFICATION_SECONDS,
    TRANSITION_ID,
    VALIDATION_CUTOFF_SECONDS,
    TransitionDeadlineExceeded,
    TransitionDeadlines,
    admit_remaining_trial,
    canonical_digest,
    file_digest,
    phase_for_runner_check,
    validate_prior_input_transition,
    validate_transition_inputs,
)

CONFIG_PATH = ROOT / "config/road-surface-teignmouth-topology-transition-v2.json"
STUDY_CONFIG_PATH = ROOT / "config/road-surface-teignmouth-topology-study.json"
BASE_CONFIG_PATH = ROOT / "config/road-surface-teignmouth-candidate.json"
STUDY_RUNNER_PATH = ROOT / "pipeline/scripts/run_teignmouth_topology_study.py"
RECONCILIATION_CODE_PATHS = (
    "pipeline/torquay_pipeline/road_surface_study_reconciliation.py",
    "pipeline/scripts/run_teignmouth_topology_after_reconciliation.py",
    "pipeline/tests/test_road_surface_study_reconciliation.py",
)
EXTENSION_CODE_PATHS = (
    "config/road-surface-teignmouth-topology-transition-v2.json",
    "docs/milestones/Teignmouth-topology-validation-v2-spec.md",
    "pipeline/torquay_pipeline/road_surface_validation_transition_v2.py",
    "pipeline/torquay_pipeline/road_surface_validation_v2.py",
    "pipeline/torquay_pipeline/road_surface_validation_v1.py",
    "pipeline/scripts/run_teignmouth_topology_validation_v2.py",
    "pipeline/scripts/profile_teignmouth_validation_v2.py",
    "pipeline/scripts/profile_teignmouth_flip05_performance_v2.py",
    "pipeline/tests/test_road_surface_validation_transition_v2.py",
    "pipeline/tests/test_road_surface_validation_v2.py",
    "pipeline/scripts/profile_teignmouth_complete_dispatch_sol.py",
    "pipeline/scripts/profile_teignmouth_complete_dispatch_sol_optimized.py",
    "pipeline/scripts/profile_teignmouth_complete_dispatch_sol_all_codes.py",
    "pipeline/scripts/profile_teignmouth_frame_selected_sol.py",
    "pipeline/tests/test_teignmouth_complete_profile.py",
    "pipeline/tests/test_teignmouth_cached_supervisor.py",
    "pipeline/torquay_pipeline/road_surface_validation_process_v1.py",
    "pipeline/scripts/run_teignmouth_validation_worker_v1.py",
    "pipeline/scripts/profile_teignmouth_process_validation_v1.py",
    "pipeline/tests/test_teignmouth_validation_process.py",
    "docs/milestones/Teignmouth-process-validation.md",
)

APPROVAL_ROOT = "docs/milestones/artifacts/Teignmouth-topology-validation-v2"
SOL_REVIEW_PATH = f"{APPROVAL_ROOT}/independent-sol-review.json"
COORDINATOR_RECEIPT_PATH = f"{APPROVAL_ROOT}/coordinator-acceptance.json"
ACCEPTED_CHECKPOINT_PREFIX = "TEIGNMOUTH_VALIDATION_V2_ACCEPTED receipt_sha256="
PENDING_CHECKPOINT_MARKER = "TEIGNMOUTH_VALIDATION_V2_REVIEW_PENDING"
EXPECTED_TIMING_POLICY = {
    "automatic_limit_escalation": False,
    "finalization_cutoff_seconds": FINALIZATION_CUTOFF_SECONDS,
    "finalization_window_seconds": FINALIZATION_RESERVE_SECONDS,
    "finalization_window_for": [
        "protected-input after-snapshot",
        "serialization",
        "aggregate write",
    ],
    "invocation_clock": "monotonic T0 captured before per-trial preparation",
    "maximum_iterations": MAXIMUM_ITERATIONS,
    "preparation_and_solver_deadline_seconds": PREPARATION_SOLVER_SECONDS,
    "qualification_projected_end_to_end_seconds": QUALIFICATION_SECONDS,
    "retry_allowed": False,
    "timeout_consumes_write_once_trial": True,
    "validation_cutoff_seconds": VALIDATION_CUTOFF_SECONDS,
    "validation_includes_assembly_and_resource_determinism": True,
}


def _read_config(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoadSurfacePatchError(f"transition config is unreadable: {exc}") from exc
    if not isinstance(value, dict):
        raise RoadSurfacePatchError("transition config must be a JSON object")
    return value


def _read_json_object(path: Path, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoadSurfacePatchError(f"{description} is missing or invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise RoadSurfacePatchError(f"{description} must be a JSON object")
    return value


def _runtime_code_hashes(config: dict[str, Any], root: Path = ROOT) -> dict[str, str]:
    """Return the exact legacy plus extension implementation map, excluding config self-hash."""
    legacy = config.get("legacy_road05_code_hashes")
    extension = config.get("extension_code_hashes")
    if not isinstance(legacy, dict) or not isinstance(extension, dict):
        raise RoadSurfacePatchError("runtime code hash bindings are malformed")
    runtime = {str(path): str(digest) for path, digest in legacy.items()}
    for path, digest in extension.items():
        if path in runtime and runtime[path] != digest:
            raise RoadSurfacePatchError(f"conflicting runtime code hash binding: {path}")
        runtime[str(path)] = str(digest)
    runtime.pop("config/road-surface-teignmouth-topology-transition-v2.json", None)
    for relative, expected in runtime.items():
        path = root / relative
        road_surface._assert_no_reparse_components(path)
        if not path.is_file() or file_digest(path) != expected:
            raise RoadSurfacePatchError(f"runtime code binding changed: {relative}")
    return dict(sorted(runtime.items()))


def _approval_payload(config: dict[str, Any], config_path: Path, root: Path) -> dict[str, Any]:
    pins = config["pinned_inputs"]
    runtime_hashes = _runtime_code_hashes(config, root)
    return {
        "transition_id": TRANSITION_ID,
        "config_path": config_path.relative_to(root).as_posix(),
        "config_sha256": file_digest(config_path),
        "spec_path": pins["transition_spec_path"],
        "spec_sha256": pins["transition_spec_sha256"],
        "runtime_code_hashes": runtime_hashes,
        "runtime_code_sha256": canonical_digest(runtime_hashes),
    }


def ensure_transition_activated(
    config: dict[str, Any], *, root: Path = ROOT, config_path: Path = CONFIG_PATH
) -> None:
    """Require real, exact Sol and coordinator artifacts before an enabled run."""
    _validate_fixed_policy(config)
    if config_path.resolve().relative_to(root.resolve()).as_posix() != (
        "config/road-surface-teignmouth-topology-transition-v2.json"
    ):
        raise RoadSurfacePatchError("approval chain config path is not the exact transition config")
    activation = config.get("activation")
    if activation == {
        "enabled": False,
        "status": "pending_independent_sol_review_and_coordinator_approval",
    }:
        raise RoadSurfacePatchError(
            "validation transition v2 is disabled pending exact Sol review and coordinator receipt"
        )
    if activation != {"enabled": True, "status": "approval_chain_required"}:
        raise RoadSurfacePatchError("transition activation state is not an approved exact state")
    chain = config.get("approval_chain")
    if not isinstance(chain, dict) or chain != {
        "coordinator_receipt_path": COORDINATOR_RECEIPT_PATH,
        "independent_sol_review_path": SOL_REVIEW_PATH,
        "accepted_checkpoint_marker_prefix": ACCEPTED_CHECKPOINT_PREFIX,
        "review_disposition": "PASS",
        "coordinator_disposition": "ACCEPTED",
    }:
        raise RoadSurfacePatchError(
            "transition approval-chain policy differs from the fixed policy"
        )

    expected_payload = _approval_payload(config, config_path, root)
    review_path = root / SOL_REVIEW_PATH
    receipt_path = root / COORDINATOR_RECEIPT_PATH
    for path, description in (
        (review_path, "independent Sol review artifact"),
        (receipt_path, "coordinator acceptance receipt"),
    ):
        road_surface._assert_no_reparse_components(path)
        if not path.is_file() or path.is_symlink():
            raise RoadSurfacePatchError(f"{description} is missing or unsafe: {path}")
    review = _read_json_object(review_path, "independent Sol review")
    expected_review = {
        "schema": "teignmouth-validation-v2-sol-review-v1",
        "reviewer": "Sol 6.1",
        "disposition": "PASS",
        **expected_payload,
    }
    if review != expected_review:
        raise RoadSurfacePatchError(
            "independent Sol review does not approve the exact config, spec and runtime code map"
        )
    review_digest = file_digest(review_path)
    receipt = _read_json_object(receipt_path, "coordinator acceptance receipt")
    expected_receipt = {
        "schema": "teignmouth-validation-v2-coordinator-acceptance-v1",
        "disposition": "ACCEPTED",
        **expected_payload,
        "independent_sol_review_path": SOL_REVIEW_PATH,
        "independent_sol_review_sha256": review_digest,
    }
    if receipt != expected_receipt:
        raise RoadSurfacePatchError(
            "coordinator receipt does not bind the exact reviewed config and implementation"
        )
    checkpoint = root / config["input_state_transition"]["checkpoint_path"]
    road_surface._assert_no_reparse_components(checkpoint)
    if checkpoint.is_symlink() or not checkpoint.is_file():
        raise RoadSurfacePatchError("coordinator checkpoint is missing or unsafe")
    receipt_marker = ACCEPTED_CHECKPOINT_PREFIX + file_digest(receipt_path)
    checkpoint_text = checkpoint.read_text(encoding="utf-8")
    if (
        checkpoint_text.count(receipt_marker) != 1
        or checkpoint_text.count(ACCEPTED_CHECKPOINT_PREFIX) != 1
        or PENDING_CHECKPOINT_MARKER in checkpoint_text
    ):
        raise RoadSurfacePatchError(
            "coordinator checkpoint does not bind exactly one accepted receipt"
        )


def _assert_exact_config_path(path: Path) -> Path:
    requested = path if path.is_absolute() else ROOT / path
    try:
        expected = CONFIG_PATH.resolve(strict=True)
        actual = requested.resolve(strict=True)
    except OSError as exc:
        raise RoadSurfacePatchError(f"transition config path is unavailable: {exc}") from exc
    if os.path.normcase(str(actual)) != os.path.normcase(str(expected)):
        raise RoadSurfacePatchError("--transition-config must name the exact v2 config")
    return actual


def _validate_static_bindings(config: dict[str, Any]) -> None:
    _validate_fixed_policy(config)
    pins = config["pinned_inputs"]
    expected = {
        pins["study_config_path"]: pins["study_config_sha256"],
        pins["base_candidate_config_path"]: pins["base_candidate_config_sha256"],
        pins["study_spec_path"]: pins["study_spec_sha256"],
        pins["transition_spec_path"]: pins["transition_spec_sha256"],
    }
    for relative, digest in expected.items():
        path = ROOT / relative
        if not path.is_file() or file_digest(path) != digest:
            raise RoadSurfacePatchError(f"pinned transition input changed: {relative}")
    if tuple(config.get("eligible_trial_ids", ())) != ELIGIBLE_TRIALS:
        raise RoadSurfacePatchError("transition eligibility differs from the fixed allowlist")
    if tuple(config.get("consumed_trial_ids", ())) != ("flip-05", "road-05"):
        raise RoadSurfacePatchError("transition consumed-trial denylist changed")
    if tuple(config.get("extension_code_paths", ())) != EXTENSION_CODE_PATHS:
        raise RoadSurfacePatchError("transition extension code-hash allowlist changed")
    expected_extension_hashes = set(EXTENSION_CODE_PATHS) - {
        "config/road-surface-teignmouth-topology-transition-v2.json"
    }
    if set(config.get("extension_code_hashes", {})) != expected_extension_hashes:
        raise RoadSurfacePatchError(
            "transition extension code-hash map is incomplete or unexpected"
        )
    for relative, expected_digest in config.get("extension_code_hashes", {}).items():
        path = ROOT / relative
        if not path.is_file() or file_digest(path) != expected_digest:
            raise RoadSurfacePatchError(f"transition extension code changed: {relative}")
    if set(config.get("legacy_road05_code_hashes", {})) != set(
        config.get("legacy_flip05_code_hashes", {})
    ) | set(RECONCILIATION_CODE_PATHS):
        raise RoadSurfacePatchError(
            "legacy flip/road code maps are not the approved extension pair"
        )
    expected_runtime = set(config["legacy_road05_code_hashes"]) | (
        set(config["extension_code_hashes"])
    )
    expected_runtime.discard("config/road-surface-teignmouth-topology-transition-v2.json")
    if set(_runtime_code_hashes(config)) != expected_runtime:
        raise RoadSurfacePatchError("complete runtime code-hash map differs from the fixed union")
    if config.get("approval_chain") != {
        "coordinator_receipt_path": COORDINATOR_RECEIPT_PATH,
        "independent_sol_review_path": SOL_REVIEW_PATH,
        "accepted_checkpoint_marker_prefix": ACCEPTED_CHECKPOINT_PREFIX,
        "review_disposition": "PASS",
        "coordinator_disposition": "ACCEPTED",
    }:
        raise RoadSurfacePatchError("transition approval-chain paths or dispositions changed")
    activation = config.get("activation")
    if activation not in (
        {
            "enabled": False,
            "status": "pending_independent_sol_review_and_coordinator_approval",
        },
        {"enabled": True, "status": "approval_chain_required"},
    ):
        raise RoadSurfacePatchError("transition activation policy changed")


def _validate_fixed_policy(config: dict[str, Any]) -> None:
    expected_top_level = {
        "activation",
        "approval_chain",
        "consumed_inventory",
        "consumed_trial_ids",
        "eligible_trial_ids",
        "extension_code_hashes",
        "extension_code_paths",
        "format_version",
        "input_state_transition",
        "legacy_flip05_code_hashes",
        "legacy_road05_code_hashes",
        "pinned_inputs",
        "purpose",
        "reconciliation_code_paths",
        "timing_policy",
        "transition_id",
    }
    if set(config) != expected_top_level:
        raise RoadSurfacePatchError("transition config fields differ from the fixed v2 schema")
    expected_pinned_fields = {
        "accepted_preview",
        "base_candidate_config_path",
        "base_candidate_config_sha256",
        "implementation_start_checkpoint_sha256",
        "release_files",
        "release_id",
        "source_manifest_path",
        "source_manifest_sha256",
        "study_config_path",
        "study_config_sha256",
        "study_id",
        "study_spec_path",
        "study_spec_sha256",
        "transition_spec_path",
        "transition_spec_sha256",
    }
    if set(config.get("pinned_inputs", {})) != expected_pinned_fields:
        raise RoadSurfacePatchError(
            "transition pinned-input fields differ from the fixed v2 schema"
        )
    if config.get("transition_id") != TRANSITION_ID:
        raise RoadSurfacePatchError("transition ID differs from the fixed v2 policy")
    if config.get("timing_policy") != EXPECTED_TIMING_POLICY:
        raise RoadSurfacePatchError("transition timing/resource policy differs from fixed limits")
    if config.get("format_version") != 2:
        raise RoadSurfacePatchError("transition config format version is unsupported")


def _run_validation_phase(
    function: Any,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    deadlines: TransitionDeadlines,
    clock: Any,
    label: str,
    metrics: dict[str, Any] | None = None,
) -> Any:
    """Interrupt Python validation work at the fixed cutoff without a stale worker."""
    deadlines.check("validation", clock())
    previous_trace = sys.gettrace()
    root = ROOT.resolve()
    # Keep strong code references to prevent id reuse. Relative membership also
    # depends on CWD; re-resolve it on CWD changes. Reparse paths stay uncached.
    membership: dict[int, tuple[Any, bool, str | None, bool]] = {}
    counts = dict.fromkeys(
        (
            "lineEvents",
            "relativeLineEvents",
            "clockPolls",
            "membershipResolutions",
            "relativeResolutions",
            "cacheHits",
            "uncachedReparseResolutions",
        ),
        0,
    )

    def deadline_trace(frame, event, arg):
        del arg
        if event == "line":
            counts["lineEvents"] += 1
            code = frame.f_code
            cached = membership.get(id(code))
            raw_filename = code.co_filename
            relative = cached[3] if cached is not None else not os.path.isabs(raw_filename)
            cwd = os.getcwd() if relative else None
            if relative:
                counts["relativeLineEvents"] += 1
            if cached is None or cached[2] != cwd:
                counts["membershipResolutions"] += 1
                counts["relativeResolutions"] += int(relative)
                cacheable = True
                try:
                    road_surface._assert_no_reparse_components(Path(raw_filename))
                except (road_surface.RoadSurfaceError, OSError, ValueError):
                    cacheable = False
                    counts["uncachedReparseResolutions"] += 1
                try:
                    filename = Path(raw_filename).resolve()
                    in_workspace = filename.is_relative_to(root)
                except (OSError, ValueError):
                    in_workspace = False
                if cacheable:
                    membership[id(code)] = (code, in_workspace, cwd, relative)
            else:
                counts["cacheHits"] += 1
                in_workspace = cached[1]
            if in_workspace:
                # No polling interval or grace period: EVERY workspace line.
                counts["clockPolls"] += 1
                deadlines.check("validation", clock())
        return deadline_trace

    def workspace_trace(frame, event, arg):
        # Absolute safe membership is invariant for this immutable phase. Avoid
        # repeating dictionary/path work, but keep EVERY workspace line poll.
        if event == "line":
            counts["lineEvents"] += 1
            counts["clockPolls"] += 1
            deadlines.check("validation", clock())
        return workspace_trace

    def select_frame(frame, event, arg):
        if event != "call":
            return None
        code = frame.f_code
        raw_filename = code.co_filename
        if not os.path.isabs(raw_filename):
            return deadline_trace
        cached = membership.get(id(code))
        if cached is None:
            counts["membershipResolutions"] += 1
            try:
                road_surface._assert_no_reparse_components(Path(raw_filename))
            except (road_surface.RoadSurfaceError, OSError, ValueError):
                # Reparse/unknown membership keeps the per-line safety path.
                return deadline_trace
            try:
                in_workspace = Path(raw_filename).resolve().is_relative_to(root)
            except (OSError, ValueError):
                return deadline_trace
            membership[id(code)] = (code, in_workspace, None, False)
        else:
            counts["cacheHits"] += 1
            in_workspace = cached[1]
        # Global call tracing remains active for workspace descendants entered
        # through external code, even when that external frame has no line hook.
        return workspace_trace if in_workspace else None

    if previous_trace is not None:
        raise RoadSurfacePatchError(
            f"cannot start bounded validation phase {label}: an external trace hook is active"
        )
    sys.settrace(select_frame)
    try:
        result = function(*args, **kwargs)
        deadlines.check("validation", clock())
        return result
    finally:
        sys.settrace(previous_trace)
        if metrics is not None:
            metrics.update(counts)
            metrics["codeObjectsCached"] = len(membership)
            metrics["pollingCadence"] = "every workspace line"
            metrics["membershipSelection"] = "safe absolute frames; relative/reparse per line"
        membership.clear()


def _offline_validation_unavailable(
    surface: Any,
    solver_report: dict[str, Any],
    accepted_preview_hashes: dict[str, str],
    *,
    reason: str,
    gate_seconds: dict[str, float],
) -> dict[str, Any]:
    """Return a complete fail-closed report when supervised validation times out."""
    candidate_bytes = surface.patch_heights.astype("<f4", copy=False).tobytes(order="C")
    candidate_hash = hashlib.sha256(candidate_bytes).hexdigest()

    def unavailable() -> dict[str, Any]:
        return {
            "passes": False,
            "available": False,
            "status": "unavailable_deadline",
            "reason": reason,
        }

    report: dict[str, Any] = {
        "inputBindings": unavailable(),
        "solverWitness": unavailable(),
        "passes": False,
        "gateNames": list(PATCH_OFFLINE_GATE_NAMES),
        "candidateFloat32Sha256": candidate_hash,
        "candidateFloat32ByteLength": len(candidate_bytes),
        "candidateFloat32Finite": bool(np.isfinite(surface.patch_heights).all()),
        "validatorVersion": "teignmouth-offline-validator-v2",
        "validationComplete": False,
        "validationStatus": "incomplete_deadline",
        "validationUnavailableReason": reason,
        "gateSeconds": dict(gate_seconds),
        "acceptedPreviewHashes": accepted_preview_hashes,
        "solverCandidateFloat32Sha256": solver_report.get("candidateFloat32Sha256"),
        "deadlineExceededDuringPhase": "post-solver offline validation",
    }
    for name in PATCH_OFFLINE_GATE_NAMES:
        report[name] = unavailable()
    return report


def _complete_offline_evaluation(aggregate: dict[str, Any]) -> tuple[bool, bool]:
    """Return whether all gates were evaluated and whether they all passed."""
    if aggregate.get("validationComplete") is not True:
        return False, False
    if aggregate.get("gateNames") != list(PATCH_OFFLINE_GATE_NAMES):
        return False, False
    gate_reports = [aggregate.get(name) for name in PATCH_OFFLINE_GATE_NAMES]
    if any(
        not isinstance(report, dict) or type(report.get("passes")) is not bool
        for report in gate_reports
    ):
        return False, False
    base_passes = all(report["passes"] for report in gate_reports)
    if not base_passes:
        # The runner skips independent asset work once a base gate has failed.
        # A fully reported base failure remains a complete, fail-closed result.
        return True, False

    assembly = aggregate.get("studyAssemblyAndResources")
    if not isinstance(assembly, dict) or type(assembly.get("passes")) is not bool:
        return False, False
    if type(assembly.get("deterministicAssets")) is not bool:
        return False, False
    for name in ("firstIndependentValidation", "secondIndependentValidation", "resourceLimits"):
        report = assembly.get(name)
        if not isinstance(report, dict) or type(report.get("passes")) is not bool:
            return False, False
    hashes = assembly.get("independentAssetHashes")
    if not isinstance(hashes, dict) or set(hashes) != {"first", "second"}:
        return False, False
    if not all(isinstance(hashes[key], dict) for key in ("first", "second")):
        return False, False
    return True, bool(
        assembly["passes"]
        and assembly["deterministicAssets"]
        and assembly["firstIndependentValidation"]["passes"]
        and assembly["secondIndependentValidation"]["passes"]
        and assembly["resourceLimits"]["passes"]
        and hashes["first"] == hashes["second"]
    )


def _patch_runner(
    runner: dict[str, Any],
    config: dict[str, Any],
    *,
    invocation_start: float,
    real_time: Any = time,
) -> dict[str, Any]:
    """Patch the live function namespace while keeping the study runner frozen."""
    namespace = runner["run_one_trial"].__globals__
    base_stage_validator = namespace["validate_study_stage_order"]
    base_code_hashes = namespace["_code_hashes"]
    base_frozen_inputs = namespace["_frozen_study_input_hashes"]
    base_protected_snapshot = namespace["_protected_hash_snapshot"]
    base_load_configs = namespace["_load_frozen_configs"]
    base_serialize = namespace["serialize_offline_report"]
    base_exclusive_write = namespace["_exclusive_write"]
    base_digest = namespace["_digest"]
    base_classify = namespace["_final_classification"]
    base_run_one_trial = namespace["run_one_trial"]
    state: dict[str, Any] = {
        "deadlines": TransitionDeadlines(invocation_start),
        "protected_parts": {},
        "before_map": None,
        "transition_preflight": None,
        "solver_budget_at_start": None,
        "post_solver_gates_active": False,
        "trace_metrics": {},
        "acceptance_gates_completed_monotonic": None,
    }

    def code_hashes(root: Path) -> dict[str, str]:
        result = base_code_hashes(root)
        for relative in RECONCILIATION_CODE_PATHS + EXTENSION_CODE_PATHS:
            path = root / relative
            runner["road_surface"]._assert_no_reparse_components(path)
            if not path.is_file():
                raise RoadSurfacePatchError(f"transition code input is missing: {relative}")
            result[relative] = file_digest(path)
        if config["activation"]["enabled"] is True:
            ensure_transition_activated(
                config,
                root=root,
                config_path=root / "config/road-surface-teignmouth-topology-transition-v2.json",
            )
            result[f"approval:{SOL_REVIEW_PATH}"] = file_digest(root / SOL_REVIEW_PATH)
            result[f"approval:{COORDINATOR_RECEIPT_PATH}"] = file_digest(
                root / COORDINATOR_RECEIPT_PATH
            )
        return result

    def capture_map_part(
        kind: str, base_function: Any, *args: Any, **kwargs: Any
    ) -> dict[str, str]:
        part = base_function(*args, **kwargs)
        state["protected_parts"][kind] = part
        if set(state["protected_parts"]) == {"protected", "study"}:
            state["current_map"] = {
                **state["protected_parts"]["protected"],
                **state["protected_parts"]["study"],
            }
            if state["before_map"] is None:
                state["before_map"] = dict(state["current_map"])
        return part

    def protected_snapshot(*args: Any, **kwargs: Any) -> dict[str, str]:
        return capture_map_part("protected", base_protected_snapshot, *args, **kwargs)

    def frozen_inputs(*args: Any, **kwargs: Any) -> dict[str, str]:
        return capture_map_part("study", base_frozen_inputs, *args, **kwargs)

    def stage_validator(
        raw_root: Path,
        trial_id: str,
        *,
        expected_study_config_sha256: str | None = None,
        expected_input_snapshot_sha256: str | None = None,
        expected_code_hashes: dict[str, str] | None = None,
    ) -> None:
        validate_reconciled_stage_order(
            raw_root,
            trial_id,
            expected_study_config_sha256=expected_study_config_sha256,
            expected_input_snapshot_sha256=None,
            expected_code_hashes=expected_code_hashes,
            base_validator=base_stage_validator,
        )
        if expected_input_snapshot_sha256 is None:
            return
        ensure_transition_activated(
            config,
            root=ROOT,
            config_path=ROOT / "config/road-surface-teignmouth-topology-transition-v2.json",
        )
        current_map = state.get("current_map")
        if not isinstance(current_map, dict):
            raise RoadSurfacePatchError(
                "current protected snapshot was not captured before stage check"
            )
        transition = validate_transition_inputs(ROOT, current_map, config=config)
        transition["priorTrials"] = validate_prior_input_transition(
            raw_root,
            trial_id,
            current_map,
            expected_input_snapshot_sha256,
            config=config,
        )
        state["transition_preflight"] = transition

    def remaining_seconds(deadline: float, phase: str, *, now: float | None = None) -> float:
        del deadline
        phase_name = phase_for_runner_check(phase)
        current = real_time.monotonic() if now is None else now
        return state["deadlines"].check(phase_name, current)

    def load_frozen_configs() -> Any:
        solver_budget = namespace["MAXIMUM_WALL_SECONDS"]
        namespace["MAXIMUM_WALL_SECONDS"] = PREPARATION_SOLVER_SECONDS
        try:
            return base_load_configs()
        finally:
            namespace["MAXIMUM_WALL_SECONDS"] = solver_budget

    def validate_candidate(
        surface: Any,
        influence: Any,
        constraints: list[dict[str, Any]],
        solver_report: dict[str, Any],
        accepted_preview_hashes: dict[str, str],
    ) -> dict[str, Any]:
        state["post_solver_gates_active"] = True
        state["process_result"] = None
        state["process_operation"] = 1
        state["process_surface"] = surface
        gate_seconds: dict[str, float] = {}
        try:
            state["deadlines"].check("validation", real_time.monotonic())
            import shapely

            bindings = {
                "runtimeHashes": {
                    **_runtime_code_hashes(config, ROOT),
                    CONFIG_PATH.relative_to(ROOT).as_posix(): file_digest(CONFIG_PATH),
                },
                "protectedBefore": state.get("before_map"),
                "consumedInventorySha256": config["consumed_inventory"]["sha256"],
                "dataSourceManifestSha256": file_digest(ROOT / "data/source-manifest.json"),
                "releaseTerrainManifestSha256": surface.inputs.manifest_sha256,
                "releaseSourceHashes": surface.inputs.source_hashes,
                "environment": {
                    "python": sys.version,
                    "numpy": np.__version__,
                    "shapely": shapely.__version__,
                    "geos": shapely.geos_version_string,
                },
            }
            response = supervise(
                ROOT,
                {
                    "surface": surface,
                    "influence": influence,
                    "constraints": constraints,
                    "solver": solver_report,
                    "acceptedPreviewHashes": accepted_preview_hashes,
                    "candidateSha256": hashlib.sha256(
                        surface.patch_heights.astype("<f4", copy=False).tobytes()
                    ).hexdigest(),
                    "bindings": bindings,
                    "deadline": state["deadlines"].validation,
                },
                deadline=state["deadlines"].validation,
                finalization_deadline=state["deadlines"].finalization,
                clock=real_time.monotonic,
            )
            state["deadlines"].check("validation", real_time.monotonic())
            state["process_result"] = response
            report = response["report"]
            gate_seconds = response["gateSeconds"]
        except (
            ProcessValidationError,
            TransitionDeadlineExceeded,
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ) as exc:
            report = _offline_validation_unavailable(
                surface,
                solver_report,
                accepted_preview_hashes,
                reason=f"process validation unavailable: {exc}",
                gate_seconds=gate_seconds,
            )
        report["validationTransition"] = {
            "transitionId": TRANSITION_ID,
            "validatorVersion": "teignmouth-offline-validator-v2",
            "deadlineMonotonicSeconds": state["deadlines"].validation,
            "validationComplete": report["validationComplete"],
            "gateSeconds": gate_seconds,
            "supervision": "windows-job-process-v1",
            "processTransport": (state["process_result"] or {}).get("processTransport"),
        }
        return report

    def consume_process_result(expected: int) -> dict[str, Any]:
        state["deadlines"].check("validation", real_time.monotonic())
        result = state.get("process_result")
        if not isinstance(result, dict) or state["process_operation"] != expected:
            raise RoadSurfacePatchError("process result operation missing, reused or out of order")
        state["process_operation"] += 1
        return result

    def asset_assembly(surface: Any, clipped: Any, aggregate: Any) -> Any:
        result = consume_process_result(1)
        if (
            surface is not state["process_surface"]
            or clipped is not result["report"]["roadPathReclip"]
            or aggregate["candidateFloat32Sha256"] != result["report"]["candidateFloat32Sha256"]
        ):
            raise RoadSurfacePatchError("process assembly inputs changed")
        return result["firstAssets"], result["secondAssets"], result["deterministic"]

    def asset_validation(assets: Any, surface: Any, candidate_hash: str, clipped: Any) -> Any:
        step = state["process_operation"]
        if step not in (2, 3):
            raise RoadSurfacePatchError("unexpected process asset validation")
        result = consume_process_result(step)
        key = "first" if step == 2 else "second"
        if (
            assets is not result[key + "Assets"]
            or surface is not state["process_surface"]
            or candidate_hash != result["report"]["candidateFloat32Sha256"]
            or clipped is not result["report"]["roadPathReclip"]
        ):
            raise RoadSurfacePatchError("process asset validation inputs changed")
        return result[key + "Validation"]

    def resource_report(mesh: Any, clipped: Any, first: Any, second: Any) -> Any:
        result = consume_process_result(4)
        if (
            mesh is not state["process_surface"].mesh
            or clipped is not result["report"]["roadPathReclip"]
            or first is not result["firstAssets"]
            or second is not result["secondAssets"]
        ):
            raise RoadSurfacePatchError("process resource inputs changed")
        return result["resources"]

    def digest_with_validation_deadline(payload: bytes) -> str:
        if state["post_solver_gates_active"]:
            state["deadlines"].check("validation", real_time.monotonic())
        return base_digest(payload)

    def final_classification(*args: Any, **kwargs: Any) -> str:
        result = base_classify(*args, **kwargs)
        aggregate = args[0] if args else kwargs.get("aggregate")
        if isinstance(aggregate, dict) and _complete_offline_evaluation(aggregate)[0]:
            state["acceptance_gates_completed_monotonic"] = real_time.monotonic()
        return result

    def exclusive_write(path: Path, payload: bytes) -> None:
        # The final aggregate is the only acceptance record. Never commit it
        # after the hard finalization deadline, even if serialization finished.
        if path.name == "offline-aggregate.json":
            elapsed = real_time.monotonic() - invocation_start
            if elapsed >= FINALIZATION_CUTOFF_SECONDS:
                raise TransitionDeadlineExceeded(
                    "finalization cutoff reached before offline aggregate commit"
                )
            temporary = path.with_name(path.name + ".teignmouth-v2-finalizing")
            road_surface._assert_no_reparse_components(path)
            road_surface._assert_no_reparse_components(temporary)
            if path.exists() or temporary.exists():
                raise RoadSurfacePatchError(
                    "offline aggregate or owned finalization temporary already exists"
                )
            created_temporary = False
            try:
                with temporary.open("xb") as stream:
                    created_temporary = True
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                if real_time.monotonic() - invocation_start >= FINALIZATION_CUTOFF_SECONDS:
                    raise TransitionDeadlineExceeded(
                        "finalization cutoff reached before offline aggregate promotion"
                    )
                # A hard link is an atomic no-overwrite commit on the same
                # volume. If another writer wins, this raises FileExistsError.
                os.link(temporary, path)
                temporary.unlink()
                return
            except BaseException:
                if created_temporary and temporary.exists():
                    temporary.unlink()
                raise
        base_exclusive_write(path, payload)

    def serialize(payload: Any) -> bytes:
        if isinstance(payload, dict):
            if payload.get("trialId") and isinstance(payload.get("solverLimits"), dict):
                payload["solverLimits"]["maximumWallSeconds"] = PREPARATION_SOLVER_SECONDS
                payload["transitionPolicy"] = _timing_record(state["deadlines"])
            if payload.get("trialId") and "trialWallBudgetSecondsAtSolverStart" in payload:
                budget = float(payload["trialWallBudgetSecondsAtSolverStart"])
                payload["trialElapsedSecondsBeforeSolver"] = max(
                    0.0, PREPARATION_SOLVER_SECONDS - budget
                )
                payload["transitionPolicy"] = _timing_record(state["deadlines"])
            is_final_aggregate = bool(
                payload.get("trialId")
                and "passes" in payload
                and "protectedHashesBefore" in payload
                and "protectedHashesAfter" in payload
            )
            if is_final_aggregate:
                before = payload.get("protectedHashesBefore")
                after = payload.get("protectedHashesAfter")
                expected_before = state.get("before_map")
                expected_after = state.get("current_map")
                maps_match = (
                    isinstance(before, dict)
                    and before == after
                    and before == expected_before
                    and after == expected_after
                )
                payload["protectedHashesMatch"] = bool(
                    payload.get("protectedHashesMatch") is True and maps_match
                )
                elapsed = real_time.monotonic() - invocation_start
                payload["trialElapsedSeconds"] = elapsed
                payload["trialDeadlineMonotonicSeconds"] = state["deadlines"].finalization
                payload["trialMaximumWallSeconds"] = FINALIZATION_CUTOFF_SECONDS
                payload["trialSolverDeadlineSeconds"] = PREPARATION_SOLVER_SECONDS
                payload["trialValidationCutoffSeconds"] = VALIDATION_CUTOFF_SECONDS
                payload["postSolverValidationCutoffIncludesAssembly"] = True
                payload["finalizationReserveSeconds"] = FINALIZATION_RESERVE_SECONDS
                payload["transitionPolicy"] = _timing_record(state["deadlines"])
                payload["transitionInputState"] = state.get("transition_preflight")
                completion_time = state.get("acceptance_gates_completed_monotonic")
                offline_evaluation_complete, all_acceptance_pass = _complete_offline_evaluation(
                    payload
                )
                validation_completed = (
                    isinstance(completion_time, (int, float))
                    and completion_time < state["deadlines"].validation
                    and offline_evaluation_complete
                )
                payload["acceptanceGatesCompletedBeforeValidationCutoff"] = validation_completed
                if not validation_completed:
                    payload["passes"] = False
                    payload["finalClassification"] = "unresolved_numerical_result"
                    payload["deadlineExceededDuringPhase"] = "post-solver validation cutoff"
                elif not all_acceptance_pass:
                    payload["passes"] = False
                    payload["finalClassification"] = "failed_offline_gate"
                else:
                    # Preserve a pass produced by the frozen implementation;
                    # this transition never promotes an earlier false result.
                    payload["passes"] = payload.get("passes") is True
                if elapsed >= FINALIZATION_CUTOFF_SECONDS:
                    payload["passes"] = False
                    payload["finalClassification"] = "finalization_timeout"
                    payload["deadlineExceededDuringPhase"] = "finalization cutoff"
                if not payload["protectedHashesMatch"]:
                    payload["passes"] = False
                    if elapsed < FINALIZATION_CUTOFF_SECONDS:
                        payload["finalClassification"] = "failed_offline_gate"
        serialized = base_serialize(payload)
        if isinstance(payload, dict) and is_final_aggregate:
            elapsed_after_serialization = real_time.monotonic() - invocation_start
            if elapsed_after_serialization >= FINALIZATION_CUTOFF_SECONDS:
                payload["trialElapsedSeconds"] = elapsed_after_serialization
                payload["passes"] = False
                payload["finalClassification"] = "finalization_timeout"
                payload["deadlineExceededDuringPhase"] = "finalization cutoff during serialization"
                serialized = base_serialize(payload)
        return serialized

    def v2_run_one_trial(trial_id: str) -> tuple[int, dict[str, Any]]:
        admit_remaining_trial(trial_id)
        budget = state["deadlines"].remaining_solver(real_time.monotonic())
        state["solver_budget_at_start"] = budget
        original_budget = namespace["MAXIMUM_WALL_SECONDS"]
        namespace["MAXIMUM_WALL_SECONDS"] = budget
        try:
            status, aggregate = base_run_one_trial(trial_id)
            if not isinstance(aggregate, dict) or aggregate.get("passes") is not True:
                status = 2
            if real_time.monotonic() - invocation_start >= FINALIZATION_CUTOFF_SECONDS:
                status = 2
            return status, aggregate
        finally:
            namespace["MAXIMUM_WALL_SECONDS"] = original_budget

    namespace["_code_hashes"] = code_hashes
    namespace["_protected_hash_snapshot"] = protected_snapshot
    namespace["_frozen_study_input_hashes"] = frozen_inputs
    namespace["validate_study_stage_order"] = stage_validator
    namespace["_remaining_trial_seconds"] = remaining_seconds
    namespace["_load_frozen_configs"] = load_frozen_configs
    namespace["validate_offline_candidate"] = validate_candidate
    namespace["assemble_deterministic_candidate_assets"] = asset_assembly
    namespace["validate_candidate_patch_assets"] = asset_validation
    namespace["_resource_report"] = resource_report
    namespace["_digest"] = digest_with_validation_deadline
    namespace["_final_classification"] = final_classification
    namespace["_exclusive_write"] = exclusive_write
    namespace["serialize_offline_report"] = serialize
    namespace["MAXIMUM_WALL_SECONDS"] = PREPARATION_SOLVER_SECONDS
    namespace["run_one_trial"] = v2_run_one_trial
    # runpy returns a mapping distinct from the function's live globals. The
    # CLI invokes through the returned mapping, so update both references.
    runner["MAXIMUM_WALL_SECONDS"] = PREPARATION_SOLVER_SECONDS
    runner["run_one_trial"] = v2_run_one_trial
    return state


def _timing_record(deadlines: TransitionDeadlines) -> dict[str, Any]:
    return {
        "transitionId": TRANSITION_ID,
        "invocationStartMonotonicSeconds": deadlines.invocation_start,
        "solverDeadlineMonotonicSeconds": deadlines.solver,
        "validationDeadlineMonotonicSeconds": deadlines.validation,
        "finalizationDeadlineMonotonicSeconds": deadlines.finalization,
        "maximumIterations": MAXIMUM_ITERATIONS,
        "qualificationProjectedEndToEndSeconds": QUALIFICATION_SECONDS,
        "validationIncludesAssemblyAndResourceDeterminism": True,
        "finalizationReserveSeconds": FINALIZATION_RESERVE_SECONDS,
        "retryAllowed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transition-config", required=True, type=Path)
    parser.add_argument("--trial", required=True, choices=ELIGIBLE_TRIALS)
    args = parser.parse_args(argv)
    invocation_start = time.monotonic()
    config_path = _assert_exact_config_path(args.transition_config)
    config = _read_config(config_path)
    _validate_static_bindings(config)
    ensure_transition_activated(config, root=ROOT, config_path=config_path)
    admit_remaining_trial(args.trial)
    runner = runpy.run_path(str(STUDY_RUNNER_PATH))
    _patch_runner(
        runner,
        config,
        invocation_start=invocation_start,
    )
    status, _aggregate = runner["run_one_trial"](args.trial)
    elapsed = time.monotonic() - invocation_start
    if elapsed >= FINALIZATION_CUTOFF_SECONDS:
        return 2
    return status


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RoadSurfacePatchError as exc:
        print(
            json.dumps({"passes": False, "error": str(exc)}, sort_keys=True),
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
