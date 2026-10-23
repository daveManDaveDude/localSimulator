"""Offline conforming local-surface patch generation for the Teignmouth correction.

This module deliberately remains separate from the accepted heightfield-preview
builder.  It constructs a bounded triangulated replacement over an immutable
2 m display surface; it does not modify source packages or browser behavior.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np
from shapely import contains_xy, distance, points
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.ops import triangulate
from shapely.strtree import STRtree

from . import road_surface as _road_surface
from .road_surface import (
    CURRENT_RELEASE_ID,
    PROFILE_WAY_IDS,
    SEVERE_CORRIDOR_WAY_IDS,
    SEVERE_CROSSFALL_NUMERICAL_MARGIN_M,
    TEIGNMOUTH_CANDIDATE_OUTPUT,
    TEIGNMOUTH_PART_INDEX,
    TEIGNMOUTH_STATION_END_M,
    TEIGNMOUTH_STATION_START_M,
    TEIGNMOUTH_WAY_ID,
    PreviewConfig,
    ReleaseInputs,
    RoadSurfaceError,
    _geometry_points,
    _line_point_tangent,
    _maximum_under_building,
    _sample_grid,
    _sample_grid_many,
    load_config,
    load_release_inputs,
)
from .road_surface_topology import (
    PlanarMesh,
    SourceOverlapIndex,
    TopologyError,
    affine_surface_overlay_extrema,
    alternate_internal_diagonals,
    build_constrained_mesh,
    graded_collar_constraints,
    localized_grid_constraints,
    localized_refinement_zone,
    road_aligned_constraints,
    source_overlap_provenance,
)

PATCH_PACKAGE_TYPE = "road-surface-local-triangle-patch"
PATCH_ALGORITHM_VERSION = "road-surface-local-triangle-patch-1.0.0"
PATCH_OUTPUT_FILES = frozenset(
    {
        "manifest.json",
        "terrain-vertices.f32",
        "terrain-indices.u32",
        "road-vertices.f32",
        "road-indices.u32",
        "road-terrain-triangles.u32",
        "qa.json",
    }
)
PATCH_GEOMETRY_WITNESS_FILES = (
    "terrain-vertices.f32",
    "terrain-indices.u32",
    "road-vertices.f32",
    "road-indices.u32",
    "road-terrain-triangles.u32",
)
PATCH_FORMAT_VERSION = 1
PATCH_FINE_SPACING_M = 0.5
PATCH_MAX_SIDE_M = 160.0
PATCH_MAX_TRIANGLES = 250_000
PATCH_MAX_VERTICES = 150_000
PATCH_MAX_ASSET_BYTES = 8 * 1024 * 1024
PATCH_MAX_MANIFEST_BYTES = 256 * 1024
PATCH_MAX_QA_BYTES = 512 * 1024
PATCH_MAX_RESIDENT_GEOMETRY_BYTES = 16 * 1024 * 1024
PATCH_MAX_PEAK_CONSTRUCTION_BYTES = 64 * 1024 * 1024
PATCH_MAX_ADDED_GRADIENT = 0.999
PATCH_MAX_ABSOLUTE_CHANGE = 4.999
PATCH_MAX_BUILDING_BASE = 2.4239
PATCH_MAX_BUILDING_P95 = 0.183
PATCH_CENTERLINE_TOLERANCE = 0.0999
PATCH_LONGITUDINAL_GRADE_DELTA = 0.0199
PATCH_LATERAL_SLOPE = 0.05
PATCH_LATERAL_SAMPLE_M = 0.25
PATCH_CROSSFALL_STEP_HEADROOM_M = 0.0001
PATCH_ENDPOINT_SPAN_M = 0.2999
PATCH_MAX_CENTERLINE_DEVIATION_M = 0.10
PATCH_MAX_LONGITUDINAL_GRADE_DELTA = 0.02
PATCH_MAX_ENDPOINT_SPAN_M = 0.30
PATCH_MAX_TRANSITION_M = 32.0
PATCH_CLEARANCE_M = 1.70
PATCH_CLEARANCE_TOLERANCE_M = 0.05
PATCH_CLEARANCE_ARITHMETIC_TOLERANCE_M = 1e-12
PATCH_ROAD_SURFACE_OFFSET_M = 0.05
PATCH_ROAD_FLOAT32_OMITTED_AREA_LIMIT_M2 = 2e-5
PATCH_ROAD_AREA_ABSOLUTE_TOLERANCE_M2 = 1e-8
PATCH_VERTICAL_ORIGIN_POLICY = "unchanged pinned release originY; local metre heights"
PATCH_OFFLINE_GATE_NAMES = (
    "inputBindings",
    "solverWitness",
    "float32FinalValidation",
    "topology",
    "sourceTriangleOwnership",
    "earthworkOverlay",
    "acceptedPlaneRefinement",
    "compositeTerrain",
    "localCorridorLongitudinal",
    "completeBuildingFootprints",
    "roadPathReclip",
    "walkClearance",
)

ACCEPTED_PREVIEW_HASHES = {
    "manifest.json": "9a3cb6c08fb57a19f94e1215ac526b1baf28634d38be1ffc7d4ed61f2de7c6f7",
    "heightfield.f32": "037a74320557088135e0885386c24fdcdea6171469db1d6329c3e82997f5c1e9",
    "qa.json": "43d7058a339416d308be09292598949d3d97f4b764a147ccc2d5fb771d434f20",
}


class RoadSurfacePatchError(RoadSurfaceError):
    """A local patch failed a strict offline construction or acceptance gate."""


def _json_native(value: Any) -> Any:
    """Recursively convert NumPy values to deterministic standard JSON values."""
    if isinstance(value, np.ndarray):
        return _json_native(value.tolist())
    if isinstance(value, np.generic):
        return _json_native(value.item())
    if isinstance(value, dict):
        return {str(key): _json_native(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_native(item) for item in value]
    return value


def serialize_offline_report(report: dict[str, Any]) -> bytes:
    """Serialize a complete aggregate report, including nested NumPy diagnostics."""
    try:
        return (
            json.dumps(
                _json_native(report),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise RoadSurfacePatchError(f"offline report is not finite JSON data: {exc}") from exc


def serialized_geometry_witness_sha256(
    assets: dict[str, bytes], candidate_float32_sha256: str
) -> str:
    """Bind the exact serialized display geometry, indices and road-face ownership."""
    digest = hashlib.sha256(b"torquay-local-patch-serialized-witness-v1\0")
    digest.update(candidate_float32_sha256.encode("ascii"))
    digest.update(b"\0")
    for name in PATCH_GEOMETRY_WITNESS_FILES:
        payload = assets.get(name)
        if not isinstance(payload, bytes):
            raise RoadSurfacePatchError(f"serialized witness is missing immutable {name} bytes")
        encoded_name = name.encode("ascii")
        digest.update(len(encoded_name).to_bytes(2, "little"))
        digest.update(encoded_name)
        digest.update(len(payload).to_bytes(8, "little"))
        digest.update(payload)
    return digest.hexdigest()


def _source_record_digest(record: dict[str, Any]) -> str:
    """Return a validated digest for file records or the readiness pointer record."""
    digest = record.get("sha256", record.get("readySha256", record.get("inventorySha256")))
    if not isinstance(digest, str) or len(digest) != 64:
        raise RoadSurfacePatchError("pinned source record has no valid SHA-256 binding")
    return digest


@dataclass(frozen=True)
class PatchBounds:
    """A rectangular replacement set aligned to complete 2 m source cells."""

    first_row: int
    first_column: int
    row_count: int
    column_count: int

    @property
    def last_row(self) -> int:
        return self.first_row + self.row_count

    @property
    def last_column(self) -> int:
        return self.first_column + self.column_count

    @property
    def coarse_cell_count(self) -> int:
        return self.row_count * self.column_count

    def validate(self, rows: int, columns: int, spacing_m: float) -> None:
        if spacing_m != 2.0:
            raise RoadSurfacePatchError("local patch requires the pinned 2 m base grid")
        if (
            self.first_row < 0
            or self.first_column < 0
            or self.row_count <= 0
            or self.column_count <= 0
            or self.last_row > rows - 1
            or self.last_column > columns - 1
        ):
            raise RoadSurfacePatchError(
                "patch coarse-cell replacement set is outside the base grid"
            )
        width_m = self.column_count * spacing_m
        depth_m = self.row_count * spacing_m
        if max(width_m, depth_m) > PATCH_MAX_SIDE_M:
            raise RoadSurfacePatchError(
                f"local patch exceeds the {PATCH_MAX_SIDE_M:g} m per-side bound: "
                f"{width_m:g} m × {depth_m:g} m"
            )


@dataclass(frozen=True)
class PatchMesh:
    """A conforming patch; indices refer to the deterministic vertex order."""

    bounds: PatchBounds
    vertices_xz: np.ndarray
    base_y: np.ndarray
    triangles: np.ndarray
    triangle_cells: np.ndarray
    triangle_cell_halves: np.ndarray
    boundary_edges: np.ndarray
    edge_counts: dict[tuple[int, int], int]
    cell_half_triangles: dict[tuple[int, int, int], tuple[int, ...]]
    triangle_key_to_id: dict[tuple[tuple[int, int], ...], int]
    triangle_geometries: tuple[Polygon, ...] | None = None
    triangle_tree: STRtree | None = None
    topology_variant: str = "existing-05"


def _orient_up(keys: tuple[tuple[int, int], ...]) -> tuple[tuple[int, int], ...]:
    if len(keys) != 3:
        raise RoadSurfacePatchError("patch face must have three vertices")
    a, b, c = keys
    area2 = (b[1] - a[1]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[1] - a[1])
    if area2 == 0:
        raise RoadSurfacePatchError("patch topology contains a zero-area face")
    return keys if area2 < 0 else (a, c, b)


def _fine_triangle_keys(
    row: int, column: int, half: int
) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    nw = (4 * row, 4 * column)
    ne = (4 * row, 4 * column + 4)
    sw = (4 * row + 4, 4 * column)
    se = (4 * row + 4, 4 * column + 4)
    return _orient_up((nw, sw, ne) if half == 0 else (ne, sw, se))


def _triangle_lattice_points(row: int, column: int, half: int) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    for local_row in range(5):
        for local_column in range(5):
            if half == 0 and local_row + local_column <= 4:
                points.append((4 * row + local_row, 4 * column + local_column))
            elif half == 1 and local_row + local_column >= 4:
                points.append((4 * row + local_row, 4 * column + local_column))
    return points


def _is_outer_fine_point(point: tuple[int, int], bounds: PatchBounds) -> bool:
    row, column = point
    outer = row in (4 * bounds.first_row, 4 * bounds.last_row) or column in (
        4 * bounds.first_column,
        4 * bounds.last_column,
    )
    return outer and (row % 4 != 0 or column % 4 != 0)


def _triangulate_triangle_with_missing_boundary_points(
    triangle_keys: tuple[tuple[int, int], tuple[int, int], tuple[int, int]],
    points: list[tuple[int, int]],
) -> list[tuple[tuple[int, int], tuple[int, int], tuple[int, int]]]:
    """Deterministically triangulate a coarse half-cell with no perimeter T-junctions."""
    point_geometry = MultiPoint([(column, row) for row, column in points])
    pieces = []
    for shape in triangulate(point_geometry):
        coords = list(shape.exterior.coords)[:-1]
        keys = []
        for column, row in coords:
            key = (int(round(row)), int(round(column)))
            if abs(row - key[0]) > 1e-8 or abs(column - key[1]) > 1e-8:
                raise RoadSurfacePatchError("triangulator returned a non-lattice patch vertex")
            keys.append(key)
        if len(keys) != 3:
            raise RoadSurfacePatchError("triangulator returned a non-triangle patch face")
        oriented = _orient_up(tuple(keys))
        polygon = Polygon([(column, row) for row, column in oriented])
        pieces.append((oriented, polygon.area))
    used = {point for triangle, _area in pieces for point in triangle}
    if used != set(points):
        missing = sorted(set(points) - used)[:8]
        raise RoadSurfacePatchError(
            f"conforming collar triangulation omitted lattice vertices: {missing}"
        )
    expected_area = Polygon([(column, row) for row, column in triangle_keys]).area
    area = math.fsum(value for _triangle, value in pieces)
    if abs(area - expected_area) > 1e-9:
        raise RoadSurfacePatchError(
            f"conforming collar does not cover its source half-cell: {area:g} vs {expected_area:g}"
        )
    pieces.sort(key=lambda value: tuple(sorted(value[0])))
    return [triangle for triangle, _area in pieces]


def _coarse_half_triangles(
    row: int, column: int, half: int, bounds: PatchBounds
) -> list[tuple[tuple[int, int], tuple[int, int], tuple[int, int]]]:
    source_triangle = _fine_triangle_keys(row, column, half)
    points = [
        point
        for point in _triangle_lattice_points(row, column, half)
        if not _is_outer_fine_point(point, bounds)
    ]
    if len(points) == 15:
        # The regular 0.5 m interior uses a fixed diagonal at every small square.
        output = []
        for local_row in range(4):
            for local_column in range(4 - local_row):
                a = (4 * row + local_row, 4 * column + local_column)
                b = (a[0], a[1] + 1)
                c = (a[0] + 1, a[1])
                output.append(_orient_up((a, c, b)))
                if local_row + local_column < 3:
                    d = (a[0] + 1, a[1] + 1)
                    output.append(_orient_up((b, d, c)))
        if half == 1:
            output = [
                _orient_up(
                    tuple(
                        (
                            4 * row + 4 - (point[0] - 4 * row),
                            4 * column + 4 - (point[1] - 4 * column),
                        )
                        for point in triangle
                    )
                )
                for triangle in output
            ]
        return sorted(output, key=lambda value: tuple(sorted(value)))
    return _triangulate_triangle_with_missing_boundary_points(source_triangle, points)


def _boundary_edge_keys(bounds: PatchBounds) -> set[tuple[tuple[int, int], tuple[int, int]]]:
    edges: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    top = 4 * bounds.first_row
    bottom = 4 * bounds.last_row
    left = 4 * bounds.first_column
    right = 4 * bounds.last_column
    for column in range(left, right, 4):
        edges.add(tuple(sorted(((top, column), (top, column + 4)))))
        edges.add(tuple(sorted(((bottom, column), (bottom, column + 4)))))
    for row in range(top, bottom, 4):
        edges.add(tuple(sorted(((row, left), (row + 4, left)))))
        edges.add(tuple(sorted(((row, right), (row + 4, right)))))
    return edges


def build_conforming_mesh(
    bounds: PatchBounds,
    accepted_heights: np.ndarray,
    width_m: float,
    depth_m: float,
    spacing_m: float,
) -> PatchMesh:
    """Refine source triangles with a 0.5 m interior and 2 m patch perimeter."""
    rows, columns = accepted_heights.shape
    bounds.validate(rows, columns, spacing_m)
    if not np.isfinite(accepted_heights).all():
        raise RoadSurfacePatchError("accepted base surface contains non-finite heights")

    keyed_triangles: list[tuple[tuple[int, int], tuple[int, int], tuple[int, int]]] = []
    cell_tags: list[tuple[int, int, int]] = []
    cell_half_ranges: dict[tuple[int, int, int], list[int]] = {}
    for row in range(bounds.first_row, bounds.last_row):
        for column in range(bounds.first_column, bounds.last_column):
            for half in (0, 1):
                start = len(keyed_triangles)
                triangles = _coarse_half_triangles(row, column, half, bounds)
                keyed_triangles.extend(triangles)
                cell_tags.extend([(row, column, half)] * len(triangles))
                cell_half_ranges[(row, column, half)] = list(range(start, start + len(triangles)))

    if not keyed_triangles:
        raise RoadSurfacePatchError("patch topology is empty")
    keys = sorted({point for triangle in keyed_triangles for point in triangle})
    vertex_ids = {point: index for index, point in enumerate(keys)}
    vertices_xz = np.asarray(
        [
            [column * PATCH_FINE_SPACING_M - width_m / 2, row * PATCH_FINE_SPACING_M - depth_m / 2]
            for row, column in keys
        ],
        dtype=np.float64,
    )
    base_y = np.asarray(
        [_sample_grid(accepted_heights, x, z, spacing_m) for x, z in vertices_xz],
        dtype=np.float32,
    )
    triangles = np.asarray(
        [[vertex_ids[key] for key in triangle] for triangle in keyed_triangles],
        dtype=np.uint32,
    )
    tags = np.asarray(cell_tags, dtype=np.int32)
    edge_counts: dict[tuple[int, int], int] = {}
    for triangle in triangles:
        for a, b in (
            (triangle[0], triangle[1]),
            (triangle[1], triangle[2]),
            (triangle[2], triangle[0]),
        ):
            edge = tuple(sorted((int(a), int(b))))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1

    key_boundary_edges = _boundary_edge_keys(bounds)
    actual_boundary_edges = {
        tuple(sorted((keys[first], keys[second])))
        for (first, second), count in edge_counts.items()
        if count == 1
    }
    if actual_boundary_edges != key_boundary_edges:
        missing = sorted(key_boundary_edges - actual_boundary_edges)[:8]
        unexpected = sorted(actual_boundary_edges - key_boundary_edges)[:8]
        raise RoadSurfacePatchError(
            "patch perimeter is not a conforming 2 m boundary; "
            f"missing={missing}, unexpected={unexpected}"
        )
    if any(count not in (1, 2) for count in edge_counts.values()):
        raise RoadSurfacePatchError("patch contains a non-manifold or overlapping interior edge")
    for triangle in triangles:
        a, b, c = (vertices_xz[int(index)] for index in triangle)
        area2 = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if not math.isfinite(float(area2)) or area2 >= 0.0:
            raise RoadSurfacePatchError("patch face winding is not finite and upward")
    total_area = math.fsum(
        abs(
            float(
                (vertices_xz[int(triangle[1]), 0] - vertices_xz[int(triangle[0]), 0])
                * (vertices_xz[int(triangle[2]), 1] - vertices_xz[int(triangle[0]), 1])
                - (vertices_xz[int(triangle[1]), 1] - vertices_xz[int(triangle[0]), 1])
                * (vertices_xz[int(triangle[2]), 0] - vertices_xz[int(triangle[0]), 0])
            )
        )
        * 0.5
        for triangle in triangles
    )
    expected_area = bounds.row_count * bounds.column_count * spacing_m**2
    if abs(total_area - expected_area) > 1e-6:
        raise RoadSurfacePatchError(
            f"patch faces do not cover the replacement set: {total_area:g} vs {expected_area:g} m²"
        )
    if np.any(~np.isfinite(vertices_xz.astype(np.float32))) or np.any(~np.isfinite(base_y)):
        raise RoadSurfacePatchError("Float32 patch coordinates or heights are non-finite")

    boundary_edges = np.asarray(
        sorted(
            (
                vertex_ids[first],
                vertex_ids[second],
            )
            for first, second in key_boundary_edges
        ),
        dtype=np.uint32,
    )
    cell_half_triangles = {key: tuple(indices) for key, indices in cell_half_ranges.items()}
    triangle_key_to_id = {
        tuple(sorted(triangle)): triangle_index
        for triangle_index, triangle in enumerate(keyed_triangles)
    }
    return PatchMesh(
        bounds=bounds,
        vertices_xz=vertices_xz,
        base_y=base_y,
        triangles=triangles,
        triangle_cells=tags[:, :2],
        triangle_cell_halves=tags[:, 2],
        boundary_edges=boundary_edges,
        edge_counts=edge_counts,
        cell_half_triangles=cell_half_triangles,
        triangle_key_to_id=triangle_key_to_id,
    )


def _patch_mesh_from_planar(
    planar: PlanarMesh,
    bounds: PatchBounds,
    inputs: ReleaseInputs,
    accepted_heights: np.ndarray,
    topology_variant: str,
) -> PatchMesh:
    """Bind arbitrary conforming X/Z topology to pinned heights and source cells."""
    vertices = np.asarray(planar.vertices_xz, dtype=np.float64)
    triangles = np.asarray(planar.triangles, dtype=np.uint32)
    base_y = _sample_grid_many(
        accepted_heights, vertices[:, 0], vertices[:, 1], inputs.spacing_m
    ).astype("<f4")
    geometries = tuple(Polygon(vertices[face.astype(np.int64)]) for face in triangles)
    if any(
        geometry.is_empty or not geometry.is_valid or geometry.area <= 0.0
        for geometry in geometries
    ):
        raise RoadSurfacePatchError("study topology contains an invalid or degenerate patch face")
    tree = STRtree(geometries)
    source_index = SourceOverlapIndex.from_grid(
        inputs.baseline,
        width_m=inputs.width_m,
        depth_m=inputs.depth_m,
        spacing_m=inputs.spacing_m,
        first_row=bounds.first_row,
        last_row=bounds.last_row,
        first_column=bounds.first_column,
        last_column=bounds.last_column,
    )
    cell_half_triangles: dict[tuple[int, int, int], tuple[int, ...]] = {}
    for row in range(bounds.first_row, bounds.last_row):
        for column in range(bounds.first_column, bounds.last_column):
            for half in (0, 1):
                source_id = 2 * (row * (inputs.columns - 1) + column) + half
                source_position = source_index.index_by_source_id[source_id]
                source_polygon = source_index.geometries[source_position]
                face_ids = sorted(
                    int(face_id)
                    for face_id in tree.query(source_polygon, predicate="intersects")
                    if geometries[int(face_id)].intersection(source_polygon).area > 1e-12
                )
                covered_area = math.fsum(
                    float(geometries[face_id].intersection(source_polygon).area)
                    for face_id in face_ids
                )
                if abs(covered_area - float(source_polygon.area)) > max(
                    1e-10, float(source_polygon.area) * 1e-10
                ):
                    raise RoadSurfacePatchError(
                        "study topology does not exactly cover an original source half-cell: "
                        f"row={row}, column={column}, half={half}, "
                        f"sourceArea={source_polygon.area:.17g}, coveredArea={covered_area:.17g}"
                    )
                cell_half_triangles[(row, column, half)] = tuple(face_ids)

    centroids = vertices[triangles.astype(np.int64)].mean(axis=1)
    columns = np.floor((centroids[:, 0] + inputs.width_m / 2) / inputs.spacing_m).astype(np.int32)
    rows = np.floor((centroids[:, 1] + inputs.depth_m / 2) / inputs.spacing_m).astype(np.int32)
    columns = np.clip(columns, bounds.first_column, bounds.last_column - 1)
    rows = np.clip(rows, bounds.first_row, bounds.last_row - 1)
    u = (centroids[:, 0] + inputs.width_m / 2) / inputs.spacing_m - columns
    v = (centroids[:, 1] + inputs.depth_m / 2) / inputs.spacing_m - rows
    halves = (u + v > 1.0).astype(np.int32)
    edge_counts: dict[tuple[int, int], int] = {}
    for face in triangles:
        for first, second in (
            (int(face[0]), int(face[1])),
            (int(face[1]), int(face[2])),
            (int(face[2]), int(face[0])),
        ):
            edge = tuple(sorted((first, second)))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
    if any(count not in (1, 2) for count in edge_counts.values()):
        raise RoadSurfacePatchError("study topology has nonmanifold or duplicate edges")
    boundary = np.asarray(planar.boundary_edges, dtype=np.uint32).reshape((-1, 2))
    return PatchMesh(
        bounds=bounds,
        vertices_xz=vertices,
        base_y=base_y,
        triangles=triangles,
        triangle_cells=np.column_stack((rows, columns)).astype(np.int32),
        triangle_cell_halves=halves,
        boundary_edges=boundary,
        edge_counts=edge_counts,
        cell_half_triangles=cell_half_triangles,
        triangle_key_to_id={},
        triangle_geometries=geometries,
        triangle_tree=tree,
        topology_variant=topology_variant,
    )


def build_topology_study_mesh(
    bounds: PatchBounds,
    accepted_heights: np.ndarray,
    inputs: ReleaseInputs,
    influence: Polygon,
    centerline_xz: list[tuple[float, float]],
    *,
    variant: str,
    refinement_base_variant: str | None = None,
) -> PatchMesh:
    """Construct one frozen topology-study candidate from the same base patch."""
    regular = build_conforming_mesh(
        bounds,
        accepted_heights,
        inputs.width_m,
        inputs.depth_m,
        inputs.spacing_m,
    )
    if variant == "existing-05":
        return replace(regular, topology_variant=variant)
    if variant == "flip-05":
        planar = PlanarMesh(
            regular.vertices_xz.copy(),
            regular.triangles.copy(),
            tuple(tuple(map(int, edge)) for edge in regular.boundary_edges),
            (),
        )
        flipped, flip_count = alternate_internal_diagonals(planar, influence)
        if flip_count == 0:
            raise RoadSurfacePatchError("flip-05 produced no eligible internal diagonal changes")
        return _patch_mesh_from_planar(flipped, bounds, inputs, accepted_heights, variant)
    if variant not in {"road-05", "collar-05", "local-025", "local-0125"}:
        raise RoadSurfacePatchError(f"unknown topology study variant {variant!r}")

    base_variant = variant
    if variant in {"local-025", "local-0125"}:
        if refinement_base_variant not in {"road-05", "collar-05"}:
            raise RoadSurfacePatchError(
                f"{variant} requires a completed road-05 or collar-05 base topology"
            )
        base_variant = refinement_base_variant

    minimum_x, minimum_z = regular.vertices_xz.min(axis=0)
    maximum_x, maximum_z = regular.vertices_xz.max(axis=0)
    domain = Polygon(
        [
            (minimum_x, minimum_z),
            (maximum_x, minimum_z),
            (maximum_x, maximum_z),
            (minimum_x, maximum_z),
        ]
    )
    constraints = [
        LineString(regular.vertices_xz[np.asarray(edge, dtype=np.int64)])
        for edge in sorted(regular.edge_counts)
    ]
    for polygon in [influence] if isinstance(influence, Polygon) else influence.geoms:
        constraints.append(LineString(polygon.exterior.coords))
        constraints.extend(LineString(ring.coords) for ring in polygon.interiors)
    constraints.extend(
        road_aligned_constraints(
            centerline_xz,
            width_m=6.0,
            station_spacing_m=0.5,
            lateral_spacing_m=0.5,
            domain=domain,
        )
    )
    if base_variant == "collar-05":
        constraints.extend(
            graded_collar_constraints(
                centerline_xz,
                width_m=6.0,
                collar_steps_m=(0.5, 1.0, 2.0),
                domain=domain,
            )
        )
    if variant in {"local-025", "local-0125"}:
        fine_spacing = 0.25 if variant == "local-025" else 0.125
        zone = localized_refinement_zone(
            centerline_xz,
            width_m=6.0,
            source_cell_spacing_m=inputs.spacing_m,
            influence=influence,
        )
        constraints.append(LineString(zone.exterior.coords))
        constraints.extend(LineString(ring.coords) for ring in zone.interiors)
        constraints.extend(localized_grid_constraints(zone, fine_spacing))
    try:
        planar = build_constrained_mesh(domain, constraints)
    except TopologyError as exc:
        raise RoadSurfacePatchError(f"{variant} constrained topology failed: {exc}") from exc
    return _patch_mesh_from_planar(planar, bounds, inputs, accepted_heights, variant)


def patch_topology_report(mesh: PatchMesh, spacing_m: float) -> dict[str, Any]:
    """Return deterministic topology and Float32 boundary measurements."""
    baseline_cell_triangles = mesh.bounds.coarse_cell_count * 2
    boundary_float32 = mesh.vertices_xz[mesh.boundary_edges].astype("<f4")
    terrain_vertex_bytes = int(len(mesh.vertices_xz) * 3 * 4)
    terrain_index_bytes = int(len(mesh.triangles) * 3 * 4)
    resource_report = validate_terrain_mesh_resources(
        len(mesh.vertices_xz),
        len(mesh.triangles),
        terrain_vertex_bytes + terrain_index_bytes,
    )
    triangles = mesh.triangles.astype(np.int64)
    vertices = mesh.vertices_xz.astype(np.float64)
    face_points = vertices[triangles]
    signed_area2 = (face_points[:, 1, 0] - face_points[:, 0, 0]) * (
        face_points[:, 2, 1] - face_points[:, 0, 1]
    ) - (face_points[:, 1, 1] - face_points[:, 0, 1]) * (
        face_points[:, 2, 0] - face_points[:, 0, 0]
    )
    covered_area = float(np.sum(np.abs(signed_area2), dtype=np.float64) * 0.5)
    expected_area = mesh.bounds.row_count * mesh.bounds.column_count * spacing_m**2
    boundary_edges = {edge for edge, count in mesh.edge_counts.items() if count == 1}
    recorded_boundary = {
        tuple(sorted((int(first), int(second)))) for first, second in mesh.boundary_edges
    }
    incidence_valid = bool(all(count in (1, 2) for count in mesh.edge_counts.values()))
    boundary_matches = boundary_edges == recorded_boundary
    boundary_degree: dict[int, int] = {}
    adjacency = [set() for _ in range(len(vertices))]
    for first, second in mesh.edge_counts:
        adjacency[first].add(second)
        adjacency[second].add(first)
    for first, second in boundary_edges:
        boundary_degree[first] = boundary_degree.get(first, 0) + 1
        boundary_degree[second] = boundary_degree.get(second, 0) + 1
    boundary_cycle_valid = bool(boundary_degree) and all(
        degree == 2 for degree in boundary_degree.values()
    )
    visited: set[int] = set()
    if adjacency:
        stack = [0]
        visited.add(0)
        while stack:
            for neighbor in adjacency[stack.pop()] - visited:
                visited.add(neighbor)
                stack.append(neighbor)
    graph_connected = len(visited) == len(vertices)
    euler_characteristic = len(vertices) - len(mesh.edge_counts) + len(mesh.triangles)
    width_m = mesh.bounds.column_count * spacing_m
    depth_m = mesh.bounds.row_count * spacing_m
    finite_geometry = bool(
        np.isfinite(vertices).all()
        and np.isfinite(mesh.base_y).all()
        and np.isfinite(signed_area2).all()
    )
    winding_valid = bool(np.all(signed_area2 < 0.0))
    area_coverage_valid = abs(covered_area - expected_area) <= 1e-6
    bounds_within_limit = width_m <= PATCH_MAX_SIDE_M and depth_m <= PATCH_MAX_SIDE_M
    passes = bool(
        finite_geometry
        and winding_valid
        and incidence_valid
        and boundary_matches
        and len(boundary_edges) == 2 * (mesh.bounds.row_count + mesh.bounds.column_count)
        and boundary_cycle_valid
        and graph_connected
        and euler_characteristic == 1
        and area_coverage_valid
        and bounds_within_limit
        and resource_report["passes"]
    )
    report = {
        "patchBoundsM": {
            "xMin": float(mesh.vertices_xz[:, 0].min()),
            "xMax": float(mesh.vertices_xz[:, 0].max()),
            "zMin": float(mesh.vertices_xz[:, 1].min()),
            "zMax": float(mesh.vertices_xz[:, 1].max()),
            "width": float(mesh.bounds.column_count * spacing_m),
            "depth": float(mesh.bounds.row_count * spacing_m),
        },
        "replacementCoarseCellCount": mesh.bounds.coarse_cell_count,
        "removedCoarseTriangleCount": baseline_cell_triangles,
        "patchTriangleCount": int(len(mesh.triangles)),
        "netTerrainTriangleIncrease": int(len(mesh.triangles) - baseline_cell_triangles),
        "patchVertexCount": int(len(mesh.vertices_xz)),
        "netTerrainVertexIncreaseUpperBound": int(len(mesh.vertices_xz)),
        "boundaryEdgeCount": int(len(mesh.boundary_edges)),
        "boundaryVertexFloat32Finite": bool(np.isfinite(boundary_float32).all()),
        "interiorEdgeCount": sum(count == 2 for count in mesh.edge_counts.values()),
        "nonManifoldEdgeCount": sum(count > 2 for count in mesh.edge_counts.values()),
        "edgeIncidenceValid": incidence_valid,
        "boundaryEdgesMatch": boundary_matches,
        "boundaryCycleValid": boundary_cycle_valid,
        "vertexGraphConnected": graph_connected,
        "eulerCharacteristic": euler_characteristic,
        "faceWindingValid": winding_valid,
        "finiteGeometry": finite_geometry,
        "coveredPlanAreaM2": covered_area,
        "expectedCoveredPlanAreaM2": expected_area,
        "areaCoverageValid": area_coverage_valid,
        "boundsWithin160mLimit": bounds_within_limit,
        "terrainVertexBytes": terrain_vertex_bytes,
        "terrainIndexBytes": terrain_index_bytes,
        "terrainMeshBytes": terrain_vertex_bytes + terrain_index_bytes,
        "resourceLimitsPass": resource_report["passes"],
        "resourceLimits": resource_report,
        "passes": passes,
    }
    if not report["passes"]:
        raise RoadSurfacePatchError(
            "conforming patch topology/resource gate failed: "
            + json.dumps(report, sort_keys=True, separators=(",", ":"))
        )
    return report


def validate_terrain_mesh_resources(
    vertex_count: int, triangle_count: int, terrain_asset_bytes: int
) -> dict[str, Any]:
    """Fail closed on the amendment's terrain-mesh count and byte ceilings."""
    report = {
        "vertexCount": vertex_count,
        "vertexLimit": PATCH_MAX_VERTICES,
        "triangleCount": triangle_count,
        "triangleLimit": PATCH_MAX_TRIANGLES,
        "terrainMeshBytes": terrain_asset_bytes,
        "terrainMeshByteLimit": PATCH_MAX_ASSET_BYTES,
        "passes": bool(
            vertex_count <= PATCH_MAX_VERTICES
            and triangle_count <= PATCH_MAX_TRIANGLES
            and terrain_asset_bytes <= PATCH_MAX_ASSET_BYTES
        ),
    }
    if not report["passes"]:
        raise RoadSurfacePatchError(
            "local terrain patch exceeds resource limits: "
            f"vertices={vertex_count}/{PATCH_MAX_VERTICES}, "
            f"triangles={triangle_count}/{PATCH_MAX_TRIANGLES}, "
            f"meshBytes={terrain_asset_bytes}/{PATCH_MAX_ASSET_BYTES}"
        )
    return report


def verify_accepted_plane_refinement(
    mesh: PatchMesh,
    accepted_heights: np.ndarray,
    spacing_m: float,
    *,
    influence: Polygon | None = None,
    fail_closed: bool = True,
) -> dict[str, Any]:
    """Check refined faces against exact accepted source-triangle planes.

    Sampling a few points per face can miss the vertex of a clipped face/source
    overlay where the plane difference is largest.  Both surfaces are affine on
    each overlay polygon, so the extrema method checks every overlay vertex.
    """
    source_index = SourceOverlapIndex.from_grid(
        accepted_heights,
        width_m=(accepted_heights.shape[1] - 1) * spacing_m,
        depth_m=(accepted_heights.shape[0] - 1) * spacing_m,
        spacing_m=spacing_m,
        first_row=mesh.bounds.first_row,
        last_row=mesh.bounds.last_row,
        first_column=mesh.bounds.first_column,
        last_column=mesh.bounds.last_column,
    )
    clip_geometry = None
    if influence is not None:
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
        extrema = affine_surface_overlay_extrema(
            planar,
            mesh.base_y.astype(np.float64, copy=False),
            source_index,
            clip_geometry=clip_geometry,
        )
    except TopologyError as exc:
        raise RoadSurfacePatchError(f"accepted-plane overlay verification failed: {exc}") from exc
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
    if fail_closed and not report["passes"]:
        raise RoadSurfacePatchError(
            "refined patch does not reproduce accepted piecewise planes within 1 mm: "
            f"maximum error={maximum_error:.9g} m"
        )
    return report


def load_candidate_inputs(
    project_root: Path, config_path: Path
) -> tuple[PreviewConfig, ReleaseInputs, np.ndarray, dict[str, str]]:
    """Load and byte-bind the exact candidate config, release and accepted preview."""
    root = project_root.resolve()
    config = load_config(config_path)
    if (
        config.treatment_variant != "teignmouth-circled-segment"
        or config.output_directory != TEIGNMOUTH_CANDIDATE_OUTPUT
    ):
        raise RoadSurfacePatchError(
            "local triangle patch requires the exact Teignmouth candidate config"
        )
    release = load_release_inputs(root, config)
    preview_root = root / "public/worlds/torquay-road-surface-preview"
    preview_bytes = {name: (preview_root / name).read_bytes() for name in ACCEPTED_PREVIEW_HASHES}
    hashes = {name: hashlib.sha256(content).hexdigest() for name, content in preview_bytes.items()}
    if hashes != ACCEPTED_PREVIEW_HASHES:
        raise RoadSurfacePatchError(
            "accepted preview no longer matches the pinned immutable base hashes: "
            + json.dumps(hashes, sort_keys=True, separators=(",", ":"))
        )
    try:
        manifest = json.loads(preview_bytes["manifest.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoadSurfacePatchError("accepted preview manifest is invalid JSON") from exc
    if (
        manifest.get("packageType") != "road-surface-display-grid-derivative"
        or manifest.get("algorithmVersion") != "road-surface-preview-3.0.0"
        or manifest.get("source", {}).get("releaseId") != CURRENT_RELEASE_ID
        or manifest.get("grid", {}).get("spacingM") != 2.0
        or manifest.get("grid", {}).get("columns") != release.columns
        or manifest.get("grid", {}).get("rows") != release.rows
    ):
        raise RoadSurfacePatchError("accepted preview identity or grid is incompatible")
    if (
        hashlib.sha256(preview_bytes["heightfield.f32"]).hexdigest()
        != manifest["assets"]["heightfield"]["sha256"]
    ):
        raise RoadSurfacePatchError("accepted preview heightfield hash does not match its manifest")
    if hashlib.sha256(preview_bytes["qa.json"]).hexdigest() != manifest["assets"]["qa"]["sha256"]:
        raise RoadSurfacePatchError("accepted preview QA hash does not match its manifest")
    expected_bytes = release.rows * release.columns * 4
    if len(preview_bytes["heightfield.f32"]) != expected_bytes:
        raise RoadSurfacePatchError("accepted preview heightfield has the wrong byte length")
    accepted = np.frombuffer(preview_bytes["heightfield.f32"], dtype="<f4").reshape(
        (release.rows, release.columns)
    )
    if not np.isfinite(accepted).all():
        raise RoadSurfacePatchError("accepted preview contains non-finite heights")
    source = manifest.get("source", {})
    release_binding = {
        "releaseId": release.release_id,
        "readySha256": release.ready_sha256,
        "inventorySha256": release.inventory_sha256,
        "terrainManifestSha256": release.manifest_sha256,
        "terrainHeightfieldSha256": release.manifest["heightfield"]["sha256"],
        "roadManifestSha256": release.road_manifest_sha256,
        "roadPayloadSha256": release.road_payload_sha256,
    }
    if any(source.get(key) != value for key, value in release_binding.items()):
        raise RoadSurfacePatchError(
            "accepted preview is not bound to the validated current release"
        )
    try:
        preview_qa = json.loads(preview_bytes["qa.json"])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RoadSurfacePatchError("accepted preview QA is invalid JSON") from exc
    if not isinstance(preview_qa, dict):
        raise RoadSurfacePatchError("accepted preview QA must be an object")
    release = replace(release, accepted_preview_qa=preview_qa)
    return config, release, accepted.copy(), hashes


def _target_part_and_bounds(
    inputs: ReleaseInputs,
) -> tuple[Polygon, PatchBounds, list[tuple[float, float]], list[float]]:
    """Derive a bounded target line buffer and 2 m cell-aligned patch extent."""
    feature = next(
        (
            item
            for item in inputs.road_payload.get("features", [])
            if item.get("source", {}).get("osmId") == TEIGNMOUTH_WAY_ID
        ),
        None,
    )
    if feature is None:
        raise RoadSurfacePatchError(f"pinned road payload has no way {TEIGNMOUTH_WAY_ID}")
    parts = feature.get("centerlinePartsXZ")
    if not isinstance(parts, list) or len(parts) <= TEIGNMOUTH_PART_INDEX:
        raise RoadSurfacePatchError("pinned Teignmouth Road part 0 is missing")
    part = [(float(point[0]), float(point[1])) for point in parts[TEIGNMOUTH_PART_INDEX]]
    if len(part) < 2:
        raise RoadSurfacePatchError("pinned Teignmouth Road part 0 has fewer than two vertices")
    cumulative = [0.0]
    for first, second in zip(part, part[1:], strict=False):
        cumulative.append(cumulative[-1] + math.dist(first, second))
    if cumulative[-1] < TEIGNMOUTH_STATION_END_M:
        raise RoadSurfacePatchError("pinned Teignmouth Road part does not cover station 155 m")

    def interpolate_station(station: float) -> tuple[float, float]:
        for index in range(len(part) - 1):
            if cumulative[index] <= station <= cumulative[index + 1]:
                length = cumulative[index + 1] - cumulative[index]
                fraction = (station - cumulative[index]) / length
                return (
                    part[index][0] + (part[index + 1][0] - part[index][0]) * fraction,
                    part[index][1] + (part[index + 1][1] - part[index][1]) * fraction,
                )
        raise RoadSurfacePatchError(f"Teignmouth station {station:g} is outside part 0")

    target_points = [
        interpolate_station(TEIGNMOUTH_STATION_START_M),
        *[
            point
            for point, station in zip(part, cumulative, strict=True)
            if TEIGNMOUTH_STATION_START_M < station < TEIGNMOUTH_STATION_END_M
        ],
        interpolate_station(TEIGNMOUTH_STATION_END_M),
    ]
    # Keep point order on the source centerline; remove only coincident vertices.
    ordered_points = [target_points[0]]
    for point in target_points[1:]:
        if point != ordered_points[-1]:
            ordered_points.append(point)
    if len(ordered_points) < 2:
        raise RoadSurfacePatchError("registered Teignmouth segment is degenerate")
    centerline = LineString(ordered_points)
    road_width = float(feature.get("estimatedWidthM", 0.0))
    if road_width != 6.0:
        raise RoadSurfacePatchError("registered Teignmouth width is not the pinned 6 m estimate")
    influence = centerline.buffer(road_width / 2 + PATCH_MAX_TRANSITION_M, cap_style="round")
    min_x, min_z, max_x, max_z = influence.bounds
    first_column = max(0, math.floor((min_x + inputs.width_m / 2) / inputs.spacing_m))
    last_column = min(
        inputs.columns - 1,
        math.ceil((max_x + inputs.width_m / 2) / inputs.spacing_m),
    )
    first_row = max(0, math.floor((min_z + inputs.depth_m / 2) / inputs.spacing_m))
    last_row = min(
        inputs.rows - 1,
        math.ceil((max_z + inputs.depth_m / 2) / inputs.spacing_m),
    )
    bounds = PatchBounds(
        first_row=first_row,
        first_column=first_column,
        row_count=last_row - first_row,
        column_count=last_column - first_column,
    )
    bounds.validate(inputs.rows, inputs.columns, inputs.spacing_m)
    return influence, bounds, ordered_points, cumulative


def _patch_sample_weights(
    mesh: PatchMesh,
    inputs: ReleaseInputs,
    x: float,
    z: float,
) -> dict[int, float]:
    """Return deterministic barycentric vertex weights for the rendered patch surface."""
    _triangle_index, weights = _patch_triangle_weights(mesh, inputs, x, z)
    return weights


def _patch_triangle_weights(
    mesh: PatchMesh,
    inputs: ReleaseInputs,
    x: float,
    z: float,
) -> tuple[int, dict[int, float]]:
    """Return a deterministic owning patch face and its barycentric weights."""
    gx = (x + inputs.width_m / 2) / inputs.spacing_m
    gz = (z + inputs.depth_m / 2) / inputs.spacing_m
    column = min(math.floor(gx), inputs.columns - 2)
    row = min(math.floor(gz), inputs.rows - 2)
    if (
        row < mesh.bounds.first_row
        or row >= mesh.bounds.last_row
        or column < mesh.bounds.first_column
        or column >= mesh.bounds.last_column
    ):
        raise RoadSurfacePatchError("registered Teignmouth sample falls outside the patch")
    if mesh.triangle_tree is not None and mesh.triangle_geometries is not None:
        point_geometry = Point(float(x), float(z))
        candidates = sorted(
            int(index) for index in mesh.triangle_tree.query(point_geometry, predicate="intersects")
        )
        point = np.asarray((x, z), dtype=np.float64)
        for triangle_index in candidates:
            indices = mesh.triangles[triangle_index].astype(np.int64)
            vertices = mesh.vertices_xz[indices].astype(np.float64)
            matrix = np.column_stack((vertices[1] - vertices[0], vertices[2] - vertices[0]))
            try:
                tail = np.linalg.solve(matrix, point - vertices[0])
            except np.linalg.LinAlgError:
                continue
            weights = np.asarray((1.0 - tail.sum(), tail[0], tail[1]))
            if np.all(weights >= -1e-9) and np.all(weights <= 1.0 + 1e-9):
                return int(triangle_index), {
                    int(index): float(weight)
                    for index, weight in zip(indices, weights, strict=True)
                    if abs(float(weight)) > 1e-14
                }
        raise RoadSurfacePatchError("registered sample is not covered by indexed patch triangles")
    u, v = gx - column, gz - row
    point = np.asarray([x, z], dtype=np.float64)
    half = 0 if u + v <= 1.0 else 1
    on_collar = row in (mesh.bounds.first_row, mesh.bounds.last_row - 1) or column in (
        mesh.bounds.first_column,
        mesh.bounds.last_column - 1,
    )
    if not on_collar:
        local_row = (v if half == 0 else 1.0 - v) * 4
        local_column = (u if half == 0 else 1.0 - u) * 4
        cell_row = min(3, max(0, math.floor(local_row)))
        cell_column = min(3, max(0, math.floor(local_column)))
        row_fraction = local_row - cell_row
        column_fraction = local_column - cell_column
        a = (4 * row + cell_row, 4 * column + cell_column)
        b = (a[0], a[1] + 1)
        c = (a[0] + 1, a[1])
        if row_fraction + column_fraction <= 1.0 or cell_row + cell_column >= 3:
            local_keys = (a, b, c)
        else:
            d = (a[0] + 1, a[1] + 1)
            local_keys = (b, d, c)
        if half == 1:
            local_keys = tuple(
                (
                    4 * row + (4 - (key[0] - 4 * row)),
                    4 * column + (4 - (key[1] - 4 * column)),
                )
                for key in local_keys
            )
        triangle_index = mesh.triangle_key_to_id.get(tuple(sorted(local_keys)))
        if triangle_index is not None:
            indices = mesh.triangles[triangle_index].astype(np.int64)
            vertices = mesh.vertices_xz[indices].astype(np.float64)
            first, second, third = vertices
            delta_first, delta_second = second - first, third - first
            relative = point - first
            determinant = delta_first[0] * delta_second[1] - delta_first[1] * delta_second[0]
            tail_first = (
                relative[0] * delta_second[1] - relative[1] * delta_second[0]
            ) / determinant
            tail_second = (
                delta_first[0] * relative[1] - delta_first[1] * relative[0]
            ) / determinant
            weights = np.asarray([1.0 - tail_first - tail_second, tail_first, tail_second])
            if np.all(weights >= -1e-8) and np.all(weights <= 1.0 + 1e-8):
                return int(triangle_index), {
                    int(index): float(weight)
                    for index, weight in zip(indices, weights, strict=True)
                    if abs(float(weight)) > 1e-14
                }
    for triangle_index in mesh.cell_half_triangles[(row, column, half)]:
        indices = mesh.triangles[triangle_index].astype(np.int64)
        vertices = mesh.vertices_xz[indices].astype(np.float64)
        matrix = np.column_stack((vertices[1] - vertices[0], vertices[2] - vertices[0]))
        try:
            tail = np.linalg.solve(matrix, point - vertices[0])
        except np.linalg.LinAlgError:
            continue
        weights = np.asarray([1.0 - tail.sum(), tail[0], tail[1]])
        if np.all(weights >= -1e-10) and np.all(weights <= 1.0 + 1e-10):
            return int(triangle_index), {
                int(index): float(weight)
                for index, weight in zip(indices, weights, strict=True)
                if abs(float(weight)) > 1e-14
            }
    raise RoadSurfacePatchError("registered Teignmouth sample is not covered by patch triangles")


@dataclass(frozen=True)
class CompositeSurface:
    """Accepted grid with one indexed local patch and the exact solver Float32 buffer."""

    mesh: PatchMesh
    inputs: ReleaseInputs
    accepted_heights: np.ndarray
    patch_heights: np.ndarray

    def __post_init__(self) -> None:
        candidate = np.asarray(self.patch_heights)
        if candidate.dtype != np.dtype("<f4") or candidate.shape != (len(self.mesh.vertices_xz),):
            raise RoadSurfacePatchError(
                "composite patch heights must be the exact Float32 vertex buffer"
            )
        if not np.isfinite(candidate).all():
            raise RoadSurfacePatchError("composite patch contains non-finite heights")

    def sample(self, x: float, z: float) -> tuple[float, int | None]:
        """Return deterministic displayed height and optional local patch triangle ID."""
        gx = (x + self.inputs.width_m / 2) / self.inputs.spacing_m
        gz = (z + self.inputs.depth_m / 2) / self.inputs.spacing_m
        column = min(math.floor(gx), self.inputs.columns - 2)
        row = min(math.floor(gz), self.inputs.rows - 2)
        bounds = self.mesh.bounds
        if not (
            bounds.first_row <= row < bounds.last_row
            and bounds.first_column <= column < bounds.last_column
        ):
            return _sample_grid(self.accepted_heights, x, z, self.inputs.spacing_m), None
        triangle_index, weights = _patch_triangle_weights(self.mesh, self.inputs, x, z)
        height = math.fsum(
            float(self.patch_heights[index]) * weight for index, weight in weights.items()
        )
        return height, triangle_index

    def sample_many(self, x: np.ndarray, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Vectorized composite sampling; triangle IDs are -1 outside the patch."""
        x_values, z_values = np.broadcast_arrays(
            np.asarray(x, dtype=np.float64), np.asarray(z, dtype=np.float64)
        )
        heights = _sample_grid_many(
            self.accepted_heights, x_values.ravel(), z_values.ravel(), self.inputs.spacing_m
        )
        triangle_ids = np.full(heights.shape, -1, dtype=np.int64)
        flat_x, flat_z = x_values.ravel(), z_values.ravel()
        columns = np.minimum(
            np.floor((flat_x + self.inputs.width_m / 2) / self.inputs.spacing_m).astype(np.int64),
            self.inputs.columns - 2,
        )
        rows = np.minimum(
            np.floor((flat_z + self.inputs.depth_m / 2) / self.inputs.spacing_m).astype(np.int64),
            self.inputs.rows - 2,
        )
        bounds = self.mesh.bounds
        local_ids = np.flatnonzero(
            (rows >= bounds.first_row)
            & (rows < bounds.last_row)
            & (columns >= bounds.first_column)
            & (columns < bounds.last_column)
        )
        for index in local_ids:
            sample_x, sample_z = float(flat_x[index]), float(flat_z[index])
            _height, triangle_id = self.sample(float(sample_x), float(sample_z))
            if triangle_id is not None:
                heights[index] = _height
                triangle_ids[index] = triangle_id
        return heights.reshape(x_values.shape), triangle_ids.reshape(x_values.shape)


def verify_composite_terrain(
    surface: CompositeSurface,
    influence: Polygon,
    *,
    fail_closed: bool = True,
) -> dict[str, Any]:
    """Check exact source/base preservation, whole-surface change, and edge-gradient limits."""
    mesh, inputs, accepted, candidate = (
        surface.mesh,
        surface.inputs,
        surface.accepted_heights,
        surface.patch_heights,
    )
    fixed = _fixed_patch_vertices(mesh, influence)
    fixed_ids = np.flatnonzero(fixed)
    fixed_bytes_match = (
        candidate[fixed_ids].astype("<f4").tobytes()
        == mesh.base_y[fixed_ids].astype("<f4").tobytes()
    )
    boundary_ids = np.unique(mesh.boundary_edges)
    boundary_height_bytes_match = (
        candidate[boundary_ids].astype("<f4").tobytes()
        == mesh.base_y[boundary_ids].astype("<f4").tobytes()
    )
    boundary_xz = mesh.vertices_xz[boundary_ids].astype("<f4")
    boundary_xy_match = True
    for vertex_id, (x, z) in zip(boundary_ids, boundary_xz, strict=True):
        column = int(round((float(x) + inputs.width_m / 2) / inputs.spacing_m))
        row = int(round((float(z) + inputs.depth_m / 2) / inputs.spacing_m))
        boundary_xy_match &= bool(
            np.float32(x).tobytes()
            == np.float32(column * inputs.spacing_m - inputs.width_m / 2).tobytes()
            and np.float32(z).tobytes()
            == np.float32(row * inputs.spacing_m - inputs.depth_m / 2).tobytes()
            and np.float32(candidate[int(vertex_id)]).tobytes()
            == np.float32(accepted[row, column]).tobytes()
        )

    outside_triangles = ~_triangles_fully_within_influence(mesh, influence)
    outside_ids = np.flatnonzero(outside_triangles)
    sample_weights = np.asarray(
        ((0.5, 0.25, 0.25), (0.25, 0.5, 0.25), (0.25, 0.25, 0.5), (1 / 3, 1 / 3, 1 / 3)),
        dtype=np.float64,
    )
    positions = mesh.vertices_xz[mesh.triangles[outside_ids]].astype(np.float64)
    values = candidate[mesh.triangles[outside_ids]].astype(np.float64)
    sample_xz = np.einsum("sk,tkd->tsd", sample_weights, positions, optimize=True)
    sample_candidate = np.einsum("sk,tk->ts", sample_weights, values, optimize=True)
    sample_accepted = _sample_grid_many(
        accepted, sample_xz[:, :, 0].ravel(), sample_xz[:, :, 1].ravel(), inputs.spacing_m
    ).reshape(sample_candidate.shape)
    outside_plane_error = (
        float(np.max(np.abs(sample_candidate - sample_accepted))) if outside_ids.size else 0.0
    )

    bounds = mesh.bounds
    baseline = inputs.baseline.astype(np.float64)
    accepted64 = accepted.astype(np.float64)
    row_nodes, column_nodes = np.indices(accepted.shape)
    unchanged_nodes = ~(
        (row_nodes >= bounds.first_row)
        & (row_nodes <= bounds.last_row)
        & (column_nodes >= bounds.first_column)
        & (column_nodes <= bounds.last_column)
    )
    old_global_change = np.abs(accepted64 - baseline)
    global_change = (
        float(np.max(old_global_change[unchanged_nodes])) if np.any(unchanged_nodes) else 0.0
    )
    patch_source = _sample_grid_many(
        baseline,
        mesh.vertices_xz[:, 0],
        mesh.vertices_xz[:, 1],
        inputs.spacing_m,
    )
    global_change = max(
        global_change, float(np.max(np.abs(candidate.astype(np.float64) - patch_source)))
    )
    unpatched_signed_changes = (accepted64 - baseline)[unchanged_nodes]
    patch_signed_changes = candidate.astype(np.float64) - patch_source
    maximum_fill_change = max(
        float(np.max(unpatched_signed_changes)) if unpatched_signed_changes.size else 0.0,
        float(np.max(patch_signed_changes)),
    )
    maximum_cut_change = min(
        float(np.min(unpatched_signed_changes)) if unpatched_signed_changes.size else 0.0,
        float(np.min(patch_signed_changes)),
    )

    x_edge_keep = ~(
        (row_nodes[:, :-1] >= bounds.first_row)
        & (row_nodes[:, :-1] <= bounds.last_row)
        & (column_nodes[:, :-1] >= bounds.first_column)
        & (column_nodes[:, :-1] < bounds.last_column)
    )
    z_edge_keep = ~(
        (row_nodes[:-1, :] >= bounds.first_row)
        & (row_nodes[:-1, :] < bounds.last_row)
        & (column_nodes[:-1, :] >= bounds.first_column)
        & (column_nodes[:-1, :] <= bounds.last_column)
    )
    old_base_x = np.abs(np.diff(baseline, axis=1)) / inputs.spacing_m
    old_preview_x = np.abs(np.diff(accepted64, axis=1)) / inputs.spacing_m
    old_base_z = np.abs(np.diff(baseline, axis=0)) / inputs.spacing_m
    old_preview_z = np.abs(np.diff(accepted64, axis=0)) / inputs.spacing_m
    outside_added = np.concatenate(
        (
            (old_preview_x - old_base_x)[x_edge_keep],
            (old_preview_z - old_base_z)[z_edge_keep],
        )
    )
    old_max_added = float(np.max(outside_added)) if outside_added.size else -math.inf
    edges = np.asarray(sorted(mesh.edge_counts), dtype=np.int64)
    edge_xz = mesh.vertices_xz[edges].astype(np.float64)
    edge_lengths = np.linalg.norm(edge_xz[:, 1] - edge_xz[:, 0], axis=1)
    source_edge = _sample_grid_many(
        baseline,
        edge_xz[:, :, 0].ravel(),
        edge_xz[:, :, 1].ravel(),
        inputs.spacing_m,
    ).reshape((-1, 2))
    candidate_edge = candidate[edges].astype(np.float64)
    source_slopes = np.abs(source_edge[:, 1] - source_edge[:, 0]) / edge_lengths
    preview_slopes = np.abs(candidate_edge[:, 1] - candidate_edge[:, 0]) / edge_lengths
    added = preview_slopes - source_slopes
    maximum_added = max(old_max_added, float(np.max(added)) if added.size else -math.inf)
    maximum_added_index = int(np.argmax(added)) if added.size else None
    directional_edge_summary = {}
    for name, mask in (
        ("x", np.isclose(edge_xz[:, 1, 1] - edge_xz[:, 0, 1], 0.0, atol=1e-9)),
        ("z", np.isclose(edge_xz[:, 1, 0] - edge_xz[:, 0, 0], 0.0, atol=1e-9)),
        ("diagonal", np.ones(len(edges), dtype=bool)),
    ):
        if name == "diagonal":
            mask = ~(
                np.isclose(edge_xz[:, 1, 1] - edge_xz[:, 0, 1], 0.0, atol=1e-9)
                | np.isclose(edge_xz[:, 1, 0] - edge_xz[:, 0, 0], 0.0, atol=1e-9)
            )
        directional_edge_summary[name] = {
            "edgeCount": int(mask.sum()),
            "maximumBaselineGradientMPerM": float(np.max(source_slopes[mask]))
            if np.any(mask)
            else 0.0,
            "maximumCandidateGradientMPerM": float(np.max(preview_slopes[mask]))
            if np.any(mask)
            else 0.0,
            "maximumPositiveAddedGradientMPerM": float(np.max(added[mask]))
            if np.any(mask)
            else -math.inf,
        }
    maximum_patch_vertex_change = float(np.max(np.abs(candidate.astype(np.float64) - patch_source)))
    report = {
        "fixedVertexCount": int(fixed.sum()),
        "fixedAcceptedFloat32BytesMatch": fixed_bytes_match,
        "perimeterVertexCount": int(len(boundary_ids)),
        "perimeterXYZFloat32BytesMatch": bool(boundary_height_bytes_match and boundary_xy_match),
        "outsideInfluenceTriangleCount": int(outside_ids.size),
        "outsideInfluenceRefinementSampleCount": int(sample_candidate.size),
        "maximumOutsideInfluenceAcceptedPlaneDeviationM": outside_plane_error,
        "outsideInfluenceAcceptedPlaneLimitM": 0.001,
        "outsideInfluenceAcceptedPlanePasses": outside_plane_error <= 0.001,
        "maximumAbsoluteChangeFromSourceM": global_change,
        "maximumAbsoluteChangeLimitM": 5.0,
        "maximumFillFromSourceM": maximum_fill_change,
        "maximumCutFromSourceM": maximum_cut_change,
        "maximumPositiveAddedGradientMPerM": maximum_added,
        "maximumPositiveAddedGradientLimitMPerM": 1.0,
        "fineEdgeGradientByDirection": directional_edge_summary,
        "maximumPositiveAddedGradientEdge": (
            {
                "vertices": [int(value) for value in edges[maximum_added_index]],
                "firstLocalXZ": edge_xz[maximum_added_index, 0].tolist(),
                "secondLocalXZ": edge_xz[maximum_added_index, 1].tolist(),
                "sourceGradientMPerM": float(source_slopes[maximum_added_index]),
                "candidateGradientMPerM": float(preview_slopes[maximum_added_index]),
            }
            if maximum_added_index is not None and added[maximum_added_index] >= old_max_added
            else None
        ),
        "patchVertexMaximumAbsoluteChangeFromSourceM": maximum_patch_vertex_change,
        "passes": bool(
            np.isfinite(candidate).all()
            and fixed_bytes_match
            and boundary_height_bytes_match
            and boundary_xy_match
            and outside_plane_error <= 0.001
            and global_change < 5.0
            and maximum_added < 1.0
        ),
    }
    if fail_closed and not report["passes"]:
        raise RoadSurfacePatchError(f"composite terrain safety gates failed: {report}")
    return report


def _coarse_triangle_polygon(row: int, column: int, half: int, inputs: ReleaseInputs) -> Polygon:
    x0 = column * inputs.spacing_m - inputs.width_m / 2
    x1 = x0 + inputs.spacing_m
    z0 = row * inputs.spacing_m - inputs.depth_m / 2
    z1 = z0 + inputs.spacing_m
    return Polygon(((x0, z0), (x1, z0), (x0, z1)) if half == 0 else ((x1, z1), (x0, z1), (x1, z0)))


def _triangle_linear_height(
    triangle_xz: np.ndarray,
    triangle_y: np.ndarray,
    x: float,
    z: float,
) -> float:
    matrix = np.column_stack((triangle_xz[1] - triangle_xz[0], triangle_xz[2] - triangle_xz[0]))
    bary_tail = np.linalg.solve(matrix, np.asarray([x, z], dtype=np.float64) - triangle_xz[0])
    weights = np.asarray([1.0 - bary_tail.sum(), bary_tail[0], bary_tail[1]])
    return float(np.dot(weights, triangle_y))


def _triangle_barycentric_weights(
    triangle_xz: np.ndarray,
    x: float,
    z: float,
) -> np.ndarray:
    """Return owner-triangle weights for a world/local XZ point."""
    matrix = np.column_stack((triangle_xz[1] - triangle_xz[0], triangle_xz[2] - triangle_xz[0]))
    bary_tail = np.linalg.solve(matrix, np.asarray([x, z], dtype=np.float64) - triangle_xz[0])
    return np.asarray([1.0 - bary_tail.sum(), bary_tail[0], bary_tail[1]])


def _barycentric_violation(weights: np.ndarray) -> float:
    return max(0.0, float(-np.min(weights)), float(np.max(weights) - 1.0))


def _triangle_vertex_adjacency(
    mesh: PatchMesh,
) -> tuple[dict[tuple[int, int], tuple[int, ...]], dict[int, tuple[int, ...]]]:
    edge_faces: dict[tuple[int, int], list[int]] = {}
    vertex_faces: dict[int, list[int]] = {}
    for triangle_id, triangle in enumerate(mesh.triangles):
        ids = [int(value) for value in triangle]
        for vertex_id in ids:
            vertex_faces.setdefault(vertex_id, []).append(triangle_id)
        for first, second in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            edge_faces.setdefault(tuple(sorted((first, second))), []).append(triangle_id)
    return (
        {edge: tuple(face_ids) for edge, face_ids in edge_faces.items()},
        {vertex: tuple(face_ids) for vertex, face_ids in vertex_faces.items()},
    )


def _shared_float32_owners(
    mesh: PatchMesh,
    triangle_id: int,
    point: tuple[float, float],
    edge_faces: dict[tuple[int, int], tuple[int, ...]],
    vertex_faces: dict[int, tuple[int, ...]],
) -> tuple[int, ...]:
    """Find exact shared-edge/vertex owners before Float32 coordinate quantization."""
    triangle_ids = mesh.triangles[triangle_id].astype(np.int64)
    owner_xz = mesh.vertices_xz[triangle_ids].astype(np.float64)
    weights = _triangle_barycentric_weights(owner_xz, *point)
    near_zero = np.flatnonzero(np.abs(weights) <= 1e-9)
    selected = {triangle_id}
    if len(near_zero) >= 2:
        vertex_local = int(np.argmax(weights))
        selected.update(vertex_faces.get(int(triangle_ids[vertex_local]), ()))
    elif len(near_zero) == 1:
        edge_ids = [int(triangle_ids[index]) for index in range(3) if index != int(near_zero[0])]
        selected.update(edge_faces.get(tuple(sorted(edge_ids)), ()))
    point_xz = np.asarray(point, dtype=np.float64)
    result = []
    for candidate_id in sorted(selected):
        candidate_triangle = mesh.triangles[candidate_id].astype(np.int64)
        candidate_xz = mesh.vertices_xz[candidate_triangle].astype(np.float64)
        if _barycentric_violation(_triangle_barycentric_weights(candidate_xz, *point_xz)) <= 1e-8:
            result.append(candidate_id)
    return tuple(result or (triangle_id,))


def _float32_neighbors(value: float, steps: int = 2) -> tuple[np.float32, ...]:
    center = np.float32(value)
    lower = upper = center
    values = {center.tobytes(): center}
    for _ in range(steps):
        lower = np.nextafter(lower, np.float32(-np.inf), dtype=np.float32)
        upper = np.nextafter(upper, np.float32(np.inf), dtype=np.float32)
        values[lower.tobytes()] = lower
        values[upper.tobytes()] = upper
    return tuple(values[key] for key in sorted(values))


def _quantize_road_point_for_owners(
    mesh: PatchMesh,
    point: tuple[float, float],
    owner_ids: tuple[int, ...],
) -> tuple[tuple[float, float], float]:
    """Choose the nearest local Float32 XZ accepted by every exact shared owner.

    A bounded 32-ULP lattice search accommodates negative-coordinate Float32 rounding
    at shared triangulation edges. The unchanged 1e-6 barycentric gate is applied to
    every exact owner; failure includes the original point and owner geometry.
    """
    quantized = (np.float32(point[0]), np.float32(point[1]))

    owner_geometry = []
    for owner_id in owner_ids:
        triangle_ids = mesh.triangles[owner_id].astype(np.int64)
        triangle_xz = mesh.vertices_xz[triangle_ids].astype(np.float64)
        matrix = np.column_stack((triangle_xz[1] - triangle_xz[0], triangle_xz[2] - triangle_xz[0]))
        owner_geometry.append((owner_id, triangle_ids, triangle_xz, np.linalg.inv(matrix)))

    def violations(candidates: np.ndarray) -> np.ndarray:
        maximum = np.zeros(len(candidates), dtype=np.float64)
        for _owner_id, _triangle_ids, triangle_xz, inverse in owner_geometry:
            tail = (candidates - triangle_xz[0]) @ inverse.T
            weights = np.column_stack((1.0 - tail.sum(axis=1), tail))
            maximum = np.maximum(
                maximum,
                np.maximum(0.0, np.maximum(-weights.min(axis=1), weights.max(axis=1) - 1.0)),
            )
        return maximum

    direct_candidate = np.asarray([[quantized[0], quantized[1]]], dtype=np.float64)
    direct_violation = float(violations(direct_candidate)[0])
    if direct_violation <= 1e-6:
        return (float(quantized[0]), float(quantized[1])), direct_violation
    search_steps = 32
    candidates_x = np.asarray(_float32_neighbors(point[0], steps=search_steps), dtype=np.float64)
    candidates_z = np.asarray(_float32_neighbors(point[1], steps=search_steps), dtype=np.float64)
    grid_x, grid_z = np.meshgrid(candidates_x, candidates_z, indexing="ij")
    candidates = np.column_stack((grid_x.ravel(), grid_z.ravel()))
    candidate_violations = violations(candidates)
    accepted_indices = np.flatnonzero(candidate_violations <= 1e-6)
    if not len(accepted_indices):
        owner_details = []
        for owner_id, triangle_ids, triangle_xz, _inverse in owner_geometry:
            weights = _triangle_barycentric_weights(
                triangle_xz, float(quantized[0]), float(quantized[1])
            )
            owner_details.append(
                {
                    "ownerTriangleId": owner_id,
                    "triangleVertexIds": triangle_ids.tolist(),
                    "triangleXZ": triangle_xz.tolist(),
                    "directFloat32BarycentricWeights": weights.tolist(),
                    "directFloat32Violation": _barycentric_violation(weights),
                }
            )
        raise RoadSurfacePatchError(
            "Float32 road vertex cannot be assigned to every exact shared owner within the "
            "unchanged 1e-6 barycentric tolerance; "
            f"pointXZ={list(point)}, directFloat32XZ={list(quantized)}, "
            f"ownerTriangleIds={list(owner_ids)}, directViolation={direct_violation:.9g}, "
            f"searchUlpRadius={search_steps}, ownerDetails={owner_details}"
        )
    displacement = np.sum((candidates[accepted_indices] - np.asarray(point)) ** 2, axis=1)
    selected = int(accepted_indices[int(np.argmin(displacement))])
    return (
        (float(np.float32(candidates[selected, 0])), float(np.float32(candidates[selected, 1]))),
        float(candidate_violations[selected]),
    )


def patch_source_triangle_ownership_report(
    mesh: PatchMesh,
    inputs: ReleaseInputs,
) -> dict[str, Any]:
    """Prove every patch face has complete, nonoverlapping source triangle provenance."""
    source_index = SourceOverlapIndex.from_grid(
        inputs.baseline,
        width_m=inputs.width_m,
        depth_m=inputs.depth_m,
        spacing_m=inputs.spacing_m,
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
    violations = []
    multiple_source_face_count = 0
    try:
        provenance = source_overlap_provenance(planar, source_index)
        for overlaps in provenance:
            if len(overlaps) > 1:
                multiple_source_face_count += 1
    except TopologyError as exc:
        violations.append({"reason": "source overlap index rejected topology", "error": str(exc)})
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
    return report


def composite_earthwork_overlay_report(surface: CompositeSurface) -> dict[str, Any]:
    """Measure earthwork extrema over the exact refined/source-triangle overlay.

    Both height fields are affine on each patch/source-triangle overlap, so their
    difference reaches extrema at the overlay polygon's vertices.
    """
    mesh = surface.mesh
    ownership = patch_source_triangle_ownership_report(mesh, surface.inputs)
    source_at_vertices = _sample_grid_many(
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
    return report


def _composite_maximum_under_polygon(
    polygon: Polygon,
    surface: CompositeSurface,
) -> float:
    """Find the exact piecewise-linear terrain maximum over one complete footprint."""
    inputs, mesh = surface.inputs, surface.mesh
    min_x, min_z, max_x, max_z = polygon.bounds
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
                coarse_polygon = _coarse_triangle_polygon(row, column, half, inputs)
                overlap = polygon.intersection(coarse_polygon)
                if overlap.is_empty:
                    continue
                if in_patch:
                    triangle_ids = mesh.cell_half_triangles[(row, column, half)]
                    for triangle_id in triangle_ids:
                        triangle_ids_array = mesh.triangles[triangle_id].astype(np.int64)
                        triangle_xz = mesh.vertices_xz[triangle_ids_array].astype(np.float64)
                        triangle_y = surface.patch_heights[triangle_ids_array].astype(np.float64)
                        face_polygon = Polygon(triangle_xz)
                        face_overlap = overlap.intersection(face_polygon)
                        if face_overlap.is_empty:
                            continue
                        for x, z in _geometry_points(face_overlap):
                            maximum = max(
                                maximum,
                                _triangle_linear_height(triangle_xz, triangle_y, x, z),
                            )
                else:
                    for x, z in _geometry_points(overlap):
                        maximum = max(
                            maximum,
                            _sample_grid(surface.accepted_heights, x, z, inputs.spacing_m),
                        )
    if not math.isfinite(maximum):
        raise RoadSurfacePatchError("building footprint has no samples on the composite surface")
    return maximum


def composite_building_base_report(
    surface: CompositeSurface,
    *,
    fail_closed: bool = True,
) -> dict[str, Any]:
    """Re-evaluate every complete building footprint and registered risk building."""
    features = surface.inputs.buildings.get("buildings")
    if not isinstance(features, list) or len(features) != 3613:
        raise RoadSurfacePatchError(
            "pinned building package must contain all 3,613 footprints for the offline gate"
        )
    changes: list[float] = []
    records = []
    for feature in features:
        if not isinstance(feature, dict):
            raise RoadSurfacePatchError("pinned building payload contains a malformed feature")
        baseline_base = _maximum_under_building(feature, surface.inputs.baseline, surface.inputs)
        candidate_base = max(
            _composite_maximum_under_polygon(
                Polygon(item["exteriorXZ"], item.get("interiorRingsXZ", [])), surface
            )
            for item in feature["geometry"]["polygons"]
        )
        change = candidate_base - baseline_base
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
        raise RoadSurfacePatchError(f"registered local building controls are missing: {missing}")
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
            baseline_y = _sample_grid(
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
            - _sample_grid(surface.inputs.baseline, x, z, surface.inputs.spacing_m)
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
        "p95LimitM": PATCH_MAX_BUILDING_P95,
        "maximumLimitM": PATCH_MAX_BUILDING_BASE,
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
            and p95 <= PATCH_MAX_BUILDING_P95
            and maximum <= PATCH_MAX_BUILDING_BASE
            and all(abs(by_id[building_id]) <= 0.05 for building_id in risk_ids[:5])
        ),
    }
    if fail_closed and not report["passes"]:
        raise RoadSurfacePatchError(
            "complete composite building-base gates failed: "
            f"p95={p95:.9g}/{PATCH_MAX_BUILDING_P95:g} m, "
            f"max={maximum:.9g}/{PATCH_MAX_BUILDING_BASE:g} m, "
            f"local review count={len(flagged)}"
        )
    return report


def _road_part_stations(
    part: list[tuple[float, float]], maximum_spacing_m: float
) -> tuple[list[float], float]:
    cumulative = [0.0]
    for first, second in zip(part, part[1:], strict=False):
        cumulative.append(cumulative[-1] + math.dist(first, second))
    length = cumulative[-1]
    if length <= 0:
        return [], 0.0
    count = max(1, math.ceil(length / maximum_spacing_m))
    stations = sorted(set([length * index / count for index in range(count + 1)] + cumulative))
    return stations, length


def mandatory_corridor_station_union(
    inputs: Any,
    *,
    way_ids: tuple[int, ...] = SEVERE_CORRIDOR_WAY_IDS,
    require_accepted_fallback_qa: bool = False,
) -> dict[tuple[int, int], tuple[float, ...]]:
    """Return the shared ≤1 m corridor samples plus pinned fallback boundary stations.

    The accepted preview's hash-validated QA records the extra stations at each connected
    harm-fallback interval endpoint. Those endpoints are part of the accepted 439-severe-
    station corridor census, so both solver constraint selection and final QA use this union.
    """
    preview_qa = getattr(inputs, "accepted_preview_qa", None)
    fallback = None
    if isinstance(preview_qa, dict):
        fallback = preview_qa.get("gridTreatment", {}).get("harmFallback")
    if require_accepted_fallback_qa and not isinstance(fallback, dict):
        raise RoadSurfacePatchError("hash-validated accepted-preview fallback QA is unavailable")

    fallback_stations: dict[tuple[int, int], list[float]] = {}
    for region in fallback.get("regions", []) if isinstance(fallback, dict) else []:
        if not isinstance(region, dict):
            raise RoadSurfacePatchError("accepted-preview fallback region is malformed")
        for interval in region.get("stationIntervals", []):
            if not isinstance(interval, dict):
                raise RoadSurfacePatchError(
                    "accepted-preview fallback station interval is malformed"
                )
            way_id = int(interval["wayId"])
            if way_id not in way_ids:
                continue
            part_index = int(interval["partIndex"])
            start, end = float(interval["startM"]), float(interval["endM"])
            if not all(math.isfinite(value) for value in (start, end)) or start > end:
                raise RoadSurfacePatchError(
                    "accepted-preview fallback interval has invalid stations"
                )
            fallback_stations.setdefault((way_id, part_index), []).extend((start, end))

    features = {
        int(feature.get("source", {}).get("osmId", -1)): feature
        for feature in inputs.road_payload.get("features", [])
        if isinstance(feature, dict)
    }
    union: dict[tuple[int, int], tuple[float, ...]] = {}
    for way_id in way_ids:
        feature = features.get(way_id)
        if feature is None:
            raise RoadSurfacePatchError(f"required severe-corridor way {way_id} is missing")
        for part_index, raw_part in enumerate(feature.get("centerlinePartsXZ", [])):
            part = [tuple(map(float, point)) for point in raw_part]
            stations, length = _road_part_stations(part, 1.0)
            if way_id == 30480989 and part_index == 0:
                stations = sorted(set(stations) | {396.0108, 409.2610})
            stations = sorted(
                set(stations)
                | {
                    station
                    for station in fallback_stations.get((way_id, part_index), [])
                    if 0.0 <= station <= length
                }
            )
            if max(np.diff(stations), default=0.0) > 1.0 + 1e-9:
                raise RoadSurfacePatchError(
                    f"mandatory corridor stations exceed 1 m for way {way_id} part {part_index}"
                )
            union[(way_id, part_index)] = tuple(float(station) for station in stations)
    return union


def _section_lateral_metrics(
    values: np.ndarray,
    sample_spacing_m: float,
    total_width_m: float,
) -> dict[str, float]:
    """Measure full-width span and the worst adjacent-sample slope."""
    differences = np.diff(np.asarray(values, dtype=np.float64))
    return {
        "fullWidthSpanM": float(np.ptp(values)),
        "endpointCrossfallPercent": float(abs(values[-1] - values[0]) / total_width_m * 100),
        "maximumLocalLateralSlopeMPerM": float(np.max(np.abs(differences)) / sample_spacing_m),
    }


def composite_local_and_corridor_report(
    surface: CompositeSurface,
    *,
    fail_closed: bool = True,
) -> dict[str, Any]:
    """Measure the registered local patch, all severe corridors and seven road profiles."""
    inputs = surface.inputs
    station_union = mandatory_corridor_station_union(inputs, require_accepted_fallback_qa=True)
    features = {
        int(feature.get("source", {}).get("osmId", -1)): feature
        for feature in inputs.road_payload.get("features", [])
        if isinstance(feature, dict)
    }
    target = features.get(TEIGNMOUTH_WAY_ID)
    if target is None:
        raise RoadSurfacePatchError("Teignmouth source feature is missing from pinned roads")
    target_part = [
        tuple(map(float, point)) for point in target["centerlinePartsXZ"][TEIGNMOUTH_PART_INDEX]
    ]
    target_cumulative = [0.0]
    for first, second in zip(target_part, target_part[1:], strict=False):
        target_cumulative.append(target_cumulative[-1] + math.dist(first, second))
    target_stations, _target_length = _road_part_stations(target_part, 1.0)
    target_stations = sorted(
        set(
            station
            for station in target_stations
            if TEIGNMOUTH_STATION_START_M <= station <= TEIGNMOUTH_STATION_END_M
        )
        | {
            station
            for station in target_cumulative
            if TEIGNMOUTH_STATION_START_M <= station <= TEIGNMOUTH_STATION_END_M
        }
        | {TEIGNMOUTH_STATION_START_M, TEIGNMOUTH_STATION_END_M, 148.15104603556912}
    )
    if max(np.diff(target_stations), default=0.0) > 1.0 + 1e-9:
        raise RoadSurfacePatchError("Teignmouth local samples exceed the 1 m station gate")
    target_offsets = np.arange(-3.0, 3.0 + PATCH_LATERAL_SAMPLE_M / 2, PATCH_LATERAL_SAMPLE_M)
    target_sections = []
    local_grade_deltas = []
    target_baseline_centers = []
    target_preview_centers = []
    for station in target_stations:
        (center_x, center_z), tangent = _line_point_tangent(target_part, station)
        normal_x, normal_z = -tangent[1], tangent[0]
        sample_x = center_x + normal_x * target_offsets
        sample_z = center_z + normal_z * target_offsets
        baseline_values = _sample_grid_many(inputs.baseline, sample_x, sample_z, inputs.spacing_m)
        preview_values, _owners = surface.sample_many(sample_x, sample_z)
        baseline_metrics = _section_lateral_metrics(baseline_values, PATCH_LATERAL_SAMPLE_M, 6.0)
        preview_metrics = _section_lateral_metrics(preview_values, PATCH_LATERAL_SAMPLE_M, 6.0)
        centerline_base = _sample_grid(inputs.baseline, center_x, center_z, inputs.spacing_m)
        centerline_preview, _center_owner = surface.sample(center_x, center_z)
        target_baseline_centers.append(centerline_base)
        target_preview_centers.append(centerline_preview)
        target_sections.append(
            {
                "stationM": float(station),
                "baselineCrossfallPercent": baseline_metrics["endpointCrossfallPercent"],
                "candidateCrossfallPercent": preview_metrics["endpointCrossfallPercent"],
                "baselineFullWidthSpanM": baseline_metrics["fullWidthSpanM"],
                "candidateFullWidthSpanM": preview_metrics["fullWidthSpanM"],
                "baselineMaximumLocalLateralSlopeMPerM": baseline_metrics[
                    "maximumLocalLateralSlopeMPerM"
                ],
                "candidateMaximumLocalLateralSlopeMPerM": preview_metrics[
                    "maximumLocalLateralSlopeMPerM"
                ],
                "centerlineDeviationM": float(centerline_preview - centerline_base),
            }
        )
    for index in range(len(target_stations) - 1):
        station_delta = target_stations[index + 1] - target_stations[index]
        baseline_grade = (
            (target_baseline_centers[index + 1] - target_baseline_centers[index])
            / station_delta
            * 100
        )
        candidate_grade = (
            (target_preview_centers[index + 1] - target_preview_centers[index])
            / station_delta
            * 100
        )
        local_grade_deltas.append(candidate_grade - baseline_grade)
    local_report = {
        "wayId": TEIGNMOUTH_WAY_ID,
        "partIndex": TEIGNMOUTH_PART_INDEX,
        "stationStartM": TEIGNMOUTH_STATION_START_M,
        "stationEndM": TEIGNMOUTH_STATION_END_M,
        "stationCount": len(target_stations),
        "maximumStationSpacingM": float(max(np.diff(target_stations), default=0.0)),
        "lateralSampleSpacingM": PATCH_LATERAL_SAMPLE_M,
        "lateralSampleCount": int(target_offsets.size),
        "maximumCrossfallPercent": max(
            item["candidateCrossfallPercent"] for item in target_sections
        ),
        "maximumLocalLateralSlopeMPerM": max(
            item["candidateMaximumLocalLateralSlopeMPerM"] for item in target_sections
        ),
        "maximumLocalLateralSlopePercent": max(
            item["candidateMaximumLocalLateralSlopeMPerM"] for item in target_sections
        )
        * 100.0,
        "maximumEndpointSpanM": max(item["candidateFullWidthSpanM"] for item in target_sections),
        "maximumAbsoluteCenterlineDeviationM": max(
            abs(item["centerlineDeviationM"]) for item in target_sections
        ),
        "maximumAbsoluteSignedGradeChangePercentagePoints": max(
            (abs(value) for value in local_grade_deltas), default=0.0
        ),
        "sections": target_sections,
    }
    local_report["passes"] = bool(
        local_report["maximumCrossfallPercent"] <= 5.0
        and local_report["maximumLocalLateralSlopePercent"] <= 5.0
        and local_report["maximumEndpointSpanM"] <= 0.30
        and local_report["maximumAbsoluteCenterlineDeviationM"] <= 0.10
        and local_report["maximumAbsoluteSignedGradeChangePercentagePoints"] <= 2.0
    )

    corridor_reports = []
    severe_failures = []
    corridor_failures = []
    severe_total = 0
    severe_counts_by_way: dict[str, int] = {}
    for way_id in SEVERE_CORRIDOR_WAY_IDS:
        feature = features.get(way_id)
        if feature is None:
            raise RoadSurfacePatchError(f"required severe-corridor way {way_id} is missing")
        width = float(feature["estimatedWidthM"])
        lateral_count = math.ceil(width / 0.25)
        lateral_step = width / lateral_count
        offsets = np.linspace(-width / 2, width / 2, lateral_count + 1)
        part_reports = []
        way_base: list[float] = []
        way_candidate: list[float] = []
        for part_index, raw_part in enumerate(feature["centerlinePartsXZ"]):
            part = [tuple(map(float, point)) for point in raw_part]
            stations = list(station_union[(way_id, part_index)])
            _uniform_stations, part_length = _road_part_stations(part, 1.0)
            station_records = []
            for station in stations:
                (center_x, center_z), tangent = _line_point_tangent(part, station)
                normal_x, normal_z = -tangent[1], tangent[0]
                sample_x = center_x + normal_x * offsets
                sample_z = center_z + normal_z * offsets
                baseline_values = _sample_grid_many(
                    inputs.baseline, sample_x, sample_z, inputs.spacing_m
                )
                candidate_values, _owners = surface.sample_many(sample_x, sample_z)
                baseline_crossfall = abs(baseline_values[-1] - baseline_values[0]) / width * 100
                candidate_crossfall = abs(candidate_values[-1] - candidate_values[0]) / width * 100
                changed_count = int(
                    np.count_nonzero(np.abs(candidate_values - baseline_values) > 0.01)
                )
                surface_class = (
                    "untreated"
                    if changed_count == 0
                    else "treated"
                    if changed_count == len(offsets)
                    else "transition"
                )
                record = {
                    "stationM": station,
                    "baselineCrossfallPercent": baseline_crossfall,
                    "candidateCrossfallPercent": candidate_crossfall,
                    "baselineMaximumLocalLateralSlopeMPerM": float(
                        np.max(np.abs(np.diff(baseline_values))) / lateral_step
                    ),
                    "candidateMaximumLocalLateralSlopeMPerM": float(
                        np.max(np.abs(np.diff(candidate_values))) / lateral_step
                    ),
                    "baselineFullWidthSpanM": float(np.ptp(baseline_values)),
                    "candidateFullWidthSpanM": float(np.ptp(candidate_values)),
                    "surfaceClass": surface_class,
                }
                station_records.append(record)
                way_base.append(baseline_crossfall)
                way_candidate.append(candidate_crossfall)
                if (
                    baseline_crossfall >= 10
                    and candidate_crossfall > baseline_crossfall * 0.5 + 1e-8
                ):
                    severe_failures.append({"wayId": way_id, "partIndex": part_index, **record})
            class_lengths = {"treated": 0.0, "transition": 0.0, "untreated": 0.0}
            boundaries = (
                [0.0]
                + [
                    (first + second) / 2
                    for first, second in zip(stations, stations[1:], strict=False)
                ]
                + [part_length]
            )
            for index, record in enumerate(station_records):
                class_lengths[record["surfaceClass"]] += max(
                    0.0, boundaries[index + 1] - boundaries[index]
                )
            base_values = np.asarray(
                [record["baselineCrossfallPercent"] for record in station_records]
            )
            candidate_values = np.asarray(
                [record["candidateCrossfallPercent"] for record in station_records]
            )
            severe_records = [
                record for record in station_records if record["baselineCrossfallPercent"] >= 10
            ]
            severe_total += len(severe_records)
            baseline_worst = max(station_records, key=lambda item: item["baselineCrossfallPercent"])
            if baseline_worst["surfaceClass"] == "untreated":
                corridor_failures.append(
                    {
                        "wayId": way_id,
                        "partIndex": part_index,
                        "reason": "baseline-worst station untreated",
                        "station": baseline_worst,
                    }
                )
            part_reports.append(
                {
                    "partIndex": part_index,
                    "lengthM": part_length,
                    "sampleCount": len(station_records),
                    "maximumStationSpacingM": float(max(np.diff(stations), default=0.0)),
                    "severeBaselineStationCount": len(severe_records),
                    "severeStationFailureCount": sum(
                        record["baselineCrossfallPercent"] >= 10
                        and record["candidateCrossfallPercent"]
                        > record["baselineCrossfallPercent"] * 0.5 + 1e-8
                        for record in station_records
                    ),
                    "baselineWorstStation": baseline_worst,
                    "treatmentLengthsM": class_lengths,
                    "baselineCrossfallPercent": {
                        "median": float(np.median(base_values)),
                        "p90": float(np.percentile(base_values, 90)),
                        "p95": float(np.percentile(base_values, 95)),
                        "maximum": float(np.max(base_values)),
                    },
                    "candidateCrossfallPercent": {
                        "median": float(np.median(candidate_values)),
                        "p90": float(np.percentile(candidate_values, 90)),
                        "p95": float(np.percentile(candidate_values, 95)),
                        "maximum": float(np.max(candidate_values)),
                    },
                }
            )
        base_values = np.asarray(way_base)
        candidate_values = np.asarray(way_candidate)
        severe_counts_by_way[str(way_id)] = int(np.count_nonzero(base_values >= 10.0))
        summary = {
            "wayId": way_id,
            "name": feature.get("sourceTags", {}).get("name"),
            "parts": part_reports,
            "baselineCrossfallPercent": {
                "median": float(np.median(base_values)),
                "p90": float(np.percentile(base_values, 90)),
                "p95": float(np.percentile(base_values, 95)),
                "maximum": float(np.max(base_values)),
            },
            "candidateCrossfallPercent": {
                "median": float(np.median(candidate_values)),
                "p90": float(np.percentile(candidate_values, 90)),
                "p95": float(np.percentile(candidate_values, 95)),
                "maximum": float(np.max(candidate_values)),
            },
        }
        if any(
            summary["candidateCrossfallPercent"][key] >= summary["baselineCrossfallPercent"][key]
            for key in ("maximum", "p95")
        ):
            corridor_failures.append({"wayId": way_id, "reason": "maximum/p95 did not decrease"})
        corridor_reports.append(summary)

    parkfield = features.get(30480989)
    if parkfield is None:
        raise RoadSurfacePatchError("Parkfield registered control feature is missing")
    parkfield_part = [tuple(map(float, point)) for point in parkfield["centerlinePartsXZ"][0]]
    parkfield_width = float(parkfield["estimatedWidthM"])
    parkfield_offsets = np.linspace(
        -parkfield_width / 2, parkfield_width / 2, math.ceil(parkfield_width / 0.25) + 1
    )
    parkfield_controls = []
    for station in (396.0108, 409.2610):
        (center_x, center_z), tangent = _line_point_tangent(parkfield_part, station)
        normal_x, normal_z = -tangent[1], tangent[0]
        xs, zs = center_x + normal_x * parkfield_offsets, center_z + normal_z * parkfield_offsets
        baseline_values = _sample_grid_many(inputs.baseline, xs, zs, inputs.spacing_m)
        candidate_values, _owners = surface.sample_many(xs, zs)
        baseline_metrics = _section_lateral_metrics(
            baseline_values, parkfield_width / (len(parkfield_offsets) - 1), parkfield_width
        )
        candidate_metrics = _section_lateral_metrics(
            candidate_values, parkfield_width / (len(parkfield_offsets) - 1), parkfield_width
        )
        center_baseline = _sample_grid(inputs.baseline, center_x, center_z, inputs.spacing_m)
        center_candidate, _owner = surface.sample(center_x, center_z)
        record = {
            "stationM": station,
            "sampleSpacingM": parkfield_width / (len(parkfield_offsets) - 1),
            "sampleCount": len(parkfield_offsets),
            "baselineCrossfallPercent": baseline_metrics["endpointCrossfallPercent"],
            "candidateCrossfallPercent": candidate_metrics["endpointCrossfallPercent"],
            "baselineMaximumLocalLateralSlopeMPerM": baseline_metrics[
                "maximumLocalLateralSlopeMPerM"
            ],
            "candidateMaximumLocalLateralSlopeMPerM": candidate_metrics[
                "maximumLocalLateralSlopeMPerM"
            ],
            "baselineFullWidthSpanM": baseline_metrics["fullWidthSpanM"],
            "candidateFullWidthSpanM": candidate_metrics["fullWidthSpanM"],
            "centerlineDeviationM": center_candidate - center_baseline,
        }
        record["passes"] = bool(
            record["candidateCrossfallPercent"] <= 5.0
            and record["candidateFullWidthSpanM"] <= 0.30
            and abs(record["centerlineDeviationM"]) <= 0.10
        )
        parkfield_controls.append(record)

    longitudinal_reports = []
    longitudinal_failures = []
    for way_id in PROFILE_WAY_IDS:
        feature = features.get(way_id)
        if feature is None:
            raise RoadSurfacePatchError(f"longitudinal profile way {way_id} is missing")
        maximum_height_delta = 0.0
        maximum_grade_delta = 0.0
        parts = []
        for part_index, raw_part in enumerate(feature["centerlinePartsXZ"]):
            part = [tuple(map(float, point)) for point in raw_part]
            stations, length = _road_part_stations(part, 5.0)
            if not stations:
                continue
            positions = [_line_point_tangent(part, station)[0] for station in stations]
            base_values = _sample_grid_many(
                inputs.baseline,
                np.asarray([point[0] for point in positions]),
                np.asarray([point[1] for point in positions]),
                inputs.spacing_m,
            )
            candidate_values, _owners = surface.sample_many(
                np.asarray([point[0] for point in positions]),
                np.asarray([point[1] for point in positions]),
            )
            height_delta = candidate_values - base_values
            base_grades = np.diff(base_values) / np.diff(stations) * 100
            candidate_grades = np.diff(candidate_values) / np.diff(stations) * 100
            grade_delta = candidate_grades - base_grades
            part_height_max = float(np.max(np.abs(height_delta)))
            part_grade_max = float(np.max(np.abs(grade_delta))) if grade_delta.size else 0.0
            maximum_height_delta = max(maximum_height_delta, part_height_max)
            maximum_grade_delta = max(maximum_grade_delta, part_grade_max)
            parts.append(
                {
                    "partIndex": part_index,
                    "lengthM": length,
                    "sampleCount": len(stations),
                    "maximumStationSpacingM": float(max(np.diff(stations), default=0.0)),
                    "signedHeightChangeRangeM": [
                        float(np.min(height_delta)),
                        float(np.max(height_delta)),
                    ],
                    "maximumAbsoluteHeightChangeM": part_height_max,
                    "signedGradeChangeRangePercentagePoints": [
                        float(np.min(grade_delta)) if grade_delta.size else 0.0,
                        float(np.max(grade_delta)) if grade_delta.size else 0.0,
                    ],
                    "maximumAbsoluteGradeChangePercentagePoints": part_grade_max,
                }
            )
        if maximum_height_delta > 0.10 or maximum_grade_delta > 2.0:
            longitudinal_failures.append(
                {
                    "wayId": way_id,
                    "maximumAbsoluteHeightChangeM": maximum_height_delta,
                    "maximumAbsoluteGradeChangePercentagePoints": maximum_grade_delta,
                }
            )
        longitudinal_reports.append(
            {
                "wayId": way_id,
                "maximumAbsoluteHeightChangeM": maximum_height_delta,
                "maximumAbsoluteGradeChangePercentagePoints": maximum_grade_delta,
                "parts": parts,
            }
        )
    corridor_failure_count = len(severe_failures) + len(corridor_failures)
    mandatory_union_counts_by_way = {
        str(way_id): sum(
            len(stations)
            for (station_way_id, _part_index), stations in station_union.items()
            if station_way_id == way_id
        )
        for way_id in SEVERE_CORRIDOR_WAY_IDS
    }
    report = {
        "teignmouthLocal": local_report,
        "severeCorridors": corridor_reports,
        "severeBaselineStationCount": severe_total,
        "severeBaselineStationCountsByWay": severe_counts_by_way,
        "mandatoryStationUnionCountsByWay": mandatory_union_counts_by_way,
        "severeStationFailureCount": len(severe_failures),
        "severeStationFailures": severe_failures,
        "corridorSummaryFailures": corridor_failures,
        "parkfieldControls": parkfield_controls,
        "sevenWayLongitudinalProfiles": longitudinal_reports,
        "longitudinalFailures": longitudinal_failures,
        "passes": bool(
            local_report["passes"]
            and severe_total == 439
            and not severe_failures
            and not corridor_failures
            and len(parkfield_controls) == 2
            and all(item["passes"] for item in parkfield_controls)
            and not longitudinal_failures
        ),
        "corridorFailureCount": corridor_failure_count,
    }
    if fail_closed and not report["passes"]:
        raise RoadSurfacePatchError(
            "composite local/corridor/longitudinal gates failed: "
            f"local={local_report}, severeCount={severe_total}, "
            f"severeFailures={len(severe_failures)}, corridorFailures={len(corridor_failures)}, "
            f"parkfield={parkfield_controls}, longitudinalFailures={longitudinal_failures}"
        )
    return report


def _clip_convex_polygon(
    subject: list[tuple[float, float]], clip: np.ndarray
) -> list[tuple[float, float]]:
    """Sutherland-Hodgman intersection of two convex XZ polygons."""
    signed_area = math.fsum(
        first[0] * second[1] - second[0] * first[1]
        for first, second in zip(clip, np.roll(clip, -1, axis=0), strict=True)
    )
    orientation = 1.0 if signed_area > 0 else -1.0
    output = subject
    for edge_start, edge_end in zip(clip, np.roll(clip, -1, axis=0), strict=True):
        input_points = output
        output = []
        if not input_points:
            break

        def side(
            point: tuple[float, float],
            edge_start: np.ndarray = edge_start,
            edge_end: np.ndarray = edge_end,
        ) -> float:
            return orientation * (
                (edge_end[0] - edge_start[0]) * (point[1] - edge_start[1])
                - (edge_end[1] - edge_start[1]) * (point[0] - edge_start[0])
            )

        previous = input_points[-1]
        previous_side = side(previous)
        for current in input_points:
            current_side = side(current)
            previous_inside, current_inside = previous_side >= -1e-12, current_side >= -1e-12
            if previous_inside != current_inside:
                denominator = previous_side - current_side
                fraction = 0.0 if denominator == 0.0 else previous_side / denominator
                output.append(
                    (
                        previous[0] + fraction * (current[0] - previous[0]),
                        previous[1] + fraction * (current[1] - previous[1]),
                    )
                )
            if current_inside:
                output.append(current)
            previous, previous_side = current, current_side
        compact: list[tuple[float, float]] = []
        for point in output:
            if not compact or math.dist(point, compact[-1]) > 1e-10:
                compact.append(point)
        if len(compact) > 1 and math.dist(compact[0], compact[-1]) <= 1e-10:
            compact.pop()
        output = compact
    return output


def _area_xz(points_xz: list[tuple[float, float]] | np.ndarray) -> float:
    return (
        abs(
            math.fsum(
                float(first[0]) * float(second[1]) - float(second[0]) * float(first[1])
                for first, second in zip(points_xz, np.roll(points_xz, -1, axis=0), strict=True)
            )
        )
        * 0.5
    )


def reclip_affected_road_batches(
    surface: CompositeSurface,
) -> dict[str, Any]:
    """Clip each affected source road/path face to its exact replacement patch faces."""
    batches = surface.inputs.road_payload.get("surfaceBatches")
    if not isinstance(batches, dict) or set(batches) != {"vehicular", "cycleway", "path"}:
        raise RoadSurfacePatchError("pinned road package has malformed display surface batches")
    mesh = surface.mesh
    output: dict[str, Any] = {}
    replacement_face_count = 0
    replacement_vertex_count = 0
    all_replaced_area = 0.0
    all_clipped_area = 0.0
    all_float32_area = 0.0
    total_omitted_area = 0.0
    maximum_float32_nudge_m = 0.0
    quantized_point_adjustment_count = 0
    edge_faces, vertex_faces = _triangle_vertex_adjacency(mesh)
    for group_name in ("vehicular", "cycleway", "path"):
        batch = batches[group_name]
        vertices = np.asarray(batch["verticesXZ"], dtype=np.float64)
        faces = np.asarray(batch["indices"], dtype=np.int64).reshape((-1, 3))
        owners = np.asarray(batch["terrainTriangles"], dtype=np.int64).reshape((-1, 3))
        if faces.ndim != 2 or faces.shape[1] != 3 or owners.shape != faces.shape:
            raise RoadSurfacePatchError(f"road batch {group_name} has malformed face ownership")
        output_vertices: list[tuple[float, float]] = []
        output_faces: list[tuple[int, int, int]] = []
        output_owners: list[int] = []
        vertex_map: dict[bytes, int] = {}
        affected_source_faces = 0
        source_area = 0.0
        exact_clipped_area = 0.0
        float32_area = 0.0
        omitted_area = 0.0
        drape_error = 0.0
        maximum_owner_weight_violation = 0.0
        maximum_float32_face_coverage_error = 0.0
        group_quantization_adjustment_count = 0
        group_maximum_float32_nudge_m = 0.0
        for face_index, face in enumerate(faces):
            row, column, half = (int(value) for value in owners[face_index])
            in_patch = (
                mesh.bounds.first_row <= row < mesh.bounds.last_row
                and mesh.bounds.first_column <= column < mesh.bounds.last_column
            )
            if not in_patch:
                continue
            affected_source_faces += 1
            source_triangle = [tuple(map(float, vertices[index])) for index in face]
            face_area = _area_xz(source_triangle)
            source_area += face_area
            source_face_clipped_area = 0.0
            source_face_float32_area = 0.0
            for patch_triangle_id in mesh.cell_half_triangles[(row, column, half)]:
                patch_indices = mesh.triangles[patch_triangle_id].astype(np.int64)
                patch_xz = mesh.vertices_xz[patch_indices].astype(np.float64)
                clipped = _clip_convex_polygon(source_triangle, patch_xz)
                if len(clipped) < 3:
                    continue
                polygon_area = _area_xz(clipped)
                if polygon_area <= 1e-14:
                    continue
                exact_clipped_area += polygon_area
                source_face_clipped_area += polygon_area
                root = clipped[0]
                for corner in range(1, len(clipped) - 1):
                    candidate_face = (root, clipped[corner], clipped[corner + 1])
                    raw_area = _area_xz(candidate_face)
                    if raw_area <= 1e-14:
                        continue
                    quantized = []
                    shared_owner_sets = []
                    for point in candidate_face:
                        point_tuple = (float(point[0]), float(point[1]))
                        shared_owners = _shared_float32_owners(
                            mesh,
                            patch_triangle_id,
                            point_tuple,
                            edge_faces,
                            vertex_faces,
                        )
                        quantized_point, owner_violation = _quantize_road_point_for_owners(
                            mesh, point_tuple, shared_owners
                        )
                        maximum_owner_weight_violation = max(
                            maximum_owner_weight_violation, owner_violation
                        )
                        direct_point = (
                            float(np.float32(point_tuple[0])),
                            float(np.float32(point_tuple[1])),
                        )
                        if quantized_point != direct_point:
                            quantized_point_adjustment_count += 1
                            group_quantization_adjustment_count += 1
                        maximum_float32_nudge_m = max(
                            maximum_float32_nudge_m,
                            math.dist(point_tuple, quantized_point),
                        )
                        group_maximum_float32_nudge_m = max(
                            group_maximum_float32_nudge_m,
                            math.dist(point_tuple, quantized_point),
                        )
                        quantized.append(quantized_point)
                        shared_owner_sets.append(shared_owners)
                    quantized_area = _area_xz(quantized)
                    if quantized_area <= 0:
                        omitted_area += raw_area
                        continue
                    ids = []
                    for point in quantized:
                        key = np.asarray(point, dtype="<f4").tobytes()
                        vertex_id = vertex_map.get(key)
                        if vertex_id is None:
                            vertex_id = len(output_vertices)
                            vertex_map[key] = vertex_id
                            output_vertices.append(point)
                        ids.append(vertex_id)
                    if len(set(ids)) != 3:
                        omitted_area += raw_area
                        continue
                    first, second, third = (np.asarray(output_vertices[index]) for index in ids)
                    cross = (second[0] - first[0]) * (third[1] - first[1]) - (
                        second[1] - first[1]
                    ) * (third[0] - first[0])
                    if not math.isfinite(float(cross)) or abs(cross) <= 0.0:
                        omitted_area += raw_area
                        continue
                    if cross > 0:
                        ids[1], ids[2] = ids[2], ids[1]
                        shared_owner_sets[1], shared_owner_sets[2] = (
                            shared_owner_sets[2],
                            shared_owner_sets[1],
                        )
                    clipped_area_face = _area_xz([output_vertices[index] for index in ids])
                    float32_area += clipped_area_face
                    source_face_float32_area += clipped_area_face
                    # Verify Float32 XZ is still contained by the exact owner triangle.
                    for vertex_id, shared_owners in zip(ids, shared_owner_sets, strict=True):
                        x, z = output_vertices[vertex_id]
                        for shared_owner in shared_owners:
                            shared_ids = mesh.triangles[shared_owner].astype(np.int64)
                            shared_xz = mesh.vertices_xz[shared_ids].astype(np.float64)
                            owner_violation = _barycentric_violation(
                                _triangle_barycentric_weights(shared_xz, x, z)
                            )
                            maximum_owner_weight_violation = max(
                                maximum_owner_weight_violation, owner_violation
                            )
                            if owner_violation > 1e-6:
                                raise RoadSurfacePatchError(
                                    "Float32 road vertex is outside a recorded shared patch owner "
                                    f"{shared_owner} by barycentric amount {owner_violation:.9g}"
                                )
                        owner_height = _triangle_linear_height(
                            patch_xz,
                            surface.patch_heights[patch_indices].astype(np.float64),
                            x,
                            z,
                        )
                        sampled_height, _sampled_owner = surface.sample(x, z)
                        if abs(sampled_height - owner_height) > 0.001:
                            raise RoadSurfacePatchError(
                                "Float32 road vertex left its owning patch plane "
                                f"{patch_triangle_id}"
                            )
                    output_faces.append(tuple(ids))
                    output_owners.append(int(patch_triangle_id))
                    replacement_face_count += 1
            face_coverage_error = abs(source_face_clipped_area - source_face_float32_area)
            maximum_float32_face_coverage_error = max(
                maximum_float32_face_coverage_error, face_coverage_error
            )
            if abs(face_area - source_face_clipped_area) > PATCH_ROAD_AREA_ABSOLUTE_TOLERANCE_M2:
                raise RoadSurfacePatchError(
                    f"road {group_name} face {face_index} reclip area differs by "
                    f"{face_area - source_face_clipped_area:.9g} m²"
                )
            if face_coverage_error > PATCH_ROAD_FLOAT32_OMITTED_AREA_LIMIT_M2:
                raise RoadSurfacePatchError(
                    f"road {group_name} face {face_index} Float32 footprint coverage differs by "
                    f"{face_coverage_error:.9g} m²"
                )
        area_difference = abs(source_area - exact_clipped_area)
        replacement_vertex_count += len(output_vertices)
        all_replaced_area += source_area
        all_clipped_area += exact_clipped_area
        all_float32_area += float32_area
        total_omitted_area += omitted_area
        if area_difference > PATCH_ROAD_AREA_ABSOLUTE_TOLERANCE_M2:
            raise RoadSurfacePatchError(
                f"road {group_name} horizontal coverage changed by {area_difference:.9g} m²"
            )
        float32_area_drift = float32_area - exact_clipped_area
        float32_coverage_error = abs(source_area - float32_area)
        if abs(float32_area_drift) > PATCH_ROAD_FLOAT32_OMITTED_AREA_LIMIT_M2:
            raise RoadSurfacePatchError(
                f"road {group_name} aggregate Float32 area drift exceeds the existing "
                f"{PATCH_ROAD_FLOAT32_OMITTED_AREA_LIMIT_M2:g} m² Float32 area limit: "
                f"{float32_area_drift:.9g} m²"
            )
        if float32_coverage_error > PATCH_ROAD_FLOAT32_OMITTED_AREA_LIMIT_M2:
            raise RoadSurfacePatchError(
                f"road {group_name} post-Float32 footprint coverage differs by "
                f"{float32_coverage_error:.9g} m²"
            )
        if omitted_area > PATCH_ROAD_FLOAT32_OMITTED_AREA_LIMIT_M2:
            raise RoadSurfacePatchError(
                f"road {group_name} Float32 collapsed {omitted_area:.9g} m² of surface"
            )
        for face, owner_id in zip(output_faces, output_owners, strict=True):
            points_xz = [output_vertices[index] for index in face]
            if owner_id < 0 or owner_id >= len(mesh.triangles):
                raise RoadSurfacePatchError(
                    f"road {group_name} has an invalid patch triangle owner"
                )
            patch_ids = mesh.triangles[owner_id].astype(np.int64)
            owner_xz = mesh.vertices_xz[patch_ids].astype(np.float64)
            owner_y = surface.patch_heights[patch_ids].astype(np.float64)
            owner_heights = [_triangle_linear_height(owner_xz, owner_y, x, z) for x, z in points_xz]
            centroid_x = math.fsum(point[0] for point in points_xz) / 3
            centroid_z = math.fsum(point[1] for point in points_xz) / 3
            centroid_owner_y = _triangle_linear_height(owner_xz, owner_y, centroid_x, centroid_z)
            face_y = math.fsum(owner_heights) / 3
            drape_error = max(
                drape_error,
                abs(face_y - centroid_owner_y),
                *[
                    abs(surface.sample(x, z)[0] - owner_y)
                    for (x, z), owner_y in zip(points_xz, owner_heights, strict=True)
                ],
            )
        if drape_error > 0.001:
            raise RoadSurfacePatchError(
                f"road {group_name} exceeds the 1 mm composite drape limit: {drape_error:.9g} m"
            )
        output[group_name] = {
            "verticesXZ": output_vertices,
            "indices": output_faces,
            "terrainTriangles": output_owners,
            "sourceFaceCount": int(len(faces)),
            "affectedSourceFaceCount": affected_source_faces,
            "unaffectedSourceFaceCount": int(len(faces) - affected_source_faces),
            "replacementFaceCount": len(output_faces),
            "replacementVertexCount": len(output_vertices),
            "affectedSourceAreaM2": source_area,
            "replacementHorizontalAreaM2": exact_clipped_area,
            "float32HorizontalAreaM2": float32_area,
            "float32HorizontalAreaDriftM2": float32_area_drift,
            "float32FootprintCoverageErrorM2": float32_coverage_error,
            "maximumFloat32FaceCoverageErrorM2": maximum_float32_face_coverage_error,
            "float32CoverageAndAreaDriftLimitM2": PATCH_ROAD_FLOAT32_OMITTED_AREA_LIMIT_M2,
            "areaDifferenceM2": area_difference,
            "float32OmittedAreaM2": omitted_area,
            "maximumOwnerTriangleBarycentricViolation": maximum_owner_weight_violation,
            "ownerTriangleContainmentTolerance": 1e-6,
            "quantizationSafeSharedEdgeAdjustmentCount": group_quantization_adjustment_count,
            "maximumFloat32RoadPointNudgeM": group_maximum_float32_nudge_m,
            "maximumRoadDrapeErrorM": drape_error,
            "passes": area_difference <= PATCH_ROAD_AREA_ABSOLUTE_TOLERANCE_M2
            and abs(float32_area_drift) <= PATCH_ROAD_FLOAT32_OMITTED_AREA_LIMIT_M2
            and float32_coverage_error <= PATCH_ROAD_FLOAT32_OMITTED_AREA_LIMIT_M2
            and maximum_float32_face_coverage_error <= PATCH_ROAD_FLOAT32_OMITTED_AREA_LIMIT_M2
            and omitted_area <= PATCH_ROAD_FLOAT32_OMITTED_AREA_LIMIT_M2,
        }
    terrain_triangles = len(mesh.triangles)
    affected_source_face_count = sum(batch["affectedSourceFaceCount"] for batch in output.values())
    unaffected_source_face_count = sum(
        batch["unaffectedSourceFaceCount"] for batch in output.values()
    )
    replacement_source_terrain_triangles = mesh.bounds.coarse_cell_count * 2
    accepted_terrain_triangle_count = (surface.inputs.rows - 1) * (surface.inputs.columns - 1) * 2
    accepted_road_triangle_count = sum(len(batch["indices"]) for batch in batches.values())
    candidate_triangle_count = (
        accepted_terrain_triangle_count
        - replacement_source_terrain_triangles
        + terrain_triangles
        + unaffected_source_face_count
        + replacement_face_count
    )
    accepted_triangle_count = accepted_terrain_triangle_count + accepted_road_triangle_count
    net_triangle_increase = candidate_triangle_count - accepted_triangle_count
    total_delta_triangles = terrain_triangles + replacement_face_count
    total_delta_vertices = len(mesh.vertices_xz) + replacement_vertex_count
    total_runtime_bytes = (
        len(mesh.vertices_xz) * 12
        + len(mesh.triangles) * 12
        + sum(
            len(batch["verticesXZ"]) * 8
            + len(batch["indices"]) * 12
            + len(batch["terrainTriangles"]) * 4
            for batch in output.values()
        )
    )
    resource_report = {
        "terrainTriangles": terrain_triangles,
        "roadPathReplacementTriangles": replacement_face_count,
        "acceptedTriangles": accepted_triangle_count,
        "candidateTriangles": candidate_triangle_count,
        "netTriangleIncrease": net_triangle_increase,
        "removedTerrainTriangles": replacement_source_terrain_triangles,
        "replacedRoadPathTriangles": affected_source_face_count,
        "unaffectedRoadPathTriangles": unaffected_source_face_count,
        "incrementalTriangles": total_delta_triangles,
        "incrementalTriangleLimit": PATCH_MAX_TRIANGLES,
        "incrementalVertices": total_delta_vertices,
        "incrementalVertexLimit": PATCH_MAX_VERTICES,
        "candidateRuntimeAssetBytes": total_runtime_bytes,
        "candidateRuntimeAssetByteLimit": PATCH_MAX_ASSET_BYTES,
        "passes": bool(
            total_delta_triangles <= PATCH_MAX_TRIANGLES
            and total_delta_vertices <= PATCH_MAX_VERTICES
            and total_runtime_bytes <= PATCH_MAX_ASSET_BYTES
        ),
    }
    if not resource_report["passes"]:
        raise RoadSurfacePatchError(
            f"candidate geometry exceeds its strict resource ceiling: {resource_report}"
        )
    return {
        "groups": output,
        "affectedSourceAreaM2": all_replaced_area,
        "replacementHorizontalAreaM2": all_clipped_area,
        "float32HorizontalAreaM2": all_float32_area,
        "float32HorizontalAreaDriftM2": all_float32_area - all_clipped_area,
        "float32FootprintCoverageErrorM2": abs(all_replaced_area - all_float32_area),
        "quantizationSafeSharedEdgeAdjustmentCount": quantized_point_adjustment_count,
        "maximumFloat32RoadPointNudgeM": maximum_float32_nudge_m,
        "float32OmittedAreaM2": total_omitted_area,
        "resourceReport": resource_report,
        "passes": all(batch["passes"] for batch in output.values()) and resource_report["passes"],
    }


def composite_walk_clearance_report(
    surface: CompositeSurface,
    clipped_roads: dict[str, Any],
) -> dict[str, Any]:
    """Check the documented 1.70 m ground-following offset over the composite seam."""
    min_x = float(surface.mesh.vertices_xz[:, 0].min())
    max_x = float(surface.mesh.vertices_xz[:, 0].max())
    min_z = float(surface.mesh.vertices_xz[:, 1].min())
    max_z = float(surface.mesh.vertices_xz[:, 1].max())
    x_grid = np.arange(math.ceil(min_x), math.floor(max_x) + 1, 1.0, dtype=np.float64)
    z_grid = np.arange(math.ceil(min_z), math.floor(max_z) + 1, 1.0, dtype=np.float64)
    grid_x, grid_z = np.meshgrid(x_grid, z_grid)
    sample_parts = [np.column_stack((grid_x.ravel(), grid_z.ravel()))]
    boundary_edges = surface.mesh.vertices_xz[surface.mesh.boundary_edges].astype(np.float64)
    sample_parts.append(boundary_edges.mean(axis=1))
    road_vertex_count = 0
    for group in ("vehicular", "cycleway", "path"):
        group_data = clipped_roads.get("groups", {}).get(group, {})
        road_points = np.asarray(group_data.get("verticesXZ", []), dtype=np.float64).reshape(-1, 2)
        road_vertex_count += len(road_points)
        if len(road_points):
            sample_parts.append(road_points)
    samples = np.concatenate(sample_parts, axis=0)
    if not len(samples):
        raise RoadSurfacePatchError("composite walk-clearance report has no sample points")
    # Exact Float32 identity removes duplicate observations deterministically.
    unique_keys = np.asarray(samples, dtype="<f4").view("<u8").reshape(-1)
    _unique_keys, unique_indices = np.unique(unique_keys, return_index=True)
    unique_samples = samples[np.sort(unique_indices)]
    ground, owners = surface.sample_many(unique_samples[:, 0], unique_samples[:, 1])
    eye_height = ground + PATCH_CLEARANCE_M
    pavement_relative_clearance = eye_height - (ground + PATCH_ROAD_SURFACE_OFFSET_M)
    finite = bool(
        np.isfinite(ground).all()
        and np.isfinite(eye_height).all()
        and np.isfinite(pavement_relative_clearance).all()
    )
    minimum_ground_clearance = float(np.min(eye_height - ground))
    maximum_ground_clearance = float(np.max(eye_height - ground))
    minimum_pavement_clearance = float(np.min(pavement_relative_clearance))
    maximum_pavement_clearance = float(np.max(pavement_relative_clearance))
    minimum_limit = PATCH_CLEARANCE_M - PATCH_CLEARANCE_TOLERANCE_M
    maximum_limit = PATCH_CLEARANCE_M + PATCH_CLEARANCE_TOLERANCE_M
    display_clearance_passes = bool(
        finite
        and minimum_ground_clearance >= minimum_limit - PATCH_CLEARANCE_ARITHMETIC_TOLERANCE_M
        and maximum_ground_clearance <= maximum_limit + PATCH_CLEARANCE_ARITHMETIC_TOLERANCE_M
    )
    pavement_clearance_passes = bool(
        finite
        and PATCH_CLEARANCE_M - PATCH_ROAD_SURFACE_OFFSET_M
        <= minimum_pavement_clearance + PATCH_CLEARANCE_ARITHMETIC_TOLERANCE_M
        and maximum_pavement_clearance
        <= PATCH_CLEARANCE_M - PATCH_ROAD_SURFACE_OFFSET_M + PATCH_CLEARANCE_ARITHMETIC_TOLERANCE_M
    )
    road_coverage_available = bool(clipped_roads.get("passes") is True and road_vertex_count > 0)
    report = {
        "method": "displayed-terrain clearance from the shared composite surface",
        "runtimeBrowserVerified": False,
        "sampleCount": int(len(unique_samples)),
        "oneMetrePatchGridSampleCount": int(len(grid_x.ravel())),
        "fineCoarseSeamMidpointSampleCount": int(len(boundary_edges)),
        "reclippedRoadPathVertexCount": road_vertex_count,
        "roadClearanceCoverageAvailable": road_coverage_available,
        "roadClearanceCoverageUnavailableReason": (
            None
            if road_coverage_available
            else "road/path reclip failed or produced no Float32 display-road vertices"
        ),
        "displaySurfaceOwnerTriangleSampleCount": int(np.count_nonzero(owners >= 0)),
        "finite": finite,
        "groundClearanceRangeM": [minimum_ground_clearance, maximum_ground_clearance],
        "pavementRelativeClearanceRangeM": [
            minimum_pavement_clearance,
            maximum_pavement_clearance,
        ],
        "clearanceLimitM": [minimum_limit, maximum_limit],
        "clearanceArithmeticToleranceM": PATCH_CLEARANCE_ARITHMETIC_TOLERANCE_M,
        "displayedTerrainClearancePasses": display_clearance_passes,
        "pavementRelativeClearanceMethod": (
            "reported separately as eye height minus displayed terrain plus road offset"
        ),
        "pavementRelativeClearancePasses": pavement_clearance_passes,
        "passes": display_clearance_passes and road_coverage_available,
    }
    return report


def validate_offline_candidate(
    surface: CompositeSurface,
    influence: Polygon,
    constraints: list[dict[str, Any]],
    solver_report: dict[str, Any],
    accepted_preview_hashes: dict[str, str],
) -> dict[str, Any]:
    """Run every available offline gate against one retained Float32 witness."""
    candidate = surface.patch_heights
    candidate_bytes = candidate.astype("<f4", copy=False).tobytes(order="C")
    candidate_hash = hashlib.sha256(candidate_bytes).hexdigest()
    input_bindings_pass = bool(
        surface.inputs.release_id == CURRENT_RELEASE_ID
        and accepted_preview_hashes == ACCEPTED_PREVIEW_HASHES
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
            "acceptedPreviewHashesMatchPinned": accepted_preview_hashes == ACCEPTED_PREVIEW_HASHES,
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
        source_nodes = _sample_grid_many(
            surface.inputs.baseline,
            surface.mesh.vertices_xz[:, 0],
            surface.mesh.vertices_xz[:, 1],
            surface.inputs.spacing_m,
        )
        edges = np.asarray(sorted(surface.mesh.edge_counts), dtype=np.int64)
        edge_lengths = np.linalg.norm(
            surface.mesh.vertices_xz[edges[:, 0]] - surface.mesh.vertices_xz[edges[:, 1]],
            axis=1,
        )
        edge_source_deltas = np.abs(source_nodes[edges[:, 0]] - source_nodes[edges[:, 1]])
        edge_limits = edge_source_deltas + PATCH_MAX_ADDED_GRADIENT * edge_lengths
        fixed_mask = _fixed_patch_vertices(surface.mesh, influence)
        fixed_mask[np.unique(surface.mesh.boundary_edges)] = True
        reports["float32FinalValidation"] = _validate_quantized_phase_one(
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
    except (RoadSurfacePatchError, KeyError, TypeError, ValueError, IndexError) as exc:
        reports["float32FinalValidation"] = {"passes": False, "error": str(exc)}

    try:
        reports["topology"] = patch_topology_report(surface.mesh, surface.inputs.spacing_m)
    except RoadSurfacePatchError as exc:
        reports["topology"] = {"passes": False, "error": str(exc)}
    reports["sourceTriangleOwnership"] = patch_source_triangle_ownership_report(
        surface.mesh, surface.inputs
    )
    reports["earthworkOverlay"] = composite_earthwork_overlay_report(surface)
    try:
        reports["acceptedPlaneRefinement"] = verify_accepted_plane_refinement(
            surface.mesh,
            surface.accepted_heights,
            surface.inputs.spacing_m,
            influence=influence,
            fail_closed=False,
        )
    except RoadSurfacePatchError as exc:
        reports["acceptedPlaneRefinement"] = {"passes": False, "error": str(exc)}
    try:
        reports["compositeTerrain"] = verify_composite_terrain(
            surface, influence, fail_closed=False
        )
    except RoadSurfacePatchError as exc:
        reports["compositeTerrain"] = {"passes": False, "error": str(exc)}
    try:
        reports["localCorridorLongitudinal"] = composite_local_and_corridor_report(
            surface, fail_closed=False
        )
    except RoadSurfacePatchError as exc:
        reports["localCorridorLongitudinal"] = {"passes": False, "error": str(exc)}
    try:
        reports["completeBuildingFootprints"] = composite_building_base_report(
            surface, fail_closed=False
        )
    except RoadSurfacePatchError as exc:
        reports["completeBuildingFootprints"] = {"passes": False, "error": str(exc)}

    try:
        reclipped_roads = reclip_affected_road_batches(surface)
        reports["roadPathReclip"] = reclipped_roads
    except (RoadSurfacePatchError, KeyError, TypeError, ValueError, IndexError) as exc:
        reclipped_roads = {"groups": {}}
        reports["roadPathReclip"] = {"passes": False, "error": str(exc)}
    try:
        reports["walkClearance"] = composite_walk_clearance_report(surface, reclipped_roads)
    except (RoadSurfacePatchError, KeyError, TypeError, ValueError, IndexError) as exc:
        reports["walkClearance"] = {"passes": False, "error": str(exc)}

    gate_names = PATCH_OFFLINE_GATE_NAMES
    reports["passes"] = all(reports.get(name, {}).get("passes", False) for name in gate_names)
    reports["gateNames"] = list(gate_names)
    reports["candidateFloat32Sha256"] = candidate_hash
    reports["candidateFloat32ByteLength"] = len(candidate_bytes)
    reports["candidateFloat32Finite"] = bool(np.isfinite(candidate).all())
    return reports


def _serialized_geometry_for_surface(
    surface: CompositeSurface,
    clipped_roads: dict[str, Any],
) -> tuple[dict[str, bytes], dict[str, dict[str, int]]]:
    """Derive every serialized geometry buffer directly from the validated inputs."""
    mesh = surface.mesh
    candidate = surface.patch_heights.astype("<f4", copy=False)
    terrain_vertices = np.column_stack(
        (mesh.vertices_xz[:, 0], candidate.astype(np.float64), mesh.vertices_xz[:, 1])
    ).astype("<f4")
    terrain_indices = mesh.triangles.astype("<u4", copy=False)
    road_vertices_parts = []
    road_index_parts = []
    road_owner_parts = []
    road_ranges: dict[str, dict[str, int]] = {}
    vertex_offset = 0
    index_offset = 0
    face_offset = 0
    for group_name in ("vehicular", "cycleway", "path"):
        group = clipped_roads["groups"][group_name]
        vertices = np.asarray(group["verticesXZ"], dtype="<f4").reshape(-1, 2)
        indices = np.asarray(group["indices"], dtype="<u4").reshape(-1, 3)
        owners = np.asarray(group["terrainTriangles"], dtype="<u4").reshape(-1)
        if len(indices) != len(owners):
            raise RoadSurfacePatchError(f"candidate {group_name} owner count does not match faces")
        road_vertices_parts.append(vertices)
        road_index_parts.append(indices + np.uint32(vertex_offset))
        road_owner_parts.append(owners)
        road_ranges[group_name] = {
            "firstVertex": vertex_offset,
            "vertexCount": int(len(vertices)),
            "firstIndex": index_offset,
            "indexCount": int(indices.size),
            "firstTriangle": face_offset,
            "triangleCount": int(len(indices)),
            "surfaceOffsetM": PATCH_ROAD_SURFACE_OFFSET_M,
        }
        vertex_offset += len(vertices)
        index_offset += int(indices.size)
        face_offset += len(indices)
    road_vertices = (
        np.concatenate(road_vertices_parts, axis=0).astype("<f4", copy=False)
        if road_vertices_parts
        else np.empty((0, 2), dtype="<f4")
    )
    road_indices = (
        np.concatenate(road_index_parts, axis=0).astype("<u4", copy=False)
        if road_index_parts
        else np.empty((0, 3), dtype="<u4")
    )
    road_owners = (
        np.concatenate(road_owner_parts, axis=0).astype("<u4", copy=False)
        if road_owner_parts
        else np.empty(0, dtype="<u4")
    )
    return (
        {
            "terrain-vertices.f32": terrain_vertices.tobytes(order="C"),
            "terrain-indices.u32": terrain_indices.tobytes(order="C"),
            "road-vertices.f32": road_vertices.tobytes(order="C"),
            "road-indices.u32": road_indices.tobytes(order="C"),
            "road-terrain-triangles.u32": road_owners.tobytes(order="C"),
        },
        road_ranges,
    )


def assemble_candidate_patch_assets(
    surface: CompositeSurface,
    clipped_roads: dict[str, Any],
    offline_report: dict[str, Any],
) -> dict[str, bytes]:
    """Serialize a validated exact Float32 witness into deterministic candidate assets."""
    gate_names = offline_report.get("gateNames")
    reports_pass = isinstance(gate_names, list) and all(
        offline_report.get(name, {}).get("passes") is True for name in PATCH_OFFLINE_GATE_NAMES
    )
    if (
        not offline_report.get("passes")
        or gate_names != list(PATCH_OFFLINE_GATE_NAMES)
        or not reports_pass
    ):
        raise RoadSurfacePatchError(
            "refusing to assemble candidate assets before all offline gates pass"
        )
    if not clipped_roads.get("passes"):
        raise RoadSurfacePatchError(
            "refusing to assemble candidate assets from failed road reclipping"
        )
    mesh = surface.mesh
    candidate = surface.patch_heights.astype("<f4", copy=False)
    if hashlib.sha256(candidate.tobytes(order="C")).hexdigest() != offline_report.get(
        "candidateFloat32Sha256"
    ):
        raise RoadSurfacePatchError("candidate Float32 witness changed after offline validation")

    binary_assets, road_ranges = _serialized_geometry_for_surface(surface, clipped_roads)
    serialized_witness_sha256 = serialized_geometry_witness_sha256(
        binary_assets, offline_report["candidateFloat32Sha256"]
    )
    asset_records = {
        name: {
            "byteLength": len(payload),
            "elementCount": len(payload) // 4,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        for name, payload in sorted(binary_assets.items())
    }
    asset_records["qa.json"] = {"elementCount": 1}
    local = offline_report["localCorridorLongitudinal"]["teignmouthLocal"]
    terrain = offline_report["compositeTerrain"]
    building = offline_report["completeBuildingFootprints"]
    reclip = clipped_roads["resourceReport"]
    qa_summary = {
        "formatVersion": 1,
        "packageType": PATCH_PACKAGE_TYPE,
        "algorithmVersion": PATCH_ALGORITHM_VERSION,
        "candidateFloat32Sha256": offline_report["candidateFloat32Sha256"],
        "serializedGeometryWitnessSha256": serialized_witness_sha256,
        "acceptedPreviewHashes": ACCEPTED_PREVIEW_HASHES,
        "offlineGatePasses": True,
        "gates": {
            name: bool(offline_report[name]["passes"]) for name in offline_report["gateNames"]
        },
        "localTeignmouth": {
            key: local[key]
            for key in (
                "wayId",
                "partIndex",
                "stationStartM",
                "stationEndM",
                "stationCount",
                "maximumStationSpacingM",
                "lateralSampleSpacingM",
                "maximumLocalLateralSlopePercent",
                "maximumEndpointSpanM",
                "maximumAbsoluteCenterlineDeviationM",
                "maximumAbsoluteSignedGradeChangePercentagePoints",
                "passes",
            )
        },
        "terrain": {
            key: terrain[key]
            for key in (
                "maximumAbsoluteChangeFromSourceM",
                "maximumFillFromSourceM",
                "maximumCutFromSourceM",
                "maximumPositiveAddedGradientMPerM",
                "maximumOutsideInfluenceAcceptedPlaneDeviationM",
                "passes",
            )
        },
        "earthworkOverlay": offline_report["earthworkOverlay"],
        "buildings": {
            "buildingCount": building["buildingCount"],
            "completeFootprintsRecomputed": building["completeFootprintsRecomputed"],
            "baseDisplacementP95AbsoluteM": building["baseDisplacementP95AbsoluteM"],
            "baseDisplacementMaximumAbsoluteM": building["baseDisplacementMaximumAbsoluteM"],
            "nearbyBuilding208684847ChangeM": building["registeredBuildingChangesM"][
                "osm:way:208684847"
            ],
            "localReviewCount": len(building["localReviewOver0_50m"]),
            "passes": building["passes"],
        },
        "roadPath": {
            "affectedSourceAreaM2": clipped_roads["affectedSourceAreaM2"],
            "replacementHorizontalAreaM2": clipped_roads["replacementHorizontalAreaM2"],
            "float32HorizontalAreaDriftM2": clipped_roads["float32HorizontalAreaDriftM2"],
            "float32FootprintCoverageErrorM2": clipped_roads["float32FootprintCoverageErrorM2"],
            "float32OmittedAreaM2": clipped_roads["float32OmittedAreaM2"],
            "quantizationSafeSharedEdgeAdjustmentCount": clipped_roads[
                "quantizationSafeSharedEdgeAdjustmentCount"
            ],
            "resourceReport": reclip,
        },
    }
    qa_bytes = serialize_offline_report(qa_summary)
    asset_records["qa.json"].update(
        {"byteLength": len(qa_bytes), "sha256": hashlib.sha256(qa_bytes).hexdigest()}
    )
    row_runs = [
        [row, mesh.bounds.first_column, mesh.bounds.last_column]
        for row in range(mesh.bounds.first_row, mesh.bounds.last_row)
    ]
    manifest = {
        "packageType": PATCH_PACKAGE_TYPE,
        "formatVersion": PATCH_FORMAT_VERSION,
        "algorithmVersion": PATCH_ALGORITHM_VERSION,
        "source": {
            "releaseId": surface.inputs.release_id,
            "readySha256": _source_record_digest(surface.inputs.source_hashes["ready.json"]),
            "inventorySha256": surface.inputs.source_hashes["inventory.json"]["sha256"],
            "terrainManifestSha256": surface.inputs.manifest_sha256,
            "terrainHeightfieldSha256": surface.inputs.source_hashes["heightfield.f32"]["sha256"],
            "roadManifestSha256": surface.inputs.road_manifest_sha256,
            "roadPayloadSha256": surface.inputs.road_payload_sha256,
            "buildingPayloadSha256": surface.inputs.source_hashes["buildings/buildings.json"][
                "sha256"
            ],
        },
        "acceptedPreview": {"assetSha256": ACCEPTED_PREVIEW_HASHES},
        "coordinateFrame": {
            "unit": "metre",
            "localOriginEastingM": surface.inputs.origin_e_m,
            "localOriginNorthingM": surface.inputs.origin_n_m,
            "verticalOriginM": surface.inputs.origin_y_m,
            "northDirection": "negative local Z",
            "verticalOriginPolicy": PATCH_VERTICAL_ORIGIN_POLICY,
        },
        "baseGrid": {
            "spacingM": surface.inputs.spacing_m,
            "columns": surface.inputs.columns,
            "rows": surface.inputs.rows,
            "widthM": surface.inputs.width_m,
            "depthM": surface.inputs.depth_m,
        },
        "patch": {
            "firstCoarseRow": mesh.bounds.first_row,
            "firstCoarseColumn": mesh.bounds.first_column,
            "coarseRowCount": mesh.bounds.row_count,
            "coarseColumnCount": mesh.bounds.column_count,
            "coarseCellReplacementRuns": row_runs,
            "boundsM": patch_topology_report(mesh, surface.inputs.spacing_m)["patchBoundsM"],
            "fineInteriorSpacingM": PATCH_FINE_SPACING_M,
            "outerBoundarySpacingM": surface.inputs.spacing_m,
            "vertexCount": int(len(mesh.vertices_xz)),
            "triangleCount": int(len(mesh.triangles)),
            "seamPolicy": (
                "exact accepted Float32 coarse boundary vertices; shared surface sampling"
            ),
            "surfaceMeaning": (
                "0.5 m conforming triangulation of existing piecewise-planar accepted/source "
                "samples; no new measured elevation claim"
            ),
        },
        "selectedSourceWindow": {
            "wayId": TEIGNMOUTH_WAY_ID,
            "partIndex": TEIGNMOUTH_PART_INDEX,
            "stationStartM": TEIGNMOUTH_STATION_START_M,
            "stationEndM": TEIGNMOUTH_STATION_END_M,
            "configuredWidthM": 6.0,
            "maximumTransitionBeyondRibbonEdgeM": PATCH_MAX_TRANSITION_M,
        },
        "mesherAndSolver": {
            "mesherVersion": PATCH_ALGORITHM_VERSION,
            "solver": "bounded deterministic Dykstra projection with Float32 revalidation",
        },
        "roadGroups": road_ranges,
        "assets": asset_records,
        "limits": {
            "maximumManifestBytes": PATCH_MAX_MANIFEST_BYTES,
            "maximumQaBytes": PATCH_MAX_QA_BYTES,
            "maximumAllRuntimeAssetBytes": PATCH_MAX_ASSET_BYTES,
        },
    }
    manifest_bytes = (
        json.dumps(
            manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
        + b"\n"
    )
    if len(manifest_bytes) > PATCH_MAX_MANIFEST_BYTES:
        raise RoadSurfacePatchError(
            f"candidate manifest exceeds {PATCH_MAX_MANIFEST_BYTES} byte limit"
        )
    if len(qa_bytes) > PATCH_MAX_QA_BYTES:
        raise RoadSurfacePatchError(f"candidate QA exceeds {PATCH_MAX_QA_BYTES} byte limit")
    output = {**binary_assets, "manifest.json": manifest_bytes, "qa.json": qa_bytes}
    runtime_bytes = sum(len(payload) for payload in output.values())
    if runtime_bytes > PATCH_MAX_ASSET_BYTES:
        raise RoadSurfacePatchError(
            f"candidate runtime files exceed {PATCH_MAX_ASSET_BYTES} byte limit: {runtime_bytes}"
        )
    validation = validate_candidate_patch_assets(
        output, surface, offline_report["candidateFloat32Sha256"], clipped_roads
    )
    if not validation["passes"]:
        raise RoadSurfacePatchError(f"assembled candidate asset contract failed: {validation}")
    return output


def assemble_deterministic_candidate_assets(
    surface: CompositeSurface,
    clipped_roads: dict[str, Any],
    offline_report: dict[str, Any],
) -> tuple[dict[str, bytes], dict[str, bytes], dict[str, Any]]:
    """Independently assemble, validate and compare two complete candidate packages."""
    first = assemble_candidate_patch_assets(surface, clipped_roads, offline_report)
    second = assemble_candidate_patch_assets(surface, clipped_roads, offline_report)
    candidate_hash = offline_report.get("candidateFloat32Sha256")
    clipped_roads = offline_report.get("roadPathReclip", {})
    first_validation = validate_candidate_patch_assets(
        first, surface, candidate_hash, clipped_roads
    )
    second_validation = validate_candidate_patch_assets(
        second, surface, candidate_hash, clipped_roads
    )
    first_hashes = {
        name: hashlib.sha256(payload).hexdigest() for name, payload in sorted(first.items())
    }
    second_hashes = {
        name: hashlib.sha256(payload).hexdigest() for name, payload in sorted(second.items())
    }
    deterministic = bool(
        first is not second
        and first_validation["passes"]
        and second_validation["passes"]
        and first_hashes == second_hashes
        and first == second
    )
    report = {
        "passes": deterministic,
        "deterministicAssets": deterministic,
        "firstAssemblyValidation": first_validation,
        "secondAssemblyValidation": second_validation,
        "firstOutputHashes": first_hashes,
        "secondOutputHashes": second_hashes,
    }
    if not deterministic:
        raise RoadSurfacePatchError(
            f"independent candidate asset assemblies did not match: {report}"
        )
    return first, second, report


def validate_candidate_patch_assets(
    assets: dict[str, bytes],
    surface: CompositeSurface,
    candidate_float32_sha256: str,
    clipped_roads: dict[str, Any],
) -> dict[str, Any]:
    """Validate the complete deterministic in-memory candidate package before publication."""
    failures: list[str] = []
    inputs = surface.inputs
    if set(assets) != PATCH_OUTPUT_FILES:
        failures.append("candidate file allowlist mismatch")
    if not all(
        isinstance(name, str) and isinstance(payload, bytes) for name, payload in assets.items()
    ):
        failures.append("candidate asset values must be immutable byte strings")
    surface_candidate = surface.patch_heights.astype("<f4", copy=False).tobytes(order="C")
    surface_candidate_hash = hashlib.sha256(surface_candidate).hexdigest()
    if surface_candidate_hash != candidate_float32_sha256:
        failures.append("external candidate Float32 digest does not match validated surface")
    try:
        expected_geometry, _expected_road_ranges = _serialized_geometry_for_surface(
            surface, clipped_roads
        )
    except (KeyError, TypeError, ValueError, RoadSurfacePatchError) as exc:
        expected_geometry = {}
        failures.append(f"cannot derive serialized geometry from validated surface: {exc}")
    if set(expected_geometry) != set(PATCH_GEOMETRY_WITNESS_FILES):
        failures.append("exact validated geometry witness is unavailable")
    else:
        for name, expected_payload in expected_geometry.items():
            if assets.get(name) != expected_payload:
                failures.append(f"serialized {name} differs from the exact validated surface")
    serialized_y_hash = None
    terrain_vertex_payload = assets.get("terrain-vertices.f32")
    if isinstance(terrain_vertex_payload, bytes) and len(terrain_vertex_payload) % 12 == 0:
        serialized_vertices = np.frombuffer(terrain_vertex_payload, dtype="<f4").reshape(-1, 3)
        serialized_y_hash = hashlib.sha256(
            serialized_vertices[:, 1].astype("<f4", copy=False).tobytes(order="C")
        ).hexdigest()
        if serialized_y_hash != candidate_float32_sha256:
            failures.append("serialized terrain Y stream does not match external candidate digest")
    else:
        failures.append("serialized terrain Y stream is malformed")
    manifest: dict[str, Any] = {}
    qa: dict[str, Any] = {}
    try:
        manifest = json.loads(assets["manifest.json"])
        qa = json.loads(assets["qa.json"])
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
        failures.append("candidate manifest or QA is invalid JSON")
    if manifest:
        if (
            manifest.get("packageType") != PATCH_PACKAGE_TYPE
            or manifest.get("formatVersion") != PATCH_FORMAT_VERSION
            or manifest.get("algorithmVersion") != PATCH_ALGORITHM_VERSION
        ):
            failures.append("candidate identity/version mismatch")
        if manifest.get("acceptedPreview", {}).get("assetSha256") != ACCEPTED_PREVIEW_HASHES:
            failures.append("candidate accepted-preview binding mismatch")
        source = manifest.get("source", {})
        expected_source = {
            "releaseId": inputs.release_id,
            "readySha256": _source_record_digest(inputs.source_hashes["ready.json"]),
            "inventorySha256": inputs.source_hashes["inventory.json"]["sha256"],
            "terrainManifestSha256": inputs.manifest_sha256,
            "terrainHeightfieldSha256": inputs.source_hashes["heightfield.f32"]["sha256"],
            "roadManifestSha256": inputs.road_manifest_sha256,
            "roadPayloadSha256": inputs.road_payload_sha256,
            "buildingPayloadSha256": inputs.source_hashes["buildings/buildings.json"]["sha256"],
        }
        if any(source.get(key) != value for key, value in expected_source.items()):
            failures.append("candidate source hash binding mismatch")
        records = manifest.get("assets", {})
        if set(records) != (PATCH_OUTPUT_FILES - {"manifest.json"}):
            failures.append("candidate manifest asset list mismatch")
        for name in PATCH_OUTPUT_FILES - {"manifest.json"}:
            payload = assets.get(name)
            record = records.get(name, {})
            if payload is None:
                continue
            if record.get("byteLength") != len(payload):
                failures.append(f"{name} byte-length descriptor mismatch")
            if record.get("sha256") != hashlib.sha256(payload).hexdigest():
                failures.append(f"{name} SHA-256 descriptor mismatch")
            expected_element_count = 1 if name == "qa.json" else len(payload) // 4
            if record.get("elementCount") != expected_element_count:
                failures.append(f"{name} element-count descriptor mismatch")
    if qa:
        gates = qa.get("gates")
        if (
            qa.get("packageType") != PATCH_PACKAGE_TYPE
            or qa.get("algorithmVersion") != PATCH_ALGORITHM_VERSION
            or qa.get("offlineGatePasses") is not True
            or qa.get("candidateFloat32Sha256") != candidate_float32_sha256
            or not isinstance(gates, dict)
            or set(gates) != set(PATCH_OFFLINE_GATE_NAMES)
            or not all(value is True for value in gates.values())
        ):
            failures.append("candidate QA does not bind a fully passing exact witness")
        if all(
            name in assets and isinstance(assets[name], bytes)
            for name in PATCH_GEOMETRY_WITNESS_FILES
        ):
            try:
                actual_witness = serialized_geometry_witness_sha256(
                    assets, candidate_float32_sha256
                )
            except RoadSurfacePatchError as exc:
                failures.append(str(exc))
            else:
                if qa.get("serializedGeometryWitnessSha256") != actual_witness:
                    failures.append("candidate serialized geometry witness hash mismatch")
        else:
            failures.append("candidate serialized geometry witness is incomplete")
    if "manifest.json" in assets and len(assets["manifest.json"]) > PATCH_MAX_MANIFEST_BYTES:
        failures.append("candidate manifest exceeds byte limit")
    if "qa.json" in assets and len(assets["qa.json"]) > PATCH_MAX_QA_BYTES:
        failures.append("candidate QA exceeds byte limit")
    total_bytes = sum(len(payload) for payload in assets.values())
    if total_bytes > PATCH_MAX_ASSET_BYTES:
        failures.append("candidate runtime assets exceed aggregate byte limit")

    arrays: dict[str, np.ndarray] = {}
    for name in ("terrain-vertices.f32", "road-vertices.f32"):
        payload = assets.get(name, b"")
        if len(payload) % 4:
            failures.append(f"{name} byte length is not float32 aligned")
            continue
        values = np.frombuffer(payload, dtype="<f4")
        arrays[name] = values
        if not np.isfinite(values).all():
            failures.append(f"{name} contains non-finite values")
    for name in ("terrain-indices.u32", "road-indices.u32", "road-terrain-triangles.u32"):
        payload = assets.get(name, b"")
        if len(payload) % 4:
            failures.append(f"{name} byte length is not uint32 aligned")
            continue
        arrays[name] = np.frombuffer(payload, dtype="<u4")

    patch = manifest.get("patch", {}) if manifest else {}
    terrain_vertex_count = int(patch.get("vertexCount", -1))
    terrain_triangle_count = int(patch.get("triangleCount", -1))
    terrain_vertices = arrays.get("terrain-vertices.f32", np.empty(0, dtype="<f4"))
    terrain_indices = arrays.get("terrain-indices.u32", np.empty(0, dtype="<u4"))
    road_vertices = arrays.get("road-vertices.f32", np.empty(0, dtype="<f4"))
    road_indices = arrays.get("road-indices.u32", np.empty(0, dtype="<u4"))
    road_owners = arrays.get("road-terrain-triangles.u32", np.empty(0, dtype="<u4"))
    if terrain_vertices.size != terrain_vertex_count * 3:
        failures.append("terrain vertex buffer does not match manifest vertex count")
    if terrain_indices.size != terrain_triangle_count * 3:
        failures.append("terrain index buffer does not match manifest triangle count")
    if terrain_indices.size and int(terrain_indices.max()) >= terrain_vertex_count:
        failures.append("terrain index buffer references a missing vertex")
    if road_vertices.size % 2 or road_indices.size % 3:
        failures.append("road vertex/index buffer dimensions are malformed")
    if road_indices.size and int(road_indices.max()) >= road_vertices.size // 2:
        failures.append("road index buffer references a missing vertex")
    if len(road_owners) != road_indices.size // 3:
        failures.append("road owner count does not match road face count")
    if road_owners.size and int(road_owners.max()) >= terrain_triangle_count:
        failures.append("road owner buffer references a missing terrain triangle")

    road_ranges = manifest.get("roadGroups", {}) if manifest else {}
    expected_first_vertex = expected_first_index = expected_first_triangle = 0
    for name in ("vehicular", "cycleway", "path"):
        record = road_ranges.get(name, {})
        if (
            record.get("firstVertex") != expected_first_vertex
            or record.get("firstIndex") != expected_first_index
            or record.get("firstTriangle") != expected_first_triangle
            or record.get("indexCount", 0) != record.get("triangleCount", 0) * 3
            or min(
                record.get("vertexCount", -1),
                record.get("indexCount", -1),
                record.get("triangleCount", -1),
            )
            < 0
            or record.get("surfaceOffsetM") != PATCH_ROAD_SURFACE_OFFSET_M
        ):
            failures.append(f"candidate {name} group range is malformed")
        expected_first_vertex += int(record.get("vertexCount", 0))
        expected_first_index += int(record.get("indexCount", 0))
        expected_first_triangle += int(record.get("triangleCount", 0))
    if (
        expected_first_vertex != road_vertices.size // 2
        or expected_first_index != road_indices.size
    ):
        failures.append("candidate road group ranges do not cover the serialized buffers")
    if expected_first_triangle != len(road_owners):
        failures.append("candidate road group ranges do not cover owner buffer")

    return {
        "passes": not failures,
        "failures": failures,
        "surfaceCandidateFloat32Sha256": surface_candidate_hash,
        "serializedTerrainYSha256": serialized_y_hash,
        "fileCount": len(assets),
        "totalRuntimeAssetBytes": total_bytes,
        "manifestBytes": len(assets.get("manifest.json", b"")),
        "qaBytes": len(assets.get("qa.json", b"")),
        "terrainVertexCount": int(terrain_vertices.size // 3),
        "terrainTriangleCount": int(terrain_indices.size // 3),
        "roadVertexCount": int(road_vertices.size // 2),
        "roadTriangleCount": int(road_indices.size // 3),
        "roadOwnerCount": int(len(road_owners)),
    }


def preflight_candidate_publish_paths(
    project_root: Path,
    requested_output: Path,
    execution_record_paths: tuple[Path, Path],
) -> tuple[Path, tuple[Path, Path]]:
    """Validate exact candidate and two fresh build-record destinations before writes."""
    root = project_root.resolve(strict=True)
    expected_output = root / TEIGNMOUTH_CANDIDATE_OUTPUT
    requested = requested_output if requested_output.is_absolute() else root / requested_output
    if ".." in requested.parts:
        raise RoadSurfacePatchError("candidate output path cannot use parent-directory aliases")
    if os.path.normcase(os.path.abspath(str(requested))) != os.path.normcase(str(expected_output)):
        raise RoadSurfacePatchError("candidate output path must match the exact reserved directory")
    protected = _road_surface._protected_execution_inputs(root) + [
        root / "public/worlds/torquay-road-surface-preview",
    ]
    output = _road_surface.guard_output_directory(
        root,
        requested,
        protected,
        owned_files=PATCH_OUTPUT_FILES,
    )
    if output.exists():
        raise RoadSurfacePatchError(
            "reserved candidate output already exists; refusing to overwrite or adopt it"
        )
    if len(execution_record_paths) != 2:
        raise RoadSurfacePatchError("candidate publication requires two fresh build records")
    canonical_records = tuple(
        _road_surface._preflight_execution_record(root, record_path)
        for record_path in execution_record_paths
    )
    if any(path is None for path in canonical_records):
        raise RoadSurfacePatchError("candidate build-record preflight returned no destination")
    records = (canonical_records[0], canonical_records[1])
    if records[0] == records[1]:
        raise RoadSurfacePatchError("candidate build-record IDs must be distinct")
    if any(_road_surface._paths_overlap(output, record) for record in records):
        raise RoadSurfacePatchError("candidate output and build-record paths overlap")
    return output, records


def _stream_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _protected_hash_snapshot(project_root: Path, inputs: Any) -> dict[str, str]:
    """Hash bound source/base bytes and direct protected files for before/after proof."""
    root = project_root.resolve(strict=True)
    snapshot: dict[str, str] = {}
    for name, record in sorted(inputs.source_hashes.items()):
        raw_path = Path(record["path"])
        path = raw_path if raw_path.is_absolute() else root / raw_path
        _road_surface._assert_no_reparse_components(path)
        actual = _stream_sha256(path)
        expected_hash = record.get(
            "sha256", record.get("readySha256", record.get("inventorySha256"))
        )
        if actual != expected_hash:
            raise RoadSurfacePatchError(f"pinned source input changed before publication: {name}")
        snapshot[f"release:{name}"] = actual

    preview_root = root / "public/worlds/torquay-road-surface-preview"
    for name, expected in sorted(ACCEPTED_PREVIEW_HASHES.items()):
        path = preview_root / name
        _road_surface._assert_no_reparse_components(path)
        actual = _stream_sha256(path)
        if actual != expected:
            raise RoadSurfacePatchError(f"accepted preview changed before publication: {name}")
        snapshot[f"acceptedPreview:{name}"] = actual

    for protected in _road_surface._protected_execution_inputs(root):
        _road_surface._assert_no_reparse_components(protected)
        if protected.is_file():
            snapshot[f"protected:{protected.relative_to(root).as_posix()}"] = _stream_sha256(
                protected
            )
        elif not protected.exists():
            snapshot[f"protected:{protected.relative_to(root).as_posix()}"] = "absent"

    for relative in (
        "public/worlds/torquay-poc-001-2km",
        "public/worlds/torquay-poc-001",
        "data/raw/ea_dtm",
    ):
        directory = root / relative
        if not directory.exists():
            snapshot[f"protectedTree:{relative}"] = "absent"
            continue
        _road_surface._assert_no_reparse_components(directory)
        digest = hashlib.sha256()
        for current, child_dirs, filenames in os.walk(directory, followlinks=False):
            current_path = Path(current)
            for name in sorted(child_dirs):
                child = current_path / name
                if _road_surface._is_reparse_point(child):
                    raise RoadSurfacePatchError(
                        f"protected tree contains a reparse directory: {child}"
                    )
            for name in sorted(filenames):
                child = current_path / name
                if _road_surface._is_reparse_point(child):
                    raise RoadSurfacePatchError(f"protected tree contains a reparse file: {child}")
                relative_child = child.relative_to(directory).as_posix()
                file_hash = _stream_sha256(child)
                digest.update(relative_child.encode("utf-8"))
                digest.update(b"\0")
                digest.update(str(child.stat().st_size).encode("ascii"))
                digest.update(b"\0")
                digest.update(file_hash.encode("ascii"))
                digest.update(b"\n")
        snapshot[f"protectedTree:{relative}"] = digest.hexdigest()
    return snapshot


def _write_record_exclusive(path: Path, content: bytes) -> tuple[int, int]:
    identity: tuple[int, int] | None = None
    try:
        with path.open("xb") as stream:
            stat = os.fstat(stream.fileno())
            identity = (stat.st_dev, stat.st_ino)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        return identity
    except BaseException:
        if identity is not None:
            try:
                stat = path.stat(follow_symlinks=False)
                if (
                    (stat.st_dev, stat.st_ino) == identity
                    and path.is_file()
                    and not path.is_symlink()
                ):
                    path.unlink()
            except FileNotFoundError:
                pass
        raise


def _rollback_published_candidate(
    output: Path | None,
    output_identity: tuple[int, int] | None,
    record_identities: list[tuple[Path, tuple[int, int]]],
    expected_assets: dict[str, bytes],
) -> None:
    for path, identity in reversed(record_identities):
        try:
            stat = path.stat(follow_symlinks=False)
            if (stat.st_dev, stat.st_ino) == identity and path.is_file() and not path.is_symlink():
                path.unlink()
        except FileNotFoundError:
            pass
    if output is None or output_identity is None or not output.exists():
        return
    try:
        stat = output.stat(follow_symlinks=False)
        if _road_surface._is_reparse_point(output) or (stat.st_dev, stat.st_ino) != output_identity:
            return
        children = list(output.iterdir())
        if {child.name for child in children} != set(expected_assets):
            return
        for child in children:
            if _road_surface._is_reparse_point(child) or not child.is_file():
                return
            if _stream_sha256(child) != hashlib.sha256(expected_assets[child.name]).hexdigest():
                return
        shutil.rmtree(output)
    except FileNotFoundError:
        return


def publish_candidate_patch_assets(
    project_root: Path,
    surface: CompositeSurface,
    offline_report: dict[str, Any],
    first_assets: dict[str, bytes],
    second_assets: dict[str, bytes],
    execution_record_paths: tuple[Path, Path],
    *,
    requested_output: Path | None = None,
) -> dict[str, Any]:
    """Publish only a fully validated exact witness; atomically own its directory/records."""
    gate_names = offline_report.get("gateNames")
    if (
        offline_report.get("passes") is not True
        or gate_names != list(PATCH_OFFLINE_GATE_NAMES)
        or not all(offline_report.get(name, {}).get("passes") is True for name in gate_names)
    ):
        raise RoadSurfacePatchError(
            "refusing publication before every aggregate offline gate passes"
        )
    candidate_hash = hashlib.sha256(
        surface.patch_heights.astype("<f4", copy=False).tobytes(order="C")
    ).hexdigest()
    if candidate_hash != offline_report.get("candidateFloat32Sha256"):
        raise RoadSurfacePatchError("candidate Float32 witness changed before publication")
    asset_validation_first = validate_candidate_patch_assets(
        first_assets, surface, candidate_hash, offline_report["roadPathReclip"]
    )
    asset_validation_second = validate_candidate_patch_assets(
        second_assets, surface, candidate_hash, offline_report["roadPathReclip"]
    )
    if first_assets is second_assets:
        raise RoadSurfacePatchError(
            "candidate deterministic check requires two independently assembled asset outputs"
        )
    if not asset_validation_first["passes"] or not asset_validation_second["passes"]:
        raise RoadSurfacePatchError(
            "refusing invalid independently assembled candidate packages: "
            f"first={asset_validation_first}, second={asset_validation_second}"
        )
    first_output_hashes = {
        name: hashlib.sha256(payload).hexdigest() for name, payload in sorted(first_assets.items())
    }
    second_output_hashes = {
        name: hashlib.sha256(payload).hexdigest() for name, payload in sorted(second_assets.items())
    }
    if first_output_hashes != second_output_hashes or first_assets != second_assets:
        raise RoadSurfacePatchError(
            "independently assembled candidate assets are not byte-identical"
        )
    asset_validation = {
        "firstAssembly": asset_validation_first,
        "secondAssembly": asset_validation_second,
        "passes": True,
        "descriptorHashesMatch": True,
    }
    assets = first_assets

    root = project_root.resolve(strict=True)
    requested = requested_output or (root / TEIGNMOUTH_CANDIDATE_OUTPUT)
    output, records = preflight_candidate_publish_paths(root, requested, execution_record_paths)
    before_hashes = _protected_hash_snapshot(root, surface.inputs)
    output_identity: tuple[int, int] | None = None
    record_identities: list[tuple[Path, tuple[int, int]]] = []
    stage: Path | None = None
    try:
        parent = output.parent
        _road_surface._assert_no_reparse_components(parent)
        stage = Path(tempfile.mkdtemp(prefix=".teignmouth-patch-stage-", dir=parent))
        _road_surface._assert_no_reparse_components(stage)
        if stage.resolve(strict=True).parent != parent.resolve(strict=True):
            raise RoadSurfacePatchError("candidate staging directory escaped its owned parent")
        for name in sorted(PATCH_OUTPUT_FILES):
            destination = stage / name
            with destination.open("xb") as stream:
                stream.write(assets[name])
                stream.flush()
                os.fsync(stream.fileno())
        staged_files = list(stage.iterdir())
        if {child.name for child in staged_files} != set(PATCH_OUTPUT_FILES):
            raise RoadSurfacePatchError("candidate staging file allowlist changed")
        for child in staged_files:
            if _road_surface._is_reparse_point(child) or not child.is_file():
                raise RoadSurfacePatchError("candidate staging contains a non-regular file")
            if _stream_sha256(child) != hashlib.sha256(assets[child.name]).hexdigest():
                raise RoadSurfacePatchError("candidate staging file bytes changed before rename")
        _road_surface.guard_output_directory(
            root,
            output,
            _road_surface._protected_execution_inputs(root)
            + [root / "public/worlds/torquay-road-surface-preview"],
            owned_files=PATCH_OUTPUT_FILES,
        )
        if output.exists():
            raise RoadSurfacePatchError("candidate output appeared during staging; refusing commit")
        for record_path in records:
            if _road_surface._preflight_execution_record(root, record_path) != record_path:
                raise RoadSurfacePatchError("build-record path changed during candidate staging")
        try:
            os.rename(stage, output)
        except FileExistsError as exc:
            raise RoadSurfacePatchError(
                "candidate output collision at final rename; refusing overwrite"
            ) from exc
        stage = None
        _road_surface._assert_no_reparse_components(output)
        output_stat = output.stat(follow_symlinks=False)
        output_identity = (output_stat.st_dev, output_stat.st_ino)
        after_hashes = _protected_hash_snapshot(root, surface.inputs)
        if after_hashes != before_hashes:
            raise RoadSurfacePatchError("protected source/base hashes changed during publication")
        output_hashes = first_output_hashes
        record_common = {
            "formatVersion": 1,
            "packageType": PATCH_PACKAGE_TYPE,
            "algorithmVersion": PATCH_ALGORITHM_VERSION,
            "outputDirectory": TEIGNMOUTH_CANDIDATE_OUTPUT,
            "releaseId": surface.inputs.release_id,
            "candidateFloat32Sha256": candidate_hash,
            "offlineGatePasses": True,
            "offlineGateNames": list(PATCH_OFFLINE_GATE_NAMES),
            "assetValidation": asset_validation,
            "outputHashes": output_hashes,
            "protectedHashesBefore": before_hashes,
            "protectedHashesAfter": after_hashes,
        }
        for assembly_index, (record_path, assembly_hashes, assembly_validation) in enumerate(
            zip(
                records,
                (first_output_hashes, second_output_hashes),
                (asset_validation_first, asset_validation_second),
                strict=True,
            ),
            start=1,
        ):
            if _road_surface._preflight_execution_record(root, record_path) != record_path:
                raise RoadSurfacePatchError("build-record path changed before exclusive write")
            record_number = int(record_path.stem.removeprefix("build-"))
            record_bytes = (
                json.dumps(
                    record_common
                    | {
                        "buildNumber": record_number,
                        "independentAssembly": assembly_index,
                        "outputHashes": assembly_hashes,
                        "assetValidation": assembly_validation,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                ).encode("utf-8")
                + b"\n"
            )
            record_identity = _write_record_exclusive(record_path, record_bytes)
            record_identities.append((record_path, record_identity))
        final_hashes = _protected_hash_snapshot(root, surface.inputs)
        if final_hashes != before_hashes:
            raise RoadSurfacePatchError("protected hashes changed before candidate handoff")
        return {
            "passes": True,
            "outputDirectory": output.relative_to(root).as_posix(),
            "outputHashes": output_hashes,
            "buildRecords": [path.relative_to(root).as_posix() for path in records],
            "protectedHashesBefore": before_hashes,
            "protectedHashesAfter": final_hashes,
            "assetValidation": asset_validation,
            "independentAssemblyOutputHashes": [first_output_hashes, second_output_hashes],
            "deterministicAssets": True,
        }
    except BaseException:
        _rollback_published_candidate(output, output_identity, record_identities, assets)
        raise
    finally:
        if stage is not None and stage.exists():
            _road_surface._assert_no_reparse_components(stage)
            if stage.resolve(strict=True).parent == output.parent.resolve(strict=True):
                shutil.rmtree(stage)


def _combine_weights(*terms: tuple[dict[int, float], float]) -> tuple[np.ndarray, np.ndarray]:
    combined: dict[int, float] = {}
    for weights, scale in terms:
        for index, value in weights.items():
            combined[index] = combined.get(index, 0.0) + scale * value
    kept = [(index, value) for index, value in sorted(combined.items()) if abs(value) > 1e-13]
    return (
        np.asarray([item[0] for item in kept], dtype=np.int64),
        np.asarray([item[1] for item in kept], dtype=np.float64),
    )


def build_local_phase_one_constraints(
    mesh: PatchMesh,
    inputs: ReleaseInputs,
    accepted_heights: np.ndarray | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build the amendment's ≤1 m/0.25 m local halfspaces on actual patch triangles."""
    feature = next(
        item
        for item in inputs.road_payload["features"]
        if item.get("source", {}).get("osmId") == TEIGNMOUTH_WAY_ID
    )
    part = [
        [float(point[0]), float(point[1])]
        for point in feature["centerlinePartsXZ"][TEIGNMOUTH_PART_INDEX]
    ]
    cumulative = [0.0]
    for first, second in zip(part, part[1:], strict=False):
        cumulative.append(cumulative[-1] + math.dist(first, second))

    def position_tangent(station: float) -> tuple[tuple[float, float], tuple[float, float]]:
        for index in range(len(part) - 1):
            if cumulative[index] <= station <= cumulative[index + 1]:
                dx = part[index + 1][0] - part[index][0]
                dz = part[index + 1][1] - part[index][1]
                length = math.hypot(dx, dz)
                fraction = (station - cumulative[index]) / length
                return (
                    (part[index][0] + dx * fraction, part[index][1] + dz * fraction),
                    (dx / length, dz / length),
                )
        raise RoadSurfacePatchError(f"station {station:g} is outside Teignmouth part 0")

    corridor_union = mandatory_corridor_station_union(inputs, way_ids=(TEIGNMOUTH_WAY_ID,))
    stations = {
        TEIGNMOUTH_STATION_START_M + index
        for index in range(math.floor(TEIGNMOUTH_STATION_END_M - TEIGNMOUTH_STATION_START_M) + 1)
    }
    stations.add(TEIGNMOUTH_STATION_END_M)
    stations.add(148.15104603556912)
    stations.update(
        station
        for station in cumulative
        if TEIGNMOUTH_STATION_START_M <= station <= TEIGNMOUTH_STATION_END_M
    )
    stations.update(
        station
        for station in corridor_union[(TEIGNMOUTH_WAY_ID, TEIGNMOUTH_PART_INDEX)]
        if TEIGNMOUTH_STATION_START_M <= station <= TEIGNMOUTH_STATION_END_M
    )
    ordered_stations = sorted(stations)
    if max(np.diff(ordered_stations), default=0.0) > 1.0 + 1e-9:
        raise RoadSurfacePatchError("local phase-I station spacing exceeds 1 m")

    constraints: list[dict[str, Any]] = []
    severe_constraint_station_count = 0
    severe_constraint_outside_patch_count = 0
    target_width = float(feature["estimatedWidthM"])
    for station in corridor_union[(TEIGNMOUTH_WAY_ID, TEIGNMOUTH_PART_INDEX)]:
        (x, z), (tangent_x, tangent_z) = position_tangent(station)
        normal_x, normal_z = -tangent_z, tangent_x
        left_x = x - normal_x * target_width / 2
        left_z = z - normal_z * target_width / 2
        right_x = x + normal_x * target_width / 2
        right_z = z + normal_z * target_width / 2
        baseline_left = _sample_grid(inputs.baseline, left_x, left_z, inputs.spacing_m)
        baseline_right = _sample_grid(inputs.baseline, right_x, right_z, inputs.spacing_m)
        baseline_crossfall = abs(baseline_right - baseline_left) / target_width * 100.0
        if baseline_crossfall < 10.0:
            continue
        try:
            left_weights = _patch_sample_weights(mesh, inputs, left_x, left_z)
            right_weights = _patch_sample_weights(mesh, inputs, right_x, right_z)
        except RoadSurfacePatchError:
            severe_constraint_outside_patch_count += 1
            continue
        indices, coefficients = _combine_weights((right_weights, 1.0), (left_weights, -1.0))
        maximum_difference = 0.5 * abs(baseline_right - baseline_left)
        solver_limit = maximum_difference - SEVERE_CROSSFALL_NUMERICAL_MARGIN_M
        label = {
            "kind": "mandatory-severe-corridor-crossfall",
            "wayId": TEIGNMOUTH_WAY_ID,
            "partIndex": TEIGNMOUTH_PART_INDEX,
            "stationM": station,
            "baselineCrossfallPercent": baseline_crossfall,
            "maximumPreviewCrossfallPercent": baseline_crossfall * 0.5,
            "solverHeadroomM": SEVERE_CROSSFALL_NUMERICAL_MARGIN_M,
        }
        constraints.extend(
            [
                {
                    "indices": indices,
                    "coefficients": coefficients,
                    "limitM": solver_limit,
                    "label": {**label, "direction": "right-minus-left"},
                },
                {
                    "indices": indices,
                    "coefficients": -coefficients,
                    "limitM": solver_limit,
                    "label": {**label, "direction": "left-minus-right"},
                },
            ]
        )
        severe_constraint_station_count += 1

    local_samples: dict[tuple[float, int], dict[int, float]] = {}
    baseline_samples: dict[tuple[float, int], float] = {}
    for station in ordered_stations:
        (center_x, center_z), (tangent_x, tangent_z) = position_tangent(station)
        normal_x, normal_z = -tangent_z, tangent_x
        for lateral_index in range(25):
            offset = -3.0 + lateral_index * PATCH_LATERAL_SAMPLE_M
            x, z = center_x + normal_x * offset, center_z + normal_z * offset
            weights = _patch_sample_weights(mesh, inputs, x, z)
            key = (station, lateral_index)
            local_samples[key] = weights
            baseline_samples[key] = _sample_grid(inputs.baseline, x, z, inputs.spacing_m)
        for lateral_index in range(24):
            first = local_samples[(station, lateral_index)]
            second = local_samples[(station, lateral_index + 1)]
            indices, coefficients = _combine_weights((second, 1.0), (first, -1.0))
            limit = PATCH_LATERAL_SLOPE * PATCH_LATERAL_SAMPLE_M - PATCH_CROSSFALL_STEP_HEADROOM_M
            label = {
                "kind": "teignmouth-local-crossfall",
                "stationM": station,
                "lateralOffsetStartM": -3.0 + lateral_index * PATCH_LATERAL_SAMPLE_M,
            }
            constraints.extend(
                [
                    {
                        "indices": indices,
                        "coefficients": coefficients,
                        "limitM": limit,
                        "label": label,
                    },
                    {
                        "indices": indices,
                        "coefficients": -coefficients,
                        "limitM": limit,
                        "label": label,
                    },
                ]
            )
        indices, coefficients = _combine_weights(
            (local_samples[(station, 24)], 1.0),
            (local_samples[(station, 0)], -1.0),
        )
        constraints.extend(
            [
                {
                    "indices": indices,
                    "coefficients": coefficients,
                    "limitM": PATCH_ENDPOINT_SPAN_M,
                    "label": {"kind": "teignmouth-endpoint-span", "stationM": station},
                },
                {
                    "indices": indices,
                    "coefficients": -coefficients,
                    "limitM": PATCH_ENDPOINT_SPAN_M,
                    "label": {"kind": "teignmouth-endpoint-span", "stationM": station},
                },
            ]
        )

    center_samples: dict[float, dict[int, float]] = {}
    center_baseline: dict[float, float] = {}
    for station in ordered_stations:
        (x, z), _tangent = position_tangent(station)
        center_samples[station] = _patch_sample_weights(mesh, inputs, x, z)
        center_baseline[station] = _sample_grid(inputs.baseline, x, z, inputs.spacing_m)
        weights = center_samples[station]
        indices = np.asarray(sorted(weights), dtype=np.int64)
        coefficients = np.asarray([weights[index] for index in indices], dtype=np.float64)
        for direction in (-1.0, 1.0):
            constraints.append(
                {
                    "indices": indices,
                    "coefficients": coefficients * direction,
                    "limitM": 0.0999 + direction * center_baseline[station],
                    "label": {"kind": "teignmouth-centerline-envelope", "stationM": station},
                }
            )
    for first_station, second_station in zip(ordered_stations, ordered_stations[1:], strict=False):
        indices, coefficients = _combine_weights(
            (center_samples[second_station], 1.0),
            (center_samples[first_station], -1.0),
        )
        baseline_grade_delta = center_baseline[second_station] - center_baseline[first_station]
        maximum_grade_delta = PATCH_LONGITUDINAL_GRADE_DELTA * (second_station - first_station)
        limit = maximum_grade_delta + baseline_grade_delta
        label = {
            "kind": "teignmouth-longitudinal-grade-delta",
            "stationStartM": first_station,
            "stationEndM": second_station,
        }
        constraints.extend(
            [
                {"indices": indices, "coefficients": coefficients, "limitM": limit, "label": label},
                {
                    "indices": indices,
                    "coefficients": -coefficients,
                    "limitM": maximum_grade_delta - baseline_grade_delta,
                    "label": label,
                },
            ]
        )
    profile_feature_by_id = {
        int(item.get("source", {}).get("osmId", -1)): item
        for item in inputs.road_payload.get("features", [])
        if isinstance(item, dict)
    }
    full_profile_constraint_count = 0
    full_profile_constrained_station_count = 0
    full_profile_missing_way_ids = []
    accepted_grid = (
        np.asarray(accepted_heights, dtype=np.float32)
        if accepted_heights is not None
        else inputs.baseline
    )
    for way_id in PROFILE_WAY_IDS:
        profile_feature = profile_feature_by_id.get(way_id)
        if profile_feature is None:
            full_profile_missing_way_ids.append(way_id)
            continue
        for part_index, raw_part in enumerate(profile_feature["centerlinePartsXZ"]):
            profile_part = [tuple(map(float, point)) for point in raw_part]
            profile_stations, _profile_length = _road_part_stations(profile_part, 5.0)
            profile_samples: list[tuple[dict[int, float] | None, float, float]] = []
            for station in profile_stations:
                (x, z), _tangent = _line_point_tangent(profile_part, station)
                baseline_height = _sample_grid(inputs.baseline, x, z, inputs.spacing_m)
                accepted_height = _sample_grid(accepted_grid, x, z, inputs.spacing_m)
                try:
                    weights: dict[int, float] | None = _patch_sample_weights(mesh, inputs, x, z)
                except RoadSurfacePatchError:
                    weights = None
                profile_samples.append((weights, baseline_height, accepted_height))
                if weights is None:
                    continue
                indices = np.asarray(sorted(weights), dtype=np.int64)
                coefficients = np.asarray([weights[index] for index in indices], dtype=np.float64)
                for direction in (-1.0, 1.0):
                    constraints.append(
                        {
                            "indices": indices,
                            "coefficients": coefficients * direction,
                            "limitM": 0.0999 + direction * baseline_height,
                            "label": {
                                "kind": "registered-full-way-centerline-envelope",
                                "wayId": way_id,
                                "partIndex": part_index,
                                "stationM": station,
                            },
                        }
                    )
                    full_profile_constraint_count += 1
                full_profile_constrained_station_count += 1
            for sample_index in range(len(profile_samples) - 1):
                first_station = profile_stations[sample_index]
                second_station = profile_stations[sample_index + 1]
                first_weights, first_baseline, first_accepted = profile_samples[sample_index]
                second_weights, second_baseline, second_accepted = profile_samples[sample_index + 1]
                if first_weights is None and second_weights is None:
                    continue
                indices, coefficients = _combine_weights(
                    (second_weights or {}, 1.0),
                    (first_weights or {}, -1.0),
                )
                station_delta = second_station - first_station
                baseline_delta = second_baseline - first_baseline
                fixed_delta = (second_accepted if second_weights is None else 0.0) - (
                    first_accepted if first_weights is None else 0.0
                )
                maximum_grade_delta = PATCH_LONGITUDINAL_GRADE_DELTA * station_delta
                label = {
                    "kind": "registered-full-way-signed-grade-change",
                    "wayId": way_id,
                    "partIndex": part_index,
                    "stationStartM": first_station,
                    "stationEndM": second_station,
                }
                constraints.extend(
                    [
                        {
                            "indices": indices,
                            "coefficients": coefficients,
                            "limitM": maximum_grade_delta + baseline_delta - fixed_delta,
                            "label": label,
                        },
                        {
                            "indices": indices,
                            "coefficients": -coefficients,
                            "limitM": maximum_grade_delta - baseline_delta + fixed_delta,
                            "label": label,
                        },
                    ]
                )
                full_profile_constraint_count += 2
    return constraints, {
        "stationCount": len(ordered_stations),
        "acceptedMandatoryStationCountInWindow": sum(
            TEIGNMOUTH_STATION_START_M <= station <= TEIGNMOUTH_STATION_END_M
            for station in corridor_union[(TEIGNMOUTH_WAY_ID, TEIGNMOUTH_PART_INDEX)]
        ),
        "mandatorySevereStationConstraintCountInPatch": severe_constraint_station_count,
        "mandatorySevereStationCountOutsidePatch": severe_constraint_outside_patch_count,
        "stationUnionContract": "shared accepted ≤1 m/source-vertex/fallback-boundary union",
        "maximumStationSpacingM": float(max(np.diff(ordered_stations), default=0.0)),
        "lateralSamplesPerStation": 25,
        "sampleSpacingAcrossWidthM": PATCH_LATERAL_SAMPLE_M,
        "constraintCount": len(constraints),
        "registeredFullWayProfileConstraintCount": full_profile_constraint_count,
        "registeredFullWayConstrainedStationCount": full_profile_constrained_station_count,
        "registeredFullWayIds": list(PROFILE_WAY_IDS),
        "registeredFullWayMissingIds": full_profile_missing_way_ids,
        "method": "renderer conforming-patch triangle barycentric interpolation",
    }


def solve_bounded_local_feasibility(
    matrix: np.ndarray,
    limits: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    *,
    maximum_iterations: int = 2000,
    maximum_wall_seconds: float = 60.0,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Row-scaled ADMM feasibility, with a separately checked bounded Farkas proof.

    This small dense phase is restricted to local halfspaces, not the full terrain
    graph. Fixed unknowns are eliminated and free unknowns are centered. A failed
    convergence test is never an infeasibility result: only a positive weighted-
    inequality contradiction over the original finite bounds earns that status.
    No external optimizer or dependency is used.
    """
    started = time.monotonic()
    matrix = np.asarray(matrix, dtype=np.float64)
    limits = np.asarray(limits, dtype=np.float64)
    lower, upper = np.asarray(lower, dtype=np.float64), np.asarray(upper, dtype=np.float64)
    if (
        matrix.ndim != 2
        or matrix.shape != (len(limits), len(lower))
        or upper.shape != lower.shape
        or not all(np.isfinite(value).all() for value in (matrix, limits, lower, upper))
        or np.any(lower > upper)
        or maximum_iterations <= 0
        or maximum_wall_seconds <= 0
        or matrix.shape[0] > 4096
        or matrix.shape[1] > 1024
    ):
        raise RoadSurfacePatchError("invalid or oversized bounded local feasibility system")
    center = (lower + upper) * 0.5
    free = lower != upper
    norms = np.linalg.norm(matrix[:, free], axis=1)
    norms = np.where(norms > 0.0, norms, 1.0)
    scaled = matrix[:, free] / norms[:, None]
    shifted_limits = (limits - matrix @ center) / norms
    free_lower, free_upper = (lower - center)[free], (upper - center)[free]
    operator = np.vstack((scaled, np.eye(int(free.sum()))))
    # Positive definite because the identity block includes every free unknown.
    inverse_operator = np.linalg.solve(operator.T @ operator, operator.T)
    x = np.zeros(int(free.sum()))
    z = operator @ x
    z[: len(limits)] = np.minimum(z[: len(limits)], shifted_limits)
    z[len(limits) :] = np.clip(z[len(limits) :], free_lower, free_upper)
    dual = np.zeros_like(z)
    status = "iteration_limit"
    certificate = None
    values = center.copy()
    iteration = 0
    for iteration in range(1, maximum_iterations + 1):
        if time.monotonic() - started >= maximum_wall_seconds:
            status = "wall_clock_limit"
            break
        x = inverse_operator @ (z - dual)
        projected = operator @ x
        relaxed = 1.6 * projected - 0.6 * z
        next_z = relaxed + dual
        next_z[: len(limits)] = np.minimum(next_z[: len(limits)], shifted_limits)
        next_z[len(limits) :] = np.clip(next_z[len(limits) :], free_lower, free_upper)
        dual += relaxed - next_z
        z = next_z
        if iteration == 1 or iteration % 10 == 0:
            values[free] = np.clip(x, free_lower, free_upper) + center[free]
            if float(np.max(matrix @ values - limits, initial=-math.inf)) <= 1e-8:
                status = "feasible"
                break
            weights = np.maximum(dual[: len(limits)] / norms, 0.0)
            total = float(np.sum(weights))
            if total <= 0.0:
                continue
            weights /= total
            # Original, unscaled inequalities and bounds are used for the proof.
            combined = matrix.T @ weights
            lower_bound = math.fsum(np.minimum(combined * lower, combined * upper))
            weighted_limit = math.fsum(limits * weights)
            magnitude = float(
                np.sum(
                    np.abs(matrix)
                    * weights[:, None]
                    * np.maximum(np.abs(lower), np.abs(upper))[None, :]
                )
            )
            allowance = (
                8
                * (len(limits) + len(lower) + 1)
                * np.finfo(np.float64).eps
                * (magnitude + float(np.sum(np.abs(limits * weights))) + 1.0)
                + 1e-12
            )
            gap = lower_bound - weighted_limit
            if gap > max(1e-8, allowance):
                certificate = {
                    "method": "nonnegative weighted inequalities versus finite variable bounds",
                    "nonnegativeRowWeights": weights.tolist(),
                    "combinedCoefficients": combined.tolist(),
                    "minimumCombinedValueOverBoundsM": lower_bound,
                    "weightedUpperLimitM": weighted_limit,
                    "contradictionGapM": gap,
                    "roundoffAllowanceM": allowance,
                }
                status = "certified_infeasible"
                break
    return values, {
        "method": "centered fixed-eliminated row-normalized ADMM, relaxation 1.6",
        "status": status,
        "iterations": iteration,
        "maximumIterations": maximum_iterations,
        "elapsedSeconds": time.monotonic() - started,
        "maximumWallSeconds": maximum_wall_seconds,
        "rowCount": len(limits),
        "variableCount": len(lower),
        "freeVariableCount": int(free.sum()),
        "maximumOriginalRowViolationM": float(np.max(matrix @ values - limits, initial=-math.inf)),
        "infeasibilityCertificate": certificate,
    }


def solve_local_phase_one(
    mesh: PatchMesh,
    inputs: ReleaseInputs,
    constraints: list[dict[str, Any]],
    *,
    influence: Polygon | None = None,
    maximum_iterations: int = 200,
    tolerance_m: float = 2e-5,
    maximum_wall_seconds: float = 120.0,
    certified_local_phase: bool = False,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Bounded Dykstra solve with a smooth warm start and a hard wall-clock limit."""
    if maximum_iterations <= 0 or maximum_wall_seconds <= 0:
        raise RoadSurfacePatchError("phase-I solver limits must be positive")
    started = time.monotonic()
    deadline = started + maximum_wall_seconds
    fixed_mask = _fixed_patch_vertices(mesh, influence, deadline=deadline)
    warm_start, warm_report = _build_flattened_warm_start(mesh, inputs, influence, fixed_mask)
    values = warm_start.astype(np.float64)
    source_nodes = _sample_grid_many(
        inputs.baseline,
        mesh.vertices_xz[:, 0],
        mesh.vertices_xz[:, 1],
        inputs.spacing_m,
    )
    lower, upper = source_nodes - 4.999, source_nodes + 4.999
    boundary = np.zeros(len(values), dtype=bool)
    boundary[mesh.boundary_edges.ravel()] = True
    fixed_mask |= boundary
    # Solve against the exact bytes that the displayed shared surface will use.
    fixed = mesh.base_y.astype("<f4").astype(np.float64)
    values[fixed_mask] = fixed[fixed_mask]
    lower[fixed_mask] = fixed[fixed_mask]
    upper[fixed_mask] = fixed[fixed_mask]
    local_phase_report = None
    if certified_local_phase:
        local_constraints = [
            item for item in constraints if item["label"].get("kind", "").startswith("teignmouth-")
        ]
        local_nodes = np.unique(np.concatenate([item["indices"] for item in local_constraints]))
        local_matrix = np.zeros((len(local_constraints), len(local_nodes)), dtype=np.float64)
        for row, item in enumerate(local_constraints):
            np.add.at(
                local_matrix[row],
                np.searchsorted(local_nodes, item["indices"]),
                item["coefficients"],
            )
        actual_limits = np.asarray(
            [_actual_local_constraint_limit(item) for item in local_constraints]
        )
        proof_lower, proof_upper = source_nodes[local_nodes] - 5.0, source_nodes[local_nodes] + 5.0
        local_fixed = fixed_mask[local_nodes]
        proof_lower[local_fixed] = fixed[local_nodes[local_fixed]]
        proof_upper[local_fixed] = fixed[local_nodes[local_fixed]]
        local_values, local_phase_report = solve_bounded_local_feasibility(
            local_matrix,
            actual_limits,
            proof_lower,
            proof_upper,
            maximum_iterations=min(maximum_iterations, 2000),
            maximum_wall_seconds=min(60.0, max(0.001, deadline - time.monotonic())),
        )
        local_phase_report["usesActualAcceptanceLimitsNotHeadroom"] = True
        local_phase_report["nodeIndices"] = local_nodes.tolist()
        local_phase_report["nodeCoordinatesXZ"] = mesh.vertices_xz[local_nodes].tolist()
        local_phase_report["lowerBoundsM"] = proof_lower.tolist()
        local_phase_report["upperBoundsM"] = proof_upper.tolist()
        local_phase_report["rows"] = [
            {
                "nodeIndices": item["indices"].tolist(),
                "coefficients": item["coefficients"].tolist(),
                "actualLimitM": float(limit),
                "label": item["label"],
            }
            for item, limit in zip(local_constraints, actual_limits, strict=True)
        ]
        values[local_nodes] = local_values
        values[fixed_mask] = fixed[fixed_mask]
    all_edges = np.asarray(list(mesh.edge_counts), dtype=np.int64)
    all_edge_lengths = np.linalg.norm(
        mesh.vertices_xz[all_edges[:, 0]] - mesh.vertices_xz[all_edges[:, 1]], axis=1
    )
    source_delta = np.abs(source_nodes[all_edges[:, 0]] - source_nodes[all_edges[:, 1]])
    all_edge_limits = source_delta + PATCH_MAX_ADDED_GRADIENT * all_edge_lengths
    fixed_fixed = fixed_mask[all_edges[:, 0]] & fixed_mask[all_edges[:, 1]]
    strict_edge_limits = source_delta + all_edge_lengths
    fixed_fixed_excess = (
        np.abs(fixed[all_edges[fixed_fixed, 0]] - fixed[all_edges[fixed_fixed, 1]])
        - strict_edge_limits[fixed_fixed]
    )
    if np.any(fixed_fixed_excess >= 0.0):
        edge_index = int(np.argmax(fixed_fixed_excess))
        raise RoadSurfacePatchError(
            "pinned accepted-surface edge violates the strict added-gradient cap: "
            f"excess={fixed_fixed_excess[edge_index]:.9g} m"
        )
    active_edge_indices = np.flatnonzero(~fixed_fixed)
    edges = all_edges[active_edge_indices]
    edge_limits = all_edge_limits[active_edge_indices]
    edge_first_fixed = fixed_mask[edges[:, 0]]
    edge_second_fixed = fixed_mask[edges[:, 1]]
    edge_both_free = ~edge_first_fixed & ~edge_second_fixed
    edge_one_fixed = edge_first_fixed ^ edge_second_fixed
    edge_free_vertex = np.where(edge_first_fixed, edges[:, 1], edges[:, 0])
    edge_fixed_vertex = np.where(edge_first_fixed, edges[:, 0], edges[:, 1])
    # Greedy edge coloring allows deterministic vectorized projections per matching.
    incident: list[set[int]] = [set() for _ in values]
    colors: list[list[int]] = []
    for edge_index, (first, second) in enumerate(edges):
        if edge_index % 8192 == 0 and time.monotonic() >= deadline:
            raise RoadSurfacePatchError(
                "phase-I solver exceeded its wall-clock cap while preparing mesh constraints"
            )
        unavailable = incident[int(first)] | incident[int(second)]
        color = next(
            (index for index in range(len(colors)) if index not in unavailable), len(colors)
        )
        if color == len(colors):
            colors.append([])
        colors[color].append(edge_index)
        incident[int(first)].add(color)
        incident[int(second)].add(color)
    del incident
    edge_corrections = np.zeros(len(edges), dtype=np.float64)
    node_corrections = np.zeros(len(values), dtype=np.float64)
    projected_constraints: list[dict[str, Any]] = []
    fixed_constraint_failures = []
    for constraint in constraints:
        nodes = np.asarray(constraint["indices"], dtype=np.int64)
        coefficients = np.asarray(constraint["coefficients"], dtype=np.float64)
        is_fixed = fixed_mask[nodes]
        fixed_part = float(np.dot(coefficients[is_fixed], fixed[nodes[is_fixed]]))
        free_nodes = nodes[~is_fixed]
        free_coefficients = coefficients[~is_fixed]
        adjusted_limit = float(constraint["limitM"]) - fixed_part
        if not len(free_nodes):
            if fixed_part - float(constraint["limitM"]) > tolerance_m:
                fixed_constraint_failures.append(
                    {
                        **constraint["label"],
                        "excessM": fixed_part - float(constraint["limitM"]),
                    }
                )
            continue
        norm = float(np.dot(free_coefficients, free_coefficients))
        if norm <= 0.0:
            fixed_constraint_failures.append(
                {**constraint["label"], "reason": "empty free constraint has nonzero norm"}
            )
            continue
        projected_constraints.append(
            {
                "indices": free_nodes,
                "coefficients": free_coefficients,
                "limitM": adjusted_limit,
                "norm": norm,
                "label": constraint["label"],
            }
        )
    linear_corrections = np.zeros(len(projected_constraints), dtype=np.float64)
    max_violation = math.inf
    worst_edge = None
    worst_local = None
    quantized_validation: dict[str, Any] | None = None
    iteration = 0
    for iteration in range(1, maximum_iterations + 1):
        if time.monotonic() >= deadline:
            break
        for color in colors:
            ids = np.asarray(color, dtype=np.int64)
            both_free = edge_both_free[ids]
            if np.any(both_free):
                free_ids = ids[both_free]
                free_first, free_second = edges[free_ids, 0], edges[free_ids, 1]
                free_correction = edge_corrections[free_ids]
                difference = values[free_second] - values[free_first] + 2.0 * free_correction
                clipped_difference = np.clip(
                    difference, -edge_limits[free_ids], edge_limits[free_ids]
                )
                next_free_correction = (difference - clipped_difference) * 0.5
                values[free_first] += -free_correction + next_free_correction
                values[free_second] += free_correction - next_free_correction
                edge_corrections[free_ids] = next_free_correction
            one_fixed = edge_one_fixed[ids]
            if np.any(one_fixed):
                one_ids = ids[one_fixed]
                free_vertices = edge_free_vertex[one_ids]
                fixed_vertices = edge_fixed_vertex[one_ids]
                adjusted_free = values[free_vertices] + edge_corrections[one_ids]
                clipped_free = np.clip(
                    adjusted_free,
                    fixed[fixed_vertices] - edge_limits[one_ids],
                    fixed[fixed_vertices] + edge_limits[one_ids],
                )
                edge_corrections[one_ids] = adjusted_free - clipped_free
                values[free_vertices] = clipped_free
        adjusted = values + node_corrections
        adjusted[fixed_mask] = fixed[fixed_mask]
        clipped = np.clip(adjusted, lower, upper)
        clipped[fixed_mask] = fixed[fixed_mask]
        node_corrections = adjusted - clipped
        node_corrections[fixed_mask] = 0.0
        values = clipped
        flat = values
        for index, constraint in enumerate(projected_constraints):
            nodes = constraint["indices"]
            coefficients = constraint["coefficients"]
            adjusted_values = flat[nodes] + linear_corrections[index] * coefficients
            violation = float(np.dot(coefficients, adjusted_values) - constraint["limitM"])
            next_correction = max(0.0, violation / constraint["norm"])
            flat[nodes] = adjusted_values - next_correction * coefficients
            linear_corrections[index] = next_correction
        values[fixed_mask] = fixed[fixed_mask]
        if iteration == 1 or iteration % 5 == 0:
            edge_violations = np.abs(values[edges[:, 1]] - values[edges[:, 0]]) - edge_limits
            edge_index = int(np.argmax(edge_violations))
            edge_violation = float(edge_violations[edge_index])
            local_violations = np.asarray(
                [
                    float(np.dot(item["coefficients"], values[item["indices"]]) - item["limitM"])
                    for item in constraints
                ],
                dtype=np.float64,
            )
            local_index = int(np.argmax(local_violations)) if len(local_violations) else None
            local_violation = (
                float(local_violations[local_index]) if local_index is not None else 0.0
            )
            worst_edge = {
                "vertices": [int(value) for value in edges[edge_index]],
                "excessM": edge_violation,
            }
            worst_local = (
                {**constraints[local_index]["label"], "excessM": local_violation}
                if local_index is not None
                else None
            )
            max_violation = max(
                edge_violation,
                local_violation,
                float(np.max(lower - values)),
                float(np.max(values - upper)),
                float(np.max(np.abs(values[fixed_mask] - fixed[fixed_mask])))
                if np.any(fixed_mask)
                else 0.0,
            )
            if local_phase_report and local_phase_report["status"] == "certified_infeasible":
                break
            if max_violation <= tolerance_m:
                candidate = values.astype("<f4")
                quantized_validation = _validate_quantized_phase_one(
                    mesh,
                    candidate,
                    source_nodes,
                    all_edges,
                    all_edge_limits,
                    constraints,
                    fixed_mask,
                    fixed,
                    influence,
                    solver_tolerance_m=tolerance_m,
                )
                if quantized_validation["passes"]:
                    break
    candidate = values.astype("<f4")
    candidate_hash = hashlib.sha256(candidate.tobytes(order="C")).hexdigest()
    if quantized_validation is None or iteration == maximum_iterations:
        quantized_validation = _validate_quantized_phase_one(
            mesh,
            candidate,
            source_nodes,
            all_edges,
            all_edge_limits,
            constraints,
            fixed_mask,
            fixed,
            influence,
            solver_tolerance_m=tolerance_m,
        )
    elapsed = time.monotonic() - started
    timed_out = elapsed >= maximum_wall_seconds
    converged = bool(
        not timed_out and max_violation <= tolerance_m and quantized_validation["passes"]
    )
    return candidate, {
        "iterations": iteration,
        "maximumIterations": maximum_iterations,
        "elapsedSeconds": elapsed,
        "maximumWallSeconds": maximum_wall_seconds,
        "wallClockLimitReached": timed_out,
        "maximumConstraintResidualM": max_violation,
        "converged": converged,
        "worstMeshEdgeConstraint": worst_edge,
        "worstLocalConstraint": worst_local,
        "maximumAbsoluteChangeFromSourceM": float(
            np.max(np.abs(candidate.astype(np.float64) - source_nodes))
        ),
        "edgeColorCount": len(colors),
        "edgeConstraintCount": len(all_edges),
        "activeEdgeConstraintCount": len(edges),
        "boundaryFixedVertexCount": int(boundary.sum()),
        "influenceFixedVertexCount": int(fixed_mask.sum()),
        "fixedOnlyConstraintFailureCount": len(fixed_constraint_failures),
        "fixedOnlyConstraintFailures": fixed_constraint_failures,
        "warmStart": warm_report,
        "quantizedValidation": quantized_validation,
        "outsideInfluence": quantized_validation["outsideInfluenceSurface"],
        "float32Finite": bool(np.isfinite(candidate).all()),
        "candidateFloat32Sha256": candidate_hash,
        "boundedLocalFeasibility": local_phase_report,
    }


def _triangles_fully_within_influence(
    mesh: PatchMesh, influence: Polygon, *, deadline: float | None = None
) -> np.ndarray:
    """Classify faces conservatively in bulk, exactly checking only boundary candidates."""
    triangles = mesh.triangles
    coordinates = mesh.vertices_xz[triangles].astype(np.float64)
    centroids = coordinates.mean(axis=1)
    radii = np.max(np.linalg.norm(coordinates - centroids[:, None, :], axis=2), axis=1)
    centroid_inside = contains_xy(influence, centroids[:, 0], centroids[:, 1])
    boundary_distances = distance(
        influence.boundary,
        points(centroids[:, 0], centroids[:, 1]),
    )
    # An interior disk of radius r around the centroid contains the complete face.
    # Faces outside this sufficient condition are checked exactly below.
    fully_inside = centroid_inside & (boundary_distances >= radii + 1e-10)
    exact_candidates = np.flatnonzero(centroid_inside & ~fully_inside)
    for offset, triangle_index in enumerate(exact_candidates):
        if offset % 1024 == 0 and deadline is not None and time.monotonic() >= deadline:
            raise RoadSurfacePatchError(
                "phase-I solver exceeded its wall-clock cap during exact influence checks"
            )
        fully_inside[triangle_index] = influence.covers(Polygon(coordinates[triangle_index]))
    return fully_inside


def _fixed_patch_vertices(
    mesh: PatchMesh, influence: Polygon | None, *, deadline: float | None = None
) -> np.ndarray:
    """Pin every vertex incident to a face that is not wholly inside influence."""
    if influence is None:
        return np.zeros(len(mesh.vertices_xz), dtype=bool)
    fixed = np.zeros(len(mesh.vertices_xz), dtype=bool)
    outside_triangles = ~_triangles_fully_within_influence(mesh, influence, deadline=deadline)
    fixed[np.unique(mesh.triangles[outside_triangles])] = True
    return fixed


def _build_flattened_warm_start(
    mesh: PatchMesh,
    inputs: ReleaseInputs,
    influence: Polygon | None = None,
    fixed_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Build a reversible smooth fade toward the unchanged source centerline profile."""
    feature = next(
        item
        for item in inputs.road_payload["features"]
        if item.get("source", {}).get("osmId") == TEIGNMOUTH_WAY_ID
    )
    part = [
        [float(point[0]), float(point[1])]
        for point in feature["centerlinePartsXZ"][TEIGNMOUTH_PART_INDEX]
    ]
    cumulative = [0.0]
    for first, second in zip(part, part[1:], strict=False):
        cumulative.append(cumulative[-1] + math.dist(first, second))

    def interpolate_station(station: float) -> tuple[float, float]:
        for index in range(len(part) - 1):
            if cumulative[index] <= station <= cumulative[index + 1]:
                dx = part[index + 1][0] - part[index][0]
                dz = part[index + 1][1] - part[index][1]
                fraction = (station - cumulative[index]) / (
                    cumulative[index + 1] - cumulative[index]
                )
                return (
                    part[index][0] + dx * fraction,
                    part[index][1] + dz * fraction,
                )
        raise RoadSurfacePatchError(f"station {station:g} is outside Teignmouth part 0")

    segment_points = [
        interpolate_station(TEIGNMOUTH_STATION_START_M),
        *[
            point
            for point, station in zip(part, cumulative, strict=True)
            if TEIGNMOUTH_STATION_START_M < station < TEIGNMOUTH_STATION_END_M
        ],
        interpolate_station(TEIGNMOUTH_STATION_END_M),
    ]
    if len(segment_points) < 2:
        raise RoadSurfacePatchError("cannot derive the registered Teignmouth warm-start segment")
    half_width = float(feature["estimatedWidthM"]) / 2
    values = mesh.base_y.astype(np.float64).copy()
    strengths = np.zeros(len(values), dtype=np.float64)
    for index, (x, z) in enumerate(mesh.vertices_xz):
        nearest = None
        for first, second in zip(segment_points, segment_points[1:], strict=False):
            dx, dz = second[0] - first[0], second[1] - first[1]
            length_squared = dx * dx + dz * dz
            fraction = min(
                1.0,
                max(0.0, ((x - first[0]) * dx + (z - first[1]) * dz) / length_squared),
            )
            candidate = (first[0] + fraction * dx, first[1] + fraction * dz)
            distance = math.hypot(x - candidate[0], z - candidate[1])
            record = (distance, candidate[0], candidate[1])
            if nearest is None or record < nearest:
                nearest = record
        assert nearest is not None
        distance, center_x, center_z = nearest
        transition_distance = max(0.0, distance - half_width)
        if transition_distance >= PATCH_MAX_TRANSITION_M:
            continue
        t = 1.0 - transition_distance / PATCH_MAX_TRANSITION_M
        strength = t * t * (3.0 - 2.0 * t)
        center_height = _sample_grid(inputs.baseline, center_x, center_z, inputs.spacing_m)
        values[index] += strength * (center_height - values[index])
        strengths[index] = strength
    if influence is not None:
        fixed = fixed_mask if fixed_mask is not None else _fixed_patch_vertices(mesh, influence)
        values[fixed] = mesh.base_y[fixed].astype(np.float64)
    else:
        fixed = np.zeros(len(values), dtype=bool)
    return values.astype(np.float64), {
        "method": "source-centerline profile with smoothstep fade from configured 6 m ribbon edge",
        "maximumTransitionDistanceM": PATCH_MAX_TRANSITION_M,
        "nonzeroStrengthVertexCount": int(np.count_nonzero(strengths)),
        "maximumStrength": float(np.max(strengths)),
        "fixedVertexCount": int(fixed.sum()),
    }


def _outside_influence_surface_report(
    mesh: PatchMesh,
    influence: Polygon,
    candidate: np.ndarray,
    fixed_mask: np.ndarray,
) -> dict[str, Any]:
    """Verify every face extending outside the influence reproduces accepted Float32 nodes."""
    triangle_outside = ~_triangles_fully_within_influence(mesh, influence)
    outside_triangles = mesh.triangles[triangle_outside]
    outside_vertex_ids = (
        np.unique(outside_triangles) if len(outside_triangles) else np.array([], dtype=int)
    )
    # Array-to-bytes is compared as one contiguous little-endian sequence for exactness.
    exact = (
        candidate[outside_vertex_ids].astype("<f4").tobytes()
        == mesh.base_y[outside_vertex_ids].astype("<f4").tobytes()
    )
    exact = exact and bool(fixed_mask[outside_vertex_ids].all())
    return {
        "tested": True,
        "outsideInfluenceTriangleCount": int(triangle_outside.sum()),
        "outsideInfluenceVertexCount": int(len(outside_vertex_ids)),
        "outsideInfluenceVerticesFixed": bool(fixed_mask[outside_vertex_ids].all()),
        "acceptedFloat32BytesPreserved": exact,
    }


def _validate_quantized_phase_one(
    mesh: PatchMesh | None,
    candidate: np.ndarray,
    source_nodes: np.ndarray,
    edges: np.ndarray,
    edge_limits: np.ndarray,
    constraints: list[dict[str, Any]],
    fixed_mask: np.ndarray,
    fixed_values: np.ndarray,
    influence: Polygon | None = None,
    solver_tolerance_m: float = 2e-5,
) -> dict[str, Any]:
    """Recheck Float32 halfspaces with solver tolerance and actual policy limits."""
    values = candidate.astype(np.float64)
    edge_lengths = (
        np.linalg.norm(mesh.vertices_xz[edges[:, 0]] - mesh.vertices_xz[edges[:, 1]], axis=1)
        if mesh is not None
        else np.empty(0, dtype=np.float64)
    )
    source_edge_deltas = np.abs(source_nodes[edges[:, 0]] - source_nodes[edges[:, 1]])
    edge_differences = np.abs(values[edges[:, 1]] - values[edges[:, 0]])
    target_edge_violations = edge_differences - edge_limits
    strict_edge_violations = edge_differences - (source_edge_deltas + edge_lengths)
    local_violations = np.asarray(
        [
            float(np.dot(item["coefficients"], values[item["indices"]]) - item["limitM"])
            for item in constraints
        ],
        dtype=np.float64,
    )
    actual_local_limits = np.asarray(
        [_actual_local_constraint_limit(item) for item in constraints],
        dtype=np.float64,
    )
    actual_local_violations = np.asarray(
        [
            float(np.dot(item["coefficients"], values[item["indices"]]) - actual_limit)
            for item, actual_limit in zip(constraints, actual_local_limits, strict=True)
        ],
        dtype=np.float64,
    )
    local_index = int(np.argmax(local_violations)) if len(local_violations) else None
    actual_local_index = (
        int(np.argmax(actual_local_violations)) if len(actual_local_violations) else None
    )
    edge_index = int(np.argmax(strict_edge_violations)) if len(strict_edge_violations) else None
    fixed_equal = (
        candidate[fixed_mask].tobytes() == fixed_values[fixed_mask].astype("<f4").tobytes()
    )
    outside_report = (
        _outside_influence_surface_report(mesh, influence, candidate, fixed_mask)
        if influence is not None and mesh is not None
        else {"tested": False, "reason": "patch mesh unavailable"}
        if influence is not None
        else {"tested": False, "reason": "no registered influence polygon supplied"}
    )
    maximum_absolute_change = float(np.max(np.abs(values - source_nodes)))
    edge_max = float(np.max(strict_edge_violations)) if len(strict_edge_violations) else -math.inf
    target_edge_max = (
        float(np.max(target_edge_violations)) if len(target_edge_violations) else -math.inf
    )
    local_max = float(np.max(local_violations)) if len(local_violations) else -math.inf
    actual_local_max = (
        float(np.max(actual_local_violations)) if len(actual_local_violations) else -math.inf
    )
    range_max = float(np.max(np.abs(values - source_nodes)))
    return {
        "passes": bool(
            np.isfinite(candidate).all()
            and local_max <= solver_tolerance_m
            and actual_local_max <= 0.0
            and target_edge_max <= solver_tolerance_m
            and edge_max < 0.0
            and maximum_absolute_change < 5.0
            and fixed_equal
            and (influence is None or outside_report["acceptedFloat32BytesPreserved"])
        ),
        "float32Finite": bool(np.isfinite(candidate).all()),
        "maximumLocalHalfspaceViolationM": local_max,
        "solverNumericalToleranceM": solver_tolerance_m,
        "solverLocalHalfspacesWithinTolerance": bool(local_max <= solver_tolerance_m),
        "maximumActualLocalAcceptanceViolationM": actual_local_max,
        "worstLocalConstraint": (
            {**constraints[local_index]["label"], "excessM": local_max}
            if local_index is not None
            else None
        ),
        "worstActualLocalConstraint": (
            {
                **constraints[actual_local_index]["label"],
                "excessM": actual_local_max,
            }
            if actual_local_index is not None
            else None
        ),
        "maximumMeshEdgeAddedGradientExcessM": edge_max,
        "maximumSolverHeadroomEdgeExcessM": target_edge_max,
        "solverHeadroomEdgeLimitsWithinTolerance": bool(target_edge_max <= solver_tolerance_m),
        "worstMeshEdge": (
            {
                "vertices": edges[edge_index].tolist(),
                "addedGradientExcessM": edge_max,
                "solverHeadroomExcessM": float(target_edge_violations[edge_index]),
            }
            if edge_index is not None
            else None
        ),
        "maximumAbsoluteSourceChangeM": maximum_absolute_change,
        "maximumAbsoluteSourceChangeLimitM": 5.0,
        "fixedVertexBytesMatch": fixed_equal,
        "fixedVertexCount": int(fixed_mask.sum()),
        "nodeBoundsMaximumM": range_max,
        "outsideInfluenceSurface": outside_report,
    }


def _actual_local_constraint_limit(constraint: dict[str, Any]) -> float:
    """Map tighter solve halfspaces to the amendment's unchanged inclusive gates."""
    kind = constraint["label"].get("kind")
    if kind == "teignmouth-local-crossfall":
        return PATCH_LATERAL_SLOPE * PATCH_LATERAL_SAMPLE_M
    if kind == "teignmouth-endpoint-span":
        return PATCH_MAX_ENDPOINT_SPAN_M
    if kind == "teignmouth-centerline-envelope":
        return constraint["limitM"] + (
            PATCH_MAX_CENTERLINE_DEVIATION_M - PATCH_CENTERLINE_TOLERANCE
        )
    if kind == "teignmouth-longitudinal-grade-delta":
        station_delta = constraint["label"]["stationEndM"] - constraint["label"]["stationStartM"]
        return (
            constraint["limitM"]
            + (PATCH_MAX_LONGITUDINAL_GRADE_DELTA - PATCH_LONGITUDINAL_GRADE_DELTA) * station_delta
        )
    if kind == "registered-full-way-centerline-envelope":
        return constraint["limitM"] + (
            PATCH_MAX_CENTERLINE_DEVIATION_M - PATCH_CENTERLINE_TOLERANCE
        )
    if kind == "registered-full-way-signed-grade-change":
        station_delta = constraint["label"]["stationEndM"] - constraint["label"]["stationStartM"]
        return (
            constraint["limitM"]
            + (PATCH_MAX_LONGITUDINAL_GRADE_DELTA - PATCH_LONGITUDINAL_GRADE_DELTA) * station_delta
        )
    return constraint["limitM"]
