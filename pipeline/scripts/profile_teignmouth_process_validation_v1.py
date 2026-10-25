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
import shutil
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


PROBE_CASES = (
    "immediate-success",
    "native-like-blocking",
    "timeout",
    "descendant-containment",
    "parent-abort-kill-on-close",
)


def containment_probe(root: Path, journal_path: Path | None = None) -> dict:
    started = time.monotonic()
    hard_stop = started + 14.0  # Leave one second for durable report/external shutdown.
    records = [{"case": name, "outcome": "not_run"} for name in PROBE_CASES]
    failure = None
    if journal_path is not None:
        with journal_path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps({"elapsedSeconds": 0, "cases": records}) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def journal():
        if journal_path is not None:
            with journal_path.open("a", encoding="utf-8") as stream:
                stream.write(
                    json.dumps({"elapsedSeconds": time.monotonic() - started, "cases": records})
                    + "\n"
                )
                stream.flush()
                os.fsync(stream.fileno())

    scratch = Path(tempfile.mkdtemp(prefix="teignmouth-containment-probe-"))
    active = None

    def launch(code):
        nonlocal active
        try:
            active = WindowsJob(
                [sys.executable, "-B", "-c", code], root, finalization_deadline=hard_stop
            )
        except Exception as exc:
            if hasattr(exc, "job"):
                active = exc.job
            raise
        return active

    def cleanup():
        nonlocal active
        if active is not None:
            active.terminate()
            confirmed = active.wait_exit(hard_stop)
            if not confirmed:
                raise ProcessValidationError("probe cleanup exit unconfirmed")
            active.close()
            active = None

    def record_case(index, operation):
        nonlocal failure
        record = records[index]
        case_started = time.monotonic()
        try:
            record.update(operation())
            record["outcome"] = "pass"
        except BaseException as exc:
            record.update(outcome="fail", error=f"{type(exc).__name__}: {exc}")
            failure = record["error"]
        finally:
            if active is not None:
                record["pid"] = active.pid
                try:
                    record["leaderExitedBeforeCleanup"] = active.exited()
                    record["jobEmptyBeforeCleanup"] = active.empty()
                    record["exitCodeBeforeCleanup"] = (
                        active.exit_code() if active.pid is not None else "not_created"
                    )
                except BaseException as exc:
                    record["observationError"] = f"{type(exc).__name__}: {exc}"
                    failure = record["observationError"]
                    record["outcome"] = "fail"
                try:
                    cleanup()
                    record["cleanupConfirmed"] = True
                except BaseException as exc:
                    record["cleanupConfirmed"] = False
                    record["cleanupError"] = f"{type(exc).__name__}: {exc}"
                    failure = record["cleanupError"]
                    record["outcome"] = "fail"
            record["elapsedSeconds"] = time.monotonic() - case_started
            journal()
        return failure is None

    def success():
        job = launch("pass")
        status = wait_worker(job, min(hard_stop, time.monotonic() + 2))
        if status != 0:
            raise ProcessValidationError(f"immediate exit code={status}")
        return {"exitCode": status}

    native_marker = scratch / "native-entered.txt"

    def blocking():
        job = launch(
            "import ctypes; from pathlib import Path; "
            f"Path({str(native_marker)!r}).write_text('entered'); "
            "ctypes.windll.kernel32.Sleep(10000)"
        )
        limit = min(hard_stop, time.monotonic() + 2)
        while not native_marker.exists() and not job.exited() and time.monotonic() < limit:
            time.sleep(0.005)
        observed = native_marker.exists() and not job.exited()
        if not observed:
            raise ProcessValidationError(f"native entry not observed; exit={job.exit_code()}")
        # Cleanup confirms this case before a separate timeout case starts.
        return {"nativeEntryObserved": True, "pid": job.pid}

    def timeout():
        job = launch("import ctypes; ctypes.windll.kernel32.Sleep(10000)")
        try:
            status = wait_worker(job, min(hard_stop, time.monotonic() + 0.25))
        except ProcessValidationError as exc:
            if "deadline" not in str(exc) and "cutoff" not in str(exc):
                raise
            return {"timeoutObserved": True, "reason": str(exc)}
        raise ProcessValidationError(f"blocking process returned early; exit={status}")

    child_marker = scratch / "descendant-pid.txt"

    def descendant():
        child_code = "import ctypes; ctypes.windll.kernel32.Sleep(10000)"
        code = (
            "import subprocess,sys,ctypes; from pathlib import Path; "
            f"child=subprocess.Popen([sys.executable,'-B','-c',{child_code!r}],"
            "creationflags=0x08000000); "
            f"Path({str(child_marker)!r}).write_text(str(child.pid)); "
            "ctypes.windll.kernel32.Sleep(10000)"
        )
        job = launch(code)
        limit = min(hard_stop, time.monotonic() + 2)
        while not child_marker.exists() and not job.exited() and time.monotonic() < limit:
            time.sleep(0.005)
        if not child_marker.exists() or job.empty():
            raise ProcessValidationError(f"descendant startup not observed; exit={job.exit_code()}")
        return {"descendantPid": int(child_marker.read_text()), "descendantStarted": True}

    abort_marker = scratch / "abort-child-pid.txt"

    def abort():
        code = (
            "import os,sys,time; from pathlib import Path; "
            f"sys.path.insert(0,{str(root / 'pipeline')!r}); "
            "from torquay_pipeline.road_surface_validation_process_v1 import WindowsJob; "
            "job=WindowsJob([sys.executable,'-B','-c',"
            "'import ctypes; ctypes.windll.kernel32.Sleep(10000)'],Path.cwd(),"
            "finalization_deadline=time.monotonic()+2); "
            f"Path({str(abort_marker)!r}).write_text(str(job.pid)); os._exit(0)"
        )
        job = launch(code)
        status = wait_worker(job, min(hard_stop, time.monotonic() + 3))
        while not job.empty() and time.monotonic() < hard_stop:
            time.sleep(0.005)
        if status != 0 or not abort_marker.exists() or not job.empty():
            raise ProcessValidationError(f"abort kill-on-close failed; exit={status}")
        return {
            "helperExitCode": status,
            "abortChildPid": int(abort_marker.read_text()),
            "jobEmptyWithoutParentTermination": True,
        }

    for index, operation in enumerate((success, blocking, timeout, descendant, abort)):
        if not record_case(index, operation):
            break
    if active is None:
        shutil.rmtree(scratch)
    else:
        failure = f"{failure}; unconfirmed ownership retained, scratch={scratch}"
    elapsed = time.monotonic() - started
    return {
        "passes": failure is None and elapsed <= 15,
        "error": failure,
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
    parser.add_argument("--replacement-containment-probe", action="store_true")
    args = parser.parse_args()
    if args.containment_probe:
        raise ProcessValidationError("original probe allowance consumed; rerun forbidden")
    if args.replacement_containment_probe:
        output = EVIDENCE / "containment-probe-replacement.json"
        attempt = EVIDENCE / "containment-probe-replacement-attempt.json"
        if output.exists() or attempt.exists():
            raise ProcessValidationError("the single containment probe is already recorded")
        write_once(
            attempt,
            {
                "probeAllowanceConsumed": True,
                "scriptSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "externalLimitSeconds": 15,
            },
        )
        try:
            report = containment_probe(
                ROOT, EVIDENCE / "containment-probe-replacement-progress.jsonl"
            )
        except BaseException as exc:
            write_once(
                output,
                {
                    "passes": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "probeAllowanceConsumed": True,
                    "cases": [
                        {"case": name, "outcome": "see_progress_journal"} for name in PROBE_CASES
                    ],
                },
            )
            raise
        write_once(output, report)
    else:
        report = assess_evidence(ROOT)
        write_once(EVIDENCE / "retained-evidence-assessment.json", report)
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("passes", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
