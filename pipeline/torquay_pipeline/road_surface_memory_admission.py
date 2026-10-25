"""Fail-closed operational admission; buffer estimates never claim to bound RSS.

This initial implementation admits only the source assessment. Execution needs
an independently justified full-tree ledger, including native allocations.
"""

from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass


class AdmissionError(ValueError):
    """No execution allowance can be issued from incomplete evidence."""


@dataclass(frozen=True)
class Availability:
    available_physical_bytes: int
    current_process_commit_available_bytes: int

    def assessment_limit(self) -> int:
        values = (self.available_physical_bytes, self.current_process_commit_available_bytes)
        if any(type(v) is not int or v <= 0 for v in values):
            raise AdmissionError("invalid fresh memory availability")
        return min(values) // 2


def guarded_job_limit(availability: Availability, page_size_bytes: int) -> int:
    """Return half the fresher host headroom, rounded down to a Windows page."""
    if type(page_size_bytes) is not int or page_size_bytes <= 0:
        raise AdmissionError("invalid system page size")
    limit = (availability.assessment_limit() // page_size_bytes) * page_size_bytes
    if limit < page_size_bytes:
        raise AdmissionError("fresh host headroom is below one system page")
    return limit


def system_page_size_bytes() -> int:
    """Query Windows page granularity without importing numerical packages."""
    if os.name != "nt":
        raise AdmissionError("Windows page-size query is required")
    from ctypes import wintypes as w

    class SystemInfo(ctypes.Structure):
        _fields_ = [
            ("architecture", w.WORD),
            ("reserved", w.WORD),
            ("page_size", w.DWORD),
            ("minimum_address", ctypes.c_void_p),
            ("maximum_address", ctypes.c_void_p),
            ("active_mask", ctypes.c_size_t),
            ("processor_count", w.DWORD),
            ("processor_type", w.DWORD),
            ("allocation_granularity", w.DWORD),
            ("processor_level", w.WORD),
            ("processor_revision", w.WORD),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetSystemInfo.argtypes = [ctypes.POINTER(SystemInfo)]
    kernel.GetSystemInfo.restype = None
    info = SystemInfo()
    kernel.GetSystemInfo(ctypes.byref(info))
    if info.page_size <= 0:
        raise AdmissionError("Windows returned an invalid page size")
    return int(info.page_size)


def fresh_availability() -> Availability:
    """ullAvailPageFile is current-process commit availability, not a reservation."""
    if os.name != "nt":
        raise AdmissionError("Windows memory admission is required")
    from ctypes import wintypes as w

    class Status(ctypes.Structure):
        _fields_ = [("length", w.DWORD), ("load", w.DWORD)] + [
            (name, ctypes.c_uint64)
            for name in (
                "total_physical",
                "available_physical",
                "total_pagefile",
                "available_pagefile",
                "total_virtual",
                "available_virtual",
                "extended",
            )
        ]

    status = Status()
    status.length = ctypes.sizeof(status)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(Status)]
    kernel.GlobalMemoryStatusEx.restype = w.BOOL
    if not kernel.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise AdmissionError("GlobalMemoryStatusEx failed")
    return Availability(int(status.available_physical), int(status.available_pagefile))


REQUIRED_COMPONENTS = frozenset(
    {
        "both_process_source_loading",
        "python_json_objects",
        "native_geos",
        "transport",
        "results_assets_finalization",
    }
)


@dataclass(frozen=True)
class ExecutionLedger:
    baseline_bytes: int | None
    additional_peak_bytes: int | None
    justified_components: frozenset[str]

    def required_limit(self, availability: Availability) -> int:
        if not REQUIRED_COMPONENTS <= self.justified_components:
            raise AdmissionError("mandatory full-tree allocation components remain unbounded")
        b, p = self.baseline_bytes, self.additional_peak_bytes
        if any(type(v) is not int or v < 0 for v in (b, p)):
            raise AdmissionError("inclusive baseline and incremental peak are required")
        # Integer arithmetic avoids float rounding for large declared bounds.
        headroom = max(b, (p + 1) // 2)
        required = b + p + headroom
        if required > availability.assessment_limit():
            raise AdmissionError("required full-tree allowance exceeds fresh host allowance")
        return required


def bounded_read(path, expected_length: int, admitted_length: int) -> bytes:
    """Read only an exact reviewed length; no fixed 16 MiB envelope ceiling."""
    if any(type(v) is not int or v < 0 for v in (expected_length, admitted_length)):
        raise AdmissionError("invalid typed read allocation")
    if expected_length > admitted_length or path.stat().st_size != expected_length:
        raise AdmissionError("read allocation or exact length mismatch")
    with path.open("rb") as stream:
        data = stream.read(expected_length + 1)
    if len(data) != expected_length:
        raise AdmissionError("file changed during bounded read")
    return data


def process_commit_observation() -> dict[str, int]:
    """Current and peak process commit, supplementary measurements only."""
    from ctypes import wintypes as w

    class Counters(ctypes.Structure):
        _fields_ = [("size", w.DWORD), ("faults", w.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "peak_ws",
                "ws",
                "peak_paged",
                "paged",
                "peak_nonpaged",
                "nonpaged",
                "pagefile",
                "peak_pagefile",
                "private",
            )
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [w.HANDLE, ctypes.c_void_p, w.DWORD]
    psapi.GetProcessMemoryInfo.restype = w.BOOL
    info = Counters()
    info.size = ctypes.sizeof(info)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(info), info.size):
        raise AdmissionError("GetProcessMemoryInfo failed")
    return {
        "currentProcessCommitBytes": int(info.private),
        "peakProcessCommitBytes": int(info.peak_pagefile),
    }
