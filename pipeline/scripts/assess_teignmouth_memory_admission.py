"""One source-only assessment under a dynamically bounded outer Windows Job."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from torquay_pipeline import road_surface_memory_admission as admission  # noqa: E402
from torquay_pipeline import road_surface_validation_process_v1 as process  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def child(output: Path, limit: int):
    from torquay_pipeline import road_surface_patch as patch

    forbidden = []

    def refuse(*args, **kwargs):
        forbidden.append("forbidden-work")
        raise RuntimeError("encoding/topology/solver/trial/worker forbidden in assessment")

    for name in ("encode", "decode", "blob", "unblob"):
        setattr(process.Codec, name, refuse)
    process.canonical = process.supervise = refuse
    process.WindowsJob.__init__ = refuse
    for name in (
        "build_topology_study_mesh",
        "build_conforming_mesh",
        "solve_local_phase_one",
        "validate_offline_candidate",
        "assemble_deterministic_candidate_assets",
    ):
        setattr(patch, name, refuse)

    paths = [
        ROOT / p
        for p in (
            "config/road-surface-teignmouth-candidate.json",
            "config/road-surface-teignmouth-topology-study.json",
            "config/road-surface-teignmouth-topology-transition-v2.json",
            "data/source-manifest.json",
            "docs/milestones/Teignmouth-timing-bootstrap-proposal.md",
            "docs/milestones/artifacts/Teignmouth-unicode-timing/bootstrap/user-approval.json",
        )
    ]
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
    import_baseline = admission.process_commit_observation()
    started = time.monotonic()
    _, inputs, accepted, preview = patch.load_candidate_inputs(ROOT, paths[0])
    loaded = time.monotonic()
    loaded_observation = admission.process_commit_observation()

    def operational_check(count):
        if type(count) is not int or count < 0 or count > limit:
            raise admission.AdmissionError("source buffer estimate exceeds operational allowance")

    binary, metadata = process.value_bound(inputs, check=operational_check)
    baseline_reservation = 3 * binary + 4 * (metadata + 1024)
    ledger = admission.ExecutionLedger(None, None, frozenset())
    try:
        ledger.required_limit(admission.Availability(limit * 2, limit * 2))
    except admission.AdmissionError as exc:
        rejection = str(exc)
    else:
        raise RuntimeError("an incomplete full-tree ledger must never admit execution")
    after = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
    result = {
        "schema": "teignmouth-memory-source-assessment-v1",
        "status": "BLOCKED_INCOMPLETE_FULL_TREE_ALLOCATION_LEDGER",
        "completeSourceSubgraphBound": {"binaryBytes": binary, "metadataBytes": metadata},
        "sourceOnlyTransferBaselineReservationBytes": baseline_reservation,
        "completeRequestBound": None,
        "allocationLedger": {
            "B": None,
            "P": None,
            "H": None,
            "BMeaning": (
                "inclusive supervisor plus worker commit after imports before materialization"
            ),
            "PMeaning": "additional simultaneous whole-tree allocations above B",
            "HFormula": "max(B, ceil(P/2)); contingency, not proof",
            "missingJustifiedComponents": sorted(admission.REQUIRED_COMPONENTS),
            "observedMemoryPeaks": {
                "importBaseline": import_baseline,
                "afterSourceLoad": loaded_observation,
                "afterBound": admission.process_commit_observation(),
            },
            "observedPeaksAreNotBounds": True,
        },
        "executionAdmission": False,
        "executionRefusal": rejection,
        "sourceLoadingSeconds": loaded - started,
        "boundSeconds": time.monotonic() - loaded,
        "releaseId": inputs.release_id,
        "releaseSources": inputs.source_hashes,
        "acceptedPreviewHashes": preview,
        "acceptedArrayBytes": accepted.nbytes,
        "protectedBefore": before,
        "protectedAfter": after,
        "protectedUnchanged": before == after,
        "forbiddenCallAttempts": forbidden,
        "activationEnabled": False,
        "timingQualificationEvidence": False,
        "collar05Absent": not (
            ROOT / ".codex/evidence/teignmouth-topology-study/collar-05"
        ).exists(),
        "candidateAbsent": not (
            ROOT / "public/worlds/torquay-road-surface-teignmouth-candidate"
        ).exists(),
    }
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return 2


def cleanup_job(job, final: float, record: dict):
    """Telemetry is optional; termination and bounded exit confirmation are not."""

    def observe(key):
        try:
            record[key] = job.memory_observation()
        except BaseException as exc:
            record.setdefault("telemetryErrors", []).append(f"{type(exc).__name__}: {exc}")

    observe("jobMemoryObservationBeforeCleanup")
    try:
        job.terminate()
    except BaseException as exc:
        record.setdefault("cleanupErrors", []).append(f"terminate: {type(exc).__name__}: {exc}")
    finally:
        # A failed termination API must not suppress the independent wait check.
        try:
            confirmed = job.wait_exit(final)
        except BaseException as exc:
            confirmed = False
            record.setdefault("cleanupErrors", []).append(f"wait: {type(exc).__name__}: {exc}")
        record["wholeTreeExitConfirmed"] = confirmed
    if confirmed:
        observe("jobMemoryObservationAfterExit")
        try:
            job.close()
        except BaseException as exc:
            record.setdefault("cleanupErrors", []).append(f"close: {type(exc).__name__}: {exc}")
            record["ownershipRetained"] = True
    else:
        # WindowsJob keeps the strong UNCONFIRMED_JOBS reference and handles.
        record["ownershipRetained"] = True
        record["error"] = "whole-tree exit unconfirmed; ownership retained"
    if record.get("cleanupErrors"):
        record["cleanupError"] = "; ".join(record["cleanupErrors"])


def guardian(output: Path):
    if output.exists() or output.with_suffix(".child.json").exists():
        raise RuntimeError("write-once assessment output exists")
    started = time.monotonic()
    final = started + 30
    availability = admission.fresh_availability()
    limit = availability.assessment_limit() // 4096 * 4096
    child_output = output.with_suffix(".child.json")
    argv = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "--child",
        "--limit",
        str(limit),
        "--output",
        str(child_output),
    ]
    job = None
    record = {
        "schema": "teignmouth-outer-assessment-v1",
        "argv": argv,
        "cwd": str(ROOT),
        "availability": asdict(availability),
        "availabilityMeaning": (
            "ullAvailPageFile is current-process commit availability; volatile, not reserved"
        ),
        "admittedJobCommitLimitBytes": limit,
        "deadlineSeconds": 30,
        "limitBehavior": "prevents further commits; does not automatically terminate",
        "requestedModel": "gpt-6.1-sol",
        "requestedEffort": "medium",
        "actualModel": "unknown",
        "actualEffort": "unknown",
    }
    try:
        try:
            job = process.WindowsJob(
                argv, ROOT, finalization_deadline=final, commit_limit_bytes=limit
            )
        except process.ProcessStartupError as exc:
            job = exc.job
            raise
        record["job"] = job.admission_evidence
        record["childExitCode"] = process.wait_worker(job, final - 5)
    except BaseException as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if job is not None:
            cleanup_job(job, final, record)
        record["elapsedSeconds"] = time.monotonic() - started
        record["withinDeadline"] = time.monotonic() < final
        record["implementationHashes"] = {
            p.relative_to(ROOT).as_posix(): sha(p)
            for p in (
                Path(__file__).resolve(),
                ROOT / "pipeline/torquay_pipeline/road_surface_memory_admission.py",
                ROOT / "pipeline/torquay_pipeline/road_surface_validation_process_v1.py",
            )
        }
        if child_output.exists():
            record["childEvidenceSha256"] = sha(child_output)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, indent=2, sort_keys=True)
            stream.write("\n")
    return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    sys.exit(child(args.output, args.limit) if args.child else guardian(args.output))
