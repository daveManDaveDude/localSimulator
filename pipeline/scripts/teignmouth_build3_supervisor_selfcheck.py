"""Fixed nonnumerical child modes for the build-3 supervisor self-check."""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / ".codex/build3-supervisor-selfcheck-retry-7/run-1"
SCRIPT = Path(__file__).resolve()


def _sha256(path: Path, deadline_qpc: int, frequency: int) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            _check_deadline(deadline_qpc, frequency)
            digest.update(block)
    return digest.hexdigest()


def _qpc_now() -> tuple[int, int]:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.QueryPerformanceCounter.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
    kernel.QueryPerformanceCounter.restype = wintypes.BOOL
    kernel.QueryPerformanceFrequency.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
    kernel.QueryPerformanceFrequency.restype = wintypes.BOOL
    counter = ctypes.c_longlong()
    frequency = ctypes.c_longlong()
    if not kernel.QueryPerformanceCounter(
        ctypes.byref(counter)
    ) or not kernel.QueryPerformanceFrequency(ctypes.byref(frequency)):
        raise ctypes.WinError(ctypes.get_last_error())
    return counter.value, frequency.value


def _check_deadline(deadline_qpc: int, frequency: int) -> None:
    counter, observed_frequency = _qpc_now()
    if observed_frequency != frequency or counter >= deadline_qpc:
        raise TimeoutError("inherited self-check QPC deadline expired")


def _api() -> Any:
    if os.name != "nt":
        raise OSError("fixed self-check requires Windows process identity")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel.Process32FirstW.restype = wintypes.BOOL
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel.Process32NextW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    return kernel


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


def _native_identity(pid: int, deadline_qpc: int, frequency: int) -> dict[str, Any]:
    kernel = _api()
    _check_deadline(deadline_qpc, frequency)
    handle = kernel.OpenProcess(0x0400 | 0x1000, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        created = wintypes.FILETIME()
        exited = wintypes.FILETIME()
        kernel_time = wintypes.FILETIME()
        user_time = wintypes.FILETIME()
        if not kernel.GetProcessTimes(
            handle,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel_time),
            ctypes.byref(user_time),
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        buffer = ctypes.create_unicode_buffer(32768)
        length = wintypes.DWORD(len(buffer))
        if not kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length)):
            raise ctypes.WinError(ctypes.get_last_error())
        image = Path(buffer.value).resolve(strict=True)
        return {
            "pid": pid,
            "creationFileTime": (created.dwHighDateTime << 32) | created.dwLowDateTime,
            "imagePath": str(image),
            "imageSha256": _sha256(image, deadline_qpc, frequency),
        }
    finally:
        kernel.CloseHandle(handle)


def _parent_pid(pid: int, deadline_qpc: int, frequency: int) -> int:
    kernel = _api()
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot in (None, wintypes.HANDLE(-1).value):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        if not kernel.Process32FirstW(snapshot, ctypes.byref(entry)):
            raise ctypes.WinError(ctypes.get_last_error())
        for _ in range(65536):
            _check_deadline(deadline_qpc, frequency)
            if entry.th32ProcessID == pid:
                return int(entry.th32ParentProcessID)
            if not kernel.Process32NextW(snapshot, ctypes.byref(entry)):
                break
        raise RuntimeError("PID absent from bounded process snapshot")
    finally:
        kernel.CloseHandle(snapshot)


def _write(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _consume_startup(mode: str) -> dict[str, Any]:
    auth_path = EVIDENCE / f"{mode}-authorization.json"
    consumed = EVIDENCE / f"{mode}-authorization.consumed.json"
    auth = json.loads(auth_path.read_text(encoding="utf-8"))
    frequency = auth.get("qpcFrequency")
    deadline_qpc = auth.get("deadlineQpc")
    if (
        auth.get("clockDomain") != "windows-qpc"
        or not isinstance(frequency, int)
        or frequency <= 0
        or not isinstance(deadline_qpc, int)
    ):
        raise ValueError("self-check authorization lacks inherited absolute deadline")
    _check_deadline(deadline_qpc, frequency)
    current = _native_identity(os.getpid(), deadline_qpc, frequency)
    launcher_pid = _parent_pid(os.getpid(), deadline_qpc, frequency)
    launcher = _native_identity(launcher_pid, deadline_qpc, frequency)
    supervisor_pid = _parent_pid(launcher_pid, deadline_qpc, frequency)
    supervisor = _native_identity(supervisor_pid, deadline_qpc, frequency)
    if (
        auth.get("schema") != "teignmouth-build3-selfcheck-helper-auth-v1"
        or auth.get("mode") != mode
        or auth.get("oneUse") is not True
        or auth.get("launcherPid") != launcher_pid
        or auth.get("launcherCreationFileTime") != launcher["creationFileTime"]
        or auth.get("launcherImagePath") != launcher["imagePath"]
        or auth.get("launcherImageSha256") != launcher["imageSha256"]
        or current["imagePath"] != auth.get("baseInterpreterPath")
        or current["imageSha256"] != auth.get("baseInterpreterSha256")
        or auth.get("venvLauncherPath") != str(ROOT / "pipeline/.venv/Scripts/python.exe")
        or auth.get("venvLauncherSha256")
        != _sha256(ROOT / "pipeline/.venv/Scripts/python.exe", deadline_qpc, frequency)
        or supervisor_pid != auth.get("supervisorPid")
        or supervisor["creationFileTime"] != auth.get("supervisorCreationFileTime")
        or supervisor["imagePath"] != auth.get("supervisorImagePath")
        or supervisor["imageSha256"] != auth.get("supervisorImageSha256")
        or _parent_pid(os.getpid(), deadline_qpc, frequency) != launcher_pid
    ):
        raise ValueError("self-check helper launcher/interpreter chain is not authorized")
    os.rename(auth_path, consumed)
    _write(
        EVIDENCE / f"{mode}-script-start.json",
        {
            "schema": "teignmouth-build3-helper-script-start-v1",
            "mode": mode,
            "nonce": auth["nonce"],
            "scriptPid": os.getpid(),
            "scriptCreationFileTime": current["creationFileTime"],
            "scriptImagePath": current["imagePath"],
            "scriptImageSha256": current["imageSha256"],
            "launcherPid": launcher_pid,
            "launcherCreationFileTime": launcher["creationFileTime"],
            "launcherImagePath": launcher["imagePath"],
            "launcherImageSha256": launcher["imageSha256"],
            "supervisorPid": supervisor_pid,
            "supervisorCreationFileTime": supervisor["creationFileTime"],
            "qpcFrequency": frequency,
            "deadlineQpc": deadline_qpc,
        },
    )
    return auth


def _write_marker(name: str, value: dict[str, Any]) -> None:
    _write(EVIDENCE / name, value)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    modes = {"--nonzero": "nonzero", "--tree-root": "tree-root"}
    if args and args[0] in modes and len(args) == 1:
        mode = modes[args[0]]
        auth = _consume_startup(mode)
        frequency = int(auth["qpcFrequency"])
        deadline_qpc = int(auth["deadlineQpc"])
        if mode == "nonzero":
            _write_marker(
                "nonzero-helper.json",
                {"status": "EXPECTED_NONZERO_HELPER", "exitCode": 7},
            )
            remaining = max(0.0, (deadline_qpc - _qpc_now()[0]) / frequency)
            time.sleep(min(0.15, remaining))
            return 7
        child = subprocess.Popen(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                "--tree-child",
                str(frequency),
                str(deadline_qpc),
            ],
            cwd=ROOT,
        )
        child_launcher_identity = _native_identity(child.pid, deadline_qpc, frequency)
        root_identity = _native_identity(os.getpid(), deadline_qpc, frequency)
        _write_marker(
            "tree-root-started.json",
            {
                "status": "CHILD_STARTED",
                "pid": os.getpid(),
                "parentPid": os.getppid(),
                "creationFileTime": root_identity["creationFileTime"],
                "childLauncherPid": child.pid,
                "childLauncherCreationFileTime": child_launcher_identity["creationFileTime"],
                "script": str(SCRIPT),
                "nonce": auth["nonce"],
            },
        )
        try:
            remaining = max(0.0, (deadline_qpc - _qpc_now()[0]) / frequency)
            child.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            remaining = max(0.0, (deadline_qpc - _qpc_now()[0]) / frequency)
            time.sleep(remaining)
        return 0
    if len(args) == 3 and args[0] == "--tree-child":
        frequency, deadline_qpc = int(args[1]), int(args[2])
        _check_deadline(deadline_qpc, frequency)
        launcher = _native_identity(os.getppid(), deadline_qpc, frequency)
        script_identity = _native_identity(os.getpid(), deadline_qpc, frequency)
        _write_marker(
            "tree-child-started.json",
            {
                "status": "CONTAINED_CHILD_STARTED",
                "pid": os.getpid(),
                "parentPid": os.getppid(),
                "launcherPid": os.getppid(),
                "launcherCreationFileTime": launcher["creationFileTime"],
                "launcherImagePath": launcher["imagePath"],
                "launcherImageSha256": launcher["imageSha256"],
                "creationFileTime": script_identity["creationFileTime"],
                "imagePath": script_identity["imagePath"],
                "imageSha256": script_identity["imageSha256"],
                "script": str(SCRIPT),
            },
        )
        remaining = max(0.0, (deadline_qpc - _qpc_now()[0]) / frequency)
        time.sleep(remaining)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
