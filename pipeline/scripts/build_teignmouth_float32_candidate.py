"""Run one reserved, bounded Teignmouth Float32 candidate build."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import multiprocessing
import os
import sys
import time
import traceback
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPOSITORY_ROOT / "config" / "road-surface-teignmouth-float32.json"
EXPECTED_OUTPUT = REPOSITORY_ROOT / "data" / "generated" / "teignmouth-float32-topology"
MAX_BUILD_SECONDS = 180.0
GATE_NAMES = (
    "storedLocalTopology",
    "sourcePerimeterAndPlanes",
    "sourceOverlayAndGradients",
    "actualFloat32Sections",
    "influenceWideRoadOwnership",
    "completeBuildingContact",
    "sharedRoadBuildingWalkSurface",
    "independentDeterministicConfirmation",
)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} root must be an object")
    return payload


def _verify_inputs(manifest: dict[str, Any]) -> dict[str, Any]:
    changed = []
    checked = 0
    for binding in manifest.get("files", []):
        relative = binding.get("path")
        path = (REPOSITORY_ROOT / str(relative)).resolve()
        if REPOSITORY_ROOT.resolve() not in path.parents:
            changed.append({"path": relative, "reason": "binding escapes repository root"})
            continue
        try:
            payload = path.read_bytes()
        except OSError as exc:
            changed.append({"path": relative, "reason": f"unavailable: {exc}"})
            continue
        checked += 1
        digest = hashlib.sha256(payload).hexdigest()
        if len(payload) != binding.get("byteLength") or digest != binding.get("sha256"):
            changed.append({"path": relative, "reason": "size or sha256 changed"})
    return {"passes": not changed, "checkedFileCount": checked, "changed": changed}


def _check_reservation(ledger: dict[str, Any], ordinal: int) -> None:
    if ledger.get("issueId") != "Teignmouth-float32-topology-representation-1":
        raise ValueError("attempt ledger belongs to a different issue")
    budget = ledger.get("budget", {}).get("implementationBuilds", {})
    if budget.get("reserved", 0) < 1 or ordinal != int(budget.get("used", -1)) + 1:
        raise ValueError("requested candidate build ordinal is not reserved in the ledger")


class _PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def _process_peak_working_set(pid: int) -> tuple[int | None, str]:
    if os.name != "nt":
        return None, "unavailable: Windows process memory API is not available"
    try:
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        open_process = kernel32.OpenProcess
        open_process.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        open_process.restype = wintypes.HANDLE
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [wintypes.HANDLE]
        close_handle.restype = wintypes.BOOL
        get_counters = psapi.GetProcessMemoryInfo
        get_counters.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_PROCESS_MEMORY_COUNTERS),
            wintypes.DWORD,
        ]
        get_counters.restype = wintypes.BOOL
        handle = open_process(0x0400 | 0x0010, False, pid)
        if not handle:
            return None, f"unavailable: OpenProcess winerror={ctypes.get_last_error()}"
        try:
            counters = _PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(counters)
            if not get_counters(handle, ctypes.byref(counters), counters.cb):
                return None, f"unavailable: GetProcessMemoryInfo winerror={ctypes.get_last_error()}"
            return int(counters.PeakWorkingSetSize), "measured via GetProcessMemoryInfo"
        finally:
            close_handle(handle)
    except (AttributeError, OSError, TypeError) as exc:
        return None, f"unavailable: {type(exc).__name__}: {exc}"


def _mark_failure_gates(evidence: Path, error_type: str, message: str) -> None:
    path = evidence / "gate-state.json"
    try:
        gates = _read_json(path, "gate state")
    except ValueError:
        gates = {name: {"passes": False, "status": "NOT_EVALUATED"} for name in GATE_NAMES}
    for name in GATE_NAMES:
        if gates.get(name, {}).get("status") == "NOT_EVALUATED":
            gates[name] = {
                "passes": False,
                "status": "UNAVAILABLE_AFTER_FAILURE",
                "reason": f"{error_type}: {message}",
            }
    _write_json(path, gates)


def _propagate_worker_result(logical_result: int) -> None:
    """Map the worker's logical return code to the spawned process exit code."""
    if logical_result != 0:
        raise SystemExit(int(logical_result))


def _select_runner_exit(
    status: str,
    timed_out: bool,
    preservation_passes: bool,
    child_exit_code: int | None,
    logical_worker_code: int | None,
) -> int:
    if (
        status == "PASS"
        and not timed_out
        and preservation_passes
        and child_exit_code == 0
        and logical_worker_code == 0
    ):
        return 0
    return 2


def _worker_build(output: Path, evidence: Path) -> int:
    output.mkdir(parents=True, exist_ok=False)
    report: dict[str, Any] = {
        "schema": "teignmouth-float32-build-report-v1",
        "startedUtc": datetime.now(UTC).isoformat(),
        "issueId": "Teignmouth-float32-topology-representation-1",
        "candidateOutput": str(output),
        "stages": {},
        "candidateEligibleForServing": False,
    }
    _write_json(evidence / "worker-progress.json", {"stage": "config", "status": "RUNNING"})
    try:
        from torquay_pipeline.teignmouth_float32_candidate import (
            assemble_candidate,
            candidate_runtime_manifest,
            construct_local_mesh,
            evaluate_gates,
            load_candidate_config,
            load_candidate_corridor,
        )

        config = load_candidate_config(CONFIG_PATH)
        report["stages"]["config"] = {"passes": True}
        _write_json(
            evidence / "worker-progress.json", {"stage": "source-load", "status": "RUNNING"}
        )
        corridor = load_candidate_corridor(REPOSITORY_ROOT, config)
        report["stages"]["frozenInputs"] = {
            "passes": True,
            "releaseId": corridor.inputs.release_id,
            "sourceHashes": corridor.inputs.source_hashes,
        }
        _write_json(evidence / "worker-progress.json", {"stage": "topology", "status": "RUNNING"})
        mesh, chart = construct_local_mesh(corridor, config.frame, evidence=evidence)
        report["stages"]["localConstruction"] = {
            "passes": True,
            "vertexCount": len(mesh.vertices_xz),
            "triangleCount": len(mesh.triangles),
            "constraintEdgeCount": len(mesh.constraint_edges),
        }
        _write_json(
            evidence / "worker-progress.json",
            {"stage": "serialization-and-gates", "status": "RUNNING"},
        )
        candidate = assemble_candidate(corridor, config.frame, mesh, chart, evidence)
        report["stages"]["offlineGates"] = evaluate_gates(candidate)
        manifest = candidate_runtime_manifest(candidate, config)
        _write_json(output / "candidate-manifest.json", manifest)
        report["candidateEligibleForServing"] = bool(manifest["gates"]["passes"])
        report["status"] = (
            "PASS" if report["candidateEligibleForServing"] else "BLOCKED_GATE_FAILURE"
        )
        _write_json(
            evidence / "worker-progress.json", {"stage": "complete", "status": report["status"]}
        )
    except Exception as exc:
        report["status"] = "BLOCKED_EXCEPTION"
        report["primaryError"] = {"type": type(exc).__name__, "message": str(exc)}
        report["traceback"] = traceback.format_exc()
        try:
            _mark_failure_gates(evidence, type(exc).__name__, str(exc))
        except Exception as telemetry_error:
            report["telemetryError"] = {
                "type": type(telemetry_error).__name__,
                "message": str(telemetry_error),
            }
        _write_json(
            evidence / "worker-progress.json",
            {"stage": "failure", "status": report["status"], "errorType": type(exc).__name__},
        )
    report["logicalWorkerStatus"] = report["status"]
    report["logicalWorkerReturnCode"] = 0 if report["status"] == "PASS" else 2
    report["finishedUtc"] = datetime.now(UTC).isoformat()
    _write_json(evidence / "build-report.json", report)
    return report["logicalWorkerReturnCode"]


def _worker_entry(
    output: Path,
    evidence: Path,
    input_manifest: dict[str, Any],
    ledger: dict[str, Any],
    ordinal: int,
) -> None:
    with (
        (evidence / "worker.stdout.log").open("w", encoding="utf-8") as stdout,
        (evidence / "worker.stderr.log").open("w", encoding="utf-8") as stderr,
        redirect_stdout(stdout),
        redirect_stderr(stderr),
    ):
        logical_result = 2
        logical_status = "BLOCKED_WORKER_LAUNCH"
        try:
            _check_reservation(ledger, ordinal)
            before = _verify_inputs(input_manifest)
            if not before["passes"]:
                raise ValueError("frozen inputs changed before worker execution")
            logical_result = _worker_build(output, evidence)
            try:
                report = _read_json(evidence / "build-report.json", "worker build report")
                logical_status = str(report.get("status", "UNKNOWN"))
            except ValueError:
                logical_status = "BLOCKED_WORKER_REPORT_MISSING"
                logical_result = 2
        except Exception as exc:
            logical_result = 2
            logical_status = "BLOCKED_WORKER_EXCEPTION"
            trace = traceback.format_exc()
            try:
                _mark_failure_gates(evidence, type(exc).__name__, str(exc))
            except Exception as telemetry_error:
                trace += (
                    "\nFailure gate telemetry error: "
                    f"{type(telemetry_error).__name__}: {telemetry_error}"
                )
            _write_json(
                evidence / "build-report.json",
                {
                    "schema": "teignmouth-float32-build-report-v1",
                    "status": logical_status,
                    "primaryError": {"type": type(exc).__name__, "message": str(exc)},
                    "traceback": trace,
                    "candidateEligibleForServing": False,
                    "logicalWorkerStatus": logical_status,
                    "logicalWorkerReturnCode": logical_result,
                },
            )
        _write_json(
            evidence / "worker-process-result.json",
            {"logicalWorkerStatus": logical_status, "logicalWorkerReturnCode": logical_result},
        )
        _propagate_worker_result(logical_result)


def _archive_partial_output(output: Path, evidence: Path) -> str | None:
    if not output.exists():
        return None
    archive = evidence / "partial-candidate-output"
    if archive.exists():
        raise FileExistsError(f"refusing to overwrite preserved partial output: {archive}")
    output.replace(archive)
    return str(archive)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-smoke", action="store_true", help="perform GIS-free imports only")
    parser.add_argument("--output-dir", type=Path, default=EXPECTED_OUTPUT)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--input-manifest", type=Path)
    parser.add_argument("--attempt-ledger", type=Path)
    parser.add_argument("--build-ordinal", type=int)
    args = parser.parse_args(argv)

    pipeline_dir = REPOSITORY_ROOT / "pipeline"
    if str(pipeline_dir) not in sys.path:
        sys.path.insert(0, str(pipeline_dir))
    try:
        from torquay_pipeline.road_surface_float32_frame import Float32LocalFrame
        from torquay_pipeline.teignmouth_float32_candidate import load_candidate_config
    except Exception as exc:
        print(f"import smoke failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if args.import_smoke:
        config = load_candidate_config(CONFIG_PATH)
        print(
            json.dumps(
                {
                    "status": "PASS_IMPORT_ONLY",
                    "frameVersion": Float32LocalFrame().version,
                    "originXYZM": config.frame.to_metadata()["originXYZM"],
                    "candidateBuildExecuted": False,
                },
                sort_keys=True,
            )
        )
        return 0

    if args.input_manifest is None or args.attempt_ledger is None or args.build_ordinal is None:
        parser.error("full builds require manifest, ledger and reserved build ordinal")
    try:
        input_manifest = _read_json(args.input_manifest, "input manifest")
        ledger = _read_json(args.attempt_ledger, "attempt ledger")
        if input_manifest.get("issueId") != "Teignmouth-float32-topology-representation-1":
            raise ValueError("input manifest belongs to another issue")
        _check_reservation(ledger, args.build_ordinal)
    except ValueError as exc:
        parser.error(str(exc))
    output = args.output_dir.resolve()
    if output != EXPECTED_OUTPUT.resolve():
        parser.error(f"output must be exactly {EXPECTED_OUTPUT}")
    if output.exists():
        parser.error("candidate output already exists; refusing overwrite")
    if args.evidence_dir is None:
        parser.error("--evidence-dir is required")
    evidence = args.evidence_dir.resolve()
    if evidence == output or output in evidence.parents:
        parser.error("failure evidence must be outside candidate output")
    before = _verify_inputs(input_manifest)
    if not before["passes"]:
        parser.error("frozen inputs changed before build; see changed paths in correction evidence")
    evidence.mkdir(parents=True, exist_ok=False)
    _write_json(evidence / "pre-run-preservation.json", before)
    _write_json(
        evidence / "gate-state.json",
        {name: {"passes": False, "status": "NOT_EVALUATED"} for name in GATE_NAMES},
    )
    started = time.monotonic()
    peak_bytes: int | None = None
    memory_status = "unavailable: no successful process sample"
    timed_out = False
    process = multiprocessing.get_context("spawn").Process(
        target=_worker_entry,
        args=(output, evidence, input_manifest, ledger, args.build_ordinal),
        name="teignmouth-float32-candidate-build",
    )
    try:
        process.start()
    except Exception as exc:
        elapsed = time.monotonic() - started
        after = _verify_inputs(input_manifest)
        _write_json(evidence / "post-run-preservation.json", after)
        _mark_failure_gates(evidence, type(exc).__name__, str(exc))
        _write_json(
            evidence / "build-report.json",
            {
                "schema": "teignmouth-float32-build-report-v1",
                "status": "BLOCKED_WORKER_START",
                "primaryError": {"type": type(exc).__name__, "message": str(exc)},
                "elapsedSeconds": elapsed,
                "maximumSeconds": MAX_BUILD_SECONDS,
                "peakWorkingSetBytes": None,
                "peakWorkingSetStatus": "unavailable: worker did not start",
                "postRunPreservation": after,
                "candidateEligibleForServing": False,
                "logicalWorkerStatus": "NOT_STARTED",
                "logicalWorkerReturnCode": None,
                "actualChildExitCode": None,
                "runnerChosenExitCode": 2,
                "externalCommandExitCode": None,
                "traceback": traceback.format_exc(),
            },
        )
        _write_json(
            evidence / "supervisor-report.json",
            {
                "elapsedSeconds": elapsed,
                "maximumSeconds": MAX_BUILD_SECONDS,
                "timedOut": False,
                "peakWorkingSetBytes": None,
                "peakWorkingSetStatus": "unavailable: worker did not start",
                "preRunPreservation": before,
                "postRunPreservation": after,
                "actualChildExitCode": None,
                "logicalWorkerReturnCode": None,
                "runnerChosenExitCode": 2,
                "externalCommandExitCode": None,
            },
        )
        return 2
    while process.is_alive():
        sample, sample_status = _process_peak_working_set(process.pid)
        if sample is not None:
            peak_bytes = max(peak_bytes or 0, sample)
            memory_status = sample_status
        elif memory_status.startswith("unavailable"):
            memory_status = sample_status
        elapsed = time.monotonic() - started
        if elapsed >= MAX_BUILD_SECONDS:
            timed_out = True
            process.kill()
            break
        time.sleep(0.2)
    process.join()
    child_exit_code = process.exitcode
    elapsed = time.monotonic() - started
    after = _verify_inputs(input_manifest)
    _write_json(evidence / "post-run-preservation.json", after)
    try:
        report = _read_json(evidence / "build-report.json", "worker build report")
    except ValueError:
        report = {"schema": "teignmouth-float32-build-report-v1", "stages": {}}
    try:
        worker_result = _read_json(evidence / "worker-process-result.json", "worker result")
    except ValueError:
        worker_result = {}
    logical_worker_code = worker_result.get("logicalWorkerReturnCode")
    logical_worker_status = worker_result.get(
        "logicalWorkerStatus", report.get("logicalWorkerStatus", "NOT_RECORDED")
    )
    report.update(
        {
            "elapsedSeconds": elapsed,
            "maximumSeconds": MAX_BUILD_SECONDS,
            "peakWorkingSetBytes": peak_bytes,
            "peakWorkingSetStatus": memory_status,
            "postRunPreservation": after,
            "candidateEligibleForServing": False
            if timed_out or not after["passes"]
            else bool(report.get("candidateEligibleForServing")),
        }
    )
    if timed_out:
        report["status"] = "TIMEOUT"
        report["primaryError"] = {
            "type": "BuildTimeout",
            "message": f"exceeded {MAX_BUILD_SECONDS:.0f} seconds",
        }
        _mark_failure_gates(evidence, "BuildTimeout", report["primaryError"]["message"])
    elif not after["passes"]:
        report["status"] = "BLOCKED_PRESERVATION_MISMATCH"
        report["primaryError"] = {
            "type": "ProtectedInputChanged",
            "message": "one or more bound inputs changed during build",
        }
    elif not timed_out and logical_worker_code is None:
        report["status"] = "BLOCKED_WORKER_RESULT_MISSING"
        report["primaryError"] = {
            "type": "WorkerResultMissing",
            "message": "worker did not persist its logical result",
        }
    elif (
        not timed_out
        and child_exit_code is not None
        and logical_worker_code is not None
        and child_exit_code != logical_worker_code
    ):
        report["status"] = "BLOCKED_WORKER_EXIT_MISMATCH"
        report["primaryError"] = {
            "type": "WorkerExitMismatch",
            "message": (
                f"logical result {logical_worker_code} differs from child exit {child_exit_code}"
            ),
        }
    partial_output = None
    if report.get("status") != "PASS":
        try:
            partial_output = _archive_partial_output(output, evidence)
        except OSError as exc:
            report["partialOutputPreservationError"] = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
    report["partialOutputArchivedToEvidence"] = partial_output
    runner_exit_code = _select_runner_exit(
        str(report.get("status", "UNKNOWN")),
        timed_out,
        bool(after["passes"]),
        child_exit_code,
        logical_worker_code,
    )
    report["logicalWorkerStatus"] = logical_worker_status
    report["logicalWorkerReturnCode"] = logical_worker_code
    report["actualChildExitCode"] = child_exit_code
    report["runnerChosenExitCode"] = runner_exit_code
    report["externalCommandExitCode"] = None
    report["externalCommandExitCapture"] = (
        "not observable by runner; caller records it if available"
    )
    if runner_exit_code != 0:
        report["candidateEligibleForServing"] = False
    _write_json(evidence / "build-report.json", report)
    _write_json(
        evidence / "supervisor-report.json",
        {
            "elapsedSeconds": elapsed,
            "maximumSeconds": MAX_BUILD_SECONDS,
            "timedOut": timed_out,
            "peakWorkingSetBytes": peak_bytes,
            "peakWorkingSetStatus": memory_status,
            "preRunPreservation": before,
            "postRunPreservation": after,
            "logicalWorkerStatus": logical_worker_status,
            "logicalWorkerReturnCode": logical_worker_code,
            "actualChildExitCode": child_exit_code,
            "runnerChosenExitCode": runner_exit_code,
            "externalCommandExitCode": None,
        },
    )
    print(
        json.dumps(
            {
                "status": report.get("status", "UNKNOWN"),
                "elapsedSeconds": elapsed,
                "timedOut": timed_out,
                "runnerChosenExitCode": runner_exit_code,
                "evidence": str(evidence),
            },
            sort_keys=True,
        )
    )
    return runner_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
