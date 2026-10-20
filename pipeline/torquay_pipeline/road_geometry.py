"""Buffer clipped OSM lines and tessellate ribbons on the fixed terrain triangles."""

from __future__ import annotations

import math
import struct
from collections import defaultdict
from typing import Any

from shapely import Geometry, constrained_delaunay_triangles, get_parts
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from .config import AoiConfig
from .road_config import RoadConfig


class RoadGeometryError(ValueError):
    """Raised when a source line or draped surface cannot be represented safely."""


DISPLAY_GROUPS = ("vehicular", "cycleway", "path")
GROUP_PRIORITY = {"vehicular": 0, "cycleway": 1, "path": 2}
FLOAT32_SLIVER_MAX_AREA_M2 = 1e-6
CURRENT_2KM_FLOAT32_SLIVER_MAX_AREA_M2 = 2e-5
FLOAT32_SLIVER_POLICY = (
    "Cull triangles only when fewer than three distinct [x,z] coordinates remain after "
    "Float32 conversion; report the count and omitted area, bounded to 1e-6 m2."
)
CURRENT_2KM_FLOAT32_SLIVER_POLICY = (
    "Cull triangles only when fewer than three distinct [x,z] coordinates remain after "
    "Float32 conversion; report the count and omitted area, bounded to 2e-5 m2 for the "
    "expanded current_2km network."
)


def float32_sliver_policy(maximum_omitted_area_m2: float) -> str:
    if maximum_omitted_area_m2 == FLOAT32_SLIVER_MAX_AREA_M2:
        return FLOAT32_SLIVER_POLICY
    if maximum_omitted_area_m2 == CURRENT_2KM_FLOAT32_SLIVER_MAX_AREA_M2:
        return CURRENT_2KM_FLOAT32_SLIVER_POLICY
    raise ValueError("unsupported Float32 road sliver omission budget")


def _polygon_parts(geometry: Geometry) -> list[Polygon]:
    if geometry.is_empty:
        return []
    if isinstance(geometry, Polygon):
        return [geometry]
    if hasattr(geometry, "geoms"):
        return [part for child in geometry.geoms for part in _polygon_parts(child)]
    return []


def _signed_area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    origin_x, origin_z = points[0]
    return (
        sum(
            (points[index][0] - origin_x) * (points[(index + 1) % len(points)][1] - origin_z)
            - (points[(index + 1) % len(points)][0] - origin_x) * (points[index][1] - origin_z)
            for index in range(len(points))
        )
        / 2
    )


def _canonical_polygons(geometry: Geometry) -> list[Polygon]:
    polygons = _polygon_parts(geometry)
    if any(not polygon.is_valid or not math.isfinite(polygon.area) for polygon in polygons):
        raise RoadGeometryError("buffered or clipped road surface is invalid or non-finite")
    polygons = [polygon for polygon in polygons if polygon.area > 0]
    polygons.sort(key=lambda polygon: (tuple(polygon.bounds), polygon.wkb_hex))
    return polygons


def _local_aoi(aoi: AoiConfig) -> Polygon:
    center_e, center_n = aoi.center_bng_m
    west, south, east, north = aoi.bbox_m
    bounds = (west - center_e, center_n - north, east - center_e, center_n - south)
    if any(not math.isfinite(value) for value in bounds):
        raise RoadGeometryError("local AOI bounds must be finite")
    return box(*bounds)


def build_display_polygons(
    features: list[dict[str, Any]], aoi: AoiConfig, config: RoadConfig
) -> tuple[dict[str, Geometry], dict[str, float]]:
    """Buffer source lines, exact-clip, then partition overlaps by display priority."""
    area_of_interest = _local_aoi(aoi)
    source_surfaces: dict[str, list[Geometry]] = defaultdict(list)
    for feature in features:
        try:
            line = LineString(feature["sourceCenterlineXZ"])
            width = float(feature["estimatedWidthM"])
            group = feature["displayGroup"]
        except (KeyError, TypeError, ValueError) as exc:
            raise RoadGeometryError(
                f"{feature.get('id', 'road')}: malformed source line metadata"
            ) from exc
        if group not in DISPLAY_GROUPS or not math.isfinite(width) or width <= 0:
            raise RoadGeometryError(f"{feature['id']}: display group or estimated width is invalid")
        if not line.is_valid or line.length <= 0:
            raise RoadGeometryError(
                f"{feature['id']}: source centerline is invalid or has zero length"
            )
        ribbon = line.buffer(
            width / 2,
            quad_segs=1,
            cap_style="flat",
            join_style="bevel",
            mitre_limit=2.0,
        )
        if not ribbon.is_valid or ribbon.area <= 0:
            raise RoadGeometryError(f"{feature['id']}: configured buffer produced invalid geometry")
        clipped = ribbon.intersection(area_of_interest)
        if clipped.is_empty:
            continue
        if not clipped.is_valid:
            raise RoadGeometryError(f"{feature['id']}: AOI-clipped ribbon is invalid")
        components = _canonical_polygons(clipped)
        area = sum(float(component.area) for component in components)
        if area < config.minimum_ribbon_area_m2:
            feature["ribbonAreaM2"] = area
            feature["ribbonExcludedReason"] = "below_minimum_ribbon_area"
            continue
        feature["ribbonAreaM2"] = area
        feature["ribbonPartIds"] = [
            f"{feature['id']}/ribbon/{index:03d}" for index in range(len(components))
        ]
        source_surfaces[group].extend(components)

    unions: dict[str, Geometry] = {}
    for group in DISPLAY_GROUPS:
        pieces = source_surfaces.get(group, [])
        union = unary_union(pieces) if pieces else Polygon()
        if not union.is_empty and (not union.is_valid or not math.isfinite(union.area)):
            raise RoadGeometryError(f"union for display group {group!r} is invalid")
        unions[group] = union

    visible: dict[str, Geometry] = {}
    occupied: Geometry = Polygon()
    areas: dict[str, float] = {}
    for group in DISPLAY_GROUPS:
        candidate = unions[group]
        rendered = (
            candidate.difference(occupied)
            if not candidate.is_empty and not occupied.is_empty
            else candidate
        )
        if not rendered.is_empty and not rendered.is_valid:
            raise RoadGeometryError(f"priority partition for {group!r} is invalid")
        visible[group] = rendered
        areas[group] = float(rendered.area)
        if not candidate.is_empty:
            occupied = unary_union([occupied, candidate]) if not occupied.is_empty else candidate
    return visible, areas


def _terrain_triangle(
    row: int, column: int, triangle: int, spacing: float, half_width: float, half_depth: float
) -> Polygon:
    x0 = column * spacing - half_width
    x1 = (column + 1) * spacing - half_width
    z0 = row * spacing - half_depth
    z1 = (row + 1) * spacing - half_depth
    a, b, c, d = (x0, z0), (x1, z0), (x0, z1), (x1, z1)
    return Polygon((a, c, b) if triangle == 0 else (b, c, d))


def _cell_range(
    minimum: float, maximum: float, half_extent: float, spacing: float, count: int
) -> range:
    first = max(0, min(count - 2, math.floor((minimum + half_extent) / spacing)))
    last = max(0, min(count - 2, math.floor((maximum + half_extent) / spacing)))
    return range(first, last + 1)


def _triangulate_polygon_component(
    polygon: Polygon,
    row: int,
    column: int,
    triangle_id: int,
    geometry: dict[str, Any],
) -> float:
    triangulated = constrained_delaunay_triangles(polygon)
    area_sum = 0.0
    triangulated_area_sum = 0.0
    # Each component was first clipped to exactly one fixed terrain triangle.
    for face in get_parts(triangulated):
        if face.geom_type != "Polygon" or len(face.exterior.coords) != 4 or face.interiors:
            raise RoadGeometryError("constrained road triangulation returned a non-triangle face")
        points = [(float(x), float(z)) for x, z in list(face.exterior.coords)[:-1]]
        # _signed_area already returns the shoelace area (including its 1/2).
        area = abs(_signed_area(points))
        if not math.isfinite(area) or area <= 0.0:
            raise RoadGeometryError("constrained road triangulation returned a degenerate face")
        triangulated_area_sum += area
        if _signed_area(points) > 0:
            points[1], points[2] = points[2], points[1]
        float32_points = [
            (
                struct.unpack("<f", struct.pack("<f", x))[0],
                struct.unpack("<f", struct.pack("<f", z))[0],
            )
            for x, z in points
        ]
        if len(set(float32_points)) < 3:
            geometry["_float32CollapsedSliverTriangleCount"] = (
                geometry.get("_float32CollapsedSliverTriangleCount", 0) + 1
            )
            geometry["_float32CollapsedSliverAreaM2"] = (
                geometry.get("_float32CollapsedSliverAreaM2", 0.0) + area
            )
            continue
        face_indices: list[int] = []
        for x, z in points:
            key = (round(x * 1_000_000_000), round(z * 1_000_000_000))
            index = geometry["_vertexLookup"].get(key)
            if index is None:
                index = len(geometry["verticesXZ"])
                geometry["_vertexLookup"][key] = index
                geometry["verticesXZ"].append([float(x), float(z)])
            face_indices.append(index)
        geometry["indices"].append(face_indices)
        geometry["terrainTriangles"].append([row, column, triangle_id])
        area_sum += area
    # Check geometric tessellation before applying the separately bounded Float32
    # sliver omission policy. Otherwise a valid sub-micro-area face that collapses
    # after conversion is misreported as a constrained-triangulation failure.
    if abs(triangulated_area_sum - float(polygon.area)) > max(1e-7, float(polygon.area) * 1e-8):
        raise RoadGeometryError(
            f"road triangulation area {triangulated_area_sum:.12g} does not match clipped "
            f"surface area {polygon.area:.12g}"
        )
    return area_sum


def tessellate_display_polygons(
    display_polygons: dict[str, Geometry],
    *,
    columns: int,
    rows: int,
    spacing_m: float,
    width_m: float,
    depth_m: float,
    vertex_limit: int = 1_000_000,
    triangle_limit: int = 1_000_000,
    maximum_collapsed_sliver_area_m2: float = FLOAT32_SLIVER_MAX_AREA_M2,
) -> tuple[dict[str, dict[str, Any]], dict[str, float], dict[str, float | int]]:
    """Constrain each indexed surface face to one exact TerrainGrid sample plane."""
    if (
        isinstance(columns, bool)
        or not isinstance(columns, int)
        or columns < 2
        or isinstance(rows, bool)
        or not isinstance(rows, int)
        or rows < 2
        or not math.isfinite(spacing_m)
        or spacing_m <= 0
        or not math.isfinite(width_m)
        or width_m <= 0
        or not math.isfinite(depth_m)
        or depth_m <= 0
        or not math.isfinite(maximum_collapsed_sliver_area_m2)
        or maximum_collapsed_sliver_area_m2 <= 0
        or abs((columns - 1) * spacing_m - width_m) > 1e-8
        or abs((rows - 1) * spacing_m - depth_m) > 1e-8
    ):
        raise RoadGeometryError("terrain dimensions, spacing, or extents are inconsistent")
    half_width, half_depth = width_m / 2, depth_m / 2
    batches: dict[str, dict[str, Any]] = {}
    areas: dict[str, float] = {}
    collapsed_sliver_count = 0
    collapsed_sliver_area = 0.0
    for group in DISPLAY_GROUPS:
        output: dict[str, Any] = {
            "verticesXZ": [],
            "indices": [],
            "terrainTriangles": [],
            "_vertexLookup": {},
            "_float32CollapsedSliverTriangleCount": 0,
            "_float32CollapsedSliverAreaM2": 0.0,
        }
        geometry = display_polygons.get(group, Polygon())
        polygons = _canonical_polygons(geometry)
        for polygon in polygons:
            row_range = _cell_range(
                polygon.bounds[1], polygon.bounds[3], half_depth, spacing_m, rows
            )
            column_range = _cell_range(
                polygon.bounds[0], polygon.bounds[2], half_width, spacing_m, columns
            )
            polygon_area = float(polygon.area)
            accumulated = 0.0
            for row in row_range:
                for column in column_range:
                    for triangle_id in (0, 1):
                        terrain_face = _terrain_triangle(
                            row, column, triangle_id, spacing_m, half_width, half_depth
                        )
                        if not polygon.intersects(terrain_face):
                            continue
                        cut = polygon.intersection(terrain_face)
                        if cut.is_empty:
                            continue
                        for component in _polygon_parts(cut):
                            if component.area <= 1e-12:
                                continue
                            accumulated += _triangulate_polygon_component(
                                component, row, column, triangle_id, output
                            )
            if abs(accumulated - polygon_area) > max(1e-6, polygon_area * 1e-8):
                raise RoadGeometryError(
                    f"terrain-cell partition area {accumulated:.12g} does not match "
                    f"road surface area {polygon_area:.12g}"
                )
        output.pop("_vertexLookup")
        collapsed_sliver_count += output.pop("_float32CollapsedSliverTriangleCount")
        collapsed_sliver_area += output.pop("_float32CollapsedSliverAreaM2")
        if len(output["verticesXZ"]) > vertex_limit or len(output["indices"]) > triangle_limit:
            raise RoadGeometryError(
                f"{group} batch exceeds safe render limits "
                f"({len(output['verticesXZ'])} vertices, {len(output['indices'])} triangles)"
            )
        batches[group] = output
        areas[group] = sum(float(polygon.area) for polygon in polygons)
    if collapsed_sliver_area > maximum_collapsed_sliver_area_m2:
        raise RoadGeometryError(
            "Float32-collapsed road slivers exceed the "
            f"{maximum_collapsed_sliver_area_m2:g} m2 omission limit "
            f"({collapsed_sliver_area:.12g} m2)"
        )
    return (
        batches,
        areas,
        {
            "float32CollapsedSliverTriangleCount": collapsed_sliver_count,
            "float32CollapsedSliverAreaM2": collapsed_sliver_area,
        },
    )
