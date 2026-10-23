from __future__ import annotations

import hashlib
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from torquay_pipeline.road_surface_patch import (
    ACCEPTED_PREVIEW_HASHES,
    RoadSurfacePatchError,
)
from torquay_pipeline.road_surface_study import RAW_TRIAL_FILES, STUDY_DIRECTORY
from torquay_pipeline.road_surface_study_reconciliation import (
    CHECKPOINT_HASH_KEY,
    reconcile_interrupted_flip_attempt,
    validate_interrupted_flip_snapshot,
    validate_reconciled_stage_order,
)


def _canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _synthetic_flip_files(
    trial: Path,
) -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
    before = {
        "protected:.codex/torquay-plan-implementation.md": "a" * 64,
        "protected:AGENTS.md": "b" * 64,
        "release:heightfield.f32": "c" * 64,
        **{f"acceptedPreview:{name}": digest for name, digest in ACCEPTED_PREVIEW_HASHES.items()},
    }
    after = dict(before)
    after[CHECKPOINT_HASH_KEY] = "d" * 64
    code = {"road_surface_patch.py": "e" * 64, "road_surface_topology.py": "f" * 64}
    candidate = b"synthetic float32 witness"
    attempt = {
        "studyId": "synthetic-study",
        "trialId": "flip-05",
        "trialOrderIndex": 0,
        "studyConfigSha256": "1" * 64,
        "baseCandidateConfigSha256": "2" * 64,
        "codeHashes": code,
        "inputSnapshotSha256": _canonical_digest(before),
        "protectedHashesBefore": before,
        "candidatePublicOutputWritten": False,
    }
    topology = {"trialId": "flip-05", "passes": True, "vertexCount": 10, "triangleCount": 12}
    solver = {
        "topologyVariant": "flip-05",
        "converged": False,
        "iterations": 2000,
        "maximumIterations": 2000,
        "maximumConstraintResidualM": 0.04508148,
        "elapsedSeconds": 24.88,
        "candidateFloat32Sha256": hashlib.sha256(candidate).hexdigest(),
    }
    certificate = {"status": "not_emitted", "verified": None}
    (trial / "attempt.json").write_text(json.dumps(attempt), encoding="utf-8")
    (trial / "topology.json").write_text(json.dumps(topology), encoding="utf-8")
    (trial / "solver-phase.json").write_text(json.dumps(solver), encoding="utf-8")
    (trial / "certificate-verification.json").write_text(json.dumps(certificate), encoding="utf-8")
    (trial / "candidate-heights.f32").write_bytes(candidate)
    for name in RAW_TRIAL_FILES - {
        "attempt.json",
        "topology.json",
        "solver-phase.json",
        "certificate-verification.json",
        "candidate-heights.f32",
        "offline-aggregate.json",
    }:
        (trial / name).write_bytes(name.encode("ascii"))
    return before, after, code, {"study": "1" * 64, "base": "2" * 64}


def test_interrupted_flip_reconciliation_allows_only_checkpoint_difference(
    tmp_path: Path,
) -> None:
    trial = tmp_path / STUDY_DIRECTORY / "flip-05"
    trial.mkdir(parents=True)
    before, after, code, config_hashes = _synthetic_flip_files(trial)

    result = validate_interrupted_flip_snapshot(
        attempt=json.loads((trial / "attempt.json").read_text(encoding="utf-8")),
        protected_after=after,
        code_hashes_after=code,
        current_study_config_sha256=config_hashes["study"],
        current_base_config_sha256=config_hashes["base"],
        candidate_output_absent=True,
    )

    assert result["verified"]
    assert result["onlyCheckpointChanged"]
    assert result["changedProtectedEntries"] == {
        CHECKPOINT_HASH_KEY: {
            "before": before[CHECKPOINT_HASH_KEY],
            "after": after[CHECKPOINT_HASH_KEY],
        }
    }


@pytest.mark.parametrize("extra_changed_key", ["protected:AGENTS.md", "release:heightfield.f32"])
def test_interrupted_flip_reconciliation_rejects_any_second_hash_difference(
    tmp_path: Path, extra_changed_key: str
) -> None:
    trial = tmp_path / STUDY_DIRECTORY / "flip-05"
    trial.mkdir(parents=True)
    before, after, code, config_hashes = _synthetic_flip_files(trial)
    after[extra_changed_key] = "9" * 64

    with pytest.raises(RoadSurfacePatchError, match="only the coordinator checkpoint"):
        validate_interrupted_flip_snapshot(
            attempt=json.loads((trial / "attempt.json").read_text(encoding="utf-8")),
            protected_after=after,
            code_hashes_after=code,
            current_study_config_sha256=config_hashes["study"],
            current_base_config_sha256=config_hashes["base"],
            candidate_output_absent=True,
        )


def test_interrupted_flip_recovery_writes_only_missing_aggregate_exclusively(
    tmp_path: Path,
) -> None:
    trial = tmp_path / STUDY_DIRECTORY / "flip-05"
    trial.mkdir(parents=True)
    _before, after, code, config_hashes = _synthetic_flip_files(trial)
    existing = {path.name: path.read_bytes() for path in trial.iterdir()}

    report = reconcile_interrupted_flip_attempt(
        tmp_path,
        protected_after=after,
        code_hashes_after=code,
        current_study_config_sha256=config_hashes["study"],
        current_base_config_sha256=config_hashes["base"],
    )

    aggregate_path = trial / "offline-aggregate.json"
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    assert report["passes"] is False
    assert report["finalClassification"] == "unresolved_numerical_result"
    assert aggregate["offlineValidation"]["status"] == "not_run"
    assert aggregate["interruption"]["runnerAfterSnapshotCompleted"] is False
    assert aggregate["candidateOutputStillAbsent"] is True
    assert {
        path.name: path.read_bytes() for path in trial.iterdir() if path != aggregate_path
    } == existing

    with pytest.raises(RoadSurfacePatchError, match="already exists"):
        reconcile_interrupted_flip_attempt(
            tmp_path,
            protected_after=after,
            code_hashes_after=code,
            current_study_config_sha256=config_hashes["study"],
            current_base_config_sha256=config_hashes["base"],
        )
    assert aggregate_path.read_bytes()


def test_interrupted_flip_recovery_failure_writes_no_aggregate(tmp_path: Path) -> None:
    trial = tmp_path / STUDY_DIRECTORY / "flip-05"
    trial.mkdir(parents=True)
    _before, after, code, config_hashes = _synthetic_flip_files(trial)
    existing = {path.name: path.read_bytes() for path in trial.iterdir()}

    with pytest.raises(RoadSurfacePatchError, match="code hashes changed"):
        reconcile_interrupted_flip_attempt(
            tmp_path,
            protected_after=after,
            code_hashes_after={**code, "road_surface_topology.py": "0" * 64},
            current_study_config_sha256=config_hashes["study"],
            current_base_config_sha256=config_hashes["base"],
        )

    assert not (trial / "offline-aggregate.json").exists()
    assert {path.name: path.read_bytes() for path in trial.iterdir()} == existing


def test_reconciled_stage_order_allows_new_snapshot_but_keeps_code_identity(
    tmp_path: Path,
) -> None:
    from torquay_pipeline.road_surface_study import validate_study_stage_order

    raw_root = tmp_path / STUDY_DIRECTORY
    flip = raw_root / "flip-05"
    flip.mkdir(parents=True)
    _before, after, old_code, config_hashes = _synthetic_flip_files(flip)
    report = reconcile_interrupted_flip_attempt(
        tmp_path,
        protected_after=after,
        code_hashes_after=old_code,
        current_study_config_sha256=config_hashes["study"],
        current_base_config_sha256=config_hashes["base"],
    )
    after_digest = report["postInterruptionInputSnapshotSha256"]
    current_code = {**old_code, "reconciliation-runner.py": "8" * 64}

    validate_reconciled_stage_order(
        raw_root,
        "road-05",
        expected_study_config_sha256=config_hashes["study"],
        expected_input_snapshot_sha256=after_digest,
        expected_code_hashes=current_code,
        base_validator=validate_study_stage_order,
    )
    with pytest.raises(RoadSurfacePatchError, match="current input snapshot differs"):
        validate_reconciled_stage_order(
            raw_root,
            "road-05",
            expected_study_config_sha256=config_hashes["study"],
            expected_input_snapshot_sha256="0" * 64,
            expected_code_hashes=current_code,
            base_validator=validate_study_stage_order,
        )
    with pytest.raises(RoadSurfacePatchError, match="implementation hashes changed"):
        validate_reconciled_stage_order(
            raw_root,
            "road-05",
            expected_study_config_sha256=config_hashes["study"],
            expected_input_snapshot_sha256=after_digest,
            expected_code_hashes={**current_code, "road_surface_topology.py": "0" * 64},
            base_validator=validate_study_stage_order,
        )


@pytest.mark.parametrize("tamper", ["flag", "protected_map", "before_map"])
def test_reconciled_stage_order_rejects_forged_recovery_flags_or_maps(
    tmp_path: Path, tamper: str
) -> None:
    from torquay_pipeline.road_surface_study import validate_study_stage_order

    raw_root = tmp_path / STUDY_DIRECTORY
    flip = raw_root / "flip-05"
    flip.mkdir(parents=True)
    _before, after, old_code, config_hashes = _synthetic_flip_files(flip)
    report = reconcile_interrupted_flip_attempt(
        tmp_path,
        protected_after=after,
        code_hashes_after=old_code,
        current_study_config_sha256=config_hashes["study"],
        current_base_config_sha256=config_hashes["base"],
    )
    aggregate_path = flip / "offline-aggregate.json"
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    if tamper == "flag":
        aggregate["interruptionReconciliation"]["verified"] = False
        match = "reconciliation object"
    elif tamper == "protected_map":
        forged = "f" * 64
        aggregate["protectedHashesAfter"][CHECKPOINT_HASH_KEY] = forged
        after_digest = _canonical_digest(aggregate["protectedHashesAfter"])
        change = {
            CHECKPOINT_HASH_KEY: {
                "before": aggregate["protectedHashesBefore"][CHECKPOINT_HASH_KEY],
                "after": forged,
            }
        }
        aggregate["protectedHashDifferences"] = change
        aggregate["postInterruptionInputSnapshotSha256"] = after_digest
        aggregate["interruptionReconciliation"]["afterSnapshotSha256"] = after_digest
        aggregate["interruptionReconciliation"]["changedProtectedEntries"] = change
        match = "current input snapshot differs"
    else:
        aggregate["protectedHashesBefore"]["protected:AGENTS.md"] = "f" * 64
        match = "before map differs"
    aggregate_path.write_text(json.dumps(aggregate), encoding="utf-8")

    with pytest.raises(RoadSurfacePatchError, match=match):
        validate_reconciled_stage_order(
            raw_root,
            "road-05",
            expected_study_config_sha256=config_hashes["study"],
            expected_input_snapshot_sha256=report["postInterruptionInputSnapshotSha256"],
            expected_code_hashes={**old_code, "reconciliation-runner.py": "8" * 64},
            base_validator=validate_study_stage_order,
        )


def test_reconciled_stage_order_rejects_changed_retained_evidence(tmp_path: Path) -> None:
    from torquay_pipeline.road_surface_study import validate_study_stage_order

    raw_root = tmp_path / STUDY_DIRECTORY
    flip = raw_root / "flip-05"
    flip.mkdir(parents=True)
    _before, after, old_code, config_hashes = _synthetic_flip_files(flip)
    report = reconcile_interrupted_flip_attempt(
        tmp_path,
        protected_after=after,
        code_hashes_after=old_code,
        current_study_config_sha256=config_hashes["study"],
        current_base_config_sha256=config_hashes["base"],
    )
    with (flip / "patch-triangles.u32").open("ab") as stream:
        stream.write(b"tampered")

    with pytest.raises(RoadSurfacePatchError, match="retained-file hashes"):
        validate_reconciled_stage_order(
            raw_root,
            "road-05",
            expected_study_config_sha256=config_hashes["study"],
            expected_input_snapshot_sha256=report["postInterruptionInputSnapshotSha256"],
            expected_code_hashes={**old_code, "reconciliation-runner.py": "8" * 64},
            base_validator=validate_study_stage_order,
        )


def test_runpy_wrapper_patches_live_trial_globals_and_hashes_reconciliation_code(
    tmp_path: Path,
) -> None:
    wrapper_path = (
        Path(__file__).resolve().parents[1]
        / "scripts/run_teignmouth_topology_after_reconciliation.py"
    )
    wrapper = runpy.run_path(str(wrapper_path))
    runner_path = tmp_path / "synthetic_runner.py"
    runner_path.write_text(
        "from torquay_pipeline import road_surface\n"
        "base_calls = []\n"
        "def validate_study_stage_order(raw_root, trial_id, **kwargs):\n"
        "    base_calls.append((raw_root, trial_id))\n"
        "    return 'base-validator'\n"
        "def _code_hashes(root):\n"
        "    return {'base': 'a' * 64}\n"
        "def run_one_trial(root):\n"
        "    result = validate_study_stage_order(root, 'flip-05')\n"
        "    return result, _code_hashes(root)\n",
        encoding="utf-8",
    )
    runner = runpy.run_path(str(runner_path))
    live_globals = runner["run_one_trial"].__globals__
    assert live_globals is not runner
    wrapper["_patch_runner"](runner)

    relative_paths = (
        "pipeline/torquay_pipeline/road_surface_study_reconciliation.py",
        "pipeline/scripts/run_teignmouth_topology_after_reconciliation.py",
        "pipeline/tests/test_road_surface_study_reconciliation.py",
    )
    for index, relative in enumerate(relative_paths):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"synthetic-{index}".encode("ascii"))

    result, hashes = runner["run_one_trial"](tmp_path)

    assert result is None
    assert live_globals["base_calls"] == [(tmp_path, "flip-05")]
    assert hashes["base"] == "a" * 64
    for relative in relative_paths:
        expected = hashlib.sha256((tmp_path / relative).read_bytes()).hexdigest()
        assert hashes[relative] == expected


def test_wrapper_reports_preflight_error_as_json_to_stderr_with_exit_two() -> None:
    project_root = Path(__file__).resolve().parents[2]
    wrapper_path = project_root / "pipeline/scripts/run_teignmouth_topology_after_reconciliation.py"
    wrong_config = project_root / "config/road-surface-teignmouth-candidate.json"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(project_root / "pipeline")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    result = subprocess.run(
        [
            sys.executable,
            str(wrapper_path),
            "--config",
            str(wrong_config),
            "--trial",
            "road-05",
        ],
        cwd=project_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 2
    assert result.stdout == ""
    error = json.loads(result.stderr)
    assert error["passes"] is False
    assert "exact frozen topology-study config" in error["error"]
