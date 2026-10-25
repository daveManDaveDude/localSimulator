"""Build-3-only import/runtime identity preflight; it never loads GIS data."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
import traceback
from ctypes import wintypes
from pathlib import Path, PureWindowsPath
from typing import Any

ISSUE = "Teignmouth-float32-topology-representation-1"
ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "pipeline"
BUILD3 = ROOT / "docs/milestones/artifacts/Teignmouth-float32-topology/build-3"
INPUT_MANIFEST = BUILD3 / "input-manifest.json"
EXTERNAL_MANIFEST = BUILD3 / "external-runtime-manifest.json"
RUNTIME_IDENTITY = BUILD3 / "runtime-identity.json"
STANDALONE_AUTH = BUILD3 / "runtime-preflight-authorization.json"
STANDALONE_AUTH_CONSUMED = BUILD3 / "runtime-preflight-authorization.consumed.json"
STANDALONE_EVIDENCE = ROOT / ".codex/build3-runtime-preflight/run-1"
STANDALONE_DISPATCH_AUTH = STANDALONE_EVIDENCE / "parent-preflight-authorization.json"
STANDALONE_DISPATCH_AUTH_CONSUMED = (
    STANDALONE_EVIDENCE / "parent-preflight-authorization.consumed.json"
)
RESULT_RELATIVE = (
    "docs/milestones/artifacts/Teignmouth-float32-topology/build-3/runtime-preflight-result.json"
)
REQUIRED_IMPORTS = (
    "numpy",
    "shapely",
    "pyproj",
    "torquay_pipeline.road_surface",
    "torquay_pipeline.road_surface_float32_frame",
    "torquay_pipeline.road_surface_topology",
    "torquay_pipeline.teignmouth_corridor_continuation",
    "torquay_pipeline.teignmouth_corridor_prototype",
    "torquay_pipeline.teignmouth_float32_candidate",
)
ENVIRONMENT_KEYS = (
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
ALLOWED_PYTHON_ENVIRONMENT = {
    "PYTHONPATH",
    "PYTHONNOUSERSITE",
    "PYTHONDONTWRITEBYTECODE",
}


def _parse_pyvenv_cfg(deadline_qpc: int, frequency: int) -> dict[str, str]:
    path = PIPELINE / ".venv/pyvenv.cfg"
    before = _sha256(path, deadline_qpc=deadline_qpc, frequency=frequency)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"pyvenv.cfg is unreadable: {path}") from exc
    values: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        _check_deadline(deadline_qpc, frequency)
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
    if _sha256(path, deadline_qpc=deadline_qpc, frequency=frequency) != before:
        raise ValueError("pyvenv.cfg changed while it was parsed")
    required = {"home", "version", "include-system-site-packages"}
    if not required.issubset(values):
        raise ValueError("pyvenv.cfg omits a required startup-policy key")
    base = Path(getattr(sys, "_base_executable", sys.executable)).resolve(strict=True).parent
    if (
        Path(values["home"]).resolve(strict=True) != base
        or values["version"] != "3.13.7"
        or values["include-system-site-packages"].casefold() != "false"
    ):
        raise ValueError("pyvenv.cfg differs from the pinned CPython 3.13.7 venv policy")
    return values


INTERNAL_AUTH = BUILD3 / "internal-preflight-authorization.json"
INTERNAL_AUTH_CONSUMED = BUILD3 / "internal-preflight-authorization.consumed.json"
INTERNAL_START = BUILD3 / "runtime-preflight-script-start.json"
_COLLECTION_PROGRESS: dict[str, Any] = {}


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


def _qpc_now() -> tuple[int, int]:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
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
        raise TimeoutError("inherited QPC deadline expired or changed during runtime preflight")


def _deadline_from_auth(auth: dict[str, Any]) -> tuple[int, int, float]:
    frequency = auth.get("qpcFrequency")
    deadline_qpc = auth.get("deadlineQpc")
    if (
        auth.get("clockDomain") != "windows-qpc"
        or not isinstance(frequency, int)
        or frequency <= 0
        or not isinstance(deadline_qpc, int)
    ):
        raise ValueError("helper authorization lacks the inherited absolute QPC deadline")
    _check_deadline(deadline_qpc, frequency)
    return deadline_qpc, frequency, deadline_qpc / frequency


def _process_parent_and_creation(pid: int, deadline_qpc: int, frequency: int) -> tuple[int, int]:
    if os.name != "nt":
        raise OSError("dispatch authorization requires Windows process identity")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel.Process32FirstW.restype = wintypes.BOOL
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel.Process32NextW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    snapshot = kernel.CreateToolhelp32Snapshot(0x00000002, 0)
    if snapshot in (None, wintypes.HANDLE(-1).value):
        raise ctypes.WinError(ctypes.get_last_error())
    parent = None
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        if not kernel.Process32FirstW(snapshot, ctypes.byref(entry)):
            raise ctypes.WinError(ctypes.get_last_error())
        for _ in range(65536):
            _check_deadline(deadline_qpc, frequency)
            if entry.th32ProcessID == pid:
                parent = int(entry.th32ParentProcessID)
                break
            if not kernel.Process32NextW(snapshot, ctypes.byref(entry)):
                break
    finally:
        kernel.CloseHandle(snapshot)
    if parent is None:
        raise RuntimeError("process parent missing from bounded process snapshot")
    handle = kernel.OpenProcess(0x0400 | 0x1000, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        _check_deadline(deadline_qpc, frequency)
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
        _check_deadline(deadline_qpc, frequency)
        value = (creation.dwHighDateTime << 32) | creation.dwLowDateTime
    finally:
        kernel.CloseHandle(handle)
    return parent, value


def _native_identity(pid: int, deadline_qpc: int, frequency: int) -> dict[str, Any]:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x0400 | 0x1000, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        _check_deadline(deadline_qpc, frequency)
        created = wintypes.FILETIME()
        exited = wintypes.FILETIME()
        kernel_time = wintypes.FILETIME()
        user_time = wintypes.FILETIME()
        kernel.GetProcessTimes.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
        ]
        kernel.GetProcessTimes.restype = wintypes.BOOL
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
        _check_deadline(deadline_qpc, frequency)
        image = Path(buffer.value).resolve(strict=True)
        return {
            "pid": pid,
            "creationFileTime": (created.dwHighDateTime << 32) | created.dwLowDateTime,
            "imagePath": str(image),
            "imageSha256": _sha256(image, deadline_qpc=deadline_qpc, frequency=frequency),
        }
    finally:
        kernel.CloseHandle(handle)


def _write_script_start(auth: dict[str, Any], mode: str) -> None:
    if mode == "build-dispatch":
        target = INTERNAL_START
    else:
        target = STANDALONE_EVIDENCE / "runtime-preflight-script-start.json"
    current_pid = os.getpid()
    deadline_qpc, frequency, _deadline = _deadline_from_auth(auth)
    parent_pid, creation = _process_parent_and_creation(current_pid, deadline_qpc, frequency)
    current = _native_identity(current_pid, deadline_qpc, frequency)
    launcher = _native_identity(parent_pid, deadline_qpc, frequency)
    if (
        current["imagePath"] != auth["baseInterpreterPath"]
        or current["imageSha256"] != auth["baseInterpreterSha256"]
        or parent_pid != auth["launcherPid"]
        or launcher["creationFileTime"] != auth["launcherCreationFileTime"]
        or launcher["imagePath"] != auth["launcherImagePath"]
        or launcher["imageSha256"] != auth["launcherImageSha256"]
        or _process_parent_and_creation(parent_pid, deadline_qpc, frequency)[0]
        != auth["supervisorPid"]
    ):
        raise ValueError("preflight process chain differs from suspended-launch authorization")
    supervisor = _native_identity(int(auth["supervisorPid"]), deadline_qpc, frequency)
    if (
        supervisor["creationFileTime"] != auth["supervisorCreationFileTime"]
        or supervisor["imagePath"] != auth["supervisorImagePath"]
        or supervisor["imageSha256"] != auth["supervisorImageSha256"]
    ):
        raise ValueError("preflight supervisor identity differs from authorization")
    if target.exists():
        raise FileExistsError("fixed preflight script-start record already exists")
    payload = {
        "schema": "teignmouth-build3-helper-script-start-v1",
        "mode": mode,
        "nonce": auth["dispatchNonce"],
        "scriptPid": current_pid,
        "scriptCreationFileTime": creation,
        "scriptImagePath": current["imagePath"],
        "scriptImageSha256": current["imageSha256"],
        "launcherPid": parent_pid,
        "launcherCreationFileTime": launcher["creationFileTime"],
        "launcherImagePath": launcher["imagePath"],
        "launcherImageSha256": launcher["imageSha256"],
        "supervisorPid": auth["supervisorPid"],
        "supervisorCreationFileTime": auth["supervisorCreationFileTime"],
        "qpcFrequency": frequency,
        "deadlineQpc": deadline_qpc,
    }
    _atomic_result(target, payload)


def _consume_internal_authorization() -> dict[str, Any]:
    auth = json.loads(INTERNAL_AUTH.read_text(encoding="utf-8"))
    deadline_qpc, frequency, _deadline = _deadline_from_auth(auth)
    current_pid = os.getpid()
    current_parent, current_creation = _process_parent_and_creation(
        current_pid, deadline_qpc, frequency
    )
    launcher_parent, launcher_creation = _process_parent_and_creation(
        current_parent, deadline_qpc, frequency
    )
    supervisor_creation = _process_parent_and_creation(launcher_parent, deadline_qpc, frequency)[1]
    ledger_snapshot_sha = _sha256(
        BUILD3 / "reserved-ledger-snapshot.json", deadline_qpc=deadline_qpc, frequency=frequency
    )
    if (
        auth.get("schema") != "teignmouth-build3-internal-preflight-auth-v1"
        or auth.get("mode") != "build-dispatch"
        or auth.get("oneUse") is not True
        or auth.get("launcherPid") != current_parent
        or auth.get("launcherCreationFileTime") != launcher_creation
        or auth.get("supervisorPid") != launcher_parent
        or auth.get("supervisorCreationFileTime") != supervisor_creation
        or auth.get("inputManifestSha256")
        != _sha256(INPUT_MANIFEST, deadline_qpc=deadline_qpc, frequency=frequency)
        or auth.get("externalRuntimeManifestSha256")
        != _sha256(EXTERNAL_MANIFEST, deadline_qpc=deadline_qpc, frequency=frequency)
        or auth.get("runtimeIdentitySha256")
        != _sha256(RUNTIME_IDENTITY, deadline_qpc=deadline_qpc, frequency=frequency)
        or auth.get("ledgerSnapshotSha256") != ledger_snapshot_sha
        or not isinstance(auth.get("dispatchNonce"), str)
    ):
        raise ValueError(
            "build-dispatch preflight lacks matching one-use contained-worker authorization"
        )
    os.rename(INTERNAL_AUTH, INTERNAL_AUTH_CONSUMED)
    auth.update(
        {
            "baseInterpreterPath": auth.get("baseInterpreterPath"),
            "baseInterpreterSha256": auth.get("baseInterpreterSha256"),
        }
    )
    _write_script_start(auth, "build-dispatch")
    return auth


def _consume_standalone_dispatch_authorization() -> dict[str, Any]:
    auth = json.loads(STANDALONE_DISPATCH_AUTH.read_text(encoding="utf-8"))
    deadline_qpc, frequency, _deadline = _deadline_from_auth(auth)
    current_pid = os.getpid()
    current_parent, current_creation = _process_parent_and_creation(
        current_pid, deadline_qpc, frequency
    )
    launcher_parent, launcher_creation = _process_parent_and_creation(
        current_parent, deadline_qpc, frequency
    )
    supervisor_creation = _process_parent_and_creation(launcher_parent, deadline_qpc, frequency)[1]
    if (
        auth.get("schema") != "teignmouth-build3-parent-preflight-auth-v1"
        or auth.get("mode") != "standalone"
        or auth.get("oneUse") is not True
        or auth.get("launcherPid") != current_parent
        or auth.get("launcherCreationFileTime") != launcher_creation
        or auth.get("supervisorPid") != launcher_parent
        or auth.get("supervisorCreationFileTime") != supervisor_creation
        or auth.get("purpose")
        not in (
            "collect-unreserved-runtime-identity",
            "verify-unreserved-runtime-identity",
        )
        or auth.get("purpose") == "verify-unreserved-runtime-identity"
        and (
            auth.get("inputManifestSha256")
            != _sha256(INPUT_MANIFEST, deadline_qpc=deadline_qpc, frequency=frequency)
            or auth.get("externalRuntimeManifestSha256")
            != _sha256(EXTERNAL_MANIFEST, deadline_qpc=deadline_qpc, frequency=frequency)
            or auth.get("runtimeIdentitySha256")
            != _sha256(RUNTIME_IDENTITY, deadline_qpc=deadline_qpc, frequency=frequency)
        )
        or not isinstance(auth.get("dispatchNonce"), str)
    ):
        raise ValueError("standalone preflight lacks matching contained-worker authorization")
    os.rename(STANDALONE_DISPATCH_AUTH, STANDALONE_DISPATCH_AUTH_CONSUMED)
    _write_script_start(auth, "standalone")
    return auth


def _sha256(path: Path, *, deadline_qpc: int | None = None, frequency: int | None = None) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            if deadline_qpc is not None and frequency is not None:
                _check_deadline(deadline_qpc, frequency)
            digest.update(block)
    return digest.hexdigest()


def _atomic_result(path: Path, record: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _repository_bindings(
    deadline_qpc: int, frequency: int, *, standalone: bool
) -> tuple[dict[str, dict[str, Any]], str]:
    _check_deadline(deadline_qpc, frequency)
    manifest_sha = _sha256(INPUT_MANIFEST, deadline_qpc=deadline_qpc, frequency=frequency)
    manifest = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    if (
        manifest.get("schema") != "teignmouth-float32-build-input-v1"
        or manifest.get("issueId") != ISSUE
        or manifest.get("buildOrdinal") != 3
        or manifest.get("candidateEligibleForServing") is not False
    ):
        raise ValueError("repository manifest is not the fixed ordinal-3 manifest")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) < 291 or manifest.get("fileCount") != len(files):
        raise ValueError("repository manifest must contain nonempty file bindings")
    bindings = {}
    folded_paths: dict[str, str] = {}
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("repository manifest contains a malformed binding")
        relative = item.get("path")
        digest_pin = item.get("sha256")
        if isinstance(relative, str):
            folded = relative.casefold()
            prior = folded_paths.get(folded)
            if prior is not None and prior != relative:
                raise ValueError(
                    f"repository manifest has case-distinct paths: {prior} <> {relative}"
                )
            folded_paths[folded] = relative
        if (
            not isinstance(relative, str)
            or relative in bindings
            or not isinstance(item.get("byteLength"), int)
            or item["byteLength"] < 0
            or not isinstance(digest_pin, str)
            or len(digest_pin) != 64
            or any(character not in "0123456789abcdef" for character in digest_pin)
        ):
            raise ValueError("repository manifest contains an invalid or duplicate path")
        path = (ROOT / relative).resolve(strict=True)
        if path.relative_to(ROOT).as_posix() != relative or not path.is_file():
            raise ValueError(f"repository input escapes or is noncanonical: {relative}")
        _check_deadline(deadline_qpc, frequency)
        payload_size = path.stat().st_size
        digest = _sha256(path, deadline_qpc=deadline_qpc, frequency=frequency)
        if (payload_size, digest) != (item.get("byteLength"), item.get("sha256")):
            raise ValueError(f"repository input hash mismatch: {relative}")
        bindings[relative] = item
    _check_deadline(deadline_qpc, frequency)
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
    missing = sorted(required - bindings.keys())
    if missing:
        raise ValueError(f"repository manifest omits mandatory control bindings: {missing}")
    if _sha256(INPUT_MANIFEST, deadline_qpc=deadline_qpc, frequency=frequency) != manifest_sha:
        raise ValueError("repository manifest changed during preflight verification")
    return bindings, manifest_sha


def _external_bindings(deadline_qpc: int, frequency: int) -> tuple[dict[str, dict[str, Any]], str]:
    _check_deadline(deadline_qpc, frequency)
    manifest_sha = _sha256(EXTERNAL_MANIFEST, deadline_qpc=deadline_qpc, frequency=frequency)
    contract = json.loads(EXTERNAL_MANIFEST.read_text(encoding="utf-8"))
    if contract.get("schema") != "teignmouth-build3-external-runtime-v1":
        raise ValueError("external runtime manifest schema mismatch")
    root_records = contract.get("roots")
    entry_records = contract.get("entries")
    if (
        not isinstance(root_records, list)
        or not root_records
        or not isinstance(entry_records, list)
        or not entry_records
        or contract.get("rootCount") != len(root_records)
        or contract.get("entryCount") != len(entry_records)
    ):
        raise ValueError("external runtime manifest counts or required lists are invalid")
    roots = []
    root_seen: set[str] = set()
    root_folded: dict[str, str] = {}
    approved_categories = {"venv-runtime", "base-python-runtime", "windows-system-runtime"}
    for item in root_records:
        _check_deadline(deadline_qpc, frequency)
        if not isinstance(item, dict) or item.get("category") not in approved_categories:
            raise ValueError("external runtime root has an unapproved category")
        raw_root = item.get("path")
        if not isinstance(raw_root, str) or raw_root in root_seen:
            raise ValueError("external runtime root path is missing or duplicated")
        previous_root = root_folded.get(raw_root.casefold())
        if previous_root is not None and previous_root != raw_root:
            raise ValueError(
                f"external roots have case-distinct identities: {previous_root} <> {raw_root}"
            )
        root_path = Path(raw_root).resolve(strict=True)
        if not root_path.is_dir() or str(root_path) != raw_root:
            raise ValueError("external runtime root is missing or noncanonical")
        root_seen.add(raw_root)
        root_folded[raw_root.casefold()] = raw_root
        roots.append((root_path, item.get("category")))
    entries = {}
    entry_folded: dict[str, str] = {}
    for item in entry_records:
        _check_deadline(deadline_qpc, frequency)
        if not isinstance(item, dict):
            raise ValueError("external runtime entry is malformed")
        raw_path = item.get("path")
        pin = item.get("sha256")
        if isinstance(raw_path, str):
            previous_path = entry_folded.get(raw_path.casefold())
            if previous_path is not None and previous_path != raw_path:
                raise ValueError(
                    f"external entries have case-distinct paths: {previous_path} <> {raw_path}"
                )
            entry_folded[raw_path.casefold()] = raw_path
        if (
            not isinstance(raw_path, str)
            or not Path(raw_path).is_absolute()
            or raw_path in entries
            or not isinstance(item.get("byteLength"), int)
            or item["byteLength"] < 0
            or not isinstance(pin, str)
            or len(pin) != 64
            or any(character not in "0123456789abcdef" for character in pin)
            or item.get("category") not in approved_categories
        ):
            raise ValueError("external runtime entry has an invalid or duplicate absolute path")
        path = Path(raw_path).resolve(strict=True)
        if str(path) != raw_path or not path.is_file():
            raise ValueError(f"external runtime file is missing or noncanonical: {raw_path}")
        matches = [(base, category) for base, category in roots if path.is_relative_to(base)]
        if len(matches) != 1 or matches[0][1] != item.get("category"):
            raise ValueError(f"external runtime path escapes its unique declared root: {raw_path}")
        if (path.stat().st_size, _sha256(path, deadline_qpc=deadline_qpc, frequency=frequency)) != (
            item.get("byteLength"),
            item.get("sha256"),
        ):
            raise ValueError(f"external runtime file hash mismatch: {raw_path}")
        entries[raw_path] = item
    if len(entries) != len(entry_records):
        raise ValueError("external runtime manifest has no file entries")
    if _sha256(EXTERNAL_MANIFEST, deadline_qpc=deadline_qpc, frequency=frequency) != manifest_sha:
        raise ValueError("external runtime manifest changed during verification")
    return entries, manifest_sha


def _prevalidate_frozen_closure(
    mode: str, auth: dict[str, Any], deadline_qpc: int, frequency: int
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    standalone = mode == "standalone"
    repository, manifest_sha = _repository_bindings(deadline_qpc, frequency, standalone=standalone)
    external, external_sha = _external_bindings(deadline_qpc, frequency)
    canonical_identities: dict[str, str] = {}
    for relative in repository:
        absolute = str((ROOT / relative).resolve(strict=True))
        folded = absolute.casefold()
        prior = canonical_identities.get(folded)
        if prior is not None:
            raise ValueError(
                "frozen runtime has duplicate or case-distinct canonical paths: "
                f"{prior} <> {absolute}"
            )
        canonical_identities[folded] = absolute
    for absolute in external:
        folded = absolute.casefold()
        prior = canonical_identities.get(folded)
        if prior is not None:
            raise ValueError(
                "frozen runtime has duplicate or case-distinct canonical paths: "
                f"{prior} <> {absolute}"
            )
        canonical_identities[folded] = absolute
    identity_sha = _sha256(RUNTIME_IDENTITY, deadline_qpc=deadline_qpc, frequency=frequency)
    if (
        auth.get("inputManifestSha256") != manifest_sha
        or auth.get("externalRuntimeManifestSha256") != external_sha
        or auth.get("runtimeIdentitySha256") != identity_sha
    ):
        raise ValueError("parent authorization does not bind the frozen runtime inputs")
    runtime_binding = repository.get(
        "docs/milestones/artifacts/Teignmouth-float32-topology/build-3/runtime-identity.json"
    )
    external_binding = repository.get(
        "docs/milestones/artifacts/Teignmouth-float32-topology/build-3/external-runtime-manifest.json"
    )
    if runtime_binding is None or external_binding is None:
        raise ValueError("repository closure omits runtime identity or external manifest controls")
    record = json.loads(RUNTIME_IDENTITY.read_text(encoding="utf-8"))
    if (
        not isinstance(record, dict)
        or record.get("schema") != "teignmouth-build3-runtime-identity-v1"
        or not isinstance(record.get("identity"), dict)
        or record.get("externalRuntimeManifestSha256") != external_sha
    ):
        raise ValueError("runtime identity schema or external-manifest linkage mismatch")
    _check_deadline(deadline_qpc, frequency)
    if (
        _sha256(INPUT_MANIFEST, deadline_qpc=deadline_qpc, frequency=frequency) != manifest_sha
        or _sha256(EXTERNAL_MANIFEST, deadline_qpc=deadline_qpc, frequency=frequency)
        != external_sha
        or _sha256(RUNTIME_IDENTITY, deadline_qpc=deadline_qpc, frequency=frequency) != identity_sha
    ):
        raise ValueError("frozen runtime controls changed during pre-import validation")
    return repository, external, record


def _assert_python_startup_profile(
    deadline_qpc: int,
    frequency: int,
    *,
    pipeline_inserted: bool,
    expected_environment: dict[str, Any] | None,
) -> dict[str, Any]:
    _check_deadline(deadline_qpc, frequency)
    _parse_pyvenv_cfg(deadline_qpc, frequency)
    if (
        platform.python_implementation() != "CPython"
        or sys.version_info[:3] != (3, 13, 7)
        or sys.maxsize != (1 << 63) - 1
        or getattr(sys, "abiflags", "")
    ):
        raise ValueError("interpreter version/debug ABI differs from pinned CPython 3.13.7")
    observed_environment = {key: os.environ.get(key) for key in ENVIRONMENT_KEYS}
    if expected_environment is not None:
        if not isinstance(expected_environment, dict) or any(
            key not in expected_environment for key in ENVIRONMENT_KEYS
        ):
            raise ValueError("frozen runtime identity omits Python profile environment keys")
        if observed_environment != {key: expected_environment[key] for key in ENVIRONMENT_KEYS}:
            raise ValueError("Python profile environment differs from the frozen identity")
    for key, value in os.environ.items():
        _check_deadline(deadline_qpc, frequency)
        if (
            key.upper().startswith("PYTHON")
            and value
            and key.upper() not in ALLOWED_PYTHON_ENVIRONMENT
        ):
            raise ValueError(f"unsupported nonempty Python startup override: {key}")
    if os.environ.get("PYTHONHOME"):
        raise ValueError("PYTHONHOME is unsupported by the finite startup profile")
    if os.environ.get("PYTHONNOUSERSITE") not in (None, "", "1"):
        raise ValueError("PYTHONNOUSERSITE must be absent or 1")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") not in (None, "", "1"):
        raise ValueError("PYTHONDONTWRITEBYTECODE must be absent or 1")
    for key in ("GEOS_LIBDIR", "GEOS_LIBRARY_PATH"):
        if os.environ.get(key):
            raise ValueError(f"{key} is unsupported by the finite native profile")

    roots = _collection_roots(deadline_qpc, frequency)
    native_path_seen: set[str] = set()
    raw_path = os.environ.get("PATH", "")
    if not raw_path:
        raise ValueError("PATH is unavailable in the finite native profile")
    for raw in raw_path.split(os.pathsep):
        _check_deadline(deadline_qpc, frequency)
        if not raw:
            raise ValueError("PATH contains an empty native search entry")
        path = Path(raw)
        resolved = path.resolve(strict=True)
        key = str(resolved).casefold()
        if (
            not path.is_absolute()
            or str(resolved) != raw
            or not resolved.is_dir()
            or key in native_path_seen
            or not _path_under_allowed_roots(raw, roots, deadline_qpc, frequency)
        ):
            raise ValueError(f"PATH entry is unsupported or ambiguous: {raw}")
        native_path_seen.add(key)
    for key in ("PROJ_DATA", "PROJ_LIB", "GDAL_DATA"):
        raw = os.environ.get(key)
        if raw:
            path = Path(raw)
            if not path.is_absolute() or str(path.resolve(strict=True)) != raw:
                raise ValueError(f"{key} is not a canonical absolute profile path")
            if not path.is_dir() or not _path_under_allowed_roots(
                raw, roots, deadline_qpc, frequency
            ):
                raise ValueError(f"{key} is not an inventoried approved data directory")

    python_path_entries = []
    raw_python_path = os.environ.get("PYTHONPATH")
    if raw_python_path:
        for raw in raw_python_path.split(os.pathsep):
            _check_deadline(deadline_qpc, frequency)
            if not raw or not Path(raw).is_absolute() or "!" in raw:
                raise ValueError("PYTHONPATH contains an empty, relative or zip-subpath entry")
            resolved = Path(raw).resolve(strict=True)
            if str(resolved) != raw or not _path_under_allowed_roots(
                raw, roots, deadline_qpc, frequency
            ):
                raise ValueError(
                    f"PYTHONPATH entry is noncanonical or outside approved roots: {raw}"
                )
            if resolved.is_dir():
                python_path_entries.append(str(resolved))
            else:
                raise ValueError(f"PYTHONPATH must contain directories, not archives/files: {raw}")
    base_home = Path(getattr(sys, "_base_executable", sys.executable)).resolve(strict=True).parent
    stdlib_zip = base_home / "python313.zip"
    if stdlib_zip.exists():
        raise ValueError(f"active standard-library archive is unsupported: {stdlib_zip}")
    venv_site = Path(sys.prefix).resolve(strict=True) / "Lib" / "site-packages"
    pth_entries: list[str] = []
    pth_spellings: dict[str, str] = {}
    for hook in sorted(venv_site.glob("*.pth"), key=lambda item: item.name.casefold()):
        _check_deadline(deadline_qpc, frequency)
        try:
            hook_bytes = hook.read_bytes()
            _check_deadline(deadline_qpc, frequency)
            lines = hook_bytes.decode("ascii").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError(f"site path hook is unreadable or non-ASCII: {hook}") from exc
        for line in lines:
            _check_deadline(deadline_qpc, frequency)
            if not line.strip() or line.startswith("#"):
                continue
            if line[0].isspace():
                raise ValueError(f"leading whitespace in site path hook is unsupported: {hook}")
            if line.startswith(("import ", "import\t")):
                raise ValueError(f"executable site path hook is unsupported: {hook}")
            target = Path(line.rstrip())
            target = target if target.is_absolute() else venv_site / target
            resolved = target.resolve(strict=True)
            if str(resolved) != str(target) or not resolved.is_dir():
                raise ValueError(f"site path hook target is missing or noncanonical: {target}")
            if not _path_under_allowed_roots(str(resolved), roots, deadline_qpc, frequency):
                raise ValueError(f"site path hook target escapes approved roots: {resolved}")
            folded_target = str(resolved).casefold()
            previous_target = pth_spellings.get(folded_target)
            if previous_target is not None and previous_target != str(resolved):
                raise ValueError(
                    "site path hooks contain case-distinct targets: "
                    f"{previous_target} <> {resolved}"
                )
            if previous_target is None:
                pth_spellings[folded_target] = str(resolved)
                pth_entries.append(str(resolved))

    script_root = Path(__file__).resolve(strict=True).parent
    expected_paths = [str(PIPELINE.resolve(strict=True))] if pipeline_inserted else []
    expected_paths.append(str(script_root))
    expected_paths.extend(python_path_entries)
    expected_paths.extend(
        [
            str(stdlib_zip),
            str(base_home / "DLLs"),
            str(base_home / "Lib"),
            str(Path(sys.prefix).resolve(strict=True) / "Lib" / "site-packages"),
        ]
    )
    expected_paths.extend(pth_entries)
    actual_paths = []
    for raw in sys.path:
        _check_deadline(deadline_qpc, frequency)
        if not isinstance(raw, str) or not raw or not Path(raw).is_absolute():
            raise ValueError("Python sys.path contains an empty or relative entry")
        actual_paths.append(str(Path(raw).resolve(strict=False)))
    expected_folded = [item.casefold() for item in expected_paths]
    actual_folded = [item.casefold() for item in actual_paths]
    if actual_folded != expected_folded:
        raise ValueError("actual sys.path order differs from the supported Windows venv profile")
    if actual_paths != expected_paths:
        raise ValueError("actual sys.path contains a case-distinct path alias")
    if len(set(actual_folded)) != len(actual_folded):
        raise ValueError("Python sys.path contains duplicate or ambiguous roots")

    site_module = sys.modules.get("site")
    if site_module is None or getattr(site_module, "ENABLE_USER_SITE", None) is not False:
        raise ValueError("Python site policy does not prove user-site processing is disabled")
    if "sitecustomize" in sys.modules or "usercustomize" in sys.modules:
        raise ValueError("custom Python startup modules are outside the finite profile")
    if not sys.dont_write_bytecode or sys.pycache_prefix is not None:
        raise ValueError("Python bytecode-cache policy differs from the -B profile")
    if (
        sys.flags.isolated
        or sys.flags.ignore_environment
        or sys.flags.no_site
        or sys.flags.safe_path
        or sys.flags.optimize
    ):
        raise ValueError("interpreter flags differ from the fixed non-isolated -B command")
    meta_types = [type(item).__name__ for item in sys.meta_path]
    if meta_types != ["type", "type", "type"] or [
        getattr(item, "__name__", None) for item in sys.meta_path
    ] != ["BuiltinImporter", "FrozenImporter", "PathFinder"]:
        raise ValueError("Python meta_path contains an unsupported finder")
    hook_names = []
    for hook in sys.path_hooks:
        _check_deadline(deadline_qpc, frequency)
        module_name = getattr(hook, "__module__", "")
        qualname = getattr(hook, "__qualname__", getattr(hook, "__name__", ""))
        hook_names.append((module_name, qualname))
    allowed_hooks = {
        ("zipimport", "zipimporter"),
        (
            "_frozen_importlib_external",
            "FileFinder.path_hook.<locals>.path_hook_for_FileFinder",
        ),
    }
    if any(item not in allowed_hooks for item in hook_names):
        raise ValueError("Python path_hooks contains an unsupported finder hook")
    _check_deadline(deadline_qpc, frequency)
    return {
        "pythonVersion": sys.version,
        "sysPath": actual_paths,
        "metaPathTypes": meta_types,
        "pathHooks": hook_names,
        "environment": observed_environment,
        "userSiteEnabled": False,
        "bytecodeWritesDisabled": sys.dont_write_bytecode,
    }


def _loaded_windows_modules(deadline_qpc: int, frequency: int) -> list[str]:
    _check_deadline(deadline_qpc, frequency)
    if os.name != "nt":
        raise OSError("build-3 runtime preflight requires Windows module identity APIs")
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    enum_modules = psapi.EnumProcessModules
    enum_modules.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.HMODULE),
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    enum_modules.restype = wintypes.BOOL
    module_name = psapi.GetModuleFileNameExW
    module_name.argtypes = [wintypes.HANDLE, wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    module_name.restype = wintypes.DWORD
    get_current = kernel.GetCurrentProcess
    get_current.argtypes = []
    get_current.restype = wintypes.HANDLE
    process = get_current()
    capacity = 256
    for _attempt in range(8):
        _check_deadline(deadline_qpc, frequency)
        modules = (wintypes.HMODULE * capacity)()
        needed = wintypes.DWORD()
        if not enum_modules(process, modules, ctypes.sizeof(modules), ctypes.byref(needed)):
            raise ctypes.WinError(ctypes.get_last_error())
        count = needed.value // ctypes.sizeof(wintypes.HMODULE)
        if count <= capacity:
            break
        if count > 65536:
            raise RuntimeError("loaded native-module census exceeded fixed bound")
        capacity = count + 32
    else:
        raise RuntimeError("loaded native-module census exceeded eight bounded attempts")
    paths = set()
    for module in modules[:count]:
        _check_deadline(deadline_qpc, frequency)
        buffer = ctypes.create_unicode_buffer(32768)
        if not module_name(process, module, buffer, len(buffer)):
            raise ctypes.WinError(ctypes.get_last_error())
        paths.add(str(Path(buffer.value).resolve(strict=True)))
    return sorted(paths, key=str.casefold)


def _actual_identity(
    numpy: Any, shapely: Any, pyproj: Any, deadline_qpc: int, frequency: int
) -> dict[str, Any]:
    _check_deadline(deadline_qpc, frequency)
    base_executable = Path(getattr(sys, "_base_executable", sys.executable)).resolve(strict=True)
    pyvenv = (PIPELINE / ".venv/pyvenv.cfg").read_text(encoding="utf-8")
    _check_deadline(deadline_qpc, frequency)
    interpreter_sha = _sha256(
        Path(sys.executable).resolve(strict=True),
        deadline_qpc=deadline_qpc,
        frequency=frequency,
    )
    base_sha = _sha256(base_executable, deadline_qpc=deadline_qpc, frequency=frequency)
    _check_deadline(deadline_qpc, frequency)
    return {
        "pythonVersion": sys.version,
        "pythonImplementation": platform.python_implementation(),
        "resolvedExecutable": str(Path(sys.executable).resolve(strict=True)),
        "baseExecutable": str(base_executable),
        "interpreterSha256": interpreter_sha,
        "baseInterpreterSha256": base_sha,
        "pyvenvCfgSha256": hashlib.sha256(pyvenv.encode("utf-8")).hexdigest(),
        "numpyVersion": numpy.__version__,
        "shapelyVersion": importlib.metadata.version("shapely"),
        "geosVersion": shapely.geos_version_string,
        "pyprojVersion": pyproj.__version__,
        "projVersion": pyproj.proj_version_str,
        "environment": {key: os.environ.get(key) for key in ENVIRONMENT_KEYS},
    }


def _census_loaded_files(
    repository: dict[str, dict[str, Any]],
    external: dict[str, dict[str, Any]],
    deadline_qpc: int,
    frequency: int,
    *,
    strict_bindings: bool,
) -> dict[str, Any]:
    paths: dict[str, str] = {}
    cache_metadata: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    archive_backed_modules: list[dict[str, str]] = []
    deadline_reached = False
    for name, module in tuple(sys.modules.items()):
        try:
            _check_deadline(deadline_qpc, frequency)
        except TimeoutError:
            deadline_reached = True
            break
        source = getattr(module, "__file__", None)
        loader = getattr(module, "__loader__", None)
        loader_module = type(loader).__module__ if loader is not None else ""
        archive_path = getattr(loader, "archive", None) if loader_module == "zipimport" else None
        source_text = str(source) if source else ""
        archive_markers = (".zip/", ".egg/", ".whl/", ".zip\\", ".egg\\", ".whl\\", "!")
        folded_source = source_text.casefold()
        archive_marker = next(
            (marker for marker in archive_markers if marker in folded_source), None
        )
        if archive_path or archive_marker:
            evidence = {
                "module": name,
                "archive": str(archive_path or source_text.split("!", 1)[0]),
                "member": source_text,
                "loader": f"{loader_module}.{type(loader).__name__}" if loader else "path",
            }
            archive_backed_modules.append(evidence)
            message = f"archive-backed module import is unsupported: {name}: {evidence['member']}"
            errors.append({"path": evidence["archive"], "error": message})
            if strict_bindings:
                raise ValueError(message)
        if source:
            if not (archive_path or archive_marker):
                try:
                    source_path = Path(source).resolve(strict=True)
                    if source_path.is_file():
                        paths[str(source_path)] = f"python-module:{name}:__file__"
                except OSError as exc:
                    errors.append({"path": str(source), "error": f"{type(exc).__name__}: {exc}"})
        cached = getattr(module, "__cached__", None)
        if cached:
            if any(marker in str(cached).casefold() for marker in archive_markers):
                evidence = {
                    "module": name,
                    "archive": str(cached),
                    "member": str(cached),
                    "loader": "cached-path",
                }
                archive_backed_modules.append(evidence)
                message = f"archive-backed bytecode cache is unsupported: {name}: {cached}"
                errors.append({"path": str(cached), "error": message})
                if strict_bindings:
                    raise ValueError(message)
                continue
            cache_path = Path(cached).resolve(strict=False)
            if cache_path.is_file():
                paths[str(cache_path)] = f"python-module:{name}:existing-bytecode-cache"
                cache_metadata.append({"module": name, "path": str(cache_path), "exists": True})
            else:
                cache_metadata.append({"module": name, "path": str(cache_path), "exists": False})
        if not strict_bindings:
            _COLLECTION_PROGRESS["cacheMetadata"] = cache_metadata
    if not deadline_reached:
        try:
            for path in _loaded_windows_modules(deadline_qpc, frequency):
                paths.setdefault(path, "loaded-native-module")
        except Exception as exc:
            deadline_reached = isinstance(exc, TimeoutError)
            errors.append(
                {"path": "loaded-native-modules", "error": f"{type(exc).__name__}: {exc}"}
            )
            if strict_bindings:
                raise
    output = []
    for absolute, role in sorted(paths.items(), key=lambda item: item[0].casefold()):
        try:
            _check_deadline(deadline_qpc, frequency)
        except TimeoutError:
            deadline_reached = True
            break
        path = Path(absolute)
        try:
            relative = path.relative_to(ROOT).as_posix()
        except ValueError:
            relative = None
        binding = repository.get(relative) if relative is not None else external.get(absolute)
        if binding is None and strict_bindings:
            raise ValueError(f"loaded module/file is not in frozen runtime closure: {absolute}")
        try:
            byte_length = path.stat().st_size
            digest = _sha256(path, deadline_qpc=deadline_qpc, frequency=frequency)
        except (OSError, TimeoutError) as exc:
            errors.append({"path": absolute, "error": f"{type(exc).__name__}: {exc}"})
            if strict_bindings:
                raise
            if isinstance(exc, TimeoutError):
                deadline_reached = True
                break
            continue
        binding_status = "unfrozen"
        if binding is not None:
            if (byte_length, digest) != (binding.get("byteLength"), binding.get("sha256")):
                raise ValueError(f"loaded module/file differs from frozen identity: {absolute}")
            binding_status = "matched"
        output.append(
            {
                "path": absolute,
                "role": role,
                "byteLength": byte_length,
                "sha256": digest,
                "category": (
                    binding.get("category", "repository" if relative is not None else "external")
                    if binding
                    else "observed-unfrozen"
                ),
                "bindingStatus": binding_status,
            }
        )
        if not strict_bindings:
            _COLLECTION_PROGRESS["loadedRuntimeFiles"] = output
    return {
        "files": output,
        "cacheMetadata": cache_metadata,
        "absentCacheCount": sum(not item["exists"] for item in cache_metadata),
        "observationErrors": errors,
        "archiveBackedModules": archive_backed_modules,
        "complete": not errors and not deadline_reached and len(output) == len(paths),
        "deadlineReached": deadline_reached,
        "observedPathCount": len(paths),
        "hashedPathCount": len(output),
    }


def _proposed_dependency_data_inventory(deadline_qpc: int, frequency: int) -> dict[str, Any]:
    distributions = []
    data_files = []
    errors = []
    observed: dict[str, dict[str, Any]] = {}
    deadline_reached = False
    approved = [Path(sys.prefix).resolve(strict=True), Path(sys.base_prefix).resolve(strict=True)]

    def add_error(
        stage: str, name: str | None, root: str | None, path: str | None, exc: Any
    ) -> None:
        row = {
            "stage": stage,
            "distribution": name,
            "root": root,
            "path": path,
            "reason": f"{type(exc).__name__}: {exc}"
            if isinstance(exc, BaseException)
            else str(exc),
        }
        errors.append(row)
        if name is not None:
            for item in distributions:
                if item["name"] == name and item["root"] == root:
                    item["proposalComplete"] = False
                    break
        _COLLECTION_PROGRESS["proposedDependencyDataInventory"] = {
            "distributions": distributions,
            "proposedDependencyDataFiles": list(observed.values()),
            "errors": errors.copy(),
            "complete": False,
            "deadlineReached": deadline_reached,
            "proposedOnly": True,
        }

    def inside_approved(path: Path) -> bool:
        return any(path == base or path.is_relative_to(base) for base in approved)

    def is_reparse(path: Path, stat_result: os.stat_result | None = None) -> bool:
        info = stat_result if stat_result is not None else path.lstat()
        return path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & 0x400)

    def check_ancestors(path: Path) -> None:
        _check_deadline(deadline_qpc, frequency)
        current = Path(path.anchor)
        for part in path.parts[1:]:
            _check_deadline(deadline_qpc, frequency)
            current = current / part
            if is_reparse(current):
                raise ValueError(f"required path traverses a reparse point: {current}")

    def observe_file(
        path: Path,
        name: str,
        root_text: str,
        source: str,
        declaration: str | None = None,
    ) -> None:
        nonlocal deadline_reached
        _check_deadline(deadline_qpc, frequency)
        try:
            if is_reparse(path):
                raise ValueError("required file is a reparse point")
            check_ancestors(path)
            canonical = path.resolve(strict=True)
            if canonical != path or not inside_approved(canonical):
                raise ValueError(
                    "required file is noncanonical or outside approved installed roots"
                )
            key = str(canonical)
            attribution = {"distribution": name, "source": source}
            if declaration is not None:
                attribution["declaredPath"] = declaration
            if key in observed:
                current = canonical.stat()
                previous = observed[key]
                if (current.st_size, current.st_mtime_ns) != (
                    previous["byteLength"],
                    previous["observedMtimeNs"],
                ):
                    raise ValueError("previously observed duplicate file changed during inventory")
                if attribution not in previous["attributions"]:
                    previous["attributions"].append(attribution)
                return
            before = canonical.stat()
            if not canonical.is_file():
                raise ValueError("required inventory entry is not a regular file")
            digest = _sha256(canonical, deadline_qpc=deadline_qpc, frequency=frequency)
            _check_deadline(deadline_qpc, frequency)
            after = canonical.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError("required file changed during observation")
            observed[key] = {
                "path": key,
                "byteLength": before.st_size,
                "observedMtimeNs": before.st_mtime_ns,
                "sha256": digest,
                "attributions": [attribution],
                "exists": True,
                "proposedOnly": True,
            }
            _COLLECTION_PROGRESS["proposedDependencyDataInventory"] = {
                "distributions": distributions,
                "proposedDependencyDataFiles": list(observed.values()),
                "errors": errors.copy(),
                "complete": False,
                "deadlineReached": False,
                "proposedOnly": True,
            }
        except TimeoutError as exc:
            deadline_reached = True
            add_error("file-observation", name, root_text, declaration or str(path), exc)
            raise
        except Exception as exc:
            detail = f"{exc}; normalized path={path}" if declaration is not None else exc
            add_error(
                "file-observation",
                name,
                root_text,
                declaration or str(path),
                detail,
            )

    _COLLECTION_PROGRESS["proposedDependencyDataInventory"] = {
        "distributions": distributions,
        "proposedDependencyDataFiles": [],
        "errors": errors,
        "complete": False,
        "deadlineReached": False,
        "proposedOnly": True,
    }
    try:
        discovered = importlib.metadata.distributions()
        iterator = iter(discovered)
    except Exception as exc:
        add_error("distribution-discovery", None, None, None, exc)
        iterator = iter(())
    while True:
        try:
            _check_deadline(deadline_qpc, frequency)
            distribution = next(iterator)
        except StopIteration:
            break
        except TimeoutError as exc:
            deadline_reached = True
            add_error("distribution-discovery", None, None, None, exc)
            break
        except Exception as exc:
            add_error("distribution-discovery", None, None, None, exc)
            break
        name = "unknown"
        root_text = None
        row: dict[str, Any] = {
            "name": name,
            "version": None,
            "root": None,
            "declaredFileCountExpected": None,
            "declaredFileCountObserved": 0,
            "treeFileCountObserved": 0,
            "proposalComplete": False,
        }
        distributions.append(row)
        distribution_error_start = len(errors)
        _COLLECTION_PROGRESS["proposedDependencyDataInventory"] = {
            "distributions": distributions,
            "proposedDependencyDataFiles": list(observed.values()),
            "errors": errors.copy(),
            "complete": False,
            "deadlineReached": False,
            "proposedOnly": True,
        }
        try:
            _check_deadline(deadline_qpc, frequency)
            name = str(distribution.metadata.get("Name") or "unknown")
            row["name"] = name
            row["version"] = distribution.version
            root = Path(distribution.locate_file("")).resolve(strict=True)
            root_text = str(root)
            row["root"] = root_text
            if not root.is_dir() or not inside_approved(root):
                raise ValueError("distribution root is absent or outside approved installed roots")
            file_items = distribution.files
            if file_items is None:
                raise ValueError("distribution metadata file inventory is unavailable (None)")
            try:
                row["declaredFileCountExpected"] = len(file_items)
            except TypeError:
                row["declaredFileCountExpected"] = None
            top_levels: set[str] = set()
            data_roots: set[Path] = set()
            try:
                declared_iterator = iter(file_items)
                for entry in declared_iterator:
                    _check_deadline(deadline_qpc, frequency)
                    declared_path = str(entry)
                    try:
                        windows_path = PureWindowsPath(declared_path)
                        components = declared_path.split("/")
                        if (
                            not declared_path
                            or "\\" in declared_path
                            or ":" in declared_path
                            or windows_path.is_absolute()
                            or windows_path.drive
                            or any(component in ("", ".") for component in components)
                        ):
                            raise ValueError(
                                "distribution RECORD path is rooted or malformed: "
                                f"{declared_path!r}"
                            )
                        relative = Path(*components)
                        normalized = Path(os.path.abspath(root / relative))
                        check_ancestors(normalized)
                        if not inside_approved(normalized):
                            raise ValueError(
                                f"distribution RECORD path escapes approved roots: {declared_path}"
                            )
                        resolved = normalized.resolve(strict=True)
                        if resolved != normalized:
                            raise ValueError(
                                f"distribution RECORD path is redirected: {declared_path}"
                            )
                        if normalized.is_relative_to(root):
                            owned_relative = normalized.relative_to(root)
                            if not owned_relative.parts:
                                raise ValueError("distribution RECORD path has no owned component")
                            first_component = owned_relative.parts[0]
                            if first_component in (".", "..") or not first_component:
                                raise ValueError(
                                    "distribution RECORD path has unsafe tree anchor: "
                                    f"{declared_path}"
                                )
                            if first_component.endswith(".data"):
                                data_roots.add(root / first_component)
                            elif not first_component.endswith((".dist-info", ".egg-info")):
                                top_levels.add(first_component)
                    except TimeoutError as exc:
                        deadline_reached = True
                        add_error(
                            "declared-path-normalization", name, root_text, declared_path, exc
                        )
                        raise
                    except Exception as exc:
                        add_error(
                            "declared-path-normalization", name, root_text, declared_path, exc
                        )
                        raise
                    row["declaredFileCountObserved"] += 1
                    observe_file(
                        normalized,
                        name,
                        root_text,
                        "declared-metadata",
                        declaration=declared_path,
                    )
            except TimeoutError:
                raise
            except Exception as exc:
                add_error("distribution-metadata-iteration", name, root_text, None, exc)
                raise
            if row["declaredFileCountObserved"] == 0:
                raise ValueError("installed distribution metadata has an empty file inventory")
            if (
                row["declaredFileCountExpected"] is not None
                and row["declaredFileCountObserved"] != row["declaredFileCountExpected"]
            ):
                raise ValueError("distribution metadata iteration did not match its declared count")
            _check_deadline(deadline_qpc, frequency)
            top_level_text = distribution.read_text("top_level.txt")
            _check_deadline(deadline_qpc, frequency)
            if top_level_text is not None:
                if not top_level_text.strip():
                    raise ValueError("present top_level.txt is empty")
                for hint in top_level_text.splitlines():
                    _check_deadline(deadline_qpc, frequency)
                    hint = hint.strip()
                    if not hint:
                        continue
                    if hint in (".", "..") or "/" in hint or "\\" in hint or ":" in hint:
                        raise ValueError(f"top_level.txt contains an unsafe component: {hint!r}")
                    hinted_dir = root / hint
                    hinted_module = root / f"{hint}.py"
                    if hinted_dir.is_dir():
                        top_levels.add(hint)
                    elif hinted_module.is_file():
                        top_levels.add(hint)
                    else:
                        raise ValueError(f"top_level.txt contradicts installed paths: {hint}")

            # Enumerate package and native-sibling trees independently of metadata.
            tree_roots: set[Path] = set()
            for top_level in top_levels:
                candidate = root / top_level
                module_file = root / f"{top_level}.py"
                if candidate.exists():
                    tree_roots.add(candidate)
                elif module_file.exists():
                    tree_roots.add(module_file)
                else:
                    raise FileNotFoundError(
                        f"distribution-owned top-level module path is absent: {top_level}"
                    )
                sibling = root / f"{top_level}.libs"
                if sibling.exists():
                    tree_roots.add(sibling)
            tree_roots.update(data_roots)
            metadata_location = getattr(distribution, "_path", None)
            if metadata_location is None:
                raise ValueError("distribution metadata tree location is unavailable")
            metadata_tree = Path(metadata_location)
            if not metadata_tree.exists():
                raise FileNotFoundError(f"distribution metadata tree is absent: {metadata_tree}")
            check_ancestors(metadata_tree)
            metadata_tree = metadata_tree.resolve(strict=True)
            if not inside_approved(metadata_tree):
                raise ValueError("distribution metadata tree escapes approved installed roots")
            tree_roots.add(metadata_tree)
            normalized_name = name.casefold().replace("-", "_")
            required_packages = {
                "numpy": ("numpy", "numpy.libs"),
                "shapely": ("shapely", "shapely.libs"),
                "pyproj": ("pyproj", "pyproj.libs"),
            }
            if normalized_name in required_packages:
                for required_tree in required_packages[normalized_name]:
                    required_path = root / required_tree
                    if not required_path.is_dir():
                        raise FileNotFoundError(
                            f"required installed package/native tree is absent: {required_path}"
                        )
                    top_levels.add(required_tree.removesuffix(".libs"))
                    tree_roots.add(required_path)
            if normalized_name == "pyproj":
                proj_tree = root / "pyproj" / "proj_dir" / "share" / "proj"
                if not proj_tree.is_dir():
                    raise FileNotFoundError(f"required PROJ data tree is absent: {proj_tree}")
                tree_roots.add(proj_tree)
            if not tree_roots:
                raise ValueError("distribution has no discoverable installed package/native tree")
            ordered_tree_roots = sorted(
                tree_roots, key=lambda item: (len(item.parts), str(item).casefold())
            )
            pruned_tree_roots: list[Path] = []
            for candidate_tree in ordered_tree_roots:
                if not any(candidate_tree.is_relative_to(parent) for parent in pruned_tree_roots):
                    pruned_tree_roots.append(candidate_tree)
            for tree_root in pruned_tree_roots:
                _check_deadline(deadline_qpc, frequency)
                check_ancestors(tree_root)
                if is_reparse(tree_root):
                    raise ValueError(f"required package tree is a reparse point: {tree_root}")
                resolved_tree = tree_root.resolve(strict=True)
                if resolved_tree != tree_root or not inside_approved(resolved_tree):
                    raise ValueError(
                        f"required package tree is not a canonical approved directory: {tree_root}"
                    )
                if resolved_tree.is_file():
                    row["treeFileCountObserved"] += 1
                    observe_file(resolved_tree, name, root_text, "independent-package-tree")
                    continue
                if not resolved_tree.is_dir():
                    raise ValueError(
                        f"required package tree is not a directory or file: {tree_root}"
                    )
                pending = [resolved_tree]
                while pending:
                    _check_deadline(deadline_qpc, frequency)
                    directory = pending.pop()
                    with os.scandir(directory) as entries:
                        for entry in entries:
                            _check_deadline(deadline_qpc, frequency)
                            item_path = Path(entry.path)
                            info = entry.stat(follow_symlinks=False)
                            if entry.is_symlink() or bool(
                                getattr(info, "st_file_attributes", 0) & 0x400
                            ):
                                raise ValueError(
                                    f"package tree contains a reparse entry: {item_path}"
                                )
                            if entry.is_dir(follow_symlinks=False):
                                pending.append(item_path)
                            elif entry.is_file(follow_symlinks=False):
                                row["treeFileCountObserved"] += 1
                                observe_file(item_path, name, root_text, "independent-package-tree")
                            else:
                                raise ValueError(f"unsupported package tree entry: {item_path}")
            row["proposalComplete"] = len(errors) == distribution_error_start
        except TimeoutError as exc:
            deadline_reached = True
            row["proposalComplete"] = False
            add_error("distribution-inventory", name, root_text, None, exc)
            break
        except Exception as exc:
            row["proposalComplete"] = False
            add_error("distribution-inventory", name, root_text, None, exc)
    final_deadline_ok = True
    try:
        _check_deadline(deadline_qpc, frequency)
    except TimeoutError as exc:
        final_deadline_ok = False
        deadline_reached = True
        add_error("completion-check", None, None, None, exc)
    complete = (
        final_deadline_ok
        and not deadline_reached
        and bool(distributions)
        and not errors
        and all(item["proposalComplete"] for item in distributions)
    )
    data_files = list(observed.values())
    for item in data_files:
        item["attributions"].sort(key=lambda row: (row["distribution"].casefold(), row["source"]))
    result = {
        "distributions": distributions,
        "proposedDependencyDataFiles": data_files,
        "errors": errors,
        "complete": complete,
        "deadlineReached": deadline_reached,
        "distributionCountObserved": len(distributions),
        "uniqueFileCountObserved": len(data_files),
        "proposedOnly": True,
    }
    _COLLECTION_PROGRESS["proposedDependencyDataInventory"] = result
    return result


def _collection_roots(deadline_qpc: int, frequency: int) -> list[dict[str, str]]:
    _check_deadline(deadline_qpc, frequency)
    roots = {
        str(Path(sys.prefix).resolve(strict=True)): "venv-runtime",
        str(Path(sys.base_prefix).resolve(strict=True)): "base-python-runtime",
        str(ROOT.resolve(strict=True)): "repository",
    }
    _check_deadline(deadline_qpc, frequency)
    windows_root = os.environ.get("SystemRoot")
    if windows_root:
        path = Path(windows_root).resolve(strict=True)
        roots[str(path)] = "windows-system-runtime"
    _check_deadline(deadline_qpc, frequency)
    return [{"path": path, "category": category} for path, category in sorted(roots.items())]


def _path_under_allowed_roots(
    path: str, roots: list[dict[str, str]], deadline_qpc: int, frequency: int
) -> bool:
    _check_deadline(deadline_qpc, frequency)
    candidate = Path(path).resolve(strict=True)
    for item in roots:
        _check_deadline(deadline_qpc, frequency)
        allowed = Path(item["path"])
        if candidate == allowed or candidate.is_relative_to(allowed):
            return True
    return False


def run_preflight(mode: str, dispatch_auth: dict[str, Any] | None = None) -> dict[str, Any]:
    if mode not in ("build-dispatch", "standalone"):
        raise ValueError("preflight mode is not fixed")
    if (
        not isinstance(dispatch_auth, dict)
        or dispatch_auth.get("mode") != mode
        or dispatch_auth.get("oneUse") is not True
        or not isinstance(dispatch_auth.get("dispatchNonce"), str)
    ):
        raise ValueError("preflight mode lacks its one-use parent authorization")
    deadline_qpc, frequency, _deadline = _deadline_from_auth(dispatch_auth)
    purpose = dispatch_auth.get("purpose") if mode == "standalone" else "build-dispatch"
    repository: dict[str, dict[str, Any]] = {}
    external: dict[str, dict[str, Any]] = {}
    frozen_record: dict[str, Any] | None = None
    if purpose != "collect-unreserved-runtime-identity":
        repository, external, frozen_record = _prevalidate_frozen_closure(
            mode, dispatch_auth, deadline_qpc, frequency
        )
    expected_environment = (
        frozen_record.get("identity", {}).get("environment") if frozen_record is not None else None
    )
    startup_profile_before_insert = _assert_python_startup_profile(
        deadline_qpc,
        frequency,
        pipeline_inserted=False,
        expected_environment=expected_environment,
    )
    _check_deadline(deadline_qpc, frequency)
    sys.path.insert(0, str(PIPELINE))
    startup_profile_before_imports = _assert_python_startup_profile(
        deadline_qpc,
        frequency,
        pipeline_inserted=True,
        expected_environment=expected_environment,
    )
    import numpy
    import pyproj
    import shapely

    for module_name in REQUIRED_IMPORTS:
        _check_deadline(deadline_qpc, frequency)
        __import__(module_name)
    startup_profile_after_imports = _assert_python_startup_profile(
        deadline_qpc,
        frequency,
        pipeline_inserted=True,
        expected_environment=expected_environment,
    )
    actual = _actual_identity(numpy, shapely, pyproj, deadline_qpc, frequency)
    if purpose == "collect-unreserved-runtime-identity":
        _COLLECTION_PROGRESS.update({"phase": "imports-complete", "runtimeIdentity": actual})
        try:
            loaded = _census_loaded_files({}, {}, deadline_qpc, frequency, strict_bindings=False)
        except Exception as exc:
            loaded = {
                "files": _COLLECTION_PROGRESS.get("loadedRuntimeFiles", []),
                "cacheMetadata": _COLLECTION_PROGRESS.get("cacheMetadata", []),
                "absentCacheCount": 0,
                "observationErrors": [
                    {"path": "loaded-runtime-census", "error": f"{type(exc).__name__}: {exc}"}
                ],
                "complete": False,
                "deadlineReached": isinstance(exc, TimeoutError),
                "observedPathCount": None,
                "hashedPathCount": len(_COLLECTION_PROGRESS.get("loadedRuntimeFiles", [])),
            }
        _COLLECTION_PROGRESS.update(
            {
                "phase": "loaded-file-census-complete-or-partial",
                "loadedRuntimeFiles": loaded["files"],
                "cacheMetadata": loaded["cacheMetadata"],
                "runtimeObservationComplete": loaded["complete"],
            }
        )
        roots = _collection_roots(deadline_qpc, frequency)
        unexpected = []
        for item in loaded["files"]:
            _check_deadline(deadline_qpc, frequency)
            if not _path_under_allowed_roots(item["path"], roots, deadline_qpc, frequency):
                unexpected.append(item["path"])
        inventory = _proposed_dependency_data_inventory(deadline_qpc, frequency)
        _COLLECTION_PROGRESS["proposedDependencyDataInventory"] = inventory
        inventory_errors = [
            {
                "path": item.get("path") or item.get("root") or "distribution-inventory",
                "error": f"{item.get('stage')}: {item.get('reason')}",
            }
            for item in inventory["errors"]
        ]
        observation_errors = [*loaded["observationErrors"], *inventory_errors]
        observation_complete = loaded["complete"] and inventory["complete"] and not unexpected
        _COLLECTION_PROGRESS.update(
            {
                "runtimeObservationErrors": observation_errors,
                "runtimeObservationComplete": observation_complete,
            }
        )
        return {
            "schema": "teignmouth-build3-runtime-preflight-result-v1",
            "status": "RUNTIME_IDENTITY_COLLECTION_ONLY",
            "mode": mode,
            "purpose": purpose,
            "runtimeIdentity": actual,
            "runtimeIdentityMatches": None,
            "venvLauncherIdentity": {
                "path": dispatch_auth.get("launcherImagePath"),
                "sha256": dispatch_auth.get("launcherImageSha256"),
                "pid": dispatch_auth.get("launcherPid"),
                "creationFileTime": dispatch_auth.get("launcherCreationFileTime"),
            },
            "baseInterpreterIdentity": {
                "path": actual["baseExecutable"],
                "sha256": actual["baseInterpreterSha256"],
            },
            "loadedRuntimeFiles": loaded["files"],
            "loadedPythonFileCount": sum(
                row["role"].startswith("python-module:") for row in loaded["files"]
            ),
            "loadedNativeFileCount": sum(
                row["role"] == "loaded-native-module" for row in loaded["files"]
            ),
            "cacheMetadata": loaded["cacheMetadata"],
            "absentCacheCount": loaded["absentCacheCount"],
            "runtimeObservationComplete": observation_complete,
            "runtimeObservationErrors": observation_errors,
            "unexpectedLoadedRoots": unexpected,
            "proposedDependencyDataInventory": inventory,
            "proposedAllowedRoots": roots,
            "startupProfileObservation": {
                "beforePipelineInsert": startup_profile_before_insert,
                "beforeThirdPartyImports": startup_profile_before_imports,
                "afterImports": startup_profile_after_imports,
                "frozenProfileVerified": False,
            },
            "dispatchNonce": dispatch_auth["dispatchNonce"],
            "dispatchAuthorizationPassed": True,
            "reservedBuildSnapshotRequired": False,
            "candidateBuildExecuted": False,
            "gisGeometryLoaded": False,
            "servingEligible": False,
        }

    standalone = mode == "standalone"
    if frozen_record is None:
        raise RuntimeError("frozen pre-import validation did not produce an identity record")
    manifest_sha = _sha256(INPUT_MANIFEST, deadline_qpc=deadline_qpc, frequency=frequency)
    external_sha = _sha256(EXTERNAL_MANIFEST, deadline_qpc=deadline_qpc, frequency=frequency)
    identity_sha = _sha256(RUNTIME_IDENTITY, deadline_qpc=deadline_qpc, frequency=frequency)
    if (
        dispatch_auth.get("inputManifestSha256") != manifest_sha
        or dispatch_auth.get("externalRuntimeManifestSha256") != external_sha
        or dispatch_auth.get("runtimeIdentitySha256") != identity_sha
    ):
        raise ValueError("a frozen runtime control changed during third-party imports")
    if frozen_record.get("identity") != actual:
        raise ValueError("actual interpreter/package/runtime identity differs from frozen record")
    loaded = _census_loaded_files(
        repository, external, deadline_qpc, frequency, strict_bindings=True
    )
    if not loaded["complete"]:
        raise ValueError("loaded runtime closure observation is incomplete")
    post_repository, post_manifest_sha = _repository_bindings(
        deadline_qpc, frequency, standalone=standalone
    )
    post_external, post_external_sha = _external_bindings(deadline_qpc, frequency)
    post_identity_sha = _sha256(RUNTIME_IDENTITY, deadline_qpc=deadline_qpc, frequency=frequency)
    if (
        post_manifest_sha != manifest_sha
        or post_external_sha != external_sha
        or post_identity_sha != identity_sha
    ):
        raise ValueError("a frozen runtime input changed during preflight")
    return {
        "schema": "teignmouth-build3-runtime-preflight-result-v1",
        "status": "PASS_RUNTIME_IDENTITY_ONLY",
        "mode": mode,
        "purpose": purpose,
        "issueId": ISSUE,
        "inputManifestSha256": manifest_sha,
        "externalRuntimeManifestSha256": external_sha,
        "runtimeIdentitySha256": identity_sha,
        "runtimeIdentity": actual,
        "runtimeIdentityMatches": True,
        "startupProfileObservation": {
            "beforePipelineInsert": startup_profile_before_insert,
            "beforeThirdPartyImports": startup_profile_before_imports,
            "afterImports": startup_profile_after_imports,
            "frozenProfileVerified": True,
        },
        "repositoryBindingCount": len(post_repository),
        "externalRuntimeBindingCount": len(post_external),
        "loadedModuleFileCount": len(loaded["files"]),
        "loadedModuleFiles": loaded["files"],
        "cacheMetadata": loaded["cacheMetadata"],
        "absentCacheCount": loaded["absentCacheCount"],
        "dispatchNonce": dispatch_auth["dispatchNonce"],
        "dispatchAuthorizationPassed": True,
        "reservedBuildSnapshotRequired": not standalone,
        "candidateBuildExecuted": False,
        "gisGeometryLoaded": False,
        "servingEligible": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("build-dispatch", "standalone"), required=True)
    args = parser.parse_args(argv)
    dispatch_auth = None
    authorized_purpose = None
    result_path = (
        STANDALONE_EVIDENCE / "runtime-preflight-result.json"
        if args.mode == "standalone"
        else ROOT / RESULT_RELATIVE
    )
    try:
        if args.mode == "standalone":
            authorization = json.loads(STANDALONE_AUTH_CONSUMED.read_text(encoding="utf-8"))
            if (
                authorization.get("schema")
                != "teignmouth-build3-runtime-preflight-authorization-v2"
                or authorization.get("authorized") is not True
                or authorization.get("oneShot") is not True
                or authorization.get("purpose")
                not in (
                    "collect-unreserved-runtime-identity",
                    "verify-unreserved-runtime-identity",
                )
            ):
                raise ValueError(
                    "standalone runtime preflight lacks exact coordinator authorization"
                )
            authorized_purpose = authorization["purpose"]
            dispatch_auth = _consume_standalone_dispatch_authorization()
            deadline_qpc, frequency, _deadline = _deadline_from_auth(dispatch_auth)
            authorization_sha = _sha256(
                STANDALONE_AUTH_CONSUMED,
                deadline_qpc=deadline_qpc,
                frequency=frequency,
            )
        else:
            authorization_sha = None
            dispatch_auth = _consume_internal_authorization()
        result = run_preflight(args.mode, dispatch_auth)
        result["coordinatorAuthorizationSha256"] = authorization_sha
    except Exception as exc:
        result = {
            "schema": "teignmouth-build3-runtime-preflight-result-v1",
            "status": (
                "RUNTIME_IDENTITY_COLLECTION_ONLY"
                if authorized_purpose == "collect-unreserved-runtime-identity"
                else "BLOCKED_RUNTIME_PREFLIGHT"
            ),
            "mode": args.mode,
            "purpose": authorized_purpose,
            "runtimeIdentityMatches": None,
            "runtimeObservationComplete": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
            "traceback": traceback.format_exc(),
            "partialCollection": _COLLECTION_PROGRESS.copy() or None,
            "dispatchNonce": dispatch_auth.get("dispatchNonce") if dispatch_auth else None,
            "dispatchAuthorizationPassed": dispatch_auth is not None,
            "candidateBuildExecuted": False,
            "gisGeometryLoaded": False,
            "servingEligible": False,
        }
    _atomic_result(result_path, result)
    print(json.dumps({"status": result["status"], "result": str(result_path)}, sort_keys=True))
    return 0 if result["status"] == "PASS_RUNTIME_IDENTITY_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
