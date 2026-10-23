"""Versioned validation context with accepted-grid identity and deadlines.

The v2 transition reuses the v1 gate calculations without changing their
arithmetic or report payloads. It adds accepted-height cache identity and a
validation deadline that marks the current and remaining gates unavailable.
"""

from __future__ import annotations

import hashlib
import math
import time
from collections.abc import Callable
from contextlib import contextmanager
from copy import deepcopy
from typing import Any

import numpy as np
from shapely.geometry import Polygon

from . import road_surface as road
from . import road_surface_patch as patch
from . import road_surface_validation_v1 as v1
from .road_surface_topology import (
    PlanarMesh,
    SourceOverlapIndex,
    TopologyError,
    _plane_coefficients,
    _polygon_parts,
    mesh_face_polygon,
)

VALIDATOR_VERSION = "teignmouth-offline-validator-v2"


class ValidationDeadlineExceeded(patch.RoadSurfacePatchError):
    """Raised when an offline validation phase reaches its fixed deadline."""


def _accepted_identity(heights: np.ndarray) -> tuple[tuple[int, ...], str, str, int]:
    canonical = np.asarray(heights, dtype="<f4").tobytes(order="C")
    return (
        tuple(int(value) for value in heights.shape),
        heights.dtype.str,
        hashlib.sha256(canonical).hexdigest(),
        id(heights),
    )


class ValidationContextV2(v1.ValidationContextV1):
    """V1 geometry caches bound to immutable-by-check accepted-grid identity."""

    def __post_init__(self) -> None:
        super().__post_init__()
        self._accepted_heights_ref = self.surface.accepted_heights
        self._accepted_identity = _accepted_identity(self._accepted_heights_ref)
        self._base_fingerprint = self.fingerprint
        digest = hashlib.sha256(b"teignmouth-offline-validation-context-v2\0")
        digest.update(self._base_fingerprint.encode("ascii"))
        digest.update(str(self._accepted_identity[0]).encode("ascii"))
        digest.update(b"\0")
        digest.update(self._accepted_identity[1].encode("ascii"))
        digest.update(b"\0")
        digest.update(self._accepted_identity[2].encode("ascii"))
        self.fingerprint = digest.hexdigest()
        self.validation_deadline_monotonic: float | None = None
        self.clock: Callable[[], float] = time.monotonic
        self._gate_validation_depth = 0

    def check_deadline(self) -> None:
        if (
            self.validation_deadline_monotonic is not None
            and self.clock() >= self.validation_deadline_monotonic
        ):
            raise ValidationDeadlineExceeded("validation cutoff reached")

    def require_surface(self, surface: patch.CompositeSurface) -> None:
        self.check_deadline()
        if surface is not self.surface:
            raise patch.RoadSurfacePatchError(
                "validator v2 cache identity does not match the bound surface"
            )
        heights = surface.accepted_heights
        if heights is not self._accepted_heights_ref:
            raise patch.RoadSurfacePatchError(
                "validator v2 accepted-heights array was replaced; rebuild validation context"
            )
        if self._gate_validation_depth:
            if (
                tuple(int(value) for value in heights.shape) != self._accepted_identity[0]
                or heights.dtype.str != self._accepted_identity[1]
            ):
                raise patch.RoadSurfacePatchError(
                    "validator v2 accepted-heights shape or dtype changed during a gate"
                )
            # The outer gate scope hashes exact accepted bytes and the full
            # surface fingerprint on exit. Nested per-building checks avoid
            # rehashing the entire mesh thousands of times.
            return
        if _accepted_identity(heights) != self._accepted_identity:
            raise patch.RoadSurfacePatchError(
                "validator v2 accepted-heights shape, dtype, or canonical Float32 bytes changed"
            )
        if v1._fingerprint_surface(surface) != self._base_fingerprint:
            raise patch.RoadSurfacePatchError(
                "validator v2 cache identity does not match the exact composite surface"
            )

    @contextmanager
    def gate_scope(self, surface: patch.CompositeSurface):
        """Bind each complete legacy gate while avoiding repeated mesh hashing."""
        self.require_surface(surface)
        self._gate_validation_depth += 1
        try:
            yield
        finally:
            self._gate_validation_depth -= 1
            if self._gate_validation_depth == 0:
                self.require_surface(surface)

    def bind_ownership(self, surface: patch.CompositeSurface) -> dict[str, Any]:
        """Compute the exact source-overlap result with a check per patch face."""
        self.require_surface(surface)
        mesh = surface.mesh
        self.check_deadline()
        source_index = SourceOverlapIndex.from_grid(
            surface.inputs.baseline,
            width_m=surface.inputs.width_m,
            depth_m=surface.inputs.depth_m,
            spacing_m=surface.inputs.spacing_m,
            first_row=mesh.bounds.first_row,
            last_row=mesh.bounds.last_row,
            first_column=mesh.bounds.first_column,
            last_column=mesh.bounds.last_column,
        )
        self.check_deadline()
        planar = PlanarMesh(
            mesh.vertices_xz,
            mesh.triangles,
            tuple(tuple(map(int, edge)) for edge in mesh.boundary_edges),
            (),
        )
        violations: list[dict[str, Any]] = []
        multiple_source_face_count = 0
        for face_id in range(len(mesh.triangles)):
            self.check_deadline()
            try:
                overlaps = source_index.overlaps(
                    mesh_face_polygon(planar, face_id), area_tolerance_m2=1e-12
                )
                if len(overlaps) > 1:
                    multiple_source_face_count += 1
            except TopologyError as exc:
                violations.append(
                    {
                        "reason": "source overlap index rejected topology",
                        "error": str(exc),
                    }
                )
                break
        report = {
            "tested": True,
            "patchTriangleCount": int(len(mesh.triangles)),
            "sourceHalfCellOwnershipViolationCount": len(violations),
            "facesOverlappingMultipleSourceTriangles": multiple_source_face_count,
            "firstOwnershipViolations": violations[:8],
            "coverageMethod": "spatially indexed source triangle overlap with exact face coverage",
            "areaToleranceM2": 1e-12,
            "passes": not violations,
        }
        if report.get("tested") is not True or report.get("patchTriangleCount") != len(
            mesh.triangles
        ):
            raise patch.RoadSurfacePatchError("validator v2 ownership report is incomplete")
        self._ownership_report = deepcopy(report)
        self._ownership_fingerprint = self.fingerprint
        return deepcopy(report)


def _unavailable(reason: str) -> dict[str, Any]:
    return {"passes": False, "available": False, "status": "unavailable_deadline", "reason": reason}


def _affine_overlay_extrema_v2(
    mesh: PlanarMesh,
    candidate_heights: np.ndarray,
    source_index: SourceOverlapIndex,
    check_deadline: Callable[[], None],
    *,
    clip_geometry: Any | None = None,
    area_tolerance_m2: float = 1e-12,
) -> dict[str, Any]:
    """V1-identical overlay arithmetic with deadline checks at every patch face."""
    values = np.asarray(candidate_heights, dtype=np.float64)
    if values.shape != (len(mesh.vertices_xz),) or not np.isfinite(values).all():
        raise TopologyError("candidate heights do not match the finite topology vertex buffer")
    if source_index.heights is None:
        raise TopologyError("overlay extrema require source heights in the overlap index")
    max_fill = -math.inf
    min_cut = math.inf
    overlay_count = 0
    tested_vertices = 0
    maximum_fill_at = None
    maximum_cut_at = None
    source_plane_coefficients = []
    for index in range(len(source_index.source_ids)):
        check_deadline()
        source_plane_coefficients.append(
            _plane_coefficients(
                np.asarray(source_index.vertices_xz[index], dtype=np.float64),
                np.asarray(source_index.heights[index], dtype=np.float64),
            )
        )
    for face_id, face in enumerate(mesh.triangles):
        check_deadline()
        patch_ids = face.astype(np.int64)
        patch_xz = mesh.vertices_xz[patch_ids]
        patch_y = values[patch_ids]
        patch_polygon = Polygon(patch_xz)
        patch_plane = _plane_coefficients(patch_xz, patch_y)
        expected_area = (
            float(patch_polygon.area)
            if clip_geometry is None
            else float(patch_polygon.intersection(clip_geometry).area)
        )
        candidate_indices = sorted(
            int(index) for index in source_index.tree.query(patch_polygon, predicate="intersects")
        )
        covered_area = 0.0
        for source_index_at in candidate_indices:
            source_polygon = source_index.geometries[source_index_at]
            clipped = patch_polygon.intersection(source_polygon)
            if clip_geometry is not None and not clipped.is_empty:
                clipped = clipped.intersection(clip_geometry)
            if clipped.is_empty or clipped.area <= area_tolerance_m2:
                continue
            covered_area += float(clipped.area)
            source_plane = source_plane_coefficients[source_index_at]
            for polygon in _polygon_parts(clipped):
                coordinates = [(float(x), float(z)) for x, z in list(polygon.exterior.coords)[:-1]]
                for ring in polygon.interiors:
                    coordinates.extend((float(x), float(z)) for x, z in list(ring.coords)[:-1])
                for x, z in coordinates:
                    candidate_y = float(patch_plane[0] * x + patch_plane[1] * z + patch_plane[2])
                    baseline_y = float(source_plane[0] * x + source_plane[1] * z + source_plane[2])
                    delta = candidate_y - baseline_y
                    if delta > max_fill:
                        max_fill = delta
                        maximum_fill_at = {
                            "patchFaceId": face_id,
                            "sourceTriangleId": source_index.source_ids[source_index_at],
                            "localXZ": [x, z],
                        }
                    if delta < min_cut:
                        min_cut = delta
                        maximum_cut_at = {
                            "patchFaceId": face_id,
                            "sourceTriangleId": source_index.source_ids[source_index_at],
                            "localXZ": [x, z],
                        }
                    tested_vertices += 1
            overlay_count += 1
        if source_index.partition_verified:
            tolerance = max(area_tolerance_m2, expected_area * 1e-10)
            if abs(covered_area - expected_area) > tolerance:
                raise TopologyError(
                    "patch face is not covered by the verified source triangle partition: "
                    f"face={face_id}, faceArea={patch_polygon.area:.17g}, "
                    f"expectedOverlayArea={expected_area:.17g}, coveredArea={covered_area:.17g}"
                )
        else:
            source_index.overlaps(patch_polygon, area_tolerance_m2=area_tolerance_m2)
    if overlay_count == 0 or tested_vertices == 0 or not math.isfinite(max_fill + min_cut):
        raise TopologyError("source overlay did not produce finite intersection extrema")
    return {
        "overlayFaceCount": overlay_count,
        "testedIntersectionVertexCount": tested_vertices,
        "maximumFillFromSourceM": max_fill,
        "maximumCutFromSourceM": min_cut,
        "maximumAbsoluteChangeFromSourceM": max(abs(max_fill), abs(min_cut)),
        "maximumFillLocation": maximum_fill_at,
        "maximumCutLocation": maximum_cut_at,
    }


def _earthwork_overlay_v2(
    surface: patch.CompositeSurface, context: ValidationContextV2
) -> dict[str, Any]:
    started = time.perf_counter()
    context.require_surface(surface)
    ownership = context.ownership_report
    if ownership is None or context._ownership_fingerprint != context.fingerprint:
        raise patch.RoadSurfacePatchError(
            "validator v2 earthwork requires prior ownership validation"
        )
    mesh = surface.mesh
    context.check_deadline()
    source_at_vertices = road._sample_grid_many(
        surface.inputs.baseline,
        mesh.vertices_xz[:, 0],
        mesh.vertices_xz[:, 1],
        surface.inputs.spacing_m,
    )
    signed_changes = surface.patch_heights.astype(np.float64) - source_at_vertices
    context.check_deadline()
    source_index = SourceOverlapIndex.from_grid(
        surface.inputs.baseline,
        width_m=surface.inputs.width_m,
        depth_m=surface.inputs.depth_m,
        spacing_m=surface.inputs.spacing_m,
        first_row=mesh.bounds.first_row,
        last_row=mesh.bounds.last_row,
        first_column=mesh.bounds.first_column,
        last_column=mesh.bounds.last_column,
    )
    context.check_deadline()
    planar = PlanarMesh(
        mesh.vertices_xz,
        mesh.triangles,
        tuple(tuple(map(int, edge)) for edge in mesh.boundary_edges),
        (),
    )
    try:
        overlay = _affine_overlay_extrema_v2(
            planar, surface.patch_heights, source_index, context.check_deadline
        )
    except TopologyError as exc:
        raise patch.RoadSurfacePatchError(f"earthwork overlay verification failed: {exc}") from exc
    maximum_fill = float(overlay["maximumFillFromSourceM"])
    minimum_fill = float(overlay["maximumCutFromSourceM"])
    maximum_absolute = max(abs(maximum_fill), abs(minimum_fill))
    maximum_index = int(np.argmax(np.abs(signed_changes))) if signed_changes.size else None
    maximum_fill_index = int(np.argmax(signed_changes)) if signed_changes.size else None
    maximum_cut_index = int(np.argmin(signed_changes)) if signed_changes.size else None

    def vertex_record(index: int | None) -> dict[str, Any] | None:
        if index is None:
            return None
        return {
            "vertexId": index,
            "localXZ": mesh.vertices_xz[index].tolist(),
            "signedChangeM": float(signed_changes[index]),
        }

    report = {
        "tested": True,
        "method": "affine difference on every exact patch/source triangle intersection polygon",
        "overlayFaceCount": int(overlay["overlayFaceCount"]),
        "testedIntersectionVertexCount": int(overlay["testedIntersectionVertexCount"]),
        "sourceTriangleOwnershipPasses": ownership["passes"],
        "sourceTriangleOwnershipViolationCount": ownership["sourceHalfCellOwnershipViolationCount"],
        "maximumAbsoluteEarthworkChangeFromSourceM": maximum_absolute,
        "maximumFillFromSourceM": maximum_fill,
        "maximumCutFromSourceM": minimum_fill,
        "maximumAbsoluteChangeVertex": vertex_record(maximum_index),
        "maximumFillVertex": vertex_record(maximum_fill_index),
        "maximumCutVertex": vertex_record(maximum_cut_index),
        "absoluteChangeLimitM": 5.0,
        "passes": bool(
            ownership["passes"] and np.isfinite(signed_changes).all() and maximum_absolute < 5.0
        ),
    }
    context.gate_seconds["earthworkOverlay"] = time.perf_counter() - started
    return report


def _accepted_plane_refinement_v2(
    surface: patch.CompositeSurface,
    context: ValidationContextV2,
    influence: Polygon,
) -> dict[str, Any]:
    """V1-identical accepted-plane check with per-patch-face deadline checks."""
    mesh = surface.mesh
    accepted = surface.accepted_heights
    spacing_m = surface.inputs.spacing_m
    source_index = SourceOverlapIndex.from_grid(
        accepted,
        width_m=(accepted.shape[1] - 1) * spacing_m,
        depth_m=(accepted.shape[0] - 1) * spacing_m,
        spacing_m=spacing_m,
        first_row=mesh.bounds.first_row,
        last_row=mesh.bounds.last_row,
        first_column=mesh.bounds.first_column,
        last_column=mesh.bounds.last_column,
    )
    context.check_deadline()
    patch_domain = Polygon(
        (
            (mesh.vertices_xz[:, 0].min(), mesh.vertices_xz[:, 1].min()),
            (mesh.vertices_xz[:, 0].max(), mesh.vertices_xz[:, 1].min()),
            (mesh.vertices_xz[:, 0].max(), mesh.vertices_xz[:, 1].max()),
            (mesh.vertices_xz[:, 0].min(), mesh.vertices_xz[:, 1].max()),
        )
    )
    clip_geometry = patch_domain.difference(influence)
    if clip_geometry.is_empty:
        return {
            "tested": True,
            "method": "exact affine extrema at every patch/source-triangle overlay vertex",
            "overlayCount": 0,
            "testedOverlayVertexCount": 0,
            "maximumAcceptedPlaneDeviationM": 0.0,
            "maximumDeviationLocation": None,
            "maximumAllowedDeviationM": 0.001,
            "passes": True,
        }
    planar = PlanarMesh(
        mesh.vertices_xz.astype(np.float64, copy=False),
        mesh.triangles.astype(np.uint32, copy=False),
        (),
        (),
    )
    try:
        extrema = _affine_overlay_extrema_v2(
            planar,
            mesh.base_y.astype(np.float64, copy=False),
            source_index,
            context.check_deadline,
            clip_geometry=clip_geometry,
        )
    except TopologyError as exc:
        raise patch.RoadSurfacePatchError(
            f"accepted-plane overlay verification failed: {exc}"
        ) from exc
    maximum_error = float(extrema["maximumAbsoluteChangeFromSourceM"])
    sample_count = int(extrema["testedIntersectionVertexCount"])
    report = {
        "tested": True,
        "method": "exact affine extrema at every patch/source-triangle overlay vertex",
        "overlayCount": int(extrema["overlayFaceCount"]),
        "testedOverlayVertexCount": sample_count,
        "maximumAcceptedPlaneDeviationM": maximum_error,
        "maximumDeviationLocation": (
            extrema["maximumFillLocation"]
            if float(extrema["maximumFillFromSourceM"])
            >= abs(float(extrema["maximumCutFromSourceM"]))
            else extrema["maximumCutLocation"]
        ),
        "maximumAllowedDeviationM": 0.001,
        "passes": maximum_error <= 0.001,
    }
    return report


def validate_offline_candidate_v2(
    surface: patch.CompositeSurface,
    influence: Polygon,
    constraints: list[dict[str, Any]],
    solver_report: dict[str, Any],
    accepted_preview_hashes: dict[str, str],
    *,
    context: ValidationContextV2 | None = None,
    validation_deadline_monotonic: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[dict[str, Any], ValidationContextV2]:
    """Run unchanged gates and stop with explicit unavailable states at deadline."""
    context = context or ValidationContextV2(surface)
    context.validation_deadline_monotonic = validation_deadline_monotonic
    context.clock = clock
    entry_deadline_error: str | None = None
    try:
        context.require_surface(surface)
    except ValidationDeadlineExceeded as exc:
        entry_deadline_error = str(exc)

    candidate_bytes = surface.patch_heights.astype("<f4", copy=False).tobytes(order="C")
    candidate_hash = hashlib.sha256(candidate_bytes).hexdigest()
    input_bindings_pass = bool(
        surface.inputs.release_id == road.CURRENT_RELEASE_ID
        and accepted_preview_hashes == patch.ACCEPTED_PREVIEW_HASHES
        and surface.inputs.source_hashes.get("heightfield.f32", {}).get("sha256")
        == surface.inputs.manifest.get("heightfield", {}).get("sha256")
        and surface.inputs.road_payload.get("worldId") == surface.inputs.manifest.get("id")
        and surface.inputs.road_payload.get("sceneProfile") == "current_2km"
    )
    reports: dict[str, Any] = {
        "inputBindings": {
            "passes": input_bindings_pass,
            "releaseId": surface.inputs.release_id,
            "releaseSourceHashes": surface.inputs.source_hashes,
            "acceptedPreviewHashes": accepted_preview_hashes,
            "acceptedPreviewHashesMatchPinned": accepted_preview_hashes
            == patch.ACCEPTED_PREVIEW_HASHES,
        },
        "solverWitness": {
            "passes": bool(
                solver_report.get("converged")
                and solver_report.get("candidateFloat32Sha256") == candidate_hash
                and solver_report.get("quantizedValidation", {}).get("passes")
            ),
            "converged": bool(solver_report.get("converged")),
            "candidateFloat32Sha256": candidate_hash,
            "candidateFloat32ByteLength": len(candidate_bytes),
            "solverCandidateFloat32Sha256": solver_report.get("candidateFloat32Sha256"),
            "quantizedValidation": solver_report.get("quantizedValidation"),
            "iterations": solver_report.get("iterations"),
            "elapsedSeconds": solver_report.get("elapsedSeconds"),
        },
    }

    gate_functions: dict[str, Callable[[], dict[str, Any]]] = {}

    def float32_validation() -> dict[str, Any]:
        source_nodes = road._sample_grid_many(
            surface.inputs.baseline,
            surface.mesh.vertices_xz[:, 0],
            surface.mesh.vertices_xz[:, 1],
            surface.inputs.spacing_m,
        )
        edges = np.asarray(sorted(surface.mesh.edge_counts), dtype=np.int64)
        edge_lengths = np.linalg.norm(
            surface.mesh.vertices_xz[edges[:, 0]] - surface.mesh.vertices_xz[edges[:, 1]], axis=1
        )
        edge_source_deltas = np.abs(source_nodes[edges[:, 0]] - source_nodes[edges[:, 1]])
        edge_limits = edge_source_deltas + patch.PATCH_MAX_ADDED_GRADIENT * edge_lengths
        fixed_mask = patch._fixed_patch_vertices(surface.mesh, influence)
        fixed_mask[np.unique(surface.mesh.boundary_edges)] = True
        return patch._validate_quantized_phase_one(
            surface.mesh,
            surface.patch_heights,
            source_nodes,
            edges,
            edge_limits,
            constraints,
            fixed_mask,
            surface.mesh.base_y.astype(np.float64),
            influence,
            solver_tolerance_m=float(solver_report.get("solverNumericalToleranceM", 2e-5)),
        )

    gate_functions["float32FinalValidation"] = float32_validation
    gate_functions["topology"] = lambda: patch.patch_topology_report(
        surface.mesh, surface.inputs.spacing_m
    )
    gate_functions["sourceTriangleOwnership"] = lambda: context.bind_ownership(surface)
    gate_functions["earthworkOverlay"] = lambda: _earthwork_overlay_v2(surface, context)
    gate_functions["acceptedPlaneRefinement"] = lambda: _accepted_plane_refinement_v2(
        surface, context, influence
    )
    gate_functions["compositeTerrain"] = lambda: patch.verify_composite_terrain(
        surface, influence, fail_closed=False
    )
    gate_functions["localCorridorLongitudinal"] = lambda: patch.composite_local_and_corridor_report(
        surface, fail_closed=False
    )
    gate_functions["completeBuildingFootprints"] = lambda: v1.composite_building_base_report_v1(
        surface, context, fail_closed=False
    )
    gate_functions["roadPathReclip"] = lambda: patch.reclip_affected_road_batches(surface)
    reclipped_roads: dict[str, Any] = {"groups": {}}
    gate_functions["walkClearance"] = lambda: patch.composite_walk_clearance_report(
        surface, reclipped_roads
    )

    # `inputBindings` and `solverWitness` are report identities, not members of
    # the frozen 12-gate result list. Iterate the frozen list exactly as v1.
    incomplete_reason: str | None = entry_deadline_error
    for name in patch.PATCH_OFFLINE_GATE_NAMES[2:]:
        if incomplete_reason is not None:
            reports[name] = _unavailable(incomplete_reason)
            continue
        started = time.perf_counter()
        try:
            context.check_deadline()
            with context.gate_scope(surface):
                result = gate_functions[name]()
            context.check_deadline()
            if name == "roadPathReclip":
                reclipped_roads = result
                gate_functions["walkClearance"] = lambda roads=result: (
                    patch.composite_walk_clearance_report(surface, roads)
                )
            reports[name] = result
        except ValidationDeadlineExceeded as exc:
            incomplete_reason = str(exc)
            reports[name] = _unavailable(incomplete_reason)
        except patch.RoadSurfacePatchError as exc:
            reports[name] = {"passes": False, "error": str(exc)}
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            reports[name] = {"passes": False, "error": str(exc)}
        context.gate_seconds[name] = time.perf_counter() - started

    if entry_deadline_error is not None:
        reports["inputBindings"] = _unavailable(entry_deadline_error)
        reports["solverWitness"] = _unavailable(entry_deadline_error)

    reports["passes"] = bool(
        incomplete_reason is None
        and all(
            reports.get(name, {}).get("passes", False) for name in patch.PATCH_OFFLINE_GATE_NAMES
        )
    )
    reports["gateNames"] = list(patch.PATCH_OFFLINE_GATE_NAMES)
    reports["candidateFloat32Sha256"] = candidate_hash
    reports["candidateFloat32ByteLength"] = len(candidate_bytes)
    reports["candidateFloat32Finite"] = bool(np.isfinite(surface.patch_heights).all())
    reports["validatorVersion"] = VALIDATOR_VERSION
    reports["validationComplete"] = incomplete_reason is None
    if incomplete_reason is not None:
        reports["validationStatus"] = "incomplete_deadline"
        reports["validationUnavailableReason"] = incomplete_reason
    return reports, context
