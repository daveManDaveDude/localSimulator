"""One synthetic containment probe and read-only retained-evidence assessment.

No retained replay is implemented until legitimate complete-path evidence is
available. In particular this script cannot dispatch a solver or study trial.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from torquay_pipeline.road_surface_validation_process_v1 import (  # noqa: E402
    ProcessValidationError,
    WindowsJob,
    wait_worker,
)

EVIDENCE = ROOT / "docs/milestones/artifacts/Teignmouth-process-validation"


def write_once(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def assess_evidence(root: Path) -> dict:
    review_root = root / "docs/milestones/artifacts/Teignmouth-topology-validation-v2"
    receipts = {
        name: (review_root / name).is_file()
        for name in ("independent-sol-review.json", "coordinator-acceptance.json")
    }
    witnesses = {}
    for name in ("flip-05", "road-05"):
        path = root / ".codex/evidence/teignmouth-topology-study" / name / "offline-aggregate.json"
        payload = path.read_bytes()
        report = json.loads(payload)
        witnesses[name] = {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "passes": report.get("passes") is True,
            "successfulAssemblyPresent": isinstance(report.get("studyAssemblyAndResources"), dict)
            and report["studyAssemblyAndResources"].get("passes") is True,
        }
    missing = []
    if not all(receipts.values()):
        missing.append(
            "Production activation review/receipt artifacts are absent; "
            "no genuine successful receipt preflight can be measured."
        )
    if not any(
        record["passes"] and record["successfulAssemblyPresent"] for record in witnesses.values()
    ):
        missing.append(
            "Both retained witnesses fail base offline gates; no legitimate retained "
            "successful assembly/independent validation/finalization path is available."
        )
    return {
        "receipts": receipts,
        "retainedWitnesses": witnesses,
        "missingEvidence": missing,
        "retainedReplayPermitted": not missing,
        "qualifiesForNextTrialTiming": False,
        "trialInvoked": False,
        "solverInvoked": False,
        "activationEnabled": False,
    }


def containment_probe(root: Path) -> dict:
    started = time.monotonic()
    hard_stop = started + 15.0
    records = []
    with tempfile.TemporaryDirectory(prefix="teignmouth-containment-probe-") as directory:
        scratch = Path(directory)
        # Immediate success; process launch and containment precede the wait.
        for label, code, window in (
            ("success", "pass", 2.0),
            ("native-block-timeout", "import ctypes; ctypes.windll.kernel32.Sleep(10000)", 0.25),
            (
                "descendant-timeout",
                "import subprocess,sys,ctypes; subprocess.Popen([sys.executable,'-B','-c',"
                "'import ctypes; ctypes.windll.kernel32.Sleep(10000)'],"
                "creationflags=0x08000000); ctypes.windll.kernel32.Sleep(10000)",
                0.75,
            ),
        ):
            step_started = time.monotonic()
            job = WindowsJob([sys.executable, "-B", "-c", code], root)
            timed_out = False
            try:
                try:
                    status = wait_worker(job, min(hard_stop - 1, time.monotonic() + window))
                except ProcessValidationError:
                    status, timed_out = None, True
                job.terminate()
                while not job.empty() and time.monotonic() < hard_stop:
                    time.sleep(0.005)
                if (
                    not job.exited()
                    or not job.empty()
                    or (label == "success" and (timed_out or status != 0))
                    or (label != "success" and not timed_out)
                ):
                    raise ProcessValidationError("synthetic containment observation failed")
                records.append(
                    {
                        "case": label,
                        "timedOut": timed_out,
                        "exitCodeBeforeTermination": status,
                        "leaderAndDescendantsExited": True,
                        "seconds": time.monotonic() - step_started,
                    }
                )
            finally:
                job.close()

        # The helper creates its own Job, resumes a blocking child, then exits
        # without closing the handle in Python. OS handle closure must kill it.
        marker = scratch / "abort-child-pid.txt"
        helper = (
            "import os,sys; from pathlib import Path; "
            f"sys.path.insert(0,{str(root / 'pipeline')!r}); "
            "from torquay_pipeline.road_surface_validation_process_v1 import WindowsJob; "
            "job=WindowsJob([sys.executable,'-B','-c',"
            "'import ctypes; ctypes.windll.kernel32.Sleep(10000)'],Path.cwd()); "
            f"Path({str(marker)!r}).write_text(str(job.pid)); os._exit(0)"
        )
        job = WindowsJob([sys.executable, "-B", "-c", helper], root)
        try:
            status = wait_worker(job, min(hard_stop - 1, time.monotonic() + 3.0))
            # The outer Job is still open and has never been terminated. Its
            # active count proves the inner child died through helper abort.
            while not job.empty() and time.monotonic() < hard_stop - 0.5:
                time.sleep(0.005)
            if status != 0 or not marker.exists() or not job.empty():
                raise ProcessValidationError("parent-abort kill-on-close not established")
            records.append(
                {
                    "case": "parent-abort-kill-on-close",
                    "leaderAndDescendantsExited": True,
                    "abortChildPid": int(marker.read_text()),
                }
            )
        finally:
            job.terminate()
            job.close()
    elapsed = time.monotonic() - started
    if elapsed > 15:
        raise ProcessValidationError("synthetic probe exceeded 15 seconds")
    return {
        "passes": True,
        "elapsedSeconds": elapsed,
        "limitSeconds": 15,
        "cases": records,
        "python": sys.version,
        "platform": platform.platform(),
        "solverInvoked": False,
        "trialInvoked": False,
        "projectGeometryUsed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--containment-probe", action="store_true")
    args = parser.parse_args()
    if args.containment_probe:
        output = EVIDENCE / "containment-probe.json"
        if output.exists():
            raise ProcessValidationError("the single containment probe is already recorded")
        try:
            report = containment_probe(ROOT)
        except BaseException as exc:
            write_once(
                output,
                {
                    "passes": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "probeAllowanceConsumed": True,
                },
            )
            raise
        write_once(output, report)
    else:
        report = assess_evidence(ROOT)
        write_once(EVIDENCE / "retained-evidence-assessment.json", report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
