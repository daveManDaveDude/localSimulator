"""External one-shot supervisor for the face-19669 diagnostic on Windows."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from ctypes import wintypes


ISSUE = "Teignmouth-float32-topology-representation-1"
ARTIFACT_ROOT = "docs/milestones/artifacts/Teignmouth-float32-topology"
DIAGNOSTIC_ROOT = f"{ARTIFACT_ROOT}/diagnostic-2"
MANIFEST_RELATIVE = f"{DIAGNOSTIC_ROOT}/input-manifest.json"
RUN_RELATIVE = f"{DIAGNOSTIC_ROOT}/run-1"
INVOCATION_RELATIVE = f"{DIAGNOSTIC_ROOT}/invocation.json"
RUNNER_RELATIVE = "pipeline/scripts/diagnose_teignmouth_overlay_face.py"
SUPERVISOR_RELATIVE = "pipeline/scripts/run_teignmouth_overlay_face_diagnostic.py"
DEADLINE_SECONDS = 120.0
POST_VERIFY_RESERVE_SECONDS = 15.0
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
CREATE_SUSPENDED = 0x00000004
CREATE_NO_WINDOW = 0x08000000
STARTF_USESTDHANDLES = 0x00000100
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
INFINITE = 0xFFFFFFFF


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
    )]


class BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)),
        ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD),
    ]


class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("nLength", wintypes.DWORD), ("lpSecurityDescriptor", wintypes.LPVOID),
        ("bInheritHandle", wintypes.BOOL),
    ]


def _api() -> Any:
    if os.name != "nt":
        raise OSError("the diagnostic supervisor requires Windows Job Objects")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CreateProcessW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
        wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
        ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION),
    ]
    kernel.CreateProcessW.restype = wintypes.BOOL
    kernel.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel.ResumeThread.restype = wintypes.DWORD
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateJobObject.restype = wintypes.BOOL
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(SECURITY_ATTRIBUTES),
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel.GetStdHandle.restype = wintypes.HANDLE
    return kernel


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".pending")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _sha256(path: Path, deadline: float | None = None) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError("wall deadline reached during preservation hashing")
            digest.update(block)
    return digest.hexdigest()


def _verify_manifest(root: Path, manifest_path: Path, deadline: float) -> dict[str, Any]:
    manifest_before = _sha256(manifest_path, deadline)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("schema"), manifest.get("issueId"), manifest.get("diagnosticOrdinal")) != (
        "teignmouth-float32-diagnostic-input-v1", ISSUE, 2
    ):
        raise ValueError("frozen diagnostic manifest identity mismatch")
    failures = []
    checked = 0
    bindings = {}
    for item in manifest.get("files", []):
        relative = item.get("path")
        if not isinstance(relative, str) or relative in bindings:
            failures.append({"path": relative, "reason": "invalid or duplicate binding"})
            continue
        path = (root / relative).resolve(strict=False)
        try:
            canonical = path.relative_to(root).as_posix()
        except ValueError:
            failures.append({"path": relative, "reason": "path escapes repository"})
            continue
        if canonical != relative or not path.is_file():
            failures.append({"path": relative, "reason": "noncanonical or missing file"})
            continue
        size = path.stat().st_size
        digest = _sha256(path, deadline)
        checked += 1
        bindings[relative] = item
        if (size, digest) != (item.get("byteLength"), item.get("sha256")):
            failures.append({"path": relative, "reason": "size or sha256 mismatch"})
    build_manifest_relative = f"{ARTIFACT_ROOT}/build-2/input-manifest.json"
    build_manifest_path = root / build_manifest_relative
    try:
        build_manifest = json.loads(build_manifest_path.read_text(encoding="utf-8"))
        diagnostic = {path: (item.get("byteLength"), item.get("sha256")) for path, item in bindings.items()}
        for item in build_manifest.get("files", []):
            path = item.get("path")
            if diagnostic.get(path) != (item.get("byteLength"), item.get("sha256")):
                failures.append({"path": path, "reason": "build-2 binding absent or changed"})
    except (OSError, ValueError, TypeError) as exc:
        failures.append({"path": build_manifest_relative, "reason": f"build-2 manifest invalid: {exc}"})
    for preservation in (root / ARTIFACT_ROOT).rglob("*preservation*.json"):
        if preservation.is_relative_to(root / RUN_RELATIVE):
            continue
        relative = preservation.relative_to(root).as_posix()
        if relative not in bindings:
            failures.append({"path": relative, "reason": "historical preservation record unbound"})
    manifest_after = _sha256(manifest_path, deadline)
    if manifest_before != manifest_after:
        failures.append({"path": MANIFEST_RELATIVE, "reason": "manifest changed during verification"})
    return {
        "passes": not failures,
        "checkedFileCount": checked,
        "changed": failures,
        "manifestSha256": manifest_after,
        "build2ProtectedBindingCount": len(build_manifest.get("files", [])) if "build_manifest" in locals() else 0,
    }


def _verify_post_manifest(root: Path, manifest: Path, deadline: float,
                          expected_manifest_sha256: str) -> dict[str, Any]:
    result = _verify_manifest(root, manifest, deadline)
    result["expectedManifestSha256"] = expected_manifest_sha256
    result["manifestHashStable"] = result.get("manifestSha256") == expected_manifest_sha256
    if not result["manifestHashStable"]:
        result["passes"] = False
        result["changed"].append({"path": MANIFEST_RELATIVE, "reason": "manifest hash changed across invocation"})
    return result


def _create_log(kernel: Any, path: Path) -> int:
    security = SECURITY_ATTRIBUTES(ctypes.sizeof(SECURITY_ATTRIBUTES), None, True)
    handle = kernel.CreateFileW(str(path), 0x40000000, 0x00000001, ctypes.byref(security), 4, 0x00000080, None)
    if handle in (None, wintypes.HANDLE(-1).value):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(handle)


def _launch_suspended(kernel: Any, root: Path, python: Path, runner: Path, manifest: Path,
                       stdout_path: Path, stderr_path: Path, deadline: float) -> tuple[int, int, int]:
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    job_info = EXTENDED_LIMIT_INFORMATION()
    job_info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                                         ctypes.byref(job_info), ctypes.sizeof(job_info)):
        error = ctypes.get_last_error()
        kernel.CloseHandle(job)
        raise ctypes.WinError(error)
    stdout_handle = _create_log(kernel, stdout_path)
    stderr_handle = _create_log(kernel, stderr_path)
    security = SECURITY_ATTRIBUTES(ctypes.sizeof(SECURITY_ATTRIBUTES), None, True)
    stdin_handle = kernel.CreateFileW("NUL", 0x80000000, 0x00000003, ctypes.byref(security),
                                      3, 0x00000080, None)
    if stdin_handle in (None, wintypes.HANDLE(-1).value):
        error = ctypes.get_last_error()
        kernel.CloseHandle(stdout_handle)
        kernel.CloseHandle(stderr_handle)
        kernel.CloseHandle(job)
        raise ctypes.WinError(error)
    startup = STARTUPINFOW()
    startup.cb = ctypes.sizeof(startup)
    startup.dwFlags = STARTF_USESTDHANDLES
    startup.hStdInput = stdin_handle
    startup.hStdOutput = stdout_handle
    startup.hStdError = stderr_handle
    info = PROCESS_INFORMATION()
    command = subprocess.list2cmdline([str(python), "-B", str(runner), "--input-manifest", str(manifest)])
    command_line = ctypes.create_unicode_buffer(command)
    created = kernel.CreateProcessW(str(python), command_line, None, None, True,
                                    CREATE_SUSPENDED | CREATE_NO_WINDOW, None, str(root),
                                    ctypes.byref(startup), ctypes.byref(info))
    kernel.CloseHandle(stdout_handle)
    kernel.CloseHandle(stderr_handle)
    kernel.CloseHandle(stdin_handle)
    if not created:
        error = ctypes.get_last_error()
        kernel.CloseHandle(job)
        raise ctypes.WinError(error)
    if not kernel.AssignProcessToJobObject(job, info.hProcess):
        error = ctypes.get_last_error()
        kernel.TerminateProcess(info.hProcess, 2)
        remaining_ms = max(0, min(5000, int((deadline - time.monotonic()) * 1000)))
        kernel.WaitForSingleObject(info.hProcess, remaining_ms)
        kernel.CloseHandle(info.hThread)
        kernel.CloseHandle(info.hProcess)
        kernel.CloseHandle(job)
        raise ctypes.WinError(error)
    if kernel.ResumeThread(info.hThread) == 0xFFFFFFFF:
        error = ctypes.get_last_error()
        kernel.TerminateJobObject(job, 2)
        remaining_ms = max(0, min(5000, int((deadline - time.monotonic()) * 1000)))
        kernel.WaitForSingleObject(info.hProcess, remaining_ms)
        kernel.CloseHandle(info.hThread)
        kernel.CloseHandle(info.hProcess)
        kernel.CloseHandle(job)
        raise ctypes.WinError(error)
    kernel.CloseHandle(info.hThread)
    return int(job), int(info.hProcess), int(info.dwProcessId)


def _exit_code(kernel: Any, process: int) -> int | None:
    code = wintypes.DWORD()
    if kernel.GetExitCodeProcess(process, ctypes.byref(code)):
        return None if code.value == 259 else int(code.value)
    return None


def _mirror_if_run_exists(record: dict[str, Any], root: Path) -> None:
    run = root / RUN_RELATIVE
    if run.is_dir():
        _write_json(run / "external-supervisor.json", record)


def main() -> int:
    started = time.monotonic()
    deadline = started + DEADLINE_SECONDS
    root = Path(__file__).resolve().parents[2]
    diagnostic_root = root / DIAGNOSTIC_ROOT
    record_path = root / INVOCATION_RELATIVE
    python = (root / "pipeline/.venv/Scripts/python.exe").resolve()
    runner = root / RUNNER_RELATIVE
    manifest = root / MANIFEST_RELATIVE
    if record_path.exists():
        raise FileExistsError(f"one-shot invocation record already exists: {record_path}")
    record: dict[str, Any] = {
        "schema": "teignmouth-overlay-external-supervisor-v2",
        "issueId": ISSUE,
        "status": "PREFLIGHT_IN_PROGRESS",
        "startedUtc": datetime.now(UTC).isoformat(),
        "wallLimitSeconds": DEADLINE_SECONDS,
        "command": [str(python), "-B", str(runner), "--input-manifest", str(manifest)],
        "processTreeContainment": "Win32 Job Object with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE",
        "killOnJobCloseConfigured": True,
        "candidateBuilt": False,
        "candidateEligibleForServing": False,
    }
    _write_json(record_path, record)
    job = process = None
    timed_out = False
    try:
        if sys.platform != "win32":
            raise OSError("supervisor requires Windows Job Objects")
        if not python.is_file() or not runner.is_file() or not manifest.is_file():
            raise FileNotFoundError("exact interpreter, diagnostic runner or frozen manifest is missing")
        if (root / RUN_RELATIVE).exists():
            raise FileExistsError("run-1 exists; refusing a second attempt")
        before = _verify_manifest(root, manifest, deadline)
        record["preRunPreservation"] = before
        record["inputManifestSha256PreRun"] = before.get("manifestSha256")
        if RUNNER_RELATIVE not in {item.get("path") for item in json.loads(manifest.read_text(encoding="utf-8")).get("files", [])}:
            raise ValueError("diagnostic runner is not bound by the frozen manifest")
        if SUPERVISOR_RELATIVE not in {item.get("path") for item in json.loads(manifest.read_text(encoding="utf-8")).get("files", [])}:
            raise ValueError("external supervisor is not bound by the frozen manifest")
        record["supervisorSha256"] = _sha256(root / SUPERVISOR_RELATIVE, deadline)
        record["diagnosticRunnerSha256"] = _sha256(runner, deadline)
        record["interpreterSha256"] = _sha256(python, deadline)
        if not before["passes"]:
            raise ValueError("pre-run preservation verification failed")
        if time.monotonic() >= deadline:
            raise TimeoutError("deadline reached before launch")
        record["status"] = "READY_TO_LAUNCH"
        record["externalDeadlineUtc"] = datetime.now(UTC).isoformat()
        _write_json(record_path, record)
        kernel = _api()
        job, process, pid = _launch_suspended(
            kernel, root, python, runner, manifest,
            diagnostic_root / "external-runner.stdout.log",
            diagnostic_root / "external-runner.stderr.log",
            deadline,
        )
        record["runnerProcessId"] = pid
        record["status"] = "RUNNING"
        _write_json(record_path, record)
        remaining_ms = max(0, int((deadline - time.monotonic() - POST_VERIFY_RESERVE_SECONDS) * 1000))
        wait_result = kernel.WaitForSingleObject(process, remaining_ms)
        timed_out = wait_result == WAIT_TIMEOUT
        if wait_result not in (WAIT_OBJECT_0, WAIT_TIMEOUT):
            raise ctypes.WinError(ctypes.get_last_error())
        if timed_out:
            record["status"] = "STOP_TIMEOUT"
            record["jobTerminationRequested"] = bool(kernel.TerminateJobObject(job, 124))
            _write_json(record_path, record)
            kernel.WaitForSingleObject(process, min(3000, max(0, int((deadline - time.monotonic()) * 1000))))
        record["childProcessExitCode"] = _exit_code(kernel, process)
        record["timedOut"] = timed_out
        record["jobClosedAfterWait"] = True
        kernel.CloseHandle(job)
        job = None
        if kernel.WaitForSingleObject(process, min(3000, max(0, int((deadline - time.monotonic()) * 1000)))) != WAIT_OBJECT_0:
            record["status"] = "STOP_TIMEOUT"
            record["childTerminationConfirmed"] = False
        else:
            record["childTerminationConfirmed"] = True
        if not record["childTerminationConfirmed"]:
            timed_out = True
        else:
            record["childProcessExitCode"] = _exit_code(kernel, process)
        child_code = record.get("childProcessExitCode")
        record["outerCommandExitCode"] = 124 if timed_out else (child_code if child_code is not None else 2)
        record["status"] = "STOP_TIMEOUT" if timed_out else ("RUNNER_EXITED" if child_code is not None else "RUNNER_EXIT_UNKNOWN")
        try:
            after = _verify_post_manifest(root, manifest, deadline, record["inputManifestSha256PreRun"])
        except Exception as exc:
            after = {"passes": False, "checkedFileCount": 0, "changed": [],
                     "error": {"type": type(exc).__name__, "message": str(exc)},
                     "manifestSha256": None}
            if isinstance(exc, TimeoutError) or time.monotonic() >= deadline:
                timed_out = True
        runner_report_path = root / RUN_RELATIVE / "runner-report.json"
        if runner_report_path.is_file():
            try:
                runner_report = json.loads(runner_report_path.read_text(encoding="utf-8"))
                record["diagnosticRunnerStatus"] = runner_report.get("status")
                record["diagnosticRunnerChosenExitCode"] = runner_report.get("runnerChosenExitCode")
            except (OSError, ValueError):
                record["diagnosticRunnerReportReadError"] = True
        record["postRunPreservation"] = after
        record["inputManifestSha256PostRun"] = after.get("manifestSha256")
        record["manifestHashStable"] = after.get("manifestSha256") == record.get("inputManifestSha256PreRun")
        if timed_out:
            record["status"] = "STOP_TIMEOUT"
            record["outerCommandExitCode"] = 124
        elif not after.get("passes"):
            record["status"] = "STOP_POST_PRESERVATION_MISMATCH"
            record["outerCommandExitCode"] = 2
        elif child_code != 0:
            record["status"] = "RUNNER_NONZERO_EXIT"
        record["elapsedWallSeconds"] = time.monotonic() - started
        _write_json(record_path, record)
        _mirror_if_run_exists(record, root)
        return int(record["outerCommandExitCode"])
    except Exception as exc:
        if job is not None:
            try:
                kernel = _api()
                kernel.TerminateJobObject(job, 2)
                if process is not None:
                    remaining_ms = max(0, min(3000, int((deadline - time.monotonic()) * 1000)))
                    kernel.WaitForSingleObject(process, remaining_ms)
                kernel.CloseHandle(job)
            except Exception:
                pass
        record["status"] = "STOP_TIMEOUT" if time.monotonic() >= deadline or isinstance(exc, TimeoutError) else "PREFLIGHT_OR_SUPERVISOR_ERROR"
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        record["traceback"] = traceback.format_exc()
        if process is not None:
            try:
                kernel = _api()
                record["childProcessExitCode"] = _exit_code(kernel, process)
                kernel.CloseHandle(process)
            except Exception:
                pass
        try:
            if "before" in locals():
                record["preRunPreservation"] = before
            if process is not None:
                try:
                    record["postRunPreservation"] = _verify_post_manifest(
                        root, manifest, deadline, record["inputManifestSha256PreRun"]
                    )
                except Exception as verification_error:
                    record["postRunPreservation"] = {
                        "passes": False, "checkedFileCount": 0, "changed": [],
                        "error": {"type": type(verification_error).__name__, "message": str(verification_error)},
                    }
                    if isinstance(verification_error, TimeoutError) or time.monotonic() >= deadline:
                        record["status"] = "STOP_TIMEOUT"
        finally:
            record["elapsedWallSeconds"] = time.monotonic() - started
            record["outerCommandExitCode"] = 124 if record["status"] == "STOP_TIMEOUT" else 2
            try:
                _write_json(record_path, record)
                _mirror_if_run_exists(record, root)
            except Exception:
                pass
        return 124 if record["status"] == "STOP_TIMEOUT" else 2
    finally:
        if process is not None:
            try:
                _api().CloseHandle(process)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
