"""Run the single bounded corridor diagnostic; a failed safety gate stops integration."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path


def peak_working_set() -> int | None:
    """Actual Windows process peak resident set, not an admission cap."""
    if os.name != "nt":
        return None

    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t)
            for name in (
                "PeakWorkingSetSize",
                "WorkingSetSize",
                "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage",
                "PagefileUsage",
                "PeakPagefileUsage",
            )
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    ctypes.windll.kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    get_info = ctypes.windll.psapi.GetProcessMemoryInfo
    get_info.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong)
    if not get_info(handle, ctypes.byref(counters), counters.cb):
        raise OSError("cannot measure process memory")
    return int(counters.PeakWorkingSetSize)


def protected_snapshot(root: Path) -> dict[str, str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    paths = {root / p for p in result.stdout.decode().split("\0") if p}
    for folder in ("public/worlds",):
        paths.update(p for p in (root / folder).rglob("*") if p.is_file())
    # Coordinator-owned state/spec may evolve while this isolated implementer runs.
    excluded = {
        ".codex/torquay-plan-implementation.md",
        "docs/milestones/Teignmouth-corridor-prototype-spec.md",
    }
    snapshot = {}
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix()
        if relative in excluded or "Teignmouth-corridor-prototype/" in relative:
            continue
        if path.is_file():
            with path.open("rb") as stream:
                snapshot[relative] = hashlib.file_digest(stream, "sha256").hexdigest()
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--diagnostic", action="store_true")
    mode.add_argument("--build", type=int, choices=(1, 2))
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    evidence = args.evidence.resolve()
    expected_parent = (root / "docs/milestones/artifacts/Teignmouth-corridor-prototype").resolve()
    if not evidence.is_relative_to(expected_parent) or evidence.exists():
        raise ValueError("evidence must be fresh and inside prototype evidence root")
    evidence.mkdir(parents=True)
    started = time.perf_counter()
    limit = 120.0 if args.diagnostic else 180.0

    def timeout() -> None:
        (evidence / "timeout.json").write_text(
            json.dumps({"status": "STOP", "reason": f"{limit}s deadline"}) + "\n"
        )
        os._exit(124)

    watchdog = threading.Timer(limit, timeout)
    watchdog.daemon = True
    watchdog.start()
    try:
        before = protected_snapshot(root)
        (evidence / "preservation-before.json").write_text(
            json.dumps(before, sort_keys=True, indent=2) + "\n"
        )
        from torquay_pipeline.teignmouth_corridor_prototype import diagnostic

        candidate = (
            None
            if args.diagnostic
            else root / f"data/generated/teignmouth-corridor-prototype/build-{args.build}"
        )
        try:
            report = diagnostic(root, candidate)
        except Exception as exc:
            report = {
                "status": "STOP",
                "stopReasons": [f"{type(exc).__name__}: {exc}"],
                "topology": {"tested": False},
                "globalSafety": {"tested": False},
            }
        after = protected_snapshot(root)
        changed = [path for path, digest in before.items() if after.get(path) != digest]
        report["preservation"] = {
            "comparedPaths": len(before),
            "changedPaths": changed,
            "passes": not changed,
            "exclusions": [
                "coordinator checkpoint",
                "active prototype spec",
                "new prototype evidence",
            ],
        }
        if changed:
            report["status"] = "STOP"
            report["stopReasons"].append("protected bytes changed")
        report["resources"] = {
            "wallSeconds": time.perf_counter() - started,
            "peakWorkingSetBytes": peak_working_set(),
            "wallLimitSeconds": limit,
            "diagnosticOrdinal": 1,
            "fullBuildOrdinal": args.build,
        }
        for name, value in (
            ("report.json", report),
            ("preservation-after.json", after),
        ):
            (evidence / name).write_text(
                json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"
            )
        print(
            json.dumps(
                {
                    key: report[key]
                    for key in ("status", "stopReasons", "topology", "globalSafety", "resources")
                }
            )
        )
        return 0 if report["status"] == "FEASIBLE" else 2
    finally:
        watchdog.cancel()


if __name__ == "__main__":
    raise SystemExit(main())
