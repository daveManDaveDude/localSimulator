"""Fail-closed paths and stage order for the local topology study."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import road_surface as _road_surface
from .road_surface_patch import PATCH_OUTPUT_FILES, RoadSurfacePatchError

STUDY_DIRECTORY = Path(".codex/evidence/teignmouth-topology-study")
TRIAL_ORDER = ("flip-05", "road-05", "collar-05", "local-025", "local-0125")
RAW_TRIAL_FILES = frozenset(
    {
        "attempt.json",
        "topology.json",
        "constraints.json",
        "candidate-heights.f32",
        "patch-vertices-xz.f64",
        "patch-base-heights.f32",
        "patch-triangles.u32",
        "solver-phase.json",
        "offline-aggregate.json",
        "certificate-verification.json",
    }
)
PREVIOUS_EVIDENCE = Path("docs/milestones/artifacts/Road-surface-treatment")
STUDY_INPUTS = (
    Path("config/road-surface-teignmouth-topology-study.json"),
    Path("docs/milestones/Teignmouth-topology-refinement-spec.md"),
    Path(".gitignore"),
    Path("pipeline/torquay_pipeline/road_surface_topology.py"),
    Path("pipeline/tests/test_road_surface_topology.py"),
    Path("pipeline/torquay_pipeline/road_surface_study.py"),
    Path("pipeline/tests/test_road_surface_study.py"),
    Path("pipeline/scripts/run_teignmouth_topology_study.py"),
)


@dataclass(frozen=True)
class StudyTrialPaths:
    """Canonical private output and reserved candidate paths after preflight."""

    root: Path
    raw_root: Path
    trial: Path
    candidate: Path


def _same_path(first: Path, second: Path) -> bool:
    return os.path.normcase(str(first)) == os.path.normcase(str(second))


def preflight_study_trial_paths(
    project_root: Path,
    trial_id: str,
    *,
    study_config: dict[str, Any] | None = None,
) -> StudyTrialPaths:
    """Reject path aliases, collisions, reparse points and protected overlaps.

    This function performs no directory creation or file writes. The caller must
    complete all source/config preflight before creating ``trial``.
    """
    root = project_root.resolve(strict=True)
    if trial_id not in TRIAL_ORDER:
        raise RoadSurfacePatchError(f"unrecognized topology study trial id {trial_id!r}")

    raw_root = root / STUDY_DIRECTORY
    expected_trial = raw_root / trial_id
    _road_surface._assert_no_reparse_components(raw_root)
    _road_surface._assert_no_reparse_components(expected_trial)
    if not _same_path(expected_trial.resolve(strict=False), expected_trial):
        raise RoadSurfacePatchError("study trial path does not resolve to its exact canonical path")
    if expected_trial.exists():
        raise RoadSurfacePatchError(
            f"study trial already exists; write-once protocol forbids resume/overwrite: {trial_id}"
        )

    evidence_parent = raw_root.parent
    _road_surface._assert_no_reparse_components(evidence_parent)
    if evidence_parent.exists() and not evidence_parent.is_dir():
        raise RoadSurfacePatchError("private evidence parent exists but is not a directory")
    if raw_root.exists():
        if not raw_root.is_dir():
            raise RoadSurfacePatchError(
                "topology study evidence root exists but is not a directory"
            )
        for child in raw_root.iterdir():
            if (
                child.name not in TRIAL_ORDER
                or not child.is_dir()
                or _road_surface._is_reparse_point(child)
            ):
                raise RoadSurfacePatchError(
                    f"topology study evidence root contains an unowned or unsafe entry: {child}"
                )
            _road_surface._assert_no_reparse_components(child)
            for output in child.iterdir():
                if (
                    output.name not in RAW_TRIAL_FILES
                    or output.is_dir()
                    or _road_surface._is_reparse_point(output)
                ):
                    raise RoadSurfacePatchError(
                        f"topology study trial contains an unowned or unsafe entry: {output}"
                    )

    protected = _road_surface._protected_execution_inputs(root) + [
        root / PREVIOUS_EVIDENCE,
        *(root / relative for relative in STUDY_INPUTS),
        root / "docs/milestones/Teignmouth-topology-refinement.md",
        root / "public/worlds/torquay-road-surface-preview",
        root
        / (
            "public/worlds/torquay-poc-001-2km/releases/"
            "616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a"
        ),
    ]
    if study_config is not None:
        raw_directory = study_config.get("run_policy", {}).get("raw_evidence_directory")
        if raw_directory != STUDY_DIRECTORY.as_posix():
            raise RoadSurfacePatchError("study config raw evidence directory is not allowlisted")
    for path in protected:
        _road_surface._assert_no_reparse_components(path)
        if _road_surface._paths_overlap(expected_trial, path):
            raise RoadSurfacePatchError(f"study output overlaps protected input '{path}'")

    candidate = root / _road_surface.TEIGNMOUTH_CANDIDATE_OUTPUT
    try:
        guarded_candidate = _road_surface.guard_output_directory(
            root,
            candidate,
            protected,
            owned_files=PATCH_OUTPUT_FILES,
        )
    except _road_surface.RoadSurfaceError as exc:
        raise RoadSurfacePatchError(f"reserved candidate path preflight failed: {exc}") from exc
    if not _same_path(guarded_candidate, candidate) or guarded_candidate.exists():
        raise RoadSurfacePatchError(
            "reserved public candidate path must remain absent and exactly allowlisted"
        )
    if _road_surface._paths_overlap(expected_trial, guarded_candidate):
        raise RoadSurfacePatchError("private study output overlaps reserved public candidate")

    return StudyTrialPaths(root, raw_root, expected_trial, guarded_candidate)


def validate_study_stage_order(
    raw_root: Path,
    trial_id: str,
    *,
    expected_study_config_sha256: str | None = None,
    expected_input_snapshot_sha256: str | None = None,
    expected_code_hashes: dict[str, str] | None = None,
) -> None:
    """Require completed, failed prior stages before admitting the next trial."""
    try:
        trial_index = TRIAL_ORDER.index(trial_id)
    except ValueError as exc:
        raise RoadSurfacePatchError(f"unrecognized topology study trial id {trial_id!r}") from exc
    if raw_root.exists():
        for later_id in TRIAL_ORDER[trial_index + 1 :]:
            if (raw_root / later_id).exists():
                raise RoadSurfacePatchError(
                    f"trial {later_id} exists before its required stage order"
                )
    if trial_index == 0:
        return
    for previous_id in TRIAL_ORDER[:trial_index]:
        previous = raw_root / previous_id
        if not previous.is_dir():
            raise RoadSurfacePatchError(
                f"trial {trial_id} is out of order; prerequisite {previous_id} is absent"
            )
        attempt_path = previous / "attempt.json"
        aggregate_path = previous / "offline-aggregate.json"
        if not attempt_path.is_file() or not aggregate_path.is_file():
            raise RoadSurfacePatchError(
                f"prerequisite trial {previous_id} is incomplete; study protocol forbids resume"
            )
        import json

        try:
            aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
            attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RoadSurfacePatchError(
                f"prerequisite aggregate is unreadable: {previous_id}"
            ) from exc
        if expected_study_config_sha256 is not None and (
            attempt.get("studyConfigSha256") != expected_study_config_sha256
        ):
            raise RoadSurfacePatchError(
                f"prerequisite trial {previous_id} used a different frozen study config"
            )
        if expected_input_snapshot_sha256 is not None and (
            attempt.get("inputSnapshotSha256") != expected_input_snapshot_sha256
        ):
            raise RoadSurfacePatchError(
                f"prerequisite trial {previous_id} used a different immutable input snapshot"
            )
        if expected_code_hashes is not None and attempt.get("codeHashes") != expected_code_hashes:
            raise RoadSurfacePatchError(
                f"prerequisite trial {previous_id} used a different frozen implementation"
            )
        if aggregate.get("passes") is True:
            raise RoadSurfacePatchError(
                f"prior trial {previous_id} passed; later trial {trial_id} is not eligible"
            )
        if aggregate.get("finalClassification") not in {
            "failed_offline_gate",
            "certified_infeasible",
            "unresolved_numerical_result",
            "failed_topology_or_resource_gate",
        }:
            raise RoadSurfacePatchError(
                f"prerequisite trial {previous_id} lacks a completed failure classification"
            )
