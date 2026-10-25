"""Admission unit tests and the authorized native Windows containment check."""

from __future__ import annotations

import ctypes
import json
import os
import runpy
import sys
import time
from pathlib import Path

import pytest

from torquay_pipeline import road_surface_memory_admission as memory
from torquay_pipeline import road_surface_validation_process_v1 as process


@pytest.mark.parametrize("failed_observations", [{1}, {2}, {1, 2}])
def test_assessment_telemetry_failure_cannot_skip_termination_wait_or_close(failed_observations):
    root = Path(__file__).resolve().parents[2]
    cleanup = runpy.run_path(str(root / "pipeline/scripts/assess_teignmouth_memory_admission.py"))[
        "cleanup_job"
    ]
    calls = []

    class Job:
        observation = 0

        def memory_observation(self):
            self.observation += 1
            calls.append(f"observe{self.observation}")
            if self.observation in failed_observations:
                raise OSError("synthetic telemetry failure")
            return {"peak": 1}

        def terminate(self):
            calls.append("terminate")

        def wait_exit(self, deadline):
            calls.append(("wait", deadline))
            return True

        def close(self):
            calls.append("close")

    record = {}
    cleanup(Job(), 123.0, record)
    assert calls == ["observe1", "terminate", ("wait", 123.0), "observe2", "close"]
    assert record["wholeTreeExitConfirmed"] is True
    assert len(record["telemetryErrors"]) == len(failed_observations)
    assert "cleanupError" not in record


@pytest.mark.parametrize("failure", ["termination", "wait-error", "unconfirmed", "close"])
def test_assessment_cleanup_failure_keeps_wait_independent_and_retains_unconfirmed_owner(failure):
    root = Path(__file__).resolve().parents[2]
    cleanup = runpy.run_path(str(root / "pipeline/scripts/assess_teignmouth_memory_admission.py"))[
        "cleanup_job"
    ]
    calls = []

    class Job:
        def memory_observation(self):
            raise OSError("telemetry unavailable")

        def terminate(self):
            calls.append("terminate")
            if failure == "termination":
                raise OSError("termination failed")

        def wait_exit(self, deadline):
            calls.append(("wait", deadline))
            if failure == "wait-error":
                raise OSError("wait failed")
            return failure != "unconfirmed"

        def close(self):
            calls.append("close")
            if failure == "close":
                raise OSError("close failed")

    job = Job()
    record = {}
    synthetic_pid = -123
    process.UNCONFIRMED_JOBS[synthetic_pid] = job
    try:
        cleanup(job, 125.0, record)
        assert calls[:2] == ["terminate", ("wait", 125.0)]
        if failure in ("wait-error", "unconfirmed"):
            assert "close" not in calls
            assert record["wholeTreeExitConfirmed"] is False
            assert record["ownershipRetained"] is True
            assert process.UNCONFIRMED_JOBS[synthetic_pid] is job
        else:
            assert calls[-1] == "close"
            assert record["wholeTreeExitConfirmed"] is True
        if failure == "close":
            assert record["ownershipRetained"] is True
        if failure != "unconfirmed":
            assert "cleanupError" in record
    finally:
        process.UNCONFIRMED_JOBS.pop(synthetic_pid)


def test_fresh_admission_uses_commit_not_address_space():
    assert memory.Availability(100, 60).assessment_limit() == 30
    assert memory.guarded_job_limit(memory.Availability(100_000, 80_000), 4096) == 36_864
    with pytest.raises(memory.AdmissionError):
        memory.Availability(100, -1).assessment_limit()
    with pytest.raises(memory.AdmissionError):
        memory.guarded_job_limit(memory.Availability(100, 100), 0)


def test_unknown_ledger_never_admits_and_inclusive_incremental_arithmetic():
    with pytest.raises(memory.AdmissionError, match="unbounded"):
        memory.ExecutionLedger(None, None, frozenset()).required_limit(
            memory.Availability(1000, 1000)
        )
    ledger = memory.ExecutionLedger(10, 21, memory.REQUIRED_COMPONENTS)
    assert ledger.required_limit(memory.Availability(100, 100)) == 42
    with pytest.raises(memory.AdmissionError, match="exceeds"):
        ledger.required_limit(memory.Availability(80, 80))


def test_typed_read_and_full_unicode_bound_have_no_fixed_caps(tmp_path):
    path = tmp_path / "record"
    path.write_bytes(b"abc")
    assert memory.bounded_read(path, 3, 3) == b"abc"
    with pytest.raises(memory.AdmissionError):
        memory.bounded_read(path, 3, 2)
    with pytest.raises(memory.AdmissionError):
        memory.bounded_read(path, 2, 3)
    checks = []
    assert process.value_bound(["\U0001f600"], check=checks.append) == (0, 86)
    assert checks == [86]


@pytest.mark.skipif(os.name != "nt", reason="Windows Job behavior required")
def test_native_outer_job_nested_membership_commit_failure_and_cleanup(tmp_path, monkeypatch):
    """No source, codec, topology, solver, trial, profile or standalone probe."""
    root = Path(__file__).resolve().parents[2]
    limit = memory.fresh_availability().assessment_limit() // 4096 * 4096
    signal = tmp_path / "ready.json"
    release = tmp_path / "release"
    leaf = tmp_path / "leaf.py"
    leaf.write_text(
        "import ctypes,json,os,time\nfrom pathlib import Path\n"
        "k=ctypes.WinDLL('kernel32',use_last_error=True)\n"
        "k.VirtualAlloc.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint32,ctypes.c_uint32]\n"
        "k.VirtualAlloc.restype=ctypes.c_void_p\n"
        f"p=k.VirtualAlloc(None,{limit + 4096},0x3000,4)\n"
        "if p:\n"
        " k.VirtualFree.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint32]\n"
        " k.VirtualFree(p,0,0x8000)\n"
        f"out=Path({str(signal)!r})\n"
        "out.write_text(json.dumps({'pid':os.getpid(),'commitDenied':not bool(p)}))\n"
        f"while not Path({str(release)!r}).exists(): time.sleep(.005)\n"
    )
    supervisor = tmp_path / "supervisor.py"
    supervisor.write_text(
        "import sys,time\nfrom pathlib import Path\n"
        f"sys.path.insert(0,{str(root / 'pipeline')!r})\n"
        "from torquay_pipeline.road_surface_validation_process_v1 import WindowsJob,wait_worker\n"
        f"j=WindowsJob([sys.executable,'-B',{str(leaf)!r}],Path({str(root)!r}),finalization_deadline=time.monotonic()+10)\n"
        "try: wait_worker(j,time.monotonic()+8)\n"
        "finally:\n j.terminate()\n assert j.wait_exit(time.monotonic()+2)\n j.close()\n"
    )
    deadline = time.monotonic() + 12
    outer_job_name = f"Local\\TVW-Test-{os.getpid()}-{time.time_ns()}"
    monkeypatch.setenv("TVW_TEIGNMOUTH_OUTER_JOB_NAME", outer_job_name)
    monkeypatch.setenv("TVW_TEIGNMOUTH_OUTER_JOB_COMMIT_LIMIT", str(limit))
    job = process.WindowsJob(
        [sys.executable, "-B", str(supervisor)],
        root,
        finalization_deadline=deadline,
        commit_limit_bytes=limit,
        job_name=outer_job_name,
    )
    try:
        assert job.admission_evidence == {
            "jobCommitLimitBytes": limit,
            "killOnClose": True,
            "breakawayDisabled": True,
            "limitQueried": True,
            "jobName": outer_job_name,
            "membershipBeforeResume": True,
        }
        while not signal.exists() and not job.exited() and time.monotonic() < deadline - 2:
            time.sleep(0.005)
        assert signal.exists(), "nested worker did not report"
        result = json.loads(signal.read_text())
        from ctypes import wintypes as w

        job.kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        job.kernel.OpenProcess.restype = w.HANDLE
        handle = job.kernel.OpenProcess(0x1000, False, result["pid"])
        assert handle
        try:
            member = w.BOOL()
            assert job.kernel.IsProcessInJob(handle, job.job, ctypes.byref(member)) and member.value
        finally:
            job.kernel.CloseHandle(handle)
        assert result["commitDenied"], "Job must reject commit beyond its aggregate allowance"
        release.touch()
        assert process.wait_worker(job, deadline - 1) == 0
    finally:
        job.terminate()
        assert job.wait_exit(deadline), "whole-tree cleanup must be confirmed"
        job.close()
    assert job.pid not in process.UNCONFIRMED_JOBS
