"""Offline RFC 7946 overview derived from the validated local real-world packages."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from pyproj import Transformer
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon, shape

from . import __version__
from .aoi import generate_selection
from .building_export import (
    BuildingExportError,
    _configured_aoi_ring,
    _load_aoi_ring,
    _terrain_identity,
    validate_building_package,
)
from .building_sources import verify_building_source
from .config import AoiConfig, load_aoi_config, validate_stored_selection
from .coordinates import pinned_transformer
from .road_config import load_road_config
from .road_export import RoadExportError, validate_road_package

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TERRAIN_DIR = ROOT / "public/worlds/torquay-poc-001"
DEFAULT_ROADS_DIR = DEFAULT_TERRAIN_DIR / "roads"
DEFAULT_BUILDINGS_DIR = DEFAULT_TERRAIN_DIR / "buildings"
DEFAULT_OUTPUT_DIR = ROOT / "data/generated/overview"
DEFAULT_PUBLISHED_DIR = DEFAULT_TERRAIN_DIR / "overview"
DEFAULT_AOI_CONFIG = ROOT / "config/aoi.torquay.json"
DEFAULT_AOI_GEOJSON = ROOT / "docs/aoi-selection.geojson"
DEFAULT_SOURCE_MANIFEST = ROOT / "data/source-manifest.json"
DEFAULT_BUILDING_CONFIG = ROOT / "config/buildings.torquay.json"
DEFAULT_ROAD_CONFIG = ROOT / "config/roads.torquay.json"

OVERVIEW_MANIFEST_MAX_BYTES = 128 * 1024
OVERVIEW_GEOJSON_MAX_BYTES = 8 * 1024 * 1024
OVERVIEW_MAX_FEATURES = 10_000
OVERVIEW_MAX_POSITIONS = 250_000
OVERVIEW_COORDINATE_DECIMALS = 9
OVERVIEW_BOUNDARY_TOLERANCE_DEGREES = 1e-6
OVERVIEW_ASSETS = ("features.geojson", "manifest.json")


class OverviewExportError(ValueError):
    """Raised when overview inputs, geometry, or deterministic output is invalid."""


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _file_identity(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    length = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                length += len(chunk)
    except OSError as exc:
        raise OverviewExportError(f"cannot read input asset '{path}': {exc}") from exc
    return {"byteLength": length, "sha256": digest.hexdigest()}


def _read_json(
    path: Path, field: str, maximum: int = 8 * 1024 * 1024
) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise OverviewExportError(f"cannot read {field} '{path}': {exc}") from exc
    if len(raw) > maximum:
        raise OverviewExportError(f"{field} '{path}' exceeds the {maximum}-byte limit")
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise OverviewExportError(f"{field} '{path}' is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise OverviewExportError(f"{field} '{path}' must be a JSON object")
    return value, raw


def _repo_path(path: Path) -> Path:
    return (path if path.is_absolute() else ROOT / path).resolve()


def _path_key(path: Path) -> Path:
    """Resolve existing symlinks and normalize case for safe path comparisons."""
    try:
        return Path(os.path.normcase(str(path.resolve(strict=False))))
    except (OSError, RuntimeError) as exc:
        raise OverviewExportError(f"cannot canonicalize protected path '{path}': {exc}") from exc


def _is_symlink_or_junction(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", lambda: False)()
    return path.is_symlink() or is_junction


def _safe_output_path(path: Path) -> Path:
    """Resolve an output path only after rejecting symlink/junction components."""
    candidate = path if path.is_absolute() else ROOT / path
    try:
        absolute = Path(os.path.abspath(candidate))
    except (OSError, RuntimeError) as exc:
        raise OverviewExportError(f"cannot resolve output path '{candidate}': {exc}") from exc
    cursor = absolute
    while True:
        try:
            if _is_symlink_or_junction(cursor):
                raise OverviewExportError(
                    f"refusing output path with symbolic-link/junction component: '{cursor}'"
                )
        except OSError as exc:
            raise OverviewExportError(
                f"cannot inspect output path component '{cursor}': {exc}"
            ) from exc
        if cursor.parent == cursor:
            break
        cursor = cursor.parent
    return _path_key(absolute)


def _is_within_path(path: Path, parent: Path) -> bool:
    try:
        return os.path.commonpath((str(path), str(parent))) == str(parent)
    except ValueError:
        return False


def _assert_disjoint_paths(
    output: Path,
    *,
    input_directories: list[Path],
    input_files: list[Path],
    allowed_output_paths: tuple[Path, ...] = (),
) -> None:
    """Reject output overlap with all input locations before staging or writing."""
    output = _path_key(output)
    allowed_parent_pairs = {
        (_path_key(path), _path_key(path.parent)) for path in allowed_output_paths
    }
    for source in input_directories:
        resolved = _path_key(source)
        overlaps = _is_within_path(output, resolved) or _is_within_path(resolved, output)
        # The published overview occupies one reserved sibling namespace inside
        # the explicitly selected terrain directory. This exception applies
        # only to that exact parent; other protected ancestors (such as docs or
        # raw data) remain protected.
        matching_directory_count = sum(
            _path_key(directory) == resolved for directory in input_directories
        )
        if (
            (output, resolved) in allowed_parent_pairs
            and _is_within_path(output, resolved)
            and output != resolved
            and matching_directory_count == 1
        ):
            overlaps = False
        if overlaps:
            raise OverviewExportError(
                f"refusing unsafe nested input/output paths: output '{output}' "
                f"overlaps protected directory '{resolved}'"
            )
    for source in input_files:
        resolved = _path_key(source)
        if _is_within_path(output, resolved) or _is_within_path(resolved, output):
            raise OverviewExportError(
                f"refusing unsafe input/output paths: output '{output}' "
                f"overlaps protected file '{resolved}'"
            )


def _overview_input_directories(
    terrain_dir: Path, roads_dir: Path, buildings_dir: Path
) -> list[Path]:
    return [
        ROOT / "docs",
        ROOT / "config",
        ROOT / "data/raw",
        terrain_dir,
        roads_dir,
        buildings_dir,
    ]


def _overview_input_files(
    aoi_config_path: Path,
    aoi_geojson_path: Path,
    source_manifest_path: Path,
) -> list[Path]:
    return [
        aoi_config_path,
        aoi_geojson_path,
        source_manifest_path,
        DEFAULT_BUILDING_CONFIG,
        DEFAULT_ROAD_CONFIG,
    ]


def _validate_aoi(config_path: Path, geojson_path: Path) -> tuple[AoiConfig, list[list[float]]]:
    try:
        config = load_aoi_config(config_path)
        generated, _geojson, _markdown = generate_selection(config)
        validate_stored_selection(
            config,
            generated["aoi"]["center_easting_m"],
            generated["aoi"]["center_northing_m"],
            generated["aoi"]["bbox_m"],
        )
        ring = _load_aoi_ring(geojson_path)
        if ring != _configured_aoi_ring(config):
            raise OverviewExportError(
                "recorded AOI GeoJSON ring differs from the configured candidate"
            )
        return config, ring
    except OverviewExportError:
        raise
    except Exception as exc:
        raise OverviewExportError(f"AOI validation failed: {exc}") from exc


def _validate_terrain(
    terrain_dir: Path, config: AoiConfig
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_path = terrain_dir / "manifest.json"
    manifest, manifest_bytes = _read_json(
        manifest_path, "terrain manifest", OVERVIEW_MANIFEST_MAX_BYTES
    )
    if manifest.get("formatVersion") != 1 or manifest.get("id") != config.id:
        raise OverviewExportError("terrain manifest formatVersion/id is not the configured world")
    if manifest.get("worldType") != "real" or manifest.get("sourceCrs") != "EPSG:27700":
        raise OverviewExportError("overview requires the validated real EPSG:27700 terrain package")
    if manifest.get("axisConvention") != "+X east, +Y up, -Z north":
        raise OverviewExportError("terrain axisConvention is unsupported")
    aoi = manifest.get("aoi")
    if not isinstance(aoi, dict) or aoi.get("boundsM") != list(config.bbox_m):
        raise OverviewExportError("terrain AOI bounds differ from the configured pending candidate")
    origin = manifest.get("origin")
    heightfield = manifest.get("heightfield")
    extent = manifest.get("extentM")
    if (
        not isinstance(origin, dict)
        or not isinstance(heightfield, dict)
        or not isinstance(extent, dict)
    ):
        raise OverviewExportError("terrain origin, extentM and heightfield objects are required")
    try:
        raw_easting = origin["eastingM"]
        raw_northing = origin["northingM"]
        raw_elevation = origin["elevationM"]
        if any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            for value in (raw_easting, raw_northing, raw_elevation)
        ):
            raise ValueError("origin coordinates must be JSON numbers, not booleans")
        easting = float(raw_easting)
        northing = float(raw_northing)
        elevation = float(raw_elevation)
        columns = heightfield["columns"]
        rows = heightfield["rows"]
        spacing = float(heightfield["spacingM"])
        width = float(extent["width"])
        depth = float(extent["depth"])
        asset = heightfield["path"]
        size = heightfield["byteLength"]
        expected_hash = heightfield["sha256"]
    except (KeyError, TypeError, ValueError) as exc:
        raise OverviewExportError(
            f"terrain manifest grid/origin metadata is malformed: {exc}"
        ) from exc
    if any(
        not math.isfinite(value) for value in (easting, northing, elevation, spacing, width, depth)
    ):
        raise OverviewExportError("terrain origin and grid metadata must be finite")
    if (
        isinstance(columns, bool)
        or not isinstance(columns, int)
        or columns < 2
        or isinstance(rows, bool)
        or not isinstance(rows, int)
        or rows < 2
        or spacing <= 0
        or width <= 0
        or depth <= 0
        or abs((columns - 1) * spacing - width) > 1e-8
        or abs((rows - 1) * spacing - depth) > 1e-8
        or columns * rows * 4 != size
        or isinstance(size, bool)
        or not isinstance(size, int)
        or not isinstance(asset, str)
        or Path(asset).name != asset
        or not isinstance(expected_hash, str)
        or len(expected_hash) != 64
    ):
        raise OverviewExportError(
            "terrain heightfield dimensions, extent, path, or identity is invalid"
        )
    heightfield_path = terrain_dir / asset
    identity = _file_identity(heightfield_path)
    if identity != {"byteLength": size, "sha256": expected_hash}:
        raise OverviewExportError(
            "terrain heightfield bytes differ from its validated manifest identity"
        )
    terrain_identity = {
        "worldId": config.id,
        "manifestSha256": _sha256(manifest_bytes),
        "heightfield": {"path": asset, **identity},
        "origin": {"eastingM": easting, "northingM": northing, "elevationM": elevation},
        "extentM": {"width": width, "depth": depth},
        "grid": {"columns": columns, "rows": rows, "spacingM": spacing},
        "axisConvention": manifest["axisConvention"],
        "verticalReference": manifest.get("provenance", {}).get("verticalReference"),
        "provenance": manifest.get("provenance"),
    }
    try:
        _terrain_identity(terrain_dir, config)
    except Exception as exc:
        raise OverviewExportError(f"terrain identity validation failed: {exc}") from exc
    return manifest, terrain_identity


def _source_config_path(config_path: Path) -> Path:
    try:
        value = json.loads(config_path.read_text(encoding="utf-8"))
        relative = value["source"]["relative_path"]
        if (
            not isinstance(relative, str)
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
        ):
            raise ValueError("source path must be a repository-relative path")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise OverviewExportError(
            f"cannot resolve source path from '{config_path}': {exc}"
        ) from exc
    return (ROOT / relative).resolve()


def _normalize_ring(coordinates: list[list[float]], *, exterior: bool) -> list[list[float]]:
    if len(coordinates) < 4 or coordinates[0] != coordinates[-1]:
        raise OverviewExportError(
            "transformed polygon ring must be closed with at least four positions"
        )
    area = (
        sum(
            left[0] * right[1] - right[0] * left[1]
            for left, right in zip(coordinates[:-1], coordinates[1:], strict=True)
        )
        / 2.0
    )
    if not math.isfinite(area) or abs(area) <= 1e-16:
        raise OverviewExportError("transformed polygon ring has zero or invalid area")
    # RFC 7946: exteriors counter-clockwise; holes clockwise in longitude/latitude.
    if (area > 0) != exterior:
        coordinates = list(reversed(coordinates))
    return coordinates


def _coordinate_transformer() -> tuple[Transformer, Transformer, dict[str, Any]]:
    inverse, inverse_info = pinned_transformer(27700, 4326)
    forward, forward_info = pinned_transformer(4326, 27700)
    return (
        inverse,
        forward,
        {
            "axisOrder": "longitude-latitude for geographic input; easting-northing for BNG",
            "bngToWgs84": inverse_info.as_dict(),
            "wgs84ToBng": forward_info.as_dict(),
            "coordinateMeaning": (
                "Numerical inverse-transform consistency only; not absolute geodetic accuracy."
            ),
        },
    )


class _CoordinateWriter:
    def __init__(
        self, origin: dict[str, float], inverse: Transformer, forward: Transformer
    ) -> None:
        self.origin = origin
        self.inverse = inverse
        self.forward = forward
        self.position_count = 0
        self.maximum_roundtrip_m = 0.0

    def point(self, x: Any, z: Any, path: str) -> list[float]:
        if (
            isinstance(x, bool)
            or isinstance(z, bool)
            or not isinstance(x, (int, float))
            or not isinstance(z, (int, float))
            or not math.isfinite(x)
            or not math.isfinite(z)
        ):
            raise OverviewExportError(f"{path} must be a finite numeric local XZ point")
        easting = self.origin["eastingM"] + float(x)
        northing = self.origin["northingM"] - float(z)
        try:
            longitude, latitude = self.inverse.transform(easting, northing, errcheck=True)
        except Exception as exc:
            raise OverviewExportError(f"{path} BNG-to-WGS84 transform failed: {exc}") from exc
        longitude = round(float(longitude), OVERVIEW_COORDINATE_DECIMALS)
        latitude = round(float(latitude), OVERVIEW_COORDINATE_DECIMALS)
        if not math.isfinite(longitude) or not math.isfinite(latitude):
            raise OverviewExportError(f"{path} transformed to non-finite WGS84 coordinates")
        try:
            check_e, check_n = self.forward.transform(longitude, latitude, errcheck=True)
        except Exception as exc:
            raise OverviewExportError(f"{path} WGS84 round-trip check failed: {exc}") from exc
        error = math.hypot(float(check_e) - easting, float(check_n) - northing)
        self.maximum_roundtrip_m = max(self.maximum_roundtrip_m, error)
        if error > 0.02:
            raise OverviewExportError(
                f"{path} numerical coordinate round-trip {error:.6f} m exceeds 0.02 m"
            )
        self.position_count += 1
        if self.position_count > OVERVIEW_MAX_POSITIONS:
            raise OverviewExportError("overview exceeds the 250,000-position limit")
        return [longitude, latitude]


def _ring_from_local(
    writer: _CoordinateWriter, points: Any, field: str, *, exterior: bool
) -> list[list[float]]:
    if not isinstance(points, list):
        raise OverviewExportError(f"{field} must be an array of local XZ points")
    ring = [
        writer.point(point[0], point[1], f"{field}[{index}]")
        for index, point in enumerate(points)
        if isinstance(point, (list, tuple)) and len(point) == 2
    ]
    if len(ring) != len(points):
        raise OverviewExportError(f"{field} contains a malformed position")
    return _normalize_ring(ring, exterior=exterior)


def _build_features(
    ring: list[list[float]],
    origin: dict[str, float],
    road_features: list[dict[str, Any]],
    building_features: list[dict[str, Any]],
    inverse: Transformer,
    forward: Transformer,
) -> tuple[dict[str, Any], dict[str, int], dict[str, int], float]:
    writer = _CoordinateWriter(origin, inverse, forward)
    # The exact recorded AOI polygon is the geographic registration source and is copied verbatim.
    features: list[dict[str, Any]] = [
        {
            "type": "Feature",
            "id": "aoi:torquay-poc-001",
            "properties": {
                "role": "aoi",
                "name": "TQ1 4HN candidate AOI",
                "selectionStatus": "selected_pending_coverage",
                "coverageStatus": "not_checked",
            },
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        }
    ]
    road_count = 0
    roads_without_aoi_centerline = 0
    for feature in road_features:
        road_id = feature.get("id")
        parts = feature.get("centerlinePartsXZ")
        if not isinstance(road_id, str) or not isinstance(parts, list):
            raise OverviewExportError(
                "roads package feature has malformed stable identity or parts"
            )
        if not parts:
            # The validated road surface may intersect the AOI even when its centerline
            # does not. The geographic overview shows clipped centerlines only.
            roads_without_aoi_centerline += 1
            continue
        geographic_parts = []
        for part_index, part in enumerate(parts):
            if not isinstance(part, list) or len(part) < 2:
                raise OverviewExportError(
                    f"road {road_id} part {part_index} must contain at least two points"
                )
            geographic_parts.append(
                [
                    writer.point(point[0], point[1], f"road {road_id} part {part_index}")
                    for point in part
                ]
            )
        if not geographic_parts:
            raise OverviewExportError(f"road {road_id} has no valid clipped centerline parts")
        props = feature.get("sourceTags")
        props = props if isinstance(props, dict) else {}
        features.append(
            {
                "type": "Feature",
                "id": f"road:{road_id}",
                "properties": {
                    "role": "road",
                    "sourceId": road_id,
                    "name": props.get("name") if isinstance(props.get("name"), str) else None,
                    "highway": feature.get("highway"),
                    "displayGroup": feature.get("displayGroup"),
                },
                "geometry": {"type": "MultiLineString", "coordinates": geographic_parts},
            }
        )
        road_count += 1
    building_count = 0
    for feature in building_features:
        building_id = feature.get("id")
        geometry = feature.get("geometry")
        polygons = geometry.get("polygons") if isinstance(geometry, dict) else None
        if not isinstance(building_id, str) or not isinstance(polygons, list) or not polygons:
            raise OverviewExportError(
                "building package feature has malformed stable identity or polygons"
            )
        geographic_polygons = []
        for polygon_index, polygon in enumerate(polygons):
            if not isinstance(polygon, dict):
                raise OverviewExportError(
                    f"building {building_id} polygon {polygon_index} is invalid"
                )
            exterior = _ring_from_local(
                writer,
                polygon.get("exteriorXZ"),
                f"building {building_id} exterior {polygon_index}",
                exterior=True,
            )
            holes = polygon.get("interiorRingsXZ")
            if not isinstance(holes, list):
                raise OverviewExportError(
                    f"building {building_id} holes {polygon_index} must be an array"
                )
            geographic_polygons.append(
                [exterior]
                + [
                    _ring_from_local(
                        writer,
                        hole,
                        f"building {building_id} hole {polygon_index}/{hole_index}",
                        exterior=False,
                    )
                    for hole_index, hole in enumerate(holes)
                ]
            )
        source = feature.get("source")
        osm_id = source.get("osmId") if isinstance(source, dict) else None
        features.append(
            {
                "type": "Feature",
                "id": f"building:{building_id}",
                "properties": {
                    "role": "building",
                    "sourceId": building_id,
                    "osmId": osm_id
                    if isinstance(osm_id, int) and not isinstance(osm_id, bool)
                    else None,
                },
                "geometry": {"type": "MultiPolygon", "coordinates": geographic_polygons},
            }
        )
        building_count += 1
    if len(features) > OVERVIEW_MAX_FEATURES:
        raise OverviewExportError("overview exceeds the 10,000-feature limit")
    payload = {"type": "FeatureCollection", "features": features}
    _validate_geojson(payload, ring)
    counts = {
        "aoi": 1,
        "roads": road_count,
        "buildings": building_count,
        "total": len(features),
        "roadsWithoutAoiCenterline": roads_without_aoi_centerline,
    }
    role_positions = {
        "aoi": len(ring),
        "roads": 0,
        "buildings": 0,
        "total": writer.position_count + len(ring),
    }
    for feature in features[1:]:
        role = feature["properties"]["role"]
        role_positions[role + "s" if role == "road" else role + "s"] += _count_positions(
            feature["geometry"]
        )
    return payload, counts, role_positions, writer.maximum_roundtrip_m


def _count_positions(geometry: dict[str, Any]) -> int:
    coordinates = geometry.get("coordinates")

    def descend(value: Any) -> int:
        if (
            isinstance(value, list)
            and len(value) == 2
            and all(isinstance(item, (int, float)) for item in value)
        ):
            return 1
        if isinstance(value, list):
            return sum(descend(item) for item in value)
        return 0

    return descend(coordinates)


def _validate_geojson(payload: dict[str, Any], ring: list[list[float]]) -> None:
    features = payload.get("features")
    if not isinstance(features, list) or not features or len(features) > OVERVIEW_MAX_FEATURES:
        raise OverviewExportError("GeoJSON features must be a bounded non-empty array")
    aoi = Polygon(ring)
    if not aoi.is_valid or aoi.is_empty:
        raise OverviewExportError("recorded AOI geographic ring is invalid")
    seen: set[str] = set()
    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise OverviewExportError(f"GeoJSON feature {index} is malformed")
        identity = feature.get("id")
        props = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(identity, str) or identity in seen:
            raise OverviewExportError(f"GeoJSON feature {index} has missing or duplicate ID")
        seen.add(identity)
        if not isinstance(props, dict) or not isinstance(geometry, dict):
            raise OverviewExportError(f"GeoJSON feature {identity} lacks properties or geometry")
        if props.get("role") == "aoi":
            if geometry.get("type") != "Polygon" or geometry.get("coordinates") != [ring]:
                raise OverviewExportError(
                    "AOI GeoJSON feature must retain the recorded boundary verbatim"
                )
            continue
        coordinates = geometry.get("coordinates")

        def check_positions(value: Any, path: str) -> None:
            if (
                isinstance(value, list)
                and len(value) == 2
                and all(
                    isinstance(item, (int, float)) and not isinstance(item, bool) for item in value
                )
            ):
                longitude, latitude = value
                if not math.isfinite(longitude) or not math.isfinite(latitude):
                    raise OverviewExportError(f"{path} contains a non-finite coordinate")
                if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
                    raise OverviewExportError(f"{path} is outside WGS84 coordinate ranges")
                return
            if not isinstance(value, list) or not value:
                raise OverviewExportError(f"{path} has malformed coordinate nesting")
            for child_index, child in enumerate(value):
                check_positions(child, f"{path}[{child_index}]")

        check_positions(coordinates, f"GeoJSON feature {identity} coordinates")
        try:
            geom = shape(geometry)
        except Exception as exc:
            raise OverviewExportError(
                f"GeoJSON feature {identity} geometry is invalid: {exc}"
            ) from exc
        if geom.is_empty or not geom.is_valid:
            raise OverviewExportError(f"GeoJSON feature {identity} has invalid geometry")
        if props.get("role") == "road" and not isinstance(geom, (LineString, MultiLineString)):
            raise OverviewExportError(f"road {identity} must retain line geometry")
        if props.get("role") == "building" and not isinstance(geom, MultiPolygon):
            raise OverviewExportError(f"building {identity} must retain MultiPolygon geometry")
        if props.get("role") not in {"road", "building"}:
            raise OverviewExportError(f"GeoJSON feature {identity} has unsupported role")
        if not aoi.buffer(OVERVIEW_BOUNDARY_TOLERANCE_DEGREES).covers(geom):
            raise OverviewExportError(
                f"GeoJSON feature {identity} extends outside the recorded candidate AOI"
            )
        if isinstance(geom, (Polygon, MultiPolygon)):
            polygons = [geom] if isinstance(geom, Polygon) else list(geom.geoms)
            for polygon in polygons:
                if not polygon.exterior.is_ccw:
                    raise OverviewExportError(
                        f"building {identity} exterior winding is not RFC 7946 CCW"
                    )
                if any(ring.is_ccw for ring in polygon.interiors):
                    raise OverviewExportError(
                        f"building {identity} hole winding is not RFC 7946 CW"
                    )
    if len(seen) != len(features):
        raise OverviewExportError("GeoJSON feature IDs are not unique")


def _validate_optional_packages(
    layers: tuple[str, ...],
    *,
    terrain_dir: Path,
    roads_dir: Path,
    buildings_dir: Path,
    config: AoiConfig,
    ring: list[list[float]],
    source_manifest: Path,
    aoi_geojson: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    road_features: list[dict[str, Any]] = []
    building_features: list[dict[str, Any]] = []
    if "roads" in layers:
        try:
            road_config, _root, _raw = load_road_config(DEFAULT_ROAD_CONFIG)
            source_path = _source_config_path(DEFAULT_ROAD_CONFIG)
            validate_road_package(
                roads_dir,
                expected_aoi=config,
                expected_aoi_ring=ring,
                terrain_package_path=terrain_dir,
                source_path=source_path,
                source_manifest_path=source_manifest,
                aoi_geojson_path=aoi_geojson,
                road_config=road_config,
            )
            road_payload, _ = _read_json(
                roads_dir / "roads.json", "roads payload", 32 * 1024 * 1024
            )
            road_features = road_payload["features"]
        except (RoadExportError, OSError, ValueError) as exc:
            raise OverviewExportError(
                f"roads input package validation failed at '{roads_dir}': {exc}"
            ) from exc
    if "buildings" in layers:
        try:
            source_path = _source_config_path(DEFAULT_BUILDING_CONFIG)
            verify_building_source(source_path, source_manifest)
            validate_building_package(
                buildings_dir,
                expected_aoi=config,
                expected_aoi_ring=ring,
                terrain_package_path=terrain_dir,
                source_path=source_path,
                source_manifest_path=source_manifest,
            )
            payload, _ = _read_json(
                buildings_dir / "buildings.json", "buildings payload", 32 * 1024 * 1024
            )
            building_features = payload["buildings"]
        except (BuildingExportError, OSError, ValueError, KeyError, TypeError) as exc:
            raise OverviewExportError(
                f"buildings input package validation failed at '{buildings_dir}': {exc}"
            ) from exc
    return road_features, building_features


def _layer_identity(
    package_dir: Path, kind: str, expected_terrain_manifest_sha256: str
) -> dict[str, Any]:
    manifest, manifest_bytes = _read_json(package_dir / "manifest.json", f"{kind} manifest")
    if kind == "roads":
        assets = manifest.get("assets")
        if not isinstance(assets, dict):
            raise OverviewExportError("roads manifest assets object is missing")
        payload_name = "roads.json"
        payload_info = assets.get("roads")
        qa_info = assets.get("qa")
        source = manifest.get("source")
    else:
        payload_name = "buildings.json"
        payload_info = manifest.get("buildings")
        qa_info = manifest.get("qaReport")
        source = manifest.get("provenance")
        if not isinstance(source, dict):
            raise OverviewExportError("buildings manifest provenance object is missing")
    if not isinstance(payload_info, dict) or not isinstance(qa_info, dict):
        raise OverviewExportError(f"{kind} package identity descriptors are missing")
    if kind == "roads":
        road_terrain_identity = manifest.get("terrainIdentity")
        road_terrain_hash = (
            road_terrain_identity.get("manifestSha256")
            if isinstance(road_terrain_identity, dict)
            else None
        )
        if road_terrain_hash != expected_terrain_manifest_sha256:
            raise OverviewExportError("roads manifest is bound to a different terrain package")
    if (
        not isinstance(expected_terrain_manifest_sha256, str)
        or len(expected_terrain_manifest_sha256) != 64
    ):
        raise OverviewExportError("validated terrain manifest hash is malformed")
    payload = _file_identity(package_dir / payload_name)
    qa = _file_identity(package_dir / str(qa_info.get("path", "qa.json")))
    if payload != {
        "byteLength": payload_info.get("byteLength"),
        "sha256": payload_info.get("sha256"),
    }:
        raise OverviewExportError(
            f"{kind} package payload differs from its validated manifest identity"
        )
    if qa != {"byteLength": qa_info.get("byteLength"), "sha256": qa_info.get("sha256")}:
        raise OverviewExportError(f"{kind} package QA differs from its validated manifest identity")
    return {
        "manifestSha256": _sha256(manifest_bytes),
        "payload": {"path": payload_name, **payload},
        "qa": {"path": str(qa_info.get("path", "qa.json")), **qa},
        "source": source,
        # Buildings are validated against the loaded terrain manifest above. The
        # current building manifest records detailed terrain identity but has a
        # legacy top-level terrainManifestSha256:null field; bind the overview to
        # the actual validated terrain manifest instead of copying that null.
        "terrainManifestSha256": expected_terrain_manifest_sha256,
    }


def _derive_package(
    *,
    terrain_dir: Path,
    roads_dir: Path,
    buildings_dir: Path,
    layers: tuple[str, ...],
    aoi_config_path: Path,
    aoi_geojson_path: Path,
    source_manifest_path: Path,
) -> dict[str, bytes]:
    if (
        not layers
        or layers[0] != "aoi"
        or len(set(layers)) != len(layers)
        or any(layer not in {"aoi", "roads", "buildings"} for layer in layers)
    ):
        raise OverviewExportError(
            "layers must contain aoi and optional roads/buildings exactly once"
        )
    config, ring = _validate_aoi(aoi_config_path, aoi_geojson_path)
    terrain, terrain_identity = _validate_terrain(terrain_dir, config)
    road_features, building_features = _validate_optional_packages(
        layers,
        terrain_dir=terrain_dir,
        roads_dir=roads_dir,
        buildings_dir=buildings_dir,
        config=config,
        ring=ring,
        source_manifest=source_manifest_path,
        aoi_geojson=aoi_geojson_path,
    )
    inverse, forward, operation = _coordinate_transformer()
    origin = terrain_identity["origin"]
    payload, counts, position_counts, max_roundtrip = _build_features(
        ring,
        origin,
        road_features,
        building_features,
        inverse,
        forward,
    )
    geojson_bytes = _json_bytes(payload)
    if len(geojson_bytes) > OVERVIEW_GEOJSON_MAX_BYTES:
        raise OverviewExportError("features.geojson exceeds the 8 MiB limit")
    if sum(position_counts.values()) > OVERVIEW_MAX_POSITIONS:
        raise OverviewExportError("overview exceeds the 250,000-position limit")
    longitudes = [position[0] for position in ring]
    latitudes = [position[1] for position in ring]
    map_bounds = [min(longitudes), min(latitudes), max(longitudes), max(latitudes)]
    optional = {}
    if "roads" in layers:
        optional["roads"] = _layer_identity(roads_dir, "roads", terrain_identity["manifestSha256"])
    if "buildings" in layers:
        optional["buildings"] = _layer_identity(
            buildings_dir, "buildings", terrain_identity["manifestSha256"]
        )
    provenance = terrain.get("provenance", {})
    source_manifest, _ = _read_json(source_manifest_path, "source manifest", 1024 * 1024)
    osm_section = source_manifest.get("osm", {})
    osm_product = osm_section.get("product", {}) if isinstance(osm_section, dict) else {}
    osm_sources = osm_section.get("sources", []) if isinstance(osm_section, dict) else []
    osm_source = osm_sources[0] if isinstance(osm_sources, list) and osm_sources else {}
    if not isinstance(osm_source, dict) or not isinstance(osm_product, dict):
        raise OverviewExportError("OSM source manifest product/source metadata is malformed")
    manifest = {
        "formatVersion": 1,
        "worldId": config.id,
        "worldType": "real",
        "packageType": "torquay-geographic-overview",
        "projection": "mercator",
        "aoi": {
            "crs": "EPSG:27700",
            "boundsM": list(config.bbox_m),
            "centerBngM": list(config.center_bng_m),
            "boundaryWgs84": {
                "crs": "EPSG:4326",
                "coordinateOrder": "longitude-latitude",
                "ring": ring,
            },
            "selectionStatus": config.selection_status,
            "coverageStatus": config.coverage_status,
        },
        "mapView": {
            "centerWgs84": [
                (map_bounds[0] + map_bounds[2]) / 2,
                (map_bounds[1] + map_bounds[3]) / 2,
            ],
            "boundsWgs84": map_bounds,
            "bearingDegrees": 0,
            "pitchDegrees": 0,
            "fitPaddingPx": 18,
        },
        "includedLayers": list(layers),
        "terrainIdentity": terrain_identity,
        "optionalLayerIdentities": optional,
        "coordinateOperation": operation,
        "coordinatePolicy": {
            "localToBng": "E=eastingOrigin+x; N=northingOrigin-z",
            "precisionDecimalPlaces": OVERVIEW_COORDINATE_DECIMALS,
            "maximumObservedRoundTripErrorM": max_roundtrip,
            "maximumAcceptedRoundTripErrorM": 0.02,
            "aoiContainmentToleranceDegrees": OVERVIEW_BOUNDARY_TOLERANCE_DEGREES,
            "interpretation": (
                "Numerical inverse-transform consistency only; the pinned operation "
                "reports 2 m and is not survey-accurate."
            ),
        },
        "counts": {
            "featuresByRole": {key: counts[key] for key in ("aoi", "roads", "buildings", "total")},
            "positionsByRole": position_counts,
        },
        "omissions": {
            "roadsWithoutAoiCenterline": counts["roadsWithoutAoiCenterline"],
            "roadsPolicy": (
                "Validated source roads with no clipped centerline are omitted from "
                "the overview; buffered road surfaces are not represented here."
            ),
        },
        "features": {
            "path": "features.geojson",
            "byteLength": len(geojson_bytes),
            "sha256": _sha256(geojson_bytes),
        },
        "limits": {
            "manifestMaxBytes": OVERVIEW_MANIFEST_MAX_BYTES,
            "featuresMaxBytes": OVERVIEW_GEOJSON_MAX_BYTES,
            "maxFeatures": OVERVIEW_MAX_FEATURES,
            "maxPositions": OVERVIEW_MAX_POSITIONS,
        },
        "generator": {
            "name": "torquay_pipeline.overview_export",
            "version": __version__,
            "format": "RFC 7946",
            "serialization": "UTF-8 compact JSON with a final newline",
        },
        "sources": {
            "terrain": {
                "publisher": provenance.get("publisher"),
                "product": provenance.get("product"),
                "catalogueUrl": provenance.get("catalogueUrl"),
                "surveyPeriod": provenance.get("productSurveyPeriod"),
                "licence": provenance.get("licence"),
                "licenceUrl": provenance.get("licenceUrl"),
                "attribution": provenance.get("attribution"),
            },
            **(
                {
                    "osm": {
                        "publisher": osm_product.get("publisher"),
                        "product": osm_product.get("name"),
                        "downloadPageUrl": osm_product.get("download_page_url"),
                        "fileUrl": osm_source.get("download_url"),
                        "extractTimestamp": osm_source.get("replication_data_timestamp"),
                        "sha256": osm_source.get("sha256"),
                        "licence": osm_product.get("licence"),
                        "licenceUrl": osm_product.get("licence_url"),
                        "attribution": osm_product.get("credit"),
                    }
                }
                if "roads" in layers or "buildings" in layers
                else {}
            ),
            "mapLibre": {
                "licence": "BSD 3-Clause License",
                "licenceUrl": "https://github.com/maplibre/maplibre-gl-js/blob/main/LICENSE.txt",
                "attribution": "MapLibre",
            },
        },
        "coverage": {
            "selectionStatus": config.selection_status,
            "coverageStatus": config.coverage_status,
            "note": (
                "Mapped feature counts and this fixed overview do not establish source "
                "completeness or approve/freeze the candidate AOI."
            ),
        },
    }
    manifest_bytes = _json_bytes(manifest)
    if len(manifest_bytes) > OVERVIEW_MANIFEST_MAX_BYTES:
        raise OverviewExportError("manifest.json exceeds the 128 KiB limit")
    return {"features.geojson": geojson_bytes, "manifest.json": manifest_bytes}


def _write_package(output_dir: Path, artifacts: dict[str, bytes]) -> None:
    parent = output_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    backup = parent / f".{output_dir.name}-backup-{uuid.uuid4().hex}"
    if backup.exists() or backup.is_symlink():
        raise OverviewExportError(f"refusing to use pre-existing overview backup path '{backup}'")
    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}-stage-", dir=parent))
    moved = False
    try:
        for name in ("features.geojson", "manifest.json"):
            path = stage / name
            with path.open("xb") as handle:
                handle.write(artifacts[name])
                handle.flush()
                os.fsync(handle.fileno())
        for name, data in artifacts.items():
            if (stage / name).read_bytes() != data:
                raise OverviewExportError(f"staged {name} differs from deterministic output")
        if output_dir.exists():
            if output_dir.is_symlink() or not output_dir.is_dir():
                raise OverviewExportError(
                    f"refusing to replace non-directory output '{output_dir}'"
                )
            os.replace(output_dir, backup)
            moved = True
        os.replace(stage, output_dir)
    except Exception as exc:
        if moved and backup.exists() and not output_dir.exists():
            os.replace(backup, output_dir)
        if isinstance(exc, OverviewExportError):
            raise
        raise OverviewExportError(
            f"could not atomically replace overview package '{output_dir}': {exc}"
        ) from exc
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
    if moved and backup.exists():
        shutil.rmtree(backup)


def build_overview_package(
    *,
    terrain_dir: Path = DEFAULT_TERRAIN_DIR,
    roads_dir: Path = DEFAULT_ROADS_DIR,
    buildings_dir: Path = DEFAULT_BUILDINGS_DIR,
    layers: tuple[str, ...] = ("aoi", "roads", "buildings"),
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    aoi_config_path: Path = DEFAULT_AOI_CONFIG,
    aoi_geojson_path: Path = DEFAULT_AOI_GEOJSON,
    source_manifest_path: Path = DEFAULT_SOURCE_MANIFEST,
) -> dict[str, Any]:
    terrain_dir, roads_dir, buildings_dir = map(_repo_path, (terrain_dir, roads_dir, buildings_dir))
    output_dir = _safe_output_path(output_dir)
    aoi_config_path, aoi_geojson_path, source_manifest_path = map(
        _repo_path, (aoi_config_path, aoi_geojson_path, source_manifest_path)
    )
    _assert_disjoint_paths(
        output_dir,
        input_directories=_overview_input_directories(terrain_dir, roads_dir, buildings_dir),
        input_files=_overview_input_files(aoi_config_path, aoi_geojson_path, source_manifest_path),
    )
    artifacts = _derive_package(
        terrain_dir=terrain_dir,
        roads_dir=roads_dir,
        buildings_dir=buildings_dir,
        layers=layers,
        aoi_config_path=aoi_config_path,
        aoi_geojson_path=aoi_geojson_path,
        source_manifest_path=source_manifest_path,
    )
    _write_package(output_dir, artifacts)
    return {
        "outputDirectory": str(output_dir),
        "layers": list(layers),
        "files": {
            name: {"byteLength": len(data), "sha256": _sha256(data)}
            for name, data in artifacts.items()
        },
        "status": "deterministic overview written; candidate AOI remains pending",
    }


def validate_overview_package(
    package_dir: Path,
    *,
    terrain_dir: Path = DEFAULT_TERRAIN_DIR,
    roads_dir: Path = DEFAULT_ROADS_DIR,
    buildings_dir: Path = DEFAULT_BUILDINGS_DIR,
    aoi_config_path: Path = DEFAULT_AOI_CONFIG,
    aoi_geojson_path: Path = DEFAULT_AOI_GEOJSON,
    source_manifest_path: Path = DEFAULT_SOURCE_MANIFEST,
) -> dict[str, Any]:
    package_dir = _repo_path(package_dir)
    terrain_dir, roads_dir, buildings_dir = map(_repo_path, (terrain_dir, roads_dir, buildings_dir))
    aoi_config_path, aoi_geojson_path, source_manifest_path = map(
        _repo_path, (aoi_config_path, aoi_geojson_path, source_manifest_path)
    )
    manifest, manifest_bytes = _read_json(
        package_dir / "manifest.json", "overview manifest", OVERVIEW_MANIFEST_MAX_BYTES
    )
    if (
        manifest.get("formatVersion") != 1
        or manifest.get("worldId") != "torquay-poc-001"
        or manifest.get("packageType") != "torquay-geographic-overview"
    ):
        raise OverviewExportError(
            "overview manifest formatVersion/worldId/packageType is unsupported"
        )
    layers = manifest.get("includedLayers")
    if not isinstance(layers, list) or any(not isinstance(layer, str) for layer in layers):
        raise OverviewExportError("manifest.includedLayers must be an array of strings")
    features = manifest.get("features")
    if not isinstance(features, dict) or features.get("path") != "features.geojson":
        raise OverviewExportError("manifest.features.path must be package-local features.geojson")
    content = (package_dir / "features.geojson").read_bytes()
    if (
        len(content) > OVERVIEW_GEOJSON_MAX_BYTES
        or len(content) != features.get("byteLength")
        or _sha256(content) != features.get("sha256")
    ):
        raise OverviewExportError("features.geojson length or SHA-256 differs from the manifest")
    expected = _derive_package(
        terrain_dir=terrain_dir,
        roads_dir=roads_dir,
        buildings_dir=buildings_dir,
        layers=tuple(layers),
        aoi_config_path=aoi_config_path,
        aoi_geojson_path=aoi_geojson_path,
        source_manifest_path=source_manifest_path,
    )
    if expected["features.geojson"] != content:
        raise OverviewExportError(
            "features.geojson differs from deterministic re-derivation from "
            "validated source packages"
        )
    if expected["manifest.json"] != manifest_bytes:
        raise OverviewExportError(
            "overview manifest differs from deterministic re-derivation and "
            "current input identities"
        )
    parsed = json.loads(content)
    _validate_geojson(parsed, manifest["aoi"]["boundaryWgs84"]["ring"])
    return {
        "status": "valid deterministic overview derived from current local packages",
        "packageDirectory": str(package_dir),
        "manifestSha256": _sha256(manifest_bytes),
        "featuresSha256": _sha256(content),
        "featuresByteLength": len(content),
        "featureCounts": manifest["counts"]["featuresByRole"],
        "includedLayers": layers,
    }
