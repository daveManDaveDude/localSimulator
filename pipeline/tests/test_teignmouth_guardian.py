"""Synthetic tests for whole-tree memory containment before numerical startup."""

from __future__ import annotations

import hashlib
import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from torquay_pipeline import road_surface_memory_admission as memory

ROOT = Path(__file__).resolve().parents[2]
GUARDIAN = ROOT / "pipeline/scripts/run_teignmouth_topology_guardian.py"


def load_guardian():
    return runpy.run_path(str(GUARDIAN))


def test_guardian_sets_queried_job_ceiling_and_one_t0_before_launch(monkeypatch):
    module = load_guardian()
    observed = {}

    class Job:
        admission_evidence = {
            "jobCommitLimitBytes": 36_864,
            "killOnClose": True,
            "breakawayDisabled": True,
            "limitQueried": True,
            "membershipBeforeResume": True,
        }

        def __init__(self, argv, cwd, **kwargs):
            observed.update(argv=argv, cwd=cwd, kwargs=kwargs)
            observed["t0"] = os.environ[module["T0_ENV"]]
            observed["job_name"] = os.environ[module["JOB_ENV"]]
            observed["limit"] = os.environ[module["LIMIT_ENV"]]

        def wait_exit(self, deadline, *, clock):
            observed["work_deadline"] = deadline
            return True

        def exit_code(self):
            return 0

        def empty(self):
            return True

        def memory_observation(self):
            return {"peakJobCommitBytes": 1234, "peakProcessCommitBytes": 1200}

        def close(self):
            observed["closed"] = True

    for name in (module["T0_ENV"], module["JOB_ENV"], module["LIMIT_ENV"]):
        monkeypatch.delenv(name, raising=False)
    status, evidence = module["run_guarded"](
        trial="collar-05",
        config_path=Path("synthetic-config.json"),
        permit_evidence={"consumedBeforeLaunch": True, "permitId": "synthetic"},
        invocation_start=100.0,
        clock=lambda: 100.0,
        availability_reader=lambda: memory.Availability(100_000, 80_000),
        page_size_reader=lambda: 4096,
        backend=Job,
    )
    assert status == 0 and evidence["passed"] is True
    assert evidence["jobCommitLimitBytes"] == 36_864
    assert evidence["memoryObservation"]["peakJobCommitBytes"] == 1234
    assert observed["t0"] == "100.0"
    assert observed["limit"] == "36864"
    assert observed["kwargs"]["finalization_deadline"] == 234.0
    assert observed["kwargs"]["commit_limit_bytes"] == 36_864
    assert observed["kwargs"]["job_name"] == observed["job_name"]
    assert observed["closed"] is True
    assert module["T0_ENV"] not in os.environ


def test_guardian_timeout_terminates_and_confirms_the_whole_tree(monkeypatch):
    module = load_guardian()
    observed = {"waits": 0}

    class Job:
        admission_evidence = {"membershipBeforeResume": True}

        def __init__(self, *args, **kwargs):
            pass

        def wait_exit(self, deadline, *, clock):
            observed["waits"] += 1
            observed.setdefault("deadlines", []).append(deadline)
            return observed["waits"] > 1

        def terminate(self):
            observed["terminated"] = True

        def empty(self):
            return True

        def close(self):
            observed["closed"] = True

    status, evidence = module["run_guarded"](
        trial="collar-05",
        config_path=Path("synthetic-config.json"),
        permit_evidence={"consumedBeforeLaunch": True, "permitId": "synthetic"},
        invocation_start=100.0,
        clock=lambda: 100.0,
        availability_reader=lambda: memory.Availability(100_000, 80_000),
        page_size_reader=lambda: 4096,
        backend=Job,
    )
    assert status == 2 and evidence["passed"] is False
    assert evidence["cleanupConfirmed"] is True
    assert observed["terminated"] is True
    assert observed["deadlines"] == [234.0, 235.0]
    assert observed["closed"] is True


def test_main_captures_one_t0_before_one_use_permit_preflight(monkeypatch, capsys):
    module = load_guardian()
    events = []

    def clock():
        events.append("clock")
        return 50.0

    def consume(*args):
        events.append("permit")
        return {"consumedBeforeLaunch": True, "permitId": "synthetic"}

    def launch(**kwargs):
        events.append(("launch", kwargs["invocation_start"]))
        return 0, {"passed": True}

    monkeypatch.setattr(module["time"], "monotonic", clock)
    globals_dict = module["main"].__globals__
    monkeypatch.setitem(globals_dict, "consume_dispatch_permit", consume)
    monkeypatch.setitem(globals_dict, "run_guarded", launch)
    assert (
        module["main"](["--transition-config", "synthetic-config.json", "--trial", "collar-05"])
        == 0
    )
    assert events == ["clock", "permit", ("launch", 50.0)]
    assert json.loads(capsys.readouterr().out)["passed"] is True


def test_dispatch_permit_is_exact_bound_and_atomically_one_use(tmp_path, monkeypatch):
    module = load_guardian()
    root = tmp_path
    (root / ".codex/evidence/teignmouth-topology-study").mkdir(parents=True)
    (root / "docs/milestones/artifacts/Teignmouth-topology-validation-v2").mkdir(parents=True)
    (root / "docs").mkdir(exist_ok=True)
    spec = root / "docs/spec.md"
    spec.write_text("spec bytes", encoding="utf-8")
    source = root / "runner.py"
    source.write_text("pass\n", encoding="utf-8")
    review = (
        root
        / "docs/milestones/artifacts/Teignmouth-topology-validation-v2/independent-sol-review.json"
    )
    receipt = (
        root
        / "docs/milestones/artifacts/Teignmouth-topology-validation-v2/coordinator-acceptance.json"
    )
    review.write_text("review", encoding="utf-8")
    receipt.write_text("receipt", encoding="utf-8")
    config_path = root / "config/transition.json"
    config_path.parent.mkdir(parents=True)
    config = {
        "activation": {"enabled": True, "status": "approval_chain_required"},
        "transition_id": "test-transition",
        "pinned_inputs": {"transition_spec_path": "docs/spec.md"},
        "legacy_road05_code_hashes": {"runner.py": hashlib.sha256(source.read_bytes()).hexdigest()},
        "extension_code_hashes": {},
    }
    config_bytes = json.dumps(config, sort_keys=True).encode("utf-8")
    config_path.write_bytes(config_bytes)
    permit_path = root / ".codex/evidence/teignmouth-topology-study/collar-05-dispatch-permit.json"
    consumed_path = (
        root / ".codex/evidence/teignmouth-topology-study/collar-05-dispatch-permit.consumed.json"
    )
    runtime_hashes = {"runner.py": hashlib.sha256(source.read_bytes()).hexdigest()}
    runtime_digest = hashlib.sha256(
        json.dumps(
            runtime_hashes, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()
    permit = {
        "schema": "teignmouth-one-use-dispatch-permit-v1",
        "disposition": "AUTHORIZED",
        "transitionId": "test-transition",
        "trialId": "collar-05",
        "configSha256": hashlib.sha256(config_bytes).hexdigest(),
        "specSha256": hashlib.sha256(spec.read_bytes()).hexdigest(),
        "runtimeCodeSha256": runtime_digest,
        "independentSolReviewSha256": hashlib.sha256(review.read_bytes()).hexdigest(),
        "coordinatorAcceptanceSha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
        "permitId": "a" * 32,
    }
    permit_path.write_text(json.dumps(permit, sort_keys=True), encoding="utf-8")
    guardian_globals = module["consume_dispatch_permit"].__globals__
    for name, value in (
        ("ROOT", root),
        ("CONFIG_PATH", config_path),
        ("PERMIT_PATH", permit_path),
        ("CONSUMED_PERMIT_PATH", consumed_path),
        ("REVIEW_PATH", review),
        ("RECEIPT_PATH", receipt),
    ):
        monkeypatch.setitem(guardian_globals, name, value)
    consumed = module["consume_dispatch_permit"](config_path, "collar-05")
    assert consumed["consumedBeforeLaunch"] is True
    assert consumed["permitId"] == "a" * 32
    assert consumed_path.read_text(encoding="utf-8") == json.dumps(permit, sort_keys=True)
    assert not permit_path.exists()
    with pytest.raises(ValueError, match="already consumed"):
        module["consume_dispatch_permit"](config_path, "collar-05")


def test_transition_runner_refuses_direct_launch_before_numerical_import(monkeypatch):
    for name in (
        "TVW_TEIGNMOUTH_T0_MONOTONIC",
        "TVW_TEIGNMOUTH_OUTER_JOB_NAME",
        "TVW_TEIGNMOUTH_OUTER_JOB_COMMIT_LIMIT",
    ):
        monkeypatch.delenv(name, raising=False)
    runner = ROOT / "pipeline/scripts/run_teignmouth_topology_validation_v2.py"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(runner),
            "--transition-config",
            str(ROOT / "config/road-surface-teignmouth-topology-transition-v2.json"),
            "--trial",
            "collar-05",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "must be launched by run_teignmouth_topology_guardian.py" in result.stderr
