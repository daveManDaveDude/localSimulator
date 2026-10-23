"""Narrow recovery checks for the coordinator-interrupted flip-05 attempt."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import road_surface
from .road_surface_patch import (
    ACCEPTED_PREVIEW_HASHES,
    RoadSurfacePatchError,
    _write_record_exclusive,
    serialize_offline_report,
)
from .road_surface_study import RAW_TRIAL_FILES, STUDY_DIRECTORY, TRIAL_ORDER

CHECKPOINT_HASH_KEY = "protected:.codex/torquay-plan-implementation.md"
RECONCILIATION_ID = "coordinator-interrupted-flip-05-v1"


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_json(path: Path, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoadSurfacePatchError(f"cannot read {description}: {exc}") from exc
    if not isinstance(value, dict):
        raise RoadSurfacePatchError(f"{description} must be a JSON object")
    return value


def validate_interrupted_flip_snapshot(
    *,
    attempt: dict[str, Any],
    protected_after: dict[str, str],
    code_hashes_after: dict[str, str],
    current_study_config_sha256: str,
    current_base_config_sha256: str,
    candidate_output_absent: bool,
) -> dict[str, Any]:
    """Validate the exact recorded before map and independent current after map."""
    before = attempt.get("protectedHashesBefore")
    if not isinstance(before, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in before.items()
    ):
        raise RoadSurfacePatchError("flip-05 attempt has no complete protected before map")
    if set(before) != set(protected_after):
        raise RoadSurfacePatchError("flip-05 before/after protected maps have different keys")
    if _canonical_digest(before) != attempt.get("inputSnapshotSha256"):
        raise RoadSurfacePatchError("flip-05 protected before map does not match its input digest")
    changed = {
        key: {"before": before[key], "after": protected_after[key]}
        for key in sorted(before)
        if before[key] != protected_after[key]
    }
    if set(changed) != {CHECKPOINT_HASH_KEY}:
        raise RoadSurfacePatchError(
            "flip-05 reconciliation permits only the coordinator checkpoint hash to differ"
        )
    if code_hashes_after != attempt.get("codeHashes"):
        raise RoadSurfacePatchError("flip-05 computational/source code hashes changed")
    if current_study_config_sha256 != attempt.get("studyConfigSha256"):
        raise RoadSurfacePatchError("flip-05 study config digest changed")
    if current_base_config_sha256 != attempt.get("baseCandidateConfigSha256"):
        raise RoadSurfacePatchError("flip-05 base candidate config digest changed")
    if candidate_output_absent is not True:
        raise RoadSurfacePatchError("reserved public candidate output is no longer absent")
    for name, digest in ACCEPTED_PREVIEW_HASHES.items():
        if before.get(f"acceptedPreview:{name}") != digest:
            raise RoadSurfacePatchError(f"flip-05 accepted preview binding differs: {name}")
        if protected_after.get(f"acceptedPreview:{name}") != digest:
            raise RoadSurfacePatchError(f"accepted preview changed during flip-05: {name}")
    if not any(key.startswith("release:") for key in before):
        raise RoadSurfacePatchError("flip-05 protected map omits pinned release file hashes")
    return {
        "verified": True,
        "reconciliationId": RECONCILIATION_ID,
        "beforeSnapshotSha256": _canonical_digest(before),
        "afterSnapshotSha256": _canonical_digest(protected_after),
        "protectedEntryCount": len(before),
        "changedProtectedEntries": changed,
        "onlyCheckpointChanged": True,
        "acceptedPreviewUnchanged": True,
        "pinnedReleaseBindingsPresent": True,
        "computationalAndSourceCodeHashesUnchanged": True,
        "studyConfigUnchanged": True,
        "baseCandidateConfigUnchanged": True,
        "candidateOutputAbsent": True,
    }


def build_interrupted_flip_aggregate(
    trial_directory: Path,
    *,
    protected_after: dict[str, str],
    code_hashes_after: dict[str, str],
    current_study_config_sha256: str,
    current_base_config_sha256: str,
    candidate_output_absent: bool,
) -> dict[str, Any]:
    """Build a truthful partial aggregate only from retained files and snapshots."""
    attempt = _read_json(trial_directory / "attempt.json", "flip-05 attempt")
    topology = _read_json(trial_directory / "topology.json", "flip-05 topology report")
    solver = _read_json(trial_directory / "solver-phase.json", "flip-05 solver report")
    certificate = _read_json(
        trial_directory / "certificate-verification.json", "flip-05 certificate report"
    )
    expected_files = RAW_TRIAL_FILES - {"offline-aggregate.json"}
    road_surface._assert_no_reparse_components(trial_directory)
    aggregate_path = trial_directory / "offline-aggregate.json"
    if aggregate_path.exists():
        raise RoadSurfacePatchError("flip-05 aggregate already exists; refusing overwrite")
    actual_files: set[str] = set()
    file_hashes: dict[str, str] = {}
    for child in trial_directory.iterdir():
        if child.is_dir() or road_surface._is_reparse_point(child):
            raise RoadSurfacePatchError("flip-05 contains an unsafe or non-file output")
        actual_files.add(child.name)
        if child.name not in expected_files:
            raise RoadSurfacePatchError(f"flip-05 contains an unexpected file: {child.name}")
        digest = hashlib.sha256(child.read_bytes()).hexdigest()
        file_hashes[child.name] = digest
    if actual_files != expected_files:
        missing = sorted(expected_files - actual_files)
        raise RoadSurfacePatchError(f"flip-05 partial output inventory differs; missing {missing}")
    if attempt.get("trialId") != "flip-05" or attempt.get("trialOrderIndex") != 0:
        raise RoadSurfacePatchError("recovery is restricted to the consumed flip-05 attempt")
    if attempt.get("candidatePublicOutputWritten") is not False:
        raise RoadSurfacePatchError("flip-05 attempt claims a public candidate write")
    if topology.get("trialId") != "flip-05" or topology.get("passes") is not True:
        raise RoadSurfacePatchError("retained flip-05 topology report is not a topology pass")
    if solver.get("topologyVariant") != "flip-05":
        raise RoadSurfacePatchError("retained solver report is not for flip-05")
    if solver.get("converged") is not False or solver.get("iterations") != 2_000:
        raise RoadSurfacePatchError(
            "retained solver report does not show the iteration-limit result"
        )
    if not isinstance(solver.get("maximumConstraintResidualM"), (int, float)):
        raise RoadSurfacePatchError("retained solver report lacks its measured residual")
    if solver.get("maximumIterations") != 2_000:
        raise RoadSurfacePatchError("retained solver report uses a different iteration limit")
    if certificate.get("status") != "not_emitted" or certificate.get("verified") is not None:
        raise RoadSurfacePatchError("flip-05 unexpectedly contains a solver certificate")
    witness_path = trial_directory / "candidate-heights.f32"
    witness_digest = hashlib.sha256(witness_path.read_bytes()).hexdigest()
    if witness_digest != solver.get("candidateFloat32Sha256"):
        raise RoadSurfacePatchError("retained Float32 witness differs from the solver report")

    reconciliation = validate_interrupted_flip_snapshot(
        attempt=attempt,
        protected_after=protected_after,
        code_hashes_after=code_hashes_after,
        current_study_config_sha256=current_study_config_sha256,
        current_base_config_sha256=current_base_config_sha256,
        candidate_output_absent=candidate_output_absent,
    )
    changed = reconciliation["changedProtectedEntries"]
    return {
        "studyId": attempt.get("studyId"),
        "trialId": "flip-05",
        "passes": False,
        "finalClassification": "unresolved_numerical_result",
        "phase": "coordinator-interrupted-after-solver",
        "interruption": {
            "reason": "coordinator requested the active trial to stop",
            "processTerminated": True,
            "runnerAfterSnapshotCompleted": False,
            "independentPostRunSnapshotCompleted": True,
            "offlineAggregateValidationCompleted": False,
            "offlineValidationStatus": "not_run",
        },
        "topology": topology,
        "solver": solver,
        "certificateVerification": certificate,
        "candidateFloat32Sha256": witness_digest,
        "candidateFloat32ByteLength": witness_path.stat().st_size,
        "offlineValidation": {
            "status": "not_run",
            "reason": "the coordinator interruption occurred before complete offline validation",
        },
        "protectedHashesBefore": attempt["protectedHashesBefore"],
        "protectedHashesAfter": protected_after,
        "protectedHashesMatch": False,
        "protectedHashDifferences": changed,
        "inputSnapshotSha256": attempt["inputSnapshotSha256"],
        "postInterruptionInputSnapshotSha256": reconciliation["afterSnapshotSha256"],
        "codeHashesBefore": attempt["codeHashes"],
        "codeHashesAfter": code_hashes_after,
        "codeUnchangedDuringTrial": True,
        "studyConfigSha256Before": attempt.get("studyConfigSha256"),
        "studyConfigSha256After": current_study_config_sha256,
        "baseCandidateConfigSha256Before": attempt.get("baseCandidateConfigSha256"),
        "baseCandidateConfigSha256After": current_base_config_sha256,
        "configsUnchangedDuringTrial": True,
        "candidateOutputStillAbsent": True,
        "candidatePublicOutputWritten": False,
        "interruptionReconciliation": reconciliation,
        "retainedFiles": file_hashes,
        "retainedFileCountBeforeAggregate": len(file_hashes),
        "trialElapsedSeconds": None,
        "trialElapsedSecondsUnavailableReason": (
            "the interrupted runner did not write its final elapsed-time field"
        ),
        "evidencePath": (Path(".codex/evidence/teignmouth-topology-study/flip-05")).as_posix(),
    }


def reconcile_interrupted_flip_attempt(
    project_root: Path,
    *,
    protected_after: dict[str, str],
    code_hashes_after: dict[str, str],
    current_study_config_sha256: str,
    current_base_config_sha256: str,
) -> dict[str, Any]:
    """Exclusively add the one missing aggregate after independent validation."""
    root = project_root.resolve(strict=True)
    raw_root = root / STUDY_DIRECTORY
    trial = raw_root / "flip-05"
    expected = root / STUDY_DIRECTORY / "flip-05"
    _road_surface_assert_exact_path(trial, expected)
    candidate = root / "public/worlds/torquay-road-surface-teignmouth-candidate"
    road_surface._assert_no_reparse_components(candidate)
    report = build_interrupted_flip_aggregate(
        trial,
        protected_after=protected_after,
        code_hashes_after=code_hashes_after,
        current_study_config_sha256=current_study_config_sha256,
        current_base_config_sha256=current_base_config_sha256,
        candidate_output_absent=not candidate.exists(),
    )
    destination = trial / "offline-aggregate.json"
    if destination.exists():
        raise RoadSurfacePatchError("flip-05 aggregate already exists; refusing overwrite")
    payload = serialize_offline_report(report)
    _write_record_exclusive(destination, payload)
    return report


def _road_surface_assert_exact_path(actual: Path, expected: Path) -> None:
    road_surface._assert_no_reparse_components(actual)
    road_surface._assert_no_reparse_components(expected)
    if (
        os.path.normcase(str(actual.resolve(strict=True)))
        != os.path.normcase(str(expected.resolve(strict=True)))
        or not actual.is_dir()
    ):
        raise RoadSurfacePatchError(
            "reconciliation path is not the exact consumed flip-05 directory"
        )


def _validate_reconciled_flip_record(
    raw_root: Path,
    attempt: dict[str, Any],
    aggregate: dict[str, Any],
    *,
    expected_input_snapshot_sha256: str | None,
) -> None:
    """Bind the recovery marker to the retained attempt, maps and output bytes."""
    trial = raw_root / "flip-05"
    expected_files = RAW_TRIAL_FILES - {"offline-aggregate.json"}
    recorded_files = aggregate.get("retainedFiles")
    if not isinstance(recorded_files, dict) or set(recorded_files) != expected_files:
        raise RoadSurfacePatchError("flip-05 retained-file inventory differs from its allowlist")
    actual_files: dict[str, str] = {}
    for child in trial.iterdir():
        if child.is_dir() or road_surface._is_reparse_point(child):
            raise RoadSurfacePatchError("flip-05 contains an unsafe retained output")
        if child.name == "offline-aggregate.json":
            continue
        if child.name not in expected_files:
            raise RoadSurfacePatchError(
                f"flip-05 contains an unexpected retained file: {child.name}"
            )
        actual_files[child.name] = hashlib.sha256(child.read_bytes()).hexdigest()
    if set(actual_files) != expected_files or actual_files != recorded_files:
        raise RoadSurfacePatchError("flip-05 retained-file hashes differ from the recovery record")
    if aggregate.get("retainedFileCountBeforeAggregate") != len(expected_files):
        raise RoadSurfacePatchError("flip-05 retained-file count differs from the recovery record")

    before = attempt.get("protectedHashesBefore")
    after = aggregate.get("protectedHashesAfter")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise RoadSurfacePatchError("flip-05 recovery record omits protected hash maps")
    if aggregate.get("protectedHashesBefore") != before:
        raise RoadSurfacePatchError("flip-05 aggregate before map differs from its attempt")
    if _canonical_digest(before) != attempt.get("inputSnapshotSha256"):
        raise RoadSurfacePatchError("flip-05 attempt before map does not match its input digest")
    if set(before) != set(after):
        raise RoadSurfacePatchError("flip-05 protected before/after maps have different keys")
    changed = {
        key: {"before": before[key], "after": after[key]}
        for key in sorted(before)
        if before[key] != after[key]
    }
    if set(changed) != {CHECKPOINT_HASH_KEY}:
        raise RoadSurfacePatchError("flip-05 recovery map does not show only the checkpoint change")
    if not any(key.startswith("release:") for key in before):
        raise RoadSurfacePatchError("flip-05 protected map omits pinned release hashes")
    for name, digest in ACCEPTED_PREVIEW_HASHES.items():
        if before.get(f"acceptedPreview:{name}") != digest:
            raise RoadSurfacePatchError(f"flip-05 accepted preview binding differs: {name}")
        if after.get(f"acceptedPreview:{name}") != digest:
            raise RoadSurfacePatchError(f"accepted preview changed after flip-05: {name}")
    if aggregate.get("protectedHashDifferences") != changed:
        raise RoadSurfacePatchError("flip-05 reported protected differences do not match its maps")
    after_digest = _canonical_digest(after)
    if aggregate.get("postInterruptionInputSnapshotSha256") != after_digest or aggregate.get(
        "inputSnapshotSha256"
    ) != attempt.get("inputSnapshotSha256"):
        raise RoadSurfacePatchError("flip-05 recovery snapshot digests do not match its maps")
    recovery = aggregate.get("interruptionReconciliation")
    if not isinstance(recovery, dict):
        raise RoadSurfacePatchError("flip-05 recovery record has no reconciliation object")
    if (
        recovery.get("verified") is not True
        or recovery.get("reconciliationId") != RECONCILIATION_ID
        or recovery.get("beforeSnapshotSha256") != attempt.get("inputSnapshotSha256")
        or recovery.get("afterSnapshotSha256") != after_digest
        or recovery.get("changedProtectedEntries") != changed
        or recovery.get("protectedEntryCount") != len(before)
        or recovery.get("onlyCheckpointChanged") is not True
        or recovery.get("acceptedPreviewUnchanged") is not True
        or recovery.get("pinnedReleaseBindingsPresent") is not True
        or recovery.get("computationalAndSourceCodeHashesUnchanged") is not True
        or recovery.get("studyConfigUnchanged") is not True
        or recovery.get("baseCandidateConfigUnchanged") is not True
        or recovery.get("candidateOutputAbsent") is not True
    ):
        raise RoadSurfacePatchError("flip-05 reconciliation object is not bound to its evidence")
    if (
        expected_input_snapshot_sha256 is not None
        and after_digest != expected_input_snapshot_sha256
    ):
        raise RoadSurfacePatchError("current input snapshot differs from reconciled flip-05 map")

    code_hashes = attempt.get("codeHashes")
    if (
        not isinstance(code_hashes, dict)
        or aggregate.get("codeHashesBefore") != code_hashes
        or aggregate.get("codeHashesAfter") != code_hashes
        or aggregate.get("codeUnchangedDuringTrial") is not True
    ):
        raise RoadSurfacePatchError("flip-05 recovery code bindings differ from its attempt")
    study_digest = attempt.get("studyConfigSha256")
    base_digest = attempt.get("baseCandidateConfigSha256")
    if (
        aggregate.get("studyConfigSha256Before") != study_digest
        or aggregate.get("studyConfigSha256After") != study_digest
        or aggregate.get("baseCandidateConfigSha256Before") != base_digest
        or aggregate.get("baseCandidateConfigSha256After") != base_digest
        or aggregate.get("configsUnchangedDuringTrial") is not True
    ):
        raise RoadSurfacePatchError("flip-05 recovery config bindings differ from its attempt")

    topology = _read_json(trial / "topology.json", "flip-05 topology report")
    solver = _read_json(trial / "solver-phase.json", "flip-05 solver report")
    certificate = _read_json(trial / "certificate-verification.json", "flip-05 certificate report")
    if aggregate.get("topology") != topology or topology.get("passes") is not True:
        raise RoadSurfacePatchError("flip-05 aggregate topology differs from retained evidence")
    if (
        aggregate.get("solver") != solver
        or solver.get("converged") is not False
        or solver.get("iterations") != 2_000
        or solver.get("maximumIterations") != 2_000
    ):
        raise RoadSurfacePatchError("flip-05 aggregate solver differs from retained evidence")
    if aggregate.get("certificateVerification") != certificate:
        raise RoadSurfacePatchError("flip-05 aggregate certificate differs from retained evidence")
    witness_digest = hashlib.sha256((trial / "candidate-heights.f32").read_bytes()).hexdigest()
    if (
        aggregate.get("candidateFloat32Sha256") != witness_digest
        or solver.get("candidateFloat32Sha256") != witness_digest
        or aggregate.get("candidateFloat32ByteLength")
        != (trial / "candidate-heights.f32").stat().st_size
    ):
        raise RoadSurfacePatchError("flip-05 aggregate witness binding differs from retained bytes")

    interruption = aggregate.get("interruption")
    if (
        aggregate.get("trialId") != "flip-05"
        or aggregate.get("passes") is not False
        or aggregate.get("finalClassification") != "unresolved_numerical_result"
        or not isinstance(interruption, dict)
        or interruption.get("runnerAfterSnapshotCompleted") is not False
        or interruption.get("independentPostRunSnapshotCompleted") is not True
        or interruption.get("offlineAggregateValidationCompleted") is not False
        or interruption.get("offlineValidationStatus") != "not_run"
        or interruption.get("processTerminated") is not True
        or aggregate.get("offlineValidation", {}).get("status") != "not_run"
        or aggregate.get("candidateOutputStillAbsent") is not True
        or aggregate.get("candidatePublicOutputWritten") is not False
    ):
        raise RoadSurfacePatchError("flip-05 recovery does not preserve its unresolved status")


def validate_reconciled_stage_order(
    raw_root: Path,
    trial_id: str,
    *,
    expected_study_config_sha256: str | None = None,
    expected_input_snapshot_sha256: str | None = None,
    expected_code_hashes: dict[str, str] | None = None,
    base_validator: Callable[..., None],
) -> None:
    """Use the single approved checkpoint-only input transition for later trials."""
    base_validator(
        raw_root,
        trial_id,
        expected_study_config_sha256=expected_study_config_sha256,
    )
    try:
        target_index = TRIAL_ORDER.index(trial_id)
    except ValueError as exc:
        raise RoadSurfacePatchError(f"unrecognized topology study trial id {trial_id!r}") from exc
    for previous_id in TRIAL_ORDER[:target_index]:
        previous = raw_root / previous_id
        attempt = _read_json(previous / "attempt.json", f"{previous_id} attempt")
        aggregate = _read_json(previous / "offline-aggregate.json", f"{previous_id} aggregate")
        recorded_codes = attempt.get("codeHashes")
        if not isinstance(recorded_codes, dict):
            raise RoadSurfacePatchError(f"{previous_id} has no comparable implementation hashes")
        if expected_code_hashes is not None:
            if not isinstance(expected_code_hashes, dict):
                raise RoadSurfacePatchError("current implementation hash map is invalid")
            if any(expected_code_hashes.get(key) != value for key, value in recorded_codes.items()):
                raise RoadSurfacePatchError(f"{previous_id} implementation hashes changed")

        if previous_id == "flip-05":
            _validate_reconciled_flip_record(
                raw_root,
                attempt,
                aggregate,
                expected_input_snapshot_sha256=expected_input_snapshot_sha256,
            )
        elif expected_input_snapshot_sha256 is not None and (
            attempt.get("inputSnapshotSha256") != expected_input_snapshot_sha256
        ):
            raise RoadSurfacePatchError(
                f"prerequisite trial {previous_id} used a different current input snapshot"
            )
