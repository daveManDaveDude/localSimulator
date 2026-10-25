"""Fixed offline validation transport and Windows Job containment.

No pickle, shell, trial dispatcher or caller-selected callable crosses this
boundary. The parent owns both absolute deadlines and all acceptance decisions.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

PROTOCOL = "teignmouth-validation-process-v2"
OPERATIONS = (
    "offline-gates",
    "independent-assembly",
    "first-asset-validation",
    "second-asset-validation",
    "resources",
    "deterministic-hashes",
)


class ProcessValidationError(ValueError):
    """Containment, protocol, deadline or cleanup failed; never accept a result."""


UNCONFIRMED_JOBS: dict[int, Any] = {}


class ProcessStartupError(ProcessValidationError):
    """Carry the owned process/Job even when construction cannot finish."""

    def __init__(self, job: Any, cause: BaseException):
        self.job = job
        super().__init__(f"worker startup failed, pid={job.pid}: {cause}")


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False, ensure_ascii=True
    ).encode()


def json_string_bound(value: str) -> int:
    """Bound an ASCII-escaped JSON string without creating its encoded buffer.

    Quotes cost two bytes. Each BMP code point (including a lone surrogate) uses
    at most one six-byte escape; each supplementary code point uses two. The
    bound deliberately also reserves six bytes for ordinary ASCII characters.
    """
    return 2 + sum(12 if ord(character) > 0xFFFF else 6 for character in value)


def validate_byte_count(byte_count: int) -> None:
    """Validate byte accounting without imposing a fixed construction ceiling."""
    if type(byte_count) is not int or byte_count < 0:
        raise ProcessValidationError("invalid construction/transfer byte accounting")


def value_bound(value: Any, *, check=None) -> tuple[int, int]:
    """Conservative binary/envelope bounds, without serializing any buffer.

    JSON strings reserve six bytes per BMP code point and twelve per non-BMP
    code point; containers reserve their tag, punctuation and field names.
    Polygon WKB size is counted from ring lengths.
    These are allocation bounds, not a claim about Python/GEOS process RSS.
    """
    import numpy as np
    from shapely.geometry import Polygon
    from shapely.strtree import STRtree

    if check is None:
        check = validate_byte_count
    if isinstance(value, np.ndarray):
        return value.nbytes, 512
    if isinstance(value, bytes):
        return len(value), 256
    if isinstance(value, Polygon):
        coordinates = len(value.exterior.coords) + sum(len(r.coords) for r in value.interiors)
        return 9 + 4 * (1 + len(value.interiors)) + 16 * coordinates, 256
    if isinstance(value, STRtree):
        return 0, 32
    if isinstance(value, Path):
        return 0, 64 + json_string_bound(str(value))
    if value is None or isinstance(value, (bool, np.bool_)):
        return 0, 8
    if isinstance(value, (int, np.integer)):
        return 0, len(str(value)) + 2
    if isinstance(value, (float, np.floating)):
        return 0, 64
    if isinstance(value, str):
        return 0, json_string_bound(value)
    if is_dataclass(value) and type(value).__name__ in Codec.classes():
        binary, metadata = 0, 512
        for field in fields(value):
            b, m = value_bound(getattr(value, field.name), check=check)
            binary, metadata = binary + b, metadata + m + json_string_bound(field.name) + 8
        return binary, metadata
    if isinstance(value, dict):
        values = (item for pair in value.items() for item in pair)
    elif isinstance(value, (list, tuple)):
        values = iter(value)
    else:
        raise ProcessValidationError("unapproved preflight value type")
    binary, metadata = 0, 64
    for item in values:
        b, m = value_bound(item, check=check)
        binary, metadata = binary + b, metadata + m + 8
        check(binary + metadata)
    return binary, metadata


def encoded_binary_bound(node: Any) -> int:
    """Read sidecar lengths without opening or decoding any sidecar."""
    if isinstance(node, dict):
        if node.get("tag") in ("array", "bytes", "wkb"):
            length = node["blob"]["bytes"]
            validate_byte_count(length)
            return length
        result = sum(encoded_binary_bound(v) for v in node.values())
    elif isinstance(node, list):
        result = sum(encoded_binary_bound(v) for v in node)
    else:
        result = 0
    validate_byte_count(result)
    return result


def encoded_file_manifest(node: Any) -> list[dict[str, Any]]:
    """Return the exact typed sidecar records embedded in an encoded graph."""
    records: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("tag") in ("array", "bytes", "wkb"):
                record = value.get("blob")
                if (
                    not isinstance(record, dict)
                    or set(record) != {"file", "bytes", "sha256"}
                    or not isinstance(record.get("file"), str)
                    or type(record.get("bytes")) is not int
                    or record["bytes"] < 0
                    or not isinstance(record.get("sha256"), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
                ):
                    raise ProcessValidationError("malformed exact sidecar manifest record")
                records.append(dict(record))
                return
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(node)
    records.sort(key=lambda item: item["file"])
    if len({record["file"] for record in records}) != len(records):
        raise ProcessValidationError("duplicate sidecar filename in exact manifest")
    return records


def safe_file(directory: Path, name: str) -> Path:
    if not name or Path(name).name != name or "/" in name or "\\" in name or ":" in name:
        raise ProcessValidationError("transport file name is not a basename")
    path = directory / name
    from .road_surface import _assert_no_reparse_components

    _assert_no_reparse_components(path)
    return path


def read_bounded(path: Path, expected_length: int) -> bytes:
    """Read one exact, caller-bound length; the host Job supplies the resource ceiling."""
    if type(expected_length) is not int or expected_length < 0:
        raise ProcessValidationError("invalid exact transport length")
    if path.stat().st_size != expected_length:
        raise ProcessValidationError("transport file length differs from its exact binding")
    with path.open("rb") as stream:
        data = stream.read(expected_length + 1)
    if len(data) != expected_length:
        raise ProcessValidationError("transport changed during exact-length read")
    return data


def write_exclusive(path: Path, payload: bytes) -> None:
    """Write one immutable protocol file and flush its contents to disk."""
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def read_json_exact(path: Path) -> tuple[bytes, Any]:
    """Read a complete JSON file and reject non-canonical or duplicate-key input."""
    length = path.stat().st_size
    payload = read_bounded(path, length)

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ProcessValidationError("duplicate JSON object key")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ProcessValidationError(f"non-finite JSON constant: {value}")

    try:
        value = json.loads(payload, object_pairs_hook=pairs, parse_constant=reject_constant)
        if canonical(value) != payload:
            raise ProcessValidationError("protocol JSON is not canonical")
    except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError) as exc:
        if isinstance(exc, ProcessValidationError):
            raise
        raise ProcessValidationError(f"invalid protocol JSON: {exc}") from exc
    return payload, value


def validate_sidecar_records(records: Any, *, prefix: str) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        raise ProcessValidationError("sidecar manifest must be a list")
    checked: list[dict[str, Any]] = []
    for record in records:
        if (
            not isinstance(record, dict)
            or set(record) != {"file", "bytes", "sha256"}
            or not isinstance(record["file"], str)
            or not record["file"].startswith(prefix + "-")
            or type(record["bytes"]) is not int
            or record["bytes"] < 0
            or not isinstance(record["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
        ):
            raise ProcessValidationError("malformed sidecar manifest record")
        checked.append(dict(record))
    checked.sort(key=lambda item: item["file"])
    if len({record["file"] for record in checked}) != len(checked):
        raise ProcessValidationError("duplicate sidecar filename in exact manifest")
    return checked


def assert_exact_files(directory: Path, expected: set[str]) -> None:
    actual: set[str] = set()
    for entry in directory.iterdir():
        safe_file(directory, entry.name)
        if entry.is_symlink() or not entry.is_file():
            raise ProcessValidationError("transport directory contains a non-regular file")
        actual.add(entry.name)
    if actual != expected:
        raise ProcessValidationError(
            f"transport directory file set mismatch; missing={sorted(expected - actual)}, "
            f"unexpected={sorted(actual - expected)}"
        )


def verify_sidecar_files(directory: Path, records: list[dict[str, Any]]) -> None:
    """Check exact sidecar lengths and SHA-256 values using bounded streaming reads."""
    for record in records:
        path = safe_file(directory, record["file"])
        if not path.is_file() or path.stat().st_size != record["bytes"]:
            raise ProcessValidationError("sidecar length differs from exact manifest")
        hasher = hashlib.sha256()
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                hasher.update(chunk)
        if hasher.hexdigest() != record["sha256"]:
            raise ProcessValidationError("sidecar hash differs from exact manifest")


def manifest_envelope(
    *,
    protocol: str,
    invocation: str,
    payload: bytes,
    files: list[dict[str, Any]],
    request_sha256: str | None = None,
) -> dict[str, Any]:
    manifest = {
        "schema": "teignmouth-process-envelope-manifest-v2",
        "protocol": protocol,
        "invocation": invocation,
        "envelopeBytes": len(payload),
        "envelopeSha256": digest(payload),
        "files": files,
    }
    if request_sha256 is not None:
        manifest["requestSha256"] = request_sha256
    return manifest


class Codec:
    """Allowlisted value graph plus hash-bound canonical array/blob sidecars.

    Geometry indexes are reconstructed from the exact ordered WKB polygons;
    Python/GEOS cache identity never crosses the boundary.
    """

    def __init__(self, directory: Path, prefix: str):
        self.directory = directory
        self.prefix = prefix
        self.byte_count = 0
        self.count = 0
        self.file_records: list[dict[str, Any]] = []

    def blob(self, payload: bytes) -> dict[str, Any]:
        self.byte_count += len(payload)
        validate_byte_count(self.byte_count)
        name = f"{self.prefix}-{self.count:06d}.bin"
        self.count += 1
        with safe_file(self.directory, name).open("xb") as stream:
            stream.write(payload)
        record = {"file": name, "bytes": len(payload), "sha256": digest(payload)}
        self.file_records.append(record)
        return record

    def unblob(self, record: dict[str, Any]) -> bytes:
        if set(record) != {"file", "bytes", "sha256"} or type(record["bytes"]) is not int:
            raise ProcessValidationError("malformed blob record")
        if record["bytes"] < 0 or not record["file"].startswith(self.prefix + "-"):
            raise ProcessValidationError("invalid blob ownership or length")
        self.byte_count += record["bytes"]
        validate_byte_count(self.byte_count)
        payload = read_bounded(safe_file(self.directory, record["file"]), record["bytes"])
        if len(payload) != record["bytes"] or digest(payload) != record["sha256"]:
            raise ProcessValidationError("blob identity mismatch")
        return payload

    @staticmethod
    def classes() -> dict[str, type]:
        from .road_surface import ReleaseInputs
        from .road_surface_patch import CompositeSurface, PatchBounds, PatchMesh

        return {
            item.__name__: item
            for item in (ReleaseInputs, CompositeSurface, PatchBounds, PatchMesh)
        }

    def encode(self, value: Any) -> Any:
        import numpy as np
        from shapely.geometry.base import BaseGeometry
        from shapely.strtree import STRtree

        if value is None or type(value) in (bool, int, str):
            return value
        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, (float, np.floating)):
            if not math.isfinite(value):
                raise ProcessValidationError("nonfinite transport scalar")
            return float(value)
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.ndarray):
            if value.dtype.kind not in "fiu" or value.dtype.itemsize not in (1, 2, 4, 8):
                raise ProcessValidationError("unsupported array dtype")
            if not np.isfinite(value).all():
                raise ProcessValidationError("nonfinite transport array")
            array = np.asarray(value, dtype=value.dtype.newbyteorder("<"), order="C")
            return {
                "tag": "array",
                "dtype": array.dtype.str,
                "shape": list(array.shape),
                "blob": self.blob(array.tobytes()),
            }
        if isinstance(value, bytes):
            return {"tag": "bytes", "blob": self.blob(value)}
        if isinstance(value, Path):
            return {"tag": "path", "value": str(value)}
        if isinstance(value, BaseGeometry):
            return {"tag": "wkb", "blob": self.blob(value.wkb)}
        if isinstance(value, STRtree):
            return {"tag": "tree"}
        if is_dataclass(value) and type(value).__name__ in self.classes():
            return {
                "tag": "record",
                "class": type(value).__name__,
                "fields": {
                    field.name: self.encode(getattr(value, field.name)) for field in fields(value)
                },
            }
        if isinstance(value, dict):
            return {
                "tag": "dict",
                "items": [[self.encode(key), self.encode(item)] for key, item in value.items()],
            }
        if isinstance(value, (tuple, list)):
            return {
                "tag": "tuple" if isinstance(value, tuple) else "list",
                "items": [self.encode(item) for item in value],
            }
        raise ProcessValidationError(f"unsupported transport type: {type(value).__name__}")

    def decode(self, value: Any) -> Any:
        import numpy as np
        import shapely
        from shapely.strtree import STRtree

        if value is None or type(value) in (bool, int, str):
            return value
        if type(value) is float and math.isfinite(value):
            return value
        if not isinstance(value, dict):
            raise ProcessValidationError("invalid transport node")
        tag = value.get("tag")
        if tag in ("array", "bytes", "wkb"):
            payload = self.unblob(value["blob"])
            if tag == "bytes":
                return payload
            if tag == "wkb":
                return shapely.from_wkb(payload)
            if value["dtype"] not in (
                "<f4",
                "<f8",
                "<i2",
                "<i4",
                "<i8",
                "<u2",
                "<u4",
                "<u8",
                "|i1",
                "|u1",
            ):
                raise ProcessValidationError("unapproved canonical dtype")
            shape = value["shape"]
            if (
                not isinstance(shape, list)
                or len(shape) > 3
                or any(type(n) is not int or n < 0 for n in shape)
            ):
                raise ProcessValidationError("invalid array shape")
            dtype = np.dtype(value["dtype"])
            if math.prod(shape) * dtype.itemsize != len(payload):
                raise ProcessValidationError("array shape/byte length mismatch")
            result = np.frombuffer(payload, dtype=dtype).reshape(shape)
            if not np.isfinite(result).all():
                raise ProcessValidationError("nonfinite decoded array")
            return result
        if tag == "path":
            return Path(value["value"])
        if tag in ("list", "tuple"):
            result = [self.decode(item) for item in value["items"]]
            return tuple(result) if tag == "tuple" else result
        if tag == "dict":
            result = {}
            for key, item in value["items"]:
                key = self.decode(key)
                if key in result:
                    raise ProcessValidationError("duplicate transport dictionary key")
                result[key] = self.decode(item)
            return result
        if tag == "record":
            cls = self.classes().get(value.get("class"))
            if cls is None or set(value["fields"]) != {field.name for field in fields(cls)}:
                raise ProcessValidationError("unapproved record or field set")
            record = value["fields"]
            tree = cls.__name__ == "PatchMesh" and record["triangle_tree"] == {"tag": "tree"}
            kwargs = {
                name: self.decode(item)
                for name, item in record.items()
                if not (tree and name == "triangle_tree")
            }
            if tree:
                kwargs["triangle_tree"] = STRtree(kwargs["triangle_geometries"])
            return cls(**kwargs)
        raise ProcessValidationError("unapproved transport tag")


def process_in_named_job(
    process_handle: Any, job_name: str, expected_commit_limit: int | None = None
) -> bool:
    """Confirm membership and optional aggregate commit limit for a named Job."""
    if os.name != "nt" or not job_name:
        return False
    from ctypes import wintypes as w

    class Limits(ctypes.Structure):
        _fields_ = [
            ("process_time", ctypes.c_int64),
            ("job_time", ctypes.c_int64),
            ("flags", w.DWORD),
            ("min_ws", ctypes.c_size_t),
            ("max_ws", ctypes.c_size_t),
            ("active", w.DWORD),
            ("affinity", ctypes.c_size_t),
            ("priority", w.DWORD),
            ("scheduling", w.DWORD),
        ]

    class IO(ctypes.Structure):
        _fields_ = [
            (name, ctypes.c_uint64)
            for name in (
                "read_ops",
                "write_ops",
                "other_ops",
                "read_bytes",
                "write_bytes",
                "other_bytes",
            )
        ]

    class Extended(ctypes.Structure):
        _fields_ = [
            ("limits", Limits),
            ("io", IO),
            ("process_memory", ctypes.c_size_t),
            ("job_memory", ctypes.c_size_t),
            ("peak_process", ctypes.c_size_t),
            ("peak_job", ctypes.c_size_t),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenJobObjectW.argtypes = [w.DWORD, w.BOOL, w.LPCWSTR]
    kernel.OpenJobObjectW.restype = w.HANDLE
    kernel.IsProcessInJob.argtypes = [w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)]
    kernel.IsProcessInJob.restype = w.BOOL
    kernel.QueryInformationJobObject.argtypes = [
        w.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        w.DWORD,
        ctypes.c_void_p,
    ]
    kernel.QueryInformationJobObject.restype = w.BOOL
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.CloseHandle.restype = w.BOOL
    job = kernel.OpenJobObjectW(0x0004, False, job_name)  # JOB_OBJECT_QUERY
    if not job:
        return False
    try:
        membership = w.BOOL()
        info = Extended()
        if (
            not kernel.IsProcessInJob(process_handle, job, ctypes.byref(membership))
            or not membership.value
            or not kernel.QueryInformationJobObject(
                job, 9, ctypes.byref(info), ctypes.sizeof(info), None
            )
        ):
            return False
        required_flags = 0x2000 | (0x200 if expected_commit_limit is not None else 0)
        if (info.limits.flags & required_flags) != required_flags:
            return False
        if info.limits.flags & (0x800 | 0x1000):
            return False
        return expected_commit_limit is None or info.job_memory == expected_commit_limit
    finally:
        kernel.CloseHandle(job)


def current_process_job_admission(job_name: str, expected_commit_limit: int) -> bool:
    """Verify this process remains in the guardian's exact, queried memory Job."""
    if os.name != "nt":
        return False
    from ctypes import wintypes as w

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    return process_in_named_job(kernel.GetCurrentProcess(), job_name, expected_commit_limit)


def resource_report_without_construction_limit(
    runner: dict[str, Any],
    mesh: Any,
    clipped: dict[str, Any],
    first_assets: dict[str, bytes],
    second_assets: dict[str, bytes],
) -> dict[str, Any]:
    """Apply every frozen resource gate except the retired 64 MiB estimate cap.

    The construction figure remains in the report as an observation. The
    aggregate Windows Job, not a predicted Python/GEOS buffer formula, contains
    actual committed memory for the v2 run.
    """
    report = runner["_resource_report"](mesh, clipped, first_assets, second_assets)
    report["peakConstructionBufferByteLimit"] = None
    report["passes"] = bool(
        report["replacementTriangleCount"] <= runner["PATCH_MAX_TRIANGLES"]
        and report["replacementVertexCount"] <= runner["PATCH_MAX_VERTICES"]
        and report["addedDrawCalls"] <= 4
        and report["runtimeAssetBytes"] <= runner["PATCH_MAX_ASSET_BYTES"]
        and report["manifestBytes"] <= runner["PATCH_MAX_MANIFEST_BYTES"]
        and report["qaBytes"] <= runner["PATCH_MAX_QA_BYTES"]
        and report["addedResidentGeometryBytes"] <= runner["PATCH_MAX_RESIDENT_GEOMETRY_BYTES"]
    )
    return report


class WindowsJob:
    """Create suspended, contain before resume; close kills every descendant."""

    def __init__(
        self,
        argv: list[str],
        cwd: Path,
        *,
        finalization_deadline: float,
        clock=time.monotonic,
        commit_limit_bytes: int | None = None,
        job_name: str | None = None,
    ):
        if os.name != "nt":
            raise ProcessValidationError("Windows Job containment is required")
        from ctypes import wintypes as w

        class Startup(ctypes.Structure):
            _fields_ = [
                ("cb", w.DWORD),
                ("reserved", w.LPWSTR),
                ("desktop", w.LPWSTR),
                ("title", w.LPWSTR),
                ("x", w.DWORD),
                ("y", w.DWORD),
                ("xs", w.DWORD),
                ("ys", w.DWORD),
                ("xc", w.DWORD),
                ("yc", w.DWORD),
                ("fill", w.DWORD),
                ("flags", w.DWORD),
                ("show", w.WORD),
                ("reserved2", w.WORD),
                ("bytes", ctypes.POINTER(ctypes.c_ubyte)),
                ("stdin", w.HANDLE),
                ("stdout", w.HANDLE),
                ("stderr", w.HANDLE),
            ]

        class Process(ctypes.Structure):
            _fields_ = [
                ("process", w.HANDLE),
                ("thread", w.HANDLE),
                ("pid", w.DWORD),
                ("tid", w.DWORD),
            ]

        class Limits(ctypes.Structure):
            _fields_ = [
                ("process_time", ctypes.c_int64),
                ("job_time", ctypes.c_int64),
                ("flags", w.DWORD),
                ("min_ws", ctypes.c_size_t),
                ("max_ws", ctypes.c_size_t),
                ("active", w.DWORD),
                ("affinity", ctypes.c_size_t),
                ("priority", w.DWORD),
                ("scheduling", w.DWORD),
            ]

        class IO(ctypes.Structure):
            _fields_ = [
                (name, ctypes.c_uint64)
                for name in (
                    "read_ops",
                    "write_ops",
                    "other_ops",
                    "read_bytes",
                    "write_bytes",
                    "other_bytes",
                )
            ]

        class Extended(ctypes.Structure):
            _fields_ = [
                ("limits", Limits),
                ("io", IO),
                ("process_memory", ctypes.c_size_t),
                ("job_memory", ctypes.c_size_t),
                ("peak_process", ctypes.c_size_t),
                ("peak_job", ctypes.c_size_t),
            ]

        if commit_limit_bytes is not None and (
            type(commit_limit_bytes) is not int or commit_limit_bytes <= 0
        ):
            raise ProcessValidationError("invalid operational Job commit limit")
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "IsProcessInJob": ([w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)], w.BOOL),
            "CreateJobObjectW": ([ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
            "OpenJobObjectW": ([w.DWORD, w.BOOL, w.LPCWSTR], w.HANDLE),
            "SetInformationJobObject": ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
            "CreateProcessW": (
                [
                    w.LPCWSTR,
                    w.LPWSTR,
                    ctypes.c_void_p,
                    ctypes.c_void_p,
                    w.BOOL,
                    w.DWORD,
                    ctypes.c_void_p,
                    w.LPCWSTR,
                    ctypes.POINTER(Startup),
                    ctypes.POINTER(Process),
                ],
                w.BOOL,
            ),
            "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
            "ResumeThread": ([w.HANDLE], w.DWORD),
            "TerminateJobObject": ([w.HANDLE, w.UINT], w.BOOL),
            "TerminateProcess": ([w.HANDLE, w.UINT], w.BOOL),
            "WaitForSingleObject": ([w.HANDLE, w.DWORD], w.DWORD),
            "GetExitCodeProcess": ([w.HANDLE, ctypes.POINTER(w.DWORD)], w.BOOL),
            "CloseHandle": ([w.HANDLE], w.BOOL),
            "QueryInformationJobObject": (
                [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p],
                w.BOOL,
            ),
        }
        for name, (args, result) in signatures.items():
            getattr(kernel, name).argtypes = args
            getattr(kernel, name).restype = result
        self.kernel = kernel
        self.extended_type = Extended
        self.process = None
        self.assigned = False
        self.job_name = job_name
        self.job = kernel.CreateJobObjectW(None, job_name)
        self.pid = None
        if not self.job:
            raise ProcessValidationError(f"CreateJobObject failed: {ctypes.get_last_error()}")
        process = Process()
        try:
            if clock() >= finalization_deadline:
                raise ProcessValidationError("startup finalization deadline reached")
            info = Extended()
            info.limits.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not kernel.SetInformationJobObject(
                self.job, 9, ctypes.byref(info), ctypes.sizeof(info)
            ):
                raise ProcessValidationError("cannot set kill-on-close Job policy")
            if commit_limit_bytes is not None:
                info.limits.flags |= 0x200  # JOB_OBJECT_LIMIT_JOB_MEMORY
                info.job_memory = commit_limit_bytes
                if not kernel.SetInformationJobObject(
                    self.job, 9, ctypes.byref(info), ctypes.sizeof(info)
                ):
                    raise ProcessValidationError("cannot set operational Job commit limit")
            queried = Extended()
            if not kernel.QueryInformationJobObject(
                self.job, 9, ctypes.byref(queried), ctypes.sizeof(queried), None
            ):
                raise ProcessValidationError("cannot query operational Job limits")
            if queried.limits.flags & (0x800 | 0x1000):
                raise ProcessValidationError("Job breakaway must be disabled")
            if not queried.limits.flags & 0x2000 or (
                commit_limit_bytes is not None
                and (not queried.limits.flags & 0x200 or queried.job_memory != commit_limit_bytes)
            ):
                raise ProcessValidationError(
                    f"queried Job limit differs from admitted limit: flags={queried.limits.flags}, "
                    f"actual={queried.job_memory}, expected={commit_limit_bytes}"
                )
            self.admission_evidence = {
                "jobCommitLimitBytes": int(queried.job_memory),
                "killOnClose": True,
                "breakawayDisabled": True,
                "limitQueried": True,
                "jobName": job_name,
            }
            startup = Startup()
            startup.cb = ctypes.sizeof(startup)
            startup.flags = 1  # STARTF_USESHOWWINDOW; SW_HIDE is zero
            command = ctypes.create_unicode_buffer(subprocess.list2cmdline(argv))
            if not kernel.CreateProcessW(
                argv[0],
                command,
                None,
                None,
                False,
                0x08000004,
                None,
                str(cwd),
                ctypes.byref(startup),
                ctypes.byref(process),
            ):
                raise ProcessValidationError(
                    f"suspended CreateProcess failed: {ctypes.get_last_error()}"
                )
            self.process, self.pid = process.process, process.pid
            UNCONFIRMED_JOBS[self.pid] = self
            if not kernel.AssignProcessToJobObject(self.job, self.process):
                raise ProcessValidationError(f"Job assignment failed: {ctypes.get_last_error()}")
            self.assigned = True
            membership = w.BOOL()
            if (
                not kernel.IsProcessInJob(self.process, self.job, ctypes.byref(membership))
                or not membership.value
            ):
                raise ProcessValidationError("cannot confirm suspended child Job membership")
            self.admission_evidence["membershipBeforeResume"] = True
            outer_job_name = os.environ.get("TVW_TEIGNMOUTH_OUTER_JOB_NAME")
            if outer_job_name and outer_job_name != job_name:
                try:
                    outer_limit = int(os.environ["TVW_TEIGNMOUTH_OUTER_JOB_COMMIT_LIMIT"])
                except (KeyError, ValueError) as exc:
                    raise ProcessValidationError(
                        "expected outer Job limit binding is missing"
                    ) from exc
                if not process_in_named_job(self.process, outer_job_name, outer_limit):
                    raise ProcessValidationError(
                        "nested worker is not in the expected outer memory Job"
                    )
                self.admission_evidence["outerMembershipBeforeResume"] = True
            if clock() >= finalization_deadline:
                raise ProcessValidationError("startup finalization deadline before resume")
            if kernel.ResumeThread(process.thread) == 0xFFFFFFFF:
                raise ProcessValidationError("cannot resume contained worker")
        except BaseException as exc:
            # Supervisor/probe receives ownership before it attempts termination.
            # Never discard the only process handle or pretend no child exists.
            raise ProcessStartupError(self, exc) from exc
        finally:
            if process.thread:
                kernel.CloseHandle(process.thread)

    def memory_observation(self) -> dict[str, int]:
        """Observed committed-memory high water, never a future allocation proof."""
        info = self.extended_type()
        if not self.kernel.QueryInformationJobObject(
            self.job, 9, ctypes.byref(info), ctypes.sizeof(info), None
        ):
            raise ProcessValidationError("cannot query Job memory observation")
        return {
            "peakJobCommitBytes": int(info.peak_job),
            "peakProcessCommitBytes": int(info.peak_process),
        }

    def exited(self) -> bool:
        if not self.process:
            return True
        result = self.kernel.WaitForSingleObject(self.process, 0)
        if result not in (0, 258):
            raise ProcessValidationError("worker wait failed")
        return result == 0

    def exit_code(self) -> int:
        from ctypes import wintypes

        code = wintypes.DWORD()
        if not self.kernel.GetExitCodeProcess(self.process, ctypes.byref(code)):
            raise ProcessValidationError("cannot obtain worker exit status")
        return code.value

    def terminate(self) -> None:
        if self.process and not self.assigned and not self.exited():
            if not self.kernel.TerminateProcess(self.process, 2) and not self.exited():
                raise ProcessValidationError(f"TerminateProcess failed: {ctypes.get_last_error()}")
        if self.job and not self.kernel.TerminateJobObject(self.job, 2):
            raise ProcessValidationError("Job termination failed")

    def wait_exit(self, deadline: float, *, clock=time.monotonic) -> bool:
        """Wait no longer than the remaining fixed finalization budget."""
        if self.process:
            milliseconds = max(0, min(0xFFFFFFFE, math.floor((deadline - clock()) * 1000)))
            outcome = self.kernel.WaitForSingleObject(self.process, milliseconds)
            if outcome == 258:
                return False
            if outcome != 0:
                raise ProcessValidationError(
                    f"cleanup wait failed: {outcome}, API error={ctypes.get_last_error()}"
                )
        while not self.empty() and clock() < deadline:
            time.sleep(min(0.005, max(0, deadline - clock())))
        return self.exited() and self.empty()

    def empty(self) -> bool:
        class Accounting(ctypes.Structure):
            _fields_ = [
                ("user", ctypes.c_int64),
                ("kernel", ctypes.c_int64),
                ("period_user", ctypes.c_int64),
                ("period_kernel", ctypes.c_int64),
                ("faults", ctypes.c_uint32),
                ("total", ctypes.c_uint32),
                ("active", ctypes.c_uint32),
                ("terminated", ctypes.c_uint32),
            ]

        accounting = Accounting()
        if not self.kernel.QueryInformationJobObject(
            self.job, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None
        ):
            raise ProcessValidationError("cannot confirm Job descendant exit")
        return accounting.active == 0

    def close(self) -> None:
        # Only verified empty Jobs may be closed explicitly during cleanup.
        # Unconfirmed Jobs retain strong tracking and both handles.
        if not self.exited() or not self.empty():
            raise ProcessValidationError("refusing to discard unconfirmed worker ownership")
        if self.pid is not None:
            UNCONFIRMED_JOBS.pop(self.pid, None)
        if self.job:
            self.kernel.CloseHandle(self.job)
            self.job = None
        if self.process:
            self.kernel.CloseHandle(self.process)
            self.process = None


def wait_worker(job: Any, deadline: float, *, clock=time.monotonic, pause=time.sleep) -> int:
    while not job.exited():
        remaining = deadline - clock()
        if remaining <= 0:
            raise ProcessValidationError("validation process deadline reached")
        pause(min(0.01, remaining))
    if clock() >= deadline:
        raise ProcessValidationError("worker result arrived after validation cutoff")
    return job.exit_code()


def supervise(
    root: Path,
    request: dict[str, Any],
    *,
    deadline: float,
    finalization_deadline: float,
    clock=time.monotonic,
    backend=WindowsJob,
) -> dict[str, Any]:
    """Own request/scratch lifecycle and reject every late or incomplete result."""
    if clock() >= deadline:
        raise ProcessValidationError("validation cutoff before worker launch")
    scratch = Path(tempfile.mkdtemp(prefix="teignmouth-validation-"))
    owned_scratch = scratch.resolve(strict=True)
    job = None
    exited = True
    completed = False
    try:
        request_binary, request_metadata = value_bound(request)
        request_metadata += 1024  # Outer request envelope and fixed memory record.
        baseline = 3 * request_binary + 4 * request_metadata
        validate_byte_count(baseline)
        encoder = Codec(scratch, "request")
        encoded = encoder.encode(request)
        invocation = uuid.uuid4().hex
        envelope = {
            "protocol": PROTOCOL,
            "invocation": invocation,
            "request": encoded,
            "memory": {"baselineBytes": baseline},
        }
        payload = canonical(envelope)
        request_files = validate_sidecar_records(encoder.file_records, prefix="request")
        if request_files != encoded_file_manifest(encoded):
            raise ProcessValidationError("encoded request sidecars differ from codec writes")
        request_manifest = manifest_envelope(
            protocol=PROTOCOL,
            invocation=invocation,
            payload=payload,
            files=request_files,
        )
        request_manifest_payload = canonical(request_manifest)
        write_exclusive(safe_file(scratch, "request.json"), payload)
        write_exclusive(safe_file(scratch, "request.manifest.json"), request_manifest_payload)
        verify_sidecar_files(scratch, request_files)
        assert_exact_files(
            scratch,
            {"request.json", "request.manifest.json"}
            | {record["file"] for record in request_files},
        )
        if clock() >= deadline:
            raise ProcessValidationError("validation cutoff during request transfer")
        worker = root / "pipeline/scripts/run_teignmouth_validation_worker_v1.py"
        try:
            job = backend(
                [sys.executable, "-B", str(worker), "--scratch", str(scratch)],
                root,
                finalization_deadline=finalization_deadline,
                clock=clock,
            )
        except ProcessStartupError as exc:
            job, exited = exc.job, False
            raise
        exited = False
        if wait_worker(job, deadline, clock=clock) != 0:
            raise ProcessValidationError("validation worker failed")
        exited = True
        verify_sidecar_files(
            scratch,
            [
                {"file": "request.json", "bytes": len(payload), "sha256": digest(payload)},
                {
                    "file": "request.manifest.json",
                    "bytes": len(request_manifest_payload),
                    "sha256": digest(request_manifest_payload),
                },
            ]
            + request_files,
        )
        result_manifest_payload, result_manifest = read_json_exact(
            safe_file(scratch, "result.manifest.json")
        )
        if (
            not isinstance(result_manifest, dict)
            or set(result_manifest)
            != {
                "schema",
                "protocol",
                "invocation",
                "envelopeBytes",
                "envelopeSha256",
                "files",
                "requestSha256",
            }
            or result_manifest["schema"] != "teignmouth-process-envelope-manifest-v2"
            or result_manifest["protocol"] != PROTOCOL
            or result_manifest["invocation"] != invocation
            or result_manifest["requestSha256"] != digest(payload)
        ):
            raise ProcessValidationError("worker result manifest binding mismatch")
        result_length = result_manifest["envelopeBytes"]
        if type(result_length) is not int or result_length < 0:
            raise ProcessValidationError("invalid exact response envelope length")
        output_path = safe_file(scratch, "result.json")
        output = read_bounded(output_path, result_length)
        if digest(output) != result_manifest["envelopeSha256"]:
            raise ProcessValidationError("response envelope hash differs from exact manifest")
        result = json.loads(output)
        if canonical(result) != output:
            raise ProcessValidationError("response envelope is not canonical")
        if (
            set(result) != {"protocol", "invocation", "requestSha256", "response", "memory"}
            or result["protocol"] != PROTOCOL
            or result["invocation"] != invocation
            or result["requestSha256"] != digest(payload)
        ):
            raise ProcessValidationError("worker response binding mismatch")
        construction_peak = result["memory"]["constructionPeakBytes"]
        response_binary = encoded_binary_bound(result["response"])
        validate_byte_count(construction_peak)
        response_files = validate_sidecar_records(result_manifest["files"], prefix="result")
        if response_files != encoded_file_manifest(result["response"]):
            raise ProcessValidationError("response sidecars differ from exact manifest")
        verify_sidecar_files(scratch, request_files + response_files)
        assert_exact_files(
            scratch,
            {"request.json", "request.manifest.json", "result.json", "result.manifest.json"}
            | {record["file"] for record in request_files + response_files},
        )
        decoder = Codec(scratch, "result")
        response = decoder.decode(result["response"])
        if decoder.byte_count != response_binary:
            raise ProcessValidationError("response byte telemetry differs from decoded sidecars")
        verify_response(request, response)
        transfer_peak = 2 * encoder.byte_count + 2 * decoder.byte_count + len(payload) + len(output)
        resource = response.get("resources")
        base_peak = resource["peakConstructionBufferBytes"] if resource else 0
        if base_peak != construction_peak:
            raise ProcessValidationError("worker construction allocation plan mismatch")
        response["processTransport"] = {
            "protocol": PROTOCOL,
            "invocation": invocation,
            "requestSha256": digest(payload),
            "requestEnvelopeBytes": len(payload),
            "requestEnvelopeSha256": digest(payload),
            "requestFiles": request_files,
            "responseEnvelopeBytes": len(output),
            "responseEnvelopeSha256": digest(output),
            "responseFiles": response_files,
            "responseManifestSha256": digest(result_manifest_payload),
            "transferPeakBytes": transfer_peak,
            "constructionPeakIncludingTransferBytes": base_peak + transfer_peak,
        }
        if clock() >= deadline:
            raise ProcessValidationError("validation cutoff during parent verification")
        completed = True
        return response
    finally:
        if job is not None:
            exited = False
            job.terminate()  # Includes an unassigned suspended startup failure.
            exited = job.wait_exit(finalization_deadline, clock=clock)
            if not exited:
                raise ProcessValidationError(
                    f"worker exit unconfirmed, pid={job.pid}; scratch retained: {scratch}"
                )
            job.close()
        if exited:
            if scratch.resolve(strict=True) != owned_scratch or scratch.is_symlink():
                raise ProcessValidationError("scratch cleanup path identity changed")
            shutil.rmtree(scratch)
        if clock() >= finalization_deadline:
            raise ProcessValidationError("process cleanup exceeded finalization cutoff")
        if completed and clock() >= deadline:
            raise ProcessValidationError("process cleanup exceeded validation cutoff")


def verify_response(request: dict[str, Any], response: dict[str, Any]) -> None:
    from .road_surface_patch import PATCH_OFFLINE_GATE_NAMES, PATCH_OUTPUT_FILES

    if not isinstance(response, dict) or response.get("bindings") != request["bindings"]:
        raise ProcessValidationError("response provenance mismatch")
    report = response.get("report", {})
    if (
        report.get("gateNames") != list(PATCH_OFFLINE_GATE_NAMES)
        or report.get("candidateFloat32Sha256") != request["candidateSha256"]
    ):
        raise ProcessValidationError("response candidate or gate identity mismatch")
    if any(
        type(report.get(name, {}).get("passes")) is not bool for name in PATCH_OFFLINE_GATE_NAMES
    ):
        raise ProcessValidationError("response gate report incomplete")
    expected = list(OPERATIONS) if report.get("passes") is True else [OPERATIONS[0]]
    if response.get("operations") != expected:
        raise ProcessValidationError("response operations missing, reordered or duplicated")
    if report.get("passes") is True:
        if report.get("validationComplete") is not True or not all(
            report[name]["passes"] for name in PATCH_OFFLINE_GATE_NAMES
        ):
            raise ProcessValidationError("incomplete gate success")
        first, second = response["firstAssets"], response["secondAssets"]
        if first is second or first != second or set(first) != PATCH_OUTPUT_FILES:
            raise ProcessValidationError("independent assets are missing or unequal")
        hashes = {
            "first": {k: digest(v) for k, v in sorted(first.items())},
            "second": {k: digest(v) for k, v in sorted(second.items())},
        }
        if response["hashes"] != hashes:
            raise ProcessValidationError("independent asset hash mismatch")


def execute_transaction(request: dict[str, Any], *, root: Path) -> dict[str, Any]:
    """The sole production worker operation; all numerical functions are frozen."""
    import runpy

    import numpy as np
    import shapely

    from . import road_surface_patch as patch
    from .road_surface_validation_v2 import validate_offline_candidate_v2

    bindings = request["bindings"]
    wrapper = runpy.run_path(
        str(root / "pipeline/scripts/run_teignmouth_topology_validation_v2.py")
    )
    config_path = root / "config/road-surface-teignmouth-topology-transition-v2.json"
    config = wrapper["_read_config"](config_path)
    wrapper["_validate_static_bindings"](config)
    expected_runtime = {
        **wrapper["_runtime_code_hashes"](config, root),
        config_path.relative_to(root).as_posix(): digest(config_path.read_bytes()),
    }
    if bindings["runtimeHashes"] != expected_runtime:
        raise ProcessValidationError("worker runtime map differs from exact reviewed map")
    actual_environment = {
        "python": sys.version,
        "numpy": np.__version__,
        "shapely": shapely.__version__,
        "geos": shapely.geos_version_string,
    }
    if bindings["environment"] != actual_environment or bindings[
        "dataSourceManifestSha256"
    ] != digest((root / "data/source-manifest.json").read_bytes()):
        raise ProcessValidationError("worker source/environment identity mismatch")
    for relative, expected in bindings["runtimeHashes"].items():
        path = root / relative
        if (
            path.resolve().is_relative_to(root.resolve()) is False
            or digest(path.read_bytes()) != expected
        ):
            raise ProcessValidationError("worker runtime/config/spec binding changed")
    surface = request["surface"]
    if (
        digest(surface.patch_heights.astype("<f4", copy=False).tobytes())
        != request["candidateSha256"]
    ):
        raise ProcessValidationError("worker candidate identity mismatch")
    if (
        len(surface.mesh.vertices_xz) > patch.PATCH_MAX_VERTICES
        or len(surface.mesh.triangles) > patch.PATCH_MAX_TRIANGLES
    ):
        raise ProcessValidationError("worker mesh exceeds unchanged ceilings")
    report, context = validate_offline_candidate_v2(
        surface,
        request["influence"],
        request["constraints"],
        request["solver"],
        request["acceptedPreviewHashes"],
        validation_deadline_monotonic=request["deadline"],
    )
    response = {
        "bindings": bindings,
        "report": report,
        "operations": [OPERATIONS[0]],
        "gateSeconds": context.gate_seconds,
    }
    if report["passes"]:
        # Keep the former byte ledger as observational telemetry. The outer
        # Windows Job now contains actual process-tree commit instead.
        runner = runpy.run_path(str(root / "pipeline/scripts/run_teignmouth_topology_study.py"))
        working = (
            surface.mesh.vertices_xz.nbytes
            + surface.mesh.base_y.nbytes
            + surface.mesh.triangles.nbytes
            + runner["_array_buffer_bytes"](report["roadPathReclip"]["groups"])
        )
        report_binary, report_metadata = value_bound(response)
        first, second, deterministic = patch.assemble_deterministic_candidate_assets(
            surface, report["roadPathReclip"], report
        )
        first_validation = patch.validate_candidate_patch_assets(
            first, surface, request["candidateSha256"], report["roadPathReclip"]
        )
        second_validation = patch.validate_candidate_patch_assets(
            second, surface, request["candidateSha256"], report["roadPathReclip"]
        )
        runner = runpy.run_path(str(root / "pipeline/scripts/run_teignmouth_topology_study.py"))
        resources = resource_report_without_construction_limit(
            runner, surface.mesh, report["roadPathReclip"], first, second
        )
        hashes = {
            "first": {k: digest(v) for k, v in sorted(first.items())},
            "second": {k: digest(v) for k, v in sorted(second.items())},
        }
        response.update(
            firstAssets=first,
            secondAssets=second,
            deterministic=deterministic,
            firstValidation=first_validation,
            secondValidation=second_validation,
            resources=resources,
            memoryTelemetry={
                "requestBaselineEstimateBytes": request["_transportBaselineBytes"],
                "workingGeometryEstimateBytes": working,
                "assemblyOutputReserveEstimateBytes": 4 * patch.PATCH_MAX_ASSET_BYTES,
                "reportBinaryEstimateBytes": report_binary,
                "reportMetadataEstimateBytes": report_metadata,
            },
            hashes=hashes,
            operations=list(OPERATIONS),
        )
    return response


def worker_main(root: Path, scratch: Path) -> int:
    path = safe_file(scratch, "request.json")
    manifest_payload, manifest = read_json_exact(safe_file(scratch, "request.manifest.json"))
    del manifest_payload
    if (
        not isinstance(manifest, dict)
        or set(manifest)
        != {"schema", "protocol", "invocation", "envelopeBytes", "envelopeSha256", "files"}
        or manifest["schema"] != "teignmouth-process-envelope-manifest-v2"
        or manifest["protocol"] != PROTOCOL
        or not isinstance(manifest["invocation"], str)
        or not re.fullmatch(r"[0-9a-f]{32}", manifest["invocation"])
    ):
        raise ProcessValidationError("invalid request manifest")
    request_length = manifest["envelopeBytes"]
    if type(request_length) is not int or request_length < 0:
        raise ProcessValidationError("invalid exact request envelope length")
    payload = read_bounded(path, request_length)
    if digest(payload) != manifest["envelopeSha256"]:
        raise ProcessValidationError("request envelope hash differs from exact manifest")
    envelope = json.loads(payload)
    if canonical(envelope) != payload:
        raise ProcessValidationError("request envelope is not canonical")
    if (
        set(envelope) != {"protocol", "invocation", "request", "memory"}
        or envelope["protocol"] != PROTOCOL
        or envelope["invocation"] != manifest["invocation"]
    ):
        raise ProcessValidationError("invalid worker request envelope")
    request_files = validate_sidecar_records(manifest["files"], prefix="request")
    if request_files != encoded_file_manifest(envelope["request"]):
        raise ProcessValidationError("request sidecars differ from exact manifest")
    verify_sidecar_files(scratch, request_files)
    assert_exact_files(
        scratch,
        {"request.json", "request.manifest.json"} | {record["file"] for record in request_files},
    )
    request_binary = encoded_binary_bound(envelope["request"])
    baseline = envelope["memory"]["baselineBytes"]
    validate_byte_count(baseline)
    request_codec = Codec(scratch, "request")
    request = request_codec.decode(envelope["request"])
    if request_codec.byte_count != request_binary:
        raise ProcessValidationError("request byte telemetry differs from decoded sidecars")
    request["_transportBaselineBytes"] = baseline
    response = execute_transaction(request, root=root)
    result_binary, result_metadata = value_bound(response)
    construction_peak = response.get("resources", {}).get("peakConstructionBufferBytes", 0)
    validate_byte_count(construction_peak)
    result_codec = Codec(scratch, "result")
    result = {
        "protocol": PROTOCOL,
        "invocation": envelope["invocation"],
        "requestSha256": digest(payload),
        "response": result_codec.encode(response),
        "memory": {"constructionPeakBytes": construction_peak},
    }
    if result_codec.byte_count != result_binary:
        raise ProcessValidationError("response byte telemetry differs from encoded sidecars")
    output = canonical(result)
    response_files = validate_sidecar_records(result_codec.file_records, prefix="result")
    if response_files != encoded_file_manifest(result["response"]):
        raise ProcessValidationError("encoded response sidecars differ from codec writes")
    write_exclusive(safe_file(scratch, "result.json"), output)
    response_manifest = manifest_envelope(
        protocol=PROTOCOL,
        invocation=envelope["invocation"],
        payload=output,
        files=response_files,
        request_sha256=digest(payload),
    )
    write_exclusive(safe_file(scratch, "result.manifest.json"), canonical(response_manifest))
    verify_sidecar_files(scratch, request_files + response_files)
    assert_exact_files(
        scratch,
        {"request.json", "request.manifest.json", "result.json", "result.manifest.json"}
        | {record["file"] for record in request_files + response_files},
    )
    return 0
