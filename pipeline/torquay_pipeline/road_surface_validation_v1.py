"""Versioned, output-equivalent offline validation accelerators.

This module adds an explicit validator transition without editing the frozen
road-surface mesher/solver or the topology-study runner. It preserves the
legacy report fields and gate implementations while caching invocation-local
geometry objects and reusing source-triangle ownership only for the exact
same surface and pinned source object.
"""

from __future__ import annotations

import hashlib
import math
import time
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from shapely.geometry import Point, Polygon

from . import road_surface as road
from . import road_surface_patch as patch
from .road_surface_topology import PlanarMesh, SourceOverlapIndex, affine_surface_overlay_extrema

VALIDATOR_VERSION = "teignmouth-offline-validator-v1"
MAX_COARSE_POLYGON_CACHE_ENTRIES = 8_192
MAX_PATCH_FACE_POLYGON_CACHE_ENTRIES = 16_384
MAX_BUILDING_SAMPLE_BATCH = 8_192


def _strictly_disjoint(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> bool:
    """Return true only for separated bounds; touching bounds still intersect."""
    return bool(a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _fingerprint_surface(surface: patch.CompositeSurface) -> str:
    """Bind reuse to exact topology, Float32 heights, source and release identity."""
    digest = hashlib.sha256(b"teignmouth-offline-validation-context-v1\0")
    mesh = surface.mesh
    inputs = surface.inputs
    digest.update(mesh.vertices_xz.astype("<f8", copy=False).tobytes(order="C"))
    digest.update(mesh.triangles.astype("<u4", copy=False).tobytes(order="C"))
    digest.update(mesh.base_y.astype("<f4", copy=False).tobytes(order="C"))
    digest.update(surface.patch_heights.astype("<f4", copy=False).tobytes(order="C"))
    digest.update(inputs.baseline.astype("<f4", copy=False).tobytes(order="C"))
    digest.update(str(inputs.release_id).encode("ascii"))
    digest.update(
        f"{inputs.spacing_m:.17g}:{inputs.width_m:.17g}:{inputs.depth_m:.17g}".encode("ascii")
    )
    digest.update(
        str(inputs.source_hashes.get("heightfield.f32", {}).get("sha256", "")).encode("ascii")
    )
    return digest.hexdigest()


@dataclass
class ValidationContextV1:
    """Bounded invocation-local geometry and exact ownership result cache."""

    surface: patch.CompositeSurface
    maximum_coarse_entries: int = MAX_COARSE_POLYGON_CACHE_ENTRIES
    maximum_face_entries: int = MAX_PATCH_FACE_POLYGON_CACHE_ENTRIES
    fingerprint: str = field(init=False)
    baseline_coarse_polygons: OrderedDict[tuple[int, int, int], Polygon] = field(
        default_factory=OrderedDict, init=False
    )
    accepted_coarse_polygons: OrderedDict[tuple[int, int, int], Polygon] = field(
        default_factory=OrderedDict, init=False
    )
    patch_face_polygons: OrderedDict[int, Polygon] = field(default_factory=OrderedDict, init=False)
    patch_face_bounds: OrderedDict[int, tuple[float, float, float, float]] = field(
        default_factory=OrderedDict, init=False
    )
    triangle_xz: np.ndarray = field(init=False)
    triangle_y: np.ndarray = field(init=False)
    triangle_bounds: np.ndarray = field(init=False)
    patch_domain_bounds: tuple[float, float, float, float] = field(init=False)
    baseline_matches_accepted: bool = field(init=False)
    _ownership_report: dict[str, Any] | None = field(default=None, init=False, repr=False)
    _ownership_fingerprint: str | None = field(default=None, init=False, repr=False)
    stats: dict[str, int] = field(default_factory=dict, init=False)
    gate_seconds: dict[str, float] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.fingerprint = _fingerprint_surface(self.surface)
        mesh = self.surface.mesh
        triangles = mesh.triangles.astype(np.int64, copy=False)
        self.triangle_xz = mesh.vertices_xz[triangles].astype(np.float64, copy=False)
        self.triangle_y = self.surface.patch_heights[triangles].astype(np.float64, copy=False)
        self.triangle_bounds = np.column_stack(
            (
                np.min(self.triangle_xz[:, :, 0], axis=1),
                np.min(self.triangle_xz[:, :, 1], axis=1),
                np.max(self.triangle_xz[:, :, 0], axis=1),
                np.max(self.triangle_xz[:, :, 1], axis=1),
            )
        )
        self.patch_domain_bounds = (
            float(np.min(mesh.vertices_xz[:, 0])),
            float(np.min(mesh.vertices_xz[:, 1])),
            float(np.max(mesh.vertices_xz[:, 0])),
            float(np.max(mesh.vertices_xz[:, 1])),
        )
        self.baseline_matches_accepted = bool(
            np.array_equal(self.surface.inputs.baseline, self.surface.accepted_heights)
        )
        self.stats.update(
            {
                "baselineCoarsePolygonHits": 0,
                "acceptedCoarsePolygonHits": 0,
                "patchFacePolygonHits": 0,
                "baselineCoarsePolygonCreations": 0,
                "acceptedCoarsePolygonCreations": 0,
                "patchFacePolygonCreations": 0,
                "bboxDisjointRejections": 0,
                "baselineIntersectionCalls": 0,
                "acceptedIntersectionCalls": 0,
                "patchFaceIntersectionCalls": 0,
                "disjointBuildingFastPaths": 0,
                "pairedGridBuildings": 0,
                "pairedGridIntersectionCalls": 0,
                "pairedGridSampleBatches": 0,
                "pairedGridSamplePoints": 0,
            }
        )

    def require_surface(self, surface: patch.CompositeSurface) -> None:
        if surface is not self.surface or _fingerprint_surface(surface) != self.fingerprint:
            raise patch.RoadSurfacePatchError(
                "validator v1 cache identity does not match the exact composite surface"
            )

    @property
    def ownership_report(self) -> dict[str, Any] | None:
        """Return a defensive copy so downstream callers cannot mutate the bound report."""
        return deepcopy(self._ownership_report)

    def bind_ownership(self, surface: patch.CompositeSurface) -> dict[str, Any]:
        """Compute ownership from the exact bound mesh and store it defensively."""
        self.require_surface(surface)
        report = patch.patch_source_triangle_ownership_report(surface.mesh, surface.inputs)
        if report.get("tested") is not True or report.get("patchTriangleCount") != len(
            surface.mesh.triangles
        ):
            raise patch.RoadSurfacePatchError(
                "validator v1 ownership report is incomplete or stale"
            )
        self._ownership_report = deepcopy(report)
        self._ownership_fingerprint = self.fingerprint
        return deepcopy(report)

    def _bounded_put(self, cache: OrderedDict, key: Any, value: Polygon, maximum: int) -> None:
        if maximum <= 0:
            return
        cache[key] = value
        cache.move_to_end(key)
        while len(cache) > maximum:
            cache.popitem(last=False)

    def coarse_bounds(self, row: int, column: int) -> tuple[float, float, float, float]:
        inputs = self.surface.inputs
        x0 = column * inputs.spacing_m - inputs.width_m / 2
        z0 = row * inputs.spacing_m - inputs.depth_m / 2
        return (x0, z0, x0 + inputs.spacing_m, z0 + inputs.spacing_m)

    def feature_outside_patch(self, feature: dict[str, Any]) -> bool:
        """Conservative strict-bounds proof that every polygon misses patch support."""
        polygons = feature["geometry"]["polygons"]
        if not polygons:
            raise road.RoadSurfaceError(f"building {feature.get('id')} has no footprint polygons")
        for polygon_record in polygons:
            polygon = Polygon(
                polygon_record["exteriorXZ"], polygon_record.get("interiorRingsXZ", [])
            )
            if polygon.is_empty or not polygon.is_valid:
                raise road.RoadSurfaceError(
                    f"building {feature.get('id')} has invalid footprint geometry"
                )
            if not _strictly_disjoint(polygon.bounds, self.patch_domain_bounds):
                return False
        return True

    def coarse_polygon(self, kind: str, row: int, column: int, half: int) -> Polygon:
        key = (row, column, half)
        cache = (
            self.baseline_coarse_polygons if kind == "baseline" else self.accepted_coarse_polygons
        )
        hit_key = "baselineCoarsePolygonHits" if kind == "baseline" else "acceptedCoarsePolygonHits"
        creation_key = (
            "baselineCoarsePolygonCreations"
            if kind == "baseline"
            else "acceptedCoarsePolygonCreations"
        )
        polygon = cache.get(key)
        if polygon is not None:
            cache.move_to_end(key)
            self.stats[hit_key] += 1
            return polygon

        inputs = self.surface.inputs
        x0 = column * inputs.spacing_m - inputs.width_m / 2
        x1 = x0 + inputs.spacing_m
        z0 = row * inputs.spacing_m - inputs.depth_m / 2
        z1 = z0 + inputs.spacing_m
        if kind == "baseline":
            coords = ((x0, z0), (x0, z1), (x1, z0)) if half == 0 else ((x1, z0), (x0, z1), (x1, z1))
        else:
            coords = ((x0, z0), (x1, z0), (x0, z1)) if half == 0 else ((x1, z1), (x0, z1), (x1, z0))
        polygon = Polygon(coords)
        self._bounded_put(cache, key, polygon, self.maximum_coarse_entries)
        self.stats[creation_key] += 1
        return polygon

    def patch_face_polygon(self, triangle_id: int) -> Polygon:
        polygon = self.patch_face_polygons.get(triangle_id)
        if polygon is not None:
            self.patch_face_polygons.move_to_end(triangle_id)
            if triangle_id in self.patch_face_bounds:
                self.patch_face_bounds.move_to_end(triangle_id)
            self.stats["patchFacePolygonHits"] += 1
            return polygon
        polygon = Polygon(self.triangle_xz[triangle_id])
        self._bounded_put(self.patch_face_polygons, triangle_id, polygon, self.maximum_face_entries)
        if triangle_id in self.patch_face_polygons:
            self.patch_face_bounds[triangle_id] = polygon.bounds
            self.patch_face_bounds.move_to_end(triangle_id)
            while len(self.patch_face_bounds) > self.maximum_face_entries:
                self.patch_face_bounds.popitem(last=False)
        retained_ids = set(self.patch_face_polygons)
        for stale_id in set(self.patch_face_bounds) - retained_ids:
            del self.patch_face_bounds[stale_id]
        self.stats["patchFacePolygonCreations"] += 1
        return polygon

    def patch_face_bounds_for(self, triangle_id: int) -> tuple[float, float, float, float]:
        bounds = self.patch_face_bounds.get(triangle_id)
        if bounds is not None:
            self.patch_face_bounds.move_to_end(triangle_id)
            return bounds
        bounds = self.patch_face_polygon(triangle_id).bounds
        if triangle_id in self.patch_face_polygons:
            self.patch_face_bounds[triangle_id] = bounds
            if len(self.patch_face_bounds) > self.maximum_face_entries:
                self.patch_face_bounds.popitem(last=False)
        return bounds


def _maximum_under_building_v1(
    feature: dict[str, Any],
    heights: np.ndarray,
    inputs: Any,
    context: ValidationContextV1,
) -> float:
    """Legacy-ordered baseline maximum with bounded polygon reuse and safe bbox rejects."""
    maximum = float("-inf")
    for polygon_record in feature["geometry"]["polygons"]:
        exterior = polygon_record["exteriorXZ"]
        holes = polygon_record.get("interiorRingsXZ", [])
        polygon = Polygon(exterior, holes)
        if polygon.is_empty or not polygon.is_valid:
            raise road.RoadSurfaceError(
                f"building {feature.get('id')} has invalid footprint geometry"
            )
        polygon_bounds = polygon.bounds
        min_x, min_z, max_x, max_z = polygon_bounds
        first_column = max(0, math.floor((min_x + inputs.width_m / 2) / inputs.spacing_m))
        last_column = min(
            inputs.columns - 2, math.floor((max_x + inputs.width_m / 2) / inputs.spacing_m)
        )
        first_row = max(0, math.floor((min_z + inputs.depth_m / 2) / inputs.spacing_m))
        last_row = min(inputs.rows - 2, math.floor((max_z + inputs.depth_m / 2) / inputs.spacing_m))
        for row in range(first_row, last_row + 1):
            for column in range(first_column, last_column + 1):
                for half in (0, 1):
                    if _strictly_disjoint(polygon_bounds, context.coarse_bounds(row, column)):
                        context.stats["bboxDisjointRejections"] += 1
                        continue
                    triangle = context.coarse_polygon("baseline", row, column, half)
                    context.stats["baselineIntersectionCalls"] += 1
                    overlap = polygon.intersection(triangle)
                    if overlap.is_empty:
                        continue
                    for x, z in road._geometry_points(overlap):
                        maximum = max(maximum, road._sample_grid(heights, x, z, inputs.spacing_m))
    if not math.isfinite(maximum):
        raise road.RoadSurfaceError(
            f"building {feature.get('id')} has no samples under its footprint"
        )
    return maximum


def _paired_grid_maxima_under_building_v1(
    feature: dict[str, Any],
    surface: patch.CompositeSurface,
    context: ValidationContextV1,
) -> tuple[float, float]:
    """Evaluate source and accepted-grid maxima from one exact intersection traversal."""
    inputs = surface.inputs
    baseline_maximum = float("-inf")
    accepted_maximum = float("-inf")
    polygon_records = feature["geometry"]["polygons"]
    if not polygon_records:
        raise road.RoadSurfaceError(f"building {feature.get('id')} has no footprint polygons")
    pending_x: list[float] = []
    pending_z: list[float] = []

    def flush_sample_batch() -> None:
        nonlocal baseline_maximum, accepted_maximum
        if not pending_x:
            return
        x_values = np.asarray(pending_x, dtype=np.float64)
        z_values = np.asarray(pending_z, dtype=np.float64)
        half_width = (inputs.columns - 1) * inputs.spacing_m / 2
        half_depth = (inputs.rows - 1) * inputs.spacing_m / 2
        invalid = (
            ~np.isfinite(x_values)
            | ~np.isfinite(z_values)
            | (x_values < -half_width)
            | (x_values > half_width)
            | (z_values < -half_depth)
            | (z_values > half_depth)
        )
        if invalid.any():
            index = int(np.flatnonzero(invalid)[0])
            # Preserve the scalar sampler's fail-closed boundary behavior.
            road._sample_grid(
                inputs.baseline,
                float(x_values[index]),
                float(z_values[index]),
                inputs.spacing_m,
            )
        baseline_values = road._sample_grid_many(
            inputs.baseline, x_values, z_values, inputs.spacing_m
        )
        accepted_values = road._sample_grid_many(
            surface.accepted_heights, x_values, z_values, inputs.spacing_m
        )
        if np.isfinite(baseline_values).all() and np.isfinite(accepted_values).all():
            baseline_maximum = max(baseline_maximum, float(np.max(baseline_values)))
            accepted_maximum = max(accepted_maximum, float(np.max(accepted_values)))
        else:
            # Match Python max's exceptional-value behavior if inputs are malformed.
            for x, z in zip(pending_x, pending_z, strict=True):
                baseline_maximum = max(
                    baseline_maximum,
                    road._sample_grid(inputs.baseline, x, z, inputs.spacing_m),
                )
                accepted_maximum = max(
                    accepted_maximum,
                    road._sample_grid(surface.accepted_heights, x, z, inputs.spacing_m),
                )
        context.stats["pairedGridSampleBatches"] += 1
        context.stats["pairedGridSamplePoints"] += len(pending_x)
        pending_x.clear()
        pending_z.clear()

    for polygon_record in polygon_records:
        polygon = Polygon(polygon_record["exteriorXZ"], polygon_record.get("interiorRingsXZ", []))
        if polygon.is_empty or not polygon.is_valid:
            raise road.RoadSurfaceError(
                f"building {feature.get('id')} has invalid footprint geometry"
            )
        min_x, min_z, max_x, max_z = polygon.bounds
        first_column = max(0, math.floor((min_x + inputs.width_m / 2) / inputs.spacing_m))
        last_column = min(
            inputs.columns - 2, math.floor((max_x + inputs.width_m / 2) / inputs.spacing_m)
        )
        first_row = max(0, math.floor((min_z + inputs.depth_m / 2) / inputs.spacing_m))
        last_row = min(inputs.rows - 2, math.floor((max_z + inputs.depth_m / 2) / inputs.spacing_m))
        bounds = polygon.bounds
        for row in range(first_row, last_row + 1):
            for column in range(first_column, last_column + 1):
                if _strictly_disjoint(bounds, context.coarse_bounds(row, column)):
                    context.stats["bboxDisjointRejections"] += 1
                    continue
                triangle = context.coarse_polygon("baseline", row, column, 0)
                for half in (0, 1):
                    if half:
                        triangle = context.coarse_polygon("baseline", row, column, half)
                    context.stats["pairedGridIntersectionCalls"] += 1
                    overlap = polygon.intersection(triangle)
                    if overlap.is_empty:
                        continue
                    for x, z in road._geometry_points(overlap):
                        pending_x.append(x)
                        pending_z.append(z)
                        if len(pending_x) >= MAX_BUILDING_SAMPLE_BATCH:
                            flush_sample_batch()
    flush_sample_batch()
    if not math.isfinite(baseline_maximum):
        raise road.RoadSurfaceError(
            f"building {feature.get('id')} has no samples under its footprint"
        )
    if not math.isfinite(accepted_maximum):
        raise patch.RoadSurfacePatchError(
            "building footprint has no samples on the composite surface"
        )
    context.stats["pairedGridBuildings"] += 1
    return baseline_maximum, accepted_maximum


def _composite_maximum_under_polygon_v1(
    polygon: Polygon,
    surface: patch.CompositeSurface,
    context: ValidationContextV1,
) -> float:
    """Legacy-ordered exact footprint maximum with invocation-local triangle reuse."""
    inputs, mesh = surface.inputs, surface.mesh
    min_x, min_z, max_x, max_z = polygon.bounds
    polygon_bounds = polygon.bounds
    first_column = max(0, math.floor((min_x + inputs.width_m / 2) / inputs.spacing_m))
    last_column = min(
        inputs.columns - 2, math.floor((max_x + inputs.width_m / 2) / inputs.spacing_m)
    )
    first_row = max(0, math.floor((min_z + inputs.depth_m / 2) / inputs.spacing_m))
    last_row = min(inputs.rows - 2, math.floor((max_z + inputs.depth_m / 2) / inputs.spacing_m))
    maximum = -math.inf
    for row in range(first_row, last_row + 1):
        for column in range(first_column, last_column + 1):
            in_patch = (
                mesh.bounds.first_row <= row < mesh.bounds.last_row
                and mesh.bounds.first_column <= column < mesh.bounds.last_column
            )
            for half in (0, 1):
                if _strictly_disjoint(polygon_bounds, context.coarse_bounds(row, column)):
                    context.stats["bboxDisjointRejections"] += 1
                    continue
                coarse_polygon = context.coarse_polygon("accepted", row, column, half)
                context.stats["acceptedIntersectionCalls"] += 1
                overlap = polygon.intersection(coarse_polygon)
                if overlap.is_empty:
                    continue
                if in_patch:
                    triangle_ids = mesh.cell_half_triangles[(row, column, half)]
                    for triangle_id in triangle_ids:
                        overlap_bounds = overlap.bounds
                        face_bounds = tuple(map(float, context.triangle_bounds[triangle_id]))
                        if _strictly_disjoint(overlap_bounds, face_bounds):
                            context.stats["bboxDisjointRejections"] += 1
                            continue
                        face_polygon = context.patch_face_polygon(triangle_id)
                        context.stats["patchFaceIntersectionCalls"] += 1
                        face_overlap = overlap.intersection(face_polygon)
                        if face_overlap.is_empty:
                            continue
                        triangle_xz = context.triangle_xz[triangle_id]
                        triangle_y = context.triangle_y[triangle_id]
                        for x, z in road._geometry_points(face_overlap):
                            maximum = max(
                                maximum,
                                patch._triangle_linear_height(triangle_xz, triangle_y, x, z),
                            )
                else:
                    for x, z in road._geometry_points(overlap):
                        maximum = max(
                            maximum,
                            road._sample_grid(surface.accepted_heights, x, z, inputs.spacing_m),
                        )
    if not math.isfinite(maximum):
        raise patch.RoadSurfacePatchError(
            "building footprint has no samples on the composite surface"
        )
    return maximum


def _building_base_change_v1(
    feature: dict[str, Any],
    surface: patch.CompositeSurface,
    context: ValidationContextV1,
) -> float:
    """Return exact building base change, proving zero outside unchanged patch support."""
    context.require_surface(surface)
    if context.baseline_matches_accepted and context.feature_outside_patch(feature):
        context.stats["disjointBuildingFastPaths"] += 1
        return 0.0
    if context.feature_outside_patch(feature):
        baseline_base, candidate_base = _paired_grid_maxima_under_building_v1(
            feature, surface, context
        )
        return candidate_base - baseline_base
    baseline_base = _maximum_under_building_v1(
        feature, surface.inputs.baseline, surface.inputs, context
    )
    candidate_base = max(
        _composite_maximum_under_polygon_v1(
            Polygon(item["exteriorXZ"], item.get("interiorRingsXZ", [])), surface, context
        )
        for item in feature["geometry"]["polygons"]
    )
    return candidate_base - baseline_base


def composite_building_base_report_v1(
    surface: patch.CompositeSurface,
    context: ValidationContextV1,
    *,
    fail_closed: bool = True,
) -> dict[str, Any]:
    """Return the legacy complete-footprint report with bounded exact geometry caches."""
    started = time.perf_counter()
    context.require_surface(surface)
    features = surface.inputs.buildings.get("buildings")
    if not isinstance(features, list) or len(features) != 3613:
        raise patch.RoadSurfacePatchError(
            "pinned building package must contain all 3,613 footprints for the offline gate"
        )
    changes: list[float] = []
    records = []
    for feature in features:
        if not isinstance(feature, dict):
            raise patch.RoadSurfacePatchError(
                "pinned building payload contains a malformed feature"
            )
        change = _building_base_change_v1(feature, surface, context)
        changes.append(change)
        records.append({"id": feature["id"], "previewMinusBaselineM": change})
    values = np.asarray(changes, dtype=np.float64)
    absolute = np.abs(values)
    by_id = {record["id"]: record["previewMinusBaselineM"] for record in records}
    required = {
        "osm:way:208684847",
        "osm:way:196536218",
        "osm:way:196536220",
        "osm:way:196536221",
        "osm:way:196536227",
        "osm:way:196536217",
        "osm:way:194444458",
        "osm:way:207341667",
        "osm:way:207341692",
        "osm:way:207341702",
        "osm:way:207341535",
        "osm:way:207341753",
    }
    missing = sorted(required - set(by_id))
    if missing:
        raise patch.RoadSurfacePatchError(
            f"registered local building controls are missing: {missing}"
        )
    p95 = float(np.percentile(absolute, 95))
    maximum = float(np.max(absolute))
    flagged = [record for record in records if abs(record["previewMinusBaselineM"]) > 0.50]
    risk_ids = (
        "osm:way:196536218",
        "osm:way:196536220",
        "osm:way:196536221",
        "osm:way:196536227",
        "osm:way:196536217",
        "osm:way:194444458",
        "osm:way:207341667",
        "osm:way:207341692",
        "osm:way:207341702",
        "osm:way:207341535",
        "osm:way:207341753",
        "osm:way:208684847",
    )
    features_by_id = {str(feature["id"]): feature for feature in features}
    footing_sections = []
    for building_id in risk_ids:
        feature = features_by_id[building_id]
        polygons = [
            Polygon(item["exteriorXZ"], item.get("interiorRingsXZ", []))
            for item in feature["geometry"]["polygons"]
        ]
        min_x = min(polygon.bounds[0] for polygon in polygons)
        min_z = min(polygon.bounds[1] for polygon in polygons)
        max_x = max(polygon.bounds[2] for polygon in polygons)
        max_z = max(polygon.bounds[3] for polygon in polygons)
        section_z = (min_z + max_z) / 2
        samples = []
        for x_value in np.arange(math.ceil(min_x), math.floor(max_x) + 1, 1.0):
            x = float(x_value)
            if not any(polygon.covers(Point(x, section_z)) for polygon in polygons):
                continue
            baseline_y = road._sample_grid(
                surface.inputs.baseline, x, section_z, surface.inputs.spacing_m
            )
            candidate_y, _owner = surface.sample(x, section_z)
            samples.append(
                {
                    "localXZ": [x, section_z],
                    "baselineLocalM": baseline_y,
                    "candidateLocalM": candidate_y,
                    "candidateMinusBaselineM": candidate_y - baseline_y,
                }
            )
        perimeter_points: list[tuple[float, float]] = []
        for polygon in polygons:
            for first, second in zip(
                list(polygon.exterior.coords), list(polygon.exterior.coords)[1:], strict=False
            ):
                length = math.dist(first, second)
                count = max(1, math.ceil(length / 1.0))
                perimeter_points.extend(
                    (
                        first[0] + (second[0] - first[0]) * index / count,
                        first[1] + (second[1] - first[1]) * index / count,
                    )
                    for index in range(count + 1)
                )
        perimeter_deltas = [
            surface.sample(x, z)[0]
            - road._sample_grid(surface.inputs.baseline, x, z, surface.inputs.spacing_m)
            for x, z in perimeter_points
        ]
        footing_sections.append(
            {
                "buildingId": building_id,
                "wholeFootprintBaseChangeM": by_id[building_id],
                "sectionAxis": "local X through footprint-bounds midpoint Z",
                "sectionSampleSpacingM": 1.0,
                "sectionSamples": samples,
                "maximumAbsoluteSectionChangeM": max(
                    (abs(item["candidateMinusBaselineM"]) for item in samples), default=0.0
                ),
                "perimeterSampleMaximumAbsoluteChangeM": max(
                    (abs(value) for value in perimeter_deltas), default=0.0
                ),
                "perimeterSampleCount": len(perimeter_points),
            }
        )
    report = {
        "buildingCount": len(records),
        "completeFootprintsRecomputed": True,
        "baseDisplacementP95AbsoluteM": p95,
        "baseDisplacementMaximumAbsoluteM": maximum,
        "p95LimitM": patch.PATCH_MAX_BUILDING_P95,
        "maximumLimitM": patch.PATCH_MAX_BUILDING_BASE,
        "registeredBuildingChangesM": {
            building_id: by_id[building_id] for building_id in sorted(required)
        },
        "registeredRiskFootingSections": footing_sections,
        "newtonLegacyBaseChangesM": {
            building_id: by_id[building_id] for building_id in risk_ids[:5]
        },
        "newtonLegacyBaseLimitM": 0.05,
        "nearbyBuilding208684847": next(
            item for item in footing_sections if item["buildingId"] == "osm:way:208684847"
        ),
        "localReviewOver0_50m": flagged,
        "individualChangesM": records,
        "passes": bool(
            len(records) == 3613
            and p95 <= patch.PATCH_MAX_BUILDING_P95
            and maximum <= patch.PATCH_MAX_BUILDING_BASE
            and all(abs(by_id[building_id]) <= 0.05 for building_id in risk_ids[:5])
        ),
    }
    if fail_closed and not report["passes"]:
        raise patch.RoadSurfacePatchError(
            "complete composite building-base gates failed: "
            f"p95={p95:.9g}/{patch.PATCH_MAX_BUILDING_P95:g} m, "
            f"max={maximum:.9g}/{patch.PATCH_MAX_BUILDING_BASE:g} m, "
            f"local review count={len(flagged)}"
        )
    context.gate_seconds["completeBuildingFootprints"] = time.perf_counter() - started
    return report


def composite_earthwork_overlay_report_v1(
    surface: patch.CompositeSurface,
    context: ValidationContextV1,
) -> dict[str, Any]:
    """Legacy earthwork report using only the identity-bound ownership result."""
    started = time.perf_counter()
    context.require_surface(surface)
    ownership = context.ownership_report
    if ownership is None or context._ownership_fingerprint != context.fingerprint:
        raise patch.RoadSurfacePatchError(
            "validator v1 earthwork requires prior ownership validation"
        )
    mesh = surface.mesh
    source_at_vertices = road._sample_grid_many(
        surface.inputs.baseline,
        mesh.vertices_xz[:, 0],
        mesh.vertices_xz[:, 1],
        surface.inputs.spacing_m,
    )
    signed_changes = surface.patch_heights.astype(np.float64) - source_at_vertices
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
    planar = PlanarMesh(
        mesh.vertices_xz,
        mesh.triangles,
        tuple(tuple(map(int, edge)) for edge in mesh.boundary_edges),
        (),
    )
    overlay = affine_surface_overlay_extrema(planar, surface.patch_heights, source_index)
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


def validate_offline_candidate_v1(
    surface: patch.CompositeSurface,
    influence: Polygon,
    constraints: list[dict[str, Any]],
    solver_report: dict[str, Any],
    accepted_preview_hashes: dict[str, str],
    *,
    context: ValidationContextV1 | None = None,
) -> tuple[dict[str, Any], ValidationContextV1]:
    """Run the same strict gates through explicit validator version 1 dispatch."""
    context = context or ValidationContextV1(surface)
    context.require_surface(surface)
    candidate = surface.patch_heights
    candidate_bytes = candidate.astype("<f4", copy=False).tobytes(order="C")
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
    try:
        gate_started = time.perf_counter()
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
        reports["float32FinalValidation"] = patch._validate_quantized_phase_one(
            surface.mesh,
            candidate,
            source_nodes,
            edges,
            edge_limits,
            constraints,
            fixed_mask,
            surface.mesh.base_y.astype(np.float64),
            influence,
            solver_tolerance_m=float(solver_report.get("solverNumericalToleranceM", 2e-5)),
        )
    except (patch.RoadSurfacePatchError, KeyError, TypeError, ValueError, IndexError) as exc:
        reports["float32FinalValidation"] = {"passes": False, "error": str(exc)}
    context.gate_seconds["float32FinalValidation"] = time.perf_counter() - gate_started
    try:
        gate_started = time.perf_counter()
        reports["topology"] = patch.patch_topology_report(surface.mesh, surface.inputs.spacing_m)
    except patch.RoadSurfacePatchError as exc:
        reports["topology"] = {"passes": False, "error": str(exc)}
    context.gate_seconds["topology"] = time.perf_counter() - gate_started
    gate_started = time.perf_counter()
    reports["sourceTriangleOwnership"] = context.bind_ownership(surface)
    context.gate_seconds["sourceTriangleOwnership"] = time.perf_counter() - gate_started
    reports["earthworkOverlay"] = composite_earthwork_overlay_report_v1(surface, context)
    try:
        gate_started = time.perf_counter()
        reports["acceptedPlaneRefinement"] = patch.verify_accepted_plane_refinement(
            surface.mesh,
            surface.accepted_heights,
            surface.inputs.spacing_m,
            influence=influence,
            fail_closed=False,
        )
    except patch.RoadSurfacePatchError as exc:
        reports["acceptedPlaneRefinement"] = {"passes": False, "error": str(exc)}
    context.gate_seconds["acceptedPlaneRefinement"] = time.perf_counter() - gate_started
    try:
        gate_started = time.perf_counter()
        reports["compositeTerrain"] = patch.verify_composite_terrain(
            surface, influence, fail_closed=False
        )
    except patch.RoadSurfacePatchError as exc:
        reports["compositeTerrain"] = {"passes": False, "error": str(exc)}
    context.gate_seconds["compositeTerrain"] = time.perf_counter() - gate_started
    try:
        gate_started = time.perf_counter()
        reports["localCorridorLongitudinal"] = patch.composite_local_and_corridor_report(
            surface, fail_closed=False
        )
    except patch.RoadSurfacePatchError as exc:
        reports["localCorridorLongitudinal"] = {"passes": False, "error": str(exc)}
    context.gate_seconds["localCorridorLongitudinal"] = time.perf_counter() - gate_started
    try:
        reports["completeBuildingFootprints"] = composite_building_base_report_v1(
            surface, context, fail_closed=False
        )
    except patch.RoadSurfacePatchError as exc:
        reports["completeBuildingFootprints"] = {"passes": False, "error": str(exc)}
    try:
        gate_started = time.perf_counter()
        reclipped_roads = patch.reclip_affected_road_batches(surface)
        reports["roadPathReclip"] = reclipped_roads
    except (patch.RoadSurfacePatchError, KeyError, TypeError, ValueError, IndexError) as exc:
        reclipped_roads = {"groups": {}}
        reports["roadPathReclip"] = {"passes": False, "error": str(exc)}
    context.gate_seconds["roadPathReclip"] = time.perf_counter() - gate_started
    try:
        gate_started = time.perf_counter()
        reports["walkClearance"] = patch.composite_walk_clearance_report(surface, reclipped_roads)
    except (patch.RoadSurfacePatchError, KeyError, TypeError, ValueError, IndexError) as exc:
        reports["walkClearance"] = {"passes": False, "error": str(exc)}
    context.gate_seconds["walkClearance"] = time.perf_counter() - gate_started
    reports["passes"] = all(
        reports.get(name, {}).get("passes", False) for name in patch.PATCH_OFFLINE_GATE_NAMES
    )
    reports["gateNames"] = list(patch.PATCH_OFFLINE_GATE_NAMES)
    reports["candidateFloat32Sha256"] = candidate_hash
    reports["candidateFloat32ByteLength"] = len(candidate_bytes)
    reports["candidateFloat32Finite"] = bool(np.isfinite(candidate).all())
    reports["validatorVersion"] = VALIDATOR_VERSION
    return reports, context
