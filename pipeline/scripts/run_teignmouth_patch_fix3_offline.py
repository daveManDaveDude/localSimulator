"""One-shot real-input offline gate for the Teignmouth patch fix-3 review.

The exact evidence directory is intentionally write-once. This runner never
publishes to ``public/worlds`` and refuses to run when its evidence or reserved
candidate directory already exists.
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from torquay_pipeline import road_surface
from torquay_pipeline.road_surface_patch import (
    PATCH_OUTPUT_FILES,
    CompositeSurface,
    RoadSurfacePatchError,
    _protected_hash_snapshot,
    _target_part_and_bounds,
    assemble_deterministic_candidate_assets,
    build_conforming_mesh,
    build_local_phase_one_constraints,
    load_candidate_inputs,
    patch_topology_report,
    serialize_offline_report,
    solve_local_phase_one,
    validate_candidate_patch_assets,
    validate_offline_candidate,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config/road-surface-teignmouth-candidate.json"
EVIDENCE_PATH = ROOT / ".codex/evidence/teignmouth-road-surface-fix3"
EVIDENCE_FILES = frozenset(
    {
        "attempt.json",
        "solver-phase.json",
        "candidate-heights.f32",
        "patch-vertices-xz.f64",
        "patch-base-heights.f32",
        "patch-triangles.u32",
        "offline-aggregate.json",
    }
)
MAXIMUM_ITERATIONS = 2_000
MAXIMUM_SOLVER_SECONDS = 120.0


def _exclusive_write(path: Path, content: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _preflight(root: Path) -> Path:
    root = root.resolve(strict=True)
    expected = root / ".codex/evidence/teignmouth-road-surface-fix3"
    if os.path.normcase(os.path.abspath(str(EVIDENCE_PATH))) != os.path.normcase(str(expected)):
        raise RoadSurfacePatchError("fix-3 evidence path is not the exact reserved directory")
    road_surface._assert_no_reparse_components(expected)
    if expected.exists():
        raise RoadSurfacePatchError(
            "fix-3 evidence path already exists; refusing a second real run or overwrite"
        )
    protected = road_surface._protected_execution_inputs(root) + [
        root / "public/worlds/torquay-road-surface-preview"
    ]
    candidate = root / road_surface.TEIGNMOUTH_CANDIDATE_OUTPUT
    road_surface.guard_output_directory(
        root,
        candidate,
        protected,
        owned_files=PATCH_OUTPUT_FILES,
    )
    if candidate.exists():
        raise RoadSurfacePatchError(
            "reserved public candidate path already exists; refusing to adopt or overwrite it"
        )
    if road_surface._paths_overlap(expected, candidate) or any(
        road_surface._paths_overlap(expected, path) for path in protected
    ):
        raise RoadSurfacePatchError("fix-3 evidence path overlaps a candidate or protected input")
    return expected


def _write_private_asset_set(directory: Path, assets: dict[str, bytes]) -> dict[str, str]:
    if set(assets) != PATCH_OUTPUT_FILES:
        raise RoadSurfacePatchError("independent assembly did not produce the exact file allowlist")
    directory.mkdir(parents=False, exist_ok=False)
    hashes: dict[str, str] = {}
    for name, content in sorted(assets.items()):
        _exclusive_write(directory / name, content)
        hashes[name] = _digest(content)
    return hashes


def main() -> int:
    evidence = _preflight(ROOT)
    # Create a write-once marker before any real-input processing. Even an
    # interrupted attempt cannot silently be repeated under this fix number.
    evidence.parent.mkdir(parents=True, exist_ok=True)
    road_surface._assert_no_reparse_components(evidence.parent)
    evidence.mkdir(parents=False, exist_ok=False)
    road_surface._assert_no_reparse_components(evidence)
    _exclusive_write(
        evidence / "attempt.json",
        serialize_offline_report(
            {
                "run": "Teignmouth shared-surface fix 3 offline gate",
                "startedUnixSeconds": time.time(),
                "solverMaximumIterations": MAXIMUM_ITERATIONS,
                "solverMaximumWallSeconds": MAXIMUM_SOLVER_SECONDS,
                "candidatePublicOutputWritten": False,
            }
        ),
    )

    start = time.monotonic()
    inputs = None
    protected_before: dict[str, str] = {}
    candidate: np.ndarray | None = None
    solver_report: dict[str, Any] | None = None
    aggregate: dict[str, Any] = {
        "passes": False,
        "phase": "input-loading",
        "candidatePublicOutputWritten": False,
    }
    config_hash_before = _digest(CONFIG_PATH.read_bytes())
    try:
        config, inputs, accepted, accepted_hashes = load_candidate_inputs(ROOT, CONFIG_PATH)
        protected_before = _protected_hash_snapshot(ROOT, inputs)
        influence, bounds, target_points, target_cumulative = _target_part_and_bounds(inputs)
        mesh = build_conforming_mesh(
            bounds,
            accepted,
            inputs.width_m,
            inputs.depth_m,
            inputs.spacing_m,
        )
        topology = patch_topology_report(mesh, inputs.spacing_m)
        constraints, constraint_summary = build_local_phase_one_constraints(mesh, inputs, accepted)
        if not topology.get("passes"):
            aggregate.update(
                {
                    "phase": "pre-solver-topology",
                    "topology": topology,
                    "constraintSummary": constraint_summary,
                    "patchBounds": bounds.__dict__,
                }
            )
            raise RoadSurfacePatchError(
                "candidate patch topology/resource gate failed before solve"
            )

        candidate, solver_report = solve_local_phase_one(
            mesh,
            inputs,
            constraints,
            influence=influence,
            maximum_iterations=MAXIMUM_ITERATIONS,
            maximum_wall_seconds=MAXIMUM_SOLVER_SECONDS,
        )
        candidate_bytes = candidate.astype("<f4", copy=False).tobytes(order="C")
        witness_hash = _digest(candidate_bytes)
        _exclusive_write(evidence / "candidate-heights.f32", candidate_bytes)
        mesh_witnesses = {
            "patch-vertices-xz.f64": mesh.vertices_xz.astype("<f8", copy=False).tobytes(order="C"),
            "patch-base-heights.f32": mesh.base_y.astype("<f4", copy=False).tobytes(order="C"),
            "patch-triangles.u32": mesh.triangles.astype("<u4", copy=False).tobytes(order="C"),
        }
        for filename, content in mesh_witnesses.items():
            _exclusive_write(evidence / filename, content)
        _exclusive_write(
            evidence / "solver-phase.json",
            serialize_offline_report(
                {
                    "solver": solver_report,
                    "candidateFloat32Sha256": witness_hash,
                    "candidateFloat32ByteLength": len(candidate_bytes),
                    "meshWitnesses": {
                        name: {"byteLength": len(content), "sha256": _digest(content)}
                        for name, content in mesh_witnesses.items()
                    },
                    "patchBounds": bounds.__dict__,
                    "targetSegmentPointsXZ": target_points,
                    "targetPartCumulativeStationsM": target_cumulative,
                    "constraintSummary": constraint_summary,
                    "candidatePublicOutputWritten": False,
                }
            ),
        )

        surface = CompositeSurface(mesh, inputs, accepted, candidate)
        aggregate = validate_offline_candidate(
            surface,
            influence,
            constraints,
            solver_report,
            accepted_hashes,
        )
        aggregate["phase"] = "offline-gates-complete"
        aggregate["solver"] = solver_report
        aggregate["constraintSummary"] = constraint_summary
        aggregate["patchTopology"] = topology
        aggregate["patchBounds"] = bounds.__dict__
        aggregate["targetSegmentPointsXZ"] = target_points
        aggregate["targetPartCumulativeStationsM"] = target_cumulative
        aggregate["candidatePublicOutputWritten"] = False
        aggregate["protectedHashesBefore"] = protected_before

        if aggregate.get("passes") is True:
            first_assets, second_assets, deterministic = assemble_deterministic_candidate_assets(
                surface,
                aggregate["roadPathReclip"],
                aggregate,
            )
            first_validation = validate_candidate_patch_assets(
                first_assets,
                surface,
                aggregate["candidateFloat32Sha256"],
                aggregate["roadPathReclip"],
            )
            second_validation = validate_candidate_patch_assets(
                second_assets,
                surface,
                aggregate["candidateFloat32Sha256"],
                aggregate["roadPathReclip"],
            )
            if not first_validation.get("passes") or not second_validation.get("passes"):
                raise RoadSurfacePatchError("isolated independent asset validation failed")
            first_hashes = _write_private_asset_set(evidence / "assembly-1", first_assets)
            second_hashes = _write_private_asset_set(evidence / "assembly-2", second_assets)
            aggregate["deterministicAssemblies"] = {
                **deterministic,
                "firstPrivateOutputHashes": first_hashes,
                "secondPrivateOutputHashes": second_hashes,
                "firstIndependentValidation": first_validation,
                "secondIndependentValidation": second_validation,
                "publicOutputWritten": False,
            }
            aggregate["passes"] = bool(
                deterministic["passes"]
                and first_hashes == second_hashes
                and first_assets == second_assets
            )
    except Exception as exc:  # Preserve exact partial diagnostics after the sole attempt.
        aggregate["passes"] = False
        aggregate["error"] = f"{type(exc).__name__}: {exc}"
        aggregate.setdefault("phase", "exception")
        if solver_report is not None:
            aggregate["solver"] = solver_report
        if candidate is not None:
            aggregate["candidateFloat32Sha256"] = _digest(
                candidate.astype("<f4", copy=False).tobytes(order="C")
            )

    after_error = None
    protected_after: dict[str, str] = {}
    if inputs is not None:
        try:
            protected_after = _protected_hash_snapshot(ROOT, inputs)
        except Exception as exc:
            after_error = f"{type(exc).__name__}: {exc}"
    aggregate["protectedHashesAfter"] = protected_after
    aggregate["protectedHashesAfterError"] = after_error
    aggregate["protectedHashesMatch"] = bool(
        protected_before and protected_before == protected_after and after_error is None
    )
    config_hash_after = _digest(CONFIG_PATH.read_bytes())
    candidate_path = ROOT / road_surface.TEIGNMOUTH_CANDIDATE_OUTPUT
    aggregate["candidateConfigSha256Before"] = config_hash_before
    aggregate["candidateConfigSha256After"] = config_hash_after
    aggregate["candidateConfigUnchanged"] = config_hash_before == config_hash_after
    aggregate["candidateOutputStillAbsent"] = not candidate_path.exists()
    if not aggregate["protectedHashesMatch"]:
        aggregate["passes"] = False
    if not aggregate["candidateConfigUnchanged"] or not aggregate["candidateOutputStillAbsent"]:
        aggregate["passes"] = False
    aggregate["candidatePublicOutputWritten"] = False
    aggregate["realRunElapsedSeconds"] = time.monotonic() - start
    aggregate["evidencePath"] = evidence.relative_to(ROOT).as_posix()
    aggregate["witnessFiles"] = {
        filename: {
            "byteLength": (evidence / filename).stat().st_size,
            "sha256": _digest((evidence / filename).read_bytes()),
        }
        for filename in EVIDENCE_FILES
        if (evidence / filename).is_file()
    }
    _exclusive_write(evidence / "offline-aggregate.json", serialize_offline_report(aggregate))
    print(
        serialize_offline_report(
            {
                "passes": aggregate.get("passes", False),
                "phase": aggregate.get("phase"),
                "error": aggregate.get("error"),
                "candidateFloat32Sha256": aggregate.get("candidateFloat32Sha256"),
                "solver": aggregate.get("solver"),
                "gateResults": {
                    name: aggregate.get(name, {}).get("passes")
                    for name in aggregate.get("gateNames", [])
                },
                "evidencePath": aggregate["evidencePath"],
                "candidatePublicOutputWritten": False,
                "candidateOutputStillAbsent": aggregate["candidateOutputStillAbsent"],
                "protectedHashesMatch": aggregate["protectedHashesMatch"],
            }
        ).decode("utf-8"),
        flush=True,
    )
    return 0 if aggregate.get("passes") is True else 2


if __name__ == "__main__":
    sys.exit(main())
