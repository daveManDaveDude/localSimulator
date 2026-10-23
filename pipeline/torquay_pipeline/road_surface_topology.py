"""Deterministic constrained topology helpers for local road-surface patches.

The mesh is assembled from an explicitly noded planar line arrangement.  Source
triangles remain provenance regions only: a replacement face may overlap more
than one of them, and that relationship is retained in a spatial index.
"""

from __future__ import annotations

import math
import struct
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np
import shapely
from shapely import union_all
from shapely.geometry import LineString, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import polygonize
from shapely.strtree import STRtree


class TopologyError(ValueError):
    """Raised when a constrained local topology is invalid or ambiguous."""


@dataclass(frozen=True)
class PlanarMesh:
    """Stable local X/Z vertices and upward-facing indexed triangle faces."""

    vertices_xz: np.ndarray
    triangles: np.ndarray
    boundary_edges: tuple[tuple[int, int], ...]
    constraint_edges: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class SourceOverlap:
    """One patch-face overlap with an immutable source triangle."""

    source_id: int
    intersection_area_m2: float


@dataclass(frozen=True)
class SourceOverlapIndex:
    """Spatially indexed original triangles and their stable source identifiers."""

    geometries: tuple[Polygon, ...]
    source_ids: tuple[int, ...]
    vertices_xz: tuple[tuple[tuple[float, float], ...], ...]
    heights: tuple[tuple[float, float, float], ...] | None
    index_by_source_id: dict[int, int]
    tree: STRtree
    partition_verified: bool = False

    @classmethod
    def create(
        cls,
        triangles_xz: Sequence[Sequence[Sequence[float]]],
        source_ids: Sequence[int],
        source_heights: Sequence[Sequence[float]] | None = None,
        *,
        partition_verified: bool = False,
    ) -> SourceOverlapIndex:
        if len(triangles_xz) != len(source_ids) or not triangles_xz:
            raise TopologyError("source overlap index requires matching nonempty triangle IDs")
        if source_heights is not None and len(source_heights) != len(source_ids):
            raise TopologyError("source heights must match the source triangle IDs")
        ordered = []
        heights_by_id: dict[int, tuple[float, float, float]] = {}
        for index, (source_id, triangle) in enumerate(zip(source_ids, triangles_xz, strict=True)):
            if len(triangle) != 3 or any(len(point) != 2 for point in triangle):
                raise TopologyError("source provenance entries must be three X/Z vertices")
            coordinates = [(float(point[0]), float(point[1])) for point in triangle]
            if not all(math.isfinite(value) for point in coordinates for value in point):
                raise TopologyError("source provenance triangle contains nonfinite coordinates")
            key = int(source_id)
            ordered.append((key, Polygon(coordinates), tuple(coordinates)))
            if source_heights is not None:
                heights = tuple(float(value) for value in source_heights[index])
                if len(heights) != 3 or not all(math.isfinite(value) for value in heights):
                    raise TopologyError(
                        "source provenance heights must contain three finite values"
                    )
                heights_by_id[key] = heights
        ordered.sort(key=lambda item: item[0])
        ids = [item[0] for item in ordered]
        if len(set(ids)) != len(ids):
            raise TopologyError("source triangle IDs must be unique")
        geometries = tuple(item[1] for item in ordered)
        vertices_xz = tuple(item[2] for item in ordered)
        ordered_heights = (
            tuple(heights_by_id[source_id] for source_id in ids)
            if source_heights is not None
            else None
        )
        if any(
            not polygon.is_valid or polygon.is_empty or polygon.area <= 0.0
            for polygon in geometries
        ):
            raise TopologyError("source overlap index contains an invalid triangle")
        return cls(
            geometries,
            tuple(ids),
            vertices_xz,
            ordered_heights,
            {source_id: index for index, source_id in enumerate(ids)},
            STRtree(geometries),
            partition_verified,
        )

    @classmethod
    def from_grid(
        cls,
        heights: np.ndarray,
        *,
        width_m: float,
        depth_m: float,
        spacing_m: float,
        first_row: int,
        last_row: int,
        first_column: int,
        last_column: int,
    ) -> SourceOverlapIndex:
        """Index the two immutable source planes in each selected grid cell."""
        grid = np.asarray(heights, dtype=np.float64)
        if (
            grid.ndim != 2
            or not np.isfinite(grid).all()
            or spacing_m <= 0.0
            or first_row < 0
            or first_column < 0
            or last_row > grid.shape[0] - 1
            or last_column > grid.shape[1] - 1
            or first_row >= last_row
            or first_column >= last_column
        ):
            raise TopologyError("source grid overlap bounds or values are invalid")
        triangles: list[list[tuple[float, float]]] = []
        source_ids: list[int] = []
        triangle_heights: list[tuple[float, float, float]] = []
        for row in range(first_row, last_row):
            z0 = row * spacing_m - depth_m / 2.0
            z1 = z0 + spacing_m
            for column in range(first_column, last_column):
                x0 = column * spacing_m - width_m / 2.0
                x1 = x0 + spacing_m
                cell_id = row * (grid.shape[1] - 1) + column
                triangles.extend(
                    (
                        [(x0, z0), (x1, z0), (x0, z1)],
                        [(x1, z1), (x0, z1), (x1, z0)],
                    )
                )
                source_ids.extend((2 * cell_id, 2 * cell_id + 1))
                triangle_heights.extend(
                    (
                        (
                            float(grid[row, column]),
                            float(grid[row, column + 1]),
                            float(grid[row + 1, column]),
                        ),
                        (
                            float(grid[row + 1, column + 1]),
                            float(grid[row + 1, column]),
                            float(grid[row, column + 1]),
                        ),
                    )
                )
        return cls.create(
            triangles,
            source_ids,
            triangle_heights,
            partition_verified=True,
        )

    def overlaps(
        self, face: Polygon, *, area_tolerance_m2: float = 1e-12
    ) -> tuple[SourceOverlap, ...]:
        """Return sorted positive-area source overlaps for one replacement face."""
        if face.is_empty or not face.is_valid or face.area <= 0.0:
            raise TopologyError("replacement face is invalid or degenerate")
        candidates = sorted(int(index) for index in self.tree.query(face, predicate="intersects"))
        rows: list[SourceOverlap] = []
        intersections = []
        for index in candidates:
            intersection = face.intersection(self.geometries[index])
            area = float(intersection.area)
            if area > area_tolerance_m2:
                rows.append(SourceOverlap(self.source_ids[index], area))
                if not self.partition_verified:
                    intersections.append(intersection)
        covered_area = math.fsum(row.intersection_area_m2 for row in rows)
        tolerance = max(area_tolerance_m2, face.area * 1e-10)
        if self.partition_verified:
            if abs(covered_area - float(face.area)) > tolerance:
                raise TopologyError(
                    "replacement face is not fully covered by the verified source partition: "
                    f"faceArea={face.area:.17g}, coveredArea={covered_area:.17g}"
                )
            return tuple(sorted(rows, key=lambda row: row.source_id))
        covered_geometry = union_all(intersections) if intersections else Polygon()
        missing_area = float(face.difference(covered_geometry).area)
        overlap_area = max(0.0, covered_area - float(covered_geometry.area))
        if missing_area > tolerance or overlap_area > tolerance:
            raise TopologyError(
                "replacement face is not fully covered by source provenance triangles: "
                f"faceArea={face.area:.17g}, coveredArea={covered_area:.17g}, "
                f"missingArea={missing_area:.17g}, overlapArea={overlap_area:.17g} m²"
            )
        return tuple(sorted(rows, key=lambda row: row.source_id))

    def sample_height(self, source_id: int, x: float, z: float) -> float:
        """Sample one original source triangle's plane by stable provenance ID."""
        if self.heights is None:
            raise TopologyError("source heights were not bound to this provenance index")
        try:
            index = self.index_by_source_id[int(source_id)]
        except KeyError as exc:
            raise TopologyError(f"source triangle {source_id} is not indexed") from exc
        triangle = np.asarray(self.vertices_xz[index], dtype=np.float64)
        values = np.asarray(self.heights[index], dtype=np.float64)
        matrix = np.column_stack((triangle[1] - triangle[0], triangle[2] - triangle[0]))
        try:
            tail = np.linalg.solve(matrix, np.asarray((x, z), dtype=np.float64) - triangle[0])
        except np.linalg.LinAlgError as exc:
            raise TopologyError(f"source triangle {source_id} is degenerate") from exc
        weights = np.asarray((1.0 - tail.sum(), tail[0], tail[1]))
        if np.min(weights) < -1e-9 or np.max(weights) > 1.0 + 1e-9:
            raise TopologyError(f"point ({x:g}, {z:g}) is outside source triangle {source_id}")
        return float(np.dot(weights, values))


def _f32(value: float) -> float:
    converted = np.float32(value)
    if not np.isfinite(converted):
        raise TopologyError(f"coordinate is not representable as finite Float32: {value!r}")
    result = float(converted)
    return 0.0 if result == 0.0 else result


def _coordinate_key(x: float, z: float) -> tuple[float, float]:
    return _f32(x), _f32(z)


def _float32_bytes(x: float, z: float) -> bytes:
    return struct.pack("<ff", _f32(x), _f32(z))


def _face_edges(polygon: Polygon) -> set[tuple[tuple[float, float], tuple[float, float]]]:
    edges = set()
    for ring in (polygon.exterior, *polygon.interiors):
        coordinates = [(float(x), float(z)) for x, z in list(ring.coords)[:-1]]
        edges.update(
            tuple(sorted((first, second)))
            for first, second in zip(coordinates, coordinates[1:] + coordinates[:1], strict=True)
        )
    return edges


def _line_geometries(lines: Iterable[LineString]) -> list[LineString]:
    output: list[LineString] = []
    for line in lines:
        if not isinstance(line, LineString) or line.is_empty or not line.is_valid:
            raise TopologyError("constraint arrangement contains an invalid line")
        if line.length <= 0.0:
            raise TopologyError("constraint arrangement contains a zero-length line")
        output.append(line)
    return output


def _line_parts(geometry: object) -> list[LineString]:
    """Flatten lineal geometry without changing its coordinates or order."""
    geometry_type = getattr(geometry, "geom_type", "")
    if geometry_type == "LineString":
        line = geometry  # type: ignore[assignment]
        return [line] if line.is_valid and line.length > 1e-12 else []  # type: ignore[attr-defined]
    if geometry_type in ("MultiLineString", "GeometryCollection"):
        return [part for child in geometry.geoms for part in _line_parts(child)]  # type: ignore[attr-defined]
    return []


def _position_tangent(
    line: LineString, stations_m: Sequence[float]
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Interpolate a polyline station and its deterministic forward tangent."""
    coordinates = [(float(x), float(z)) for x, z in line.coords]
    lengths = [
        math.dist(first, second)
        for first, second in zip(coordinates, coordinates[1:], strict=False)
    ]
    cumulative = [0.0]
    for length in lengths:
        cumulative.append(cumulative[-1] + length)
    if not all(math.isfinite(value) and value >= 0.0 for value in stations_m):
        raise TopologyError("road-normal station list must be finite and nonnegative")
    output = []
    for station in stations_m:
        if station > cumulative[-1] + 1e-9:
            raise TopologyError(f"road-normal station {station:g} exceeds line length")
        index = min(
            len(lengths) - 1, max(0, int(np.searchsorted(cumulative, station, side="right") - 1))
        )
        length = lengths[index]
        if length <= 0.0:
            raise TopologyError("road-normal centerline contains a zero-length segment")
        fraction = min(1.0, max(0.0, (station - cumulative[index]) / length))
        first, second = coordinates[index], coordinates[index + 1]
        tangent = ((second[0] - first[0]) / length, (second[1] - first[1]) / length)
        point = (
            first[0] + fraction * (second[0] - first[0]),
            first[1] + fraction * (second[1] - first[1]),
        )
        output.append((point, tangent))
    return output


def road_aligned_constraints(
    centerline_xz: Sequence[Sequence[float]],
    *,
    width_m: float,
    station_spacing_m: float = 0.5,
    lateral_spacing_m: float = 0.5,
    domain: Polygon | None = None,
) -> tuple[LineString, ...]:
    """Build a pinned ribbon, centerline and normal sections for a road-aligned mesh.

    The normal section endpoints span the supplied configured width. At sharp bends,
    section intersections are left for the common noding step to resolve explicitly.
    """
    coordinates = [(float(point[0]), float(point[1])) for point in centerline_xz]
    line = LineString(coordinates)
    if (
        line.is_empty
        or not line.is_valid
        or line.length <= 0.0
        or width_m <= 0.0
        or station_spacing_m <= 0.0
        or lateral_spacing_m <= 0.0
        or not all(math.isfinite(value) for point in coordinates for value in point)
    ):
        raise TopologyError("road-aligned topology inputs must be finite nonzero geometry")
    stations = [float(value) for value in np.arange(0.0, line.length, station_spacing_m)]
    stations.append(float(line.length))
    stations = sorted(set(stations))
    sections: list[LineString] = []
    offsets = [float(value) for value in np.arange(-width_m / 2, width_m / 2, lateral_spacing_m)]
    offsets.extend((-width_m / 2, width_m / 2))
    offsets = sorted(set(offsets))
    ribbon = line.buffer(width_m / 2, cap_style="flat", join_style="mitre")
    if ribbon.is_empty or not ribbon.is_valid or ribbon.area <= 0.0:
        raise TopologyError("configured road ribbon is invalid")
    for (x, z), (tangent_x, tangent_z) in _position_tangent(line, stations):
        normal_x, normal_z = -tangent_z, tangent_x
        section_points = [(x + normal_x * offset, z + normal_z * offset) for offset in offsets]
        for first, second in zip(section_points, section_points[1:], strict=False):
            sections.extend(_line_parts(LineString((first, second)).intersection(ribbon)))
    lines = [line, *_line_parts(ribbon.boundary), *sections]
    if domain is not None:
        clipped = []
        for constraint in lines:
            clipped.extend(_line_parts(constraint.intersection(domain)))
        lines = clipped
    return tuple(lines)


def localized_refinement_zone(
    centerline_xz: Sequence[Sequence[float]],
    *,
    width_m: float,
    source_cell_spacing_m: float,
    influence: Polygon,
) -> Polygon:
    """Select the entire configured ribbon plus one source cell, within influence."""
    line = LineString([(float(x), float(z)) for x, z in centerline_xz])
    if (
        line.is_empty
        or not line.is_valid
        or line.length <= 0.0
        or width_m <= 0.0
        or source_cell_spacing_m <= 0.0
        or influence.is_empty
        or not influence.is_valid
    ):
        raise TopologyError(
            "localized refinement requires valid line, influence and positive sizes"
        )
    target_radius = width_m / 2.0 + source_cell_spacing_m
    zone = line.buffer(target_radius, cap_style="flat", join_style="mitre").intersection(influence)
    if zone.is_empty or not zone.is_valid or zone.area <= 0.0:
        raise TopologyError("localized refinement zone is empty or invalid")
    return zone


def localized_grid_constraints(region: Polygon, spacing_m: float) -> tuple[LineString, ...]:
    """Return deterministic axis-aligned refinement lines clipped to a valid zone."""
    if (
        not isinstance(region, Polygon)
        or region.is_empty
        or not region.is_valid
        or region.area <= 0.0
        or not math.isfinite(spacing_m)
        or spacing_m <= 0.0
    ):
        raise TopologyError("localized refinement grid requires a valid polygon and spacing")
    min_x, min_z, max_x, max_z = region.bounds
    first_x = math.ceil((min_x - 1e-10) / spacing_m) * spacing_m
    first_z = math.ceil((min_z - 1e-10) / spacing_m) * spacing_m
    lines: list[LineString] = []
    for x in np.arange(first_x, max_x + spacing_m * 1e-9, spacing_m):
        lines.extend(
            _line_parts(
                LineString(
                    ((float(x), min_z - spacing_m), (float(x), max_z + spacing_m))
                ).intersection(region)
            )
        )
    for z in np.arange(first_z, max_z + spacing_m * 1e-9, spacing_m):
        lines.extend(
            _line_parts(
                LineString(
                    ((min_x - spacing_m, float(z)), (max_x + spacing_m, float(z)))
                ).intersection(region)
            )
        )
    return tuple(
        sorted(
            lines,
            key=lambda line: tuple((float(x), float(z)) for x, z in line.coords),
        )
    )


def graded_collar_constraints(
    centerline_xz: Sequence[Sequence[float]],
    *,
    width_m: float,
    collar_steps_m: Sequence[float] = (0.5, 1.0, 2.0),
    domain: Polygon | None = None,
) -> tuple[LineString, ...]:
    """Return deterministic nested boundaries for a graded conforming road collar."""
    line = LineString([(float(x), float(z)) for x, z in centerline_xz])
    if line.is_empty or not line.is_valid or line.length <= 0.0 or width_m <= 0.0:
        raise TopologyError("collar topology requires a finite road line and positive width")
    steps = tuple(float(value) for value in collar_steps_m)
    if (
        not steps
        or any(not math.isfinite(value) or value <= 0.0 for value in steps)
        or tuple(sorted(set(steps))) != steps
    ):
        raise TopologyError("collar distances must be finite, positive, unique and increasing")
    road_ribbon = line.buffer(width_m / 2, cap_style="flat", join_style="mitre")
    lines = []
    for distance_m in steps:
        offset = road_ribbon.buffer(distance_m, cap_style="flat", join_style="mitre")
        if offset.is_empty or not offset.is_valid:
            raise TopologyError(f"road collar at {distance_m:g} m is invalid")
        lines.extend(_line_parts(offset.boundary))
    if domain is not None:
        lines = [
            clipped for linework in lines for clipped in _line_parts(linework.intersection(domain))
        ]
    return tuple(lines)


def _polygon_sort_key(polygon: Polygon) -> tuple[float, float, float, float, float, bytes]:
    return (*map(float, polygon.bounds), float(polygon.area), polygon.normalize().wkb)


def _noded_faces(domain: Polygon, constraints: Iterable[LineString]) -> tuple[Polygon, ...]:
    if domain.is_empty or not domain.is_valid or domain.area <= 0.0:
        raise TopologyError("topology domain must be a valid positive-area polygon")
    clipped: list[LineString] = []
    for line in _line_geometries(constraints):
        intersection = line.intersection(domain)
        if intersection.is_empty:
            continue
        if intersection.geom_type == "LineString":
            clipped.append(intersection)
        elif intersection.geom_type == "MultiLineString":
            clipped.extend(intersection.geoms)
        else:
            # Point-only contacts do not add a planar constraint edge.
            continue

    # unary_union nodes all proper and endpoint intersections before polygonizing.
    noded = shapely.union_all([domain.boundary, *clipped])
    faces = [
        face
        for face in polygonize(noded)
        if face.area > 0.0 and domain.covers(face.representative_point())
    ]
    faces.sort(key=_polygon_sort_key)
    face_edges = set().union(*(_face_edges(face) for face in faces))
    noded_edges: set[tuple[tuple[float, float], tuple[float, float]]] = set()

    def collect_edges(geometry: object) -> None:
        geometry_type = getattr(geometry, "geom_type", "")
        if geometry_type == "LineString":
            coordinates = [(float(x), float(z)) for x, z in geometry.coords]  # type: ignore[attr-defined]
            noded_edges.update(
                tuple(sorted((first, second)))
                for first, second in zip(coordinates, coordinates[1:], strict=False)
            )
        elif hasattr(geometry, "geoms"):
            for child in geometry.geoms:  # type: ignore[attr-defined]
                collect_edges(child)

    collect_edges(noded)
    missing_edges = noded_edges - face_edges
    if missing_edges:
        raise TopologyError(
            "noded constraint arrangement contains edges not represented by polygon faces: "
            f"{sorted(missing_edges)[:8]}"
        )
    total_area = math.fsum(float(face.area) for face in faces)
    tolerance = max(1e-10, float(domain.area) * 1e-12)
    if not faces or abs(total_area - float(domain.area)) > tolerance:
        raise TopologyError(
            "noded constraint arrangement does not partition the complete domain: "
            f"domainArea={domain.area:.17g}, faceArea={total_area:.17g}, "
            f"difference={total_area - domain.area:.17g} m²"
        )
    return tuple(faces)


def build_constrained_mesh(domain: Polygon, constraints: Iterable[LineString]) -> PlanarMesh:
    """Node constraint lines, polygonize their faces, then constrained-triangulate them.

    Shapely's constrained Delaunay operation is applied to each polygon face, so
    every noded arrangement edge is a face boundary and must remain a triangle
    edge. Coordinates are keyed by actual Float32 X/Z values before serialization.
    """
    linework = _line_geometries(constraints)
    faces = _noded_faces(domain, linework)
    keyed_faces: list[tuple[tuple[float, float], ...]] = []
    construction_by_key: dict[bytes, tuple[float, float]] = {}
    construction_by_exact: dict[tuple[float, float], bytes] = {}
    triangulated_faces = shapely.constrained_delaunay_triangles(np.asarray(faces, dtype=object))
    for face, triangulated in zip(faces, triangulated_faces, strict=True):
        face_area = math.fsum(float(triangle.area) for triangle in triangulated.geoms)
        tolerance = max(1e-10, float(face.area) * 1e-12)
        if abs(face_area - float(face.area)) > tolerance:
            raise TopologyError("constrained triangulation does not cover a noded polygon face")
        face_boundary_edges = _face_edges(face)
        triangle_edges: set[tuple[tuple[float, float], tuple[float, float]]] = set()
        for triangle in triangulated.geoms:
            coordinates = [(float(x), float(z)) for x, z in list(triangle.exterior.coords)[:-1]]
            if len(coordinates) != 3:
                raise TopologyError("constrained Delaunay operation returned a nontriangle face")
            # Shapely returns CCW rings; the terrain's positive-Y winding in X/Z is clockwise.
            area2 = (coordinates[1][0] - coordinates[0][0]) * (
                coordinates[2][1] - coordinates[0][1]
            ) - (coordinates[1][1] - coordinates[0][1]) * (coordinates[2][0] - coordinates[0][0])
            if area2 == 0.0 or not math.isfinite(area2):
                raise TopologyError("constrained triangulation contains a degenerate face")
            if area2 > 0.0:
                coordinates.reverse()
            for point in coordinates:
                key = _float32_bytes(*point)
                exact = (point[0], point[1])
                previous = construction_by_key.get(key)
                if previous is not None and previous != exact:
                    raise TopologyError(
                        "distinct Float64 topology vertices collide after Float32 conversion: "
                        f"{previous!r} and {exact!r}"
                    )
                construction_by_key[key] = exact
                construction_by_exact[exact] = key
            keyed_faces.append(tuple(coordinates))
            triangle_edges.update(
                tuple(sorted((first, second)))
                for first, second in zip(
                    coordinates, coordinates[1:] + coordinates[:1], strict=True
                )
            )
        missing = face_boundary_edges - triangle_edges
        if missing:
            raise TopologyError(
                "constrained triangulation omitted noded arrangement boundary edges: "
                f"{sorted(missing)[:8]}"
            )

    ordered_exact = sorted(construction_by_exact, key=lambda point: _float32_bytes(*point))
    vertex_ids = {point: index for index, point in enumerate(ordered_exact)}
    vertices = np.asarray(ordered_exact, dtype=np.float64)
    triangles = np.asarray(
        [[vertex_ids[point] for point in face] for face in keyed_faces], dtype=np.uint32
    )
    triangles = _stable_orient_and_sort(vertices, triangles)
    edge_counts: dict[tuple[int, int], int] = {}
    for triangle in triangles:
        for first, second in (
            (triangle[0], triangle[1]),
            (triangle[1], triangle[2]),
            (triangle[2], triangle[0]),
        ):
            edge = tuple(sorted((int(first), int(second))))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
    if any(count not in (1, 2) for count in edge_counts.values()):
        raise TopologyError("constrained mesh has a nonmanifold or duplicate edge")
    boundary_edges = tuple(sorted(edge for edge, count in edge_counts.items() if count == 1))
    expected_boundary_edges = set()
    for face in faces:
        for first, second in _face_edges(face):
            if domain.boundary.covers(LineString((first, second))):
                expected_boundary_edges.add(tuple(sorted((vertex_ids[first], vertex_ids[second]))))
    if set(boundary_edges) != expected_boundary_edges:
        missing = sorted(expected_boundary_edges - set(boundary_edges))[:8]
        unexpected = sorted(set(boundary_edges) - expected_boundary_edges)[:8]
        raise TopologyError(
            "constrained mesh boundary does not match the domain rings: "
            f"missing={missing}, unexpected={unexpected}"
        )
    expected_arrangement_edges = set()
    for face in faces:
        for first, second in _face_edges(face):
            expected_arrangement_edges.add(tuple(sorted((vertex_ids[first], vertex_ids[second]))))
    all_edges = set(edge_counts)
    if not expected_arrangement_edges.issubset(all_edges):
        missing = sorted(expected_arrangement_edges - all_edges)[:8]
        raise TopologyError(f"noded constraint edges are absent from triangulation: {missing}")
    constraint_edges = tuple(sorted(all_edges & expected_arrangement_edges))
    return PlanarMesh(vertices, triangles, boundary_edges, constraint_edges)


def _stable_orient_and_sort(vertices: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """Use stable Float32 vertex order and clockwise X/Z faces for upward normals."""
    output: list[tuple[int, int, int]] = []
    for triangle in triangles:
        ids = [int(value) for value in triangle]
        points = vertices[ids].astype(np.float32).astype(np.float64)
        area2 = (points[1, 0] - points[0, 0]) * (points[2, 1] - points[0, 1]) - (
            points[1, 1] - points[0, 1]
        ) * (points[2, 0] - points[0, 0])
        if not math.isfinite(float(area2)) or area2 == 0.0:
            raise TopologyError("Float32 topology contains a zero-area or nonfinite triangle")
        if area2 > 0.0:
            ids[1], ids[2] = ids[2], ids[1]
        # Rotate the smallest vertex ID to the first slot without changing winding.
        smallest = ids.index(min(ids))
        ids = ids[smallest:] + ids[:smallest]
        output.append(tuple(ids))
    output.sort(key=lambda item: tuple(sorted(item)))
    if len(set(tuple(sorted(face)) for face in output)) != len(output):
        raise TopologyError("constrained triangulation produced duplicate faces")
    return np.asarray(output, dtype=np.uint32)


def mesh_face_polygon(mesh: PlanarMesh, face_id: int) -> Polygon:
    """Return a stable polygon view of a canonical indexed face."""
    face = mesh.triangles[face_id].astype(np.int64)
    return Polygon(mesh.vertices_xz[face])


def alternate_internal_diagonals(mesh: PlanarMesh, influence: Polygon) -> tuple[PlanarMesh, int]:
    """Flip a deterministic, nonadjacent set of unconstrained faces inside influence.

    Every source vertex, boundary edge and arrangement constraint is retained. The
    flip only changes connectivity where the complete convex two-face quad is covered
    by the supplied deformation influence.
    """
    if influence.is_empty or not influence.is_valid:
        raise TopologyError("diagonal flip influence must be valid polygon geometry")
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for face_id, triangle in enumerate(mesh.triangles):
        for first, second in (
            (int(triangle[0]), int(triangle[1])),
            (int(triangle[1]), int(triangle[2])),
            (int(triangle[2]), int(triangle[0])),
        ):
            edge_faces.setdefault(tuple(sorted((first, second))), []).append(face_id)
    constrained = {tuple(sorted(edge)) for edge in mesh.constraint_edges}
    candidates = []
    for edge, face_ids in edge_faces.items():
        if edge in constrained or len(face_ids) != 2:
            continue
        first_face, second_face = (mesh.triangles[index].astype(np.int64) for index in face_ids)
        first_opposites = set(map(int, first_face)) - set(edge)
        second_opposites = set(map(int, second_face)) - set(edge)
        if len(first_opposites) != 1 or len(second_opposites) != 1:
            continue
        opposite_first, opposite_second = first_opposites.pop(), second_opposites.pop()
        if opposite_first == opposite_second:
            continue
        quad_ids = [edge[0], opposite_first, edge[1], opposite_second]
        quad_points = mesh.vertices_xz[np.asarray(quad_ids, dtype=np.int64)]
        center = np.mean(quad_points, axis=0)
        order = np.argsort(np.arctan2(quad_points[:, 1] - center[1], quad_points[:, 0] - center[0]))
        ordered_ids = [quad_ids[int(index)] for index in order]
        quad = Polygon(mesh.vertices_xz[np.asarray(ordered_ids, dtype=np.int64)])
        if (
            not quad.is_valid
            or not quad.equals(quad.convex_hull)
            or len(list(quad.exterior.coords)) != 5
            or abs(
                quad.area
                - math.fsum(
                    Polygon(mesh.vertices_xz[mesh.triangles[index]]).area for index in face_ids
                )
            )
            > max(1e-12, quad.area * 1e-12)
            or not influence.covers(quad)
        ):
            continue
        ordered_points = mesh.vertices_xz[np.asarray(ordered_ids, dtype=np.int64)]
        turns = []
        for index in range(4):
            first = ordered_points[(index + 1) % 4] - ordered_points[index]
            second = ordered_points[(index + 2) % 4] - ordered_points[(index + 1) % 4]
            turns.append(float(first[0] * second[1] - first[1] * second[0]))
        if any(abs(turn) <= 1e-12 for turn in turns) or not (
            all(turn > 0.0 for turn in turns) or all(turn < 0.0 for turn in turns)
        ):
            continue
        new_edge = tuple(sorted((opposite_first, opposite_second)))
        if new_edge in edge_faces:
            continue
        candidates.append(
            (edge, tuple(face_ids), opposite_first, opposite_second, tuple(ordered_ids))
        )

    # Stable greedy selection ensures no two flips reuse a face. Alternating the
    # sorted candidate sequence changes enough local connectivity to form a useful
    # sensitivity trial while retaining every original lattice vertex.
    selected = []
    used_faces: set[int] = set()
    for candidate_index, candidate in enumerate(sorted(candidates)):
        edge, face_ids, opposite_first, opposite_second, ordered_ids = candidate
        if candidate_index % 2 == 1 or used_faces.intersection(face_ids):
            continue
        selected.append(candidate)
        used_faces.update(face_ids)
    output = mesh.triangles.astype(np.int64).copy()
    for edge, face_ids, first_opposite, second_opposite, _ordered_ids in selected:
        output[face_ids[0]] = (edge[0], first_opposite, second_opposite)
        output[face_ids[1]] = (edge[1], second_opposite, first_opposite)
    output = _stable_orient_and_sort(mesh.vertices_xz, output.astype(np.uint32))
    counts: dict[tuple[int, int], int] = {}
    for face in output:
        for first, second in (
            (int(face[0]), int(face[1])),
            (int(face[1]), int(face[2])),
            (int(face[2]), int(face[0])),
        ):
            edge = tuple(sorted((first, second)))
            counts[edge] = counts.get(edge, 0) + 1
    if any(count not in (1, 2) for count in counts.values()):
        raise TopologyError("alternate diagonal topology is nonmanifold")
    boundary = tuple(sorted(edge for edge, count in counts.items() if count == 1))
    if boundary != tuple(sorted(mesh.boundary_edges)):
        raise TopologyError("alternate diagonal topology changed the fixed boundary")
    if not constrained.issubset(counts):
        raise TopologyError("alternate diagonal topology removed a pinned arrangement edge")
    return (
        PlanarMesh(mesh.vertices_xz.copy(), output, boundary, mesh.constraint_edges),
        len(selected),
    )


def source_overlap_provenance(
    mesh: PlanarMesh,
    source_index: SourceOverlapIndex,
    *,
    area_tolerance_m2: float = 1e-12,
) -> tuple[tuple[SourceOverlap, ...], ...]:
    """Return immutable source provenance for every local face in stable order."""
    return tuple(
        source_index.overlaps(mesh_face_polygon(mesh, face_id), area_tolerance_m2=area_tolerance_m2)
        for face_id in range(len(mesh.triangles))
    )


def affine_surface_overlay_extrema(
    mesh: PlanarMesh,
    candidate_heights: Sequence[float],
    source_index: SourceOverlapIndex,
    *,
    clip_geometry: BaseGeometry | None = None,
    area_tolerance_m2: float = 1e-12,
) -> dict[str, float | int]:
    """Measure affine candidate-minus-source extrema on every overlap polygon.

    Both surfaces are planar on each patch/source triangle pair, so their
    difference reaches its extrema at the vertices of each clipped overlay.
    """
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
    source_plane_coefficients = tuple(
        _plane_coefficients(
            np.asarray(source_index.vertices_xz[index], dtype=np.float64),
            np.asarray(source_index.heights[index], dtype=np.float64),
        )
        for index in range(len(source_index.source_ids))
    )
    for face_id, face in enumerate(mesh.triangles):
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


def _polygon_parts(geometry: object) -> list[Polygon]:
    geometry_type = getattr(geometry, "geom_type", "")
    if geometry_type == "Polygon":
        return [geometry]  # type: ignore[list-item]
    if hasattr(geometry, "geoms"):
        return [polygon for child in geometry.geoms for polygon in _polygon_parts(child)]  # type: ignore[attr-defined]
    return []


def _linear_height(triangle_xz: np.ndarray, triangle_y: np.ndarray, x: float, z: float) -> float:
    matrix = np.column_stack((triangle_xz[1] - triangle_xz[0], triangle_xz[2] - triangle_xz[0]))
    try:
        tail = np.linalg.solve(matrix, np.asarray((x, z), dtype=np.float64) - triangle_xz[0])
    except np.linalg.LinAlgError as exc:
        raise TopologyError("cannot interpolate a degenerate source or patch triangle") from exc
    return float(np.dot((1.0 - tail.sum(), tail[0], tail[1]), triangle_y))


def _plane_coefficients(triangle_xz: np.ndarray, triangle_y: np.ndarray) -> np.ndarray:
    matrix = np.column_stack((triangle_xz[:, 0], triangle_xz[:, 1], np.ones(3)))
    try:
        return np.linalg.solve(matrix, triangle_y)
    except np.linalg.LinAlgError as exc:
        raise TopologyError("cannot interpolate a degenerate source or patch triangle") from exc
