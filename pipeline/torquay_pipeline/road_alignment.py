"""Read-only numerical road/terrain alignment diagnostics for the current 2 km scene.

All geographic transforms and terrain calculations stay in this module.  The
driver verifies and reads existing source/package files, then writes only its
own report and registered comparison panels.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import osmium
from matplotlib import patheffects
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from .alignment_report import read_palette_window
from .comparison_sources import VerifiedComparisonSource, verify_comparison_source
from .config import AoiConfig, load_aoi_config
from .coordinates import pinned_transformer
from .road_config import RoadConfig, load_road_config
from .road_geometry import DISPLAY_GROUPS, build_display_polygons
from .roads import import_osm_roads
from .terrain_export import _sample_bilinear_mosaic
from .terrain_sources import verify_source_manifest

CURRENT_RELEASE_ID = "616e5f069acd6faa633a5ace3e04e1fee9d3d0fdb68c20e5ed0c29bb921a588a"
MAX_PROFILE_STATION_SPACING_M = 5.0
TERRAIN_TRIANGLE_TOLERANCE_GRID_FRACTION = 1e-6
RENDERER_DRAPE_TOLERANCE_M = 0.001
ROAD_SURFACE_OFFSET_M = 0.05
WAY_CONTEXTS = {
    22975541: {"name": "Teignmouth Road", "context": "Teignmouth Road longitudinal profile"},
    22976771: {"name": "Teignmouth Road", "context": "Teignmouth Road longitudinal profile"},
    24806641: {"name": "Teignmouth Road", "context": "Cricketfield / Teignmouth junction"},
    30480035: {"name": "Teignmouth Road", "context": "Cricketfield / Teignmouth junction"},
    78455395: {"name": "Teignmouth Road", "context": "Pennys Hill / Teignmouth steep section"},
    78455388: {"name": "Pennys Hill", "context": "Pennys Hill / Teignmouth steep section"},
    30482119: {"name": "Arthington", "context": "Arthington mild crossfall control"},
    30482121: {"name": "Arthington", "context": "Arthington mild crossfall control"},
    23595196: {"name": "Cricketfield Road", "context": "Cricketfield / Teignmouth junction"},
    686711262: {"name": "Cricketfield Road", "context": "Cricketfield / Teignmouth junction"},
    689028452: {"name": "Cricketfield Road", "context": "Cricketfield / Teignmouth junction"},
}
PANEL_CONTEXTS = (
    {
        "id": "pennys-teignmouth-steep",
        "title": "Pennys Hill / Teignmouth Road · steep candidate",
        "centerLocalXZ": [-244.518, -58.794],
        "halfSizeM": 100.0,
        "wayIds": [78455388, 78455395],
    },
    {
        "id": "cricketfield-teignmouth-junction",
        "title": "Cricketfield Road / Teignmouth Road · junction candidate",
        "centerLocalXZ": [-307.96, -28.828],
        "halfSizeM": 100.0,
        "wayIds": [23595196, 686711262, 689028452, 24806641, 30480035],
    },
    {
        "id": "arthington-control",
        "title": "Arthington · mild crossfall control",
        "centerLocalXZ": [-511.744, 207.096],
        "halfSizeM": 80.0,
        "wayIds": [30482119, 30482121],
    },
)
ALLOWED_OUTPUTS = {
    "analysis.json",
    "input-inventory.json",
    "browser-evidence.json",
    *{
        f"registered-{context['id']}-{view}.png"
        for context in PANEL_CONTEXTS
        for view in ("reference", "overlay")
    },
}


class RoadAlignmentError(ValueError):
    """Raised when an input contract or read-only output guard fails."""


@dataclass(frozen=True)
class TerrainGrid:
    """Validated current-release Float32 heightfield using the renderer's fixed triangles."""

    heights: np.ndarray
    columns: int
    rows: int
    spacing_m: float
    width_m: float
    depth_m: float
    origin_e_m: float
    origin_n_m: float
    origin_y_m: float

    @property
    def half_width_m(self) -> float:
        return self.width_m / 2

    @property
    def half_depth_m(self) -> float:
        return self.depth_m / 2

    def sample_relative(self, x: float, z: float) -> float:
        """Sample the same two fixed planes used by the browser TerrainGrid."""
        if (
            not math.isfinite(x)
            or not math.isfinite(z)
            or x < -self.half_width_m
            or x > self.half_width_m
            or z < -self.half_depth_m
            or z > self.half_depth_m
        ):
            raise RoadAlignmentError(f"terrain sample ({x}, {z}) is outside the heightfield")
        grid_x = (x + self.half_width_m) / self.spacing_m
        grid_z = (z + self.half_depth_m) / self.spacing_m
        column = min(math.floor(grid_x), self.columns - 2)
        row = min(math.floor(grid_z), self.rows - 2)
        u = grid_x - column
        v = grid_z - row
        a = float(self.heights[row, column])
        b = float(self.heights[row, column + 1])
        c = float(self.heights[row + 1, column])
        d = float(self.heights[row + 1, column + 1])
        if u + v <= 1:
            return a + (b - a) * u + (c - a) * v
        return d + (c - d) * (1 - u) + (b - d) * (1 - v)

    def sample_absolute(self, x: float, z: float) -> float:
        return self.origin_y_m + self.sample_relative(x, z)

    def bng(self, x: float, z: float) -> tuple[float, float]:
        return self.origin_e_m + x, self.origin_n_m - z


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise RoadAlignmentError(f"cannot hash input '{path}': {exc}") from exc
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RoadAlignmentError(f"cannot read JSON input '{path}': {exc}") from exc
    if not isinstance(value, dict):
        raise RoadAlignmentError(f"JSON input '{path}' must be an object")
    return value


def _resolve_project_path(project_root: Path, relative: str) -> Path:
    path = (project_root / relative).resolve()
    try:
        path.relative_to(project_root.resolve())
    except ValueError as exc:
        raise RoadAlignmentError(f"project-relative input escapes workspace: {relative}") from exc
    if not path.is_file():
        raise RoadAlignmentError(f"required read-only input is missing: {relative}")
    return path


def input_inventory(project_root: Path) -> dict[str, Any]:
    """Hash every source/package file used by the numerical and map diagnostics."""
    ready_path = project_root / "public/worlds/torquay-poc-001-2km/ready.json"
    ready = _json(ready_path)
    if ready.get("releaseId") != CURRENT_RELEASE_ID:
        raise RoadAlignmentError("ready.json does not select the accepted active 2 km release")
    release_base = Path("public/worlds/torquay-poc-001-2km/releases") / CURRENT_RELEASE_ID
    inventory_path = project_root / release_base / "inventory.json"
    inventory_bytes = inventory_path.read_bytes()
    inventory_hash = hashlib.sha256(inventory_bytes).hexdigest()
    if ready.get("inventorySha256") != inventory_hash or ready.get("inventoryByteLength") != len(
        inventory_bytes
    ):
        raise RoadAlignmentError("current ready pointer does not match its inventory bytes")
    inventory = json.loads(inventory_bytes)
    if not isinstance(inventory, dict) or inventory.get("releaseId") != CURRENT_RELEASE_ID:
        raise RoadAlignmentError("current release inventory has an unexpected release identity")

    files = {
        "data/source-manifest.json",
        "data/comparison-source-manifest.json",
        "config/aoi.torquay.json",
        "config/roads.torquay.json",
        "public/worlds/torquay-poc-001-2km/ready.json",
        (release_base / "inventory.json").as_posix(),
        (release_base / "manifest.json").as_posix(),
        (release_base / "qa.json").as_posix(),
        (release_base / "scene-qa.json").as_posix(),
        (release_base / "heightfield.f32").as_posix(),
        (release_base / "roads/manifest.json").as_posix(),
        (release_base / "roads/roads.json").as_posix(),
        (release_base / "roads/qa.json").as_posix(),
        (release_base / "buildings/manifest.json").as_posix(),
        (release_base / "buildings/buildings.json").as_posix(),
        (release_base / "buildings/qa.json").as_posix(),
        "data/raw/osm/devon-261016.osm.pbf",
        "data/raw/osm/devon-261016.osm.pbf.md5",
        "data/raw/comparison/os_openmap_local/selected-members/SX96NW.tif",
        "data/raw/comparison/os_openmap_local/selected-members/SX96SW.tif",
        "data/raw/comparison/os_openmap_local/selected-members/licence.txt",
        "data/raw/comparison/os_openmap_local/selected-members/readme.txt",
    }
    source_manifest = _json(project_root / "data/source-manifest.json")
    for source in source_manifest.get("sources", []):
        if isinstance(source, dict):
            relative = source.get("raster_relative_path")
            if isinstance(relative, str):
                files.add(f"data/raw/ea_dtm/{relative}")
    for relative in files.copy():
        if relative.startswith("data/raw/ea_dtm/") and relative.endswith(".tif"):
            files.add(relative + ".xml")
    files.add("data/raw/comparison/os_openmap_local/openmaplocal-2026-04-sx-geotiff.zip")

    rows = []
    for relative in sorted(files):
        path = _resolve_project_path(project_root, relative)
        rows.append(
            {
                "path": relative,
                "byteLength": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "releaseId": CURRENT_RELEASE_ID,
        "readySha256": sha256_file(ready_path),
        "inventorySha256": inventory_hash,
        "files": rows,
        "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def _is_reparse_point(path: Path) -> bool:
    if path.is_symlink():
        return True
    if not path.exists():
        return False
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction()) if callable(is_junction) else False


def _check_path_components(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    cursor = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        cursor = cursor / part
        if _is_reparse_point(cursor):
            raise RoadAlignmentError(f"output path crosses a symlink or junction: '{cursor}'")


def guard_output_directory(project_root: Path, requested: Path) -> Path:
    """Allow only the dedicated issue directory and reject input aliases before writes."""
    expected = project_root / "docs/milestones/artifacts/Road-alignment"
    requested_absolute = Path(
        os.path.abspath(requested if requested.is_absolute() else project_root / requested)
    )
    expected_absolute = Path(os.path.abspath(expected))
    if os.path.normcase(str(requested_absolute)) != os.path.normcase(str(expected_absolute)):
        raise RoadAlignmentError(
            "output-dir must be exactly docs/milestones/artifacts/Road-alignment"
        )
    _check_path_components(requested_absolute)
    if requested_absolute.exists() and not requested_absolute.is_dir():
        raise RoadAlignmentError("output-dir exists but is not a directory")
    if requested_absolute.is_dir():
        for child in requested_absolute.iterdir():
            if child.name not in ALLOWED_OUTPUTS or child.is_dir() or _is_reparse_point(child):
                raise RoadAlignmentError(
                    f"output-dir contains an unowned or unsafe entry: '{child.name}'"
                )
    return requested_absolute


def _load_terrain(terrain_package: Path, manifest: dict[str, Any]) -> TerrainGrid:
    contract = manifest.get("heightfield")
    origin = manifest.get("origin")
    extent = manifest.get("extentM")
    if (
        not isinstance(contract, dict)
        or not isinstance(origin, dict)
        or not isinstance(extent, dict)
    ):
        raise RoadAlignmentError("terrain manifest is missing its grid contract")
    columns, rows = contract.get("columns"), contract.get("rows")
    if (columns, rows, contract.get("spacingM"), extent.get("width"), extent.get("depth")) != (
        1001,
        1001,
        2.0,
        2000.0,
        2000.0,
    ):
        raise RoadAlignmentError("terrain grid is not the accepted 1,001 × 1,001, 2 m scene")
    relative = contract.get("path")
    if relative != "heightfield.f32":
        raise RoadAlignmentError("current terrain heightfield must use its fixed package path")
    binary = (terrain_package / relative).read_bytes()
    if (
        len(binary) != contract.get("byteLength")
        or hashlib.sha256(binary).hexdigest() != contract.get("sha256")
        or len(binary) != columns * rows * 4
    ):
        raise RoadAlignmentError("terrain heightfield bytes do not match their manifest")
    return TerrainGrid(
        heights=np.frombuffer(binary, dtype="<f4").reshape(rows, columns),
        columns=columns,
        rows=rows,
        spacing_m=float(contract["spacingM"]),
        width_m=float(extent["width"]),
        depth_m=float(extent["depth"]),
        origin_e_m=float(origin["eastingM"]),
        origin_n_m=float(origin["northingM"]),
        origin_y_m=float(origin["elevationM"]),
    )


def _point_in_triangle(
    x: float, z: float, row: int, column: int, triangle: int, grid: TerrainGrid
) -> bool:
    u = (x + grid.half_width_m) / grid.spacing_m - column
    v = (z + grid.half_depth_m) / grid.spacing_m - row
    epsilon = TERRAIN_TRIANGLE_TOLERANCE_GRID_FRACTION
    return (
        -epsilon <= u <= 1 + epsilon
        and -epsilon <= v <= 1 + epsilon
        and (u + v <= 1 + epsilon if triangle == 0 else u + v >= 1 - epsilon)
    )


def inspect_face(
    points_xz: list[tuple[float, float]],
    row: int,
    column: int,
    triangle: int,
    grid: TerrainGrid,
    surface_offset_m: float = ROAD_SURFACE_OFFSET_M,
) -> dict[str, Any]:
    """Measure triangle containment and centroid drape in double and renderer Float32."""
    if len(points_xz) != 3 or triangle not in (0, 1):
        raise RoadAlignmentError("a road mesh face must have three vertices and triangle 0 or 1")
    inside_double = all(_point_in_triangle(x, z, row, column, triangle, grid) for x, z in points_xz)
    ys = [grid.sample_relative(x, z) + surface_offset_m for x, z in points_xz]
    centroid_x = sum(x for x, _z in points_xz) / 3
    centroid_z = sum(z for _x, z in points_xz) / 3
    residual_double = sum(ys) / 3 - (
        grid.sample_relative(centroid_x, centroid_z) + surface_offset_m
    )
    float_points = [(_f32(x), _f32(z)) for x, z in points_xz]
    float_ys = [_f32(value) for value in ys]
    float_centroid_x = sum(x for x, _z in float_points) / 3
    float_centroid_z = sum(z for _x, z in float_points) / 3
    residual_float32 = sum(float_ys) / 3 - (
        grid.sample_relative(float_centroid_x, float_centroid_z) + surface_offset_m
    )
    cross = _horizontal_cross(float_points)
    area64 = abs(_horizontal_cross(points_xz)) / 2
    return {
        "containedInDouble": inside_double,
        "containedInFloat32": all(
            _point_in_triangle(x, z, row, column, triangle, grid) for x, z in float_points
        ),
        "doubleCentroidResidualM": residual_double,
        "float32CentroidResidualM": residual_float32,
        "float32HorizontalCross": cross,
        "float32Reoriented": cross > 0,
        "float32Collapsed": cross == 0,
        "doubleProjectedAreaM2": area64,
    }


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _horizontal_cross(points: list[tuple[float, float]]) -> float:
    first, second, third = points
    return (second[0] - first[0]) * (third[1] - first[1]) - (second[1] - first[1]) * (
        third[0] - first[0]
    )


class _SelectedWayHandler(osmium.SimpleHandler):
    def __init__(self, selected_ids: set[int]) -> None:
        super().__init__()
        self.selected_ids = selected_ids
        self.ways: dict[int, dict[str, Any]] = {}

    def way(self, way: Any) -> None:
        way_id = int(way.id)
        if way_id not in self.selected_ids:
            return
        nodes = []
        for node in way.nodes:
            if not node.location.valid():
                raise RoadAlignmentError(f"OSM way {way_id} has a missing PBF node location")
            nodes.append(
                {
                    "nodeId": int(node.ref),
                    "longitude": float(node.location.lon),
                    "latitude": float(node.location.lat),
                }
            )
        self.ways[way_id] = {
            "version": int(way.version),
            "name": next((str(tag.v) for tag in way.tags if tag.k == "name"), None),
            "nodes": nodes,
        }


def _load_selected_pbf_ways(path: Path) -> dict[int, dict[str, Any]]:
    handler = _SelectedWayHandler(set(WAY_CONTEXTS))
    try:
        handler.apply_file(str(path), locations=True, idx="flex_mem")
    except Exception as exc:
        raise RoadAlignmentError(f"cannot resolve named ways from original PBF: {exc}") from exc
    missing = sorted(set(WAY_CONTEXTS) - set(handler.ways))
    if missing:
        raise RoadAlignmentError(
            f"named road candidates are absent from the verified PBF: {missing}"
        )
    return handler.ways


def _transform_source_ways(
    source_ways: dict[int, dict[str, Any]], grid: TerrainGrid
) -> tuple[dict[int, list[dict[str, float | int]]], dict[str, Any]]:
    transformer, operation = pinned_transformer(4326, 27700)
    transformed: dict[int, list[dict[str, float | int]]] = {}
    for way_id, way in source_ways.items():
        nodes = way["nodes"]
        eastings, northings = transformer.transform(
            [node["longitude"] for node in nodes],
            [node["latitude"] for node in nodes],
            errcheck=True,
        )
        transformed[way_id] = [
            {
                "nodeId": node["nodeId"],
                "longitude": node["longitude"],
                "latitude": node["latitude"],
                "eastingM": float(easting),
                "northingM": float(northing),
                "localX": float(easting) - grid.origin_e_m,
                "localZ": grid.origin_n_m - float(northing),
            }
            for node, easting, northing in zip(nodes, eastings, northings, strict=True)
        ]
    return transformed, operation.as_dict()


def _source_coordinate_comparison(
    source_ways: dict[int, dict[str, Any]],
    transformed: dict[int, list[dict[str, float | int]]],
    imported_features: dict[int, dict[str, Any]],
    package_features: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    output = []
    for way_id in sorted(WAY_CONTEXTS):
        source = source_ways[way_id]
        imported = imported_features[way_id]
        package = package_features[way_id]
        if source["name"] != WAY_CONTEXTS[way_id]["name"]:
            raise RoadAlignmentError(f"source way {way_id} name differs from the accepted context")
        source_points = {int(point["nodeId"]): point for point in transformed[way_id]}
        normalized_ids = imported.get("sourceNodeIdsNormalized")
        quantized_points = imported.get("sourceCenterlineXZ")
        if not isinstance(normalized_ids, list) or not isinstance(quantized_points, list):
            raise RoadAlignmentError(f"re-imported way {way_id} has no normalized centerline")
        node_comparisons = []
        for node_id, point in zip(normalized_ids, quantized_points, strict=True):
            original = source_points.get(int(node_id))
            if original is None:
                raise RoadAlignmentError(f"source way {way_id} lost normalized node {node_id}")
            dx = float(point[0]) - float(original["localX"])
            dz = float(point[1]) - float(original["localZ"])
            node_comparisons.append(
                {
                    "nodeId": int(node_id),
                    "sourceLocalXZ": [float(original["localX"]), float(original["localZ"])],
                    "quantizedLocalXZ": [float(point[0]), float(point[1])],
                    "deltaXZMetres": [dx, dz],
                    "deltaMagnitudeM": math.hypot(dx, dz),
                }
            )
        raw_node_by_id = {int(point["nodeId"]): point for point in transformed[way_id]}
        delta_summary = coordinate_delta_summary(
            [
                (
                    float(raw_node_by_id[int(node_id)]["localX"]),
                    float(raw_node_by_id[int(node_id)]["localZ"]),
                )
                for node_id in normalized_ids
            ],
            [(float(point[0]), float(point[1])) for point in quantized_points],
        )
        max_axis_delta = delta_summary["maximumAbsoluteAxisDeltaM"]
        expected_parts = imported["centerlinePartsXZ"]
        package_parts = package.get("centerlinePartsXZ")
        if package_parts != expected_parts:
            raise RoadAlignmentError(
                f"published clipped centerline for way {way_id} differs from re-derived input"
            )
        output.append(
            {
                "wayId": way_id,
                "name": source["name"],
                "nodeCount": len(source["nodes"]),
                "normalizedNodeCount": len(node_comparisons),
                "coordinateOperation": "pinned_transformer(4326, 27700), always x/y order",
                "quantizationStepM": 0.001,
                "quantizationPolicy": "round(local coordinate / 0.001 m) × 0.001 m",
                "maxAbsoluteAxisDeltaM": max_axis_delta,
                "maxEuclideanDeltaM": delta_summary["maximumEuclideanDeltaM"],
                "expectedPerAxisBoundM": 0.0005001,
                "withinDocumentedMillimetreQuantization": max_axis_delta <= 0.0005001,
                "originalPbfNodesProjectedAndRetained": transformed[way_id],
                "publishedClippedCenterlineMatchesReimport": True,
                "sourceNodesAndQuantizedCoordinates": node_comparisons,
            }
        )
    return output


def _line_point_tangent(
    part: list[list[float]], station_m: float
) -> tuple[tuple[float, float], tuple[float, float]]:
    lengths = [math.dist(a, b) for a, b in zip(part, part[1:], strict=False)]
    total = sum(lengths)
    if total <= 0:
        raise RoadAlignmentError("candidate road centerline part has zero length")
    station = min(max(station_m, 0.0), total)
    accumulated = 0.0
    for index, (first, second) in enumerate(zip(part, part[1:], strict=False)):
        segment = lengths[index]
        if segment <= 0:
            continue
        if station <= accumulated + segment or index == len(lengths) - 1:
            ratio = (station - accumulated) / segment
            dx = float(second[0]) - float(first[0])
            dz = float(second[1]) - float(first[1])
            return (
                (float(first[0]) + dx * ratio, float(first[1]) + dz * ratio),
                (dx / segment, dz / segment),
            )
        accumulated += segment
    raise RoadAlignmentError("cannot derive a tangent from a candidate centerline")


def _sample_source_raster(
    raster_paths: list[Path], grid: TerrainGrid, positions_xz: list[tuple[float, float]]
) -> list[float]:
    eastings = np.asarray(
        [grid.origin_e_m + x for x, _z in positions_xz], dtype=np.float64
    ).reshape(1, -1)
    northings = np.asarray(
        [grid.origin_n_m - z for _x, z in positions_xz], dtype=np.float64
    ).reshape(1, -1)
    try:
        elevations = _sample_bilinear_mosaic(raster_paths, eastings, northings)
    except Exception as exc:
        raise RoadAlignmentError(f"cannot sample original EA 1 m source rasters: {exc}") from exc
    return [float(value) for value in np.ravel(elevations)]


def _percentiles(values: list[float]) -> dict[str, float | None]:
    return {
        "medianAbsolutePercent": float(np.median(values)) if values else None,
        "maximumAbsolutePercent": max(values) if values else None,
    }


def coordinate_delta_summary(
    source_points: list[tuple[float, float]], represented_points: list[tuple[float, float]]
) -> dict[str, float]:
    """Report pointwise X/Z deltas without translating or fitting either line."""
    if len(source_points) != len(represented_points) or not source_points:
        raise RoadAlignmentError("coordinate comparison requires matching non-empty point arrays")
    deltas = [
        (actual[0] - source[0], actual[1] - source[1])
        for source, actual in zip(source_points, represented_points, strict=True)
    ]
    return {
        "maximumAbsoluteAxisDeltaM": max(abs(value) for delta in deltas for value in delta),
        "maximumEuclideanDeltaM": max(math.hypot(dx, dz) for dx, dz in deltas),
    }


def absolute_grade_percent(stations_m: list[float], elevations_m: list[float]) -> list[float]:
    """Compute absolute grade for successive samples with their actual station spacing."""
    if len(stations_m) != len(elevations_m) or len(stations_m) < 2:
        raise RoadAlignmentError("grade calculation requires at least two matched samples")
    grades = []
    for start, end, z0, z1 in zip(
        stations_m, stations_m[1:], elevations_m, elevations_m[1:], strict=False
    ):
        distance = end - start
        if distance <= 0 or not math.isfinite(distance):
            raise RoadAlignmentError("profile stations must increase by finite positive distances")
        grades.append(abs(z1 - z0) / distance * 100)
    return grades


def cross_grade_percent(
    first_elevation_m: float, second_elevation_m: float, width_m: float
) -> float:
    """Absolute ground crossfall beneath two opposite samples across configured width."""
    if width_m <= 0 or not math.isfinite(width_m):
        raise RoadAlignmentError("crossfall width must be finite and positive")
    return abs(second_elevation_m - first_elevation_m) / width_m * 100


def _summarize_profile(
    feature: dict[str, Any], grid: TerrainGrid, raster_paths: list[Path]
) -> dict[str, Any]:
    way_id = int(feature["source"]["osmId"])
    parts = feature.get("centerlinePartsXZ")
    if not isinstance(parts, list) or not parts:
        raise RoadAlignmentError(f"road way {way_id} has no clipped centerline part")
    width_m = float(feature["estimatedWidthM"])
    longitudinal = {"packageTerrain": [], "source1mDtm": []}
    crossfall = {"packageTerrain": [], "source1mDtm": []}
    part_records = []
    for part_index, part_value in enumerate(parts):
        part = [[float(point[0]), float(point[1])] for point in part_value]
        total_length = sum(math.dist(a, b) for a, b in zip(part, part[1:], strict=False))
        if total_length <= 0:
            continue
        intervals = max(1, math.ceil(total_length / MAX_PROFILE_STATION_SPACING_M))
        step_m = total_length / intervals
        center_samples = []
        for index in range(intervals + 1):
            station = index * step_m
            point, _tangent = _line_point_tangent(part, station)
            center_samples.append((station, point))
        positions = [point for _station, point in center_samples]
        source_elevations = _sample_source_raster(raster_paths, grid, positions)
        package_elevations = [grid.sample_absolute(*point) for point in positions]
        station_values = [station for station, _point in center_samples]
        package_steps = absolute_grade_percent(station_values, package_elevations)
        source_steps = absolute_grade_percent(station_values, source_elevations)
        longitudinal["packageTerrain"].extend(package_steps)
        longitudinal["source1mDtm"].extend(source_steps)

        cross_samples = []
        cross_positions: list[tuple[float, float]] = []
        for index in range(intervals):
            station = (index + 0.5) * step_m
            center, tangent = _line_point_tangent(part, station)
            normal = (-tangent[1], tangent[0])
            half_width = width_m / 2
            left = (center[0] + normal[0] * half_width, center[1] + normal[1] * half_width)
            right = (center[0] - normal[0] * half_width, center[1] - normal[1] * half_width)
            if any(
                abs(point[0]) > grid.half_width_m or abs(point[1]) > grid.half_depth_m
                for point in (left, right)
            ):
                continue
            cross_positions.extend((left, right))
            cross_samples.append(
                {
                    "stationM": station,
                    "centerLocalXZ": list(center),
                    "tangentXZ": list(tangent),
                    "oppositeLocalXZ": [list(left), list(right)],
                }
            )
        source_cross_elevations = _sample_source_raster(raster_paths, grid, cross_positions)
        package_cross_elevations = [grid.sample_absolute(*point) for point in cross_positions]
        package_cross_grades = []
        source_cross_grades = []
        for index, sample in enumerate(cross_samples):
            package_pair = package_cross_elevations[index * 2 : index * 2 + 2]
            source_pair = source_cross_elevations[index * 2 : index * 2 + 2]
            package_delta = package_pair[0] - package_pair[1]
            source_delta = source_pair[0] - source_pair[1]
            package_grade = cross_grade_percent(*package_pair, width_m)
            source_grade = cross_grade_percent(*source_pair, width_m)
            package_cross_grades.append(package_grade)
            source_cross_grades.append(source_grade)
            sample["bngOppositeCoordinatesEN"] = [
                list(grid.bng(*point)) for point in cross_positions[index * 2 : index * 2 + 2]
            ]
            sample["packageElevationsM"] = package_pair
            sample["source1mDtmElevationsM"] = source_pair
            sample["signedPackageLeftMinusRightM"] = package_delta
            sample["signedSourceLeftMinusRightM"] = source_delta
            sample["packageAbsoluteCrossGradePercent"] = package_grade
            sample["sourceAbsoluteCrossGradePercent"] = source_grade
        crossfall["packageTerrain"].extend(package_cross_grades)
        crossfall["source1mDtm"].extend(source_cross_grades)
        for index, sample in enumerate(center_samples):
            x, z = sample[1]
            sample_record = {
                "stationM": sample[0],
                "localXZ": [x, z],
                "bngEN": list(grid.bng(x, z)),
                "packageTerrainElevationM": package_elevations[index],
                "source1mDtmElevationM": source_elevations[index],
            }
            if index == 0 or index == intervals:
                sample_record["endpointRole"] = (
                    "stored-way-direction start" if index == 0 else "stored-way-direction end"
                )
            center_samples[index] = (sample[0], sample[1], sample_record)
        part_records.append(
            {
                "partIndex": part_index,
                "storedWayDirection": "first clipped vertex to last clipped vertex",
                "lengthM": total_length,
                "intervalCount": intervals,
                "maximumStationSpacingM": step_m,
                "crossfallIntervalsSkippedOutsideTerrain": intervals - len(cross_samples),
                "signedEndpointChangePackageTerrainM": package_elevations[-1]
                - package_elevations[0],
                "signedEndpointChangeSource1mDtmM": source_elevations[-1] - source_elevations[0],
                "packageTerrainElevationRangeM": [min(package_elevations), max(package_elevations)],
                "source1mDtmElevationRangeM": [min(source_elevations), max(source_elevations)],
                "longitudinalSamples": [sample[2] for sample in center_samples],
                "crossfallSamples": cross_samples,
            }
        )

    return {
        "wayId": way_id,
        "name": feature["sourceTags"].get("name"),
        "highway": feature["highway"],
        "displayGroup": feature["displayGroup"],
        "widthM": width_m,
        "widthMethod": feature["widthMethod"],
        "rawOsmWidthTag": feature["widthEvidence"].get("rawWidth"),
        "rawOsmLanesTag": feature["widthEvidence"].get("rawLanes"),
        "terrainSurfaceOffsetM": ROAD_SURFACE_OFFSET_M,
        "longitudinalGrade": {
            "packageTerrain": _percentiles(longitudinal["packageTerrain"]),
            "source1mDtm": _percentiles(longitudinal["source1mDtm"]),
        },
        "crossGrade": {
            "measurement": "opposite samples at ± half the configured width, at interval midpoints",
            "packageTerrain": _percentiles(crossfall["packageTerrain"]),
            "source1mDtm": _percentiles(crossfall["source1mDtm"]),
        },
        "parts": part_records,
        "interpretation": (
            "Terrain under an estimated ribbon only; this is not a surveyed road edge, "
            "engineered carriageway profile, or completeness finding."
        ),
    }


def _triangle_area(points: list[tuple[float, float]]) -> float:
    return abs(_horizontal_cross(points)) / 2


def _scan_mesh(
    road_payload: dict[str, Any], grid: TerrainGrid
) -> tuple[dict[str, Any], dict[str, float]]:
    batches = road_payload.get("surfaceBatches")
    if not isinstance(batches, dict):
        raise RoadAlignmentError("roads payload is missing surfaceBatches")
    summary: dict[str, Any] = {
        "rendererDrapeToleranceM": RENDERER_DRAPE_TOLERANCE_M,
        "terrainTriangleContainmentToleranceGridFraction": TERRAIN_TRIANGLE_TOLERANCE_GRID_FRACTION,
        "surfaceOffsetM": ROAD_SURFACE_OFFSET_M,
        "byDisplayGroup": {},
        "faceCount": 0,
        "doubleContainmentFailures": 0,
        "float32ContainmentFailures": 0,
        "maximumAbsoluteDoubleCentroidResidualM": 0.0,
        "maximumAbsoluteFloat32CentroidResidualM": 0.0,
        "float32ReorientedTriangleCount": 0,
        "float32CollapsedTriangleCount": 0,
        "float32CollapsedProjectedAreaM2": 0.0,
    }
    mesh_areas: dict[str, float] = {}
    for group in DISPLAY_GROUPS:
        batch = batches.get(group)
        if not isinstance(batch, dict):
            raise RoadAlignmentError(f"road surface batch {group!r} is missing")
        vertices = batch.get("verticesXZ")
        indices = batch.get("indices")
        terrain_cells = batch.get("terrainTriangles")
        if (
            not isinstance(vertices, list)
            or not isinstance(indices, list)
            or not isinstance(terrain_cells, list)
        ):
            raise RoadAlignmentError(f"road surface batch {group!r} is malformed")
        if len(indices) != len(terrain_cells):
            raise RoadAlignmentError(f"road surface batch {group!r} face metadata is misaligned")
        area_sum = 0.0
        reoriented = 0
        collapsed = 0
        collapsed_area = 0.0
        containment_double = 0
        containment_float = 0
        max_double = 0.0
        max_float = 0.0
        for face, terrain_cell in zip(indices, terrain_cells, strict=True):
            row, column, triangle = (int(value) for value in terrain_cell)
            if not (0 <= row < grid.rows - 1 and 0 <= column < grid.columns - 1):
                raise RoadAlignmentError(f"{group} face references a terrain cell outside the grid")
            points = [
                (float(vertices[int(index)][0]), float(vertices[int(index)][1])) for index in face
            ]
            measure = inspect_face(points, row, column, triangle, grid)
            area_sum += measure["doubleProjectedAreaM2"]
            summary["faceCount"] += 1
            containment_double += not measure["containedInDouble"]
            containment_float += not measure["containedInFloat32"]
            max_double = max(max_double, abs(measure["doubleCentroidResidualM"]))
            max_float = max(max_float, abs(measure["float32CentroidResidualM"]))
            reoriented += bool(measure["float32Reoriented"])
            collapsed += bool(measure["float32Collapsed"])
            if measure["float32Collapsed"]:
                collapsed_area += measure["doubleProjectedAreaM2"]
        mesh_areas[group] = area_sum
        summary["doubleContainmentFailures"] += containment_double
        summary["float32ContainmentFailures"] += containment_float
        summary["maximumAbsoluteDoubleCentroidResidualM"] = max(
            summary["maximumAbsoluteDoubleCentroidResidualM"], max_double
        )
        summary["maximumAbsoluteFloat32CentroidResidualM"] = max(
            summary["maximumAbsoluteFloat32CentroidResidualM"], max_float
        )
        summary["float32ReorientedTriangleCount"] += reoriented
        summary["float32CollapsedTriangleCount"] += collapsed
        summary["float32CollapsedProjectedAreaM2"] += collapsed_area
        summary["byDisplayGroup"][group] = {
            "faceCount": len(indices),
            "projectedMeshAreaM2": area_sum,
            "doubleContainmentFailures": containment_double,
            "float32ContainmentFailures": containment_float,
            "maximumAbsoluteDoubleCentroidResidualM": max_double,
            "maximumAbsoluteFloat32CentroidResidualM": max_float,
            "float32ReorientedTriangleCount": reoriented,
            "float32CollapsedTriangleCount": collapsed,
            "float32CollapsedProjectedAreaM2": collapsed_area,
        }
    return summary, mesh_areas


def _surface_comparison(
    features: list[dict[str, Any]],
    visible_polygons: dict[str, Any],
    mesh_areas: dict[str, float],
) -> dict[str, Any]:
    by_group = {}
    total_buffer_area = 0.0
    total_visible = 0.0
    for group in DISPLAY_GROUPS:
        pieces = [feature for feature in features if feature["displayGroup"] == group]
        raw_buffer = sum(float(feature.get("ribbonAreaM2", 0.0)) for feature in pieces)
        visible_geometry = visible_polygons[group]
        mesh_area = mesh_areas[group]
        difference = mesh_area - float(visible_geometry.area)
        components = list(getattr(visible_geometry, "geoms", (visible_geometry,)))
        largest = max((float(part.area) for part in components if not part.is_empty), default=0.0)
        by_group[group] = {
            "featureCount": len(pieces),
            "sumOfPerWayClippedBuffersBeforeUnionM2": raw_buffer,
            "sourceBufferGroupUnionThenPriorityAreaM2": float(visible_geometry.area),
            "publishedMeshProjectedAreaM2": mesh_area,
            "publishedMeshMinusExpectedVisibleAreaM2": difference,
            "largestConnectedVisibleComponentM2": largest,
            "areaMatchesWithinFloat32OmissionAndRounding": abs(difference) <= 5e-5,
        }
        total_buffer_area += raw_buffer
        total_visible += float(visible_geometry.area)
    largest_group_area = max(
        (item["largestConnectedVisibleComponentM2"] for item in by_group.values()), default=0.0
    )
    return {
        "aoiAreaM2": 4_000_000.0,
        "sumOfPerWayClippedBuffersBeforeUnionM2": total_buffer_area,
        "priorityPartitionedDisjointAreaM2": total_visible,
        "priorityPartitionedAoiAreaPercent": total_visible / 4_000_000.0 * 100,
        "largestConnectedVisibleComponentAcrossGroupsM2": largest_group_area,
        "groupAreaDetails": by_group,
        "policy": (
            "union within display groups; partition priority vehicular > cycleway > path; "
            "AOI clip; fixed terrain-triangle subdivision"
        ),
        "interpretation": (
            "A way's configured buffer is not a distinct visible surface at junctions: "
            "group unions and priority partitioning reduce overlaps. These areas do not measure "
            "surveyed carriageway width."
        ),
    }


def _candidate_window_surface_summaries(
    features: list[dict[str, Any]],
    visible_polygons: dict[str, Any],
    aoi: AoiConfig,
    grid: TerrainGrid,
) -> list[dict[str, Any]]:
    """Summarize configured road ribbons within the registered map context windows."""
    center_e, center_n = aoi.center_bng_m
    west, south, east, north = aoi.bbox_m
    local_aoi = box(west - center_e, center_n - north, east - center_e, center_n - south)
    summaries = []

    for context in PANEL_CONTEXTS:
        center_x, center_z = context["centerLocalXZ"]
        radius = float(context["halfSizeM"])
        min_x, min_z = center_x - radius, center_z - radius
        max_x, max_z = center_x + radius, center_z + radius
        window = box(min_x, min_z, max_x, max_z)
        by_group: dict[str, list[Any]] = {group: [] for group in DISPLAY_GROUPS}
        intersecting_ways: list[dict[str, Any]] = []

        for feature in features:
            group = feature.get("displayGroup")
            if group not in DISPLAY_GROUPS:
                raise RoadAlignmentError("road feature has an unknown display group")
            line = LineString(feature["sourceCenterlineXZ"])
            width = float(feature["estimatedWidthM"])
            # Keep the same buffer parameters used by build_display_polygons.
            ribbon = line.buffer(
                width / 2,
                quad_segs=1,
                cap_style="flat",
                join_style="bevel",
                mitre_limit=2.0,
            ).intersection(local_aoi)
            clipped = ribbon.intersection(window)
            if clipped.is_empty or clipped.area <= 0:
                continue
            area = float(clipped.area)
            eligible = feature.get("ribbonExcludedReason") != "below_minimum_ribbon_area"
            way_id = int(feature["source"]["osmId"])
            intersecting_ways.append(
                {
                    "wayId": way_id,
                    "name": feature.get("sourceTags", {}).get("name"),
                    "displayGroup": group,
                    "estimatedWidthM": width,
                    "clippedRibbonAreaM2": area,
                    "eligibleForPublishedUnion": eligible,
                    "isNamedCandidateWay": way_id in context["wayIds"],
                }
            )
            if eligible:
                by_group[group].append(clipped)

        occupied = Polygon()
        group_records = {}
        rederived_visible_area = 0.0
        published_visible_area = 0.0
        for group in DISPLAY_GROUPS:
            pieces = by_group[group]
            group_union = unary_union(pieces) if pieces else Polygon()
            priority_visible = (
                group_union.difference(occupied)
                if not group_union.is_empty and not occupied.is_empty
                else group_union
            )
            expected_visible = visible_polygons[group].intersection(window)
            symmetric_difference_area = float(
                priority_visible.symmetric_difference(expected_visible).area
            )
            group_area = float(group_union.area)
            priority_area = float(priority_visible.area)
            expected_area = float(expected_visible.area)
            group_records[group] = {
                "eligiblePerWayBufferSumBeforeGroupUnionM2": sum(
                    record["clippedRibbonAreaM2"]
                    for record in intersecting_ways
                    if record["displayGroup"] == group and record["eligibleForPublishedUnion"]
                ),
                "groupUnionAreaM2": group_area,
                "priorityPartitionedVisibleAreaM2": priority_area,
                "publishedVisibleSurfaceAreaM2": expected_area,
                "reconstructedMinusPublishedAreaM2": priority_area - expected_area,
                "priorityVisibleSymmetricDifferenceM2": symmetric_difference_area,
            }
            rederived_visible_area += priority_area
            published_visible_area += expected_area
            if not group_union.is_empty:
                occupied = (
                    unary_union([occupied, group_union]) if not occupied.is_empty else group_union
                )

        def summarize_way_set(records: list[dict[str, Any]]) -> dict[str, Any]:
            eligible_records = [record for record in records if record["eligibleForPublishedUnion"]]
            excluded_records = [
                record for record in records if not record["eligibleForPublishedUnion"]
            ]

            def largest(items: list[dict[str, Any]]) -> dict[str, Any] | None:
                if not items:
                    return None
                winner = max(items, key=lambda item: item["clippedRibbonAreaM2"])
                return {
                    "wayId": winner["wayId"],
                    "name": winner["name"],
                    "displayGroup": winner["displayGroup"],
                    "estimatedWidthM": winner["estimatedWidthM"],
                    "clippedRibbonAreaM2": winner["clippedRibbonAreaM2"],
                }

            return {
                "intersectingWayCount": len(records),
                "sumOfPerWayClippedBufferAreasBeforeUnionM2": sum(
                    record["clippedRibbonAreaM2"] for record in records
                ),
                "eligiblePerWayBufferSumBeforeUnionM2": sum(
                    record["clippedRibbonAreaM2"] for record in eligible_records
                ),
                "minimumAreaExcludedBufferSumM2": sum(
                    record["clippedRibbonAreaM2"] for record in excluded_records
                ),
                "largestEligiblePerWayClippedRibbon": largest(eligible_records),
                "largestPerWayClippedRibbonIncludingMinimumAreaExcluded": largest(records),
            }

        candidate_records = [
            record for record in intersecting_ways if record["isNamedCandidateWay"]
        ]
        summaries.append(
            {
                "id": context["id"],
                "title": context["title"],
                "windowInterpretation": (
                    "Registered comparison-panel candidate window; this bounds local surface "
                    "area only and does not establish a match to the user screenshot camera."
                ),
                "candidateWayIds": list(context["wayIds"]),
                "candidateWindowBoundsLocalXZ": {
                    "minimumX": min_x,
                    "minimumZ": min_z,
                    "maximumX": max_x,
                    "maximumZ": max_z,
                },
                "candidateWindowBoundsBngEN": {
                    "westEasting": grid.origin_e_m + min_x,
                    "southNorthing": grid.origin_n_m - max_z,
                    "eastEasting": grid.origin_e_m + max_x,
                    "northNorthing": grid.origin_n_m - min_z,
                },
                "windowAreaM2": float(window.area),
                "network": summarize_way_set(intersecting_ways),
                "namedCandidateWays": summarize_way_set(candidate_records),
                "groupUnionAndPriorityAreas": group_records,
                "reconstructedPriorityVisibleAreaM2": rederived_visible_area,
                "publishedPriorityVisibleAreaM2": published_visible_area,
            }
        )
    return summaries


def _raster_paths(project_root: Path, source_manifest: dict[str, Any]) -> list[Path]:
    paths = [
        project_root / "data/raw/ea_dtm" / record["raster_relative_path"]
        for record in source_manifest["sources"]
    ]
    return sorted(paths, key=lambda path: path.name.casefold())


def _comparison_window(
    context: dict[str, Any], grid: TerrainGrid
) -> tuple[float, float, float, float]:
    x, z = context["centerLocalXZ"]
    radius = float(context["halfSizeM"])
    west = math.floor(grid.origin_e_m + x - radius)
    east = math.ceil(grid.origin_e_m + x + radius)
    south = math.floor(grid.origin_n_m - (z + radius))
    north = math.ceil(grid.origin_n_m - (z - radius))
    return float(west), float(south), float(east), float(north)


def _render_registered_panels(
    source: VerifiedComparisonSource,
    road_payload: dict[str, Any],
    grid: TerrainGrid,
) -> tuple[dict[str, bytes], list[dict[str, Any]]]:
    outputs: dict[str, bytes] = {}
    records = []
    roads = road_payload["features"]
    for context in PANEL_CONTEXTS:
        bounds = _comparison_window(context, grid)
        window = read_palette_window(source, bounds)
        left, bottom, right, top = window.bounds_m
        for kind in ("reference", "overlay"):
            fig, ax = plt.subplots(figsize=(8.5, 7.0), dpi=170)
            fig.subplots_adjust(left=0.11, right=0.97, top=0.88, bottom=0.14)
            ax.imshow(
                window.rgba(),
                origin="upper",
                extent=(left, right, bottom, top),
                interpolation="nearest",
                zorder=0,
            )
            if kind == "overlay":
                for feature in roads:
                    color = "#00f0d0" if feature.get("displayGroup") == "vehicular" else "#e741ff"
                    for part in feature.get("centerlinePartsXZ", []):
                        local = LineString([(float(point[0]), float(point[1])) for point in part])
                        if not local.intersects(
                            box(
                                left - grid.origin_e_m,
                                grid.origin_n_m - top,
                                right - grid.origin_e_m,
                                grid.origin_n_m - bottom,
                            )
                        ):
                            continue
                        clipped = local.intersection(
                            box(
                                left - grid.origin_e_m,
                                grid.origin_n_m - top,
                                right - grid.origin_e_m,
                                grid.origin_n_m - bottom,
                            )
                        )
                        for part_geometry in getattr(clipped, "geoms", [clipped]):
                            if part_geometry.geom_type != "LineString" or part_geometry.is_empty:
                                continue
                            coords = [grid.bng(float(x), float(z)) for x, z in part_geometry.coords]
                            ax.plot(
                                [point[0] for point in coords],
                                [point[1] for point in coords],
                                color=color,
                                linewidth=1.15,
                                zorder=5,
                                path_effects=[
                                    patheffects.Stroke(linewidth=2.7, foreground="white"),
                                    patheffects.Normal(),
                                ],
                            )
                for way_id in context["wayIds"]:
                    feature = next(
                        (item for item in roads if item.get("source", {}).get("osmId") == way_id),
                        None,
                    )
                    if feature is None:
                        continue
                    for part in feature.get("centerlinePartsXZ", []):
                        line = LineString([(float(point[0]), float(point[1])) for point in part])
                        if not line.intersects(
                            box(
                                left - grid.origin_e_m,
                                grid.origin_n_m - top,
                                right - grid.origin_e_m,
                                grid.origin_n_m - bottom,
                            )
                        ):
                            continue
                        point = line.interpolate(line.length / 2)
                        easting, northing = grid.bng(point.x, point.y)
                        ax.text(
                            easting,
                            northing,
                            feature.get("sourceTags", {}).get("name", str(way_id)),
                            fontsize=6.3,
                            color="#111111",
                            ha="center",
                            va="center",
                            bbox={
                                "facecolor": "white",
                                "alpha": 0.8,
                                "edgecolor": "none",
                                "pad": 1.5,
                            },
                            zorder=7,
                        )
            title = f"{context['title']} · {kind}"
            ax.set_title(title, fontsize=10)
            ax.set_xlim(left, right)
            ax.set_ylim(bottom, top)
            ax.set_aspect("equal")
            ax.set_xlabel("Easting (m), EPSG:27700")
            ax.set_ylabel("Northing (m), EPSG:27700")
            ax.text(
                0.01,
                -0.19,
                "April 2026 OS OpenMap–Local, 1 m pixel registration. Overlay is dated OSM "
                "centerline linework; generalized map symbols do not establish surveyed "
                "kerb width or elevation.",
                transform=ax.transAxes,
                fontsize=6.5,
                va="top",
            )
            fig.text(
                0.98,
                0.025,
                "Contains Ordnance Survey data © Crown copyright and database right 2026 · "
                "© OpenStreetMap contributors",
                ha="right",
                fontsize=6,
            )
            image = io.BytesIO()
            fig.savefig(image, format="png", dpi=170, facecolor="white")
            plt.close(fig)
            name = f"registered-{context['id']}-{kind}.png"
            outputs[name] = image.getvalue()
        records.append(
            {
                "id": context["id"],
                "title": context["title"],
                "wayIds": context["wayIds"],
                "localCenterXZ": context["centerLocalXZ"],
                "registeredWindowBoundsBngM": list(window.bounds_m),
                "pixelRegistration": "AREA_OR_POINT=Area; exact source affine; no warp/resampling",
                "sourceTiles": list(window.tile_names),
                "referenceFile": f"registered-{context['id']}-reference.png",
                "overlayFile": f"registered-{context['id']}-overlay.png",
            }
        )
    return outputs, records


def _atomic_write(output_dir: Path, outputs: dict[str, bytes]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    staged: dict[Path, Path] = {}
    try:
        for filename, content in outputs.items():
            if filename not in ALLOWED_OUTPUTS:
                raise RoadAlignmentError(f"refusing an unowned diagnostic output '{filename}'")
            target = output_dir / filename
            with tempfile.NamedTemporaryFile(
                prefix=f".{filename}.", suffix=".stage", dir=output_dir, delete=False
            ) as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
                staged[target] = Path(stream.name)
        for target, stage in staged.items():
            os.replace(stage, target)
    finally:
        for stage in staged.values():
            stage.unlink(missing_ok=True)


def _float_report(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _float_report(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_float_report(item) for item in value]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def run_assessment(project_root: Path, requested_output_dir: Path) -> dict[str, Any]:
    """Run read-only package/source diagnostics and publish only scoped artifacts."""
    project_root = project_root.resolve()
    output_dir = guard_output_directory(project_root, requested_output_dir)
    release_base = project_root / "public/worlds/torquay-poc-001-2km/releases" / CURRENT_RELEASE_ID
    inventory = input_inventory(project_root)
    aoi_path = project_root / "config/aoi.torquay.json"
    road_config_path = project_root / "config/roads.torquay.json"
    source_manifest_path = project_root / "data/source-manifest.json"
    comparison_manifest_path = project_root / "data/comparison-source-manifest.json"
    aoi: AoiConfig = load_aoi_config(aoi_path)
    road_config: RoadConfig = load_road_config(road_config_path)[0]
    if (
        aoi.profile != "current_2km"
        or aoi.selection_status != "selected_pending_coverage"
        or aoi.coverage_status != "not_checked"
    ):
        raise RoadAlignmentError(
            "the 2 km candidate must remain selected_pending_coverage / not_checked"
        )
    release_manifest = _json(release_base / "manifest.json")
    road_manifest = _json(release_base / "roads/manifest.json")
    road_payload = _json(release_base / "roads/roads.json")
    terrain_manifest = release_manifest
    grid = _load_terrain(release_base, terrain_manifest)
    if road_manifest.get("sceneProfile") != "current_2km" or road_manifest.get("worldId") != aoi.id:
        raise RoadAlignmentError("road release is not bound to the current_2km AOI")
    road_descriptor = road_manifest.get("assets", {}).get("roads", {})
    road_payload_path = release_base / "roads/roads.json"
    if road_descriptor.get("byteLength") != road_payload_path.stat().st_size or road_descriptor.get(
        "sha256"
    ) != sha256_file(road_payload_path):
        raise RoadAlignmentError("published road payload does not match its manifest")

    source_manifest, _verified_ea = verify_source_manifest(
        source_manifest_path, project_root / "data/raw/ea_dtm"
    )
    pbf_record = source_manifest.get("osm", {}).get("sources", [{}])[0]
    pbf_path = project_root / pbf_record.get("relative_path", "")
    if not pbf_path.is_file():
        raise RoadAlignmentError("the manifest-bound dated OSM PBF is missing")
    imported = import_osm_roads(pbf_path, source_manifest_path, aoi, road_config)
    imported_by_id = {int(feature["source"]["osmId"]): feature for feature in imported.features}
    package_by_id = {
        int(feature["source"]["osmId"]): feature for feature in road_payload.get("features", [])
    }
    for way_id in WAY_CONTEXTS:
        if way_id not in imported_by_id or way_id not in package_by_id:
            raise RoadAlignmentError(
                f"candidate way {way_id} is missing from the re-import or package"
            )
    selected_ways = _load_selected_pbf_ways(pbf_path)
    projected_ways, operation = _transform_source_ways(selected_ways, grid)
    coordinate_comparison = _source_coordinate_comparison(
        selected_ways, projected_ways, imported_by_id, package_by_id
    )

    raster_paths = _raster_paths(project_root, source_manifest)
    profiles = [
        _summarize_profile(imported_by_id[way_id], grid, raster_paths)
        for way_id in sorted(WAY_CONTEXTS)
    ]
    source_display_polygons, source_buffer_areas = build_display_polygons(
        imported.features, aoi, road_config
    )
    mesh_report, mesh_areas = _scan_mesh(road_payload, grid)
    surface_report = _surface_comparison(imported.features, source_display_polygons, mesh_areas)
    surface_report["candidateWindowSummaries"] = _candidate_window_surface_summaries(
        imported.features, source_display_polygons, aoi, grid
    )
    surface_report["prePriorityGroupAreasM2"] = source_buffer_areas
    # Check every re-imported way against the same public package feature contract.
    reproduced_count = 0
    maximum_centerline_vertex_delta = 0.0
    for feature in imported.features:
        published = package_by_id.get(int(feature["source"]["osmId"]))
        if published is None:
            raise RoadAlignmentError("re-imported OSM way is missing from the immutable package")
        if published.get("centerlinePartsXZ") != feature.get("centerlinePartsXZ"):
            raise RoadAlignmentError(
                f"published clipped centerline differs for way {feature['source']['osmId']}"
            )
        reproduced_count += 1
    surface_report["rederivedPublishedCenterlineCount"] = reproduced_count
    surface_report["maximumPublishedClippedCenterlineVertexDeltaM"] = (
        maximum_centerline_vertex_delta
    )

    comparison_source = verify_comparison_source(
        comparison_manifest_path,
        project_root / "data/raw/comparison/os_openmap_local",
    )
    panels, panel_records = _render_registered_panels(comparison_source, road_payload, grid)
    coordinate_accuracy = road_manifest.get("coordinateOperation", {}).get("wgs84ToBng", {})
    profiles_by_id = {record["wayId"]: record for record in profiles}
    context_results = []
    for context in PANEL_CONTEXTS:
        context_way_profiles = [
            profiles_by_id[way_id] for way_id in context["wayIds"] if way_id in profiles_by_id
        ]
        max_cross = max(
            (
                part["crossfallSamples"][index]["packageAbsoluteCrossGradePercent"]
                for profile in context_way_profiles
                for part in profile["parts"]
                for index in range(len(part["crossfallSamples"]))
            ),
            default=0.0,
        )
        context_results.append(
            {
                "id": context["id"],
                "candidateWayIds": context["wayIds"],
                "maximumObservedPackageCrossGradePercent": max_cross,
                "classification": (
                    "source/representation limitation"
                    if context["id"] != "arthington-control"
                    else "inconclusive control"
                ),
                "reason": (
                    "The numeric result is terrain beneath configured estimated-width ribbons; "
                    "it does not establish surveyed carriageway width or engineering. Exact "
                    "screenshot pose/segment correspondence remains unknown."
                ),
                "registeredPanels": next(
                    item for item in panel_records if item["id"] == context["id"]
                ),
            }
        )

    comparison_manifest = _json(comparison_manifest_path)
    report = {
        "formatVersion": 1,
        "issue": "Road-alignment focused diagnostic; not TVW-016",
        "generatedBy": "scripts/assess-road-alignment.py",
        "release": {
            "releaseId": CURRENT_RELEASE_ID,
            "sceneProfile": release_manifest.get("sceneProfile"),
            "readySha256": inventory["readySha256"],
            "inventorySha256": inventory["inventorySha256"],
            "roadPayloadSha256": road_descriptor.get("sha256"),
            "terrainHeightfieldSha256": terrain_manifest.get("heightfield", {}).get("sha256"),
            "roadFeatureCount": len(road_payload.get("features", [])),
        },
        "aoi": {
            "profile": aoi.profile,
            "boundsBngM": list(aoi.bbox_m),
            "centerBngM": list(aoi.center_bng_m),
            "anchor": aoi.anchor.postcode,
            "selectionStatus": aoi.selection_status,
            "coverageStatus": aoi.coverage_status,
        },
        "inputs": inventory,
        "source": {
            "pbfPath": pbf_path.relative_to(project_root).as_posix(),
            "pbfSha256": pbf_record.get("sha256"),
            "replicationTimestamp": pbf_record.get("replication_data_timestamp"),
            "coordinateOperation": operation,
            "reportedAccuracyM": coordinate_accuracy.get("reportedAccuracyM"),
            "preferredMissingGridNames": coordinate_accuracy.get("preferredMissingGridNames"),
            "coordinateOperationCaveat": coordinate_accuracy.get("missingPreferredGridCaveat"),
            "sourceCoordinatesCompared": coordinate_comparison,
            "terrainRasters": [
                {
                    "path": path.relative_to(project_root).as_posix(),
                    "sha256": sha256_file(path),
                    "method": (
                        "existing EA 1 m EPSG:27700 raster; bilinear interpolation "
                        "between AREA pixel centers"
                    ),
                }
                for path in raster_paths
            ],
        },
        "surface": surface_report,
        "terrainMesh": mesh_report,
        "profiles": {
            "maximumStationSpacingM": MAX_PROFILE_STATION_SPACING_M,
            "longitudinalMethod": (
                "successive centerline terrain samples in stored OSM way direction; "
                "absolute grade percent"
            ),
            "crossfallMethod": (
                "opposite samples at ± half configured width at interval midpoints; "
                "absolute grade percent"
            ),
            "packageTerrainMethod": (
                "heightfield values evaluated on the browser's fixed two-triangle 2 m planes"
            ),
            "sourceRasterMethod": (
                "existing EA 1 m DTM; bilinear interpolation between source pixel centers"
            ),
            "ways": profiles,
        },
        "referenceComparison": {
            "sourceId": comparison_manifest["sources"][0]["sourceId"],
            "edition": comparison_manifest["sources"][0]["edition"],
            "archiveSha256": comparison_source.record["archive"]["sha256"],
            "selectedTiles": [tile.to_dict() for tile in comparison_source.tiles],
            "panels": panel_records,
            "limitation": (
                "OS OpenMap–Local generalized symbols do not establish surveyed kerb width, "
                "carriageway edge, road elevation, or a survey-grade centerline offset."
            ),
        },
        "contexts": context_results,
        "overallFinding": {
            "classification": (
                "inconclusive for a product defect; source/representation limitation "
                "supported for steep estimated ribbons"
            ),
            "summary": (
                "The investigation reproduces source-to-package coordinates and surface areas, "
                "then compares terrain crossfall beneath estimated widths. A steep local terrain "
                "crossfall is observable; it does not show that the road was engineered at that "
                "grade or that the centerline is horizontally wrong. User screenshot camera pose "
                "and exact segment correspondence are unavailable, and the registered map is "
                "generalized. No renderer or GIS correction is evidenced by this diagnostic alone."
            ),
            "noCorrectionRecommended": True,
        },
        "browserEvidence": {
            "status": "separate Playwright capture is recorded in browser-evidence.json",
            "profile": "playwright.road-alignment.config.ts",
            "expectedScreenshots": [
                f"docs/milestones/screenshots/Road-alignment/{name}"
                for context in PANEL_CONTEXTS
                for name in (
                    f"{context['id']}-overhead.png",
                    f"{context['id']}-low-oblique.png",
                )
            ],
        },
        "limits": [
            "OSM is the dated 2026-10-16 extract; local street representation may differ "
            "from the user's screenshot date.",
            "Width is a configured visual estimate; raw width/lanes tags were not applied.",
            "The pinned coordinate operation reports 2 m accuracy and omits the preferred "
            "OSTN15 grid; this is not a measured alignment error.",
            "Terrain profiles do not establish surveyed road edges, carriageway engineering, "
            "bridges, or vertical design.",
            "Six browser poses are candidate reproductions; a street label alone does not "
            "establish exact correspondence to a user screenshot.",
            "The AOI remains selected_pending_coverage / not_checked; no completeness or "
            "approval finding is made.",
        ],
    }
    outputs = {
        "input-inventory.json": (
            json.dumps(inventory, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode("utf-8"),
        **panels,
    }
    inventory_after = input_inventory(project_root)
    if inventory_after != inventory:
        raise RoadAlignmentError("a source/package input changed during the read-only analysis")
    report["outputHashes"] = {
        filename: hashlib.sha256(content).hexdigest()
        for filename, content in sorted(outputs.items())
    }
    outputs["analysis.json"] = (
        json.dumps(_float_report(report), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    guard_output_directory(project_root, output_dir)
    _atomic_write(output_dir, outputs)
    return {
        "outputDir": output_dir.relative_to(project_root).as_posix(),
        "releaseId": CURRENT_RELEASE_ID,
        "inputInventorySha256": inventory["sha256"],
        "analysisSha256": hashlib.sha256(outputs["analysis.json"]).hexdigest(),
        "featureCount": len(imported.features),
        "profileCount": len(profiles),
        "meshFaces": mesh_report["faceCount"],
        "outputFiles": sorted(outputs),
    }
