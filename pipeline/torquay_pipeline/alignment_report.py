"""Registered map panels and an integrity-bound, manually reviewed alignment report."""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle
from rasterio.windows import Window
from shapely.geometry import LineString, Point, Polygon

from .comparison_sources import (
    ComparisonSourceError,
    VerifiedComparisonSource,
    verify_comparison_source,
)
from .coordinates import pinned_transformer, transform_bng_to_wgs84

AOI_BOUNDS_M = (
    290608.9018176432,
    64853.48350844931,
    291608.9018176432,
    65853.48350844931,
)
SCREENING_THRESHOLD_M = 10.0
OS_ATTRIBUTION = "Contains Ordnance Survey data © Crown copyright and database right 2026"
OS_LICENCE_URL = "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
OSM_ATTRIBUTION = "© OpenStreetMap contributors; extract provided by Geofabrik GmbH"
OSM_LICENCE_URL = "https://www.openstreetmap.org/copyright"
AXIS_MAPPING = "E=originE+x; N=originN-z; north is up-screen and -Z in the world."
RASTER_REGISTRATION = (
    "AREA_OR_POINT=Area; pixel centers are left+column+0.5 m and top-row-0.5 m. "
    "Source imagery is read as-is without warp/resampling."
)
PIXEL_EDGE_REGISTRATION = "AREA_OR_POINT=Area; source raster is not warped or resampled"


class AlignmentReportError(ValueError):
    """Raised when comparison config, local assets, or report evidence is invalid."""


@dataclass(frozen=True)
class RasterWindow:
    """Exact palette raster pixels with their pixel-edge bounds and pixel registration."""

    indices: np.ndarray
    palette: np.ndarray
    bounds_m: tuple[float, float, float, float]
    requested_bounds_m: tuple[float, float, float, float]
    width: int
    height: int
    tile_names: tuple[str, ...]

    def rgba(self) -> np.ndarray:
        return self.palette[self.indices]


@dataclass(frozen=True)
class LocalPackages:
    """Integrity-verified existing terrain, road, and building package data."""

    terrain_manifest: dict[str, Any]
    terrain_manifest_sha256: str
    road_manifest: dict[str, Any]
    road_manifest_sha256: str
    road_payload: dict[str, Any]
    road_payload_sha256: str
    road_qa_sha256: str
    building_manifest: dict[str, Any]
    building_manifest_sha256: str
    building_payload: dict[str, Any]
    building_payload_sha256: str
    building_qa_sha256: str


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hash_path(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise AlignmentReportError(f"cannot read report input '{path}': {exc}") from exc
    return digest.hexdigest()


def _read_json(path: Path, field: str) -> tuple[dict[str, Any], bytes]:
    try:
        content = path.read_bytes()
        value = json.loads(content)
    except OSError as exc:
        raise AlignmentReportError(f"cannot read {field} '{path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AlignmentReportError(f"{field} '{path}' is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise AlignmentReportError(f"{field} '{path}' must contain a JSON object")
    return value, content


def _safe_asset(package_dir: Path, relative: object, field: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise AlignmentReportError(f"{field} must be a safe relative asset path")
    parts = Path(relative).parts
    if Path(relative).is_absolute() or any(part in {"", ".", ".."} for part in parts):
        raise AlignmentReportError(f"{field} must be a safe relative asset path")
    candidate = package_dir.joinpath(*parts).resolve()
    try:
        candidate.relative_to(package_dir.resolve())
    except ValueError as exc:
        raise AlignmentReportError(f"{field} escapes its package directory") from exc
    return candidate


def _verify_descriptor(
    package_dir: Path, descriptor: object, field: str
) -> tuple[dict[str, Any], bytes]:
    if not isinstance(descriptor, dict):
        raise AlignmentReportError(f"{field} descriptor must be an object")
    path = _safe_asset(package_dir, descriptor.get("path"), f"{field}.path")
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise AlignmentReportError(
            f"{field} asset '{path}' is missing or unreadable: {exc}"
        ) from exc
    digest = _hash_bytes(content)
    if descriptor.get("byteLength") != len(content) or descriptor.get("sha256") != digest:
        raise AlignmentReportError(
            f"{field} asset byte length or SHA-256 differs from its manifest"
        )
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AlignmentReportError(f"{field} asset '{path}' is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise AlignmentReportError(f"{field} asset '{path}' must contain a JSON object")
    return value, content


def load_local_packages(
    terrain_package_dir: Path, road_package_dir: Path, building_package_dir: Path
) -> LocalPackages:
    """Read only the already-published local packages and verify their hashes/identity."""
    terrain_path = terrain_package_dir / "manifest.json"
    terrain, terrain_bytes = _read_json(terrain_path, "terrain manifest")
    if terrain.get("id") != "torquay-poc-001" or terrain.get("worldType") != "real":
        raise AlignmentReportError("comparison requires the reviewed local real terrain package")
    terrain_identity = terrain.get("origin")
    if not isinstance(terrain_identity, dict):
        raise AlignmentReportError("terrain manifest origin is missing or malformed")

    road_path = road_package_dir / "manifest.json"
    road_manifest, road_manifest_bytes = _read_json(road_path, "road package manifest")
    road_assets = road_manifest.get("assets")
    if not isinstance(road_assets, dict):
        raise AlignmentReportError("road package manifest assets are missing")
    road_payload, road_payload_bytes = _verify_descriptor(
        road_package_dir, road_assets.get("roads"), "road payload"
    )
    _road_qa, road_qa_bytes = _verify_descriptor(road_package_dir, road_assets.get("qa"), "road QA")

    building_path = building_package_dir / "manifest.json"
    building_manifest, building_manifest_bytes = _read_json(
        building_path, "building package manifest"
    )
    building_payload, building_payload_bytes = _verify_descriptor(
        building_package_dir, building_manifest.get("buildings"), "building payload"
    )
    _building_qa, building_qa_bytes = _verify_descriptor(
        building_package_dir, building_manifest.get("qaReport"), "building QA"
    )

    for label, manifest in (("road", road_manifest), ("building", building_manifest)):
        if manifest.get("worldId") != terrain.get("id"):
            raise AlignmentReportError(f"{label} package worldId differs from the terrain world")
        if manifest.get("sourceCrs") != "EPSG:27700":
            raise AlignmentReportError(f"{label} package is not in EPSG:27700")
        aoi = manifest.get("aoi")
        if not isinstance(aoi, dict) or aoi.get("boundsM") != list(AOI_BOUNDS_M):
            raise AlignmentReportError(
                f"{label} package AOI bounds differ from the reviewed 1 km AOI"
            )
        if (
            aoi.get("selectionStatus") != "selected_pending_coverage"
            or aoi.get("coverageStatus") != "not_checked"
        ):
            raise AlignmentReportError(f"{label} package must preserve the pending AOI status")
        if manifest.get("terrainIdentity", {}).get("worldId") != terrain.get("id"):
            raise AlignmentReportError(
                f"{label} package terrain identity differs from the actual terrain"
            )
        if manifest.get("terrainIdentity", {}).get("heightfieldSha256") != terrain.get(
            "heightfield", {}
        ).get("sha256"):
            raise AlignmentReportError(f"{label} package terrain heightfield identity differs")
        if manifest.get("terrainIdentity", {}).get("origin") != terrain_identity:
            raise AlignmentReportError(
                f"{label} package terrain origin differs from the actual terrain"
            )

    roads = road_payload.get("features")
    buildings = building_payload.get("buildings")
    if not isinstance(roads, list) or not isinstance(buildings, list):
        raise AlignmentReportError(
            "existing OSM road/building payloads have malformed feature arrays"
        )

    return LocalPackages(
        terrain_manifest=terrain,
        terrain_manifest_sha256=_hash_bytes(terrain_bytes),
        road_manifest=road_manifest,
        road_manifest_sha256=_hash_bytes(road_manifest_bytes),
        road_payload=road_payload,
        road_payload_sha256=_hash_bytes(road_payload_bytes),
        road_qa_sha256=_hash_bytes(road_qa_bytes),
        building_manifest=building_manifest,
        building_manifest_sha256=_hash_bytes(building_manifest_bytes),
        building_payload=building_payload,
        building_payload_sha256=_hash_bytes(building_payload_bytes),
        building_qa_sha256=_hash_bytes(building_qa_bytes),
    )


def _package_summary(packages: LocalPackages) -> dict[str, Any]:
    return {
        "terrain": {
            "manifestSha256": packages.terrain_manifest_sha256,
            "heightfieldSha256": packages.terrain_manifest["heightfield"]["sha256"],
        },
        "roads": {
            "manifestSha256": packages.road_manifest_sha256,
            "payloadSha256": packages.road_payload_sha256,
            "qaSha256": packages.road_qa_sha256,
            "mappedWays": len(packages.road_payload["features"]),
        },
        "buildings": {
            "manifestSha256": packages.building_manifest_sha256,
            "payloadSha256": packages.building_payload_sha256,
            "qaSha256": packages.building_qa_sha256,
            "mappedFootprints": len(packages.building_payload["buildings"]),
        },
    }


def _project_relative_file(project_root: Path, relative: object, field: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise AlignmentReportError(f"{field} must be a safe project-relative POSIX path")
    path = Path(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise AlignmentReportError(f"{field} is unsafe")
    candidate = (project_root / Path(*path.parts)).resolve()
    try:
        candidate.relative_to(project_root.resolve())
    except ValueError as exc:
        raise AlignmentReportError(f"{field} escapes the project") from exc
    return candidate


def _candidate_bytes(path: Path, pending_outputs: dict[Path, bytes] | None) -> bytes | None:
    if pending_outputs:
        resolved = path.resolve()
        for candidate, content in pending_outputs.items():
            if candidate.resolve() == resolved:
                return content
    try:
        return path.read_bytes()
    except OSError:
        return None


def _load_report_packages(report: dict[str, Any], project_root: Path) -> LocalPackages:
    record = report.get("localPackages")
    paths = record.get("packagePaths") if isinstance(record, dict) else None
    if not isinstance(paths, dict) or set(paths) != {"terrain", "roads", "buildings"}:
        raise AlignmentReportError(
            "localPackages.packagePaths must identify the three local packages"
        )
    resolved = {
        key: _project_relative_file(project_root, value, f"localPackages.packagePaths.{key}")
        for key, value in paths.items()
    }
    for key, path in resolved.items():
        if not path.is_dir():
            raise AlignmentReportError(f"localPackages.{key} package directory is missing")
    packages = load_local_packages(resolved["terrain"], resolved["roads"], resolved["buildings"])
    if record != {
        **_package_summary(packages),
        "packagePaths": paths,
    }:
        raise AlignmentReportError(
            "localPackages hashes/counts do not match the validated local package assets"
        )
    return packages


def read_palette_window(
    source: VerifiedComparisonSource, requested_bounds_m: tuple[float, float, float, float]
) -> RasterWindow:
    """Read the requested area without resampling or changing the source affine."""
    left, bottom, right, top = requested_bounds_m
    if (
        not all(math.isfinite(value) for value in requested_bounds_m)
        or left >= right
        or bottom >= top
    ):
        raise AlignmentReportError("requested raster window must be finite and ordered")
    if not source.cover(requested_bounds_m):
        raise AlignmentReportError(
            f"verified comparison tiles do not cover the requested EPSG:27700 window {requested_bounds_m}"  # noqa: E501
        )
    out_left, out_bottom = math.floor(left), math.floor(bottom)
    out_right, out_top = math.ceil(right), math.ceil(top)
    width, height = out_right - out_left, out_top - out_bottom
    if width <= 0 or height <= 0 or width * height > 25_000_000:
        raise AlignmentReportError("requested map window has unsafe or empty raster dimensions")
    canvas = np.zeros((height, width), dtype=np.uint8)
    covered = np.zeros((height, width), dtype=bool)
    palette: np.ndarray | None = None
    used_tiles: list[str] = []

    for tile in source.tiles:
        tleft, tbottom, tright, ttop = tile.bounds
        x0, x1 = max(out_left, tleft), min(out_right, tright)
        y0, y1 = max(out_bottom, tbottom), min(out_top, ttop)
        if x0 >= x1 or y0 >= y1:
            continue
        if palette is None:
            with rasterio.open(tile.path) as dataset:
                color_map = dataset.colormap(1)
            palette = np.zeros((256, 4), dtype=np.uint8)
            for index, rgba in color_map.items():
                palette[index] = rgba
        else:
            with rasterio.open(tile.path) as dataset:
                color_map = dataset.colormap(1)
            current = np.zeros((256, 4), dtype=np.uint8)
            for index, rgba in color_map.items():
                current[index] = rgba
            if not np.array_equal(current, palette):
                raise AlignmentReportError("selected OS tiles use different colour palettes")
        col_start, col_stop = int(x0 - tleft), int(x1 - tleft)
        row_start, row_stop = int(ttop - y1), int(ttop - y0)
        out_col_start, out_col_stop = int(x0 - out_left), int(x1 - out_left)
        out_row_start, out_row_stop = int(out_top - y1), int(out_top - y0)
        with rasterio.open(tile.path) as dataset:
            data = dataset.read(
                1,
                window=Window(
                    col_start,
                    row_start,
                    col_stop - col_start,
                    row_stop - row_start,
                ),
            )
        block = covered[out_row_start:out_row_stop, out_col_start:out_col_stop]
        if np.any(block):
            raise AlignmentReportError("selected OS tiles overlap within the requested map window")
        canvas[out_row_start:out_row_stop, out_col_start:out_col_stop] = data
        block[:] = True
        used_tiles.append(tile.path.name)
    if palette is None or not np.all(covered):
        raise AlignmentReportError("the registered raster window contains an uncovered pixel gap")
    return RasterWindow(
        indices=canvas,
        palette=palette,
        bounds_m=(float(out_left), float(out_bottom), float(out_right), float(out_top)),
        requested_bounds_m=requested_bounds_m,
        width=width,
        height=height,
        tile_names=tuple(sorted(set(used_tiles))),
    )


def _load_config(path: Path) -> tuple[dict[str, Any], bytes]:
    raw, content = _read_json(path, "alignment configuration")
    if raw.get("format_version") != 1 or raw.get("world_id") != "torquay-poc-001":
        raise AlignmentReportError("alignment config format_version/world_id is unsupported")
    aoi = raw.get("aoi")
    if not isinstance(aoi, dict) or aoi.get("bounds_m") != list(AOI_BOUNDS_M):
        raise AlignmentReportError("alignment config must use the exact reviewed 1 km AOI bounds")
    if (
        aoi.get("selection_status") != "selected_pending_coverage"
        or aoi.get("coverage_status") != "not_checked"
    ):
        raise AlignmentReportError(
            "alignment config must preserve selected_pending_coverage/not_checked"
        )
    if raw.get("source_id") != "os-openmap-local-apr-2026-sx":
        raise AlignmentReportError(
            "alignment config must use the accepted independent April 2026 OS source"
        )
    spots = raw.get("spots")
    if not isinstance(spots, list) or len(spots) != 3:
        raise AlignmentReportError("alignment config must contain exactly three selected contexts")
    if any(not isinstance(spot, dict) for spot in spots):
        raise AlignmentReportError("each selected context must be an object")
    accepted_ids = {spot.get("id") for spot in spots}
    if any(not isinstance(value, str) or not value for value in accepted_ids):
        raise AlignmentReportError("selected context IDs must be nonempty strings")
    if len(accepted_ids) != 3:
        raise AlignmentReportError("selected context IDs must be unique strings")
    if not {"ne-second-main", "nw-audley-pencorse", "sw-teignmouth-snowberry"}.issubset(
        accepted_ids
    ):
        raise AlignmentReportError("alignment config has lost an accepted comparison context")
    for index, spot in enumerate(spots):
        if spot.get("debug_context_id") != spot.get("id"):
            raise AlignmentReportError(
                f"spots[{index}].debug_context_id must identify the active selected context"
            )
    manual_review = raw.get("manual_review")
    if not isinstance(manual_review, dict):
        raise AlignmentReportError(
            "manual_review must be an object with reviewer, date, and method"
        )
    for field in ("reviewed_by", "reviewed_at_utc", "method"):
        if not isinstance(manual_review.get(field), str) or not manual_review[field].strip():
            raise AlignmentReportError(f"manual_review.{field} must be a nonempty string")
    return raw, content


def _load_report_config(report: dict[str, Any], project_root: Path) -> dict[str, Any]:
    descriptor = report.get("alignmentConfig")
    if (
        not isinstance(descriptor, dict)
        or descriptor.get("path") != "config/alignment.torquay.json"
    ):
        raise AlignmentReportError(
            "alignmentConfig must bind the accepted config/alignment.torquay.json"
        )
    path = _project_relative_file(project_root, descriptor.get("path"), "alignmentConfig.path")
    if not path.is_file() or descriptor.get("sha256") != _hash_path(path):
        raise AlignmentReportError("alignmentConfig file is missing or its SHA-256 differs")
    config, _ = _load_config(path)
    return config


def _json_values_equal(actual: Any, expected: Any) -> bool:
    """Compare JSON values without Python's bool-as-int equality shortcut."""
    try:
        return json.dumps(
            actual, sort_keys=True, ensure_ascii=False, allow_nan=False
        ) == json.dumps(expected, sort_keys=True, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        return False


def _source_report_metadata(source_record: dict[str, Any]) -> dict[str, Any]:
    """Map the accepted source manifest record to the report's verified source view."""
    archive = source_record.get("archive")
    tiles = source_record.get("selectedTiles")
    if not isinstance(archive, dict) or not isinstance(tiles, list) or len(tiles) != 2:
        raise AlignmentReportError("comparison source manifest archive/tiles are malformed")
    archive_path = archive.get("relativePath")
    if (
        not isinstance(archive_path, str)
        or not archive_path
        or "\\" in archive_path
        or ":" in archive_path
        or Path(archive_path).is_absolute()
        or any(part in {"", ".", ".."} for part in Path(archive_path).parts)
    ):
        raise AlignmentReportError("comparison source manifest archive path is unsafe")
    if (
        isinstance(archive.get("sizeBytes"), bool)
        or not isinstance(archive.get("sizeBytes"), int)
        or archive["sizeBytes"] <= 0
        or not isinstance(archive.get("sha256"), str)
        or len(archive["sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in archive["sha256"])
    ):
        raise AlignmentReportError("comparison source manifest archive identity is malformed")
    report_tiles: list[dict[str, Any]] = []
    for index, tile in enumerate(tiles):
        if not isinstance(tile, dict):
            raise AlignmentReportError(f"comparison source selectedTiles[{index}] is malformed")
        member = tile.get("archiveMember")
        relative_path = tile.get("relativePath")
        raster = tile.get("raster")
        if (
            not isinstance(member, str)
            or not member
            or not isinstance(relative_path, str)
            or not relative_path
            or "\\" in relative_path
            or ":" in relative_path
            or Path(relative_path).is_absolute()
            or any(part in {"", ".", ".."} for part in Path(relative_path).parts)
            or not isinstance(raster, dict)
        ):
            raise AlignmentReportError(
                f"comparison source selectedTiles[{index}] identity/raster is malformed"
            )
        report_tiles.append(
            {
                "member": member,
                "filename": Path(relative_path).name,
                "sizeBytes": tile.get("sizeBytes"),
                "sha256": tile.get("sha256"),
                "crc32": tile.get("crc32"),
                "crs": raster.get("crs"),
                "width": raster.get("width"),
                "height": raster.get("height"),
                "bandCount": raster.get("bandCount"),
                "dtype": raster.get("dtype"),
                "transform": raster.get("transform"),
                "boundsM": raster.get("boundsM"),
                "resolutionM": raster.get("resolutionM"),
                "colorInterpretation": raster.get("colorInterpretation"),
                "pixelInterpretation": raster.get("pixelInterpretation"),
                "nodata": raster.get("nodata"),
                "paletteEntries": raster.get("paletteEntries"),
                "tags": raster.get("tags"),
            }
        )
    licence = source_record.get("licence")
    acquisition = source_record.get("acquisition")
    if not isinstance(licence, dict) or not isinstance(acquisition, dict):
        raise AlignmentReportError("comparison source manifest licence/acquisition is malformed")
    return {
        "sourceId": source_record.get("sourceId"),
        "publisher": source_record.get("publisher"),
        "product": source_record.get("product"),
        "edition": source_record.get("edition"),
        "archiveFilename": Path(archive_path).name,
        "archiveBytes": archive["sizeBytes"],
        "archiveSha256": archive["sha256"],
        "selectedTiles": report_tiles,
        "licence": licence,
        "acquisition": acquisition,
    }


def _expected_comparison_window(
    config_spot: dict[str, Any], source_record: dict[str, Any], label: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive exact pixel-edge and tile registration from config and source metadata."""
    requested_values = config_spot.get("window_bounds_bng_m")
    if (
        not isinstance(requested_values, list)
        or len(requested_values) != 4
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in requested_values
        )
    ):
        raise AlignmentReportError(f"{label}.comparisonWindow config bounds are malformed")
    requested = [float(value) for value in requested_values]
    left, bottom, right, top = requested
    if left >= right or bottom >= top:
        raise AlignmentReportError(f"{label}.comparisonWindow config bounds are unordered")
    pixel_edges = [
        float(math.floor(left)),
        float(math.floor(bottom)),
        float(math.ceil(right)),
        float(math.ceil(top)),
    ]
    pixel_left, pixel_bottom, pixel_right, pixel_top = pixel_edges
    width, height = pixel_right - pixel_left, pixel_top - pixel_bottom
    if width <= 0 or height <= 0 or width * height > 25_000_000:
        raise AlignmentReportError(f"{label}.comparisonWindow has unsafe pixel dimensions")

    records = source_record.get("selectedTiles")
    if not isinstance(records, list):
        raise AlignmentReportError("comparison source selectedTiles are malformed")
    tile_bounds: list[tuple[str, tuple[float, float, float, float]]] = []
    for index, record in enumerate(records):
        raster = record.get("raster") if isinstance(record, dict) else None
        bounds = raster.get("boundsM") if isinstance(raster, dict) else None
        relative_path = record.get("relativePath") if isinstance(record, dict) else None
        if (
            not isinstance(bounds, list)
            or len(bounds) != 4
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in bounds
            )
            or not isinstance(relative_path, str)
        ):
            raise AlignmentReportError(
                f"comparison source selectedTiles[{index}] raster bounds are malformed"
            )
        tile_bounds.append((Path(relative_path).name, tuple(float(v) for v in bounds)))

    used_tiles = sorted(
        name
        for name, (tile_left, tile_bottom, tile_right, tile_top) in tile_bounds
        if max(pixel_left, tile_left) < min(pixel_right, tile_right)
        and max(pixel_bottom, tile_bottom) < min(pixel_top, tile_top)
    )
    if not used_tiles:
        raise AlignmentReportError(f"{label}.comparisonWindow is outside selected raster tiles")
    x_edges = sorted(
        {float(pixel_left), float(pixel_right)}
        | {
            max(float(pixel_left), bounds[0])
            for _, bounds in tile_bounds
            if pixel_left < bounds[2] and pixel_right > bounds[0]
        }
        | {
            min(float(pixel_right), bounds[2])
            for _, bounds in tile_bounds
            if pixel_left < bounds[2] and pixel_right > bounds[0]
        }
    )
    y_edges = sorted(
        {float(pixel_bottom), float(pixel_top)}
        | {
            max(float(pixel_bottom), bounds[1])
            for _, bounds in tile_bounds
            if pixel_bottom < bounds[3] and pixel_top > bounds[1]
        }
        | {
            min(float(pixel_top), bounds[3])
            for _, bounds in tile_bounds
            if pixel_bottom < bounds[3] and pixel_top > bounds[1]
        }
    )
    for y0, y1 in zip(y_edges, y_edges[1:], strict=False):
        for x0, x1 in zip(x_edges, x_edges[1:], strict=False):
            if x1 <= x0 or y1 <= y0:
                continue
            if not any(
                bounds[0] <= x0 and x1 <= bounds[2] and bounds[1] <= y0 and y1 <= bounds[3]
                for _, bounds in tile_bounds
            ):
                raise AlignmentReportError(
                    f"{label}.comparisonWindow has an uncovered raster pixel gap"
                )
    comparison = {
        "bngBoundsM": requested,
        "actualRasterPixelEdgeBoundsM": pixel_edges,
        "widthPixels": int(width),
        "heightPixels": int(height),
        "pixelSizeM": 1.0,
        "tileNames": used_tiles,
    }
    observation = config_spot.get("manual_observation")
    pixel_reference = {
        "registration": PIXEL_EDGE_REGISTRATION,
        "pixelSizeM": 1.0,
        "requestedWindowBNGMetres": requested,
        "actualPixelEdgeWindowBNGMetres": pixel_edges,
        "manualReferencePointBNGMetres": (
            observation.get("reference_point_bng_m") if isinstance(observation, dict) else None
        ),
    }
    return comparison, pixel_reference


def _validate_report_coordinate_reference(report: dict[str, Any], packages: LocalPackages) -> None:
    reference = report.get("coordinateReference")
    if not isinstance(reference, dict):
        raise AlignmentReportError("coordinateReference is missing or malformed")
    if (
        reference.get("crs") != "EPSG:27700"
        or reference.get("aoi") != report.get("aoi")
        or reference.get("axisMapping") != AXIS_MAPPING
        or reference.get("rasterRegistration") != RASTER_REGISTRATION
    ):
        raise AlignmentReportError(
            "coordinateReference does not match the registered AOI/axis contract"
        )
    road_operation = packages.road_manifest.get("coordinateOperation", {}).get("wgs84ToBng")
    if not isinstance(road_operation, dict):
        raise AlignmentReportError("local road package has no WGS84-to-BNG coordinate operation")
    try:
        _transformer, expected_operation = pinned_transformer(4326, 27700)
    except ValueError as exc:
        raise AlignmentReportError(f"cannot verify the pinned coordinate operation: {exc}") from exc
    if road_operation != expected_operation.as_dict():
        raise AlignmentReportError(
            "local road package does not use the pinned EPSG:1314 + EPSG:19916 operation"
        )
    if reference.get("localCoordinateOperation") != road_operation:
        raise AlignmentReportError(
            "coordinateReference operation differs from the validated road package operation"
        )
    uncertainty = reference.get("uncertaintyComponents")
    if (
        not isinstance(uncertainty, list)
        or not uncertainty
        or any(not isinstance(item, str) or not item.strip() for item in uncertainty)
    ):
        raise AlignmentReportError("coordinateReference uncertaintyComponents are required")


def _validate_report_controls(report_spot: dict[str, Any], config_spot: dict[str, Any]) -> None:
    label = f"spots[{report_spot.get('id', '?')}]"
    control = config_spot["control"]
    actual = report_spot.get("control")
    if not isinstance(actual, dict):
        raise AlignmentReportError(f"{label}.control is missing or malformed")
    expected = {
        "featureRole": control["feature_role"],
        "osmNodeId": control["osm_node_id"],
        "osmWayIds": control["osm_way_ids"],
        "roadNames": control["road_names"],
        "localXZMetres": control["local_xz_m"],
        "bngENMetres": control["bng_e_n_m"],
        "wgs84LonLat": control["wgs84_lon_lat"],
    }
    if any(actual.get(key) != value for key, value in expected.items()):
        raise AlignmentReportError(
            f"{label}.control does not match the bound accepted configuration"
        )
    if report_spot.get("selectionStatus") != config_spot.get("selection_status"):
        raise AlignmentReportError(f"{label}.selectionStatus differs from the bound configuration")
    if report_spot.get("selectionRationale") != config_spot.get("selection_rationale"):
        raise AlignmentReportError(
            f"{label}.selectionRationale differs from the bound configuration"
        )
    if report_spot.get("alignmentStatus") != config_spot.get("alignment_status"):
        raise AlignmentReportError(f"{label}.alignmentStatus differs from the bound configuration")
    if report_spot.get("debugContextId") != config_spot.get("debug_context_id"):
        raise AlignmentReportError(f"{label}.debugContextId differs from the bound configuration")
    comparison = report_spot.get("comparisonWindow")
    if not isinstance(comparison, dict) or comparison.get("bngBoundsM") != config_spot.get(
        "window_bounds_bng_m"
    ):
        raise AlignmentReportError(
            f"{label}.comparisonWindow does not match the registered context"
        )
    expected_observation = config_spot.get("manual_observation")
    actual_observation = report_spot.get("manualObservation")
    expected_observation = (
        {
            "summary": expected_observation.get("summary"),
            "reviewedBy": expected_observation.get("reviewed_by"),
            "method": expected_observation.get("method"),
            "confidence": expected_observation.get("confidence"),
            "referencePointBngM": expected_observation.get("reference_point_bng_m"),
            "screeningAssessment": expected_observation.get("screening_assessment"),
        }
        if isinstance(expected_observation, dict)
        else None
    )
    if actual_observation != expected_observation:
        raise AlignmentReportError(
            f"{label}.manualObservation differs from the bound configuration"
        )


def _validated_control(config: dict[str, Any], packages: LocalPackages) -> list[dict[str, Any]]:
    roads = packages.road_payload.get("features")
    buildings = packages.building_payload.get("buildings")
    assert isinstance(roads, list) and isinstance(buildings, list)
    roads_by_id = {
        str(feature.get("id")): feature for feature in roads if isinstance(feature, dict)
    }
    buildings_by_id = {
        str(feature.get("id")): feature for feature in buildings if isinstance(feature, dict)
    }
    origin = packages.terrain_manifest["origin"]
    origin_e, origin_n = float(origin["eastingM"]), float(origin["northingM"])
    validated: list[dict[str, Any]] = []

    for index, spot in enumerate(config["spots"]):
        field = f"spots[{index}]"
        if not isinstance(spot, dict) or not isinstance(spot.get("control"), dict):
            raise AlignmentReportError(f"{field} must contain a control object")
        control = spot["control"]
        way_ids = control.get("osm_way_ids")
        node_id = control.get("osm_node_id")
        local = control.get("local_xz_m")
        bng = control.get("bng_e_n_m")
        lonlat = control.get("wgs84_lon_lat")
        if (
            not isinstance(way_ids, list)
            or len(way_ids) != 2
            or any(isinstance(item, bool) or not isinstance(item, int) for item in way_ids)
            or isinstance(node_id, bool)
            or not isinstance(node_id, int)
            or not isinstance(local, list)
            or len(local) != 2
            or not isinstance(bng, list)
            or len(bng) != 2
            or not isinstance(lonlat, list)
            or len(lonlat) != 2
        ):
            raise AlignmentReportError(
                f"{field}.control has malformed source identities/coordinates"
            )
        if not all(
            isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
            for value in (*local, *bng, *lonlat)
        ):
            raise AlignmentReportError(f"{field}.control coordinates must be finite numbers")
        longitude, latitude = (float(value) for value in lonlat)
        if not (-180.0 <= longitude <= 180.0 and -90.0 <= latitude <= 90.0):
            raise AlignmentReportError(f"{field}.control WGS84 coordinates are out of range")
        expected_e, expected_n = origin_e + float(local[0]), origin_n - float(local[1])
        if math.dist((expected_e, expected_n), tuple(float(value) for value in bng)) > 0.002:
            raise AlignmentReportError(
                f"{field}.control BNG does not match the local XZ convention"
            )
        if not (
            AOI_BOUNDS_M[0] <= expected_e <= AOI_BOUNDS_M[2]
            and AOI_BOUNDS_M[1] <= expected_n <= AOI_BOUNDS_M[3]
        ):
            raise AlignmentReportError(f"{field}.control lies outside the reviewed AOI")
        try:
            expected_lon, expected_lat, _operation = transform_bng_to_wgs84(
                [expected_e], [expected_n]
            )
        except ValueError as exc:
            raise AlignmentReportError(f"{field}.control WGS84 transform failed: {exc}") from exc
        if abs(expected_lon[0] - longitude) > 1e-7 or abs(expected_lat[0] - latitude) > 1e-7:
            raise AlignmentReportError(
                f"{field}.control WGS84 coordinates do not match the pinned BNG operation"
            )
        source_features: list[dict[str, Any]] = []
        for way_id in way_ids:
            feature = roads_by_id.get(f"way/{way_id}")
            if feature is None:
                raise AlignmentReportError(f"{field} references missing exported road way/{way_id}")
            source = feature.get("source")
            node_ids = source.get("nodeIds") if isinstance(source, dict) else None
            if not isinstance(node_ids, list) or node_id not in node_ids:
                raise AlignmentReportError(
                    f"{field} road way/{way_id} does not retain shared OSM node/{node_id}"
                )
            distance = min(
                (
                    Point(expected_e, expected_n).distance(
                        LineString([(origin_e + p[0], origin_n - p[1]) for p in part])
                    )
                    for part in feature.get("centerlinePartsXZ", [])
                    if isinstance(part, list) and len(part) >= 2
                ),
                default=math.inf,
            )
            if distance > 0.002:
                raise AlignmentReportError(
                    f"{field} control does not lie on exported way/{way_id} centerline"
                )
            source_features.append(feature)
        if not isinstance(spot.get("original_context"), dict):
            raise AlignmentReportError(f"{field}.original_context is required")
        original = spot["original_context"]
        building_id = original.get("building_way_id")
        if isinstance(building_id, int) and f"osm:way:{building_id}" not in buildings_by_id:
            raise AlignmentReportError(
                f"{field} original context building way/{building_id} is missing"
            )
        window = spot.get("window_bounds_bng_m")
        if (
            not isinstance(window, list)
            or len(window) != 4
            or not all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                for value in window
            )
            or window[0] >= window[2]
            or window[1] >= window[3]
            or window[0] < AOI_BOUNDS_M[0]
            or window[1] < AOI_BOUNDS_M[1]
            or window[2] > AOI_BOUNDS_M[2]
            or window[3] > AOI_BOUNDS_M[3]
        ):
            raise AlignmentReportError(
                f"{field}.window_bounds_bng_m must be an ordered in-AOI extent"
            )
        status = spot.get("alignment_status")
        if not isinstance(status, str) or status not in {
            "pass",
            "fail",
            "inconclusive",
            "unavailable",
            "pending_visual_review",
        }:
            raise AlignmentReportError(f"{field}.alignment_status is unsupported")
        observation = spot.get("manual_observation")
        if status != "pending_visual_review":
            if not isinstance(observation, dict):
                raise AlignmentReportError(f"{field} needs a manual observation for {status}")
            if (
                not isinstance(observation.get("summary"), str)
                or not observation["summary"].strip()
            ):
                raise AlignmentReportError(f"{field}.manual_observation.summary is required")
            if (
                not isinstance(observation.get("reviewed_by"), str)
                or not observation["reviewed_by"].strip()
            ):
                raise AlignmentReportError(f"{field}.manual_observation.reviewed_by is required")
        elif observation is not None and not isinstance(observation, dict):
            raise AlignmentReportError(f"{field}.manual_observation must be null or an object")
        validated.append(
            {
                **spot,
                "_controlBng": [expected_e, expected_n],
                "_roadFeatures": source_features,
                "_building": buildings_by_id.get(f"osm:way:{building_id}")
                if isinstance(building_id, int)
                else None,
            }
        )
    return validated


def _world_geometries(
    roads: list[dict[str, Any]], buildings: list[dict[str, Any]], origin_e: float, origin_n: float
) -> tuple[
    list[tuple[dict[str, Any], list[list[tuple[float, float]]]]],
    list[tuple[dict[str, Any], list[list[tuple[float, float]]]]],
]:
    road_lines: list[tuple[dict[str, Any], list[list[tuple[float, float]]]]] = []
    for road in roads:
        for part in road.get("centerlinePartsXZ", []):
            if isinstance(part, list) and len(part) >= 2:
                road_lines.append(
                    (
                        road,
                        [
                            (origin_e + float(point[0]), origin_n - float(point[1]))
                            for point in part
                        ],
                    )
                )
    building_rings: list[tuple[dict[str, Any], list[list[tuple[float, float]]]]] = []
    for building in buildings:
        geometry = building.get("geometry")
        if not isinstance(geometry, dict) or not isinstance(geometry.get("polygons"), list):
            continue
        for polygon in geometry["polygons"]:
            if not isinstance(polygon, dict):
                continue
            rings = [polygon.get("exteriorXZ"), *polygon.get("interiorRingsXZ", [])]
            transformed: list[list[tuple[float, float]]] = []
            for ring in rings:
                if isinstance(ring, list) and len(ring) >= 4:
                    transformed.append(
                        [(origin_e + float(point[0]), origin_n - float(point[1])) for point in ring]
                    )
            if transformed:
                building_rings.append((building, transformed))
    return road_lines, building_rings


def _draw_scale_and_north(ax: Any, bounds: tuple[float, float, float, float]) -> None:
    left, bottom, right, top = bounds
    span = min(right - left, top - bottom)
    length = 50.0 if span >= 150 else 20.0
    x0 = left + (right - left) * 0.06
    y0 = bottom + (top - bottom) * 0.065
    ax.plot(
        [x0, x0 + length], [y0, y0], color="black", linewidth=3.3, solid_capstyle="butt", zorder=20
    )
    ax.plot(
        [x0, x0 + length], [y0, y0], color="white", linewidth=1.6, solid_capstyle="butt", zorder=21
    )
    ax.text(
        x0 + length / 2,
        y0 + span * 0.018,
        f"{length:g} m",
        ha="center",
        va="bottom",
        fontsize=7,
        color="black",
        zorder=21,
    )
    nx, ny = right - (right - left) * 0.075, top - (top - bottom) * 0.11
    ax.annotate(
        "N",
        xy=(nx, ny + span * 0.08),
        xytext=(nx, ny),
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        arrowprops={"arrowstyle": "-|>", "lw": 1.2, "color": "black"},
        zorder=22,
    )


def _panel_bytes(
    spot: dict[str, Any],
    window: RasterWindow,
    packages: LocalPackages,
    panel_kind: str,
) -> bytes:
    roads = packages.road_payload.get("features")
    buildings = packages.building_payload.get("buildings")
    assert isinstance(roads, list) and isinstance(buildings, list)
    origin = packages.terrain_manifest["origin"]
    origin_e, origin_n = float(origin["eastingM"]), float(origin["northingM"])
    bounds = window.bounds_m
    image_left, image_bottom, image_right, image_top = bounds
    footprint = Polygon(
        [
            (AOI_BOUNDS_M[0], AOI_BOUNDS_M[1]),
            (AOI_BOUNDS_M[2], AOI_BOUNDS_M[1]),
            (AOI_BOUNDS_M[2], AOI_BOUNDS_M[3]),
            (AOI_BOUNDS_M[0], AOI_BOUNDS_M[3]),
        ]
    )
    control_e, control_n = spot["_controlBng"]
    fig, ax = plt.subplots(figsize=(8.0, 7.0), dpi=180)
    if panel_kind in {"reference", "overlay"}:
        cmap = ListedColormap(window.palette.astype(np.float32) / 255.0)
        ax.imshow(
            window.indices,
            cmap=cmap,
            vmin=0,
            vmax=255,
            origin="upper",
            extent=(image_left, image_right, image_bottom, image_top),
            interpolation="nearest",
            zorder=0,
        )
    if panel_kind in {"overlay", "package"}:
        if panel_kind == "package":
            ax.set_facecolor("#f7f5ed")
        road_lines, building_rings = _world_geometries(roads, buildings, origin_e, origin_n)
        for road, coords in road_lines:
            line = LineString(coords)
            if not line.intersects(footprint) or not line.intersects(
                Polygon(
                    [
                        (image_left, image_bottom),
                        (image_right, image_bottom),
                        (image_right, image_top),
                        (image_left, image_top),
                    ]
                )
            ):
                continue
            clipped = line.intersection(
                Polygon(
                    [
                        (image_left, image_bottom),
                        (image_right, image_bottom),
                        (image_right, image_top),
                        (image_left, image_top),
                    ]
                )
            )
            geometries = (
                [clipped]
                if clipped.geom_type == "LineString"
                else list(getattr(clipped, "geoms", []))
            )
            color = "#00d7c5" if road.get("displayGroup") == "vehicular" else "#f06bff"
            for geometry in geometries:
                if geometry.geom_type == "LineString" and not geometry.is_empty:
                    x, y = geometry.xy
                    ax.plot(
                        x,
                        y,
                        color=color,
                        linewidth=0.85 if panel_kind == "overlay" else 1.2,
                        alpha=0.95,
                        zorder=5,
                    )
        for _building, rings in building_rings:
            for coords in rings:
                polygon = Polygon(coords)
                if not polygon.intersects(footprint) or not polygon.intersects(
                    Polygon(
                        [
                            (image_left, image_bottom),
                            (image_right, image_bottom),
                            (image_right, image_top),
                            (image_left, image_top),
                        ]
                    )
                ):
                    continue
                clipped = polygon.intersection(
                    Polygon(
                        [
                            (image_left, image_bottom),
                            (image_right, image_bottom),
                            (image_right, image_top),
                            (image_left, image_top),
                        ]
                    )
                )
                polygons = (
                    [clipped]
                    if clipped.geom_type == "Polygon"
                    else list(getattr(clipped, "geoms", []))
                )
                for part in polygons:
                    if part.geom_type == "Polygon":
                        x, y = part.exterior.xy
                        ax.plot(
                            x,
                            y,
                            color="#e61978",
                            linewidth=0.55 if panel_kind == "overlay" else 0.8,
                            alpha=0.95,
                            zorder=4,
                        )
                        for interior in part.interiors:
                            x, y = interior.xy
                            ax.plot(
                                x,
                                y,
                                color="#e61978",
                                linewidth=0.45,
                                linestyle="--",
                                alpha=0.75,
                                zorder=4,
                            )

    aoi_line = Polygon(
        [
            (AOI_BOUNDS_M[0], AOI_BOUNDS_M[1]),
            (AOI_BOUNDS_M[2], AOI_BOUNDS_M[1]),
            (AOI_BOUNDS_M[2], AOI_BOUNDS_M[3]),
            (AOI_BOUNDS_M[0], AOI_BOUNDS_M[3]),
        ]
    )
    x, y = aoi_line.exterior.xy
    ax.plot(x, y, color="#f5c400", linewidth=2.2, zorder=15)
    ax.scatter([control_e], [control_n], marker="x", s=50, linewidth=2, color="#111111", zorder=18)
    ax.scatter(
        [control_e],
        [control_n],
        marker="o",
        s=20,
        facecolors="none",
        edgecolors="#fff200",
        linewidth=1.2,
        zorder=19,
    )
    ax.set_xlim(image_left, image_right)
    ax.set_ylim(image_bottom, image_top)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Easting (m, EPSG:27700)", fontsize=8)
    ax.set_ylabel("Northing (m, EPSG:27700)", fontsize=8)
    ax.tick_params(labelsize=7)
    panel_title = {
        "reference": "OS OpenMap–Local reference",
        "overlay": "Registered OS raster + OSM package",
        "package": "OSM package geometry only",
    }[panel_kind]
    ax.set_title(f"{spot['label']} · {panel_title}", fontsize=10, pad=8)
    _draw_scale_and_north(ax, bounds)
    locator = ax.inset_axes([0.735, 0.735, 0.225, 0.225], facecolor="white")
    locator.add_patch(
        Rectangle(
            (AOI_BOUNDS_M[0], AOI_BOUNDS_M[1]),
            AOI_BOUNDS_M[2] - AOI_BOUNDS_M[0],
            AOI_BOUNDS_M[3] - AOI_BOUNDS_M[1],
            fill=False,
            edgecolor="#d4a900",
            linewidth=1.2,
        )
    )
    locator.add_patch(
        Rectangle(
            (image_left, image_bottom),
            image_right - image_left,
            image_top - image_bottom,
            fill=False,
            edgecolor="#db2569",
            linewidth=1.5,
        )
    )
    locator.scatter([control_e], [control_n], marker="o", s=7, color="#111111", zorder=3)
    locator.set_xlim(AOI_BOUNDS_M[0] - 25, AOI_BOUNDS_M[2] + 25)
    locator.set_ylim(AOI_BOUNDS_M[1] - 25, AOI_BOUNDS_M[3] + 25)
    locator.set_aspect("equal", adjustable="box")
    locator.set_xticks([])
    locator.set_yticks([])
    locator.set_title("AOI / comparison window", fontsize=5.5, pad=2)
    locator.grid(False)
    credit = (
        OS_ATTRIBUTION if panel_kind == "reference" else f"{OS_ATTRIBUTION} · {OSM_ATTRIBUTION}"
    )
    fig.text(0.5, 0.017, credit, ha="center", fontsize=5.8, wrap=True)
    fig.text(
        0.5,
        0.004,
        "AOI status: selected_pending_coverage / not_checked · placement comparison only",
        ha="center",
        fontsize=5.6,
    )
    fig.tight_layout(rect=(0.055, 0.055, 0.99, 0.97))
    buffer = io.BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=180,
        metadata={"Software": "torquay_pipeline.alignment_report", "Creation Time": None},
    )
    plt.close(fig)
    return buffer.getvalue()


def _atomic_write_outputs(outputs: dict[Path, bytes]) -> None:
    """Replace a group of output files together, restoring prior bytes on failure."""
    staged: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}
    installed: list[Path] = []
    try:
        for target, content in outputs.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(
                prefix=f".{target.name}.", suffix=".stage", dir=target.parent
            )
            stage = Path(name)
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            staged[target] = stage
        for target in outputs:
            if target.exists():
                fd, name = tempfile.mkstemp(
                    prefix=f".{target.name}.", suffix=".backup", dir=target.parent
                )
                os.close(fd)
                backup = Path(name)
                backup.unlink()
                os.replace(target, backup)
                backups[target] = backup
        for target, stage in staged.items():
            os.replace(stage, target)
            installed.append(target)
    except OSError as exc:
        for target in installed:
            target.unlink(missing_ok=True)
        for target, backup in backups.items():
            if backup.exists():
                os.replace(backup, target)
        raise AlignmentReportError(f"cannot atomically write alignment evidence: {exc}") from exc
    finally:
        for stage in staged.values():
            stage.unlink(missing_ok=True)
    for backup in backups.values():
        backup.unlink(missing_ok=True)


def _validate_prior_candidate(value: Any, active_ids: set[str], project_root: Path) -> None:
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        raise AlignmentReportError(
            "alignment report must preserve the superseded SW candidate as one prior record"
        )
    descriptor = value[0]
    path_text = descriptor.get("path")
    if not isinstance(path_text, str) or not path_text or "\\" in path_text or ":" in path_text:
        raise AlignmentReportError("prior candidate report path must be project-relative")
    path = Path(path_text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise AlignmentReportError("prior candidate report path is unsafe")
    candidate = (project_root / Path(*path.parts)).resolve()
    try:
        candidate.relative_to(project_root.resolve())
    except ValueError as exc:
        raise AlignmentReportError("prior candidate report path escapes the project") from exc
    if not candidate.is_file() or descriptor.get("byteLength") != candidate.stat().st_size:
        raise AlignmentReportError("prior candidate record is missing or has incorrect byte length")
    if descriptor.get("sha256") != _hash_path(candidate):
        raise AlignmentReportError("prior candidate record SHA-256 mismatch")
    try:
        payload = json.loads(candidate.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise AlignmentReportError(
            f"prior candidate record is unreadable or invalid JSON: {exc}"
        ) from exc
    if (
        not isinstance(payload, dict)
        or payload.get("formatVersion") != 1
        or payload.get("candidateRole")
        != "inconclusive prior candidate; not counted among active comparison spots"
        or descriptor.get("record") != payload.get("record")
    ):
        raise AlignmentReportError(
            "prior candidate record contents do not match the preserved artifact"
        )
    record = payload["record"]
    if (
        not isinstance(record, dict)
        or record.get("id") != "sw-st-vincent-chapel"
        or record.get("id") in active_ids
        or record.get("alignmentStatus") != "inconclusive"
    ):
        raise AlignmentReportError(
            "prior SW candidate must remain separately inconclusive and uncounted"
        )
    observation = record.get("manualObservation")
    if (
        not isinstance(observation, dict)
        or not isinstance(observation.get("summary"), str)
        or not observation["summary"].strip()
    ):
        raise AlignmentReportError("prior SW candidate is missing its inconclusive observation")
    evidence_items = record.get("evidence")
    if not isinstance(evidence_items, list) or len(evidence_items) != 4:
        raise AlignmentReportError("prior SW candidate must retain all four evidence views")
    kinds: set[str] = set()
    for item in evidence_items:
        if not isinstance(item, dict):
            raise AlignmentReportError("prior candidate evidence entries must be objects")
        kind = item.get("kind")
        evidence_path_text = item.get("path")
        if kind not in {"reference", "overlay", "package", "scene"} or kind in kinds:
            raise AlignmentReportError("prior candidate evidence kinds are invalid or duplicated")
        kinds.add(kind)
        if (
            not isinstance(evidence_path_text, str)
            or not evidence_path_text
            or "\\" in evidence_path_text
            or ":" in evidence_path_text
        ):
            raise AlignmentReportError("prior candidate evidence path is unsafe")
        evidence_path = Path(evidence_path_text)
        if evidence_path.is_absolute() or any(
            part in {"", ".", ".."} for part in evidence_path.parts
        ):
            raise AlignmentReportError("prior candidate evidence path is unsafe")
        evidence_file = (project_root / Path(*evidence_path.parts)).resolve()
        try:
            evidence_file.relative_to(project_root.resolve())
        except ValueError as exc:
            raise AlignmentReportError("prior candidate evidence path escapes the project") from exc
        if not evidence_file.is_file():
            raise AlignmentReportError("prior candidate evidence file is missing")
        if item.get("byteLength") != evidence_file.stat().st_size or item.get(
            "sha256"
        ) != _hash_path(evidence_file):
            raise AlignmentReportError("prior candidate evidence integrity mismatch")
    if kinds != {"reference", "overlay", "package", "scene"}:
        raise AlignmentReportError("prior candidate record is missing a required evidence view")
    browser = record.get("browserSession")
    if not isinstance(browser, dict) or browser.get("expectedContextId") != record["id"]:
        raise AlignmentReportError(
            "prior candidate browser evidence is not bound to its original context"
        )


def validate_alignment_report(
    report: Any,
    project_root: Path,
    *,
    pending_outputs: dict[Path, bytes] | None = None,
) -> dict[str, Any]:
    """Validate result states and integrity-bound local evidence without inferring visual PASS."""
    if (
        not isinstance(report, dict)
        or isinstance(report.get("formatVersion"), bool)
        or report.get("formatVersion") != 1
    ):
        raise AlignmentReportError("alignment report must be an object with formatVersion=1")
    if report.get("sourceIndependence") != "independent_publisher_os_openmap_local":
        raise AlignmentReportError("alignment report must identify the independent OS map source")
    source = report.get("source")
    if not isinstance(source, dict):
        raise AlignmentReportError("alignment report source metadata is missing or malformed")
    for field in ("sourceId", "publisher", "product", "edition"):
        if not isinstance(source.get(field), str) or not source[field].strip():
            raise AlignmentReportError(f"alignment report source.{field} is required")
    licence = source.get("licence")
    if not isinstance(licence, dict):
        raise AlignmentReportError("alignment report source.licence is missing or malformed")
    if (
        licence.get("name") != "Open Government Licence v3.0"
        or licence.get("url") != OS_LICENCE_URL
        or licence.get("requiredAttribution") != OS_ATTRIBUTION
    ):
        raise AlignmentReportError("alignment report OS licence/required attribution is incorrect")
    source_manifest = report.get("sourceManifest")
    if not isinstance(source_manifest, dict):
        raise AlignmentReportError("alignment report sourceManifest descriptor is missing")
    source_manifest_path_text = source_manifest.get("path")
    if (
        not isinstance(source_manifest_path_text, str)
        or not source_manifest_path_text
        or "\\" in source_manifest_path_text
        or ":" in source_manifest_path_text
    ):
        raise AlignmentReportError("sourceManifest.path must be a safe project-relative path")
    if source_manifest_path_text != "data/comparison-source-manifest.json":
        raise AlignmentReportError(
            "sourceManifest.path must bind data/comparison-source-manifest.json"
        )
    source_manifest_path = Path(source_manifest_path_text)
    if source_manifest_path.is_absolute() or any(
        part in {"", ".", ".."} for part in source_manifest_path.parts
    ):
        raise AlignmentReportError("sourceManifest.path is unsafe")
    source_manifest_file = _project_relative_file(
        project_root, source_manifest_path_text, "sourceManifest.path"
    )
    try:
        source_manifest_file.relative_to(project_root.resolve())
    except ValueError as exc:
        raise AlignmentReportError("sourceManifest.path escapes the project") from exc
    if not source_manifest_file.is_file() or source_manifest.get("sha256") != _hash_path(
        source_manifest_file
    ):
        raise AlignmentReportError("sourceManifest file is missing or its SHA-256 differs")
    try:
        source_manifest_value = json.loads(source_manifest_file.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise AlignmentReportError(
            f"sourceManifest file is unreadable or invalid JSON: {exc}"
        ) from exc
    source_records = (
        source_manifest_value.get("sources") if isinstance(source_manifest_value, dict) else None
    )
    if (
        not isinstance(source_manifest_value, dict)
        or source_manifest_value.get("formatVersion") != 1
        or source_manifest_value.get("scope") != "comparison-only"
        or not isinstance(source_records, list)
        or len(source_records) != 1
        or not isinstance(source_records[0], dict)
    ):
        raise AlignmentReportError("bound comparison source manifest has an invalid structure")
    source_record = source_records[0]
    expected_source = _source_report_metadata(source_record)
    if not _json_values_equal(source, expected_source):
        raise AlignmentReportError(
            "source archive/tile/raster metadata does not match the bound comparison manifest"
        )
    browser_descriptor = report.get("browserSessionEvidence")
    if not isinstance(browser_descriptor, dict):
        raise AlignmentReportError("alignment report browserSessionEvidence is missing")
    browser_path_text = browser_descriptor.get("path")
    if (
        not isinstance(browser_path_text, str)
        or not browser_path_text
        or "\\" in browser_path_text
        or ":" in browser_path_text
    ):
        raise AlignmentReportError(
            "browserSessionEvidence.path must be a safe project-relative path"
        )
    browser_file = _project_relative_file(
        project_root, browser_path_text, "browserSessionEvidence.path"
    )
    if (
        not browser_file.is_file()
        or browser_descriptor.get("byteLength") != browser_file.stat().st_size
    ):
        raise AlignmentReportError(
            "browser session evidence is missing or has an incorrect byte length"
        )
    if browser_descriptor.get("sha256") != _hash_path(browser_file):
        raise AlignmentReportError("browser session evidence SHA-256 mismatch")
    try:
        browser_evidence = json.loads(browser_file.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise AlignmentReportError(f"browser session evidence is invalid JSON: {exc}") from exc
    if not isinstance(browser_evidence, dict):
        raise AlignmentReportError("browser session evidence must be a JSON object")
    for error_field in ("consoleErrors", "pageErrors", "failedRequests"):
        if browser_evidence.get(error_field) != []:
            raise AlignmentReportError(f"browser session evidence contains {error_field}")
    aoi = report.get("aoi")
    if not isinstance(aoi, dict):
        raise AlignmentReportError("alignment report AOI metadata must be an object")
    if (
        aoi.get("boundsM") != list(AOI_BOUNDS_M)
        or aoi.get("selectionStatus") != "selected_pending_coverage"
        or aoi.get("coverageStatus") != "not_checked"
    ):
        raise AlignmentReportError("alignment report must preserve the pending AOI status")
    config = _load_report_config(report, project_root)
    if report.get("reportId") != config.get("report_id"):
        raise AlignmentReportError("reportId differs from the bound accepted configuration")
    if report.get("source", {}).get("sourceId") != config.get("source_id"):
        raise AlignmentReportError("report sourceId differs from the bound accepted configuration")
    packages = _load_report_packages(report, project_root)
    _validate_report_coordinate_reference(report, packages)
    config_spots = _validated_control(config, packages)
    config_by_id = {spot["id"]: spot for spot in config_spots}
    browser_records_value = browser_evidence.get("evidence")
    if not isinstance(browser_records_value, list):
        raise AlignmentReportError("browser session evidence has no evidence array")
    browser_records: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(browser_records_value):
        if not isinstance(record, dict):
            raise AlignmentReportError(f"browser evidence[{index}] must be an object")
        context_id = record.get("expectedContextId")
        if not isinstance(context_id, str) or not context_id or context_id in browser_records:
            raise AlignmentReportError(
                f"browser evidence[{index}].expectedContextId must be unique nonempty text"
            )
        browser_records[context_id] = record
    spots = report.get("spots")
    if not isinstance(spots, list) or len(spots) != 3:
        raise AlignmentReportError("alignment report must contain exactly three registered spots")
    if set(browser_records) != set(config_by_id):
        raise AlignmentReportError(
            "browser evidence contexts differ from the accepted configuration"
        )
    statuses: set[str] = set()
    evidence_paths: set[str] = set()
    spot_ids: set[str] = set()
    for index, spot in enumerate(spots):
        label = f"spots[{index}]"
        if not isinstance(spot, dict) or not isinstance(spot.get("id"), str):
            raise AlignmentReportError(f"{label} must be an object with an id")
        if not spot["id"] or spot["id"] in spot_ids:
            raise AlignmentReportError(f"{label}.id must be nonempty and unique")
        spot_ids.add(spot["id"])
        config_spot = config_by_id.get(spot["id"])
        if config_spot is None:
            raise AlignmentReportError(f"{label}.id is not in the bound accepted configuration")
        _validate_report_controls(spot, config_spot)
        expected_window, expected_pixel_reference = _expected_comparison_window(
            config_spot, source_record, label
        )
        if not _json_values_equal(spot.get("comparisonWindow"), expected_window):
            raise AlignmentReportError(
                f"{label}.comparisonWindow pixel edges/tiles do not match the accepted "
                "config and source raster metadata"
            )
        control_record = spot.get("control")
        if not isinstance(control_record, dict) or not _json_values_equal(
            control_record.get("pixelReference"), expected_pixel_reference
        ):
            raise AlignmentReportError(
                f"{label}.control.pixelReference does not match the registered raster window"
            )
        status = spot.get("alignmentStatus")
        if not isinstance(status, str) or status not in {
            "pass",
            "fail",
            "inconclusive",
            "unavailable",
            "pending_visual_review",
        }:
            raise AlignmentReportError(f"{label}.alignmentStatus is unsupported")
        statuses.add(status)
        evidence = spot.get("evidence")
        if not isinstance(evidence, list) or len(evidence) != 4:
            raise AlignmentReportError(
                f"{label}.evidence must include reference, overlay, OSM-only package and actual 3D scene views"  # noqa: E501
            )
        kinds: set[str] = set()
        for item in evidence:
            if not isinstance(item, dict):
                raise AlignmentReportError(f"{label}.evidence items must be objects")
            kind = item.get("kind")
            if kind not in {"reference", "overlay", "package", "scene"} or kind in kinds:
                raise AlignmentReportError(
                    f"{label}.evidence kinds must be unique reference/overlay/package/scene"
                )
            kinds.add(kind)
            path_text = item.get("path")
            if (
                not isinstance(path_text, str)
                or not path_text
                or "\\" in path_text
                or ":" in path_text
            ):
                raise AlignmentReportError(
                    f"{label}.evidence path must be a safe project-relative POSIX path"
                )
            path = Path(path_text)
            if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
                raise AlignmentReportError(f"{label}.evidence path is unsafe")
            expected_evidence_path = (
                Path("docs/milestones/screenshots") / f"TVW-012-{spot['id']}-{kind}.png"
            ).as_posix()
            if path_text != expected_evidence_path:
                raise AlignmentReportError(
                    f"{label}.evidence path does not identify the registered {kind} panel"
                )
            candidate = (project_root / Path(*path.parts)).resolve()
            try:
                candidate.relative_to(project_root.resolve())
            except ValueError as exc:
                raise AlignmentReportError(f"{label}.evidence path escapes the project") from exc
            asset_bytes = _candidate_bytes(candidate, pending_outputs)
            if asset_bytes is None:
                raise AlignmentReportError(f"{label}.evidence file is missing: '{path_text}'")
            size = len(asset_bytes)
            digest = _hash_bytes(asset_bytes)
            if item.get("byteLength") != size or item.get("sha256") != digest:
                raise AlignmentReportError(
                    f"{label}.evidence file hash/length mismatch for '{path_text}'"
                )
            evidence_paths.add(path_text)
        if kinds != {"reference", "overlay", "package", "scene"}:
            raise AlignmentReportError(f"{label}.evidence is missing a required panel kind")
        if status != "pending_visual_review":
            observation = spot.get("manualObservation")
            if not isinstance(observation, dict):
                raise AlignmentReportError(
                    f"{label} cannot have {status} without a recorded manual observation"
                )
            if (
                not isinstance(observation.get("summary"), str)
                or not observation["summary"].strip()
            ):
                raise AlignmentReportError(
                    f"{label}.manualObservation.summary is required for {status}"
                )
            if (
                not isinstance(observation.get("reviewedBy"), str)
                or not observation["reviewedBy"].strip()
            ):
                raise AlignmentReportError(
                    f"{label} cannot have {status} without an identified reviewer"
                )
        if spot.get("debugContextId") != spot["id"]:
            raise AlignmentReportError(
                f"{label}.debugContextId does not match its registered spot id"
            )
        browser_session = spot.get("browserSession")
        if not isinstance(browser_session, dict):
            raise AlignmentReportError(
                f"{label}.browserSession must contain actual browser metadata"
            )
        if browser_session.get("expectedContextId") != spot["id"]:
            raise AlignmentReportError(
                f"{label}.browserSession context id differs from its registered spot"
            )
        credits = browser_session.get("sourceCredits")
        required_credits = {
            "Contains Environment Agency copyright and/or database right 2022 (DTM)",
            f"{OS_ATTRIBUTION} (OS OpenMap Local)",
            "© OpenStreetMap contributors; extract provided by Geofabrik GmbH",
        }
        if (
            not isinstance(credits, list)
            or any(not isinstance(item, str) for item in credits)
            or not required_credits.issubset(set(credits))
        ):
            raise AlignmentReportError(f"{label}.browserSession is missing source attribution")
        raw_browser = browser_records[spot["id"]]
        camera = raw_browser.get("camera")
        raw_runtime = raw_browser.get("runtime")
        target = raw_browser.get("targetLocalXZMetres")
        if (
            not isinstance(camera, dict)
            or not isinstance(raw_runtime, dict)
            or not isinstance(target, list)
            or len(target) != 2
        ):
            raise AlignmentReportError(f"{label}.browserSession raw camera evidence is malformed")
        reported_camera = browser_session.get("cameraPoseLocalMetres")
        configured_target = config_spot["control"]["local_xz_m"]
        camera_offset = raw_browser.get("cameraOffsetM")
        values = [
            camera.get("x"),
            camera.get("y"),
            camera.get("z"),
            camera.get("bearing"),
            camera.get("pitch"),
            *target,
            camera_offset,
            raw_browser.get("sampledGroundHeightM"),
            raw_browser.get("eyeHeightAboveTerrainM"),
        ]
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in values
        ):
            raise AlignmentReportError(f"{label}.browserSession has invalid camera values")
        target_matches = (
            math.dist(
                tuple(float(value) for value in target),
                tuple(float(value) for value in configured_target),
            )
            <= 0.001
        )
        camera_distance = math.hypot(
            float(camera["x"]) - float(target[0]),
            float(camera["z"]) - float(target[1]),
        )
        if (
            not target_matches
            or not isinstance(reported_camera, dict)
            or reported_camera != camera
            or not 29.99 <= float(camera_offset) <= 60.01
            or abs(camera_distance - float(camera_offset)) > 0.03
            or abs(
                float(camera["y"])
                - float(raw_browser["sampledGroundHeightM"])
                - float(raw_browser["eyeHeightAboveTerrainM"])
            )
            > 0.01
            or browser_session.get("targetLocalXZMetres") != target
            or browser_session.get("cameraOffsetM") != camera_offset
            or browser_session.get("sampledGroundHeightM")
            != raw_browser.get("sampledGroundHeightM")
            or browser_session.get("eyeHeightAboveTerrainM")
            != raw_browser.get("eyeHeightAboveTerrainM")
            or browser_session.get("expectedContextId") != raw_browser.get("expectedContextId")
            or browser_session.get("poseMethod") != raw_browser.get("poseMethod")
            or browser_session.get("viewport") != raw_browser.get("viewport")
            or browser_session.get("renderer") != raw_runtime.get("renderer")
            or browser_session.get("canvas") != raw_runtime.get("canvas")
        ):
            raise AlignmentReportError(
                f"{label}.browserSession pose/target does not match the accepted "
                "control and raw browser evidence"
            )
        scene_item = next(item for item in evidence if item.get("kind") == "scene")
        screenshot_path = raw_browser.get("screenshotPath")
        try:
            screenshot_file = Path(screenshot_path).resolve()
        except (TypeError, OSError) as exc:
            raise AlignmentReportError(f"{label} raw screenshot path is invalid") from exc
        expected_scene = _project_relative_file(
            project_root, scene_item.get("path"), f"{label}.sceneEvidence.path"
        )
        if screenshot_file != expected_scene.resolve():
            raise AlignmentReportError(
                f"{label} raw browser screenshot does not match scene evidence"
            )
    if len(evidence_paths) != 12:
        raise AlignmentReportError(
            "each comparison spot requires distinct reference, overlay, OSM-only and 3D scene images"  # noqa: E501
        )
    _validate_prior_candidate(report.get("priorCandidates"), spot_ids, project_root)
    issue_status = report.get("issueStatus")
    alignment_status = report.get("alignmentGateStatus")
    combined_status = report.get("combinedM5Status")
    if issue_status not in {"in_progress", "complete", "blocked"}:
        raise AlignmentReportError("issueStatus is unsupported")
    if alignment_status not in {"pending", "pass", "fail", "inconclusive", "unavailable"}:
        raise AlignmentReportError("alignmentGateStatus is unsupported")
    if combined_status != "pending":
        raise AlignmentReportError("combined M5 must remain pending until coordinator review")
    expected_alignment = (
        "pass"
        if statuses == {"pass"}
        else "fail"
        if "fail" in statuses
        else "unavailable"
        if "unavailable" in statuses
        else "inconclusive"
        if "inconclusive" in statuses
        else "pending"
    )
    if alignment_status != expected_alignment:
        raise AlignmentReportError(
            "alignmentGateStatus does not match the explicit per-spot outcomes"
        )
    expected_issue = (
        "complete" if statuses and statuses.issubset({"pass", "fail"}) else "in_progress"
    )
    if issue_status != expected_issue:
        raise AlignmentReportError(
            "issueStatus does not match whether all required outcomes are recorded"
        )
    return {
        "spotCount": len(spots),
        "evidenceFileCount": len(evidence_paths),
        "priorCandidateCount": 1,
        "spotStatuses": sorted(statuses),
    }


def _prepare_alignment_inputs(
    config_path: Path,
    source_manifest_path: Path,
    source_root: Path,
    terrain_package_dir: Path,
    road_package_dir: Path,
    building_package_dir: Path,
    project_root: Path,
) -> tuple[dict[str, Any], VerifiedComparisonSource, LocalPackages, list[dict[str, Any]]]:
    config, _ = _load_config(config_path)
    try:
        source = verify_comparison_source(source_manifest_path, source_root)
    except ComparisonSourceError as exc:
        raise AlignmentReportError(str(exc)) from exc
    packages = load_local_packages(terrain_package_dir, road_package_dir, building_package_dir)
    if not source.cover(AOI_BOUNDS_M):
        raise AlignmentReportError("selected OS 5 km tiles do not cover the full reviewed AOI")
    spots = _validated_control(config, packages)
    return config, source, packages, spots


def _render_alignment_panel_outputs(
    config_path: Path,
    source_manifest_path: Path,
    source_root: Path,
    terrain_package_dir: Path,
    road_package_dir: Path,
    building_package_dir: Path,
    project_root: Path,
) -> tuple[dict[Path, bytes], dict[str, Any]]:
    """Render all static panels into memory without changing existing evidence."""
    _config, source, packages, spots = _prepare_alignment_inputs(
        config_path,
        source_manifest_path,
        source_root,
        terrain_package_dir,
        road_package_dir,
        building_package_dir,
        project_root,
    )
    origin = packages.terrain_manifest["origin"]
    output_files: dict[Path, bytes] = {}
    panel_count = 0
    for spot in spots:
        bounds = tuple(float(value) for value in spot["window_bounds_bng_m"])
        window = read_palette_window(source, bounds)
        for panel_kind in ("reference", "overlay", "package"):
            image = _panel_bytes(spot, window, packages, panel_kind)
            relative = (
                Path("docs/milestones/screenshots") / f"TVW-012-{spot['id']}-{panel_kind}.png"
            )
            output_files[project_root / relative] = image
            panel_count += 1
    return output_files, {
        "panelCount": panel_count,
        "spotCount": len(spots),
        "tiles": sorted({tile.path.name for tile in source.tiles}),
        "sourceArchiveSha256": source.record["archive"]["sha256"],
        "terrainOrigin": origin,
    }


def render_alignment_panels(
    config_path: Path,
    source_manifest_path: Path,
    source_root: Path,
    terrain_package_dir: Path,
    road_package_dir: Path,
    building_package_dir: Path,
    project_root: Path,
) -> dict[str, Any]:
    """Generate and atomically publish the source, overlay, and OSM-only panels."""
    output_files, result = _render_alignment_panel_outputs(
        config_path,
        source_manifest_path,
        source_root,
        terrain_package_dir,
        road_package_dir,
        building_package_dir,
        project_root,
    )
    _atomic_write_outputs(output_files)
    return result


def _write_validated_alignment_report(
    report: dict[str, Any],
    panel_outputs: dict[Path, bytes],
    project_root: Path,
) -> Path:
    """Validate the complete candidate output set before one rollback-safe publication."""
    validate_alignment_report(report, project_root, pending_outputs=panel_outputs)
    report_bytes = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )
    report_path = project_root / "docs/milestones/artifacts/TVW-012-alignment.json"
    markdown_path = project_root / "docs/milestones/TVW-012.md"
    outputs = dict(panel_outputs)
    outputs[report_path] = report_bytes
    outputs[markdown_path] = _markdown_report(report).encode("utf-8")
    _atomic_write_outputs(outputs)
    return report_path


def build_alignment_artifacts(
    config_path: Path,
    source_manifest_path: Path,
    source_root: Path,
    terrain_package_dir: Path,
    road_package_dir: Path,
    building_package_dir: Path,
    project_root: Path,
) -> dict[str, Any]:
    """Refresh static panels and write an integrity-bound report after browser evidence exists."""
    panel_outputs, _panel_metadata = _render_alignment_panel_outputs(
        config_path,
        source_manifest_path,
        source_root,
        terrain_package_dir,
        road_package_dir,
        building_package_dir,
        project_root,
    )
    config, source, packages, spots = _prepare_alignment_inputs(
        config_path,
        source_manifest_path,
        source_root,
        terrain_package_dir,
        road_package_dir,
        building_package_dir,
        project_root,
    )
    reports: list[dict[str, Any]] = []
    browser_evidence_path = project_root / "docs/milestones/artifacts/TVW-012-browser-evidence.json"
    browser_evidence, browser_evidence_bytes = _read_json(
        browser_evidence_path, "Playwright browser evidence"
    )
    prior_candidate_path = (
        project_root / "docs/milestones/artifacts/TVW-012-prior-sw-inconclusive.json"
    )
    prior_candidate, prior_candidate_bytes = _read_json(
        prior_candidate_path, "preserved inconclusive SW candidate"
    )
    if (
        prior_candidate.get("formatVersion") != 1
        or prior_candidate.get("candidateRole")
        != "inconclusive prior candidate; not counted among active comparison spots"
        or not isinstance(prior_candidate.get("record"), dict)
    ):
        raise AlignmentReportError("preserved prior SW candidate artifact has invalid metadata")
    for error_field in ("consoleErrors", "pageErrors", "failedRequests"):
        if browser_evidence.get(error_field) != []:
            raise AlignmentReportError(
                f"actual browser evidence records unexpected {error_field}: "
                f"{browser_evidence.get(error_field)!r}"
            )
    browser_records = browser_evidence.get("evidence")
    if not isinstance(browser_records, list) or len(browser_records) != 3:
        raise AlignmentReportError(
            "Playwright evidence must contain exactly three registered scenes"
        )
    browser_by_context: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(browser_records):
        if not isinstance(item, dict):
            raise AlignmentReportError(f"Playwright evidence[{index}] must be an object")
        context_id = item.get("expectedContextId")
        if not isinstance(context_id, str) or not context_id or context_id in browser_by_context:
            raise AlignmentReportError(
                f"Playwright evidence[{index}].expectedContextId must be unique nonempty text"
            )
        browser_by_context[context_id] = item
    if set(browser_by_context) != {spot["id"] for spot in spots}:
        raise AlignmentReportError("Playwright evidence context IDs differ from the selected spots")
    spot_by_id = {spot["id"]: spot for spot in spots}
    for spot_id, browser_record in browser_by_context.items():
        pose = browser_record.get("camera")
        runtime = browser_record.get("runtime")
        viewport = browser_record.get("viewport")
        target_local = browser_record.get("targetLocalXZMetres")
        camera_offset = browser_record.get("cameraOffsetM")
        if (
            not isinstance(pose, dict)
            or not isinstance(runtime, dict)
            or not isinstance(viewport, dict)
            or not isinstance(target_local, list)
            or len(target_local) != 2
            or browser_record.get("expectedContextId") != spot_id
            or browser_record.get("poseMethod")
            != "development-only QA camera pose setter; no camera travel is implied"
            or browser_record.get("browserVersion") in {None, ""}
            or not isinstance(browser_record.get("browserName"), str)
        ):
            raise AlignmentReportError(f"Playwright evidence for {spot_id} is incomplete")
        numeric = [
            pose.get("x"),
            pose.get("y"),
            pose.get("z"),
            pose.get("bearing"),
            pose.get("pitch"),
            browser_record.get("sampledGroundHeightM"),
            browser_record.get("eyeHeightAboveTerrainM"),
            *target_local,
            camera_offset,
            viewport.get("width"),
            viewport.get("height"),
            viewport.get("devicePixelRatio"),
        ]
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in numeric
        ):
            raise AlignmentReportError(
                f"Playwright evidence for {spot_id} has invalid pose/viewport values"
            )
        if not isinstance(runtime.get("renderer"), str) or not runtime.get("renderer"):
            raise AlignmentReportError(f"Playwright renderer identity is missing for {spot_id}")
        configured_target = spot_by_id[spot_id]["control"]["local_xz_m"]
        target_matches = (
            math.hypot(
                float(target_local[0]) - float(configured_target[0]),
                float(target_local[1]) - float(configured_target[1]),
            )
            <= 0.001
        )
        camera_offset_matches = (
            29.99 <= float(camera_offset) <= 60.01
            and abs(
                math.hypot(
                    float(pose["x"]) - float(target_local[0]),
                    float(pose["z"]) - float(target_local[1]),
                )
                - float(camera_offset)
            )
            <= 0.03
        )
        if not target_matches or not camera_offset_matches:
            raise AlignmentReportError(
                f"Playwright camera target/offset does not match the registered context for {spot_id}"  # noqa: E501
            )

    for spot in spots:
        bounds = tuple(float(value) for value in spot["window_bounds_bng_m"])
        window = read_palette_window(source, bounds)
        panels: list[dict[str, Any]] = []
        for panel_kind in ("reference", "overlay", "package"):
            relative = (
                Path("docs/milestones/screenshots") / f"TVW-012-{spot['id']}-{panel_kind}.png"
            )
            image_path = project_root / relative
            image_bytes = panel_outputs.get(image_path)
            if image_bytes is None:
                raise AlignmentReportError(
                    f"registered {panel_kind} panel is missing for {spot['id']}: '{relative.as_posix()}'"  # noqa: E501
                )
            panels.append(
                {
                    "kind": panel_kind,
                    "path": relative.as_posix(),
                    "byteLength": len(image_bytes),
                    "sha256": _hash_bytes(image_bytes),
                }
            )
        scene_path = Path("docs/milestones/screenshots") / f"TVW-012-{spot['id']}-scene.png"
        scene_image = project_root / scene_path
        if not scene_image.is_file():
            raise AlignmentReportError(
                f"actual 3D browser scene evidence is missing for {spot['id']}: '{scene_path.as_posix()}'"  # noqa: E501
            )
        scene_bytes = scene_image.read_bytes()
        scene_evidence = {
            "kind": "scene",
            "path": scene_path.as_posix(),
            "byteLength": len(scene_bytes),
            "sha256": _hash_bytes(scene_bytes),
        }
        browser_record = browser_by_context[spot["id"]]
        expected_screenshot = project_root / browser_record.get("screenshotPath", "")
        if expected_screenshot.resolve() != scene_image.resolve():
            raise AlignmentReportError(
                f"Playwright screenshot path does not match registered scene for {spot['id']}"
            )
        if browser_record.get("expectedContextId") != spot["id"]:
            raise AlignmentReportError(f"Playwright scene context mismatch for {spot['id']}")
        status = spot["alignment_status"]
        raw_observation = spot.get("manual_observation")
        observation = (
            {
                "summary": raw_observation.get("summary"),
                "reviewedBy": raw_observation.get("reviewed_by"),
                "method": raw_observation.get("method"),
                "confidence": raw_observation.get("confidence"),
                "referencePointBngM": raw_observation.get("reference_point_bng_m"),
                "screeningAssessment": raw_observation.get("screening_assessment"),
            }
            if isinstance(raw_observation, dict)
            else None
        )
        if status in {"pass", "fail"} and not isinstance(observation, dict):
            raise AlignmentReportError(
                f"{spot['id']} cannot be marked {status} before its manual observation is recorded"
            )
        bng_window = window.bounds_m
        report_spot = {
            "id": spot["id"],
            "label": spot["label"],
            "selectionStatus": spot["selection_status"],
            "selectionRationale": spot["selection_rationale"],
            "originalContext": spot["original_context"],
            "control": {
                "featureRole": spot["control"]["feature_role"],
                "osmNodeId": spot["control"]["osm_node_id"],
                "osmWayIds": spot["control"]["osm_way_ids"],
                "roadNames": spot["control"]["road_names"],
                "localXZMetres": spot["control"]["local_xz_m"],
                "bngENMetres": spot["control"]["bng_e_n_m"],
                "wgs84LonLat": spot["control"]["wgs84_lon_lat"],
                "pixelReference": {
                    "registration": "AREA_OR_POINT=Area; source raster is not warped or resampled",
                    "pixelSizeM": 1.0,
                    "requestedWindowBNGMetres": list(bounds),
                    "actualPixelEdgeWindowBNGMetres": list(bng_window),
                    "manualReferencePointBNGMetres": observation.get("referencePointBngM")
                    if isinstance(observation, dict)
                    else None,
                },
            },
            "comparisonWindow": {
                "bngBoundsM": list(bounds),
                "actualRasterPixelEdgeBoundsM": list(bng_window),
                "widthPixels": window.width,
                "heightPixels": window.height,
                "pixelSizeM": 1.0,
                "tileNames": list(window.tile_names),
            },
            "debugContextId": spot["debug_context_id"],
            "alignmentStatus": status,
            "manualObservation": observation,
            "browserSession": {
                "browserName": browser_record["browserName"],
                "browserVersion": browser_record["browserVersion"],
                "viewport": browser_record["viewport"],
                "renderer": browser_record["runtime"]["renderer"],
                "canvas": browser_record["runtime"]["canvas"],
                "cameraPoseLocalMetres": browser_record["camera"],
                "sampledGroundHeightM": browser_record["sampledGroundHeightM"],
                "eyeHeightAboveTerrainM": browser_record["eyeHeightAboveTerrainM"],
                "expectedContextId": browser_record["expectedContextId"],
                "poseMethod": browser_record["poseMethod"],
                "targetLocalXZMetres": browser_record["targetLocalXZMetres"],
                "cameraOffsetM": browser_record["cameraOffsetM"],
                "sourceCredits": [
                    "Contains Environment Agency copyright and/or database right 2022 (DTM)",
                    "Contains Ordnance Survey data © Crown copyright and database right 2026 (OS OpenMap Local)",  # noqa: E501
                    "© OpenStreetMap contributors; extract provided by Geofabrik GmbH",
                ],
            },
            "evidence": [*panels, scene_evidence],
        }
        reports.append(report_spot)

    spot_statuses = {spot["alignmentStatus"] for spot in reports}
    if spot_statuses == {"pass"}:
        alignment_gate = "pass"
    elif "fail" in spot_statuses:
        alignment_gate = "fail"
    elif "unavailable" in spot_statuses:
        alignment_gate = "unavailable"
    elif "inconclusive" in spot_statuses:
        alignment_gate = "inconclusive"
    else:
        alignment_gate = "pending"
    issue_status = (
        "complete"
        if spot_statuses.issubset({"pass", "fail"}) and len(spot_statuses) > 0
        else "in_progress"
    )
    try:
        config_relative = config_path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise AlignmentReportError("alignment config must reside within the project") from exc
    if config_relative != "config/alignment.torquay.json":
        raise AlignmentReportError("alignment report requires config/alignment.torquay.json")
    package_paths: dict[str, str] = {}
    for key, package_dir in (
        ("terrain", terrain_package_dir),
        ("roads", road_package_dir),
        ("buildings", building_package_dir),
    ):
        try:
            package_paths[key] = (
                package_dir.resolve().relative_to(project_root.resolve()).as_posix()
            )
        except ValueError as exc:
            raise AlignmentReportError(f"{key} package must reside within the project") from exc
    report = {
        "formatVersion": 1,
        "reportId": config["report_id"],
        "alignmentConfig": {
            "path": config_relative,
            "sha256": _hash_path(config_path.resolve()),
        },
        "issueStatus": issue_status,
        "alignmentGateStatus": alignment_gate,
        "combinedM5Status": "pending",
        "sourceIndependence": "independent_publisher_os_openmap_local",
        "source": {
            **_source_report_metadata(source.record),
        },
        "sourceManifest": {
            "path": source.manifest_path.relative_to(project_root).as_posix(),
            "sha256": _hash_path(source.manifest_path),
        },
        "browserSessionEvidence": {
            "path": browser_evidence_path.relative_to(project_root).as_posix(),
            "byteLength": len(browser_evidence_bytes),
            "sha256": _hash_bytes(browser_evidence_bytes),
        },
        "aoi": {
            "boundsM": list(AOI_BOUNDS_M),
            "selectionStatus": "selected_pending_coverage",
            "coverageStatus": "not_checked",
        },
        "coordinateReference": {
            "crs": "EPSG:27700",
            "aoi": {
                "boundsM": list(AOI_BOUNDS_M),
                "selectionStatus": "selected_pending_coverage",
                "coverageStatus": "not_checked",
            },
            "axisMapping": AXIS_MAPPING,
            "rasterRegistration": RASTER_REGISTRATION,
            "localCoordinateOperation": packages.road_manifest.get("coordinateOperation", {}).get(
                "wgs84ToBng"
            ),
            "uncertaintyComponents": [
                "Pinned OSM-to-BNG operation reports 2 m accuracy; preferred OSTN15 grid is unavailable and PROJ best_available is false.",  # noqa: E501
                "OS OpenMap–Local is a generalized cartographic raster with nominal 1:10,000 map scale, not a survey control source.",  # noqa: E501
                "Raster pixel resolution is 1 m; symbol line widths and manual pixel selection limit centerline precision.",  # noqa: E501
                "OS edition and OSM extract have different update/survey vintages; OSM coordinates have mapping uncertainty.",  # noqa: E501
            ],
        },
        "screeningRule": {
            "triggerMetres": SCREENING_THRESHOLD_M,
            "meaning": "Predeclared investigation trigger after scale, symbol thickness and uncertainty review; not a survey tolerance or accuracy guarantee.",  # noqa: E501
        },
        "localPackages": {**_package_summary(packages), "packagePaths": package_paths},
        "manualReview": {
            "reviewedBy": config["manual_review"]["reviewed_by"],
            "reviewedAtUtc": config["manual_review"]["reviewed_at_utc"],
            "method": config["manual_review"]["method"],
            "observationsAreExplicitConfigInputs": True,
        },
        "spots": reports,
        "priorCandidates": [
            {
                "path": prior_candidate_path.relative_to(project_root).as_posix(),
                "byteLength": len(prior_candidate_bytes),
                "sha256": _hash_bytes(prior_candidate_bytes),
                "record": prior_candidate["record"],
            }
        ],
        "issues": config.get("issues", []),
        "notes": [
            "Feature counts do not prove OSM or AOI completeness.",
            "The NW Baron Road / Lindfield Close context remains recorded as unavailable/ambiguous and is not counted; Pencorse Road / Audley Avenue is the accepted replacement selection.",  # noqa: E501
            "The former SW St Vincent’s Road / Chapel Court candidate remains separately preserved as inconclusive and is not counted; Teignmouth Road / Snowberry Close is the accepted replacement selection.",  # noqa: E501
            "Three bounded map comparisons do not approve/freeze the AOI or complete M2.",
            "Combined M5 remains pending coordinator review and cannot pass from image generation alone.",  # noqa: E501
        ],
    }
    report_path = _write_validated_alignment_report(report, panel_outputs, project_root)
    return {
        "report": report_path,
        "spotCount": len(reports),
        "issueStatus": issue_status,
        "alignmentGateStatus": alignment_gate,
        "combinedM5Status": "pending",
    }


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# TVW-012: Independent map alignment comparison",
        "",
        f"**Issue status:** {report['issueStatus']} · **Alignment gate:** {report['alignmentGateStatus']} · **Combined M5:** {report['combinedM5Status']}",  # noqa: E501
        "**AOI:** `selected_pending_coverage` / `not_checked`",
        "",
        "## Source and registration",
        "",
        f"- Product: {report['source']['publisher']} {report['source']['product']} ({report['source']['edition']}).",  # noqa: E501
        f"- Archive: `{report['source']['archiveFilename']}`; {report['source']['archiveBytes']:,} bytes; SHA-256 `{report['source']['archiveSha256']}`.",  # noqa: E501
        f"- Licence: [{report['source']['licence']['name']}]({report['source']['licence']['url']}); attribution: `{report['source']['licence']['requiredAttribution']}`.",  # noqa: E501
        "- Raster source CRS/registration: EPSG:27700; palette GeoTIFF, 1 m pixels, AREA_OR_POINT=Area. The imagery is unwarped.",  # noqa: E501
        "- OSM-to-BNG uses the recorded EPSG:1314 + EPSG:19916 operation (2 m reported accuracy); preferred OSTN15 is unavailable and `best_available` is false.",  # noqa: E501
        "- 10 m is a screening trigger after scale/symbol uncertainty, not a survey tolerance or OS accuracy guarantee.",  # noqa: E501
        "",
        "## Spots",
        "",
    ]
    table_header = ["Spot", "OSM control", "OS pixel window", "Status", "Observation"]
    table_records: list[list[str]] = []
    for spot in report["spots"]:
        c = spot["control"]
        obs = spot.get("manualObservation")
        summary = (
            obs.get("summary", "Manual visual review not yet recorded.")
            if isinstance(obs, dict)
            else "Manual visual review not yet recorded."
        )
        tile_names = ", ".join(spot["comparisonWindow"]["tileNames"])
        road_ids = ", ".join(f"way/{value}" for value in c["osmWayIds"])
        pixel_dimensions = (
            f"{spot['comparisonWindow']['widthPixels']}×"
            f"{spot['comparisonWindow']['heightPixels']} px"
        )
        table_records.append(
            [
                spot["label"],
                f"node/{c['osmNodeId']}; ways {road_ids}",
                f"{tile_names}; {pixel_dimensions}",
                spot["alignmentStatus"],
                summary,
            ]
        )
    widths = [
        max(len(row[index]) for row in [table_header, *table_records])
        for index in range(len(table_header))
    ]

    def format_row(cells: list[str]) -> str:
        return (
            "| "
            + " | ".join(cell.ljust(width) for cell, width in zip(cells, widths, strict=True))
            + " |"
        )

    lines.append(format_row(table_header))
    lines.append("| " + " | ".join("-" * width for width in widths) + " |")
    lines.extend(format_row(table_record) for table_record in table_records)
    lines.append("")
    for spot in report["spots"]:
        lines.extend([f"### {spot['label']}", ""])
        for evidence in spot["evidence"]:
            evidence_link = Path(evidence["path"]).relative_to("docs/milestones").as_posix()
            lines.append(f"- [{spot['id']} {evidence['kind']} panel]({evidence_link})")
            if evidence["kind"] == "scene":
                lines.append(
                    "  - Source credit: Environment Agency copyright/database right 2022 (DTM); "
                    "Ordnance Survey data © Crown copyright and database right 2026; "
                    "© OpenStreetMap contributors, extract provided by Geofabrik GmbH."
                )
        lines.append("")
    prior = report["priorCandidates"][0]["record"]
    prior_observation = prior["manualObservation"]
    lines.extend(
        [
            "## Prior candidate, retained but not counted",
            "",
            f"**{prior['label']}** remains `inconclusive` after its registered review. {prior_observation['summary']}",  # noqa: E501
            "",
        ]
    )
    for evidence in prior["evidence"]:
        evidence_link = Path(evidence["path"]).relative_to("docs/milestones").as_posix()
        lines.append(f"- [Prior candidate {evidence['kind']} panel]({evidence_link})")
    lines.append(
        "- [Integrity-bound prior candidate record](artifacts/TVW-012-prior-sw-inconclusive.json)"
    )
    lines.append("")
    lines.extend(
        [
            "## Limits and gate decision",
            "",
            "The original NW Baron Road / Lindfield Close context remains unavailable/ambiguous: its named target ways are absent from the clipped OSM export, and its nearest eligible way is an unnamed footway. It is not counted. Pencorse Road / Audley Avenue is the accepted in-AOI replacement selection.",  # noqa: E501
            "The prior SW St Vincent’s Road / Chapel Court candidate remains inconclusive and is not counted; Teignmouth Road / Snowberry Close is the accepted replacement selection.",  # noqa: E501
            "",
            "OS OpenMap–Local is generalized cartography and OSM is a mapped database; labels, road symbol widths, editions, mapping dates, and the reported 2 m coordinate-operation accuracy constrain what can be concluded. These bounded comparisons cannot prove completeness or approve/freeze the AOI.",  # noqa: E501
            "",
            "The combined M5 gate remains pending coordinator review. M2 coverage and TVW-013 remain separate.",  # noqa: E501
            "",
        ]
    )
    return "\n".join(lines)
