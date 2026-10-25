"""Read-only Stage A source-subgraph assessment, not a trial/profile/probe.

Only load/hash pinned source inputs and run the existing allocation estimator.
No candidate topology, witness, solver, codec or worker is allowed.
"""
from pathlib import Path
import sys
import hashlib
import json
import time
import os
import platform

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "pipeline"))
from torquay_pipeline import road_surface_patch as patch
from torquay_pipeline import road_surface_validation_process_v1 as process
import numpy as np
import shapely

OUT = Path(__file__).with_name("source-request-representability.json")
if OUT.exists():
    raise RuntimeError("assessment output already exists; no overwrite")

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

started = time.monotonic()
proposal = ROOT / "docs/milestones/Teignmouth-timing-bootstrap-proposal.md"
approval_path = ROOT / "docs/milestones/artifacts/Teignmouth-unicode-timing/bootstrap/user-approval.json"
approval = json.loads(approval_path.read_bytes())
assert sha(proposal) == approval["approvedProposalSha256"] == "63cc4ca3a01906b71514d10590da4692399e91aa4e8ecefbc955cad627f2640f"
config_path = ROOT / "config/road-surface-teignmouth-candidate.json"
module_path = ROOT / "pipeline/torquay_pipeline/road_surface_validation_process_v1.py"
source_paths = [proposal, approval_path, config_path, module_path,
               ROOT / "config/road-surface-teignmouth-topology-study.json",
               ROOT / "config/road-surface-teignmouth-topology-transition-v2.json",
               ROOT / "data/source-manifest.json"]
protected_before = {p.relative_to(ROOT).as_posix(): {"sha256": sha(p), "byteLength": p.stat().st_size} for p in source_paths}
forbidden_calls = []
def forbidden(*args, **kwargs):
    forbidden_calls.append("forbidden topology/solver/codec/transport entry")
    raise RuntimeError("forbidden work in source-only assessment")
for name in ("encode", "decode", "blob", "unblob"):
    setattr(process.Codec, name, forbidden)
process.canonical = forbidden
process.supervise = forbidden
process.WindowsJob.__init__ = forbidden
for name in ("build_topology_study_mesh", "build_conforming_mesh", "solve_local_phase_one", "validate_offline_candidate", "assemble_deterministic_candidate_assets"):
    setattr(patch, name, forbidden)

observed = {"requireMemoryCalls": 0, "largestCheckedBytes": 0, "firstRejectedBytes": None}
original_require = process.require_memory
def observe_require(byte_count):
    observed["requireMemoryCalls"] += 1
    observed["largestCheckedBytes"] = max(observed["largestCheckedBytes"], byte_count)
    if type(byte_count) is int and byte_count > process.MAX_BYTES and observed["firstRejectedBytes"] is None:
        observed["firstRejectedBytes"] = byte_count
    return original_require(byte_count)
process.require_memory = observe_require

load_started = time.monotonic()
_config, inputs, accepted, preview_hashes = patch.load_candidate_inputs(ROOT, config_path)
load_seconds = time.monotonic() - load_started
input_identity = {
    "releaseId": inputs.release_id,
    "releaseTerrainManifestSha256": inputs.manifest_sha256,
    "dataSourceManifestSha256": sha(ROOT / "data/source-manifest.json"),
    "releaseSourceHashes": inputs.source_hashes,
    "acceptedPreviewHashes": preview_hashes,
    "sourceRoadPayloadBytes": (inputs.release_root / "roads/roads.json").stat().st_size,
    "baselineArray": {"shape": list(inputs.baseline.shape), "dtype": inputs.baseline.dtype.str, "nbytes": inputs.baseline.nbytes},
    "acceptedArray": {"shape": list(accepted.shape), "dtype": accepted.dtype.str, "nbytes": accepted.nbytes},
}
fit = False
completed_bound = None
error = None
bound_started = time.monotonic()
try:
    binary, metadata = process.value_bound(inputs)
    completed_bound = {"binaryBytes": binary, "metadataBytes": metadata,
                       "baselineLowerBoundBytes": 3 * binary + 4 * metadata}
    original_require(completed_bound["baselineLowerBoundBytes"])
    fit = True
except process.ProcessValidationError as exc:
    error = f"{type(exc).__name__}: {exc}"
bound_seconds = time.monotonic() - bound_started

# The input graph is an unmodified subgraph of CompositeSurface in the fixed
# request. Positive overhead/candidate/mesh fields can only increase its bound.
# A negative result here proves the whole request cannot meet this protocol's
# existing estimate; it does not assert an actual RSS/physical memory overrun.
protected_after = {p.relative_to(ROOT).as_posix(): {"sha256": sha(p), "byteLength": p.stat().st_size} for p in source_paths}
record = {
    "schema": "teignmouth-source-request-representability-v1",
    "assessmentOnly": True,
    "assessmentImplementationSha256": sha(Path(__file__)),
    "approvedProposalSha256": sha(proposal),
    "approvalArtifactSha256": sha(approval_path),
    "estimatorImplementationSha256": sha(module_path),
    "actualModel": "unknown; runtime identity not exposed",
    "actualReasoningEffort": "unknown; runtime setting not exposed",
    "requestedModel": "gpt-6.1-sol", "requestedReasoningEffort": "medium",
    "environment": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "shapely": shapely.__version__, "geos": shapely.geos_version_string, "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS")},
    "inputIdentity": input_identity,
    "evaluatedSubgraph": "Unmodified pinned ReleaseInputs (surface.inputs) transferred recursively by Codec.encode(CompositeSurface).",
    "completeSourceSubgraphBound": completed_bound,
    "limitBytes": process.MAX_BYTES,
    "observedEstimatorChecks": observed,
    "sourceSubgraphFits": fit,
    "fullRequestFitProven": False,
    "status": "SOURCE_SUBGRAPH_FITS_FURTHER_COMPLETE_BOUND_REQUIRED" if fit else "BLOCKED_SOURCE_REQUEST_UNREPRESENTABLE",
    "error": error,
    "boundInterpretation": "Existing conservative estimator rejection, not a measured allocation/RSS overrun. A partial-subgraph rejection is a lower-bound obstruction; no complete byte total is fabricated.",
    "observer": "Wrapped require_memory only to record arguments, then called the unchanged original guard. No source module was edited.",
    "sourceLoadingSeconds": load_seconds,
    "boundInspectionSeconds": bound_seconds,
    "assessmentElapsedSeconds": time.monotonic() - started,
    "timingQualificationEvidence": False,
    "protectedBindingsBefore": protected_before,
    "protectedBindingsAfter": protected_after,
    "protectedBindingsUnchanged": protected_before == protected_after,
    "forbiddenCallAttempts": forbidden_calls,
    "requestEncodingOrDecodingInvoked": False,
    "topologySolverTrialWorkerProbeProfileCandidateInvoked": False,
    "activationEnabled": False,
    "collar05DirectoryAbsent": not (ROOT / ".codex/evidence/teignmouth-topology-study/collar-05").exists(),
    "candidateDirectoryAbsent": not (ROOT / "public/worlds/torquay-road-surface-teignmouth-candidate").exists(),
}
with OUT.open("x", encoding="utf-8") as stream:
    json.dump(record, stream, sort_keys=True, indent=2, allow_nan=False)
    stream.write("\n")
print(json.dumps({"status": record["status"], "observedEstimatorChecks": observed,
                  "completeSourceSubgraphBound": completed_bound, "limitBytes": process.MAX_BYTES,
                  "error": error, "sourceLoadingSeconds": load_seconds,
                  "boundInspectionSeconds": bound_seconds,
                  "protectedBindingsUnchanged": record["protectedBindingsUnchanged"],
                  "collar05DirectoryAbsent": record["collar05DirectoryAbsent"],
                  "forbiddenCallAttempts": forbidden_calls}))
sys.exit(0 if fit else 2)
