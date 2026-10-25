"""Synthetic and pinned-input regressions for validation transition v2."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from shapely.geometry import Polygon
from test_road_surface_validation_v1 import _small_patch_surface

from torquay_pipeline import road_surface
from torquay_pipeline import road_surface_patch as patch
from torquay_pipeline.road_surface_patch import PATCH_OFFLINE_GATE_NAMES, RoadSurfacePatchError
from torquay_pipeline.road_surface_validation_transition_v2 import (
    CHECKPOINT_KEY,
    ELIGIBLE_TRIALS,
    EVIDENCE_TREE_KEY,
    WORKFLOW_METADATA_TRANSITION,
    TransitionDeadlineExceeded,
    TransitionDeadlines,
    admit_remaining_trial,
    canonical_digest,
    file_digest,
    phase_for_runner_check,
    tree_digest_excluding,
    validate_consumed_trial_inventory,
    validate_prior_input_transition,
    validate_transition_inputs,
    validate_workflow_metadata,
)

ROOT = Path(__file__).resolve().parents[2]
RAW_TRIALS = ROOT / ".codex/evidence/teignmouth-topology-study"
INVENTORY_PATH = (
    ROOT
    / "docs/milestones/artifacts/Road-surface-treatment/teignmouth-topology-study/profiles/"
    / "consumed-trials-inventory-v2.json"
)
CONFIG_PATH = ROOT / "config/road-surface-teignmouth-topology-transition-v2.json"


def test_deadlines_share_t0_and_keep_distinct_windows() -> None:
    deadlines = TransitionDeadlines(100.0)
    assert deadlines.solver == 220.0
    assert deadlines.validation == 225.0
    assert deadlines.finalization == 235.0
    assert deadlines.remaining_solver(134.0) == 86.0
    assert deadlines.check("validation", 224.0) == 1.0
    assert deadlines.qualification(125.0)
    assert not deadlines.qualification(125.000001)
    with pytest.raises(TransitionDeadlineExceeded):
        deadlines.check("solver", 220.0)


@pytest.mark.parametrize("trial_id", ["flip-05", "road-05"])
def test_consumed_trial_ids_cannot_be_retried(trial_id: str) -> None:
    with pytest.raises(RoadSurfacePatchError, match="consumed and cannot be retried"):
        admit_remaining_trial(trial_id)


@pytest.mark.parametrize("trial_id", ELIGIBLE_TRIALS)
def test_only_remaining_trials_are_admitted(trial_id: str) -> None:
    admit_remaining_trial(trial_id)


def test_frozen_runner_phase_labels_map_to_the_reviewed_cutoffs() -> None:
    assert phase_for_runner_check("pinned input loading") == "solver"
    assert phase_for_runner_check("bounded solver") == "solver"
    assert phase_for_runner_check("solver result validation") == "solver"
    assert phase_for_runner_check("offline aggregate validation") == "validation"
    assert phase_for_runner_check("independent asset assembly") == "validation"
    assert phase_for_runner_check("resource and determinism validation") == "validation"
    with pytest.raises(RoadSurfacePatchError, match="unmapped transition phase"):
        phase_for_runner_check("new unreviewed phase")


def test_tree_digest_excludes_only_the_exact_inventory_file(tmp_path: Path) -> None:
    tree = tmp_path / "evidence"
    (tree / "profiles").mkdir(parents=True)
    (tree / "trial").mkdir()
    (tree / "profiles/inventory.json").write_bytes(b"inventory")
    (tree / "trial/report.json").write_bytes(b"report")
    all_digest = tree_digest_excluding(tree, "missing.json")
    without_inventory = tree_digest_excluding(tree, "profiles/inventory.json")
    assert all_digest != without_inventory
    expected = hashlib.sha256()
    payload = b"report"
    expected.update(b"trial/report.json\0")
    expected.update(str(len(payload)).encode("ascii"))
    expected.update(b"\0")
    expected.update(hashlib.sha256(payload).hexdigest().encode("ascii"))
    expected.update(b"\n")
    assert without_inventory == expected.hexdigest()


def test_consumed_inventory_checks_every_retained_file_and_rejects_tampering(
    tmp_path: Path,
) -> None:
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    temporary_raw = tmp_path / ".codex/evidence/teignmouth-topology-study"
    for trial_id, files in inventory.items():
        destination = temporary_raw / trial_id
        destination.mkdir(parents=True)
        for name in files:
            shutil.copyfile(RAW_TRIALS / trial_id / name, destination / name)

    checked = validate_consumed_trial_inventory(
        tmp_path,
        inventory,
        raw_trial_directory=".codex/evidence/teignmouth-topology-study",
    )
    assert {key: len(value) for key, value in checked.items()} == {
        "flip-05": 10,
        "road-05": 10,
    }

    target = temporary_raw / "road-05/candidate-heights.f32"
    target.write_bytes(target.read_bytes()[:-1] + bytes([target.read_bytes()[-1] ^ 1]))
    with pytest.raises(RoadSurfacePatchError, match="consumed trial bytes differ"):
        validate_consumed_trial_inventory(
            tmp_path,
            inventory,
            raw_trial_directory=".codex/evidence/teignmouth-topology-study",
        )


def test_current_named_input_transition_and_consumed_maps_are_exact() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    road_attempt = json.loads((RAW_TRIALS / "road-05/attempt.json").read_text(encoding="utf-8"))
    current_map = deepcopy(road_attempt["protectedHashesBefore"])
    checkpoint = ROOT / ".codex/torquay-plan-implementation.md"
    current_map[CHECKPOINT_KEY] = file_digest(checkpoint)
    current_map[EVIDENCE_TREE_KEY] = config["input_state_transition"][
        "current_evidence_tree_sha256"
    ]
    current_map["protected:AGENTS.md"] = file_digest(ROOT / "AGENTS.md")
    transition = validate_transition_inputs(ROOT, current_map, config=config)
    assert transition["passed"] is True
    assert transition["checkpointSha256"] == file_digest(checkpoint)
    assert transition["inventory"]["sha256"] == config["consumed_inventory"]["sha256"]

    map_digest = canonical_digest(current_map)
    prior = validate_prior_input_transition(
        RAW_TRIALS,
        "collar-05",
        current_map,
        map_digest,
        config=config,
    )
    assert prior["passed"] is True
    assert len(prior["priorInputTransitions"]) == 2
    assert prior["priorInputTransitions"][0]["trialId"] == "flip-05"
    assert prior["priorInputTransitions"][1]["trialId"] == "road-05"

    tampered = deepcopy(current_map)
    tampered["protected:AGENTS.md"] = "0" * 64
    with pytest.raises(
        RoadSurfacePatchError, match="workflow metadata current protected AGENTS binding differs"
    ):
        validate_prior_input_transition(
            RAW_TRIALS,
            "collar-05",
            tampered,
            canonical_digest(tampered),
            config=config,
        )


def _load_wrapper():
    scripts_path = ROOT / "pipeline/scripts"
    sys.path.insert(0, str(scripts_path))
    try:
        import run_teignmouth_topology_validation_v2 as wrapper
    finally:
        sys.path.remove(str(scripts_path))
    return wrapper


def _install_synthetic_approval_chain(tmp_path: Path, config: dict, wrapper) -> tuple[Path, dict]:
    config = deepcopy(config)
    config["activation"] = {"enabled": True, "status": "approval_chain_required"}
    config_path = tmp_path / "config/road-surface-teignmouth-topology-transition-v2.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps(config, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    code_paths = set(config["legacy_road05_code_hashes"]) | set(config["extension_code_hashes"])
    code_paths.discard("config/road-surface-teignmouth-topology-transition-v2.json")
    for relative in code_paths:
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)

    approval_root = tmp_path / wrapper.APPROVAL_ROOT
    approval_root.mkdir(parents=True)
    review_path = tmp_path / wrapper.SOL_REVIEW_PATH
    receipt_path = tmp_path / wrapper.COORDINATOR_RECEIPT_PATH
    payload = wrapper._approval_payload(config, config_path, tmp_path)
    review = {
        "schema": "teignmouth-validation-v2-sol-review-v1",
        "reviewer": "Sol 6.1",
        "disposition": "PASS",
        **payload,
    }
    review_path.write_text(json.dumps(review, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "schema": "teignmouth-validation-v2-coordinator-acceptance-v1",
        "disposition": "ACCEPTED",
        **payload,
        "independent_sol_review_path": wrapper.SOL_REVIEW_PATH,
        "independent_sol_review_sha256": file_digest(review_path),
    }
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    checkpoint = tmp_path / config["input_state_transition"]["checkpoint_path"]
    checkpoint.parent.mkdir(parents=True)
    marker = wrapper.ACCEPTED_CHECKPOINT_PREFIX + file_digest(receipt_path)
    checkpoint.write_text(f"accepted receipt\n{marker}\n", encoding="utf-8")
    return config_path, config


def test_static_policy_rejects_tampered_limits_and_unapproved_chain() -> None:
    wrapper = _load_wrapper()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    wrapper._validate_fixed_policy(config)

    tampered = deepcopy(config)
    tampered["timing_policy"]["qualification_projected_end_to_end_seconds"] = 999.0
    with pytest.raises(RoadSurfacePatchError, match="timing/resource policy"):
        wrapper._validate_fixed_policy(tampered)

    enabled_alone = deepcopy(config)
    enabled_alone["activation"] = {"enabled": True, "status": "approval_chain_required"}
    with pytest.raises(RoadSurfacePatchError, match="independent Sol review artifact"):
        wrapper.ensure_transition_activated(enabled_alone)


def test_static_bindings_pin_v1_transitive_dependency_and_reject_its_mutation() -> None:
    wrapper = _load_wrapper()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    runtime_path = "pipeline/torquay_pipeline/road_surface_validation_v1.py"
    assert runtime_path in wrapper.EXTENSION_CODE_PATHS
    assert runtime_path in config["extension_code_hashes"]
    wrapper._validate_static_bindings(config)

    tampered = deepcopy(config)
    tampered["extension_code_hashes"][runtime_path] = "0" * 64
    with pytest.raises(RoadSurfacePatchError, match="extension code changed"):
        wrapper._validate_static_bindings(tampered)


def test_exact_sol_review_receipt_and_checkpoint_chain_is_required(tmp_path: Path) -> None:
    wrapper = _load_wrapper()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config_path, activated = _install_synthetic_approval_chain(tmp_path, config, wrapper)
    wrapper.ensure_transition_activated(activated, root=tmp_path, config_path=config_path)

    review_path = tmp_path / wrapper.SOL_REVIEW_PATH
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["config_sha256"] = "a" * 64
    review_path.write_text(json.dumps(review, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(RoadSurfacePatchError, match="exact config, spec and runtime"):
        wrapper.ensure_transition_activated(activated, root=tmp_path, config_path=config_path)


def test_approval_receipt_or_checkpoint_tampering_rejects_activation(tmp_path: Path) -> None:
    wrapper = _load_wrapper()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config_path, activated = _install_synthetic_approval_chain(tmp_path, config, wrapper)
    receipt_path = tmp_path / wrapper.COORDINATOR_RECEIPT_PATH
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["runtime_code_sha256"] = "f" * 64
    receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(RoadSurfacePatchError, match="coordinator receipt"):
        wrapper.ensure_transition_activated(activated, root=tmp_path, config_path=config_path)

    config_path, activated = _install_synthetic_approval_chain(tmp_path / "second", config, wrapper)
    checkpoint = tmp_path / "second" / activated["input_state_transition"]["checkpoint_path"]
    checkpoint.write_text("accepted but unbound\n", encoding="utf-8")
    with pytest.raises(RoadSurfacePatchError, match="checkpoint does not bind"):
        wrapper.ensure_transition_activated(
            activated, root=tmp_path / "second", config_path=config_path
        )


def _runner_globals(base_run=None):
    globals_dict = {
        "validate_study_stage_order": lambda *args, **kwargs: None,
        "_code_hashes": lambda root: {},
        "_frozen_study_input_hashes": lambda *args, **kwargs: {"study": "same"},
        "_protected_hash_snapshot": lambda *args, **kwargs: {"protected": "same"},
        "_load_frozen_configs": lambda: None,
        "_digest": lambda payload: hashlib.sha256(payload).hexdigest(),
        "serialize_offline_report": lambda value: json.dumps(value, sort_keys=True).encode(),
        "_exclusive_write": lambda path, payload: None,
        "assemble_deterministic_candidate_assets": lambda *args, **kwargs: None,
        "validate_candidate_patch_assets": lambda *args, **kwargs: None,
        "_resource_report": lambda *args, **kwargs: None,
        "_final_classification": lambda *args, **kwargs: "offline_pass",
        "MAXIMUM_WALL_SECONDS": 120.0,
        "time": time,
    }
    if base_run is None:
        exec("def run_one_trial(trial_id): return 0, {}", globals_dict)
    else:
        globals_dict["_base_run_one_trial"] = base_run
        exec(
            "def run_one_trial(trial_id): return _base_run_one_trial(trial_id)",
            globals_dict,
        )
    return globals_dict


def _complete_success_aggregate() -> dict[str, object]:
    aggregate: dict[str, object] = {
        "trialId": "collar-05",
        "passes": True,
        "validationComplete": True,
        "gateNames": list(PATCH_OFFLINE_GATE_NAMES),
        "studyAssemblyAndResources": {
            "passes": True,
            "deterministicAssets": True,
            "firstIndependentValidation": {"passes": True},
            "secondIndependentValidation": {"passes": True},
            "resourceLimits": {"passes": True},
            "independentAssetHashes": {
                "first": {"mesh": "a" * 64},
                "second": {"mesh": "a" * 64},
            },
        },
    }
    aggregate.update({name: {"passes": True} for name in PATCH_OFFLINE_GATE_NAMES})
    aggregate.update(
        {
            "protectedHashesMatch": True,
            "protectedHashesBefore": {"protected": "same", "study": "same"},
            "protectedHashesAfter": {"protected": "same", "study": "same"},
        }
    )
    return aggregate


def test_wrapper_keeps_one_real_clock_and_preservation_bool_requires_exact_maps() -> None:
    wrapper = _load_wrapper()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    invocation_start = time.monotonic()
    observed: dict[str, object] = {}

    def base_run(trial_id):
        observed["time_module"] = globals_dict["time"]
        globals_dict["_protected_hash_snapshot"]("root", None)
        globals_dict["_frozen_study_input_hashes"]("root")
        remaining = globals_dict["_remaining_trial_seconds"](
            0.0, "pinned input loading", now=invocation_start + 2.0
        )
        before = {"protected": "same", "study": "same"}
        aggregate = {
            "trialId": trial_id,
            "passes": True,
            "protectedHashesMatch": True,
            "protectedHashesBefore": before,
            "protectedHashesAfter": {"protected": "changed", "study": "same"},
        }
        encoded = globals_dict["serialize_offline_report"](aggregate)
        return 0, {**json.loads(encoded), "remaining": remaining}

    globals_dict = _runner_globals(base_run)
    original_time = globals_dict["time"]
    base_function = globals_dict["run_one_trial"]
    runner_map = {"run_one_trial": base_function, "road_surface": road_surface}
    wrapper._patch_runner(runner_map, config, invocation_start=invocation_start)
    status, result = runner_map["run_one_trial"]("collar-05")
    assert status == 2
    assert observed["time_module"] is original_time
    assert globals_dict["time"] is original_time
    assert result["remaining"] == pytest.approx(118.0)
    assert result["protectedHashesMatch"] is False
    assert result["passes"] is False


def test_protected_source_mutation_between_snapshots_cannot_preserve_pass() -> None:
    wrapper = _load_wrapper()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    invocation_start = time.monotonic()
    protected_calls = 0

    def protected_snapshot(*_args, **_kwargs):
        nonlocal protected_calls
        protected_calls += 1
        return {"protected": "before" if protected_calls == 1 else "mutated"}

    def frozen_inputs(*_args, **_kwargs):
        return {"study": "same"}

    globals_dict = _runner_globals()
    globals_dict["_protected_hash_snapshot"] = protected_snapshot
    globals_dict["_frozen_study_input_hashes"] = frozen_inputs
    globals_dict["_complete_success_aggregate"] = _complete_success_aggregate
    exec(
        "def run_one_trial(trial_id):\n"
        "    before = {**_protected_hash_snapshot('root', None), "
        "**_frozen_study_input_hashes('root')}\n"
        "    after = {**_protected_hash_snapshot('root', None), "
        "**_frozen_study_input_hashes('root')}\n"
        "    aggregate = _complete_success_aggregate()\n"
        "    aggregate.update({'trialId': trial_id, 'protectedHashesBefore': before, "
        "'protectedHashesAfter': after})\n"
        "    return 0, json.loads(serialize_offline_report(aggregate))\n",
        globals_dict,
    )
    globals_dict["json"] = json
    base_run = globals_dict["run_one_trial"]
    runner_map = {"run_one_trial": base_run, "road_surface": road_surface}
    wrapper._patch_runner(runner_map, config, invocation_start=invocation_start)

    status, result = runner_map["run_one_trial"]("collar-05")
    assert status == 2
    assert result["protectedHashesBefore"] == {"protected": "before", "study": "same"}
    assert result["protectedHashesAfter"] == {"protected": "mutated", "study": "same"}
    assert result["protectedHashesMatch"] is False
    assert result["passes"] is False


def test_attempt_serialization_does_not_run_aggregate_finalizer() -> None:
    wrapper = _load_wrapper()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    invocation_start = time.monotonic()
    globals_dict = _runner_globals(lambda trial_id: (0, {}))
    runner_map = {"run_one_trial": globals_dict["run_one_trial"], "road_surface": road_surface}
    wrapper._patch_runner(runner_map, config, invocation_start=invocation_start)
    attempt = {
        "trialId": "collar-05",
        "solverLimits": {"maximumWallSeconds": 120.0},
        "protectedHashesBefore": {"protected": "before"},
    }
    result = json.loads(globals_dict["serialize_offline_report"](attempt))
    assert "passes" not in result
    assert "protectedHashesMatch" not in result
    assert "protectedHashesAfter" not in result


def test_wrapper_serializes_late_clock_as_failed_and_rejects_late_commit() -> None:
    wrapper = _load_wrapper()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    clock = SimpleNamespace(now=100.0)
    fake_time = SimpleNamespace(
        monotonic=lambda: clock.now,
        perf_counter=time.perf_counter,
        time=time.time,
    )
    invocation_start = 100.0
    globals_dict: dict[str, object] = {}
    exec("def run_one_trial(trial_id): return 0, {}", globals_dict)
    globals_dict.update(_runner_globals(globals_dict["run_one_trial"]))
    globals_dict["time"] = fake_time
    base_run = globals_dict["run_one_trial"]
    namespace = base_run.__globals__
    runner_map = {"run_one_trial": base_run, "road_surface": road_surface}
    wrapper._patch_runner(
        runner_map, config, invocation_start=invocation_start, real_time=fake_time
    )
    namespace["_protected_hash_snapshot"]("root", None)
    namespace["_frozen_study_input_hashes"]("root")
    complete = _complete_success_aggregate()
    namespace["_final_classification"](complete, None, None, None)
    wrapper_fn = namespace["serialize_offline_report"]
    clock.now = 239.0
    payload = complete
    encoded = wrapper_fn(payload)
    decoded = json.loads(encoded)
    assert decoded["trialElapsedSeconds"] == 139.0
    assert decoded["passes"] is False
    assert decoded["finalClassification"] == "finalization_timeout"
    with pytest.raises(TransitionDeadlineExceeded, match="before offline aggregate commit"):
        namespace["_exclusive_write"](Path("offline-aggregate.json"), encoded)


@pytest.mark.parametrize(
    ("elapsed", "classification"),
    [(125.001, "unresolved_numerical_result"), (135.0, "finalization_timeout")],
)
def test_stale_incomplete_aggregate_cannot_become_pass_after_cutoff(
    elapsed: float, classification: str
) -> None:
    wrapper = _load_wrapper()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    clock = SimpleNamespace(now=100.0)
    fake_time = SimpleNamespace(
        monotonic=lambda: clock.now,
        perf_counter=time.perf_counter,
        time=time.time,
    )
    globals_dict: dict[str, object] = {}
    exec("def run_one_trial(trial_id): return 0, {}", globals_dict)
    globals_dict.update(_runner_globals(globals_dict["run_one_trial"]))
    globals_dict["time"] = fake_time
    base_run = globals_dict["run_one_trial"]
    namespace = base_run.__globals__
    runner_map = {"run_one_trial": base_run, "road_surface": road_surface}
    wrapper._patch_runner(runner_map, config, invocation_start=100.0, real_time=fake_time)
    namespace["_protected_hash_snapshot"]("root", None)
    namespace["_frozen_study_input_hashes"]("root")

    incomplete = _complete_success_aggregate()
    incomplete.pop("walkClearance")
    namespace["_final_classification"](incomplete, None, None, None)
    assert namespace.get("acceptance_gates_completed_monotonic") is None

    clock.now = 100.0 + elapsed
    result = json.loads(namespace["serialize_offline_report"](incomplete))
    assert result["passes"] is False
    assert result["finalClassification"] == classification
    if elapsed >= 135.0:
        with pytest.raises(TransitionDeadlineExceeded, match="before offline aggregate commit"):
            namespace["_exclusive_write"](Path("offline-aggregate.json"), b"{}")


@pytest.mark.parametrize("elapsed", [125.001, 135.0])
def test_finalizer_cannot_reclassify_incomplete_gates_as_pass(elapsed: float) -> None:
    wrapper = _load_wrapper()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    clock = SimpleNamespace(now=100.0)
    fake_time = SimpleNamespace(monotonic=lambda: clock.now)
    globals_dict = _runner_globals(lambda trial_id: (0, {}))
    globals_dict["time"] = fake_time
    base_run = globals_dict["run_one_trial"]
    namespace = base_run.__globals__
    runner_map = {"run_one_trial": base_run, "road_surface": road_surface}
    wrapper._patch_runner(runner_map, config, invocation_start=100.0, real_time=fake_time)
    namespace["_protected_hash_snapshot"]("root", None)
    namespace["_frozen_study_input_hashes"]("root")
    aggregate = _complete_success_aggregate()
    aggregate.pop("localCorridorLongitudinal")
    namespace["_final_classification"](aggregate, None, None, None)
    clock.now = 100.0 + elapsed
    result = json.loads(namespace["serialize_offline_report"](aggregate))
    assert result["passes"] is False
    assert result["acceptanceGatesCompletedBeforeValidationCutoff"] is False

    if elapsed >= 135.0:
        assert result["finalClassification"] == "finalization_timeout"
    else:
        assert result["finalClassification"] == "unresolved_numerical_result"


def test_finalization_cutoff_during_temp_write_never_promotes_aggregate(tmp_path: Path) -> None:
    wrapper = _load_wrapper()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    readings = iter((234.99, 235.0))
    fake_time = SimpleNamespace(monotonic=lambda: next(readings))
    globals_dict = _runner_globals()
    base_run = globals_dict["run_one_trial"]
    namespace = base_run.__globals__
    runner_map = {"run_one_trial": base_run, "road_surface": road_surface}
    wrapper._patch_runner(runner_map, config, invocation_start=100.0, real_time=fake_time)
    final_path = tmp_path / "offline-aggregate.json"
    temporary_path = tmp_path / "offline-aggregate.json.teignmouth-v2-finalizing"

    with pytest.raises(TransitionDeadlineExceeded, match="before offline aggregate promotion"):
        namespace["_exclusive_write"](final_path, b'{"passes":true}')
    assert not final_path.exists()
    assert not temporary_path.exists()


def test_existing_aggregate_is_never_overwritten_by_finalizer(tmp_path: Path) -> None:
    wrapper = _load_wrapper()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    fake_time = SimpleNamespace(monotonic=lambda: 100.0)
    globals_dict = _runner_globals()
    base_run = globals_dict["run_one_trial"]
    namespace = base_run.__globals__
    runner_map = {"run_one_trial": base_run, "road_surface": road_surface}
    wrapper._patch_runner(runner_map, config, invocation_start=100.0, real_time=fake_time)
    final_path = tmp_path / "offline-aggregate.json"
    final_path.write_bytes(b"prior")

    with pytest.raises(RoadSurfacePatchError, match="already exists"):
        namespace["_exclusive_write"](final_path, b"replacement")
    assert final_path.read_bytes() == b"prior"


def test_unfinished_acceptance_is_failed_after_validation_cutoff() -> None:
    wrapper = _load_wrapper()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    clock = SimpleNamespace(now=100.0)
    fake_time = SimpleNamespace(
        monotonic=lambda: clock.now,
        perf_counter=time.perf_counter,
        time=time.time,
    )
    globals_dict = _runner_globals()
    globals_dict["time"] = fake_time
    base_run = globals_dict["run_one_trial"]
    namespace = base_run.__globals__
    runner_map = {"run_one_trial": base_run, "road_surface": road_surface}
    wrapper._patch_runner(runner_map, config, invocation_start=100.0, real_time=fake_time)
    namespace["_protected_hash_snapshot"]("root", None)
    namespace["_frozen_study_input_hashes"]("root")
    clock.now = 126.0
    aggregate = {
        "trialId": "collar-05",
        "passes": True,
        "validationComplete": True,
        "studyAssemblyAndResources": {"passes": True},
        "protectedHashesMatch": True,
        "protectedHashesBefore": {"protected": "same", "study": "same"},
        "protectedHashesAfter": {"protected": "same", "study": "same"},
    }
    result = json.loads(namespace["serialize_offline_report"](aggregate))
    assert result["acceptanceGatesCompletedBeforeValidationCutoff"] is False
    assert result["passes"] is False
    assert result["finalClassification"] == "unresolved_numerical_result"


def test_validation_cutoff_includes_asset_and_resource_checks() -> None:
    deadlines = TransitionDeadlines(10.0)
    with pytest.raises(TransitionDeadlineExceeded):
        deadlines.check(phase_for_runner_check("independent asset assembly"), 135.0)
    with pytest.raises(TransitionDeadlineExceeded):
        deadlines.check(phase_for_runner_check("resource and determinism validation"), 135.0)


def test_bounded_validation_subphase_checks_deadline_after_work() -> None:
    wrapper = _load_wrapper()
    clock = SimpleNamespace(now=100.0)
    deadlines = TransitionDeadlines(100.0)
    invoked = []

    def completes_after_cutoff() -> str:
        invoked.append(True)
        clock.now = 225.0
        return "late"

    with pytest.raises(TransitionDeadlineExceeded, match="validation cutoff reached"):
        wrapper._run_validation_phase(
            completes_after_cutoff,
            (),
            {},
            deadlines=deadlines,
            clock=lambda: clock.now,
            label="synthetic-long-gate",
        )
    assert invoked == [True]

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    with pytest.raises(RoadSurfacePatchError, match="disabled pending exact Sol review"):
        wrapper.ensure_transition_activated(config)

    activation_probe = deepcopy(config)
    activation_probe["activation"] = {"enabled": True, "status": "approved"}
    with pytest.raises(RoadSurfacePatchError, match="activation state"):
        wrapper.ensure_transition_activated(activation_probe)

    invocation_start = time.monotonic()
    globals_dict = _runner_globals()
    globals_dict["invocation_start"] = invocation_start
    exec(
        "def run_one_trial(trial_id):\n"
        "    remaining = _remaining_trial_seconds(0.0, 'pinned input loading', "
        "now=invocation_start + 2.0)\n"
        "    return 0, {'trialId': trial_id, 'remaining': remaining}\n",
        globals_dict,
    )
    base_run = globals_dict["run_one_trial"]
    runner_map = {"run_one_trial": base_run, "road_surface": object()}
    wrapper._patch_runner(
        runner_map,
        config,
        invocation_start=invocation_start,
    )
    assert runner_map["run_one_trial"] is globals_dict["run_one_trial"]
    assert runner_map["run_one_trial"] is not base_run
    status, result = runner_map["run_one_trial"]("collar-05")
    assert status == 2
    assert result["trialId"] == "collar-05"
    assert result["remaining"] == pytest.approx(118.0)


def test_patched_offline_validator_dispatch_supervises_and_discards_late_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    wrapper = _load_wrapper()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    clock = SimpleNamespace(now=100.0)
    fake_time = SimpleNamespace(
        monotonic=lambda: clock.now,
        perf_counter=time.perf_counter,
        time=time.time,
    )
    observed: dict[str, bool] = {}

    # Give this synthetic validator a filename outside the workspace so it
    # returns after advancing time. The supervisor must reject that late result
    # in its post-call deadline check and synthesize unavailable gate records.
    validator_globals: dict[str, object] = {
        "clock": clock,
        "sys": sys,
        "observed": observed,
        "_complete_success_aggregate": _complete_success_aggregate,
    }
    exec(
        compile(
            "def late_validator(surface, influence, constraints, solver_report, "
            "accepted_preview_hashes, *, context, **kwargs):\n"
            "    observed['trace_installed'] = sys.gettrace() is not None\n"
            "    clock.now = 226.0\n"
            "    return _complete_success_aggregate(), context\n",
            str(tmp_path.parent / "late_offline_validator_probe.py"),
            "exec",
        ),
        validator_globals,
    )
    monkeypatch.setattr(
        wrapper, "validate_offline_candidate_v2", validator_globals["late_validator"]
    )

    globals_dict = _runner_globals()
    base_run = globals_dict["run_one_trial"]
    runner_map = {"run_one_trial": base_run, "road_surface": road_surface}
    wrapper._patch_runner(
        runner_map,
        config,
        invocation_start=100.0,
        real_time=fake_time,
    )
    namespace = base_run.__globals__

    report = namespace["validate_offline_candidate"](
        _small_patch_surface(),
        Polygon(),
        [],
        {"converged": True, "candidateFloat32Sha256": "a" * 64},
        patch.ACCEPTED_PREVIEW_HASHES,
    )

    assert observed["trace_installed"] is True
    assert sys.gettrace() is None
    assert report["passes"] is False
    assert report["validationComplete"] is False
    assert report["validationStatus"] == "incomplete_deadline"
    assert report["deadlineExceededDuringPhase"] == "post-solver offline validation"
    for gate in PATCH_OFFLINE_GATE_NAMES:
        assert report[gate]["passes"] is False
        assert report[gate]["available"] is False
        assert report[gate]["status"] == "unavailable_deadline"


def test_workflow_metadata_transition_rejects_changed_authorization_or_archive(tmp_path):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    policy = WORKFLOW_METADATA_TRANSITION
    for key in (
        "agents_path",
        "agents_before_path",
        "checkpoint_before_path",
        "archive_manifest_path",
        "authorization_path",
    ):
        relative = policy[key]
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    current = {"protected:AGENTS.md": policy["current_agents_sha256"]}
    assert validate_workflow_metadata(tmp_path, current, config=config)["passed"]
    tampered = deepcopy(config)
    tampered["input_state_transition"]["workflow_metadata_transition"]["current_agents_sha256"] = (
        "0" * 64
    )
    with pytest.raises(RoadSurfacePatchError, match="exact authorization"):
        validate_workflow_metadata(tmp_path, current, config=tampered)
    archive = tmp_path / policy["agents_before_path"]
    archive.write_bytes(archive.read_bytes() + b"changed")
    with pytest.raises(RoadSurfacePatchError, match="bound bytes changed"):
        validate_workflow_metadata(tmp_path, current, config=config)
