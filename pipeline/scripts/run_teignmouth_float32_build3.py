"""Fixed-path, one-shot supervisor for Teignmouth Float32 build 3."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import time
import traceback
import winreg
from ctypes import wintypes
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ISSUE = "Teignmouth-float32-topology-representation-1"
ROOT = Path(__file__).absolute().parents[2]
BUILD3_RELATIVE = "docs/milestones/artifacts/Teignmouth-float32-topology/build-3"
BUILD3 = ROOT / BUILD3_RELATIVE
INPUT_MANIFEST = BUILD3 / "input-manifest.json"
LEDGER = ROOT / "docs/milestones/artifacts/Teignmouth-float32-topology/attempt-ledger.json"
LEDGER_SNAPSHOT = BUILD3 / "reserved-ledger-snapshot.json"
EXTERNAL_MANIFEST = BUILD3 / "external-runtime-manifest.json"
RUNTIME_IDENTITY = BUILD3 / "runtime-identity.json"
PREFLIGHT_SCRIPT = ROOT / "pipeline/scripts/teignmouth_build3_runtime_preflight.py"
BUILDER_SCRIPT = ROOT / "pipeline/scripts/build_teignmouth_float32_candidate.py"
SELFCHECK_HELPER = ROOT / "pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py"
PYTHON = ROOT / "pipeline/.venv/Scripts/python.exe"
EXPECTED_OUTPUT = ROOT / "data/generated/teignmouth-float32-topology"
RUN_LEAF = BUILD3 / "run-1"
INVOCATION = BUILD3 / "invocation.json"
PREFLIGHT_RESULT = BUILD3 / "runtime-preflight-result.json"
SELF_ROOT = ROOT / ".codex/build3-supervisor-selfcheck-retry-7"
SELF_RUN = SELF_ROOT / "run-1"
PREFLIGHT_SELF_ROOT = ROOT / ".codex/build3-runtime-preflight"
PREFLIGHT_SELF_RUN = PREFLIGHT_SELF_ROOT / "run-1"
TOTAL_SECONDS = 180.0
NUMERICAL_CUTOFF_SECONDS = 150.0
SELF_CHECK_SECONDS = 10.0
STANDALONE_PREFLIGHT_SECONDS = 30.0
PROFILE_ENVIRONMENT_KEYS = (
    "PATH",
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONNOUSERSITE",
    "PYTHONDONTWRITEBYTECODE",
    "PYTHONUSERBASE",
    "PYTHONPYCACHEPREFIX",
    "PYTHONSAFEPATH",
    "PYTHONPLATLIBDIR",
    "PYTHONCASEOK",
    "VIRTUAL_ENV",
    "PROJ_DATA",
    "PROJ_LIB",
    "GDAL_DATA",
    "GEOS_LIBRARY_PATH",
    "GEOS_LIBDIR",
    "SYSTEMROOT",
    "PROCESSOR_ARCHITECTURE",
)
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1
JOB_OBJECT_BASIC_PROCESS_ID_LIST = 3
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_QUERY_INFORMATION = 0x0400
SYNCHRONIZE = 0x00100000
CREATE_SUSPENDED = 0x00000004
CREATE_NO_WINDOW = 0x08000000
STARTF_USESTDHANDLES = 0x00000100
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
STILL_ACTIVE = 259
ERROR_MORE_DATA = 234
TH32CS_SNAPPROCESS = 0x00000002
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        (name, ctypes.c_ulonglong)
        for name in (
            "ReadOperationCount",
            "WriteOperationCount",
            "OtherOperationCount",
            "ReadTransferCount",
            "WriteTransferCount",
            "OtherTransferCount",
        )
    ]


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


class BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_longlong),
        ("TotalKernelTime", ctypes.c_longlong),
        ("ThisPeriodTotalUserTime", ctypes.c_longlong),
        ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
        ("TotalPageFaultCount", wintypes.DWORD),
        ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD),
        ("TotalTerminatedProcesses", wintypes.DWORD),
    ]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("nLength", wintypes.DWORD),
        ("lpSecurityDescriptor", wintypes.LPVOID),
        ("bInheritHandle", wintypes.BOOL),
    ]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


def _api() -> Any:
    if os.name != "nt":
        raise OSError("build-3 supervision requires Windows Job Objects")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.POINTER(STARTUPINFOW),
        ctypes.POINTER(PROCESS_INFORMATION),
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
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(SECURITY_ATTRIBUTES),
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.QueryInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel.QueryInformationJobObject.restype = wintypes.BOOL
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.IsProcessInJob.argtypes = [
        wintypes.HANDLE,
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.BOOL),
    ]
    kernel.IsProcessInJob.restype = wintypes.BOOL
    kernel.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.GetCurrentProcessId.argtypes = []
    kernel.GetCurrentProcessId.restype = wintypes.DWORD
    kernel.QueryPerformanceFrequency.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
    kernel.QueryPerformanceFrequency.restype = wintypes.BOOL
    kernel.QueryPerformanceCounter.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
    kernel.QueryPerformanceCounter.restype = wintypes.BOOL
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel.Process32FirstW.restype = wintypes.BOOL
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel.Process32NextW.restype = wintypes.BOOL
    kernel.GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
    kernel.GetFileAttributesW.restype = wintypes.DWORD
    kernel.CloseHandle.restype = wintypes.BOOL
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    return kernel, psapi


def _process_identity(kernel: Any, pid: int, deadline: float) -> dict[str, Any]:
    if time.monotonic() >= deadline:
        raise TimeoutError("deadline before native process identity query")
    handle = kernel.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_QUERY_INFORMATION, False, pid
    )
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        creation = wintypes.FILETIME()
        exit_time = wintypes.FILETIME()
        kernel_time = wintypes.FILETIME()
        user_time = wintypes.FILETIME()
        if not kernel.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel_time),
            ctypes.byref(user_time),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        image_buffer = ctypes.create_unicode_buffer(32768)
        image_size = wintypes.DWORD(len(image_buffer))
        if not kernel.QueryFullProcessImageNameW(handle, 0, image_buffer, ctypes.byref(image_size)):
            raise ctypes.WinError(ctypes.get_last_error())
        image_path = Path(image_buffer.value).resolve(strict=True)
        image_hash = _sha256(image_path, deadline)
        if time.monotonic() >= deadline:
            raise TimeoutError("deadline during native process identity verification")
        return {
            "pid": pid,
            "creationFileTime": (creation.dwHighDateTime << 32) | creation.dwLowDateTime,
            "imagePath": str(image_path),
            "imageSha256": image_hash,
        }
    finally:
        kernel.CloseHandle(handle)


def _process_identity_from_handle(
    kernel: Any, handle: int, pid: int, deadline: float
) -> dict[str, Any]:
    if time.monotonic() >= deadline:
        raise TimeoutError("deadline before retained native process identity query")
    creation = wintypes.FILETIME()
    exit_time = wintypes.FILETIME()
    kernel_time = wintypes.FILETIME()
    user_time = wintypes.FILETIME()
    if not kernel.GetProcessTimes(
        handle,
        ctypes.byref(creation),
        ctypes.byref(exit_time),
        ctypes.byref(kernel_time),
        ctypes.byref(user_time),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    image_buffer = ctypes.create_unicode_buffer(32768)
    image_size = wintypes.DWORD(len(image_buffer))
    if not kernel.QueryFullProcessImageNameW(handle, 0, image_buffer, ctypes.byref(image_size)):
        raise ctypes.WinError(ctypes.get_last_error())
    image_path = Path(image_buffer.value).resolve(strict=True)
    image_hash = _sha256(image_path, deadline)
    if time.monotonic() >= deadline:
        raise TimeoutError("deadline during retained native process identity verification")
    return {
        "pid": int(pid),
        "creationFileTime": (creation.dwHighDateTime << 32) | creation.dwLowDateTime,
        "imagePath": str(image_path),
        "imageSha256": image_hash,
    }


def _parent_pid(kernel: Any, pid: int, deadline: float) -> int:
    if time.monotonic() >= deadline:
        raise TimeoutError("deadline before parent identity census")
    snapshot = kernel.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot in (None, INVALID_HANDLE_VALUE):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        if not kernel.Process32FirstW(snapshot, ctypes.byref(entry)):
            raise ctypes.WinError(ctypes.get_last_error())
        attempts = 0
        while attempts < 65536:
            if time.monotonic() >= deadline:
                raise TimeoutError("deadline during bounded parent identity census")
            attempts += 1
            if entry.th32ProcessID == pid:
                return int(entry.th32ParentProcessID)
            if not kernel.Process32NextW(snapshot, ctypes.byref(entry)):
                break
        raise RuntimeError("current process parent identity was not found in bounded snapshot")
    finally:
        kernel.CloseHandle(snapshot)


def _assert_tree_contained(
    kernel: Any,
    job: int,
    roots: list[int],
    deadline: float,
    *,
    require_complete_snapshot: bool = False,
) -> dict[str, Any] | None:
    snapshot = kernel.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot in (None, INVALID_HANDLE_VALUE):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        if not kernel.Process32FirstW(snapshot, ctypes.byref(entry)):
            raise ctypes.WinError(ctypes.get_last_error())
        rows = []
        terminal_error: int | None = None
        for _ in range(65536):
            if time.monotonic() >= deadline:
                raise TimeoutError("deadline during bounded descendant containment census")
            rows.append((int(entry.th32ProcessID), int(entry.th32ParentProcessID)))
            if require_complete_snapshot:
                try:
                    ctypes.set_last_error(0)
                except Exception as exc:
                    raise RuntimeError(
                        "could not clear private last error before strict snapshot advance"
                    ) from exc
            if not kernel.Process32NextW(snapshot, ctypes.byref(entry)):
                if require_complete_snapshot:
                    terminal_error = ctypes.get_last_error()
                    if type(terminal_error) is not int or terminal_error != 18:
                        raise RuntimeError(
                            "strict process snapshot did not terminate with ERROR_NO_MORE_FILES "
                            f"(captured={terminal_error!r})"
                        )
                break
        else:
            raise RuntimeError("descendant containment census exceeded fixed process bound")
    finally:
        kernel.CloseHandle(snapshot)
    known = set(roots)
    descendants = set()
    for _ in range(64):
        if time.monotonic() >= deadline:
            raise TimeoutError("deadline during descendant ancestry expansion")
        changed = False
        for pid, parent in rows:
            if time.monotonic() >= deadline:
                raise TimeoutError("deadline during descendant process census")
            if parent in known and pid not in known:
                known.add(pid)
                descendants.add(pid)
                changed = True
        if not changed:
            break
    else:
        raise RuntimeError("descendant containment exceeded fixed ancestry depth")
    job_ids = set(_process_list(kernel, job, deadline))
    for pid, _parent in rows:
        if time.monotonic() >= deadline:
            raise TimeoutError("deadline during exact Job membership comparison")
        if pid in descendants and pid not in job_ids:
            handle = kernel.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                kernel.CloseHandle(handle)
                raise RuntimeError(f"live descendant PID {pid} escaped the exact inner Job")
    if require_complete_snapshot:
        return {
            "snapshotComplete": True,
            "terminalError": terminal_error,
            "rowCount": len(rows),
            "ancestryComplete": True,
            "comparisonComplete": True,
        }
    return None


def _contained_interpreter_child(
    kernel: Any,
    job: int,
    launcher_pid: int,
    base_path: str,
    base_sha256: str,
    deadline: float,
    *,
    retain_handle: bool = False,
    launcher_handle: int | None = None,
    launcher_creation_filetime: int | None = None,
) -> dict[str, Any]:
    if retain_handle and (launcher_handle is None or launcher_creation_filetime is None):
        raise ValueError("retained interpreter discovery requires the original launcher identity")
    if (
        retain_handle
        and _process_creation_filetime(kernel, launcher_handle) != launcher_creation_filetime
    ):
        raise RuntimeError("original launcher handle creation identity changed")
    attempts = 0
    while time.monotonic() < deadline and attempts < 120:
        attempts += 1
        for pid in _process_list(kernel, job, deadline):
            if pid == launcher_pid:
                continue
            try:
                if _parent_pid(kernel, pid, deadline) != launcher_pid:
                    continue
                identity = _process_identity(kernel, pid, deadline)
            except (OSError, RuntimeError):
                continue
            if identity["imagePath"] == base_path and identity["imageSha256"] == base_sha256:
                handle = kernel.OpenProcess(
                    PROCESS_QUERY_LIMITED_INFORMATION
                    | PROCESS_QUERY_INFORMATION
                    | (SYNCHRONIZE if retain_handle else 0),
                    False,
                    pid,
                )
                if not handle:
                    continue
                transferred = False
                try:
                    if retain_handle:
                        retained_identity = _process_identity_from_handle(
                            kernel, handle, pid, deadline
                        )
                        if retained_identity != identity:
                            raise RuntimeError(
                                "retained interpreter identity differs from discovery"
                            )
                        if _parent_pid(kernel, pid, deadline) != launcher_pid:
                            raise RuntimeError(
                                "retained interpreter is not a child of the exact launcher"
                            )
                    member = wintypes.BOOL()
                    if (
                        not kernel.IsProcessInJob(handle, job, ctypes.byref(member))
                        or not member.value
                    ):
                        raise RuntimeError("base interpreter child is outside the exact inner Job")
                    if retain_handle:
                        identity = dict(identity)
                        identity["retainedHandle"] = int(handle)
                        identity["handleOwnershipTransferred"] = True
                        transferred = True
                        return identity
                finally:
                    if not transferred and not kernel.CloseHandle(handle):
                        raise ctypes.WinError(ctypes.get_last_error())
                return identity
        time.sleep(min(0.025, max(0.0, deadline - time.monotonic())))
    raise TimeoutError("approved launcher did not produce its exact contained base interpreter")


def _verify_helper_start(
    kernel: Any,
    mode: str,
    launcher_identity: dict[str, Any],
    script_identity: dict[str, Any],
    nonce: str,
    job: int,
    deadline: float,
) -> dict[str, Any]:
    path = {
        "build-dispatch": BUILD3 / "runtime-preflight-script-start.json",
        "standalone": PREFLIGHT_SELF_RUN / "runtime-preflight-script-start.json",
        "nonzero": SELF_RUN / "nonzero-script-start.json",
        "tree-root": SELF_RUN / "tree-root-script-start.json",
    }.get(mode)
    if path is None:
        raise ValueError("unknown helper-start mode")
    attempts = 0
    while not path.is_file() and time.monotonic() < deadline and attempts < 120:
        attempts += 1
        time.sleep(min(0.025, max(0.0, deadline - time.monotonic())))
    if not path.is_file():
        raise TimeoutError("preflight did not publish its one-use interpreter identity")
    marker = json.loads(path.read_text(encoding="utf-8"))
    supervisor_identity = _process_identity(kernel, os.getpid(), deadline)
    if (
        marker.get("schema") != "teignmouth-build3-helper-script-start-v1"
        or marker.get("mode") != mode
        or marker.get("nonce") != nonce
        or marker.get("launcherPid") != launcher_identity["pid"]
        or marker.get("launcherCreationFileTime") != launcher_identity["creationFileTime"]
        or marker.get("supervisorPid") != supervisor_identity["pid"]
        or marker.get("supervisorCreationFileTime") != supervisor_identity["creationFileTime"]
        or marker.get("scriptPid") != script_identity["pid"]
        or marker.get("scriptCreationFileTime") != script_identity["creationFileTime"]
        or marker.get("scriptImagePath") != script_identity["imagePath"]
        or marker.get("scriptImageSha256") != script_identity["imageSha256"]
    ):
        raise ValueError("preflight script-start record differs from native process identities")
    handle = kernel.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_QUERY_INFORMATION,
        False,
        script_identity["pid"],
    )
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        member = wintypes.BOOL()
        if not kernel.IsProcessInJob(handle, job, ctypes.byref(member)) or not member.value:
            raise RuntimeError("preflight interpreter is not in the exact inner Job")
    finally:
        kernel.CloseHandle(handle)
    return marker


def _startup_record_path(mode: str) -> Path:
    return {
        "build-3": BUILD3 / "supervisor-script-start.json",
        "self-check": SELF_ROOT / "supervisor-script-start.json",
        "runtime-preflight-only": PREFLIGHT_SELF_ROOT / "supervisor-script-start.json",
    }[mode]


def _handoff(mode: str) -> tuple[float, float, dict[str, Any]]:
    paths = {
        "build-3": BUILD3 / "dispatch-handoff.json",
        "self-check": SELF_ROOT / "self-check-handoff.json",
        "runtime-preflight-only": PREFLIGHT_SELF_ROOT / "runtime-preflight-handoff.json",
    }
    source = paths[mode]
    consumed = {
        "build-3": BUILD3 / "dispatch-handoff.consumed.json",
        "self-check": SELF_ROOT / "self-check-handoff.consumed.json",
        "runtime-preflight-only": PREFLIGHT_SELF_ROOT / "runtime-preflight-handoff.consumed.json",
    }[mode]
    _assert_fixed_no_reparse(source)
    if consumed.exists():
        raise FileExistsError("fixed one-use handoff was already consumed")
    kernel, _psapi = _api()
    handoff = json.loads(source.read_text(encoding="utf-8"))
    current_pid = int(kernel.GetCurrentProcessId())
    expected_wrapper_mode = {
        "build-3": "build",
        "self-check": "self-check",
        "runtime-preflight-only": "runtime-preflight",
    }[mode]
    expected_budget = {
        "build-3": TOTAL_SECONDS,
        "self-check": SELF_CHECK_SECONDS,
        "runtime-preflight-only": STANDALONE_PREFLIGHT_SECONDS,
    }[mode]
    frequency = handoff.get("qpcFrequency")
    start_tick = handoff.get("startQpc")
    deadline_tick = handoff.get("deadlineQpc")
    if (
        handoff.get("schema") != "teignmouth-build3-parent-handoff-v2"
        or handoff.get("mode") != expected_wrapper_mode
        or handoff.get("oneUse") is not True
        or handoff.get("clockDomain") != "windows-qpc"
        or not re.fullmatch(r"[0-9a-f]{32}", str(handoff.get("nonce", "")))
        or handoff.get("expectedSupervisorScript") != str(Path(__file__).resolve())
        or handoff.get("launcherPath") != str(PYTHON.resolve())
        or not re.fullmatch(r"[0-9a-f]{64}", str(handoff.get("launcherSha256", "")))
        or not isinstance(handoff.get("launcherPid"), int)
        or not isinstance(handoff.get("launcherCreationFileTime"), int)
        or handoff.get("launcherImagePath") != str(PYTHON.resolve())
        or handoff.get("launcherImageSha256") != handoff.get("launcherSha256")
        or not isinstance(handoff.get("wrapperPid"), int)
        or not isinstance(handoff.get("wrapperCreationFileTime"), int)
        or not re.fullmatch(r"[0-9a-f]{64}", str(handoff.get("baseInterpreterSha256", "")))
        or not isinstance(frequency, int)
        or frequency <= 0
        or not isinstance(start_tick, int)
        or not isinstance(deadline_tick, int)
        or handoff.get("budgetSeconds") != expected_budget
        or abs((deadline_tick - start_tick) / frequency - expected_budget) > 1.0 / frequency
    ):
        raise ValueError("fixed parent handoff identity/schema/mode/deadline mismatch")
    start = start_tick / frequency
    deadline = deadline_tick / frequency
    native_frequency = ctypes.c_longlong()
    native_counter = ctypes.c_longlong()
    if (
        not kernel.QueryPerformanceFrequency(ctypes.byref(native_frequency))
        or not kernel.QueryPerformanceCounter(ctypes.byref(native_counter))
        or native_frequency.value != frequency
        or abs(native_counter.value / frequency - time.monotonic()) > 0.25
    ):
        raise ValueError("parent and supervisor do not share the verified Windows QPC clock domain")
    if time.monotonic() < start - 0.25 or time.monotonic() >= deadline:
        raise TimeoutError("parent-owned absolute deadline expired or uses another clock domain")
    if _sha256(PYTHON, deadline) != handoff["launcherSha256"]:
        raise ValueError("approved venv launcher hash differs from parent handoff")
    if mode in ("self-check", "runtime-preflight-only"):
        leaf = SELF_RUN if mode == "self-check" else PREFLIGHT_SELF_RUN
        _assert_fixed_no_reparse(leaf, allow_missing_leaf=True)
        if leaf.exists():
            raise FileExistsError("standalone run leaf exists before supervisor-owned creation")
    launcher_pid = int(handoff["launcherPid"])
    if current_pid == launcher_pid or _parent_pid(kernel, current_pid, deadline) != launcher_pid:
        raise ValueError("supervisor is not the exact base-interpreter child of its venv launcher")
    launcher_identity = _process_identity(kernel, launcher_pid, deadline)
    if (
        launcher_identity["creationFileTime"] != handoff["launcherCreationFileTime"]
        or launcher_identity["imagePath"] != str(PYTHON.resolve())
        or launcher_identity["imageSha256"] != handoff["launcherSha256"]
    ):
        raise ValueError("venv launcher native identity differs from the parent handoff")
    wrapper_pid = int(handoff["wrapperPid"])
    if _parent_pid(kernel, launcher_pid, deadline) != wrapper_pid:
        raise ValueError("venv launcher is not a direct child of the authenticated wrapper")
    wrapper_identity = _process_identity(kernel, wrapper_pid, deadline)
    if (
        wrapper_identity["creationFileTime"] != handoff.get("wrapperCreationFileTime")
        or wrapper_identity["imagePath"] != handoff.get("wrapperImagePath")
        or wrapper_identity["imageSha256"] != handoff.get("wrapperImageSha256")
    ):
        raise ValueError("wrapper PID/creation/native-image identity does not match handoff")
    current_identity = _process_identity(kernel, current_pid, deadline)
    if current_identity["imagePath"] != handoff.get("baseInterpreterPath") or current_identity[
        "imageSha256"
    ] != handoff.get("baseInterpreterSha256"):
        raise ValueError("supervisor native base-interpreter identity differs from handoff")
    current_handle = kernel.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_QUERY_INFORMATION, False, current_pid
    )
    if not current_handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        in_job = wintypes.BOOL()
        if (
            not kernel.IsProcessInJob(current_handle, None, ctypes.byref(in_job))
            or not in_job.value
        ):
            raise ValueError("supervisor interpreter is not contained in an outer Job Object")
    finally:
        kernel.CloseHandle(current_handle)
    if mode == "build-3":
        if handoff.get("phase") != "reserved-build-dispatch":
            raise ValueError("build handoff is not in reserved-dispatch phase")
        for field in (
            "inputManifestSha256",
            "externalRuntimeManifestSha256",
            "reservedLedgerSnapshotSha256",
            "runtimeIdentitySha256",
        ):
            if not re.fullmatch(r"[0-9a-f]{64}", str(handoff.get(field, ""))):
                raise ValueError(f"parent handoff lacks fixed protected binding: {field}")
    elif mode == "self-check":
        if handoff.get("phase") != "nonnumerical-self-check":
            raise ValueError("self-check handoff phase mismatch")
    else:
        if (
            handoff.get("phase") != "standalone-identity-preparation"
            or not re.fullmatch(
                r"[0-9a-f]{64}", str(handoff.get("standaloneAuthorizationSha256", ""))
            )
            or handoff.get("standalonePurpose")
            not in ("collect-unreserved-runtime-identity", "verify-unreserved-runtime-identity")
        ):
            raise ValueError("standalone preparation handoff lacks its separate authorization pin")
        if handoff.get("standalonePurpose") == "verify-unreserved-runtime-identity":
            for field in (
                "inputManifestSha256",
                "externalRuntimeManifestSha256",
                "runtimeIdentitySha256",
            ):
                if not re.fullmatch(r"[0-9a-f]{64}", str(handoff.get(field, ""))):
                    raise ValueError(f"standalone verification lacks frozen binding: {field}")
        elif any(
            handoff.get(field) is not None
            for field in (
                "inputManifestSha256",
                "externalRuntimeManifestSha256",
                "runtimeIdentitySha256",
                "reservedLedgerSnapshotSha256",
            )
        ):
            raise ValueError("identity collection must not use frozen or reserved manifest pins")
    script_start_path = _startup_record_path(mode)
    _assert_fixed_no_reparse(script_start_path, allow_missing_leaf=True)
    if script_start_path.exists():
        raise FileExistsError("fixed supervisor script-start evidence already exists")
    os.rename(source, consumed)
    identity_record = {
        "schema": "teignmouth-build3-script-start-v1",
        "mode": mode,
        "nonce": handoff["nonce"],
        "scriptPid": current_pid,
        "scriptCreationFileTime": current_identity["creationFileTime"],
        "scriptImagePath": current_identity["imagePath"],
        "scriptImageSha256": current_identity["imageSha256"],
        "launcherPid": launcher_pid,
        "launcherCreationFileTime": launcher_identity["creationFileTime"],
        "launcherImagePath": launcher_identity["imagePath"],
        "launcherImageSha256": launcher_identity["imageSha256"],
        "wrapperPid": wrapper_pid,
        "wrapperCreationFileTime": wrapper_identity["creationFileTime"],
        "wrapperImagePath": wrapper_identity["imagePath"],
        "wrapperImageSha256": wrapper_identity["imageSha256"],
        "scriptPath": str(Path(__file__).resolve()),
        "absoluteDeadlineMonotonicSeconds": deadline,
    }
    _write_exclusive(script_start_path, identity_record)
    return start, deadline, {**handoff, "scriptStartIdentity": identity_record}


def _assert_fixed_no_reparse(path: Path, *, allow_missing_leaf: bool = False) -> None:
    absolute = Path(os.path.abspath(path))
    try:
        absolute.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"fixed path escapes workspace: {path}") from exc
    current = Path(absolute.anchor)
    components = [current]
    for part in absolute.parts[1:]:
        current = current / part
        components.append(current)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_attributes = kernel32.GetFileAttributesW
    get_attributes.argtypes = [wintypes.LPCWSTR]
    get_attributes.restype = wintypes.DWORD
    for component in components:
        if allow_missing_leaf and not component.exists():
            break
        attributes = get_attributes(str(component))
        if attributes == 0xFFFFFFFF:
            raise FileNotFoundError(f"fixed path component missing: {component}")
        if attributes & 0x400:
            raise ValueError(f"fixed path component is a reparse point: {component}")
    if absolute.resolve(strict=absolute.exists()) != absolute:
        raise ValueError(f"fixed lexical path resolves through a redirected path: {absolute}")


def _write_exclusive(path: Path, record: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _update_owned(path: Path, record: dict[str, Any]) -> None:
    pending = path.with_name(path.name + ".pending")
    with pending.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(pending, path)


def _sha256(path: Path, deadline: float) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            if time.monotonic() >= deadline:
                raise TimeoutError("absolute deadline reached while hashing protected files")
            digest.update(block)
    return digest.hexdigest()


def _verify_repository(
    manifest_path: Path,
    expected_manifest_sha: str | None,
    deadline: float,
    *,
    standalone: bool = False,
) -> dict[str, Any]:
    _assert_fixed_no_reparse(manifest_path)
    initial_sha = _sha256(manifest_path, deadline)
    if expected_manifest_sha is not None and initial_sha != expected_manifest_sha:
        raise ValueError("build-3 input manifest differs from the original pinned SHA-256")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema") != "teignmouth-float32-build-input-v1"
        or manifest.get("issueId") != ISSUE
        or manifest.get("buildOrdinal") != 3
        or manifest.get("candidateEligibleForServing") is not False
    ):
        raise ValueError("input manifest is not fixed to this issue/build ordinal")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) < 291 or manifest.get("fileCount") != len(files):
        raise ValueError("repository manifest must contain a nonempty file binding list")
    required = {
        "pipeline/scripts/run_teignmouth_float32_build3.py",
        "pipeline/scripts/invoke_teignmouth_float32_build3.ps1",
        "pipeline/scripts/teignmouth_build3_runtime_preflight.py",
        "pipeline/scripts/teignmouth_build3_supervisor_selfcheck.py",
        "pipeline/scripts/build_teignmouth_float32_candidate.py",
        "pipeline/torquay_pipeline/road_surface.py",
        "pipeline/torquay_pipeline/road_surface_float32_frame.py",
        "pipeline/torquay_pipeline/road_surface_topology.py",
        "pipeline/torquay_pipeline/teignmouth_corridor_continuation.py",
        "pipeline/torquay_pipeline/teignmouth_corridor_prototype.py",
        "pipeline/torquay_pipeline/teignmouth_float32_candidate.py",
        "pipeline/.venv/Scripts/python.exe",
        "pipeline/.venv/pyvenv.cfg",
        "config/road-surface-teignmouth-float32.json",
        "docs/milestones/artifacts/Teignmouth-float32-topology/build-3/external-runtime-manifest.json",
        "docs/milestones/artifacts/Teignmouth-float32-topology/build-3/runtime-identity.json",
    }
    if not standalone:
        required.update(
            {
                "docs/milestones/artifacts/Teignmouth-float32-topology/build-3/reserved-ledger-snapshot.json",
                "docs/milestones/artifacts/Teignmouth-float32-topology/attempt-ledger.json",
            }
        )
    paths = [item.get("path") for item in files if isinstance(item, dict)]
    if len(paths) != len(files) or len(paths) != len(set(paths)):
        raise ValueError("repository manifest contains malformed or duplicate bindings")
    case_paths: dict[str, str] = {}
    for relative in paths:
        if not isinstance(relative, str):
            raise ValueError("repository manifest contains a non-string path")
        key = relative.casefold()
        prior = case_paths.get(key)
        if prior is not None and prior != relative:
            raise ValueError(
                f"repository manifest contains case-distinct paths: {prior} <> {relative}"
            )
        case_paths[key] = relative
    folded_paths: dict[str, str] = {}
    for relative in paths:
        if not isinstance(relative, str):
            raise ValueError("repository manifest contains a non-string path")
        prior = folded_paths.get(relative.casefold())
        if prior is not None and prior != relative:
            raise ValueError(f"repository manifest has case-distinct paths: {prior} <> {relative}")
        folded_paths[relative.casefold()] = relative
    missing = sorted(required - set(paths))
    if missing:
        raise ValueError(f"repository manifest omits mandatory control bindings: {missing}")
    changed = []
    checked = 0
    for item in files:
        if time.monotonic() >= deadline:
            changed.append({"reason": "deadline reached; verification stopped with partial counts"})
            break
        relative = item.get("path")
        if not isinstance(relative, str):
            changed.append({"path": relative, "reason": "invalid binding path"})
            continue
        path = ROOT / relative
        try:
            _assert_fixed_no_reparse(path)
            resolved = path.resolve(strict=False)
            canonical = resolved.relative_to(ROOT).as_posix()
        except ValueError:
            changed.append({"path": relative, "reason": "binding escapes repository"})
            continue
        except (OSError, FileNotFoundError) as exc:
            changed.append({"path": relative, "reason": f"fixed path check failed: {exc}"})
            continue
        path = resolved
        if canonical != relative or not path.is_file():
            changed.append({"path": relative, "reason": "noncanonical or missing input"})
            continue
        try:
            size = path.stat().st_size
            digest = _sha256(path, deadline)
        except TimeoutError as exc:
            changed.append({"path": relative, "reason": f"verification deadline: {exc}"})
            break
        except OSError as exc:
            changed.append(
                {"path": relative, "reason": f"hash failure: {type(exc).__name__}: {exc}"}
            )
            continue
        checked += 1
        if (size, digest) != (item.get("byteLength"), item.get("sha256")):
            changed.append({"path": relative, "reason": "size or SHA-256 mismatch"})
    try:
        final_sha = _sha256(manifest_path, deadline)
    except (OSError, TimeoutError) as exc:
        return {
            "passes": False,
            "checkedFileCount": checked,
            "declaredFileCount": len(files),
            "changed": [
                *changed,
                {
                    "path": str(manifest_path),
                    "reason": f"final manifest hash unavailable: {exc}",
                },
            ],
            "manifestSha256": None,
            "partial": True,
        }
    if final_sha != initial_sha:
        changed.append(
            {"path": str(manifest_path), "reason": "manifest changed during verification"}
        )
    if expected_manifest_sha is not None and final_sha != expected_manifest_sha:
        changed.append(
            {"path": str(manifest_path), "reason": "manifest SHA differs from invocation pin"}
        )
    return {
        "passes": not changed,
        "checkedFileCount": checked,
        "declaredFileCount": len(files),
        "changed": changed,
        "manifestSha256": final_sha,
    }


def _verify_runtime_identity_record(
    identity_path: Path,
    expected_identity_sha: str,
    expected_external_sha: str,
    deadline: float,
) -> dict[str, Any]:
    _assert_fixed_no_reparse(identity_path)
    digest = _sha256(identity_path, deadline)
    if digest != expected_identity_sha:
        raise ValueError("runtime identity differs from the parent handoff pin")
    record = json.loads(identity_path.read_text(encoding="utf-8"))
    if (
        not isinstance(record, dict)
        or record.get("schema") != "teignmouth-build3-runtime-identity-v1"
        or not isinstance(record.get("identity"), dict)
        or record.get("externalRuntimeManifestSha256") != expected_external_sha
    ):
        raise ValueError("runtime identity schema or external-manifest linkage is invalid")
    if _sha256(identity_path, deadline) != digest:
        raise ValueError("runtime identity changed during schema verification")
    return {"passes": True, "sha256": digest, "identity": record.get("identity")}


def _parse_pyvenv_cfg(path: Path, deadline: float) -> dict[str, str]:
    before = _sha256(path, deadline)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"pyvenv.cfg is unreadable: {path}") from exc
    values: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        if time.monotonic() >= deadline:
            raise TimeoutError("finite startup profile deadline while parsing pyvenv.cfg")
        if not line.strip() or line.startswith("#"):
            continue
        if line[0].isspace():
            raise ValueError(f"leading whitespace in pyvenv.cfg line {line_number}")
        if "=" not in line:
            raise ValueError(f"malformed pyvenv.cfg line {line_number}")
        key, value = line.split("=", 1)
        key = key.strip().casefold()
        if not key or key in values:
            raise ValueError(f"empty or duplicate pyvenv.cfg key at line {line_number}")
        if key not in {"home", "version", "include-system-site-packages", "executable", "command"}:
            raise ValueError(f"unsupported pyvenv.cfg key at line {line_number}: {key}")
        values[key] = value.strip()
    if _sha256(path, deadline) != before:
        raise ValueError("pyvenv.cfg changed while it was parsed")
    required = {"home", "version", "include-system-site-packages"}
    if not required.issubset(values):
        raise ValueError("pyvenv.cfg omits a required finite-profile key")
    if (
        values["version"] != "3.13.7"
        or values["include-system-site-packages"].casefold() != "false"
    ):
        raise ValueError("pyvenv.cfg differs from the finite CPython 3.13.7 profile")
    return values


def _verify_finite_startup_profile(
    deadline: float,
    *,
    stage: str,
    expected_environment: dict[str, Any],
    expected_manifest_sha: str,
    expected_external_sha: str,
    expected_identity_sha: str,
) -> dict[str, Any]:
    """Bind every disk-backed Python/native candidate in the fixed S/P profile."""
    if os.name != "nt":
        raise OSError("finite build-3 startup profile requires Windows path semantics")

    input_record = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    external_record = json.loads(EXTERNAL_MANIFEST.read_text(encoding="utf-8"))
    identity_record = json.loads(RUNTIME_IDENTITY.read_text(encoding="utf-8"))
    if time.monotonic() >= deadline:
        raise TimeoutError("finite startup profile deadline before binding maps")
    if (
        _sha256(INPUT_MANIFEST, deadline) != expected_manifest_sha
        or _sha256(EXTERNAL_MANIFEST, deadline) != expected_external_sha
        or _sha256(RUNTIME_IDENTITY, deadline) != expected_identity_sha
        or identity_record.get("schema") != "teignmouth-build3-runtime-identity-v1"
        or identity_record.get("externalRuntimeManifestSha256") != expected_external_sha
    ):
        raise ValueError("finite profile control files differ from authenticated pins")
    repo = {str(item["path"]): item for item in input_record.get("files", [])}
    external = {
        os.path.normcase(os.path.abspath(str(item["path"]))): item
        for item in external_record.get("entries", [])
    }
    if not repo or not external:
        raise ValueError("finite startup profile lacks frozen repository/external bindings")
    canonical_inputs: dict[str, str] = {}
    for relative in repo:
        absolute = str((ROOT / relative).resolve(strict=True))
        key = absolute.casefold()
        if key in canonical_inputs:
            raise ValueError(
                f"repository references collide canonically: {canonical_inputs[key]} <> {absolute}"
            )
        canonical_inputs[key] = absolute
    for absolute in external:
        key = absolute.casefold()
        if key in canonical_inputs:
            raise ValueError(
                "repository/external references collide canonically: "
                f"{canonical_inputs[key]} <> {absolute}"
            )
        canonical_inputs[key] = absolute
    if (
        os.environ.get("PROCESSOR_ARCHITECTURE") != "AMD64"
        or sys.maxsize != (1 << 63) - 1
        or not os.environ.get("SYSTEMROOT")
    ):
        raise ValueError("finite profile requires the pinned AMD64 Windows runtime and SystemRoot")
    observed_environment = {key: os.environ.get(key) for key in PROFILE_ENVIRONMENT_KEYS}
    if any(
        key not in expected_environment for key in PROFILE_ENVIRONMENT_KEYS
    ) or observed_environment != {
        key: expected_environment[key] for key in PROFILE_ENVIRONMENT_KEYS
    }:
        raise ValueError("inherited environment differs from frozen finite-profile identity")
    allowed_python_environment = {"PYTHONPATH", "PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE"}
    for key, value in os.environ.items():
        if time.monotonic() >= deadline:
            raise TimeoutError("finite startup profile deadline while checking Python overrides")
        if (
            key.upper().startswith("PYTHON")
            and value
            and key.upper() not in allowed_python_environment
        ):
            raise ValueError(f"unsupported Python startup override: {key}")
    approved_roots = _collection_roots_from_external(external_record)

    def require_approved(path: Path) -> Path:
        raw = str(path)
        if (
            not path.is_absolute()
            or raw.startswith(("\\\\", "//"))
            or raw.startswith(("\\\\?\\", "\\\\.\\"))
            or ":" in raw[2:]
        ):
            raise ValueError(
                f"finite-profile path is nonlocal, ADS-bearing, or noncanonical: {path}"
            )
        resolved = path.resolve(strict=True)
        if resolved != path:
            raise ValueError(f"finite-profile path is redirected or noncanonical: {path}")
        matches = [
            Path(item["path"]).resolve(strict=True)
            for item in approved_roots
            if resolved == Path(item["path"]).resolve(strict=True)
            or resolved.is_relative_to(Path(item["path"]).resolve(strict=True))
        ]
        if len(matches) != 1:
            raise ValueError(f"finite-profile path is outside exactly one approved root: {path}")
        return resolved

    for root_record in external_record.get("roots", []):
        require_approved(Path(root_record["path"]))

    roots: list[Path] = []
    base_home = Path(os.environ.get("VIRTUAL_ENV", str(ROOT / "pipeline/.venv")))
    pyvenv = base_home / "pyvenv.cfg"
    if not pyvenv.is_file():
        pyvenv = ROOT / "pipeline/.venv/pyvenv.cfg"
    values = _parse_pyvenv_cfg(pyvenv, deadline)
    if (
        values.get("version") != "3.13.7"
        or values.get("include-system-site-packages", "false").casefold() != "false"
    ):
        raise ValueError("venv pyvenv.cfg differs from the finite CPython 3.13.7 profile")
    base_executable = Path(getattr(sys, "_base_executable", sys.executable)).resolve(strict=True)
    if Path(values["home"]).resolve(strict=True) != base_executable.parent:
        raise ValueError("venv pyvenv.cfg home differs from the authenticated base interpreter")
    if base_home.resolve(strict=True) != (ROOT / "pipeline/.venv").resolve(strict=True):
        raise ValueError("VIRTUAL_ENV differs from the fixed project venv")
    for directory in (
        ROOT / "pipeline/.venv/Scripts",
        ROOT / "pipeline/.venv",
        base_executable.parent,
        base_executable.parent / "DLLs",
    ):
        for name in ("python._pth", "python313._pth"):
            if (directory / name).exists():
                raise ValueError(f"Python path override file is unsupported: {directory / name}")

    def add_root(raw: str | Path, *, required: bool = True) -> None:
        if time.monotonic() >= deadline:
            raise TimeoutError("finite startup profile deadline while deriving roots")
        path = Path(raw)
        if not path.is_absolute():
            raise ValueError(f"finite startup profile contains relative root: {raw}")
        if not path.exists():
            if required:
                raise FileNotFoundError(f"required finite-profile root is absent: {path}")
            return
        resolved = path.resolve(strict=True)
        if resolved != path or not resolved.is_dir():
            raise ValueError(f"finite-profile root is noncanonical or not a directory: {path}")
        if any(os.path.normcase(str(resolved)) == os.path.normcase(str(old)) for old in roots):
            return
        roots.append(resolved)

    script_root = Path(__file__).resolve(strict=True).parent
    add_root(script_root)
    add_root(ROOT / "pipeline")
    add_root(base_executable.parent / "Lib")
    add_root(base_executable.parent / "DLLs")
    add_root(Path(sys.prefix).resolve(strict=True) / "Lib" / "site-packages")
    raw_python_path = os.environ.get("PYTHONPATH", "")
    python_path_seen: set[str] = set()
    for raw in raw_python_path.split(os.pathsep):
        if not raw:
            if raw_python_path:
                raise ValueError("PYTHONPATH contains an empty search entry")
            continue
        path = Path(raw)
        if not path.is_absolute() or "!" in raw:
            raise ValueError("PYTHONPATH is outside the supported finite profile")
        if str(path).casefold() in python_path_seen:
            raise ValueError("PYTHONPATH contains a duplicate or case-ambiguous entry")
        python_path_seen.add(str(path).casefold())
        require_approved(path)
        if path.suffix.casefold() in {".zip", ".egg", ".whl"}:
            raise ValueError(f"active PYTHONPATH archive is unsupported: {path}")
        add_root(path)

    stdlib_zip = base_executable.parent / "python313.zip"
    absent_optional_sources: list[str] = []
    if stdlib_zip.exists():
        raise ValueError(
            f"optional standard-library archive is present and unsupported: {stdlib_zip}"
        )
    absent_optional_sources.append(str(stdlib_zip))

    site_packages = Path(sys.prefix).resolve(strict=True) / "Lib" / "site-packages"
    python_roots = list(roots)
    if os.environ.get("PYTHONPATH"):
        for raw in os.environ["PYTHONPATH"].split(os.pathsep):
            if raw:
                python_roots.append(Path(raw).resolve(strict=True))
    site_hook_count = 0
    pth_spellings: dict[str, str] = {}
    for site_directory in (site_packages, base_executable.parent / "Lib"):
        if not site_directory.is_dir():
            continue
        for hook in site_directory.glob("*.pth"):
            if time.monotonic() >= deadline:
                raise TimeoutError("finite startup profile deadline while reading .pth files")
            site_hook_count += 1
            raw_bytes = hook.read_bytes()
            try:
                lines = raw_bytes.decode("ascii").splitlines()
            except UnicodeDecodeError as exc:
                raise ValueError(f"non-ASCII .pth file is unsupported: {hook}") from exc
            _bind_profile_file(hook, repo, external, deadline)
            for line in lines:
                if time.monotonic() >= deadline:
                    raise TimeoutError("finite startup profile deadline while parsing .pth")
                if not line.strip() or line.startswith("#"):
                    continue
                if line[0].isspace():
                    raise ValueError(f"leading whitespace in .pth line is unsupported: {hook}")
                if line.startswith(("import ", "import\t")):
                    raise ValueError(f"executable .pth line is unsupported: {hook}")
                target = Path(line.rstrip())
                target = target if target.is_absolute() else site_directory / target
                if not target.is_dir() or str(target.resolve(strict=True)) != str(target):
                    raise ValueError(f".pth target is missing or noncanonical: {target}")
                approved_roots = _collection_roots_from_external(external_record)
                target_resolved = target.resolve(strict=True)
                if not any(
                    target_resolved == Path(item["path"]).resolve(strict=True)
                    or target_resolved.is_relative_to(Path(item["path"]).resolve(strict=True))
                    for item in approved_roots
                ):
                    raise ValueError(f".pth target escapes approved roots: {target}")
                folded_target = str(target_resolved).casefold()
                previous_target = pth_spellings.get(folded_target)
                if previous_target is not None and previous_target != str(target_resolved):
                    raise ValueError(
                        f".pth targets contain case-distinct identities: "
                        f"{previous_target} <> {target_resolved}"
                    )
                if previous_target is None:
                    pth_spellings[folded_target] = str(target_resolved)
                python_roots.append(target)
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    "finite startup profile deadline during PythonCore registry checks"
                )
            key_path = r"Software\Python\PythonCore\3.13\PythonPath"
            try:
                with winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ | view) as key:
                    values, subkeys, _modified = winreg.QueryInfoKey(key)
                    if values or subkeys:
                        raise ValueError(
                            f"PythonCore search-path registry override is unsupported: {key_path}"
                        )
            except FileNotFoundError:
                pass
            install_path = r"Software\Python\PythonCore\3.13\InstallPath"
            try:
                with winreg.OpenKey(hive, install_path, 0, winreg.KEY_READ | view) as key:
                    values, subkeys, _modified = winreg.QueryInfoKey(key)
                    if subkeys or values > 1:
                        raise ValueError(
                            f"PythonCore install registry configuration is ambiguous: "
                            f"{install_path}"
                        )
                    if values == 1:
                        registered = winreg.QueryValueEx(key, None)[0]
                        if (
                            not registered
                            or Path(registered).resolve(strict=True) != base_executable.parent
                        ):
                            raise ValueError(
                                "PythonCore registry home differs from authenticated base: "
                                f"{install_path}"
                            )
            except FileNotFoundError:
                pass

    native_roots = [
        PYTHON.parent,
        base_executable.parent,
        base_executable.parent / "DLLs",
        ROOT,
        Path(os.environ.get("SystemRoot", "")),
        Path(os.environ.get("SystemRoot", "")) / "System32",
    ]
    native_path_seen: set[str] = set()
    for raw in os.environ.get("PATH", "").split(os.pathsep):
        if not raw:
            raise ValueError("PATH contains an empty native search entry")
        native_path = require_approved(Path(raw))
        native_key = os.path.normcase(str(native_path))
        if native_key in native_path_seen:
            raise ValueError("PATH contains a duplicate or case-ambiguous entry")
        native_path_seen.add(native_key)
        native_roots.append(native_path)
    package_native_roots = [
        site_packages / name for name in ("numpy.libs", "shapely.libs", "pyproj.libs")
    ]
    for path in package_native_roots:
        if not path.is_dir():
            raise FileNotFoundError(f"required package native tree is absent: {path}")

    data_roots = [site_packages]
    for key in ("PROJ_DATA", "PROJ_LIB", "GDAL_DATA"):
        raw = os.environ.get(key)
        if raw:
            path = Path(raw)
            require_approved(path)
            if not path.is_dir() or str(path.resolve(strict=True)) != raw:
                raise ValueError(f"{key} is missing or noncanonical: {raw}")
            data_roots.append(path)

    visited: set[str] = set()
    directory_spellings: dict[str, str] = {}
    candidate_count = 0
    candidate_bytes = 0
    python_suffixes = {".py", ".pyw", ".pyc", ".pyo", ".pyd"}
    native_suffixes = {".pyd", ".dll", ".exe", ".ocx", ".cpl"}

    def assert_no_reparse(path: Path) -> Path:
        absolute = Path(os.path.abspath(path))
        if not absolute.is_absolute():
            raise ValueError(f"finite-profile path is not absolute: {path}")
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        get_attributes = kernel.GetFileAttributesW
        get_attributes.argtypes = [ctypes.c_wchar_p]
        get_attributes.restype = wintypes.DWORD
        current = Path(absolute.anchor)
        for component in absolute.parts[1:]:
            if time.monotonic() >= deadline:
                raise TimeoutError("finite startup profile deadline during ancestor validation")
            current = current / component
            attributes = get_attributes(str(current))
            if attributes == 0xFFFFFFFF:
                raise FileNotFoundError(f"finite-profile path component is unavailable: {current}")
            if attributes & 0x400:
                raise ValueError(f"finite-profile path traverses a reparse point: {current}")
        resolved = absolute.resolve(strict=True)
        if resolved != absolute:
            raise ValueError(f"finite-profile path is redirected: {absolute}")
        return absolute

    def inspect(path: Path) -> None:
        nonlocal candidate_count, candidate_bytes
        if time.monotonic() >= deadline:
            raise TimeoutError("finite startup profile deadline during candidate census")
        resolved = assert_no_reparse(path)
        key = os.path.normcase(str(resolved))
        if key in visited:
            if visited_paths[key] != str(resolved):
                raise ValueError(f"finite-profile case alias is ambiguous: {resolved}")
            return
        visited.add(key)
        visited_paths[key] = str(resolved)
        try:
            path.relative_to(ROOT)
            binding = repo.get(path.resolve(strict=True).relative_to(ROOT).as_posix())
        except ValueError:
            binding = external.get(key)
        if binding is None:
            raise ValueError(f"unbound finite-profile executable candidate: {resolved}")
        before = resolved.stat()
        digest = _sha256(resolved, deadline)
        after = resolved.stat()
        if time.monotonic() >= deadline:
            raise TimeoutError("finite startup profile deadline after header metadata check")
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError(f"finite-profile candidate changed while observed: {resolved}")
        if (after.st_size, digest) != (binding.get("byteLength"), binding.get("sha256")):
            raise ValueError(f"finite-profile candidate differs from frozen binding: {resolved}")
        candidate_count += 1
        candidate_bytes += after.st_size

    def is_customization_name(name: str) -> bool:
        folded = name.casefold()
        return folded in {"sitecustomize", "usercustomize"} or folded.startswith(
            ("sitecustomize.", "usercustomize.")
        )

    def register_directory(path: Path) -> Path:
        resolved = assert_no_reparse(path)
        exact = str(resolved)
        key = exact.casefold()
        previous = directory_spellings.get(key)
        if previous is not None and previous != exact:
            raise ValueError(f"finite-profile directory case collision: {previous} <> {exact}")
        directory_spellings[key] = exact
        return resolved

    def reject_loader_sidecars(path: Path) -> None:
        for suffix in (".local", ".manifest", ".config"):
            if time.monotonic() >= deadline:
                raise TimeoutError("finite startup profile deadline during sidecar check")
            for sidecar in (Path(str(path) + suffix), path.with_suffix(suffix)):
                try:
                    os.lstat(sidecar)
                except (FileNotFoundError, NotADirectoryError):
                    exists = False
                else:
                    exists = True
                if time.monotonic() >= deadline:
                    raise TimeoutError("finite startup profile deadline after sidecar check")
                if exists:
                    raise ValueError(f"loader redirection sidecar is unsupported: {sidecar}")

    def classify_profile_file(
        path: Path,
        *,
        python_role: bool,
        all_files_role: bool,
        deadline: float,
    ) -> dict[str, bool]:
        if time.monotonic() >= deadline:
            raise TimeoutError("finite startup profile deadline before file classification")
        resolved = assert_no_reparse(path)
        before = resolved.stat()
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f"finite-profile inspected path is not a regular file: {resolved}")
        try:
            with resolved.open("rb") as stream:
                if time.monotonic() >= deadline:
                    raise TimeoutError("finite startup profile deadline before header read")
                header = stream.read(2)
                if time.monotonic() >= deadline:
                    raise TimeoutError("finite startup profile deadline after header read")
        except TimeoutError:
            raise
        except OSError as exc:
            raise ValueError(f"finite-profile header read failed: {resolved}") from exc
        if time.monotonic() >= deadline:
            raise TimeoutError("finite startup profile deadline after header metadata check")
        after = resolved.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError(f"finite-profile file changed during header observation: {resolved}")
        suffix = resolved.suffix.casefold()
        is_native = suffix in native_suffixes or header == b"MZ"
        is_passive_archive = suffix in {".zip", ".egg", ".whl"} and not is_native
        is_candidate = all_files_role or is_native or (python_role and suffix in python_suffixes)
        return {
            "isNative": is_native,
            "isPassiveArchive": is_passive_archive,
            "isCandidate": is_candidate,
        }

    def walk(
        root: Path,
        *,
        recursive: bool,
        python_candidates: bool,
        role: str,
        all_files: bool = False,
        loader_relevant: bool = False,
    ) -> None:
        if time.monotonic() >= deadline:
            raise TimeoutError(f"finite startup profile deadline before walking {root}")
        if not root.exists():
            if role in ("python-root", "native-root"):
                raise FileNotFoundError(f"required finite-profile root is absent: {root}")
            return
        root = require_approved(register_directory(root))
        if not root.is_dir():
            raise ValueError(f"finite-profile search root is not a directory: {root}")

        def on_error(error: OSError) -> None:
            raise error

        for current, dirs, files in os.walk(
            root, topdown=True, onerror=on_error, followlinks=False
        ):
            if time.monotonic() >= deadline:
                raise TimeoutError(f"finite startup profile deadline while walking {root}")
            current_path = register_directory(Path(current))
            if is_customization_name(current_path.name):
                raise ValueError(
                    f"customization package is outside the finite profile: {current_path}"
                )
            kept = []
            for name in dirs:
                child = current_path / name
                register_directory(child)
                if is_customization_name(name):
                    raise ValueError(
                        f"customization package is outside the finite profile: {child}"
                    )
                if loader_relevant and name.casefold().endswith((".local", ".manifest", ".config")):
                    raise ValueError(f"unresolved loader redirection directory: {child}")
                kept.append(name)
            dirs[:] = kept if recursive else []
            for name in files:
                if time.monotonic() >= deadline:
                    raise TimeoutError("finite startup profile deadline during directory entries")
                path = current_path / name
                assert_no_reparse(path)
                classification = classify_profile_file(
                    path,
                    python_role=python_candidates,
                    all_files_role=all_files,
                    deadline=deadline,
                )
                if is_customization_name(path.name) or is_customization_name(path.stem):
                    raise ValueError(f"customization module is outside the finite profile: {path}")
                if loader_relevant and path.name.casefold().endswith(
                    (".local", ".manifest", ".config")
                ):
                    raise ValueError(f"unresolved loader redirection sidecar: {path}")
                if classification["isNative"]:
                    reject_loader_sidecars(path)
                if not classification["isCandidate"]:
                    continue
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        "finite startup profile deadline after header/sidecar checks"
                    )
                if classification["isCandidate"]:
                    inspect(path)

    visited_paths: dict[str, str] = {}
    for root in python_roots:
        walk(root, recursive=True, python_candidates=True, role="python-root")
    for root in native_roots:
        if not root.is_absolute():
            raise ValueError(f"native search root is relative: {root}")
        if not root.exists():
            raise FileNotFoundError(f"required native search root is absent: {root}")
        walk(
            root,
            recursive=False,
            python_candidates=False,
            role="native-root",
            loader_relevant=True,
        )
    for root in package_native_roots:
        walk(
            root,
            recursive=True,
            python_candidates=False,
            role="package-native-root",
            loader_relevant=True,
        )
    for root in data_roots:
        walk(
            root, recursive=True, python_candidates=False, role="runtime-data-root", all_files=True
        )

    def beneath(path: Path, root: Path) -> bool:
        candidate = os.path.normcase(str(path))
        base_path = os.path.normcase(str(root)).rstrip("\\/")
        return candidate == base_path or candidate.startswith(base_path + os.sep)

    expected_candidates: set[str] = set()
    binding_rows = [(ROOT / relative, binding) for relative, binding in repo.items()] + [
        (Path(item["path"]), item) for item in external_record.get("entries", [])
    ]
    for raw_path, _binding in binding_rows:
        if time.monotonic() >= deadline:
            raise TimeoutError(
                "finite startup profile deadline while reconciling manifest candidates"
            )
        path = assert_no_reparse(raw_path)
        in_python = any(beneath(path, root) for root in python_roots)
        in_native = any(
            os.path.normcase(str(path.parent)) == os.path.normcase(str(root))
            for root in native_roots
        ) or any(beneath(path, root) for root in package_native_roots)
        in_data = any(beneath(path, root) for root in data_roots)
        if not (in_python or in_native or in_data):
            continue
        classification = classify_profile_file(
            path,
            python_role=in_python,
            all_files_role=in_data,
            deadline=deadline,
        )
        loader_sidecar = path.name.casefold().endswith((".local", ".manifest", ".config"))
        if in_native and loader_sidecar:
            raise ValueError(f"unresolved loader redirection sidecar: {path}")
        if classification["isNative"]:
            reject_loader_sidecars(path)
        if classification["isCandidate"]:
            key = os.path.normcase(str(path))
            expected_candidates.add(key)
            if key not in visited_paths:
                raise ValueError(f"frozen candidate binding was not observed: {path}")
    if expected_candidates != set(visited_paths):
        raise ValueError("discovered and frozen finite-profile candidate sets do not reconcile")

    if time.monotonic() >= deadline:
        raise TimeoutError("finite startup profile expired before completion")
    if (
        _sha256(INPUT_MANIFEST, deadline) != expected_manifest_sha
        or _sha256(EXTERNAL_MANIFEST, deadline) != expected_external_sha
        or _sha256(RUNTIME_IDENTITY, deadline) != expected_identity_sha
    ):
        raise ValueError("finite profile controls changed during candidate enumeration")
    return {
        "stage": stage,
        "passes": True,
        "pythonRootCount": len(roots),
        "nativeRootCount": len(native_roots),
        "candidateFileCount": candidate_count,
        "candidateByteCount": candidate_bytes,
        "absentOptionalSources": absent_optional_sources,
        "siteHookFileCount": site_hook_count,
        "customizationModulesAbsent": True,
        "claim": "finite-profile observation only; no atomic load confinement",
    }


def _bind_profile_file(
    path: Path,
    repository: dict[str, dict[str, Any]],
    external: dict[str, dict[str, Any]],
    deadline: float,
) -> None:
    absolute = Path(os.path.abspath(path))
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    get_attributes = kernel.GetFileAttributesW
    get_attributes.argtypes = [ctypes.c_wchar_p]
    get_attributes.restype = wintypes.DWORD
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        if time.monotonic() >= deadline:
            raise TimeoutError(
                "finite startup profile deadline during archive/control ancestry check"
            )
        current = current / component
        attributes = get_attributes(str(current))
        if attributes == 0xFFFFFFFF:
            raise FileNotFoundError(f"profile archive/control path is unavailable: {current}")
        if attributes & 0x400:
            raise ValueError(f"profile archive/control traverses a reparse point: {current}")
    resolved = absolute.resolve(strict=True)
    if resolved != absolute:
        raise ValueError(f"profile archive/control is redirected: {absolute}")
    key = os.path.normcase(str(resolved))
    binding = external.get(key)
    if binding is None:
        try:
            binding = repository.get(resolved.relative_to(ROOT).as_posix())
        except ValueError:
            binding = None
    if binding is None or (
        resolved.stat().st_size,
        _sha256(resolved, deadline),
    ) != (binding.get("byteLength"), binding.get("sha256")):
        raise ValueError(f"unbound or mismatched finite-profile archive: {resolved}")


def _collection_roots_from_external(contract: dict[str, Any]) -> list[dict[str, str]]:
    roots = [{"path": str(ROOT.resolve(strict=True)), "category": "repository"}]
    for item in contract.get("roots", []):
        roots.append({"path": str(item["path"]), "category": str(item["category"])})
    return roots


def _verify_external(
    external_path: Path, expected_sha: str | None, deadline: float
) -> dict[str, Any]:
    _assert_fixed_no_reparse(external_path)
    initial_sha = _sha256(external_path, deadline)
    if expected_sha is not None and initial_sha != expected_sha:
        raise ValueError("external runtime manifest differs from original pinned SHA-256")
    contract = json.loads(external_path.read_text(encoding="utf-8"))
    if contract.get("schema") != "teignmouth-build3-external-runtime-v1":
        raise ValueError("external runtime manifest schema mismatch")
    roots = []
    entries = contract.get("entries")
    root_records = contract.get("roots")
    if (
        not isinstance(root_records, list)
        or not root_records
        or not isinstance(entries, list)
        or not entries
        or contract.get("rootCount") != len(root_records)
        or contract.get("entryCount") != len(entries)
    ):
        raise ValueError("external runtime manifest roots and entries must be nonempty lists")
    root_paths = [item.get("path") for item in root_records if isinstance(item, dict)]
    external_paths = [item.get("path") for item in entries if isinstance(item, dict)]
    if len(root_paths) != len(root_records) or len(root_paths) != len(set(root_paths)):
        raise ValueError("external runtime manifest has malformed or duplicate roots")
    if len(external_paths) != len(entries) or len(external_paths) != len(set(external_paths)):
        raise ValueError("external runtime manifest has malformed or duplicate entries")
    for label, values in (("root", root_paths), ("external", external_paths)):
        seen: dict[str, str] = {}
        for value in values:
            if not isinstance(value, str):
                raise ValueError(f"external runtime manifest has a non-string {label} path")
            folded = value.casefold()
            previous = seen.get(folded)
            if previous is not None and previous != value:
                raise ValueError(
                    f"external runtime manifest has case-distinct {label} paths: "
                    f"{previous} <> {value}"
                )
            seen[folded] = value
    folded_paths: dict[str, str] = {}
    for raw_path in external_paths:
        if not isinstance(raw_path, str):
            raise ValueError("external runtime manifest contains a non-string path")
        prior = folded_paths.get(raw_path.casefold())
        if prior is not None and prior != raw_path:
            raise ValueError(
                f"external runtime manifest has case-distinct paths: {prior} <> {raw_path}"
            )
        folded_paths[raw_path.casefold()] = raw_path
    allowed_categories = {"venv-runtime", "base-python-runtime", "windows-system-runtime"}
    allowed_categories = {"venv-runtime", "base-python-runtime", "windows-system-runtime"}
    for entry in root_records:
        if not isinstance(entry, dict) or entry.get("category") not in allowed_categories:
            raise ValueError("external runtime root has an invalid category")
        raw_root = entry.get("path")
        if not isinstance(raw_root, str):
            raise ValueError("external runtime root path is malformed")
        path = Path(raw_root).resolve(strict=True)
        if str(path) != raw_root or not path.is_dir():
            raise ValueError("external runtime root is unavailable or noncanonical")
        roots.append((path, entry.get("category")))
    changed = []
    checked = 0
    for entry in entries:
        if time.monotonic() >= deadline:
            changed.append(
                {"reason": "deadline reached; external verification stopped with partial counts"}
            )
            break
        if not isinstance(entry, dict):
            changed.append({"reason": "external entry is malformed"})
            continue
        raw = entry.get("path")
        pin = entry.get("sha256")
        if (
            not isinstance(raw, str)
            or not Path(raw).is_absolute()
            or not isinstance(entry.get("byteLength"), int)
            or entry["byteLength"] < 0
            or not isinstance(pin, str)
            or len(pin) != 64
            or any(character not in "0123456789abcdef" for character in pin)
            or entry.get("category") not in allowed_categories
        ):
            changed.append({"path": raw, "reason": "external binding is not absolute"})
            continue
        path = Path(raw).resolve(strict=False)
        try:
            canonical = str(path)
        except OSError as exc:
            changed.append({"path": raw, "reason": str(exc)})
            continue
        if canonical != raw or not path.is_file():
            changed.append({"path": raw, "reason": "external file is missing or noncanonical"})
            continue
        root_matches = [(base, category) for base, category in roots if path.is_relative_to(base)]
        if len(root_matches) != 1 or root_matches[0][1] != entry.get("category"):
            changed.append({"path": raw, "reason": "external root/category mismatch"})
            continue
        try:
            size = path.stat().st_size
            digest = _sha256(path, deadline)
        except TimeoutError as exc:
            changed.append({"path": raw, "reason": f"verification deadline: {exc}"})
            break
        except OSError as exc:
            changed.append({"path": raw, "reason": f"hash failure: {type(exc).__name__}: {exc}"})
            continue
        checked += 1
        if (size, digest) != (entry.get("byteLength"), entry.get("sha256")):
            changed.append({"path": raw, "reason": "external size or SHA-256 mismatch"})
    try:
        final_sha = _sha256(external_path, deadline)
    except (OSError, TimeoutError) as exc:
        return {
            "passes": False,
            "checkedFileCount": checked,
            "declaredFileCount": len(entries),
            "changed": [
                *changed,
                {
                    "path": str(external_path),
                    "reason": f"final manifest hash unavailable: {exc}",
                },
            ],
            "manifestSha256": None,
            "partial": True,
        }
    if final_sha != initial_sha:
        changed.append(
            {"path": str(external_path), "reason": "external manifest changed during verification"}
        )
    if expected_sha is not None and final_sha != expected_sha:
        changed.append(
            {
                "path": str(external_path),
                "reason": "external manifest SHA differs from invocation pin",
            }
        )
    return {
        "passes": not changed,
        "checkedFileCount": checked,
        "declaredFileCount": len(entries),
        "changed": changed,
        "manifestSha256": final_sha,
    }


def _fixed_ledger_preflight(
    expected_snapshot_sha: str | None = None, deadline: float | None = None
) -> dict[str, Any]:
    snapshot_sha = _sha256(LEDGER_SNAPSHOT, deadline if deadline is not None else time.monotonic())
    if expected_snapshot_sha is not None and snapshot_sha != expected_snapshot_sha:
        raise ValueError("reserved ledger snapshot differs from parent handoff binding")
    snapshot = json.loads(LEDGER_SNAPSHOT.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    budget = ledger.get("budget", {})
    builds = budget.get("implementationBuilds", {})
    diagnostics = budget.get("diagnostics", {})
    luna = budget.get("lunaCorrectionCycles", {})
    sol = budget.get("solCorrections", {})
    if snapshot != ledger:
        raise ValueError("live ledger differs from frozen post-reservation snapshot")
    if (
        ledger.get("issueId") != ISSUE
        or builds.get("used") != 2
        or builds.get("reserved") != 1
        or builds.get("maximum") != 6
        or builds.get("maximumSecondsEach") != TOTAL_SECONDS
        or diagnostics.get("used") != 2
        or diagnostics.get("reserved") != 0
        or luna.get("used") != 4
        or luna.get("reserved") != 0
        or sol.get("used") != 1
        or sol.get("reserved") != 0
        or ledger.get("candidateEligibleForServing") is True
    ):
        raise ValueError("live ledger does not show the exact one-time ordinal-3 reservation")
    return {
        "passes": True,
        "buildOrdinal": 3,
        "used": 2,
        "reserved": 1,
        "maximumSeconds": TOTAL_SECONDS,
        "reservedLedgerSnapshotSha256": snapshot_sha,
    }


def _create_job(kernel: Any) -> int:
    job = kernel.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    info = EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(
        job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(info), ctypes.sizeof(info)
    ):
        error = ctypes.get_last_error()
        kernel.CloseHandle(job)
        raise ctypes.WinError(error)
    return int(job)


def _create_log_handle(kernel: Any, path: Path) -> int:
    security = SECURITY_ATTRIBUTES(ctypes.sizeof(SECURITY_ATTRIBUTES), None, True)
    handle = kernel.CreateFileW(
        str(path), 0x40000000, 0x00000001, ctypes.byref(security), 1, 0x00000080, None
    )
    if handle in (None, wintypes.HANDLE(-1).value):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(handle)


def _require_current_console(kernel: Any, deadline: float) -> None:
    if time.monotonic() >= deadline:
        raise TimeoutError("deadline before current-console API binding")
    get_console_process_list = kernel.GetConsoleProcessList
    if time.monotonic() >= deadline:
        raise TimeoutError("deadline while resolving current-console API")
    get_console_process_list.argtypes = [ctypes.POINTER(wintypes.DWORD), wintypes.DWORD]
    get_console_process_list.restype = wintypes.DWORD
    if time.monotonic() >= deadline:
        raise TimeoutError("deadline after current-console API binding")

    current_pid = int(kernel.GetCurrentProcessId())
    if time.monotonic() >= deadline:
        raise TimeoutError("deadline after current process ID query")
    python_pid = os.getpid()
    if current_pid <= 0 or current_pid != python_pid:
        raise RuntimeError("current process ID does not match the authenticated Python process")
    if time.monotonic() >= deadline:
        raise TimeoutError("deadline after validating the authenticated supervisor PID")

    capacity = 32
    for attempt in range(4):
        if time.monotonic() >= deadline:
            raise TimeoutError("deadline before current-console PID allocation")
        if capacity <= 0 or capacity > 4096:
            raise RuntimeError("current-console PID buffer bound exceeded")
        pids = (wintypes.DWORD * capacity)()
        if time.monotonic() >= deadline:
            raise TimeoutError("deadline after current-console PID allocation")
        returned = get_console_process_list(pids, capacity)
        if not returned:
            native_error = ctypes.get_last_error()
        else:
            native_error = None
        if time.monotonic() >= deadline:
            raise TimeoutError("current-console PID query completed after the inherited deadline")
        if native_error is not None:
            raise ctypes.WinError(native_error)
        try:
            returned_count = int(returned)
        except (TypeError, ValueError, OverflowError) as exc:
            raise RuntimeError("current-console PID query returned a malformed count") from exc
        if returned_count <= 0 or returned_count > 0xFFFFFFFF:
            raise RuntimeError("current-console PID query returned an invalid count")
        if returned_count > capacity:
            if attempt == 3:
                raise RuntimeError("current-console PID query remained incomplete after four calls")
            next_capacity = max(capacity * 2, returned_count)
            if next_capacity > 4096:
                raise RuntimeError("current-console PID query exceeded the 4096-entry bound")
            capacity = next_capacity
            continue

        observed: set[int] = set()
        for index in range(returned_count):
            if time.monotonic() >= deadline:
                raise TimeoutError("deadline while reading current-console PIDs")
            pid = int(pids[index])
            if pid <= 0 or pid in observed:
                raise RuntimeError("current-console PID list contained zero or duplicate IDs")
            observed.add(pid)
        if time.monotonic() >= deadline:
            raise TimeoutError("deadline after reading current-console PIDs")
        if current_pid not in observed:
            raise RuntimeError("current console does not contain the authenticated supervisor PID")
        if time.monotonic() >= deadline:
            raise TimeoutError("deadline before accepting current-console attachment")
        return
    raise RuntimeError("current-console PID query did not produce a complete list")


def _launch_suspended(
    kernel: Any,
    job: int,
    argv: list[str],
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    deadline: float,
    before_resume: Any | None = None,
    *,
    inherit_current_console: bool = False,
) -> dict[str, Any]:
    if not isinstance(inherit_current_console, bool):
        raise TypeError("inherit_current_console must be a bool")
    stdout_handle = _create_log_handle(kernel, stdout_path)
    try:
        stderr_handle = _create_log_handle(kernel, stderr_path)
    except Exception:
        kernel.CloseHandle(stdout_handle)
        raise
    security = SECURITY_ATTRIBUTES(ctypes.sizeof(SECURITY_ATTRIBUTES), None, True)
    stdin = kernel.CreateFileW(
        "NUL", 0x80000000, 0x00000003, ctypes.byref(security), 3, 0x00000080, None
    )
    if stdin in (None, wintypes.HANDLE(-1).value):
        error = ctypes.get_last_error()
        kernel.CloseHandle(stdout_handle)
        kernel.CloseHandle(stderr_handle)
        raise ctypes.WinError(error)
    startup = STARTUPINFOW()
    startup.cb = ctypes.sizeof(startup)
    startup.dwFlags = STARTF_USESTDHANDLES
    startup.hStdInput = stdin
    startup.hStdOutput = stdout_handle
    startup.hStdError = stderr_handle
    process_info = PROCESS_INFORMATION()
    command = subprocess.list2cmdline(argv)
    command_buffer = ctypes.create_unicode_buffer(command)
    created = False
    stdio_release_confirmed: list[bool | None] = [None, None, None]
    stdio_release_errors: list[Any | None] = [None, None, None]
    stdio_release_failed = False
    try:
        if inherit_current_console:
            _require_current_console(kernel, deadline)
        if time.monotonic() >= deadline:
            raise TimeoutError("deadline before suspended process creation")
        creation_flags = CREATE_SUSPENDED
        if not inherit_current_console:
            creation_flags |= CREATE_NO_WINDOW
        created = kernel.CreateProcessW(
            argv[0],
            command_buffer,
            None,
            None,
            True,
            creation_flags,
            None,
            str(cwd),
            ctypes.byref(startup),
            ctypes.byref(process_info),
        )
        if not created:
            create_error = ctypes.get_last_error()
            raise ctypes.WinError(create_error)
    finally:
        primary_error = sys.exception()
        for index, stdio_handle in enumerate((stdout_handle, stderr_handle, stdin)):
            try:
                close_result = kernel.CloseHandle(stdio_handle)
            except BaseException as close_exception:
                stdio_release_confirmed[index] = False
                stdio_release_errors[index] = close_exception
                stdio_release_failed = True
                continue
            if close_result:
                stdio_release_confirmed[index] = True
                continue
            try:
                close_error = ctypes.get_last_error()
            except BaseException as close_exception:
                stdio_release_errors[index] = close_exception
            else:
                stdio_release_errors[index] = close_error
            stdio_release_confirmed[index] = False
            stdio_release_failed = True
        if stdio_release_failed and primary_error is not None:
            try:
                roles = ("stdout", "stderr", "stdin")
                release_details = []
                for index, confirmed in enumerate(stdio_release_confirmed):
                    if not confirmed:
                        error = stdio_release_errors[index]
                        detail = error if isinstance(error, int) else type(error).__name__
                        release_details.append(f"{roles[index]}={detail}")
                primary_error.add_note("stdio release unconfirmed: " + "; ".join(release_details))
            except BaseException:
                pass
    assigned = False
    try:
        if stdio_release_failed:
            raise RuntimeError("stdio handle release was not confirmed before child resume")
        if not kernel.AssignProcessToJobObject(job, process_info.hProcess):
            raise ctypes.WinError(ctypes.get_last_error())
        assigned = True
        if time.monotonic() >= deadline:
            kernel.TerminateJobObject(job, 124)
            raise TimeoutError("deadline reached before suspended process could resume")
        process_creation = _process_creation_filetime(kernel, int(process_info.hProcess))
        if before_resume is not None:
            before_resume(int(process_info.dwProcessId), process_creation)
        if kernel.ResumeThread(process_info.hThread) == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
        return {
            "handle": int(process_info.hProcess),
            "pid": int(process_info.dwProcessId),
            "createdFileTime": process_creation,
        }
    except Exception as primary:
        cleanup_errors: list[str] = []
        if stdio_release_failed:
            try:
                roles = ("stdout", "stderr", "stdin")
                release_details = []
                for index, confirmed in enumerate(stdio_release_confirmed):
                    if not confirmed:
                        error = stdio_release_errors[index]
                        detail = error if isinstance(error, int) else type(error).__name__
                        release_details.append(f"{roles[index]}={detail}")
                primary.add_note("stdio release unconfirmed: " + "; ".join(release_details))
            except BaseException:
                pass
        if assigned:
            if not kernel.TerminateJobObject(job, 2):
                cleanup_errors.append(f"TerminateJobObject failed: {ctypes.get_last_error()}")
        else:
            if not kernel.TerminateProcess(process_info.hProcess, 2):
                cleanup_errors.append(f"TerminateProcess failed: {ctypes.get_last_error()}")
        # Always make one nonblocking observation at an expired deadline. A live
        # suspended process must not be mistaken for a terminated one.
        remaining_ms = max(0, min(2000, int((deadline - time.monotonic()) * 1000)))
        wait_result = kernel.WaitForSingleObject(process_info.hProcess, remaining_ms)
        if wait_result != WAIT_OBJECT_0:
            cleanup_errors.append(
                f"created process termination was not confirmed (wait={wait_result})"
            )
        else:
            exit_code = wintypes.DWORD()
            if kernel.GetExitCodeProcess(process_info.hProcess, ctypes.byref(exit_code)):
                cleanup_errors.append(f"created process exit code observed: {exit_code.value}")
            else:
                cleanup_errors.append(
                    f"process exited but exit code unavailable: {ctypes.get_last_error()}"
                )
        if cleanup_errors and hasattr(primary, "add_note"):
            primary.add_note("launch cleanup: " + "; ".join(cleanup_errors))
        kernel.CloseHandle(process_info.hProcess)
        raise
    finally:
        kernel.CloseHandle(process_info.hThread)


def _process_creation_filetime(kernel: Any, process: int) -> int | None:
    creation = wintypes.FILETIME()
    exit_time = wintypes.FILETIME()
    kernel_time = wintypes.FILETIME()
    user_time = wintypes.FILETIME()
    if not kernel.GetProcessTimes(
        process,
        ctypes.byref(creation),
        ctypes.byref(exit_time),
        ctypes.byref(kernel_time),
        ctypes.byref(user_time),
    ):
        return None
    return (creation.dwHighDateTime << 32) | creation.dwLowDateTime


def _process_list(kernel: Any, job: int, deadline: float) -> list[int]:
    capacity = 32
    for _attempt in range(8):
        if time.monotonic() >= deadline:
            raise TimeoutError("deadline reached during bounded Job Object process census")
        size = ctypes.sizeof(wintypes.DWORD) * 2 + ctypes.sizeof(ctypes.c_size_t) * capacity
        buffer = ctypes.create_string_buffer(size)
        returned = wintypes.DWORD()
        ok = kernel.QueryInformationJobObject(
            job, JOB_OBJECT_BASIC_PROCESS_ID_LIST, buffer, size, ctypes.byref(returned)
        )
        count_assigned = ctypes.cast(buffer, ctypes.POINTER(wintypes.DWORD))[0]
        count_listed = ctypes.cast(
            ctypes.byref(buffer, ctypes.sizeof(wintypes.DWORD)), ctypes.POINTER(wintypes.DWORD)
        )[0]
        if ok:
            values = ctypes.cast(
                ctypes.byref(buffer, ctypes.sizeof(wintypes.DWORD) * 2),
                ctypes.POINTER(ctypes.c_size_t),
            )
            result = []
            for index in range(count_listed):
                if time.monotonic() >= deadline:
                    raise TimeoutError("deadline while reading bounded Job process IDs")
                result.append(int(values[index]))
            return result
        error = ctypes.get_last_error()
        if error != ERROR_MORE_DATA and returned.value <= size:
            raise ctypes.WinError(error)
        if capacity >= 65536:
            raise RuntimeError("Job Object process list exceeded fixed census bound")
        requested_capacity = max(
            capacity * 2,
            int(count_assigned),
            int(returned.value // ctypes.sizeof(ctypes.c_size_t)) + 8,
        )
        if requested_capacity > 65536:
            raise RuntimeError("Job Object process list exceeded fixed census bound")
        capacity = requested_capacity
    raise RuntimeError("Job Object process-list query exceeded eight bounded attempts")


def _job_active_count(kernel: Any, job: int) -> int:
    info = BASIC_ACCOUNTING_INFORMATION()
    if not kernel.QueryInformationJobObject(
        job, JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION, ctypes.byref(info), ctypes.sizeof(info), None
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(info.ActiveProcesses)


def _observe_selfcheck_unexpected_members(
    kernel: Any,
    job: int,
    deadline: float,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    started = time.monotonic()
    unexpected = sorted(int(pid) for pid in snapshot["unexpectedPids"])
    selected = unexpected[:8]
    result: dict[str, Any] = {
        "status": "observing",
        "startedMonotonicSeconds": started,
        "endedMonotonicSeconds": None,
        "originalSnapshotPhase": snapshot.get("phase"),
        "sourceCensusComplete": snapshot.get("complete") is True,
        "sourceSnapshotStartMonotonicSeconds": snapshot.get("observedStartMonotonicSeconds"),
        "sourceSnapshotEndMonotonicSeconds": snapshot.get("observedEndMonotonicSeconds"),
        "eligiblePidCount": len(unexpected),
        "attemptedPidCount": 0,
        "detailLimit": 8,
        "omittedDetailCount": len(unexpected) - len(selected),
        "deadlineReached": False,
        "observations": [],
        "errors": [],
    }

    def error_value(exc: BaseException) -> dict[str, Any]:
        return {"type": type(exc).__name__, "message": str(exc)}

    def observe_file_metadata(path: Path, phase: str) -> dict[str, Any]:
        started_at = time.monotonic()
        observation: dict[str, Any] = {
            "phase": phase,
            "canonicalPath": str(path),
            "status": "unverified",
            "startedMonotonicSeconds": started_at,
            "endedMonotonicSeconds": None,
            "regularFile": None,
            "reparsePoint": None,
            "metadata": None,
            "requiredComparable": False,
            "optionalAvailability": {
                "st_birthtime_ns": None,
                "st_file_attributes": None,
            },
            "error": None,
        }
        if started_at >= deadline:
            observation["status"] = "deadline-exhausted"
            observation["error"] = {
                "type": "TimeoutError",
                "message": "deadline before file metadata",
            }
            observation["endedMonotonicSeconds"] = time.monotonic()
            return observation
        try:
            link_info = path.lstat()
            if time.monotonic() >= deadline:
                observation["status"] = "deadline-exhausted"
                observation["error"] = {
                    "type": "TimeoutError",
                    "message": "deadline after no-follow metadata",
                }
                observation["endedMonotonicSeconds"] = time.monotonic()
                return observation
            file_info = path.stat()
            ended_at = time.monotonic()
            attributes_available = hasattr(file_info, "st_file_attributes")
            link_attributes_available = hasattr(link_info, "st_file_attributes")
            attributes = int(file_info.st_file_attributes) if attributes_available else None
            link_attributes = (
                int(link_info.st_file_attributes) if link_attributes_available else None
            )
            reparse_point = stat.S_ISLNK(link_info.st_mode) or bool(
                (attributes is not None and attributes & 0x400)
                or (link_attributes is not None and link_attributes & 0x400)
            )
            regular_file = stat.S_ISREG(file_info.st_mode) and not reparse_point
            birthtime_available = hasattr(file_info, "st_birthtime_ns")
            metadata = {
                "st_dev": int(file_info.st_dev) if hasattr(file_info, "st_dev") else None,
                "st_ino": int(file_info.st_ino) if hasattr(file_info, "st_ino") else None,
                "st_size": int(file_info.st_size) if hasattr(file_info, "st_size") else None,
                "st_mtime_ns": (
                    int(file_info.st_mtime_ns) if hasattr(file_info, "st_mtime_ns") else None
                ),
                "st_ctime_ns": (
                    int(file_info.st_ctime_ns) if hasattr(file_info, "st_ctime_ns") else None
                ),
                "st_mode": int(file_info.st_mode) if hasattr(file_info, "st_mode") else None,
                "st_file_attributes": attributes,
                "st_birthtime_ns": (
                    int(file_info.st_birthtime_ns) if birthtime_available else None
                ),
            }
            required_fields = (
                "st_dev",
                "st_ino",
                "st_size",
                "st_mtime_ns",
                "st_ctime_ns",
                "st_mode",
            )
            required_comparable = all(metadata[name] is not None for name in required_fields)
            required_comparable = required_comparable and metadata["st_ino"] != 0
            observation.update(
                {
                    "endedMonotonicSeconds": ended_at,
                    "regularFile": regular_file,
                    "reparsePoint": reparse_point,
                    "metadata": metadata,
                    "requiredComparable": required_comparable,
                    "optionalAvailability": {
                        "st_birthtime_ns": birthtime_available,
                        "st_file_attributes": attributes_available,
                        "nofollow_file_attributes": link_attributes_available,
                    },
                    "late": ended_at >= deadline,
                    "status": (
                        "observed"
                        if regular_file and required_comparable and ended_at < deadline
                        else "unverified"
                    ),
                }
            )
            if ended_at >= deadline:
                observation["status"] = "deadline-exhausted"
            elif not regular_file:
                observation["error"] = {
                    "type": "UnsafeFileType",
                    "message": "file endpoint is not a regular non-reparse file",
                }
            elif not required_comparable:
                observation["error"] = {
                    "type": "UnsupportedMetadata",
                    "message": "required file identity/size/nanosecond metadata is unavailable",
                }
            return observation
        except Exception as exc:
            observation["endedMonotonicSeconds"] = time.monotonic()
            observation["status"] = (
                "deadline-exhausted" if time.monotonic() >= deadline else "unverified"
            )
            observation["error"] = error_value(exc)
            return observation

    def compare_file_metadata(
        before: dict[str, Any], same_path: dict[str, Any], after_resolve: dict[str, Any]
    ) -> tuple[str, str | None]:
        endpoints = (before, same_path, after_resolve)
        if any(endpoint.get("status") == "deadline-exhausted" for endpoint in endpoints):
            return "deadline-exhausted", "deadline expired during endpoint metadata comparison"
        if any(endpoint.get("status") != "observed" for endpoint in endpoints):
            return "unverified", "one or more file metadata endpoints are unavailable or unsafe"
        canonical_paths = [endpoint.get("canonicalPath") for endpoint in endpoints]
        if canonical_paths[0] != canonical_paths[1] or canonical_paths[0] != canonical_paths[2]:
            return "changed", "canonical file path differed between metadata endpoints"
        required_fields = (
            "st_dev",
            "st_ino",
            "st_size",
            "st_mtime_ns",
            "st_ctime_ns",
            "st_mode",
        )
        metadata = [endpoint["metadata"] for endpoint in endpoints]
        if any(any(values.get(name) is None for name in required_fields) for values in metadata):
            return "unverified", "required file metadata is not comparable"
        availability = [endpoint["optionalAvailability"] for endpoint in endpoints]
        for optional_name in ("st_birthtime_ns", "st_file_attributes"):
            flags = [values.get(optional_name) for values in availability]
            if len(set(flags)) != 1:
                return "unverified", f"{optional_name} availability differs across endpoints"
        for field_name in required_fields:
            values = [metadata_item[field_name] for metadata_item in metadata]
            if values[0] != values[1] or values[0] != values[2]:
                return "changed", f"{field_name} differed across file metadata endpoints"
        for optional_name in ("st_birthtime_ns", "st_file_attributes"):
            if availability[0].get(optional_name):
                values = [metadata_item[optional_name] for metadata_item in metadata]
                if values[0] is None or values[0] != values[1] or values[0] != values[2]:
                    return "changed", f"{optional_name} differed across file metadata endpoints"
        return "observed-metadata-match", None

    def verify_image_path(row: dict[str, Any], raw_path: str) -> None:
        stability = row["imageStability"]
        stability["rawPath"] = raw_path

        def partial(status: str, reason: str, error: dict[str, Any] | None = None) -> None:
            stability["status"] = status
            stability["reason"] = reason
            if error is not None:
                stability["errors"].append(error)
            row["imageSha256"].update(
                {
                    "status": (
                        "deadline-exhausted"
                        if status == "deadline-exhausted"
                        else "unverified-stability"
                    ),
                    "value": None,
                }
            )
            if status == "deadline-exhausted":
                result["deadlineReached"] = True

        try:
            if not Path(raw_path).is_absolute():
                partial("unverified", "native image path is not absolute")
                return
            if time.monotonic() >= deadline:
                partial("deadline-exhausted", "deadline before canonical path resolution")
                return
            resolve_before_started = time.monotonic()
            canonical_before = Path(raw_path).resolve(strict=True)
            resolve_before_ended = time.monotonic()
            stability["canonicalBefore"] = str(canonical_before)
            stability["resolveBefore"] = {
                "status": "observed" if resolve_before_ended < deadline else "late",
                "startedMonotonicSeconds": resolve_before_started,
                "endedMonotonicSeconds": resolve_before_ended,
            }
            row["imagePath"]["canonicalPath"] = str(canonical_before)
            row["imagePath"]["canonicalStatus"] = (
                "observed" if resolve_before_ended < deadline else "deadline-exhausted"
            )
            stability["rawPathCanonicalMatch"] = raw_path == str(canonical_before)
            if resolve_before_ended >= deadline:
                partial("deadline-exhausted", "canonical path resolution completed after deadline")
                return
            before_metadata = observe_file_metadata(canonical_before, "before-hash")
            stability["metadataBeforeHash"] = before_metadata
            if before_metadata["status"] != "observed":
                partial(
                    "deadline-exhausted"
                    if before_metadata["status"] == "deadline-exhausted"
                    else "unverified",
                    "pre-hash file metadata is unavailable, unsafe, or incomparable",
                    before_metadata.get("error"),
                )
                return
            if stability["rawPathCanonicalMatch"] is not True:
                partial(
                    "unverified",
                    "native raw path differs from its exact canonical filesystem spelling",
                )
                return
            if time.monotonic() >= deadline:
                partial("deadline-exhausted", "deadline before file hash")
                return
            hash_started = time.monotonic()
            try:
                candidate_digest = _sha256(canonical_before, deadline)
                hash_ended = time.monotonic()
                row["imageSha256"].update(
                    {
                        "status": "provisional",
                        "value": None,
                        "candidateValue": candidate_digest,
                        "hashStartedMonotonicSeconds": hash_started,
                        "hashEndedMonotonicSeconds": hash_ended,
                    }
                )
            except Exception as exc:
                status = "deadline-exhausted" if time.monotonic() >= deadline else "unverified"
                partial(status, "existing file hash did not complete", error_value(exc))
                return
            if time.monotonic() >= deadline:
                partial("deadline-exhausted", "file hash completed at or after deadline")
                return
            metadata_same_path = observe_file_metadata(canonical_before, "after-hash-same-path")
            stability["metadataAfterSamePath"] = metadata_same_path
            if time.monotonic() >= deadline:
                partial("deadline-exhausted", "same-path metadata completed at or after deadline")
                return
            resolve_after_started = time.monotonic()
            canonical_after = Path(raw_path).resolve(strict=True)
            resolve_after_ended = time.monotonic()
            stability["canonicalAfter"] = str(canonical_after)
            stability["resolveAfter"] = {
                "status": "observed" if resolve_after_ended < deadline else "late",
                "startedMonotonicSeconds": resolve_after_started,
                "endedMonotonicSeconds": resolve_after_ended,
            }
            if resolve_after_ended >= deadline:
                partial("deadline-exhausted", "post-hash path resolution completed after deadline")
                return
            metadata_after_resolve = observe_file_metadata(
                canonical_after, "after-hash-resolved-path"
            )
            stability["metadataAfterResolve"] = metadata_after_resolve
            if time.monotonic() >= deadline:
                partial(
                    "deadline-exhausted", "resolved-path metadata completed at or after deadline"
                )
                return
            comparison, reason = compare_file_metadata(
                before_metadata, metadata_same_path, metadata_after_resolve
            )
            stability["comparison"] = reason or "required and available optional metadata matched"
            if str(canonical_after) != str(canonical_before):
                comparison = "changed"
                stability["comparison"] = "canonical target changed for the same raw native path"
            if time.monotonic() >= deadline:
                partial("deadline-exhausted", "deadline before endpoint stability acceptance")
                return
            if comparison == "observed-metadata-match":
                stability["status"] = comparison
                row["imageSha256"].update(
                    {
                        "status": "observed",
                        "value": candidate_digest,
                        "candidateValue": None,
                    }
                )
                return
            if comparison == "changed":
                stability["status"] = "changed"
                stability["reason"] = stability["comparison"]
                row["imageSha256"].update(
                    {
                        "status": "changed/unverified",
                        "value": None,
                        "candidateValue": candidate_digest,
                    }
                )
                return
            partial("unverified", reason or "file endpoint metadata did not verify")
            row["imageSha256"]["candidateValue"] = candidate_digest
        except Exception as exc:
            try:
                status = "deadline-exhausted" if time.monotonic() >= deadline else "unverified"
                partial(
                    status, "same-path image stability could not be established", error_value(exc)
                )
            except Exception:
                pass

    for pid in selected:
        if time.monotonic() >= deadline:
            result["deadlineReached"] = True
            break
        row: dict[str, Any] = {
            "censusPid": pid,
            "censusSnapshotStartMonotonicSeconds": snapshot.get("observedStartMonotonicSeconds"),
            "censusSnapshotEndMonotonicSeconds": snapshot.get("observedEndMonotonicSeconds"),
            "detailStartedMonotonicSeconds": time.monotonic(),
            "censusIdentityAssociation": "unproven",
            "historicalProcessAssociation": {
                "status": "unknown",
                "reason": "PID may have disappeared or been reused between census and open",
            },
            "open": {"status": "not-attempted", "requestedAccessMask": None},
            "membershipBefore": {"status": "not-attempted", "value": None},
            "creationBefore": {"status": "not-attempted", "value": None},
            "exitTimeBefore": {"status": "not-attempted", "value": None},
            "zeroTimeWait": {"status": "not-attempted", "result": None},
            "exitCode": {"status": "not-attempted", "rawValue": None},
            "imagePath": {"status": "not-attempted", "rawPath": None},
            "imageSha256": {
                "status": "not-attempted",
                "value": None,
                "candidateValue": None,
            },
            "imageStability": {
                "status": "not-attempted",
                "startedMonotonicSeconds": None,
                "endedMonotonicSeconds": None,
                "rawPathCanonicalMatch": None,
                "canonicalBefore": None,
                "canonicalAfter": None,
                "metadataBeforeHash": None,
                "metadataAfterSamePath": None,
                "metadataAfterResolve": None,
                "comparison": None,
                "errors": [],
            },
            "creationAfter": {"status": "not-attempted", "value": None},
            "exitTimeAfter": {"status": "not-attempted", "value": None},
            "membershipAfter": {"status": "not-attempted", "value": None},
            "parentOriginAndClass": "unestablished",
            "handleClose": {
                "status": "unobserved",
                "closeAttempted": None,
                "releaseStatus": "unknown",
                "startedMonotonicSeconds": None,
                "startedReason": "pre-close telemetry omitted for cleanup safety",
                "endedMonotonicSeconds": None,
                "error": None,
            },
            "errors": [],
        }
        result["observations"].append(row)
        requested_access = (
            PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_QUERY_INFORMATION | SYNCHRONIZE
        )
        row["open"]["requestedAccessMask"] = requested_access
        if time.monotonic() >= deadline:
            row["open"] = {
                "status": "deadline-exhausted",
                "requestedAccessMask": requested_access,
            }
            row["handleClose"].update(
                {"status": "not-opened", "closeAttempted": False, "releaseStatus": "not-applicable"}
            )
            row["detailEndedMonotonicSeconds"] = time.monotonic()
            result["deadlineReached"] = True
            break
        result["attemptedPidCount"] += 1
        open_started = time.monotonic()
        try:
            handle = kernel.OpenProcess(requested_access, False, pid)
        except Exception as exc:
            row["open"] = {
                "status": "error",
                "requestedAccessMask": requested_access,
                "startedMonotonicSeconds": open_started,
                "endedMonotonicSeconds": time.monotonic(),
                "error": error_value(exc),
            }
            row["handleClose"].update(
                {"status": "not-opened", "closeAttempted": False, "releaseStatus": "not-applicable"}
            )
            row["errors"].append({"field": "open", **error_value(exc)})
            row["detailEndedMonotonicSeconds"] = time.monotonic()
            if time.monotonic() >= deadline:
                result["deadlineReached"] = True
            continue
        if not handle:
            error_code = ctypes.get_last_error()
            error = {
                "type": "WinError",
                "code": error_code,
                "message": str(ctypes.WinError(error_code)),
            }
            row["open"] = {
                "status": "unavailable",
                "requestedAccessMask": requested_access,
                "startedMonotonicSeconds": open_started,
                "endedMonotonicSeconds": time.monotonic(),
                "error": error,
            }
            row["handleClose"].update(
                {"status": "not-opened", "closeAttempted": False, "releaseStatus": "not-applicable"}
            )
            row["errors"].append({"field": "open", **error})
            row["detailEndedMonotonicSeconds"] = time.monotonic()
            if time.monotonic() >= deadline:
                result["deadlineReached"] = True
            continue

        # The handle is locally owned from this point and is closed exactly once.
        try:
            row["open"] = {
                "status": "opened",
                "requestedAccessMask": requested_access,
                "startedMonotonicSeconds": open_started,
                "endedMonotonicSeconds": time.monotonic(),
                "late": time.monotonic() >= deadline,
            }

            def observe_membership(
                field_name: str, member_row: dict[str, Any], member_handle: int
            ) -> None:
                field = member_row[field_name]
                if time.monotonic() >= deadline:
                    field["status"] = "deadline-exhausted"
                    result["deadlineReached"] = True
                    return
                member = wintypes.BOOL()
                operation_started = time.monotonic()
                try:
                    call_succeeded = kernel.IsProcessInJob(member_handle, job, ctypes.byref(member))
                    operation_ended = time.monotonic()
                    if not call_succeeded:
                        error_code = ctypes.get_last_error()
                        field.update(
                            {
                                "status": "unavailable",
                                "value": None,
                                "startedMonotonicSeconds": operation_started,
                                "endedMonotonicSeconds": operation_ended,
                                "error": {
                                    "type": "WinError",
                                    "code": error_code,
                                    "message": str(ctypes.WinError(error_code)),
                                },
                            }
                        )
                    else:
                        field.update(
                            {
                                "status": "observed",
                                "value": bool(member.value),
                                "startedMonotonicSeconds": operation_started,
                                "endedMonotonicSeconds": operation_ended,
                                "late": operation_ended >= deadline,
                            }
                        )
                        if operation_ended >= deadline:
                            result["deadlineReached"] = True
                except Exception as exc:
                    field.update(
                        {
                            "status": "unavailable",
                            "value": None,
                            "startedMonotonicSeconds": operation_started,
                            "endedMonotonicSeconds": time.monotonic(),
                            "error": error_value(exc),
                        }
                    )
                    member_row["errors"].append({"field": field_name, **error_value(exc)})
                    if time.monotonic() >= deadline:
                        result["deadlineReached"] = True

            observe_membership("membershipBefore", row, handle)

            if time.monotonic() < deadline:
                operation_started = time.monotonic()
                creation = wintypes.FILETIME()
                exit_time = wintypes.FILETIME()
                kernel_time = wintypes.FILETIME()
                user_time = wintypes.FILETIME()
                try:
                    succeeded = kernel.GetProcessTimes(
                        handle,
                        ctypes.byref(creation),
                        ctypes.byref(exit_time),
                        ctypes.byref(kernel_time),
                        ctypes.byref(user_time),
                    )
                    operation_ended = time.monotonic()
                    if not succeeded:
                        error_code = ctypes.get_last_error()
                        failure = {
                            "type": "WinError",
                            "code": error_code,
                            "message": str(ctypes.WinError(error_code)),
                        }
                        row["creationBefore"].update(
                            {"status": "unavailable", "value": None, "error": failure}
                        )
                        row["exitTimeBefore"].update(
                            {"status": "unavailable", "value": None, "error": failure}
                        )
                    else:
                        creation_value = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
                        exit_value = (exit_time.dwHighDateTime << 32) | exit_time.dwLowDateTime
                        row["creationBefore"].update(
                            {
                                "status": "observed",
                                "value": creation_value,
                                "startedMonotonicSeconds": operation_started,
                                "endedMonotonicSeconds": operation_ended,
                                "late": operation_ended >= deadline,
                            }
                        )
                        row["exitTimeBefore"].update(
                            {
                                "status": "observed",
                                "value": exit_value,
                                "startedMonotonicSeconds": operation_started,
                                "endedMonotonicSeconds": operation_ended,
                                "late": operation_ended >= deadline,
                            }
                        )
                    if operation_ended >= deadline:
                        result["deadlineReached"] = True
                except Exception as exc:
                    failure = error_value(exc)
                    row["creationBefore"].update(
                        {"status": "unavailable", "value": None, "error": failure}
                    )
                    row["exitTimeBefore"].update(
                        {"status": "unavailable", "value": None, "error": failure}
                    )
                    row["errors"].append({"field": "process-times-before", **failure})
            else:
                row["creationBefore"]["status"] = "deadline-exhausted"
                row["exitTimeBefore"]["status"] = "deadline-exhausted"
                result["deadlineReached"] = True

            if time.monotonic() < deadline:
                operation_started = time.monotonic()
                try:
                    wait_result = int(kernel.WaitForSingleObject(handle, 0))
                    operation_ended = time.monotonic()
                    wait_status = (
                        "signaled"
                        if wait_result == WAIT_OBJECT_0
                        else "nonsignaled"
                        if wait_result == WAIT_TIMEOUT
                        else "unavailable"
                    )
                    row["zeroTimeWait"].update(
                        {
                            "status": wait_status,
                            "result": wait_result,
                            "startedMonotonicSeconds": operation_started,
                            "endedMonotonicSeconds": operation_ended,
                            "late": operation_ended >= deadline,
                        }
                    )
                    if wait_status == "unavailable":
                        error_code = ctypes.get_last_error()
                        row["zeroTimeWait"]["error"] = {
                            "type": "WinError",
                            "code": error_code,
                            "message": str(ctypes.WinError(error_code)),
                        }
                    if operation_ended >= deadline:
                        result["deadlineReached"] = True
                except Exception as exc:
                    row["zeroTimeWait"].update(
                        {
                            "status": "unavailable",
                            "result": None,
                            "error": error_value(exc),
                        }
                    )
                    row["errors"].append({"field": "zero-time-wait", **error_value(exc)})
            else:
                row["zeroTimeWait"]["status"] = "deadline-exhausted"
                result["deadlineReached"] = True

            if time.monotonic() < deadline:
                operation_started = time.monotonic()
                code = wintypes.DWORD()
                try:
                    succeeded = kernel.GetExitCodeProcess(handle, ctypes.byref(code))
                    operation_ended = time.monotonic()
                    if succeeded:
                        row["exitCode"].update(
                            {
                                "status": "observed",
                                "rawValue": int(code.value),
                                "interpretation": (
                                    "STILL_ACTIVE sentinel; liveness remains ambiguous"
                                    if code.value == STILL_ACTIVE
                                    else "raw exit value observed; census association unproven"
                                ),
                                "startedMonotonicSeconds": operation_started,
                                "endedMonotonicSeconds": operation_ended,
                                "late": operation_ended >= deadline,
                            }
                        )
                    else:
                        error_code = ctypes.get_last_error()
                        row["exitCode"].update(
                            {
                                "status": "unavailable",
                                "rawValue": None,
                                "error": {
                                    "type": "WinError",
                                    "code": error_code,
                                    "message": str(ctypes.WinError(error_code)),
                                },
                            }
                        )
                    if operation_ended >= deadline:
                        result["deadlineReached"] = True
                except Exception as exc:
                    row["exitCode"].update(
                        {"status": "unavailable", "rawValue": None, "error": error_value(exc)}
                    )
                    row["errors"].append({"field": "exit-code", **error_value(exc)})
            else:
                row["exitCode"]["status"] = "deadline-exhausted"
                result["deadlineReached"] = True

            if time.monotonic() < deadline:
                operation_started = time.monotonic()
                try:
                    image_buffer = ctypes.create_unicode_buffer(32768)
                    image_size = wintypes.DWORD(len(image_buffer))
                    succeeded = kernel.QueryFullProcessImageNameW(
                        handle, 0, image_buffer, ctypes.byref(image_size)
                    )
                    operation_ended = time.monotonic()
                    if not succeeded:
                        error_code = ctypes.get_last_error()
                        stability_started = operation_started
                        stability_ended = time.monotonic()
                        row["imagePath"].update(
                            {
                                "status": "unavailable",
                                "rawPath": None,
                                "error": {
                                    "type": "WinError",
                                    "code": error_code,
                                    "message": str(ctypes.WinError(error_code)),
                                },
                            }
                        )
                        row["imageStability"].update(
                            {
                                "status": "unverified",
                                "startedMonotonicSeconds": stability_started,
                                "endedMonotonicSeconds": stability_ended,
                                "reason": "native image path query was unavailable",
                            }
                        )
                        row["imageSha256"].update({"status": "unverified-stability", "value": None})
                    else:
                        raw_path = image_buffer.value
                        row["imagePath"].update(
                            {
                                "status": "observed",
                                "rawPath": raw_path,
                                "reportedCharacterCount": int(image_size.value),
                                "startedMonotonicSeconds": operation_started,
                                "endedMonotonicSeconds": operation_ended,
                                "late": operation_ended >= deadline,
                            }
                        )
                        row["imageStability"]["startedMonotonicSeconds"] = time.monotonic()
                        verify_image_path(row, raw_path)
                        row["imageStability"]["endedMonotonicSeconds"] = time.monotonic()
                    if operation_ended >= deadline:
                        result["deadlineReached"] = True
                        row["imageStability"].update(
                            {
                                "status": "deadline-exhausted",
                                "startedMonotonicSeconds": operation_started,
                                "endedMonotonicSeconds": time.monotonic(),
                                "reason": "native image path query completed after deadline",
                            }
                        )
                        row["imageSha256"].update({"status": "deadline-exhausted", "value": None})
                except Exception as exc:
                    try:
                        failure = error_value(exc)
                        row["imagePath"].update(
                            {"status": "unavailable", "rawPath": None, "error": failure}
                        )
                        row["imageSha256"].update({"status": "unverified-stability", "value": None})
                        row["imageStability"].update(
                            {
                                "status": "unverified",
                                "startedMonotonicSeconds": operation_started,
                                "endedMonotonicSeconds": time.monotonic(),
                                "reason": "native image path query/reporting failed",
                            }
                        )
                        row["errors"].append({"field": "image-path", **failure})
                    except Exception:
                        pass
            else:
                row["imagePath"]["status"] = "deadline-exhausted"
                row["imageStability"].update(
                    {
                        "status": "deadline-exhausted",
                        "startedMonotonicSeconds": time.monotonic(),
                        "endedMonotonicSeconds": time.monotonic(),
                        "reason": "deadline before native image path query",
                    }
                )
                row["imageSha256"].update({"status": "deadline-exhausted", "value": None})
                result["deadlineReached"] = True

            if time.monotonic() < deadline:
                operation_started = time.monotonic()
                creation = wintypes.FILETIME()
                exit_time = wintypes.FILETIME()
                kernel_time = wintypes.FILETIME()
                user_time = wintypes.FILETIME()
                try:
                    succeeded = kernel.GetProcessTimes(
                        handle,
                        ctypes.byref(creation),
                        ctypes.byref(exit_time),
                        ctypes.byref(kernel_time),
                        ctypes.byref(user_time),
                    )
                    operation_ended = time.monotonic()
                    if not succeeded:
                        error_code = ctypes.get_last_error()
                        failure = {
                            "type": "WinError",
                            "code": error_code,
                            "message": str(ctypes.WinError(error_code)),
                        }
                        row["creationAfter"].update(
                            {"status": "unavailable", "value": None, "error": failure}
                        )
                        row["exitTimeAfter"].update(
                            {"status": "unavailable", "value": None, "error": failure}
                        )
                    else:
                        row["creationAfter"].update(
                            {
                                "status": "observed",
                                "value": (creation.dwHighDateTime << 32) | creation.dwLowDateTime,
                                "startedMonotonicSeconds": operation_started,
                                "endedMonotonicSeconds": operation_ended,
                                "late": operation_ended >= deadline,
                            }
                        )
                        row["exitTimeAfter"].update(
                            {
                                "status": "observed",
                                "value": (exit_time.dwHighDateTime << 32) | exit_time.dwLowDateTime,
                                "startedMonotonicSeconds": operation_started,
                                "endedMonotonicSeconds": operation_ended,
                                "late": operation_ended >= deadline,
                            }
                        )
                    if operation_ended >= deadline:
                        result["deadlineReached"] = True
                except Exception as exc:
                    failure = error_value(exc)
                    row["creationAfter"].update(
                        {"status": "unavailable", "value": None, "error": failure}
                    )
                    row["exitTimeAfter"].update(
                        {"status": "unavailable", "value": None, "error": failure}
                    )
                    row["errors"].append({"field": "process-times-after", **failure})
            else:
                row["creationAfter"]["status"] = "deadline-exhausted"
                row["exitTimeAfter"]["status"] = "deadline-exhausted"
                result["deadlineReached"] = True

            observe_membership("membershipAfter", row, handle)
            row["detailEndedMonotonicSeconds"] = time.monotonic()
            row["parentOriginAndClass"] = {
                "status": "unestablished",
                "trustedParent": False,
                "trustedClass": False,
            }
        finally:
            try:
                close_result = kernel.CloseHandle(handle)
            except Exception as close_exception:
                try:
                    row["handleClose"].update(
                        {
                            "status": "close-failed/release-unconfirmed",
                            "closeAttempted": True,
                            "releaseStatus": "unknown",
                            "startedMonotonicSeconds": None,
                            "startedReason": "pre-close telemetry omitted for cleanup safety",
                            "endedMonotonicSeconds": time.monotonic(),
                            "error": error_value(close_exception),
                        }
                    )
                    if time.monotonic() >= deadline:
                        result["deadlineReached"] = True
                except Exception:
                    pass
            else:
                try:
                    if close_result:
                        row["handleClose"].update(
                            {
                                "status": "released",
                                "closeAttempted": True,
                                "releaseStatus": "released",
                                "startedMonotonicSeconds": None,
                                "startedReason": "pre-close telemetry omitted for cleanup safety",
                                "endedMonotonicSeconds": time.monotonic(),
                                "error": None,
                            }
                        )
                    else:
                        error_code = ctypes.get_last_error()
                        row["handleClose"].update(
                            {
                                "status": "close-failed/release-unconfirmed",
                                "closeAttempted": True,
                                "releaseStatus": "unknown",
                                "startedMonotonicSeconds": None,
                                "startedReason": "pre-close telemetry omitted for cleanup safety",
                                "endedMonotonicSeconds": time.monotonic(),
                                "error": {
                                    "type": "WinError",
                                    "code": error_code,
                                    "message": str(ctypes.WinError(error_code)),
                                },
                            }
                        )
                    if time.monotonic() >= deadline:
                        result["deadlineReached"] = True
                except Exception:
                    pass

    result["omittedDetailCount"] = max(0, result["eligiblePidCount"] - result["attemptedPidCount"])
    result["endedMonotonicSeconds"] = time.monotonic()
    if result["deadlineReached"]:
        result["status"] = "deadline-exhausted"
    elif result["omittedDetailCount"]:
        result["status"] = "partial-capped"
    elif any(
        row["errors"]
        or row["open"]["status"] != "opened"
        or row["membershipBefore"]["status"] != "observed"
        or row["creationBefore"]["status"] != "observed"
        or row["exitTimeBefore"]["status"] != "observed"
        or row["zeroTimeWait"]["status"] not in ("signaled", "nonsignaled")
        or row["exitCode"]["status"] != "observed"
        or row["imagePath"].get("canonicalStatus") != "observed"
        or row["imageStability"]["status"] != "observed-metadata-match"
        or row["imageSha256"]["status"] != "observed"
        or row["creationAfter"]["status"] != "observed"
        or row["exitTimeAfter"]["status"] != "observed"
        or row["membershipAfter"]["status"] != "observed"
        or row["handleClose"]["status"] != "released"
        for row in result["observations"]
    ):
        result["status"] = "partial-observation"
    else:
        result["status"] = "observed"
    return result


def _selfcheck_job_snapshot(
    kernel: Any,
    job: int | None,
    deadline: float,
    phase: str,
    normal_completion: dict[str, Any],
) -> dict[str, Any]:
    started = time.monotonic()

    def accounting(label: str) -> dict[str, Any]:
        if job is None:
            return {"status": "unavailable", "value": None, "error": "inner Job unavailable"}
        if time.monotonic() >= deadline:
            return {"status": "deadline-exhausted", "value": None, "error": None}
        try:
            info = BASIC_ACCOUNTING_INFORMATION()
            if not kernel.QueryInformationJobObject(
                job,
                JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION,
                ctypes.byref(info),
                ctypes.sizeof(info),
                None,
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            if time.monotonic() >= deadline:
                return {"status": "deadline-exhausted", "value": None, "error": None}
            return {"status": "observed", "value": int(info.ActiveProcesses), "error": None}
        except Exception as exc:
            return {
                "status": "deadline-exhausted" if time.monotonic() >= deadline else "unavailable",
                "value": None,
                "error": {"type": type(exc).__name__, "message": str(exc), "phase": label},
            }

    before = accounting("accounting-before")
    census: dict[str, Any] = {
        "status": "unavailable",
        "complete": False,
        "pids": None,
        "partialPids": None,
        "countAssigned": None,
        "countListed": None,
        "bufferCapacity": None,
        "bufferBytes": None,
        "returnedBytes": None,
        "attempts": 0,
        "queryError": None,
    }
    if job is None:
        census["queryError"] = {"type": "Unavailable", "message": "inner Job unavailable"}
    else:
        capacity = 32
        header_size = ctypes.sizeof(wintypes.DWORD) * 2
        for attempt in range(8):
            census["attempts"] = attempt + 1
            if time.monotonic() >= deadline:
                census["status"] = "deadline-exhausted"
                census["queryError"] = {
                    "type": "TimeoutError",
                    "message": "deadline before PID census",
                }
                break
            size = header_size + ctypes.sizeof(ctypes.c_size_t) * capacity
            buffer = ctypes.create_string_buffer(size)
            returned = wintypes.DWORD()
            try:
                ok = kernel.QueryInformationJobObject(
                    job,
                    JOB_OBJECT_BASIC_PROCESS_ID_LIST,
                    buffer,
                    size,
                    ctypes.byref(returned),
                )
                census["bufferCapacity"] = capacity
                census["bufferBytes"] = size
                census["returnedBytes"] = int(returned.value)
                if time.monotonic() >= deadline:
                    census["status"] = "deadline-exhausted"
                    census["queryError"] = {
                        "type": "TimeoutError",
                        "message": "deadline during PID census",
                    }
                    break
                if ok and returned.value > size:
                    census["queryError"] = {
                        "type": "InvalidBufferLength",
                        "message": f"returned bytes {returned.value} exceed allocated bytes {size}",
                    }
                    census["status"] = "incomplete"
                    break
                if returned.value and returned.value < header_size:
                    census["queryError"] = {
                        "type": "InvalidHeaderLength",
                        "message": "reported returned-byte count is below the PID-list header size",
                    }
                    census["status"] = "incomplete"
                    break
                assigned = int(ctypes.cast(buffer, ctypes.POINTER(wintypes.DWORD))[0])
                listed = int(
                    ctypes.cast(
                        ctypes.byref(buffer, ctypes.sizeof(wintypes.DWORD)),
                        ctypes.POINTER(wintypes.DWORD),
                    )[0]
                )
                census["countAssigned"] = assigned
                census["countListed"] = listed
                if assigned > 65536 or listed > 65536:
                    census["status"] = "incomplete"
                    census["queryError"] = {
                        "type": "InvalidProcessCount",
                        "message": "Job PID header exceeds the fixed 65536-process bound",
                    }
                    break
                if listed > capacity:
                    census["queryError"] = {
                        "type": "CapacityMismatch",
                        "message": f"listed count {listed} exceeds capacity {capacity}",
                    }
                    if capacity >= 65536 or attempt == 7:
                        census["status"] = "incomplete"
                        break
                    capacity = min(65536, max(capacity * 2, listed, assigned))
                    continue
                if returned.value and returned.value < header_size + listed * ctypes.sizeof(
                    ctypes.c_size_t
                ):
                    census["queryError"] = {
                        "type": "ShortPidBuffer",
                        "message": "reported returned-byte count does not contain every listed PID",
                    }
                    census["status"] = "incomplete"
                    break
                values = ctypes.cast(
                    ctypes.byref(buffer, header_size), ctypes.POINTER(ctypes.c_size_t)
                )
                partial = []
                for index in range(listed):
                    if time.monotonic() >= deadline:
                        census["status"] = "deadline-exhausted"
                        census["queryError"] = {
                            "type": "TimeoutError",
                            "message": "deadline while reading PID census",
                        }
                        break
                    partial.append(int(values[index]))
                census["partialPids"] = partial
                if census["status"] == "deadline-exhausted":
                    break
                if not ok:
                    error_code = ctypes.get_last_error()
                    census["queryError"] = {
                        "type": "WinError",
                        "code": error_code,
                        "message": str(ctypes.WinError(error_code)),
                    }
                    if error_code == ERROR_MORE_DATA and capacity < 65536 and attempt < 7:
                        capacity = min(65536, max(capacity * 2, assigned, listed + 8))
                        continue
                    census["status"] = "incomplete"
                    break
                if assigned != listed:
                    census["queryError"] = {
                        "type": "AssignmentMismatch",
                        "message": f"assigned count {assigned} differs from listed count {listed}",
                    }
                    if capacity < 65536 and attempt < 7:
                        capacity = min(65536, max(capacity * 2, assigned, listed + 8))
                        continue
                    census["status"] = "incomplete"
                    break
                if any(pid <= 0 or pid > 0xFFFFFFFF for pid in partial) or len(set(partial)) != len(
                    partial
                ):
                    census["queryError"] = {
                        "type": "InvalidPidList",
                        "message": "PID list contains zero, out-of-range, or duplicate identifiers",
                    }
                    census["status"] = "incomplete"
                    break
                census["pids"] = partial
                census["status"] = "complete"
                census["complete"] = True
                census["queryError"] = None
                break
            except Exception as exc:
                census["status"] = (
                    "deadline-exhausted" if time.monotonic() >= deadline else "unavailable"
                )
                census["queryError"] = {"type": type(exc).__name__, "message": str(exc)}
                break
        else:
            census["status"] = "incomplete"
            census["queryError"] = {
                "type": "AttemptLimit",
                "message": "PID census exceeded eight attempts",
            }

    after = accounting("accounting-after")
    known_pids = sorted(
        {
            int(identity["pid"])
            for identity in normal_completion.get("identities", {}).values()
            if isinstance(identity, dict) and identity.get("pid") is not None
        }
    )
    pids = census["pids"]
    complete = (
        before["status"] == "observed" and after["status"] == "observed" and census["complete"]
    )
    snapshot = {
        "phase": phase,
        "observedStartMonotonicSeconds": started,
        "observedEndMonotonicSeconds": time.monotonic(),
        "accountingBefore": before,
        "pidCensus": census,
        "accountingAfter": after,
        "normalPairIdentities": normal_completion.get("identities"),
        "waitStates": normal_completion.get("waits"),
        "exitStates": normal_completion.get("exits"),
        "knownNormalPairPids": known_pids,
        "unexpectedPids": sorted(set(pids) - set(known_pids)) if pids is not None else None,
        "complete": complete,
    }
    if complete and snapshot["unexpectedPids"]:
        try:
            snapshot["unexpectedMemberDetails"] = _observe_selfcheck_unexpected_members(
                kernel, job, deadline, snapshot
            )
        except Exception as diagnostic_error:
            try:
                snapshot["unexpectedMemberDetails"] = {
                    "status": "diagnostic-error",
                    "startedMonotonicSeconds": time.monotonic(),
                    "endedMonotonicSeconds": time.monotonic(),
                    "originalSnapshotPhase": phase,
                    "sourceCensusComplete": complete,
                    "eligiblePidCount": len(snapshot["unexpectedPids"]),
                    "attemptedPidCount": None,
                    "detailLimit": 8,
                    "omittedDetailCount": len(snapshot["unexpectedPids"]),
                    "deadlineReached": time.monotonic() >= deadline,
                    "observations": [],
                    "errors": [
                        {"type": type(diagnostic_error).__name__, "message": str(diagnostic_error)}
                    ],
                }
            except Exception:
                pass
    return snapshot


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


def _sample_job(
    kernel: Any, psapi: Any, job: int, runner_pid: int, deadline: float
) -> dict[str, Any]:
    rows = []
    concurrent_sum = 0
    unavailable = []
    for pid in _process_list(kernel, job, deadline):
        if time.monotonic() >= deadline:
            raise TimeoutError("deadline reached during optional resource sample")
        handle = kernel.OpenProcess(0x1000 | 0x0010, False, pid)
        if not handle:
            unavailable.append(
                {"pid": pid, "reason": f"OpenProcess winerror={ctypes.get_last_error()}"}
            )
            continue
        try:
            counters = _PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(counters)
            if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                unavailable.append(
                    {
                        "pid": pid,
                        "reason": f"GetProcessMemoryInfo winerror={ctypes.get_last_error()}",
                    }
                )
                continue
            path_buffer = ctypes.create_unicode_buffer(32768)
            path_size = wintypes.DWORD(len(path_buffer))
            image = None
            if kernel.QueryFullProcessImageNameW(handle, 0, path_buffer, ctypes.byref(path_size)):
                image = path_buffer.value
            creation = wintypes.FILETIME()
            exit_time = wintypes.FILETIME()
            kernel_time = wintypes.FILETIME()
            user_time = wintypes.FILETIME()
            if not kernel.GetProcessTimes(
                handle,
                ctypes.byref(creation),
                ctypes.byref(exit_time),
                ctypes.byref(kernel_time),
                ctypes.byref(user_time),
            ):
                unavailable.append({"pid": pid, "reason": "process creation identity unavailable"})
                continue
            creation_id = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
            rows.append(
                {
                    "pid": pid,
                    "creationFileTime": creation_id,
                    "processIdentity": f"{pid}:{creation_id}",
                    "role": "builder-runner" if pid == runner_pid else "contained-descendant",
                    "imagePath": image,
                    "peakWorkingSetBytes": int(counters.PeakWorkingSetSize),
                    "workingSetBytesAtSample": int(counters.WorkingSetSize),
                }
            )
            concurrent_sum += int(counters.WorkingSetSize)
        finally:
            kernel.CloseHandle(handle)
    return {
        "sampledProcesses": rows,
        "unavailableProcesses": unavailable,
        "concurrentTreeWorkingSetSumBytes": concurrent_sum,
    }


def _wait_process(
    kernel: Any,
    process: int,
    deadline: float,
    sample: Any | None = None,
    containment: Any | None = None,
) -> tuple[bool, dict[str, Any]]:
    timed_out = False
    samples = []
    peak_per_process: dict[str, int] = {}
    telemetry_errors: list[dict[str, str]] = []
    peak_concurrent_sum = 0
    successful_observation_count = 0
    unavailable_process_count = 0
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            break
        wait_ms = min(250, int(remaining * 1000))
        if wait_ms <= 0:
            timed_out = True
            break
        result = kernel.WaitForSingleObject(process, wait_ms)
        if result == WAIT_OBJECT_0:
            break
        if result != WAIT_TIMEOUT:
            raise ctypes.WinError(ctypes.get_last_error())
        if containment is not None:
            containment()
        if sample is not None:
            try:
                observation = sample()
            except Exception as exc:
                observation = {
                    "sampledProcesses": [],
                    "unavailableProcesses": [],
                    "concurrentTreeWorkingSetSumBytes": None,
                }
                telemetry_errors.append({"type": type(exc).__name__, "message": str(exc)})
            samples.append(observation)
            observed_rows = observation.get("sampledProcesses", [])
            unavailable_process_count += len(observation.get("unavailableProcesses", []))
            if observed_rows:
                successful_observation_count += 1
            concurrent = observation.get("concurrentTreeWorkingSetSumBytes")
            if observed_rows and isinstance(concurrent, int):
                peak_concurrent_sum = max(peak_concurrent_sum, concurrent)
            for row in observed_rows:
                identity = row["processIdentity"]
                peak_per_process[identity] = max(
                    peak_per_process.get(identity, 0), row["peakWorkingSetBytes"]
                )
    return timed_out, {
        "sampleCount": len(samples),
        "sampleIntervalTargetSeconds": 0.25,
        "peakPerProcessPeakWorkingSetBytes": peak_per_process,
        "successfulMemoryObservationCount": successful_observation_count,
        "unavailableProcessObservationCount": unavailable_process_count,
        "peakConcurrentSampledTreeWorkingSetSumBytes": (
            peak_concurrent_sum if successful_observation_count else None
        ),
        "lastSample": samples[-1] if samples else None,
        "telemetryStatus": (
            "partial: successful samples with inaccessible process rows"
            if successful_observation_count and unavailable_process_count
            else "measured"
            if successful_observation_count
            else "unavailable: no successful contained process samples"
        ),
        "samplingErrors": telemetry_errors,
        "partialScope": bool(telemetry_errors or timed_out),
    }


def _exit_code(kernel: Any, process: int) -> int | None:
    code = wintypes.DWORD()
    if not kernel.GetExitCodeProcess(process, ctypes.byref(code)) or code.value == STILL_ACTIVE:
        return None
    return int(code.value)


def _terminate_job(kernel: Any, job: int, deadline: float, exit_code: int) -> dict[str, Any]:
    requested = bool(kernel.TerminateJobObject(job, exit_code))
    wait_budget = max(0, min(3000, int((deadline - time.monotonic()) * 1000)))
    deadline_hit = time.monotonic() >= deadline
    while not deadline_hit and _job_active_count(kernel, job) > 0:
        remaining_ms = max(0, min(200, int((deadline - time.monotonic()) * 1000)))
        if remaining_ms == 0:
            deadline_hit = True
            break
        time.sleep(min(0.05, remaining_ms / 1000.0))
    active = _job_active_count(kernel, job)
    return {
        "terminationRequested": requested,
        "activeProcessCountAfterRequest": active,
        "terminationConfirmed": active == 0,
        "waitBudgetMilliseconds": wait_budget,
        "deadlineReached": deadline_hit,
    }


def _archive_partial_output(evidence: Path, record: dict[str, Any]) -> None:
    if not EXPECTED_OUTPUT.exists():
        record["partialOutputArchive"] = {
            "status": "NO_OUTPUT_TO_ARCHIVE",
            "retainedGeneratedOutputPath": None,
            "candidateEligibleForServing": False,
        }
        return
    _assert_fixed_no_reparse(EXPECTED_OUTPUT)
    _assert_fixed_no_reparse(evidence)
    source = EXPECTED_OUTPUT.resolve(strict=True)
    target_lexical = evidence / "partial-candidate-output"
    target = target_lexical.resolve(strict=False)
    evidence_root = evidence.resolve(strict=True)
    if (
        source != EXPECTED_OUTPUT
        or not source.is_dir()
        or ROOT.resolve(strict=True) not in source.parents
    ):
        raise ValueError("generated candidate output is not the exact safe fixed directory")
    if (
        target_lexical != target
        or target.exists()
        or evidence_root not in target.parents
        or target == evidence_root
    ):
        raise FileExistsError("partial-output archive path is unsafe or already exists")
    source.replace(target)
    if source.exists() or not target.is_dir():
        raise OSError("partial candidate output move did not complete as requested")
    record["partialOutputArchive"] = {
        "status": "ARCHIVED",
        "path": str(target),
        "retainedGeneratedOutputPath": str(target),
        "candidateEligibleForServing": False,
    }


def _base_record(mode: str, command: list[str], started: float, deadline: float) -> dict[str, Any]:
    budget = deadline - started
    return {
        "schema": "teignmouth-build3-supervisor-invocation-v1",
        "issueId": ISSUE,
        "buildOrdinal": 3,
        "mode": mode,
        "status": "INVOCATION_STARTED",
        "startedUtc": datetime.now(UTC).isoformat(),
        "supervisorPid": os.getpid(),
        "monotonicStartSeconds": started,
        "absoluteDeadlineMonotonicSeconds": deadline,
        "numericalCutoffMonotonicSeconds": started + NUMERICAL_CUTOFF_SECONDS
        if mode == "build-3"
        else None,
        "wallLimitSeconds": budget,
        "numericalCutoffSeconds": min(NUMERICAL_CUTOFF_SECONDS, budget)
        if mode == "build-3"
        else None,
        "command": command,
        "candidateBuilt": False,
        "candidateEligibleForServing": False,
    }


def _mirror_record(record: dict[str, Any]) -> None:
    if RUN_LEAF.is_dir():
        _update_owned(RUN_LEAF / "external-supervisor.json", record)


def _exception_message_with_notes(exc: BaseException) -> str:
    try:
        message = str(exc)
    except BaseException:
        return "exception message unavailable"
    try:
        notes = getattr(exc, "__notes__", None)
        if isinstance(notes, list):
            bounded_notes = [note[:512] for note in notes[:4] if isinstance(note, str)]
            if bounded_notes:
                serialized_notes = json.dumps(
                    bounded_notes, ensure_ascii=True, separators=(",", ":")
                )
                return f"{message} [secondary notes: {serialized_notes}]"
    except BaseException:
        pass
    return message


def _selfcheck() -> int:
    started, deadline, handoff = _handoff("self-check")
    _assert_fixed_no_reparse(SELF_RUN, allow_missing_leaf=True)
    _assert_fixed_no_reparse(RUN_LEAF, allow_missing_leaf=True)
    _assert_fixed_no_reparse(EXPECTED_OUTPUT, allow_missing_leaf=True)
    if RUN_LEAF.exists() or EXPECTED_OUTPUT.exists():
        raise FileExistsError("self-check refuses any candidate build/evidence output")
    if SELF_RUN.exists():
        raise FileExistsError("build-3 supervisor self-check is one-shot; evidence already exists")
    SELF_RUN.mkdir(parents=True, exist_ok=False)
    record_path = SELF_RUN / "invocation.json"
    record = _base_record(
        "self-check",
        [str(PYTHON), "-B", str(Path(__file__).resolve()), "--self-check"],
        started,
        deadline,
    )
    record["parentHandoff"] = handoff
    normal_completion: dict[str, Any] = {
        "phase": "not-started",
        "identities": {"launcher": None, "interpreter": None},
        "handleOwnership": {
            "launcher": {"status": "not-created", "owned": False},
            "interpreter": {"status": "not-created", "owned": False},
        },
        "waits": {
            "launcher": {"status": "unobserved", "signaled": None, "timedOut": None},
            "interpreter": {"status": "unobserved", "signaled": None, "timedOut": None},
        },
        "exits": {
            "launcher": {"status": "unobserved", "code": None},
            "interpreter": {"status": "unobserved", "code": None},
        },
        "firstSnapshot": None,
        "latestSnapshot": None,
        "drainIterations": 0,
        "drainError": None,
        "primaryError": None,
        "evidenceCheckpointErrors": [],
    }
    record["normalHelperCompletion"] = normal_completion
    _write_exclusive(record_path, record)
    kernel = None
    job = None
    handles = []
    normal_stage_active = False

    def retain_snapshot(snapshot: dict[str, Any]) -> None:
        if normal_completion["firstSnapshot"] is None:
            normal_completion["firstSnapshot"] = snapshot
        normal_completion["latestSnapshot"] = snapshot
        record["normalHelperCompletion"] = normal_completion

    def persist_normal_checkpoint() -> None:
        try:
            if time.monotonic() >= deadline:
                raise TimeoutError("inherited deadline before normal completion checkpoint")
            _update_owned(record_path, record)
            if time.monotonic() >= deadline:
                raise TimeoutError("inherited deadline during normal completion checkpoint")
        except Exception as persistence_error:
            normal_completion["evidenceCheckpointErrors"].append(
                {
                    "phase": normal_completion.get("phase"),
                    "type": type(persistence_error).__name__,
                    "message": str(persistence_error),
                }
            )
            record["normalHelperCompletion"] = normal_completion
            raise

    def observe_normal_exit(handle: int) -> dict[str, Any]:
        code = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
            error_code = ctypes.get_last_error()
            return {
                "status": "unavailable",
                "code": None,
                "error": {"type": "WinError", "code": error_code},
            }
        if code.value == STILL_ACTIVE:
            return {"status": "still-active", "code": int(code.value), "error": None}
        return {"status": "observed", "code": int(code.value), "error": None}

    def checkpoint_normal_failure(primary: BaseException) -> None:
        normal_completion["primaryError"] = {
            "type": type(primary).__name__,
            "message": _exception_message_with_notes(primary),
            "phase": normal_completion.get("phase"),
        }
        if isinstance(normal_completion.get("finalAcceptance"), dict):
            normal_completion["finalAcceptance"]["accepted"] = False
        normal_completion["phase"] = "exception-checkpoint"
        try:
            if kernel is not None:
                snapshot = _selfcheck_job_snapshot(
                    kernel, job, deadline, "exception-checkpoint", normal_completion
                )
                retain_snapshot(snapshot)
            else:
                normal_completion["latestSnapshot"] = {
                    "phase": "exception-checkpoint",
                    "complete": False,
                    "status": "unavailable",
                    "reason": "native API initialization did not complete",
                    "observedStartMonotonicSeconds": time.monotonic(),
                    "observedEndMonotonicSeconds": time.monotonic(),
                }
            record["normalHelperCompletion"] = normal_completion
            _update_owned(record_path, record)
        except Exception as checkpoint_error:
            normal_completion["evidenceCheckpointErrors"].append(
                {"type": type(checkpoint_error).__name__, "message": str(checkpoint_error)}
            )
            record["normalHelperCompletion"] = normal_completion

    try:
        kernel, psapi = _api()
        job = _create_job(kernel)

        def authorize_helper(mode: str, launcher_pid: int, launcher_creation: int | None) -> None:
            if launcher_creation is None:
                raise RuntimeError("cannot bind self-check helper to launcher creation identity")
            launcher_identity = _process_identity(kernel, launcher_pid, deadline)
            supervisor_identity = _process_identity(kernel, os.getpid(), deadline)
            _write_exclusive(
                SELF_RUN / f"{mode}-authorization.json",
                {
                    "schema": "teignmouth-build3-selfcheck-helper-auth-v1",
                    "mode": mode,
                    "oneUse": True,
                    "nonce": handoff["nonce"],
                    "supervisorPid": supervisor_identity["pid"],
                    "supervisorCreationFileTime": supervisor_identity["creationFileTime"],
                    "supervisorImagePath": supervisor_identity["imagePath"],
                    "supervisorImageSha256": supervisor_identity["imageSha256"],
                    "launcherPid": launcher_pid,
                    "launcherCreationFileTime": launcher_creation,
                    "launcherImagePath": launcher_identity["imagePath"],
                    "launcherImageSha256": launcher_identity["imageSha256"],
                    "baseInterpreterPath": handoff["baseInterpreterPath"],
                    "baseInterpreterSha256": handoff["baseInterpreterSha256"],
                    "venvLauncherPath": handoff["launcherPath"],
                    "venvLauncherSha256": handoff["launcherSha256"],
                    "clockDomain": handoff["clockDomain"],
                    "qpcFrequency": handoff["qpcFrequency"],
                    "deadlineQpc": handoff["deadlineQpc"],
                },
            )

        normal_completion["phase"] = "launch"
        normal_stage_active = True
        normal = _launch_suspended(
            kernel,
            job,
            [str(PYTHON), "-B", str(SELFCHECK_HELPER), "--nonzero"],
            ROOT,
            SELF_RUN / "nonzero.stdout.log",
            SELF_RUN / "nonzero.stderr.log",
            deadline,
            before_resume=lambda pid, created: authorize_helper("nonzero", pid, created),
            inherit_current_console=True,
        )
        handles.append(normal["handle"])
        normal_completion["handleOwnership"]["launcher"] = {
            "status": "owned",
            "owned": True,
        }
        launcher_identity = _process_identity_from_handle(
            kernel, normal["handle"], normal["pid"], deadline
        )
        if (
            launcher_identity["creationFileTime"] != normal["createdFileTime"]
            or launcher_identity["imagePath"] != handoff["launcherPath"]
            or launcher_identity["imageSha256"] != handoff["launcherSha256"]
        ):
            raise RuntimeError(
                "nonzero launcher handle does not match its authenticated native identity"
            )
        normal_completion["identities"]["launcher"] = launcher_identity
        normal_completion["phase"] = "authenticate-interpreter"
        normal_script = _contained_interpreter_child(
            kernel,
            job,
            normal["pid"],
            handoff["baseInterpreterPath"],
            handoff["baseInterpreterSha256"],
            deadline,
            retain_handle=True,
            launcher_handle=normal["handle"],
            launcher_creation_filetime=normal["createdFileTime"],
        )
        interpreter_handle = normal_script["retainedHandle"]
        handles.append(interpreter_handle)
        if normal_script.pop("handleOwnershipTransferred") is not True:
            raise RuntimeError("normal interpreter handle ownership was not transferred")
        normal_script.pop("retainedHandle")
        normal_completion["handleOwnership"]["interpreter"] = {
            "status": "owned",
            "owned": True,
        }
        normal_completion["identities"]["interpreter"] = dict(normal_script)
        normal_completion["phase"] = "verify-start-marker"
        normal_start = _verify_helper_start(
            kernel,
            "nonzero",
            {"pid": normal["pid"], "creationFileTime": normal["createdFileTime"]},
            normal_script,
            handoff["nonce"],
            job,
            deadline,
        )
        if (
            normal_start.get("scriptPid") != normal_script["pid"]
            or normal_start.get("scriptCreationFileTime") != normal_script["creationFileTime"]
            or normal_start.get("scriptImagePath") != normal_script["imagePath"]
            or normal_start.get("scriptImageSha256") != normal_script["imageSha256"]
        ):
            raise RuntimeError(
                "nonzero helper start marker differs from retained interpreter identity"
            )
        normal_completion["helperStart"] = normal_start
        normal_completion["phase"] = "wait-launcher"
        try:
            timed_out, normal_telemetry = _wait_process(
                kernel,
                normal["handle"],
                deadline,
                lambda: _sample_job(kernel, psapi, job, normal["pid"], deadline),
                lambda: _assert_tree_contained(kernel, job, [normal["pid"]], deadline),
            )
        except Exception as wait_error:
            normal_completion["waits"]["launcher"] = {
                "status": "unavailable",
                "signaled": None,
                "timedOut": None,
                "error": {"type": type(wait_error).__name__, "message": str(wait_error)},
            }
            raise
        normal_completion["waits"]["launcher"] = {
            "status": "observed",
            "signaled": not timed_out,
            "timedOut": timed_out,
            "telemetry": normal_telemetry,
        }
        launcher_exit_observation = observe_normal_exit(normal["handle"])
        normal_exit = (
            launcher_exit_observation["code"]
            if launcher_exit_observation["status"] == "observed"
            else None
        )
        normal_completion["exits"]["launcher"] = launcher_exit_observation
        normal_completion["phase"] = "wait-interpreter"
        try:
            interpreter_timed_out, interpreter_telemetry = _wait_process(
                kernel,
                interpreter_handle,
                deadline,
                lambda: _sample_job(kernel, psapi, job, normal["pid"], deadline),
                lambda: _assert_tree_contained(kernel, job, [normal["pid"]], deadline),
            )
        except Exception as wait_error:
            normal_completion["waits"]["interpreter"] = {
                "status": "unavailable",
                "signaled": None,
                "timedOut": None,
                "error": {"type": type(wait_error).__name__, "message": str(wait_error)},
            }
            raise
        normal_completion["waits"]["interpreter"] = {
            "status": "observed",
            "signaled": not interpreter_timed_out,
            "timedOut": interpreter_timed_out,
            "telemetry": interpreter_telemetry,
        }
        interpreter_exit_observation = observe_normal_exit(interpreter_handle)
        interpreter_exit = (
            interpreter_exit_observation["code"]
            if interpreter_exit_observation["status"] == "observed"
            else None
        )
        normal_completion["exits"]["interpreter"] = interpreter_exit_observation
        normal_completion["phase"] = "drain-inner-job"
        post_wait_snapshot = _selfcheck_job_snapshot(
            kernel, job, deadline, "post-wait", normal_completion
        )
        retain_snapshot(post_wait_snapshot)
        record["normalHelperExitCode"] = normal_exit
        record["normalHelperScriptStart"] = normal_start
        record["normalHelperTimedOut"] = timed_out
        record["normalHelperTelemetry"] = normal_telemetry
        record["normalHelperCompletion"] = normal_completion
        persist_normal_checkpoint()
        if time.monotonic() >= deadline:
            raise TimeoutError("normal helper post-wait evidence reached the inherited deadline")
        if (
            timed_out
            or interpreter_timed_out
            or normal_exit != 7
            or interpreter_exit != 7
            or normal_completion["waits"]["launcher"]["signaled"] is not True
            or normal_completion["waits"]["interpreter"]["signaled"] is not True
        ):
            raise RuntimeError(
                "fixed nonzero launcher/interpreter exits did not both match expected exit 7"
            )
        if not post_wait_snapshot["complete"]:
            raise RuntimeError("post-wait inner Job snapshot is incomplete")
        if post_wait_snapshot["unexpectedPids"]:
            raise RuntimeError("post-wait inner Job snapshot contains an unexpected process")

        normal_completion["phase"] = "release-completed-handles"
        for role, handle in (("interpreter", interpreter_handle), ("launcher", normal["handle"])):
            if not kernel.CloseHandle(handle):
                normal_completion["handleOwnership"][role] = {
                    "status": "close-failed",
                    "owned": True,
                    "error": ctypes.get_last_error(),
                }
                raise ctypes.WinError(ctypes.get_last_error())
            handles.remove(handle)
            normal_completion["handleOwnership"][role] = {"status": "released", "owned": False}

        normal_completion["phase"] = "drain-inner-job"
        normal_completion["drainIterations"] = 0
        while True:
            if time.monotonic() >= deadline:
                normal_completion["drainError"] = {
                    "type": "TimeoutError",
                    "message": "deadline expired before complete empty Job accounting/census",
                }
                record["normalHelperCompletion"] = normal_completion
                persist_normal_checkpoint()
                raise TimeoutError("normal helper Job did not settle before the inherited deadline")
            drain_snapshot = _selfcheck_job_snapshot(
                kernel,
                job,
                deadline,
                "drain-inner-job",
                normal_completion,
            )
            retain_snapshot(drain_snapshot)
            normal_completion["drainIterations"] += 1
            if not drain_snapshot["complete"]:
                normal_completion["drainError"] = {
                    "type": "IncompleteSnapshot",
                    "message": "inner Job accounting or complete PID census is unavailable",
                }
                record["normalHelperCompletion"] = normal_completion
                persist_normal_checkpoint()
                raise RuntimeError("normal helper Job drain observation is incomplete")
            if drain_snapshot["unexpectedPids"]:
                normal_completion["drainError"] = {
                    "type": "UnexpectedMembers",
                    "pids": drain_snapshot["unexpectedPids"],
                }
                record["normalHelperCompletion"] = normal_completion
                persist_normal_checkpoint()
                raise RuntimeError("normal helper Job drain found unexpected members")
            before_count = drain_snapshot["accountingBefore"]["value"]
            after_count = drain_snapshot["accountingAfter"]["value"]
            census_pids = drain_snapshot["pidCensus"]["pids"]
            if before_count == 0 and after_count == 0 and census_pids == []:
                if time.monotonic() >= deadline:
                    normal_completion["drainError"] = {
                        "type": "TimeoutError",
                        "message": "deadline expired before accepting complete empty Job snapshot",
                    }
                    record["normalHelperCompletion"] = normal_completion
                    persist_normal_checkpoint()
                    raise TimeoutError("empty Job snapshot arrived at the inherited deadline")
                break
            normal_completion["unresolvedKnownPidResidue"] = census_pids
            normal_completion["latestSnapshot"] = drain_snapshot
            record["normalHelperCompletion"] = normal_completion
            if time.monotonic() >= deadline:
                normal_completion["drainError"] = {
                    "type": "TimeoutError",
                    "message": "deadline expired while known terminated PID residue remained",
                }
                persist_normal_checkpoint()
                raise TimeoutError(
                    "normal helper Job residue did not drain before the inherited deadline"
                )
            time.sleep(min(0.025, max(0.0, deadline - time.monotonic())))
        normal_completion["phase"] = "normal-complete"
        normal_completion["drainError"] = None
        normal_completion["finalAcceptance"] = {
            "launcherExitCode": normal_exit,
            "interpreterExitCode": interpreter_exit,
            "accountingBefore": before_count,
            "accountingAfter": after_count,
            "completePids": census_pids,
            "accepted": True,
        }
        record["normalHelperExitCode"] = normal_exit
        record["normalHelperScriptStart"] = normal_start
        record["normalHelperTimedOut"] = False
        record["normalHelperTelemetry"] = normal_telemetry
        record["normalInterpreterTimedOut"] = False
        record["normalInterpreterTelemetry"] = interpreter_telemetry
        record["normalHelperCompletion"] = normal_completion
        persist_normal_checkpoint()
        if time.monotonic() >= deadline:
            normal_completion["phase"] = "deadline-after-normal-complete-persist"
            normal_completion["finalAcceptance"]["accepted"] = False
            normal_completion["drainError"] = {
                "type": "TimeoutError",
                "message": "normal completion checkpoint crossed the inherited deadline",
            }
            record["normalHelperCompletion"] = normal_completion
            persist_normal_checkpoint()
            raise TimeoutError("normal helper completed after the inherited deadline")
        normal_stage_active = False
        tree = _launch_suspended(
            kernel,
            job,
            [str(PYTHON), "-B", str(SELFCHECK_HELPER), "--tree-root"],
            ROOT,
            SELF_RUN / "tree.stdout.log",
            SELF_RUN / "tree.stderr.log",
            deadline,
            before_resume=lambda pid, created: authorize_helper("tree-root", pid, created),
            inherit_current_console=True,
        )
        handles.append(tree["handle"])
        tree_script = _contained_interpreter_child(
            kernel,
            job,
            tree["pid"],
            handoff["baseInterpreterPath"],
            handoff["baseInterpreterSha256"],
            deadline,
        )
        tree_start = _verify_helper_start(
            kernel,
            "tree-root",
            {"pid": tree["pid"], "creationFileTime": tree["createdFileTime"]},
            tree_script,
            handoff["nonce"],
            job,
            deadline,
        )
        containment_deadline = deadline - 1.0
        tree_wait_started = time.monotonic()
        tree_cutoff = tree_wait_started + 3.0
        tree_boundary = {
            "inheritedDeadline": deadline,
            "cleanupReserveSeconds": 1.0,
            "containmentDeadline": containment_deadline,
            "waitStarted": tree_wait_started,
            "waitHorizon": tree_cutoff,
            "waitOutcome": "not-started",
            "periodicAttemptCount": 0,
            "periodicCompletionCount": 0,
            "lastPeriodicStart": None,
            "lastPeriodicEnd": None,
            "lastPeriodicStatus": "not-started",
            "lastPeriodicTerminalError": None,
            "lastPeriodicRowCount": None,
            "finalStart": None,
            "finalEnd": None,
            "finalStatus": "not-started",
            "finalTerminalError": None,
            "finalRowCount": None,
            "finalComplete": False,
        }
        record["treeProbeBoundary"] = tree_boundary
        tree_state = {
            "periodicAttempts": 0,
            "periodicCompletions": 0,
            "finalAttempted": False,
            "finalComplete": False,
        }
        if tree_cutoff >= containment_deadline:
            tree_boundary["waitOutcome"] = "failed"
            raise TimeoutError("insufficient inherited time for tree wait and containment reserve")

        def complete_tree_census(*, final: bool) -> dict[str, Any]:
            if final:
                if tree_state["finalAttempted"]:
                    raise RuntimeError("mandatory final tree census was attempted more than once")
                tree_state["finalAttempted"] = True
                start_key, end_key = "finalStart", "finalEnd"
                status_key = "finalStatus"
                terminal_key, rows_key = "finalTerminalError", "finalRowCount"
            else:
                if tree_state["periodicAttempts"] >= 16:
                    raise RuntimeError("periodic tree census exceeded fixed attempt bound")
                tree_state["periodicAttempts"] += 1
                tree_boundary["periodicAttemptCount"] = tree_state["periodicAttempts"]
                start_key, end_key = "lastPeriodicStart", "lastPeriodicEnd"
                status_key = "lastPeriodicStatus"
                terminal_key, rows_key = "lastPeriodicTerminalError", "lastPeriodicRowCount"
            try:
                census_started = time.monotonic()
                tree_boundary[start_key] = census_started
                tree_boundary[end_key] = None
                tree_boundary[status_key] = "running"
                if census_started >= containment_deadline:
                    tree_boundary[status_key] = "late"
                    raise TimeoutError(
                        "tree containment census started at/after containment deadline"
                    )
                proof = _assert_tree_contained(
                    kernel,
                    job,
                    [tree["pid"]],
                    containment_deadline,
                    require_complete_snapshot=True,
                )
                if (
                    not isinstance(proof, dict)
                    or proof.get("snapshotComplete") is not True
                    or proof.get("ancestryComplete") is not True
                    or proof.get("comparisonComplete") is not True
                    or type(proof.get("terminalError")) is not int
                    or proof["terminalError"] != 18
                    or type(proof.get("rowCount")) is not int
                    or not 1 <= proof["rowCount"] <= 65536
                ):
                    raise RuntimeError("strict tree census returned an invalid completion proof")
                census_ended = time.monotonic()
                tree_boundary[end_key] = census_ended
                tree_boundary[terminal_key] = proof["terminalError"]
                tree_boundary[rows_key] = proof["rowCount"]
                if census_ended >= containment_deadline:
                    tree_boundary[status_key] = "late"
                    raise TimeoutError(
                        "tree containment census returned at/after containment deadline"
                    )
                tree_boundary[status_key] = "complete"
                if final:
                    tree_state["finalComplete"] = True
                    tree_boundary["finalComplete"] = True
                else:
                    tree_state["periodicCompletions"] += 1
                    tree_boundary["periodicCompletionCount"] = tree_state["periodicCompletions"]
                return proof
            except BaseException:
                try:
                    if tree_boundary.get(status_key) != "late":
                        tree_boundary[status_key] = "failed"
                except BaseException:
                    pass
                raise

        try:
            tree_boundary["waitOutcome"] = "waiting"
            tree_timeout, tree_telemetry = _wait_process(
                kernel,
                tree["handle"],
                tree_cutoff,
                lambda: _sample_job(kernel, psapi, job, tree["pid"], containment_deadline),
                lambda: complete_tree_census(final=False),
            )
        except BaseException:
            try:
                tree_boundary["waitOutcome"] = "failed"
            except BaseException:
                pass
            raise
        if not tree_timeout:
            try:
                tree_boundary["waitOutcome"] = "early-exit"
            except BaseException:
                pass
            raise RuntimeError("fixed contained child/grandchild probe exited before timeout")
        try:
            tree_horizon_observed = time.monotonic()
        except BaseException:
            try:
                tree_boundary["waitOutcome"] = "unavailable"
            except BaseException:
                pass
            raise
        if tree_horizon_observed < tree_cutoff:
            tree_boundary["waitOutcome"] = "early-exit"
            raise RuntimeError("tree helper wait returned before expected timeout horizon")
        if tree_horizon_observed >= containment_deadline:
            tree_boundary["waitOutcome"] = "late"
            raise TimeoutError("tree helper wait crossed containment deadline")
        tree_boundary["waitOutcome"] = "expected-horizon"
        complete_tree_census(final=True)
        if not tree_state["finalComplete"]:
            raise RuntimeError("mandatory final tree census did not complete")
        root_marker_path = SELF_RUN / "tree-root-started.json"
        child_marker_path = SELF_RUN / "tree-child-started.json"
        marker_deadline = min(deadline, time.monotonic() + 1.0)
        while time.monotonic() < marker_deadline and not child_marker_path.is_file():
            time.sleep(min(0.025, max(0.0, marker_deadline - time.monotonic())))
        if not root_marker_path.is_file() or not child_marker_path.is_file():
            raise RuntimeError("self-check did not prove the intended child process started")
        root_marker = json.loads(root_marker_path.read_text(encoding="utf-8"))
        child_marker = json.loads(child_marker_path.read_text(encoding="utf-8"))
        if (
            root_marker.get("pid") != tree_script["pid"]
            or root_marker.get("parentPid") != tree["pid"]
            or root_marker.get("creationFileTime") != tree_script["creationFileTime"]
            or child_marker.get("launcherPid") != root_marker.get("childLauncherPid")
            or child_marker.get("launcherCreationFileTime")
            != root_marker.get("childLauncherCreationFileTime")
            or child_marker.get("creationFileTime", 0) <= 0
            or root_marker.get("nonce") != handoff["nonce"]
            or tree_start.get("scriptPid") != tree_script["pid"]
        ):
            raise RuntimeError("self-check process ancestry/creation identity did not match")
        child_identity = _process_identity(kernel, int(child_marker["pid"]), deadline)
        child_launcher_identity = _process_identity(
            kernel, int(child_marker["launcherPid"]), deadline
        )
        if (
            child_identity["creationFileTime"] != child_marker["creationFileTime"]
            or child_identity["imagePath"] != handoff["baseInterpreterPath"]
            or child_identity["imageSha256"] != handoff["baseInterpreterSha256"]
            or _parent_pid(kernel, int(child_marker["pid"]), deadline)
            != int(child_marker["launcherPid"])
            or child_launcher_identity["creationFileTime"]
            != child_marker["launcherCreationFileTime"]
            or child_marker.get("launcherImagePath") != child_launcher_identity["imagePath"]
            or child_marker.get("launcherImageSha256") != child_launcher_identity["imageSha256"]
            or child_launcher_identity["imagePath"] != handoff["launcherPath"]
            or child_launcher_identity["imageSha256"] != handoff["launcherSha256"]
            or _parent_pid(kernel, int(child_marker["launcherPid"]), deadline) != tree_script["pid"]
        ):
            raise RuntimeError("self-check child launcher/interpreter native chain mismatch")
        child_handle = kernel.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_QUERY_INFORMATION,
            False,
            int(child_marker["pid"]),
        )
        if not child_handle:
            raise RuntimeError("cannot observe self-check child process membership")
        try:
            child_in_job = wintypes.BOOL()
            if (
                not kernel.IsProcessInJob(child_handle, job, ctypes.byref(child_in_job))
                or not child_in_job.value
            ):
                raise RuntimeError("self-check child is outside exact inner Job membership")
        finally:
            kernel.CloseHandle(child_handle)
        child_launcher_handle = kernel.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_QUERY_INFORMATION,
            False,
            int(child_marker["launcherPid"]),
        )
        if not child_launcher_handle:
            raise RuntimeError("cannot observe child venv launcher membership")
        try:
            launcher_in_job = wintypes.BOOL()
            if (
                not kernel.IsProcessInJob(child_launcher_handle, job, ctypes.byref(launcher_in_job))
                or not launcher_in_job.value
            ):
                raise RuntimeError("child venv launcher is outside exact inner Job membership")
        finally:
            kernel.CloseHandle(child_launcher_handle)
        active_before_termination = _job_active_count(kernel, job)
        if active_before_termination < 2:
            raise RuntimeError("self-check did not observe both contained root and child")
        termination = _terminate_job(kernel, job, deadline, 124)
        if not termination.get("terminationConfirmed"):
            raise RuntimeError("self-check descendant termination was not confirmed")
        if _job_active_count(kernel, job) != 0:
            raise RuntimeError("self-check Job Object still has active processes")
        kernel.CloseHandle(job)
        job = None
        remaining_ms = max(0, min(1500, int((deadline - time.monotonic()) * 1000)))
        tree_wait = kernel.WaitForSingleObject(tree["handle"], remaining_ms)
        tree_exit = _exit_code(kernel, tree["handle"])
        if tree_wait != WAIT_OBJECT_0 or tree_exit is None or time.monotonic() >= deadline:
            raise RuntimeError("self-check root exit/deadline could not be confirmed")
        record.update(
            {
                "status": "PASS_NONNUMERICAL_CONTAINMENT_SELFCHECK",
                "normalHelperExitCode": normal_exit,
                "normalHelperScriptStart": normal_start,
                "normalHelperTimedOut": False,
                "normalHelperTelemetry": normal_telemetry,
                "treeProbeTimedOut": tree_timeout,
                "treeRootExitCodeAfterTermination": tree_exit,
                "treeRootIdentity": root_marker,
                "treeChildIdentity": child_marker,
                "treeHelperScriptStart": tree_start,
                "activeProcessesBeforeTermination": active_before_termination,
                "activeProcessesAfterTermination": 0,
                "termination": termination,
                "candidateBuilt": False,
                "gisGeometryLoaded": False,
                "build3RunLeafCreated": False,
                "candidateOutputCreated": False,
                "elapsedWallSeconds": time.monotonic() - started,
                "modeBudgetSeconds": SELF_CHECK_SECONDS,
                "outerCommandExitCode": 0,
            }
        )
        if RUN_LEAF.exists() or EXPECTED_OUTPUT.exists():
            raise RuntimeError("nonnumerical self-check unexpectedly created candidate output")
        _update_owned(record_path, record)
        return 0
    except Exception as exc:
        if normal_stage_active:
            checkpoint_normal_failure(exc)
        record.update(
            {
                "status": "BLOCKED_SELFCHECK",
                "error": {
                    "type": type(exc).__name__,
                    "message": _exception_message_with_notes(exc),
                },
                "elapsedWallSeconds": time.monotonic() - started,
                "modeBudgetSeconds": SELF_CHECK_SECONDS,
                "outerCommandExitCode": 2,
            }
        )
        try:
            _update_owned(record_path, record)
        except Exception as persistence_error:
            try:
                secondary = {
                    "phase": "outer-exception-record",
                    "type": type(persistence_error).__name__,
                    "message": str(persistence_error),
                }
                record["exceptionPersistenceError"] = secondary
                completion = record.get("normalHelperCompletion")
                if isinstance(completion, dict):
                    completion.setdefault("evidenceCheckpointErrors", []).append(secondary)
            except Exception:
                pass
        raise
    finally:
        if job is not None and kernel is not None:
            try:
                record["finallyTermination"] = _terminate_job(kernel, job, deadline, 2)
            except Exception as cleanup_error:
                record["finallyTerminationError"] = {
                    "type": type(cleanup_error).__name__,
                    "message": str(cleanup_error),
                }
            finally:
                kernel.CloseHandle(job)
                job = None
        for handle in handles:
            try:
                kernel.CloseHandle(handle)
            except Exception:
                pass
        try:
            _update_owned(record_path, record)
        except Exception:
            pass


def _preflight_only() -> int:
    started, deadline, handoff = _handoff("runtime-preflight-only")
    _assert_fixed_no_reparse(PREFLIGHT_SELF_RUN, allow_missing_leaf=True)
    _assert_fixed_no_reparse(RUN_LEAF, allow_missing_leaf=True)
    _assert_fixed_no_reparse(EXPECTED_OUTPUT, allow_missing_leaf=True)
    if RUN_LEAF.exists() or EXPECTED_OUTPUT.exists():
        raise FileExistsError("runtime preflight refuses candidate build/output paths")
    authorization_path = BUILD3 / "runtime-preflight-authorization.json"
    consumed_authorization = BUILD3 / "runtime-preflight-authorization.consumed.json"
    if not authorization_path.is_file() or consumed_authorization.exists():
        raise FileNotFoundError("separate runtime-preflight disposition is required")
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    authorization_sha = _sha256(authorization_path, deadline)
    purpose = handoff.get("standalonePurpose")
    if (
        authorization.get("schema") != "teignmouth-build3-runtime-preflight-authorization-v2"
        or authorization.get("authorized") is not True
        or authorization.get("oneShot") is not True
        or authorization.get("purpose") != purpose
        or purpose
        not in (
            "collect-unreserved-runtime-identity",
            "verify-unreserved-runtime-identity",
        )
    ):
        raise ValueError("runtime-preflight authorization record does not match the fixed schema")
    os.rename(authorization_path, consumed_authorization)
    if PREFLIGHT_SELF_RUN.exists():
        raise FileExistsError("standalone runtime preflight is one-shot")
    PREFLIGHT_SELF_RUN.mkdir(parents=True, exist_ok=False)
    record_path = PREFLIGHT_SELF_RUN / "invocation.json"
    command = [str(PYTHON), "-B", str(PREFLIGHT_SCRIPT), "--mode", "standalone"]
    record = _base_record("runtime-preflight-only", command, started, deadline)
    record["parentHandoff"] = handoff
    record["coordinatorAuthorizationSha256"] = authorization_sha
    record["standalonePurpose"] = purpose
    _write_exclusive(record_path, record)
    frozen_before: dict[str, Any] | None = None
    kernel = None
    job = None
    process = None
    try:
        if purpose == "verify-unreserved-runtime-identity":
            repository_before = _verify_repository(
                INPUT_MANIFEST,
                handoff.get("inputManifestSha256"),
                deadline,
                standalone=True,
            )
            external_before = _verify_external(
                EXTERNAL_MANIFEST,
                handoff.get("externalRuntimeManifestSha256"),
                deadline,
            )
            identity_before = _verify_runtime_identity_record(
                RUNTIME_IDENTITY,
                str(handoff.get("runtimeIdentitySha256")),
                str(handoff.get("externalRuntimeManifestSha256")),
                deadline,
            )
            if (
                not repository_before.get("passes")
                or repository_before.get("checkedFileCount")
                != repository_before.get("declaredFileCount")
                or not external_before.get("passes")
                or external_before.get("checkedFileCount")
                != external_before.get("declaredFileCount")
                or not identity_before.get("passes")
            ):
                raise RuntimeError("standalone frozen closure failed before preflight launch")
            frozen_before = {
                "repository": repository_before,
                "external": external_before,
                "runtimeIdentity": identity_before,
            }
            profile_before = _verify_finite_startup_profile(
                deadline,
                stage="standalone-before-preflight",
                expected_environment=identity_before["identity"].get("environment", {}),
                expected_manifest_sha=str(handoff.get("inputManifestSha256")),
                expected_external_sha=str(handoff.get("externalRuntimeManifestSha256")),
                expected_identity_sha=str(handoff.get("runtimeIdentitySha256")),
            )
            record["finiteStartupProfileBeforeLaunch"] = profile_before
            record["frozenClosureBeforeLaunch"] = frozen_before
            _update_owned(record_path, record)
        kernel, _psapi = _api()
        job = _create_job(kernel)

        dispatch_auth_path = PREFLIGHT_SELF_RUN / "parent-preflight-authorization.json"

        def authorize_standalone(worker_pid: int, worker_creation: int | None) -> None:
            if worker_creation is None:
                raise RuntimeError("cannot bind standalone preflight to worker creation identity")
            supervisor_identity = _process_identity(kernel, os.getpid(), deadline)
            launcher_identity = _process_identity(kernel, worker_pid, deadline)
            _write_exclusive(
                dispatch_auth_path,
                {
                    "schema": "teignmouth-build3-parent-preflight-auth-v1",
                    "mode": "standalone",
                    "oneUse": True,
                    "dispatchNonce": handoff["nonce"],
                    "supervisorPid": supervisor_identity["pid"],
                    "supervisorCreationFileTime": supervisor_identity["creationFileTime"],
                    "supervisorImagePath": supervisor_identity["imagePath"],
                    "supervisorImageSha256": supervisor_identity["imageSha256"],
                    "launcherPid": worker_pid,
                    "launcherCreationFileTime": worker_creation,
                    "launcherImagePath": launcher_identity["imagePath"],
                    "launcherImageSha256": launcher_identity["imageSha256"],
                    "baseInterpreterPath": handoff["baseInterpreterPath"],
                    "baseInterpreterSha256": handoff["baseInterpreterSha256"],
                    "clockDomain": handoff["clockDomain"],
                    "qpcFrequency": handoff["qpcFrequency"],
                    "deadlineQpc": handoff["deadlineQpc"],
                    "purpose": purpose,
                    "inputManifestSha256": handoff.get("inputManifestSha256"),
                    "externalRuntimeManifestSha256": handoff.get("externalRuntimeManifestSha256"),
                    "runtimeIdentitySha256": handoff.get("runtimeIdentitySha256"),
                },
            )

        process = _launch_suspended(
            kernel,
            job,
            command,
            ROOT,
            PREFLIGHT_SELF_RUN / "preflight.stdout.log",
            PREFLIGHT_SELF_RUN / "preflight.stderr.log",
            deadline,
            before_resume=authorize_standalone,
        )
        helper_script_identity = _contained_interpreter_child(
            kernel,
            job,
            process["pid"],
            handoff["baseInterpreterPath"],
            handoff["baseInterpreterSha256"],
            deadline,
        )
        _verify_helper_start(
            kernel,
            "standalone",
            {"pid": process["pid"], "creationFileTime": process["createdFileTime"]},
            helper_script_identity,
            handoff["nonce"],
            job,
            deadline,
        )
        _assert_tree_contained(kernel, job, [process["pid"]], deadline)
        timed_out, telemetry = _wait_process(
            kernel,
            process["handle"],
            deadline,
            containment=lambda: _assert_tree_contained(kernel, job, [process["pid"]], deadline),
        )
        if timed_out:
            termination = _terminate_job(kernel, job, deadline, 124)
            kernel.CloseHandle(job)
            job = None
        else:
            termination = {"terminationConfirmed": _job_active_count(kernel, job) == 0}
        if not termination.get("terminationConfirmed"):
            raise RuntimeError("standalone preflight process tree was not confirmed terminated")
        child_exit = _exit_code(kernel, process["handle"])
        record["preflightExitObservedAfterTermination"] = child_exit is not None
        result_path = PREFLIGHT_SELF_RUN / "runtime-preflight-result.json"
        result = (
            json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else None
        )
        frozen_after = None
        frozen_after_passes = purpose != "verify-unreserved-runtime-identity"
        if frozen_before is not None:
            profile_after = _verify_finite_startup_profile(
                deadline,
                stage="standalone-after-preflight-termination",
                expected_environment=identity_before["identity"].get("environment", {}),
                expected_manifest_sha=str(handoff.get("inputManifestSha256")),
                expected_external_sha=str(handoff.get("externalRuntimeManifestSha256")),
                expected_identity_sha=str(handoff.get("runtimeIdentitySha256")),
            )
            record["finiteStartupProfileAfterTermination"] = profile_after
            repository_after = _verify_repository(
                INPUT_MANIFEST,
                handoff.get("inputManifestSha256"),
                deadline,
                standalone=True,
            )
            external_after = _verify_external(
                EXTERNAL_MANIFEST,
                handoff.get("externalRuntimeManifestSha256"),
                deadline,
            )
            identity_after = _verify_runtime_identity_record(
                RUNTIME_IDENTITY,
                str(handoff.get("runtimeIdentitySha256")),
                str(handoff.get("externalRuntimeManifestSha256")),
                deadline,
            )
            frozen_after = {
                "repository": repository_after,
                "external": external_after,
                "runtimeIdentity": identity_after,
            }
            frozen_after_passes = (
                repository_after.get("passes") is True
                and repository_after.get("checkedFileCount")
                == repository_after.get("declaredFileCount")
                and repository_before.get("manifestSha256")
                == repository_after.get("manifestSha256")
                and repository_before.get("checkedFileCount")
                == repository_after.get("checkedFileCount")
                and external_after.get("passes") is True
                and external_after.get("checkedFileCount")
                == external_after.get("declaredFileCount")
                and external_before.get("manifestSha256") == external_after.get("manifestSha256")
                and external_before.get("checkedFileCount")
                == external_after.get("checkedFileCount")
                and identity_after.get("passes") is True
                and identity_before.get("sha256") == identity_after.get("sha256")
            )
            record["frozenClosureAfterTermination"] = frozen_after
            record["frozenClosurePostcheckPassed"] = frozen_after_passes
        passed = (
            not timed_out
            and child_exit == 0
            and child_exit is not None
            and result
            and result.get("status") == "PASS_RUNTIME_IDENTITY_ONLY"
            and result.get("dispatchNonce") == handoff["nonce"]
            and result.get("dispatchAuthorizationPassed") is True
            and result.get("runtimeIdentityMatches") is True
            and result.get("inputManifestSha256") == handoff.get("inputManifestSha256")
            and result.get("externalRuntimeManifestSha256")
            == handoff.get("externalRuntimeManifestSha256")
            and result.get("runtimeIdentitySha256") == handoff.get("runtimeIdentitySha256")
            and result.get("repositoryBindingCount", 0) > 0
            and result.get("externalRuntimeBindingCount", 0) > 0
            and result.get("loadedModuleFileCount", 0) > 0
            and result.get("candidateBuildExecuted") is False
            and result.get("gisGeometryLoaded") is False
            and result.get("servingEligible") is False
            and termination.get("terminationConfirmed") is True
            and frozen_after_passes
            and record.get("finiteStartupProfileBeforeLaunch", {}).get("passes") is True
            and record.get("finiteStartupProfileAfterTermination", {}).get("passes") is True
            and time.monotonic() < deadline
        )
        collection_only = (
            not timed_out
            and child_exit == 2
            and result
            and result.get("status") == "RUNTIME_IDENTITY_COLLECTION_ONLY"
            and result.get("purpose") == purpose
            and result.get("dispatchNonce") == handoff["nonce"]
            and result.get("dispatchAuthorizationPassed") is True
            and termination.get("terminationConfirmed") is True
            and time.monotonic() < deadline
        )
        if RUN_LEAF.exists() or EXPECTED_OUTPUT.exists():
            passed = False
            record["unexpectedCandidateOutput"] = True
        record.update(
            {
                "status": (
                    "PASS_RUNTIME_IDENTITY_ONLY"
                    if passed
                    else "RUNTIME_IDENTITY_COLLECTION_ONLY"
                    if collection_only
                    else "BLOCKED_RUNTIME_PREFLIGHT"
                ),
                "preflightRunnerExitCode": child_exit,
                "preflightTimedOut": timed_out,
                "preflightResultStatus": result.get("status") if result else "MISSING",
                "resourceTelemetry": telemetry,
                "frozenClosurePostcheckPassed": frozen_after_passes,
                "frozenClosureAfterTermination": frozen_after,
                "termination": termination,
                "elapsedWallSeconds": time.monotonic() - started,
                "modeBudgetSeconds": STANDALONE_PREFLIGHT_SECONDS,
                "outerCommandExitCode": 0 if passed else 2,
                "build3RunLeafCreated": False,
                "candidateOutputCreated": False,
            }
        )
        _update_owned(record_path, record)
        return 0 if passed else 2
    except Exception as exc:
        record.update(
            {
                "status": "BLOCKED_RUNTIME_PREFLIGHT",
                "error": {"type": type(exc).__name__, "message": str(exc)},
                "modeBudgetSeconds": STANDALONE_PREFLIGHT_SECONDS,
                "elapsedWallSeconds": time.monotonic() - started,
                "outerCommandExitCode": 2,
            }
        )
        _update_owned(record_path, record)
        raise
    finally:
        if job is not None and kernel is not None:
            try:
                if _job_active_count(kernel, job) > 0:
                    _terminate_job(kernel, job, deadline, 2)
            finally:
                kernel.CloseHandle(job)
        if process is not None and kernel is not None:
            kernel.CloseHandle(process["handle"])


def _run_build() -> int:
    started, deadline, handoff = _handoff("build-3")
    numerical_cutoff = min(started + NUMERICAL_CUTOFF_SECONDS, deadline)
    _assert_fixed_no_reparse(BUILD3)
    _assert_fixed_no_reparse(RUN_LEAF, allow_missing_leaf=True)
    _assert_fixed_no_reparse(EXPECTED_OUTPUT, allow_missing_leaf=True)
    command = [
        str(PYTHON),
        "-B",
        str(BUILDER_SCRIPT),
        "--input-manifest",
        str(INPUT_MANIFEST),
        "--attempt-ledger",
        str(LEDGER),
        "--build-ordinal",
        "3",
        "--evidence-dir",
        str(RUN_LEAF),
    ]
    if INVOCATION.exists() or RUN_LEAF.exists() or EXPECTED_OUTPUT.exists():
        raise FileExistsError(
            "build-3 invocation, run leaf or candidate output already exists; refusing retry"
        )
    if PREFLIGHT_RESULT.exists():
        raise FileExistsError("build-3 runtime-preflight result exists; refusing overwrite/retry")
    record = _base_record("build-3", command, started, deadline)
    record["inputManifestPath"] = str(INPUT_MANIFEST)
    record["externalRuntimeManifestPath"] = str(EXTERNAL_MANIFEST)
    record["parentHandoff"] = handoff
    _write_exclusive(INVOCATION, record)
    invocation_manifest_sha = None
    invocation_external_sha = None
    before_repo = before_external = None
    job = None
    process_handles: list[dict[str, Any]] = []
    kernel = psapi = None
    timed_out = False
    builder_launched = False
    try:
        if not PYTHON.is_file() or not BUILDER_SCRIPT.is_file() or not INPUT_MANIFEST.is_file():
            raise FileNotFoundError("fixed venv, builder or build-3 input manifest is unavailable")
        if (
            not LEDGER_SNAPSHOT.is_file()
            or not EXTERNAL_MANIFEST.is_file()
            or not RUNTIME_IDENTITY.is_file()
        ):
            raise FileNotFoundError("fixed reserved ledger/runtime identity closure is incomplete")
        before_repo = _verify_repository(INPUT_MANIFEST, handoff["inputManifestSha256"], deadline)
        invocation_manifest_sha = before_repo["manifestSha256"]
        before_external = _verify_external(
            EXTERNAL_MANIFEST, handoff["externalRuntimeManifestSha256"], deadline
        )
        invocation_external_sha = before_external["manifestSha256"]
        record.update(
            {
                "inputManifestSha256": invocation_manifest_sha,
                "externalRuntimeManifestSha256": invocation_external_sha,
                "preRunRepositoryPreservation": before_repo,
                "preRunExternalPreservation": before_external,
            }
        )
        if not before_repo["passes"] or not before_external["passes"]:
            raise ValueError("pre-run protected-input/runtime preservation verification failed")
        identity_for_profile = _verify_runtime_identity_record(
            RUNTIME_IDENTITY,
            str(handoff["runtimeIdentitySha256"]),
            str(handoff["externalRuntimeManifestSha256"]),
            deadline,
        )
        profile_before = _verify_finite_startup_profile(
            deadline,
            stage="build-before-preflight",
            expected_environment=identity_for_profile["identity"].get("environment", {}),
            expected_manifest_sha=str(handoff["inputManifestSha256"]),
            expected_external_sha=str(handoff["externalRuntimeManifestSha256"]),
            expected_identity_sha=str(handoff["runtimeIdentitySha256"]),
        )
        record["finiteStartupProfileBeforePreflight"] = profile_before
        record["ledgerReservation"] = _fixed_ledger_preflight(
            handoff["reservedLedgerSnapshotSha256"], deadline
        )
        if _sha256(PYTHON, deadline) != next(
            (
                item["sha256"]
                for item in json.loads(INPUT_MANIFEST.read_text(encoding="utf-8")).get("files", [])
                if item.get("path") == "pipeline/.venv/Scripts/python.exe"
            ),
            None,
        ):
            raise ValueError("fixed venv interpreter differs from input manifest binding")
        if RUN_LEAF.exists() or EXPECTED_OUTPUT.exists() or PREFLIGHT_RESULT.exists():
            raise FileExistsError("fixed run, output or preflight-result path is no longer fresh")
        if time.monotonic() >= numerical_cutoff:
            raise TimeoutError("identity work consumed the numerical launch window")
        kernel, psapi = _api()
        job = _create_job(kernel)
        preflight_cmd = [str(PYTHON), "-B", str(PREFLIGHT_SCRIPT), "--mode", "build-dispatch"]
        internal_auth_path = BUILD3 / "internal-preflight-authorization.json"

        def authorize_preflight(worker_pid: int, worker_creation: int | None) -> None:
            if worker_creation is None:
                raise RuntimeError("cannot bind internal authorization to worker creation identity")
            supervisor_identity = _process_identity(kernel, os.getpid(), numerical_cutoff)
            launcher_identity = _process_identity(kernel, worker_pid, numerical_cutoff)
            _write_exclusive(
                internal_auth_path,
                {
                    "schema": "teignmouth-build3-internal-preflight-auth-v1",
                    "mode": "build-dispatch",
                    "oneUse": True,
                    "dispatchNonce": handoff["nonce"],
                    "supervisorPid": supervisor_identity["pid"],
                    "supervisorCreationFileTime": supervisor_identity["creationFileTime"],
                    "supervisorImagePath": supervisor_identity["imagePath"],
                    "supervisorImageSha256": supervisor_identity["imageSha256"],
                    "launcherPid": worker_pid,
                    "launcherCreationFileTime": worker_creation,
                    "launcherImagePath": launcher_identity["imagePath"],
                    "launcherImageSha256": launcher_identity["imageSha256"],
                    "baseInterpreterPath": handoff["baseInterpreterPath"],
                    "baseInterpreterSha256": handoff["baseInterpreterSha256"],
                    "clockDomain": handoff["clockDomain"],
                    "qpcFrequency": handoff["qpcFrequency"],
                    "deadlineQpc": handoff["deadlineQpc"],
                    "inputManifestSha256": invocation_manifest_sha,
                    "externalRuntimeManifestSha256": invocation_external_sha,
                    "runtimeIdentitySha256": handoff["runtimeIdentitySha256"],
                    "ledgerSnapshotSha256": handoff["reservedLedgerSnapshotSha256"],
                },
            )

        preflight = _launch_suspended(
            kernel,
            job,
            preflight_cmd,
            ROOT,
            BUILD3 / "runtime-preflight.stdout.log",
            BUILD3 / "runtime-preflight.stderr.log",
            numerical_cutoff,
            before_resume=authorize_preflight,
        )
        preflight_script_identity = _contained_interpreter_child(
            kernel,
            job,
            preflight["pid"],
            handoff["baseInterpreterPath"],
            handoff["baseInterpreterSha256"],
            numerical_cutoff,
        )
        preflight_marker = _verify_helper_start(
            kernel,
            "build-dispatch",
            {"pid": preflight["pid"], "creationFileTime": preflight["createdFileTime"]},
            preflight_script_identity,
            handoff["nonce"],
            job,
            numerical_cutoff,
        )
        _assert_tree_contained(kernel, job, [preflight["pid"]], numerical_cutoff)
        record["runtimePreflightScriptStartIdentity"] = preflight_marker
        process_handles.append({"role": "runtime-preflight", **preflight})
        record["runtimePreflightProcess"] = {
            "pid": preflight["pid"],
            "creationFileTime": preflight["createdFileTime"],
            "executable": str(PYTHON),
            "role": "identity-only-runtime-preflight",
        }
        _update_owned(INVOCATION, record)
        preflight_timeout, preflight_telemetry = _wait_process(
            kernel,
            preflight["handle"],
            numerical_cutoff,
            containment=lambda: _assert_tree_contained(
                kernel, job, [preflight["pid"]], numerical_cutoff
            ),
        )
        preflight_exit = _exit_code(kernel, preflight["handle"])
        record["runtimePreflightExitCode"] = preflight_exit
        record["runtimePreflightTimedOut"] = preflight_timeout
        record["runtimePreflightResourceTelemetry"] = preflight_telemetry
        preflight_result = (
            json.loads(PREFLIGHT_RESULT.read_text(encoding="utf-8"))
            if PREFLIGHT_RESULT.is_file()
            else None
        )
        record["runtimePreflightResultStatus"] = (
            preflight_result.get("status") if preflight_result else "MISSING"
        )
        if (
            preflight_timeout
            or preflight_exit != 0
            or not preflight_result
            or preflight_result.get("status") != "PASS_RUNTIME_IDENTITY_ONLY"
            or preflight_result.get("dispatchNonce") != handoff["nonce"]
            or preflight_result.get("dispatchAuthorizationPassed") is not True
        ):
            raise RuntimeError("identity-only runtime preflight did not pass")
        if _job_active_count(kernel, job) != 0:
            raise RuntimeError("runtime preflight left descendants active in its Job Object")
        profile_after_preflight = _verify_finite_startup_profile(
            numerical_cutoff,
            stage="build-after-preflight",
            expected_environment=identity_for_profile["identity"].get("environment", {}),
            expected_manifest_sha=str(handoff["inputManifestSha256"]),
            expected_external_sha=str(handoff["externalRuntimeManifestSha256"]),
            expected_identity_sha=str(handoff["runtimeIdentitySha256"]),
        )
        record["finiteStartupProfileAfterPreflight"] = profile_after_preflight
        record["runtimePreflightExitObservedAfterTermination"] = preflight_exit is not None
        if time.monotonic() >= numerical_cutoff:
            raise TimeoutError("runtime preflight consumed the numerical launch window")
        if not profile_before.get("passes") or not profile_after_preflight.get("passes"):
            raise RuntimeError("finite startup profile did not remain complete before builder")
        repo_before_dispatch = _verify_repository(
            INPUT_MANIFEST, invocation_manifest_sha, numerical_cutoff
        )
        ext_before_dispatch = _verify_external(
            EXTERNAL_MANIFEST, invocation_external_sha, numerical_cutoff
        )
        if not repo_before_dispatch["passes"] or not ext_before_dispatch["passes"]:
            raise ValueError("protected inputs changed before numerical dispatch")
        ledger_status = _fixed_ledger_preflight(
            handoff["reservedLedgerSnapshotSha256"], numerical_cutoff
        )
        record["ledgerReservationBeforeNumericalDispatch"] = ledger_status
        if RUN_LEAF.exists() or EXPECTED_OUTPUT.exists():
            raise FileExistsError("run leaf or candidate output appeared before dispatch")
        record["status"] = "NUMERICAL_RUNNER_STARTING"
        _update_owned(INVOCATION, record)
        process = _launch_suspended(
            kernel,
            job,
            command,
            ROOT,
            BUILD3 / "external-runner.stdout.log",
            BUILD3 / "external-runner.stderr.log",
            numerical_cutoff,
        )
        builder_launched = True
        process_handles.append({"role": "candidate-builder-runner", **process})
        record["builderRunnerProcess"] = {
            "pid": process["pid"],
            "creationFileTime": process["createdFileTime"],
            "executable": str(PYTHON),
            "role": "candidate-builder-runner",
        }
        record["status"] = "NUMERICAL_RUNNER_ACTIVE"
        _update_owned(INVOCATION, record)
        builder_script_identity = _contained_interpreter_child(
            kernel,
            job,
            process["pid"],
            handoff["baseInterpreterPath"],
            handoff["baseInterpreterSha256"],
            numerical_cutoff,
        )
        record["builderRunnerProcess"] = {
            "pid": process["pid"],
            "creationFileTime": process["createdFileTime"],
            "interpreterPid": builder_script_identity["pid"],
            "interpreterCreationFileTime": builder_script_identity["creationFileTime"],
            "interpreterImagePath": builder_script_identity["imagePath"],
            "interpreterImageSha256": builder_script_identity["imageSha256"],
            "executable": str(PYTHON),
            "role": "candidate-builder-runner",
        }
        record["status"] = "NUMERICAL_RUNNER_ACTIVE"
        _update_owned(INVOCATION, record)

        def sample() -> dict[str, Any]:
            return _sample_job(kernel, psapi, job, process["pid"], numerical_cutoff)

        timed_out, resource = _wait_process(
            kernel,
            process["handle"],
            numerical_cutoff,
            sample,
            lambda: _assert_tree_contained(kernel, job, [process["pid"]], numerical_cutoff),
        )
        record["resourceTelemetry"] = resource
        record["numericalCutoffReached"] = timed_out
        if timed_out:
            record["status"] = "STOP_NUMERICAL_CUTOFF"
            _update_owned(INVOCATION, record)
            record["termination"] = _terminate_job(kernel, job, deadline, 124)
        active = _job_active_count(kernel, job)
        if active > 0:
            record["status"] = "STOP_DESCENDANTS_REMAINED"
            record["termination"] = _terminate_job(kernel, job, deadline, 2)
        if _job_active_count(kernel, job) > 0:
            raise RuntimeError(
                "Job Object still has active processes; refusing archive/preservation PASS"
            )
        record["terminationConfirmed"] = True
        runner_exit = _exit_code(kernel, process["handle"])
        record["builderRunnerExitCodeAfterTermination"] = runner_exit
        record["builderRunnerExitObservedAfterTermination"] = runner_exit is not None
        job_active_before_close = _job_active_count(kernel, job)
        kernel.CloseHandle(job)
        job = None
        record["jobClosedAfterActiveCountZero"] = job_active_before_close == 0
        logical_report = None
        worker_result = None
        if RUN_LEAF.is_dir():
            for name, target in (
                ("build-report.json", "builderLogicalReport"),
                ("worker-process-result.json", "numericalWorkerResult"),
            ):
                path = RUN_LEAF / name
                if path.is_file():
                    try:
                        payload = json.loads(path.read_text(encoding="utf-8"))
                        if target == "builderLogicalReport":
                            logical_report = payload
                        else:
                            worker_result = payload
                    except (OSError, json.JSONDecodeError) as exc:
                        record[f"{target}ReadError"] = f"{type(exc).__name__}: {exc}"
        record["builderLogicalWorkerStatus"] = (
            worker_result.get("logicalWorkerStatus")
            if worker_result
            else logical_report.get("logicalWorkerStatus")
            if logical_report
            else "UNAVAILABLE"
        )
        record["builderLogicalWorkerExitCode"] = (
            worker_result.get("logicalWorkerReturnCode")
            if worker_result
            else logical_report.get("logicalWorkerReturnCode")
            if logical_report
            else None
        )
        record["numericalWorkerActualExitCode"] = (
            logical_report.get("actualChildExitCode") if logical_report else None
        )
        record["runnerChosenExitCode"] = (
            logical_report.get("runnerChosenExitCode") if logical_report else None
        )
        if record.get("status") not in ("STOP_NUMERICAL_CUTOFF", "STOP_DESCENDANTS_REMAINED"):
            record["status"] = (
                "BUILDER_RUNNER_EXITED" if runner_exit is not None else "BUILDER_EXIT_UNKNOWN"
            )
        if (
            record["status"] == "BUILDER_RUNNER_EXITED"
            and runner_exit == 0
            and logical_report
            and logical_report.get("status") == "PASS"
        ):
            record["status"] = "PASS_QUARANTINED_NOT_SERVABLE"
        elif record["status"] not in ("STOP_NUMERICAL_CUTOFF", "STOP_DESCENDANTS_REMAINED"):
            record["status"] = "BUILDER_NONPASS_OR_MISSING_RESULT"
        if builder_launched and record["status"] != "PASS_QUARANTINED_NOT_SERVABLE":
            try:
                _archive_partial_output(RUN_LEAF, record)
            except Exception as exc:
                record["partialOutputArchive"] = {
                    "status": "ARCHIVE_FAILED_OUTPUT_RETAINED",
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
        tail_deadline = deadline
        try:
            after_repo = _verify_repository(INPUT_MANIFEST, invocation_manifest_sha, tail_deadline)
        except Exception as exc:
            after_repo = {
                "passes": False,
                "checkedFileCount": 0,
                "changed": [{"reason": f"{type(exc).__name__}: {exc}"}],
                "manifestSha256": None,
            }
        try:
            after_external = _verify_external(
                EXTERNAL_MANIFEST, invocation_external_sha, tail_deadline
            )
        except Exception as exc:
            after_external = {
                "passes": False,
                "checkedFileCount": 0,
                "changed": [{"reason": f"{type(exc).__name__}: {exc}"}],
                "manifestSha256": None,
            }
        record["postRunRepositoryPreservation"] = after_repo
        record["postRunExternalPreservation"] = after_external
        record["preservationPasses"] = bool(after_repo["passes"] and after_external["passes"])
        record["absoluteDeadlinePassed"] = time.monotonic() < deadline
        if not record["absoluteDeadlinePassed"]:
            record["status"] = "STOP_TIMEOUT"
        if not record["preservationPasses"]:
            record["status"] = "STOP_PRESERVATION_OR_DEADLINE"
        record["manifestHashStable"] = after_repo.get("manifestSha256") == invocation_manifest_sha
        record["externalManifestHashStable"] = (
            after_external.get("manifestSha256") == invocation_external_sha
        )
        record["supervisorChosenExitCode"] = (
            0
            if record["status"] == "PASS_QUARANTINED_NOT_SERVABLE"
            and record["preservationPasses"]
            and record["absoluteDeadlinePassed"]
            else 2
        )
        record["callerObservedSupervisorExitCode"] = None
        record["callerExitCaptureInstruction"] = (
            "record the native process exit immediately; this field is not inferred"
        )
        record["candidateEligibleForServing"] = False
        record["elapsedWallSeconds"] = time.monotonic() - started
        record["deadlineExceededSeconds"] = max(0.0, record["elapsedWallSeconds"] - TOTAL_SECONDS)
        _update_owned(INVOCATION, record)
        _mirror_record(record)
        return int(record["supervisorChosenExitCode"])
    except Exception as exc:
        record["status"] = (
            "STOP_TIMEOUT"
            if time.monotonic() >= deadline or isinstance(exc, TimeoutError)
            else "SUPERVISOR_OR_PREFLIGHT_FAILURE"
        )
        record["supervisorError"] = {"type": type(exc).__name__, "message": str(exc)}
        record["traceback"] = traceback.format_exc()
        if job is not None:
            try:
                record["termination"] = _terminate_job(kernel, job, deadline, 2)
            except Exception as termination_error:
                record["terminationError"] = {
                    "type": type(termination_error).__name__,
                    "message": str(termination_error),
                }
            try:
                kernel.CloseHandle(job)
            except Exception:
                pass
            job = None
        if process_handles:
            record["processExitCodesAfterTermination"] = [
                {
                    "role": item["role"],
                    "pid": item["pid"],
                    "creationFileTime": item["createdFileTime"],
                    "exitCode": (
                        _exit_code(kernel, item["handle"])
                        if kernel is not None
                        and record.get("termination", {}).get("terminationConfirmed")
                        else None
                    ),
                    "terminationConfirmed": bool(
                        record.get("termination", {}).get("terminationConfirmed")
                    ),
                }
                for item in process_handles
            ]
            builder = next(
                (item for item in process_handles if item["role"] == "candidate-builder-runner"),
                None,
            )
            if builder is not None:
                confirmed = bool(record.get("termination", {}).get("terminationConfirmed"))
                record["builderRunnerExitCodeAfterTermination"] = (
                    _exit_code(kernel, builder["handle"])
                    if kernel is not None and confirmed
                    else None
                )
                record["builderRunnerExitObservedAfterTermination"] = (
                    record["builderRunnerExitCodeAfterTermination"] is not None
                )
        if record.get("termination", {}).get("terminationRequested"):
            record["forcedTermination"] = True
        if builder_launched and record.get("termination", {}).get("terminationConfirmed"):
            try:
                if RUN_LEAF.is_dir():
                    _archive_partial_output(RUN_LEAF, record)
                elif EXPECTED_OUTPUT.exists():
                    record["partialOutputArchive"] = {
                        "status": "OUTPUT_RETAINED_NO_EVIDENCE_LEAF",
                        "path": str(EXPECTED_OUTPUT),
                        "candidateEligibleForServing": False,
                    }
            except Exception as archive_error:
                record["partialOutputArchive"] = {
                    "status": "ARCHIVE_FAILED_OUTPUT_RETAINED",
                    "path": str(EXPECTED_OUTPUT) if EXPECTED_OUTPUT.exists() else None,
                    "error": {"type": type(archive_error).__name__, "message": str(archive_error)},
                }
        elif EXPECTED_OUTPUT.exists():
            record["partialOutputArchive"] = {
                "status": "OUTPUT_RETAINED_UNOWNED_OR_TERMINATION_UNCONFIRMED",
                "path": str(EXPECTED_OUTPUT),
                "candidateEligibleForServing": False,
            }
        if invocation_manifest_sha is not None:
            try:
                record["postRunRepositoryPreservation"] = _verify_repository(
                    INPUT_MANIFEST, invocation_manifest_sha, deadline
                )
            except Exception as verify_error:
                record["postRunRepositoryPreservation"] = {
                    "passes": False,
                    "checkedFileCount": 0,
                    "changed": [{"reason": f"{type(verify_error).__name__}: {verify_error}"}],
                }
            try:
                record["postRunExternalPreservation"] = _verify_external(
                    EXTERNAL_MANIFEST, invocation_external_sha, deadline
                )
            except Exception as verify_error:
                record["postRunExternalPreservation"] = {
                    "passes": False,
                    "checkedFileCount": 0,
                    "changed": [{"reason": f"{type(verify_error).__name__}: {verify_error}"}],
                }
        record["supervisorChosenExitCode"] = 124 if record["status"] == "STOP_TIMEOUT" else 2
        record["callerObservedSupervisorExitCode"] = None
        record["elapsedWallSeconds"] = time.monotonic() - started
        record["deadlineExceededSeconds"] = max(0.0, record["elapsedWallSeconds"] - TOTAL_SECONDS)
        _update_owned(INVOCATION, record)
        _mirror_record(record)
        return int(record["supervisorChosenExitCode"])
    finally:
        if job is not None and kernel is not None:
            try:
                kernel.CloseHandle(job)
            except Exception:
                pass
        for process_record in process_handles:
            if kernel is not None:
                try:
                    kernel.CloseHandle(process_record["handle"])
                except Exception:
                    pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--runtime-preflight-only", action="store_true")
    args = parser.parse_args(argv)
    if args.self_check and args.runtime_preflight_only:
        parser.error("fixed modes are mutually exclusive")
    try:
        if args.self_check:
            return _selfcheck()
        if args.runtime_preflight_only:
            return _preflight_only()
        return _run_build()
    except Exception as exc:
        print(
            json.dumps(
                {"status": "BLOCKED", "errorType": type(exc).__name__, "message": str(exc)},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
