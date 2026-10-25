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
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any

PROTOCOL = "teignmouth-validation-process-v1"
MAX_BYTES = 64 * 1024 * 1024
MAX_ENVELOPE = 16 * 1024 * 1024
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


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def safe_file(directory: Path, name: str) -> Path:
    if not name or Path(name).name != name or "/" in name or "\\" in name or ":" in name:
        raise ProcessValidationError("transport file name is not a basename")
    path = directory / name
    from .road_surface import _assert_no_reparse_components

    _assert_no_reparse_components(path)
    return path


def read_bounded(path: Path, maximum: int) -> bytes:
    if path.stat().st_size > maximum:
        raise ProcessValidationError("transport file exceeds byte ceiling")
    with path.open("rb") as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ProcessValidationError("transport grew beyond byte ceiling")
    return data


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

    def blob(self, payload: bytes) -> dict[str, Any]:
        self.byte_count += len(payload)
        if self.byte_count > MAX_BYTES:
            raise ProcessValidationError("transport buffers exceed construction ceiling")
        name = f"{self.prefix}-{self.count:06d}.bin"
        self.count += 1
        with safe_file(self.directory, name).open("xb") as stream:
            stream.write(payload)
        return {"file": name, "bytes": len(payload), "sha256": digest(payload)}

    def unblob(self, record: dict[str, Any]) -> bytes:
        if set(record) != {"file", "bytes", "sha256"} or type(record["bytes"]) is not int:
            raise ProcessValidationError("malformed blob record")
        if record["bytes"] < 0 or not record["file"].startswith(self.prefix + "-"):
            raise ProcessValidationError("invalid blob ownership or length")
        self.byte_count += record["bytes"]
        if self.byte_count > MAX_BYTES:
            raise ProcessValidationError("transport buffers exceed construction ceiling")
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
            if self.byte_count + value.nbytes > MAX_BYTES:
                raise ProcessValidationError("array transport exceeds construction ceiling")
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


class WindowsJob:
    """Create suspended, contain before resume; close kills every descendant."""

    def __init__(self, argv: list[str], cwd: Path):
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

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
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
        self.process = None
        self.job = kernel.CreateJobObjectW(None, None)
        self.pid = None
        if not self.job:
            raise ProcessValidationError(f"CreateJobObject failed: {ctypes.get_last_error()}")
        process = Process()
        try:
            info = Extended()
            info.limits.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not kernel.SetInformationJobObject(
                self.job, 9, ctypes.byref(info), ctypes.sizeof(info)
            ):
                raise ProcessValidationError("cannot set kill-on-close Job policy")
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
            if not kernel.AssignProcessToJobObject(self.job, self.process):
                raise ProcessValidationError(f"Job assignment failed: {ctypes.get_last_error()}")
            if kernel.ResumeThread(process.thread) == 0xFFFFFFFF:
                raise ProcessValidationError("cannot resume contained worker")
        except BaseException:
            if self.process:
                kernel.TerminateProcess(self.process, 2)
                kernel.WaitForSingleObject(self.process, 1000)
            self.close()
            raise
        finally:
            if process.thread:
                kernel.CloseHandle(process.thread)

    def exited(self) -> bool:
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
        if self.job and not self.kernel.TerminateJobObject(self.job, 2):
            raise ProcessValidationError("Job termination failed")

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
        encoder = Codec(scratch, "request")
        encoded = encoder.encode(request)
        invocation = uuid.uuid4().hex
        envelope = {"protocol": PROTOCOL, "invocation": invocation, "request": encoded}
        payload = canonical(envelope)
        if len(payload) > MAX_ENVELOPE or 2 * encoder.byte_count + len(payload) > MAX_BYTES:
            raise ProcessValidationError("request transfer exceeds construction ceiling")
        safe_file(scratch, "request.json").write_bytes(payload)
        if clock() >= deadline:
            raise ProcessValidationError("validation cutoff during request transfer")
        worker = root / "pipeline/scripts/run_teignmouth_validation_worker_v1.py"
        job = backend([sys.executable, "-B", str(worker), "--scratch", str(scratch)], root)
        exited = False
        if wait_worker(job, deadline, clock=clock) != 0:
            raise ProcessValidationError("validation worker failed")
        exited = True
        output = read_bounded(safe_file(scratch, "result.json"), MAX_ENVELOPE)
        result = json.loads(output)
        if (
            set(result) != {"protocol", "invocation", "requestSha256", "response"}
            or result["protocol"] != PROTOCOL
            or result["invocation"] != invocation
            or result["requestSha256"] != digest(payload)
        ):
            raise ProcessValidationError("worker response binding mismatch")
        decoder = Codec(scratch, "result")
        response = decoder.decode(result["response"])
        verify_response(request, response)
        transfer_peak = 2 * encoder.byte_count + 2 * decoder.byte_count + len(payload) + len(output)
        resource = response.get("resources")
        base_peak = resource["peakConstructionBufferBytes"] if resource else 0
        if base_peak + transfer_peak > MAX_BYTES:
            raise ProcessValidationError(
                "combined validation/transfer construction ceiling exceeded"
            )
        response["processTransport"] = {
            "protocol": PROTOCOL,
            "invocation": invocation,
            "requestSha256": digest(payload),
            "transferPeakBytes": transfer_peak,
            "constructionPeakIncludingTransferBytes": base_peak + transfer_peak,
        }
        if clock() >= deadline:
            raise ProcessValidationError("validation cutoff during parent verification")
        completed = True
        return response
    finally:
        if job is not None:
            try:
                job.terminate()  # Includes descendants even after the leader exited.
                while not job.empty() and clock() < finalization_deadline:
                    time.sleep(0.005)
                exited = job.exited() and job.empty()
                if not exited:
                    raise ProcessValidationError(
                        f"worker exit unconfirmed; scratch retained: {scratch}"
                    )
            finally:
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
        resources = runner["_resource_report"](
            surface.mesh, report["roadPathReclip"], first, second
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
            hashes=hashes,
            operations=list(OPERATIONS),
        )
    return response


def worker_main(root: Path, scratch: Path) -> int:
    payload = read_bounded(safe_file(scratch, "request.json"), MAX_ENVELOPE)
    envelope = json.loads(payload)
    if set(envelope) != {"protocol", "invocation", "request"} or envelope["protocol"] != PROTOCOL:
        raise ProcessValidationError("invalid worker request envelope")
    request = Codec(scratch, "request").decode(envelope["request"])
    response = execute_transaction(request, root=root)
    result = {
        "protocol": PROTOCOL,
        "invocation": envelope["invocation"],
        "requestSha256": digest(payload),
        "response": Codec(scratch, "result").encode(response),
    }
    output = canonical(result)
    if len(output) > MAX_ENVELOPE:
        raise ProcessValidationError("result envelope exceeds byte ceiling")
    temporary = safe_file(scratch, "result-writing.json")
    with temporary.open("xb") as stream:
        stream.write(output)
        stream.flush()
        os.fsync(stream.fileno())
    os.rename(temporary, safe_file(scratch, "result.json"))
    return 0
