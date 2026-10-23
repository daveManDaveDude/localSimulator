from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from torquay_pipeline.road_surface import RoadSurfaceError
from torquay_pipeline.road_surface_patch import RoadSurfacePatchError
from torquay_pipeline.road_surface_study import (
    STUDY_DIRECTORY,
    preflight_study_trial_paths,
    validate_study_stage_order,
)


def _load_study_runner():
    script = Path(__file__).parents[1] / "scripts/run_teignmouth_topology_study.py"
    spec = importlib.util.spec_from_file_location("run_teignmouth_topology_study", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_study_preflight_accepts_only_absent_private_trial_without_writes(tmp_path: Path) -> None:
    paths = preflight_study_trial_paths(tmp_path, "flip-05")

    assert paths.trial == tmp_path / STUDY_DIRECTORY / "flip-05"
    assert not paths.raw_root.exists()
    assert not paths.trial.exists()
    assert not paths.candidate.exists()


@pytest.mark.parametrize("trial_id", ["../flip-05", "flip-05/child", "FLIP-05", "other"])
def test_study_preflight_rejects_trial_path_aliases(tmp_path: Path, trial_id: str) -> None:
    with pytest.raises(RoadSurfacePatchError, match="unrecognized"):
        preflight_study_trial_paths(tmp_path, trial_id)
    assert not (tmp_path / STUDY_DIRECTORY).exists()


def test_study_preflight_rejects_existing_trial_without_changing_it(tmp_path: Path) -> None:
    existing = tmp_path / STUDY_DIRECTORY / "flip-05"
    existing.mkdir(parents=True)
    marker = existing / "attempt.json"
    marker.write_bytes(b"owned elsewhere")

    with pytest.raises(RoadSurfacePatchError, match="already exists"):
        preflight_study_trial_paths(tmp_path, "flip-05")

    assert marker.read_bytes() == b"owned elsewhere"


def test_study_preflight_rejects_unowned_parent_entry(tmp_path: Path) -> None:
    raw_root = tmp_path / STUDY_DIRECTORY
    raw_root.mkdir(parents=True)
    unrelated = raw_root / "backup"
    unrelated.write_bytes(b"preserve")

    with pytest.raises(RoadSurfacePatchError, match="unowned or unsafe"):
        preflight_study_trial_paths(tmp_path, "flip-05")

    assert unrelated.read_bytes() == b"preserve"


def test_study_preflight_rejects_symlinked_evidence_root(tmp_path: Path) -> None:
    evidence_parent = tmp_path / ".codex" / "evidence"
    evidence_parent.mkdir(parents=True)
    target = tmp_path / "outside"
    target.mkdir()
    link = evidence_parent / "teignmouth-topology-study"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink creation is unavailable: {exc}")

    with pytest.raises(RoadSurfaceError, match="symlink or junction"):
        preflight_study_trial_paths(tmp_path, "flip-05")

    assert list(target.iterdir()) == []


def test_study_preflight_rejects_wrong_evidence_root_from_config(tmp_path: Path) -> None:
    config = {"run_policy": {"raw_evidence_directory": ".codex/evidence/other"}}

    with pytest.raises(RoadSurfacePatchError, match="not allowlisted"):
        preflight_study_trial_paths(tmp_path, "flip-05", study_config=config)

    assert not (tmp_path / STUDY_DIRECTORY).exists()


def test_study_preflight_rejects_overlap_with_protected_input(tmp_path: Path, monkeypatch) -> None:
    from torquay_pipeline import road_surface_study

    monkeypatch.setattr(
        road_surface_study, "STUDY_DIRECTORY", Path("public/worlds/torquay-road-surface-preview")
    )

    with pytest.raises(RoadSurfacePatchError, match="overlaps protected"):
        preflight_study_trial_paths(tmp_path, "flip-05")


def test_stage_order_requires_completed_failure_and_stops_after_pass(tmp_path: Path) -> None:
    raw_root = tmp_path / STUDY_DIRECTORY
    flip = raw_root / "flip-05"
    flip.mkdir(parents=True)
    (flip / "attempt.json").write_text("{}", encoding="utf-8")
    aggregate_path = flip / "offline-aggregate.json"
    aggregate_path.write_text(
        json.dumps({"passes": False, "finalClassification": "failed_offline_gate"}),
        encoding="utf-8",
    )

    validate_study_stage_order(raw_root, "road-05")
    aggregate_path.write_text(
        json.dumps({"passes": True, "finalClassification": "offline_pass"}),
        encoding="utf-8",
    )
    with pytest.raises(RoadSurfacePatchError, match="passed"):
        validate_study_stage_order(raw_root, "road-05")
    assert aggregate_path.is_file()


def test_stage_order_does_not_admit_partial_or_missing_prerequisite(tmp_path: Path) -> None:
    raw_root = tmp_path / STUDY_DIRECTORY
    partial = raw_root / "flip-05"
    partial.mkdir(parents=True)
    (partial / "attempt.json").write_text("{}", encoding="utf-8")

    with pytest.raises(RoadSurfacePatchError, match="incomplete"):
        validate_study_stage_order(raw_root, "road-05")

    with pytest.raises(RoadSurfacePatchError, match="absent"):
        validate_study_stage_order(tmp_path / "missing", "road-05")


def test_stage_order_rejects_future_trial_directory(tmp_path: Path) -> None:
    future = tmp_path / STUDY_DIRECTORY / "collar-05"
    future.mkdir(parents=True)

    with pytest.raises(RoadSurfacePatchError, match="exists before its required stage order"):
        validate_study_stage_order(tmp_path / STUDY_DIRECTORY, "flip-05")


def test_stage_order_binds_config_input_snapshot_and_code_hashes(tmp_path: Path) -> None:
    raw_root = tmp_path / STUDY_DIRECTORY
    flip = raw_root / "flip-05"
    flip.mkdir(parents=True)
    (flip / "attempt.json").write_text(
        json.dumps(
            {
                "studyConfigSha256": "a" * 64,
                "inputSnapshotSha256": "b" * 64,
                "codeHashes": {"runner.py": "c" * 64},
            }
        ),
        encoding="utf-8",
    )
    (flip / "offline-aggregate.json").write_text(
        json.dumps({"passes": False, "finalClassification": "failed_offline_gate"}),
        encoding="utf-8",
    )

    validate_study_stage_order(
        raw_root,
        "road-05",
        expected_study_config_sha256="a" * 64,
        expected_input_snapshot_sha256="b" * 64,
        expected_code_hashes={"runner.py": "c" * 64},
    )
    with pytest.raises(RoadSurfacePatchError, match="different frozen implementation"):
        validate_study_stage_order(
            raw_root,
            "road-05",
            expected_code_hashes={"runner.py": "d" * 64},
        )


def test_runner_requires_exact_frozen_configs_and_refinement_stage_base(tmp_path: Path) -> None:
    runner = _load_study_runner()
    study, study_digest, base_digest = runner._load_frozen_configs()
    assert study_digest == runner.FROZEN_STUDY_CONFIG_SHA256
    assert base_digest == runner.FROZEN_BASE_CONFIG_SHA256
    assert study["refinement_policy"]["stage_2_requires_all_topology_trials_failed"]

    raw_root = tmp_path
    for trial_id, slope in (("road-05", 4.5), ("collar-05", 3.5)):
        trial = raw_root / trial_id
        trial.mkdir()
        (trial / "attempt.json").write_text(
            json.dumps({"inputSnapshotSha256": "e" * 64}),
            encoding="utf-8",
        )
        (trial / "offline-aggregate.json").write_text(
            json.dumps(
                {
                    "passes": False,
                    "localCorridorLongitudinal": {
                        "teignmouthLocal": {
                            "maximumLocalLateralSlopePercent": slope,
                            "maximumEndpointSpanM": 0.25,
                            "maximumAbsoluteCenterlineDeviationM": 0.08,
                            "maximumAbsoluteSignedGradeChangePercentagePoints": 1.0,
                        }
                    },
                    "compositeTerrain": {
                        "maximumAbsoluteChangeFromSourceM": 2.0,
                        "maximumPositiveAddedGradientMPerM": 0.7,
                    },
                    "completeBuildingFootprints": {
                        "baseDisplacementMaximumAbsoluteM": 1.0,
                        "baseDisplacementP95AbsoluteM": 0.1,
                    },
                    "candidateFloat32Sha256": trial_id,
                }
            ),
            encoding="utf-8",
        )

    selected, record = runner._refinement_base_for_trial("local-025", raw_root)
    assert selected == "collar-05"
    assert record["trialId"] == selected

    local = raw_root / "local-025"
    local.mkdir()
    (local / "attempt.json").write_text(
        json.dumps({"refinementBase": {"trialId": selected}}), encoding="utf-8"
    )
    assert runner._refinement_base_for_trial("local-0125", raw_root)[0] == selected


def test_trial_deadline_uses_one_shared_budget_and_fails_closed() -> None:
    runner = _load_study_runner()

    assert runner._remaining_trial_seconds(10.0, "synthetic solver", now=9.25) == 0.75
    with pytest.raises(RoadSurfacePatchError, match="expired before synthetic QA"):
        runner._remaining_trial_seconds(10.0, "synthetic QA", now=10.0)


def test_refinement_selection_fails_when_both_topologies_lack_gate_metrics(
    tmp_path: Path,
) -> None:
    runner = _load_study_runner()
    for trial_id in ("road-05", "collar-05"):
        trial = tmp_path / trial_id
        trial.mkdir()
        (trial / "attempt.json").write_text("{}", encoding="utf-8")
        (trial / "offline-aggregate.json").write_text("{}", encoding="utf-8")

    with pytest.raises(RoadSurfacePatchError, match="no completed road-aligned topology"):
        runner._refinement_base_for_trial("local-025", tmp_path)
