"""Run the opt-in Teignmouth transition under a whole-tree Windows Job cap."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from torquay_pipeline.road_surface_memory_admission import (  # noqa: E402
    Availability,
    fresh_availability,
    guarded_job_limit,
    system_page_size_bytes,
)
from torquay_pipeline.road_surface_validation_process_v1 import (  # noqa: E402
    ProcessStartupError,
    WindowsJob,
)

RUNNER = ROOT / "pipeline/scripts/run_teignmouth_topology_validation_v2.py"
T0_ENV = "TVW_TEIGNMOUTH_T0_MONOTONIC"
JOB_ENV = "TVW_TEIGNMOUTH_OUTER_JOB_NAME"
LIMIT_ENV = "TVW_TEIGNMOUTH_OUTER_JOB_COMMIT_LIMIT"
PERMIT_PATH = ROOT / ".codex/evidence/teignmouth-topology-study/collar-05-dispatch-permit.json"
CONSUMED_PERMIT_PATH = ROOT / (
    ".codex/evidence/teignmouth-topology-study/collar-05-dispatch-permit.consumed.json"
)
CONFIG_PATH = ROOT / "config/road-surface-teignmouth-topology-transition-v2.json"
REVIEW_PATH = (
    ROOT / "docs/milestones/artifacts/Teignmouth-topology-validation-v2/independent-sol-review.json"
)
RECEIPT_PATH = (
    ROOT / "docs/milestones/artifacts/Teignmouth-topology-validation-v2/coordinator-acceptance.json"
)
MAXIMUM_SECONDS = 135.0
CLEANUP_RESERVE_SECONDS = 1.0
WORK_STOP_SECONDS = MAXIMUM_SECONDS - CLEANUP_RESERVE_SECONDS


def _restore_environment(original: dict[str, str | None]) -> None:
    for name, value in original.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime_hashes(config: dict[str, Any]) -> dict[str, str]:
    hashes = dict(config.get("legacy_road05_code_hashes", {}))
    for relative, digest in config.get("extension_code_hashes", {}).items():
        if relative in hashes and hashes[relative] != digest:
            raise ValueError(f"conflicting runtime file binding: {relative}")
        hashes[relative] = digest
    hashes.pop("config/road-surface-teignmouth-topology-transition-v2.json", None)
    for relative, digest in hashes.items():
        path = ROOT / relative
        if path.is_symlink() or not path.is_file() or _sha256(path) != digest:
            raise ValueError(f"runtime file does not match its exact binding: {relative}")
    return dict(sorted(hashes.items()))


def _assert_plain_path(path: Path) -> None:
    root = ROOT.resolve(strict=True)
    target = path.resolve(strict=True)
    try:
        relative = target.relative_to(root)
    except ValueError as exc:
        raise ValueError("permit path escapes the project root") from exc
    current = root
    for part in relative.parts:
        current = current / part
        info = current.lstat()
        if current.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("permit path contains a symlink or reparse point")


def consume_dispatch_permit(config_path: Path, trial: str) -> dict[str, Any]:
    """Atomically consume the exact one-use permit before starting Python work."""
    requested = config_path if config_path.is_absolute() else ROOT / config_path
    if os.path.normcase(str(requested.resolve(strict=True))) != os.path.normcase(
        str(CONFIG_PATH.resolve(strict=True))
    ):
        raise ValueError("dispatch permit only applies to the exact v2 config")
    raw_config = CONFIG_PATH.read_bytes()
    config = json.loads(raw_config)
    if config.get("activation") != {
        "enabled": True,
        "status": "approval_chain_required",
    }:
        raise ValueError("transition activation has not passed its independent approval gate")
    runtime_hashes = _runtime_hashes(config)
    runtime_digest = hashlib.sha256(
        json.dumps(
            runtime_hashes, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    ).hexdigest()
    if not REVIEW_PATH.is_file() or not RECEIPT_PATH.is_file():
        raise ValueError("exact independent review and coordinator receipt are required")
    if CONSUMED_PERMIT_PATH.exists():
        raise ValueError("the one-use collar-05 dispatch permit was already consumed")
    _assert_plain_path(PERMIT_PATH)
    permit = json.loads(PERMIT_PATH.read_bytes())
    expected = {
        "schema": "teignmouth-one-use-dispatch-permit-v1",
        "disposition": "AUTHORIZED",
        "transitionId": config["transition_id"],
        "trialId": "collar-05",
        "configSha256": hashlib.sha256(raw_config).hexdigest(),
        "specSha256": _sha256(ROOT / config["pinned_inputs"]["transition_spec_path"]),
        "runtimeCodeSha256": runtime_digest,
        "independentSolReviewSha256": _sha256(REVIEW_PATH),
        "coordinatorAcceptanceSha256": _sha256(RECEIPT_PATH),
    }
    if (
        not isinstance(permit, dict)
        or trial != "collar-05"
        or set(permit) != set(expected) | {"permitId"}
    ):
        raise ValueError("dispatch permit schema or one-use trial binding is invalid")
    if any(permit.get(key) != value for key, value in expected.items()):
        raise ValueError("dispatch permit does not bind the exact reviewed transition")
    if not isinstance(permit["permitId"], str) or not re.fullmatch(
        r"[0-9a-f]{32}", permit["permitId"]
    ):
        raise ValueError("dispatch permit id is malformed")
    try:
        os.link(PERMIT_PATH, CONSUMED_PERMIT_PATH)
        PERMIT_PATH.unlink()
    except OSError as exc:
        raise ValueError(f"cannot atomically consume the one-use dispatch permit: {exc}") from exc
    return {
        "permitPath": str(PERMIT_PATH.relative_to(ROOT)),
        "consumedPermitPath": str(CONSUMED_PERMIT_PATH.relative_to(ROOT)),
        "permitSha256": _sha256(CONSUMED_PERMIT_PATH),
        "permitId": permit["permitId"],
        "consumedBeforeLaunch": True,
    }


def run_guarded(
    *,
    trial: str,
    config_path: Path,
    permit_evidence: dict[str, Any],
    invocation_start: float,
    clock: Callable[[], float] = time.monotonic,
    availability_reader: Callable[[], Availability] = fresh_availability,
    page_size_reader: Callable[[], int] = system_page_size_bytes,
    backend: Any = WindowsJob,
) -> tuple[int, dict[str, Any]]:
    """Launch the numerical entrypoint suspended, bounded and write-once safe."""
    if trial != "collar-05" or permit_evidence.get("consumedBeforeLaunch") is not True:
        raise ValueError("the exact collar-05 one-use permit must be consumed before launch")
    if (
        type(invocation_start) not in (int, float)
        or not math.isfinite(invocation_start)
        or invocation_start < 0
    ):
        raise ValueError("the original finite invocation T0 is required")
    stop_deadline = invocation_start + WORK_STOP_SECONDS
    cleanup_deadline = invocation_start + MAXIMUM_SECONDS
    if clock() >= stop_deadline:
        return 2, {
            "schema": "teignmouth-whole-tree-guardian-v1",
            "invocationStartMonotonicSeconds": invocation_start,
            "workStopSeconds": WORK_STOP_SECONDS,
            "cleanupReserveSeconds": CLEANUP_RESERVE_SECONDS,
            "maximumSeconds": MAXIMUM_SECONDS,
            "trial": trial,
            "configPath": str(config_path),
            "dispatchPermit": dict(permit_evidence),
            "passed": False,
            "cleanupConfirmed": True,
            "error": "invocation preflight consumed the bounded work window",
        }
    availability = availability_reader()
    page_size = page_size_reader()
    commit_limit = guarded_job_limit(availability, page_size)
    if clock() >= stop_deadline:
        return 2, {
            "schema": "teignmouth-whole-tree-guardian-v1",
            "invocationStartMonotonicSeconds": invocation_start,
            "workStopSeconds": WORK_STOP_SECONDS,
            "cleanupReserveSeconds": CLEANUP_RESERVE_SECONDS,
            "maximumSeconds": MAXIMUM_SECONDS,
            "availability": {
                "availablePhysicalBytes": availability.available_physical_bytes,
                "currentProcessCommitAvailableBytes": (
                    availability.current_process_commit_available_bytes
                ),
            },
            "pageSizeBytes": page_size,
            "jobCommitLimitBytes": commit_limit,
            "trial": trial,
            "configPath": str(config_path),
            "dispatchPermit": dict(permit_evidence),
            "passed": False,
            "cleanupConfirmed": True,
            "error": "memory admission consumed the bounded work window",
        }
    job_name = f"Local\\TVW-Teignmouth-{uuid.uuid4().hex}"
    prior_env = {name: os.environ.get(name) for name in (T0_ENV, JOB_ENV, LIMIT_ENV)}
    os.environ[T0_ENV] = repr(invocation_start)
    os.environ[JOB_ENV] = job_name
    os.environ[LIMIT_ENV] = str(commit_limit)

    process_job: Any | None = None
    cleanup_confirmed = False
    result: dict[str, Any] = {
        "schema": "teignmouth-whole-tree-guardian-v1",
        "invocationStartMonotonicSeconds": invocation_start,
        "workStopSeconds": WORK_STOP_SECONDS,
        "cleanupReserveSeconds": CLEANUP_RESERVE_SECONDS,
        "maximumSeconds": MAXIMUM_SECONDS,
        "availability": {
            "availablePhysicalBytes": availability.available_physical_bytes,
            "currentProcessCommitAvailableBytes": (
                availability.current_process_commit_available_bytes
            ),
        },
        "pageSizeBytes": page_size,
        "jobCommitLimitBytes": commit_limit,
        "jobName": job_name,
        "trial": trial,
        "configPath": str(config_path),
        "dispatchPermit": dict(permit_evidence),
        "passed": False,
    }
    try:
        process_job = backend(
            [
                sys.executable,
                "-B",
                str(RUNNER),
                "--transition-config",
                str(config_path),
                "--trial",
                trial,
            ],
            ROOT,
            finalization_deadline=stop_deadline,
            clock=clock,
            commit_limit_bytes=commit_limit,
            job_name=job_name,
        )
        result["containment"] = dict(process_job.admission_evidence)
        if not process_job.wait_exit(stop_deadline, clock=clock):
            result["error"] = "whole-tree work cutoff reached"
            process_job.terminate()
            cleanup_confirmed = process_job.wait_exit(cleanup_deadline, clock=clock)
            result["timedOut"] = True
        else:
            result["exitCode"] = process_job.exit_code()
            cleanup_confirmed = process_job.empty()
            if not cleanup_confirmed:
                result["error"] = "computation supervisor exited with live Job descendants"
                process_job.terminate()
                cleanup_confirmed = process_job.wait_exit(cleanup_deadline, clock=clock)
            if cleanup_confirmed:
                result["memoryObservation"] = process_job.memory_observation()
                elapsed = clock() - invocation_start
                result["elapsedSeconds"] = elapsed
                result["passed"] = bool(
                    result["exitCode"] == 0 and elapsed <= 125.0 and cleanup_confirmed
                )
                if result["exitCode"] != 0:
                    result["error"] = "contained computation returned a failure status"
                elif elapsed > 125.0:
                    result["error"] = "complete trial exceeded the unchanged 125-second gate"
    except ProcessStartupError as exc:
        process_job = exc.job
        result["error"] = str(exc)
        try:
            process_job.terminate()
            cleanup_confirmed = process_job.wait_exit(cleanup_deadline, clock=clock)
        except BaseException as cleanup_error:
            result["cleanupError"] = str(cleanup_error)
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        if process_job is not None:
            try:
                process_job.terminate()
                cleanup_confirmed = process_job.wait_exit(cleanup_deadline, clock=clock)
            except BaseException as cleanup_error:
                result["cleanupError"] = str(cleanup_error)
    finally:
        try:
            if process_job is not None and cleanup_confirmed:
                try:
                    process_job.close()
                except BaseException as close_error:
                    cleanup_confirmed = False
                    result["cleanupError"] = str(close_error)
                    result["passed"] = False
        finally:
            _restore_environment(prior_env)
    result["cleanupConfirmed"] = cleanup_confirmed if process_job is not None else True
    if not cleanup_confirmed and process_job is not None:
        result["passed"] = False
    return (0 if result["passed"] else 2), result


def main(argv: list[str] | None = None) -> int:
    invocation_start = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transition-config", required=True, type=Path)
    parser.add_argument("--trial", required=True, choices=("collar-05",))
    args = parser.parse_args(argv)
    try:
        permit_evidence = consume_dispatch_permit(args.transition_config, args.trial)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, sort_keys=True))
        return 2
    try:
        status, evidence = run_guarded(
            trial=args.trial,
            config_path=args.transition_config,
            permit_evidence=permit_evidence,
            invocation_start=invocation_start,
        )
    except BaseException as exc:
        print(json.dumps({"passed": False, "error": f"{type(exc).__name__}: {exc}"}))
        return 2
    print(json.dumps(evidence, sort_keys=True, separators=(",", ":")))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
