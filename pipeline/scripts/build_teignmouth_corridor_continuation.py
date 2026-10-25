"""Run one reserved continuation build and persist failures before optional telemetry."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import traceback
from ctypes import wintypes
from pathlib import Path
from typing import Any


def peak_working_set_bytes() -> int | None:
    """Return Windows process peak RSS; None on unsupported platforms."""
    if os.name != "nt":
        return None

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.argtypes = ()
    get_info = psapi.GetProcessMemoryInfo
    get_info.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    )
    get_info.restype = wintypes.BOOL
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    if not get_info(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(counters.PeakWorkingSetSize)


def preservation_snapshot(root: Path) -> dict[str, str]:
    listing = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    paths = {root / item for item in listing.stdout.decode().split("\0") if item}
    paths.update(path for path in (root / "public/worlds").rglob("*") if path.is_file())
    snapshot: dict[str, str] = {}
    for path in sorted(paths):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in {
            ".codex/torquay-plan-implementation.md",
            "docs/milestones/artifacts/Teignmouth-corridor-prototype/continuation-1/attempt-ledger.json",
        }:
            continue
        if relative.startswith(
            "docs/milestones/artifacts/Teignmouth-corridor-prototype/continuation-1/sol-correction-1/build-6/"
        ):
            continue
        with path.open("rb") as stream:
            snapshot[relative] = hashlib.file_digest(stream, "sha256").hexdigest()
    return snapshot


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def ensure_pipeline_importable(root: Path) -> None:
    pipeline_path = str((root / "pipeline").resolve())
    if pipeline_path not in sys.path:
        sys.path.insert(0, pipeline_path)


def interpreter_identity(root: Path) -> dict[str, str]:
    expected = (root / "pipeline/.venv/Scripts/python.exe").resolve()
    actual = Path(sys.executable).resolve()
    if actual != expected:
        raise RuntimeError(
            f"continuation runner requires existing interpreter {expected}; got {actual}"
        )
    return {
        "executable": str(actual),
        "version": sys.version,
        "prefix": str(Path(sys.prefix).resolve()),
    }


def finalize_attempt_report(
    evidence: Path,
    report: dict[str, Any],
    before: dict[str, str],
    after: dict[str, str],
    primary_error: dict[str, str] | None,
    started: float,
    memory_reader=peak_working_set_bytes,
) -> dict[str, Any]:
    """Persist both snapshots and primary errors even when optional telemetry raises."""
    report["primaryError"] = primary_error
    report["resources"] = {
        "wallSeconds": time.perf_counter() - started,
        "wallLimitSeconds": 180,
        "candidateRuntimeBuffersWritten": False,
    }
    try:
        report["resources"]["peakWorkingSetBytes"] = memory_reader()
        report["resources"]["peakWorkingSetStatus"] = (
            "measured" if os.name == "nt" else "unavailable_on_non_windows"
        )
    except Exception as exc:
        report["resources"]["peakWorkingSetBytes"] = None
        report["resources"]["peakWorkingSetStatus"] = "unavailable"
        report["resources"]["peakWorkingSetError"] = f"{type(exc).__name__}: {exc}"
    try:
        write_json(evidence / "preservation-after.json", after)
    finally:
        write_json(evidence / "report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--import-smoke", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    identity = interpreter_identity(root)
    ensure_pipeline_importable(root)
    if args.import_smoke:
        import torquay_pipeline.teignmouth_corridor_continuation  # noqa: F401

        print("continuation pipeline import passed; no GIS data read")
        return 0
    if args.evidence is None:
        parser.error("--evidence is required unless --import-smoke is used")
    evidence = args.evidence.resolve()
    expected = root / Path(
        "docs/milestones/artifacts/Teignmouth-corridor-prototype/continuation-1/sol-correction-1/build-6"
    )
    if evidence != expected.resolve() or evidence.exists():
        raise ValueError("expected a fresh sol-correction-1/build-6 evidence directory")
    evidence.mkdir(parents=True)
    write_json(evidence / "interpreter-identity.json", identity)
    started = time.perf_counter()
    timer: threading.Timer | None = None

    def timeout() -> None:
        write_json(evidence / "timeout.json", {"status": "STOP", "reason": "180s build deadline"})
        os._exit(124)

    timer = threading.Timer(180.0, timeout)
    timer.daemon = True
    timer.start()
    report: dict[str, Any] = {"status": "STOP", "stopReasons": []}
    before: dict[str, str] = {}
    primary_error: dict[str, str] | None = None
    try:
        before = preservation_snapshot(root)
        write_json(evidence / "preservation-before.json", before)
        try:
            from torquay_pipeline.teignmouth_corridor_continuation import build_continuation

            report = build_continuation(root, evidence)
            report["interpreterIdentity"] = identity
        except Exception as exc:  # Preserve the primary failure and traceback.
            primary_error = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            report = {
                "status": "STOP",
                "stopReasons": [f"{type(exc).__name__}: {exc}"],
                "interpreterIdentity": identity,
            }
    except Exception as exc:
        primary_error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        report = {
            "status": "STOP",
            "stopReasons": [f"{type(exc).__name__}: {exc}"],
            "interpreterIdentity": identity,
        }
    finally:
        try:
            after = preservation_snapshot(root)
            changed = [name for name, digest in before.items() if after.get(name) != digest]
            report["preservation"] = {
                "passes": not changed,
                "comparedPaths": len(before),
                "changedPaths": changed,
                "rawDataHashing": "raw GIS excluded; packaged source hashes reported by loader",
                "excludedPaths": [
                    ".codex/torquay-plan-implementation.md",
                    "continuation-1/attempt-ledger.json",
                    "current owned sol-correction-1/build-6 output directory",
                ],
            }
            if changed:
                report["status"] = "STOP"
                report.setdefault("stopReasons", []).append("protected-byte change")
            report["additionalOfflineGates"] = {
                "roadDrapeAndOwnership": False,
                "completeBuildingContact": False,
                "sharedWalkSurface": False,
                "candidateEligibleForServing": False,
                "reason": "required coherence gates are not implemented and evidenced",
            }
            if report.get("status") == "GEOMETRY_READY":
                report["status"] = "STOP"
                report.setdefault("stopReasons", []).append(
                    "required road/building/walk gates unavailable"
                )
        except Exception as exc:
            report["status"] = "STOP"
            report.setdefault("stopReasons", []).append(
                f"preservation-after failure: {type(exc).__name__}: {exc}"
            )
            after = {}
        try:
            report = finalize_attempt_report(
                evidence, report, before, after, primary_error, started
            )
        finally:
            if timer:
                timer.cancel()
    print(
        json.dumps(
            {
                "status": report["status"],
                "stopReasons": report.get("stopReasons"),
                "primaryError": primary_error,
                "interpreterIdentity": identity,
                "resources": report["resources"],
            }
        )
    )
    return 0 if report["status"] == "GEOMETRY_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
