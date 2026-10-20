"""Build a deterministic local 2 m EA DTM heightfield package for TVW-008."""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib import patheffects
from matplotlib.colors import Normalize
from matplotlib.patches import Rectangle
from rasterio.windows import Window

from .aoi import generate_selection
from .config import AoiConfig
from .coordinates import transform_wgs84_to_bng
from .terrain_sources import inspect_raster

OUTPUT_SPACING_M = 2.0
OUTPUT_COLUMNS = 501
OUTPUT_ROWS = 501
MAX_SOURCE_WINDOW_CELLS = 4_100_000
RESAMPLING_ERROR_LIMIT_M = 0.25
FLOAT32_ERROR_LIMIT_M = 1e-4
PROBE_SEED = 20261017
EA_ATTRIBUTION = (
    "Contains public sector information licensed under the Open Government Licence v3.0. "
    "© Environment Agency copyright and/or database right 2022."
)
EA_PRODUCT = "LIDAR Composite DTM 1 m (2022 composite)"
VERTICAL_REFERENCE = "Ordnance Survey Newlyn using OSTN’15 and OSGM’15 transformation models"
TERRAIN_GENERATOR = "torquay_pipeline.terrain_export"
TERRAIN_GENERATOR_VERSION = "0.1.0"


class TerrainExportError(ValueError):
    """Raised when source terrain cannot be safely resampled or published."""


@dataclass(frozen=True)
class ResampledGrid:
    """Absolute pixel-center interpolations on the output AOI vertex lattice."""

    elevations_m: np.ndarray
    eastings_m: np.ndarray
    northings_m: np.ndarray
    origin_elevation_m: float
    bounds_m: tuple[float, float, float, float]


def _source_valid(
    dataset: rasterio.io.DatasetReader, values: np.ndarray, mask: np.ndarray
) -> np.ndarray:
    nodata = dataset.nodata
    valid = (mask > 0) & np.isfinite(values)
    if nodata is not None:
        valid &= ~np.isnan(values) if math.isnan(float(nodata)) else values != nodata
    return valid


def _validate_source(path: Path) -> tuple[float, float, int, int]:
    """Validate the exact supported 1 m pixel-center raster grid."""
    metadata, _sidecar = inspect_raster(path)
    if metadata.crs != "EPSG:27700":
        raise TerrainExportError(f"source '{path.name}' must use EPSG:27700")
    left, _bottom, _right, top = metadata.bounds
    if not (float(left).is_integer() and float(top).is_integer()):
        raise TerrainExportError(f"source '{path.name}' must have integer-aligned grid bounds")
    return float(left), float(top), metadata.width, metadata.height


def _sample_bilinear_mosaic(
    raster_paths: list[Path], eastings_m: np.ndarray, northings_m: np.ndarray
) -> np.ndarray:
    """Sample an output lattice from source pixel centers without filling/extrapolation."""
    if not raster_paths:
        raise TerrainExportError("no verified source rasters were supplied")
    if eastings_m.shape != northings_m.shape or eastings_m.ndim != 2:
        raise TerrainExportError("output eastings and northings must be matching 2D arrays")
    if not (np.isfinite(eastings_m).all() and np.isfinite(northings_m).all()):
        raise TerrainExportError("output coordinates must be finite")

    ordered = sorted(
        (path.resolve() for path in raster_paths), key=lambda item: item.as_posix().casefold()
    )
    metadata = [_validate_source(path) for path in ordered]
    grid_left = min(item[0] for item in metadata)
    grid_top = max(item[1] for item in metadata)
    fractional_columns = eastings_m - grid_left - 0.5
    fractional_rows = grid_top - northings_m - 0.5
    lower_columns = np.floor(fractional_columns).astype(np.int64)
    lower_rows = np.floor(fractional_rows).astype(np.int64)
    min_column = int(lower_columns.min())
    max_column = int(lower_columns.max()) + 1
    min_row = int(lower_rows.min())
    max_row = int(lower_rows.max()) + 1
    shape = (max_row - min_row + 1, max_column - min_column + 1)
    if shape[0] <= 0 or shape[1] <= 0 or shape[0] * shape[1] > MAX_SOURCE_WINDOW_CELLS:
        raise TerrainExportError(
            "requested source window is invalid or exceeds the safe memory limit"
        )
    values = np.full(shape, np.nan, dtype=np.float64)
    valid = np.zeros(shape, dtype=bool)
    conflicts = 0

    for path, (left, top, width, height) in zip(ordered, metadata, strict=True):
        tile_column_start = int(left - grid_left)
        tile_row_start = int(grid_top - top)
        col_start = max(min_column, tile_column_start)
        col_stop = min(max_column + 1, tile_column_start + width)
        row_start = max(min_row, tile_row_start)
        row_stop = min(max_row + 1, tile_row_start + height)
        if col_start >= col_stop or row_start >= row_stop:
            continue

        local_col = col_start - tile_column_start
        local_row = row_start - tile_row_start
        window_width = col_stop - col_start
        window_height = row_stop - row_start
        try:
            with rasterio.open(path) as dataset:
                window = Window(local_col, local_row, window_width, window_height)
                source_values = dataset.read(1, window=window).astype(np.float64)
                source_mask = dataset.read_masks(1, window=window)
                source_valid = _source_valid(dataset, source_values, source_mask)
        except Exception as exc:
            raise TerrainExportError(
                f"cannot read required source window from '{path.name}': {exc}"
            ) from exc

        target_rows = slice(row_start - min_row, row_stop - min_row)
        target_columns = slice(col_start - min_column, col_stop - min_column)
        target_values = values[target_rows, target_columns]
        target_valid = valid[target_rows, target_columns]
        overlap = target_valid & source_valid
        if np.any(overlap):
            conflicts += int(
                np.count_nonzero(overlap & (np.abs(target_values - source_values) > 1e-6))
            )
        if conflicts:
            raise TerrainExportError(
                "overlapping source rasters contain conflicting valid elevations"
            )
        fill = source_valid & ~target_valid
        target_values[fill] = source_values[fill]
        target_valid |= source_valid

    local_columns = lower_columns - min_column
    local_rows = lower_rows - min_row
    fractions_u = fractional_columns - lower_columns
    fractions_v = fractional_rows - lower_rows
    c0 = local_columns
    c1 = c0 + 1
    r0 = local_rows
    r1 = r0 + 1
    corners = (
        (r0, c0, (1 - fractions_u) * (1 - fractions_v)),
        (r0, c1, fractions_u * (1 - fractions_v)),
        (r1, c0, (1 - fractions_u) * fractions_v),
        (r1, c1, fractions_u * fractions_v),
    )
    result = np.zeros(eastings_m.shape, dtype=np.float64)
    required_missing = np.zeros(eastings_m.shape, dtype=bool)
    for row_index, column_index, weight in corners:
        contributor_valid = valid[row_index, column_index]
        required = weight > 0.0
        required_missing |= required & ~contributor_valid
        result += np.where(contributor_valid, values[row_index, column_index], 0.0) * weight
    if np.any(required_missing):
        missing_count = int(np.count_nonzero(required_missing))
        first_row, first_column = np.argwhere(required_missing)[0]
        raise TerrainExportError(
            f"source coverage cannot bilinearly support {missing_count} output vertex/vertices; "
            f"first missing at output row {first_row}, column {first_column} "
            f"(E={eastings_m[first_row, first_column]:.3f}, "
            f"N={northings_m[first_row, first_column]:.3f} m). NoData and uncovered inputs "
            "are not filled or extrapolated."
        )
    return result


def resample_vertices(
    raster_paths: list[Path],
    bounds_m: tuple[float, float, float, float],
    *,
    columns: int = OUTPUT_COLUMNS,
    rows: int = OUTPUT_ROWS,
    spacing_m: float = OUTPUT_SPACING_M,
) -> ResampledGrid:
    """Bilinearly sample source 1 m pixel centers on an inclusive vertex grid."""
    west, south, east, north = bounds_m
    if columns < 2 or rows < 2 or not math.isfinite(spacing_m) or spacing_m <= 0:
        raise TerrainExportError("output grid dimensions and spacing must be positive")
    if not all(math.isfinite(item) for item in bounds_m) or not west < east or not south < north:
        raise TerrainExportError("AOI bounds must be finite and ordered")
    expected_width = (columns - 1) * spacing_m
    expected_depth = (rows - 1) * spacing_m
    if not math.isclose(east - west, expected_width, rel_tol=0, abs_tol=1e-7):
        raise TerrainExportError("output columns and spacing do not span the AOI width")
    if not math.isclose(north - south, expected_depth, rel_tol=0, abs_tol=1e-7):
        raise TerrainExportError("output rows and spacing do not span the AOI depth")
    eastings = west + np.arange(columns, dtype=np.float64) * spacing_m
    northings = north - np.arange(rows, dtype=np.float64) * spacing_m
    x_grid, y_grid = np.meshgrid(eastings, northings)
    elevations = _sample_bilinear_mosaic(raster_paths, x_grid, y_grid)
    center_row, center_column = rows // 2, columns // 2
    if (rows - 1) % 2 or (columns - 1) % 2:
        raise TerrainExportError("center-origin grid must have a vertex at the AOI center")
    origin = float(elevations[center_row, center_column])
    return ResampledGrid(
        elevations_m=elevations,
        eastings_m=eastings,
        northings_m=northings,
        origin_elevation_m=origin,
        bounds_m=bounds_m,
    )


def _independent_pixel_center_sample(
    raster_paths: list[Path], eastings_m: float, northings_m: float
) -> float:
    """Read a cell center by its containing pixel, independently of the mosaic sampler."""
    for path in sorted(raster_paths, key=lambda item: item.as_posix().casefold()):
        try:
            with rasterio.open(path) as dataset:
                bounds = dataset.bounds
                if not (
                    bounds.left <= eastings_m < bounds.right
                    and bounds.bottom < northings_m <= bounds.top
                ):
                    continue
                col = int(math.floor(eastings_m - bounds.left))
                row = int(math.floor(bounds.top - northings_m))
                value = dataset.read(1, window=Window(col, row, 1, 1))[0, 0]
                mask = dataset.read_masks(1, window=Window(col, row, 1, 1))[0, 0]
                if bool(_source_valid(dataset, np.asarray([[value]]), np.asarray([[mask]]))[0, 0]):
                    return float(value)
        except Exception as exc:
            raise TerrainExportError(
                f"independent probe could not read '{path.name}': {exc}"
            ) from exc
    raise TerrainExportError(
        f"independent probe at E={eastings_m:.3f}, N={northings_m:.3f} m has no valid source pixel"
    )


def _independent_bilinear_sample(
    raster_paths: list[Path], eastings_m: float, northings_m: float
) -> float:
    """Bilinearly interpolate by direct per-center raster reads, not the output mosaic."""
    infos = [_validate_source(path) for path in raster_paths]
    left = min(item[0] for item in infos)
    top = max(item[1] for item in infos)
    col_fraction = eastings_m - left - 0.5
    row_fraction = top - northings_m - 0.5
    col0, row0 = math.floor(col_fraction), math.floor(row_fraction)
    u, v = col_fraction - col0, row_fraction - row0
    values = (
        _independent_pixel_center_sample(raster_paths, left + col0 + 0.5, top - row0 - 0.5),
        _independent_pixel_center_sample(raster_paths, left + col0 + 1.5, top - row0 - 0.5),
        _independent_pixel_center_sample(raster_paths, left + col0 + 0.5, top - row0 - 1.5),
        _independent_pixel_center_sample(raster_paths, left + col0 + 1.5, top - row0 - 1.5),
    )
    a, b, c, d = values
    return (1 - v) * ((1 - u) * a + u * b) + v * ((1 - u) * c + u * d)


def _provenance_sources(
    source_manifest: dict[str, Any], verified_sources: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    manifest_records = {
        record.get("tile_name"): record
        for record in source_manifest.get("sources", [])
        if isinstance(record, dict)
    }
    sources: list[dict[str, Any]] = []
    for source in verified_sources:
        raster = source["raster"]
        archive = source["archive"]
        sidecar = source["metadata_sidecar"]
        manifest_record = manifest_records.get(source.get("tile_name"), {})
        recorded_sidecar = manifest_record.get("metadata_sidecar", {})
        sources.append(
            {
                "tileName": source.get("tile_name"),
                "archiveFilename": archive["filename"],
                "archiveSizeBytes": archive["size_bytes"],
                "archiveSha256": archive["sha256"],
                "archiveDownloadUrl": source.get("download_url"),
                "downloadDate": source.get("download_date"),
                "archiveRasterMember": archive["raster_member"]["member"],
                "archiveXmlMember": archive["metadata_sidecar_member"]["member"],
                "rasterFilename": raster["filename"],
                "rasterSizeBytes": raster["size_bytes"],
                "rasterSha256": raster["sha256"],
                "rasterCrs": raster["crs"],
                "rasterTransform": raster["transform"],
                "rasterBoundsM": raster["bounds_m"],
                "rasterWidthPixels": raster["width_pixels"],
                "rasterHeightPixels": raster["height_pixels"],
                "rasterResolutionM": raster["resolution_m"],
                "rasterDtype": raster["dtype"],
                "rasterNodata": raster["nodata"],
                "xmlFilename": sidecar["filename"],
                "xmlSizeBytes": sidecar["size_bytes"],
                "xmlSha256": sidecar["sha256"],
                "tileSurveyPeriod": recorded_sidecar.get("tile_survey_period"),
                "xmlVerticalReference": recorded_sidecar.get("vertical_reference"),
            }
        )
    return sources


def _build_qa(
    grid: ResampledGrid,
    raster_paths: list[Path],
    relative_values: np.ndarray,
) -> dict[str, Any]:
    rows, columns = grid.elevations_m.shape
    randomizer = random.Random(PROBE_SEED)
    random_indexes = randomizer.sample(range(rows * columns), 10)
    fixed_indexes = {
        "north_west_corner": 0,
        "north_east_corner": columns - 1,
        "south_west_corner": (rows - 1) * columns,
        "south_east_corner": rows * columns - 1,
        "center": (rows // 2) * columns + columns // 2,
    }
    fixed_indexes.update(_source_seam_probe_indexes(grid, raster_paths))
    probes: list[dict[str, Any]] = []
    for label, index in [
        *fixed_indexes.items(),
        *((f"seeded_{i + 1}", idx) for i, idx in enumerate(random_indexes)),
    ]:
        row, column = divmod(index, columns)
        easting = float(grid.eastings_m[column])
        northing = float(grid.northings_m[row])
        reference = _independent_bilinear_sample(raster_paths, easting, northing)
        generation = float(grid.elevations_m[row, column])
        quantized = float(relative_values[row, column])
        resampling_error = abs(generation - reference)
        quantization_error = abs(quantized - (reference - grid.origin_elevation_m))
        probes.append(
            {
                "label": label,
                "row": row,
                "column": column,
                "eastingM": easting,
                "northingM": northing,
                "independentBilinearElevationM": reference,
                "exportedBilinearElevationM": generation,
                "relativeFloat32M": quantized,
                "resamplingErrorM": resampling_error,
                "float32QuantizationErrorM": quantization_error,
            }
        )
    max_resampling_error = max(item["resamplingErrorM"] for item in probes)
    max_quantization_error = max(item["float32QuantizationErrorM"] for item in probes)
    if max_resampling_error > RESAMPLING_ERROR_LIMIT_M:
        raise TerrainExportError(
            "independent bilinear probes exceed the "
            f"{RESAMPLING_ERROR_LIMIT_M:g} m resampling limit"
        )
    if max_quantization_error > FLOAT32_ERROR_LIMIT_M:
        raise TerrainExportError(
            f"Float32 probes exceed the {FLOAT32_ERROR_LIMIT_M:g} m quantization limit"
        )
    return {
        "formatVersion": 1,
        "status": "pass",
        "probeSeed": PROBE_SEED,
        "sampling": "bilinear between source 1 m area-pixel centers; no extrapolation or filling",
        "outputGrid": {
            "columns": columns,
            "rows": rows,
            "vertexCount": rows * columns,
            "spacingM": OUTPUT_SPACING_M,
            "boundsM": list(grid.bounds_m),
            "rowOrder": "north-to-south",
        },
        "originElevationM": grid.origin_elevation_m,
        "sourceBilinearElevationRangeM": [
            float(np.min(grid.elevations_m)),
            float(np.max(grid.elevations_m)),
        ],
        "relativeFloat32RangeM": [
            float(np.min(relative_values)),
            float(np.max(relative_values)),
        ],
        "errorBudgets": {
            "resamplingTargetM": RESAMPLING_ERROR_LIMIT_M,
            "maximumObservedResamplingErrorM": max_resampling_error,
            "float32QuantizationLimitM": FLOAT32_ERROR_LIMIT_M,
            "maximumObservedFloat32QuantizationErrorM": max_quantization_error,
            "errorTypesMeasuredSeparately": True,
        },
        "probes": probes,
        "allRequiredBilinearContributorsValid": True,
        "nodataFilled": False,
        "extrapolationUsed": False,
    }


def _source_seam_probe_indexes(grid: ResampledGrid, raster_paths: list[Path]) -> dict[str, int]:
    """Return probes immediately on either side of source boundaries crossing the grid."""
    if len(raster_paths) < 2:
        return {}
    source_grids = []
    for path in sorted(raster_paths, key=lambda item: item.as_posix().casefold()):
        left, top, width, height = _validate_source(path)
        source_grids.append((left, top - height, left + width, top))

    eastings = grid.eastings_m
    northings = grid.northings_m
    columns = len(eastings)
    grid_west, grid_east = float(eastings[0]), float(eastings[-1])
    grid_south, grid_north = float(northings[-1]), float(northings[0])
    probes: dict[str, int] = {}
    horizontal_seen: set[float] = set()
    vertical_seen: set[float] = set()

    def add_horizontal(seam: float, overlap_west: float, overlap_east: float) -> None:
        if seam in horizontal_seen or not grid_south < seam < grid_north:
            return
        left = max(overlap_west, grid_west)
        right = min(overlap_east, grid_east)
        north_rows = np.flatnonzero(northings > seam)
        south_rows = np.flatnonzero(northings < seam)
        if left > right or not len(north_rows) or not len(south_rows):
            return
        horizontal_seen.add(seam)
        column = int(np.argmin(np.abs(eastings - (left + right) / 2)))
        north_row = int(north_rows[-1])
        south_row = int(south_rows[0])
        probes[f"source_seam_{len(horizontal_seen)}_north"] = north_row * columns + column
        probes[f"source_seam_{len(horizontal_seen)}_south"] = south_row * columns + column

    def add_vertical(seam: float, overlap_south: float, overlap_north: float) -> None:
        if seam in vertical_seen or not grid_west < seam < grid_east:
            return
        lower = max(overlap_south, grid_south)
        upper = min(overlap_north, grid_north)
        west_columns = np.flatnonzero(eastings < seam)
        east_columns = np.flatnonzero(eastings > seam)
        if lower > upper or not len(west_columns) or not len(east_columns):
            return
        vertical_seen.add(seam)
        row = int(np.argmin(np.abs(northings - (lower + upper) / 2)))
        west_column = int(west_columns[-1])
        east_column = int(east_columns[0])
        probes[f"source_seam_vertical_{len(vertical_seen)}_west"] = row * columns + west_column
        probes[f"source_seam_vertical_{len(vertical_seen)}_east"] = row * columns + east_column

    for first_index, first in enumerate(source_grids):
        first_west, first_south, first_east, first_north = first
        for second in source_grids[first_index + 1 :]:
            second_west, second_south, second_east, second_north = second
            overlap_west = max(first_west, second_west)
            overlap_east = min(first_east, second_east)
            overlap_south = max(first_south, second_south)
            overlap_north = min(first_north, second_north)
            if overlap_west < overlap_east:
                if math.isclose(first_north, second_south, abs_tol=1e-9):
                    add_horizontal(first_north, overlap_west, overlap_east)
                if math.isclose(second_north, first_south, abs_tol=1e-9):
                    add_horizontal(second_north, overlap_west, overlap_east)
            if overlap_south < overlap_north:
                if math.isclose(first_east, second_west, abs_tol=1e-9):
                    add_vertical(first_east, overlap_south, overlap_north)
                if math.isclose(second_east, first_west, abs_tol=1e-9):
                    add_vertical(second_east, overlap_south, overlap_north)
    return probes


def _load_wgs84_aoi_boundary(config: AoiConfig, geojson_path: Path | None = None) -> dict[str, Any]:
    """Read the generated geographic ring and verify it still matches this AOI."""
    source_path = geojson_path or (
        Path(__file__).resolve().parents[2]
        / (
            "docs/milestones/artifacts/AOI-1km-selection/aoi-selection.geojson"
            if config.profile == "historical_1km"
            else "docs/aoi-selection.geojson"
        )
    )
    try:
        source = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TerrainExportError(
            f"cannot read generated AOI boundary from {source_path}: {exc}"
        ) from exc
    features = source.get("features") if isinstance(source, dict) else None
    _selection, generated, _markdown = generate_selection(config)
    feature_id = f"{config.id}-aoi"
    source_features = (
        [
            feature
            for feature in features or []
            if isinstance(feature, dict) and feature.get("id") == feature_id
        ]
        if isinstance(features, list)
        else []
    )
    generated_features = [
        feature
        for feature in generated.get("features", [])
        if isinstance(feature, dict) and feature.get("id") == feature_id
    ]
    if (
        not isinstance(source, dict)
        or source.get("type") != "FeatureCollection"
        or len(source_features) != 1
        or len(generated_features) != 1
        or source_features[0] != generated_features[0]
    ):
        raise TerrainExportError(
            f"{source_path} candidate polygon does not match the configured AOI"
        )
    geometry = source_features[0].get("geometry")
    coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if (
        not isinstance(geometry, dict)
        or geometry.get("type") != "Polygon"
        or not isinstance(coordinates, list)
        or len(coordinates) != 1
    ):
        raise TerrainExportError(
            f"{source_path} must contain one Polygon exterior ring for {feature_id}"
        )
    ring = coordinates[0]
    if (
        not isinstance(ring, list)
        or len(ring) != 5
        or ring[0] != ring[-1]
        or any(
            not isinstance(position, list)
            or len(position) != 2
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in position
            )
            or not -180 <= position[0] <= 180
            or not -90 <= position[1] <= 90
            for position in ring
        )
    ):
        raise TerrainExportError(
            f"{source_path} candidate polygon must contain a finite, closed WGS84 ring"
        )
    return {
        "crs": "EPSG:4326",
        "coordinateOrder": "longitude-latitude",
        "geometryType": "Polygon",
        "ring": ring,
    }


def _manifest(
    config: AoiConfig,
    grid: ResampledGrid,
    binary: bytes,
    qa: dict[str, Any],
    sources: list[dict[str, Any]],
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    rows, columns = grid.elevations_m.shape
    west, south, east, north = grid.bounds_m
    try:
        anchor_easting, anchor_northing, operation_info = transform_wgs84_to_bng(
            config.anchor.longitude, config.anchor.latitude
        )
    except ValueError as exc:
        raise TerrainExportError(f"cannot record the configured anchor transform: {exc}") from exc
    if not (
        math.isclose(anchor_easting, config.center_bng_m[0], abs_tol=1e-7)
        and math.isclose(anchor_northing, config.center_bng_m[1], abs_tol=1e-7)
    ):
        raise TerrainExportError(
            "configured WGS84 anchor does not match its pinned EPSG:1314 + EPSG:19916 BNG center"
        )
    boundary_wgs84 = _load_wgs84_aoi_boundary(config)
    product = source_manifest.get("product")
    if not isinstance(product, dict):
        raise TerrainExportError("source manifest is missing publisher product metadata")
    catalogue_url = product.get("publisher_dataset_url")
    product_survey_period = product.get("catalogue_vintage")
    xml_copyright_conflict = product.get("metadata_note")
    if not all(
        isinstance(value, str) and value.strip()
        for value in (catalogue_url, product_survey_period, xml_copyright_conflict)
    ):
        raise TerrainExportError(
            "source manifest is missing publisher catalogue period or XML copyright details"
        )
    preferred_missing_grid_names = sorted(
        {
            str(grid_record.get("short_name"))
            for preferred in operation_info.preferred_missing_operations
            for grid_record in preferred.get("grids", [])
            if isinstance(grid_record, dict)
            and not grid_record.get("available", False)
            and isinstance(grid_record.get("short_name"), str)
            and grid_record.get("short_name")
        }
    )
    if not preferred_missing_grid_names:
        raise TerrainExportError(
            "pinned coordinate operation did not report its unavailable preferred grid"
        )
    anchor_wgs84 = {
        "postcode": config.anchor.postcode,
        "crs": "EPSG:4326",
        "longitude": config.anchor.longitude,
        "latitude": config.anchor.latitude,
        "coordinateMeaning": config.anchor.coordinate_meaning,
        "quality": config.anchor.quality,
        "sourceName": config.anchor.source_name,
        "sourceUrl": config.anchor.source_url,
        "sourceLicense": config.anchor.source_license,
        "retrievedDate": config.anchor.retrieved_date,
    }
    coordinate_operation = {
        "name": operation_info.name,
        "authorityCodes": ["EPSG:1314", "EPSG:19916"],
        "definition": operation_info.definition,
        "reportedAccuracyM": operation_info.reported_accuracy_m,
        "selectedUsesGrids": operation_info.uses_grids,
        "bestAvailable": operation_info.best_available,
        "preferredMissingGridNames": preferred_missing_grid_names,
        "missingPreferredGridCaveat": (
            "PROJ_NETWORK=OFF; the preferred higher-accuracy operation is unavailable because "
            + ", ".join(preferred_missing_grid_names)
            + "; the pinned non-ballpark EPSG:1314 + EPSG:19916 operation is recorded above."
        ),
    }
    manifest = {
        "formatVersion": 1,
        "id": config.id,
        "name": config.name,
        "worldType": "real",
        "sourceCrs": "EPSG:27700",
        "axisConvention": "+X east, +Y up, -Z north",
        "origin": {
            "eastingM": config.center_bng_m[0],
            "northingM": config.center_bng_m[1],
            "elevationM": grid.origin_elevation_m,
        },
        "extentM": {"width": east - west, "depth": north - south},
        "heightfield": {
            "path": "heightfield.f32",
            "columns": columns,
            "rows": rows,
            "spacingM": OUTPUT_SPACING_M,
            "rowOrder": "north-to-south",
            "byteOrder": "little-endian",
            "encoding": "float32",
            "valueMeaning": "world Y in metres relative to origin elevation",
            "sha256": hashlib.sha256(binary).hexdigest(),
            "byteLength": len(binary),
        },
        "provenance": {
            "kind": "real",
            "generator": TERRAIN_GENERATOR,
            "generatorVersion": TERRAIN_GENERATOR_VERSION,
            "publisher": "Environment Agency",
            "product": EA_PRODUCT,
            "licence": "Open Government Licence v3.0",
            "attribution": EA_ATTRIBUTION,
            "verticalReference": VERTICAL_REFERENCE,
            "licenceUrl": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
            "catalogueUrl": catalogue_url,
            "productSurveyPeriod": product_survey_period,
            "xmlCopyrightConflict": xml_copyright_conflict,
            "coordinateOperation": coordinate_operation,
            "sources": sources,
            "selectionStatus": config.selection_status,
            "coverageStatus": config.coverage_status,
            "resampling": "bilinear interpolation between source 1 m area-pixel centers",
            "fillPolicy": "none; every positive-weight source contributor must be valid",
            "qa": {
                "reportPath": (
                    "qa.json"
                    if config.profile == "current_2km"
                    else "../docs/milestones/artifacts/TVW-008-qa.json"
                ),
                "sampling": qa["sampling"],
                "maximumObservedResamplingErrorM": qa["errorBudgets"][
                    "maximumObservedResamplingErrorM"
                ],
                "maximumObservedFloat32QuantizationErrorM": qa["errorBudgets"][
                    "maximumObservedFloat32QuantizationErrorM"
                ],
            },
        },
        "aoi": {
            "crs": "EPSG:27700",
            "boundsM": [west, south, east, north],
            "centerBngM": [config.center_bng_m[0], config.center_bng_m[1]],
            "widthM": east - west,
            "heightM": north - south,
            "anchorWgs84": anchor_wgs84,
            "boundaryWgs84": boundary_wgs84,
            "selectionStatus": config.selection_status,
            "coverageStatus": config.coverage_status,
        },
    }
    # Older manifests without a profile remain the accepted historical 1 km
    # package. New 2 km packages carry an explicit profile identity.
    if config.profile == "current_2km":
        manifest["sceneProfile"] = "current_2km"
    return manifest


def _render_preview(
    grid: ResampledGrid,
    output_path: Path,
    qa: dict[str, Any],
) -> bytes:
    west, south, east, north = grid.bounds_m
    values = grid.elevations_m
    minimum = float(np.min(values))
    maximum = float(np.max(values))
    norm = (
        Normalize(vmin=minimum, vmax=maximum)
        if minimum < maximum
        else Normalize(vmin=minimum - 0.5, vmax=maximum + 0.5)
    )
    figure, axis = plt.subplots(figsize=(10, 8))
    figure.subplots_adjust(left=0.12, right=0.86, top=0.88, bottom=0.2)
    figure.patch.set_facecolor("white")
    contour = axis.contourf(
        grid.eastings_m,
        grid.northings_m,
        values,
        levels=np.linspace(minimum, maximum, 32) if minimum < maximum else 2,
        cmap="terrain",
        norm=norm,
        extend="both",
    )
    axis.add_patch(
        Rectangle(
            (west, south),
            east - west,
            north - south,
            fill=False,
            edgecolor="#d62728",
            linewidth=2,
            zorder=4,
            label="1 km candidate AOI",
        )
    )
    axis.plot(
        (west + east) / 2,
        (south + north) / 2,
        marker="+",
        color="#111111",
        markersize=12,
        markeredgewidth=2,
        zorder=5,
        label="Configured postcode centroid",
    )
    axis.set_xlabel("Easting (m, EPSG:27700)")
    axis.set_ylabel("Northing (m, EPSG:27700; north up)")
    axis.set_xlim(west, east)
    axis.set_ylim(south, north)
    axis.set_aspect("equal")
    axis.grid(color="white", linewidth=0.35, alpha=0.5)
    axis.legend(loc="lower left", framealpha=0.9, fontsize=8)
    axis.set_title(
        f"Environment Agency {EA_PRODUCT}\n"
        f"{grid.elevations_m.shape[1]} × {grid.elevations_m.shape[0]} vertices · "
        f"{OUTPUT_SPACING_M:g} m · measured source elevations "
        f"{minimum:.2f}–{maximum:.2f} m"
    )
    figure.colorbar(
        contour,
        ax=axis,
        fraction=0.045,
        pad=0.04,
        label="Source elevation (m; OS Newlyn orthometric reference)",
    )

    scale_y = south + 55
    scale_x = east - 300
    bar = axis.plot(
        [scale_x, scale_x + 250], [scale_y, scale_y], color="black", linewidth=3, zorder=6
    )[0]
    bar.set_path_effects(
        [patheffects.Stroke(linewidth=6, foreground="white"), patheffects.Normal()]
    )
    axis.plot(
        [scale_x, scale_x], [scale_y - 15, scale_y + 15], color="black", linewidth=2.5, zorder=7
    )
    axis.plot(
        [scale_x + 250, scale_x + 250],
        [scale_y - 15, scale_y + 15],
        color="black",
        linewidth=2.5,
        zorder=7,
    )
    axis.text(
        scale_x + 125,
        scale_y + 17,
        "250 m",
        ha="center",
        va="bottom",
        color="black",
        fontsize=8,
        zorder=5,
        bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none", "pad": 1},
    )
    figure.text(
        0.01,
        0.075,
        f"Bilinear source elevations {minimum:.3f}–{maximum:.3f} m; "
        f"centre origin {grid.origin_elevation_m:.3f} m. "
        f"{len(qa['probes'])} fixed QA probes passed; no filling or extrapolation.",
        ha="left",
        va="bottom",
        fontsize=8,
        color="#202124",
    )
    figure.text(0.01, 0.03, EA_ATTRIBUTION, ha="left", va="bottom", fontsize=7, color="#30343b")
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        figure.savefig(
            temporary,
            dpi=160,
            format="png",
            metadata={"Software": "TVW-008 deterministic terrain preview"},
            facecolor=figure.get_facecolor(),
        )
        return temporary.read_bytes()
    finally:
        plt.close(figure)
        temporary.unlink(missing_ok=True)


def _json_bytes(value: dict[str, Any]) -> bytes:
    try:
        return (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode(
            "utf-8"
        )
    except (TypeError, ValueError) as exc:
        raise TerrainExportError(f"cannot serialize deterministic terrain metadata: {exc}") from exc


def _stage_file(path: Path, content: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{path.name}.", suffix=".stage", dir=path.parent, delete=False
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            return Path(handle.name)
    except OSError as exc:
        raise TerrainExportError(f"cannot stage output '{path}': {exc}") from exc


def _publish_transaction(artifacts: list[tuple[Path, bytes]], manifest_path: Path) -> None:
    """Stage all outputs, replace manifest last, and restore prior files on error."""
    staged: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}
    replaced: list[Path] = []
    try:
        for target, content in artifacts:
            staged[target] = _stage_file(target, content)
        ordered_targets = [target for target, _content in artifacts if target != manifest_path]
        ordered_targets.append(manifest_path)
        for target in ordered_targets:
            if target.exists():
                with tempfile.NamedTemporaryFile(
                    prefix=f".{target.name}.", suffix=".backup", dir=target.parent, delete=False
                ) as handle:
                    backup = Path(handle.name)
                backup.unlink(missing_ok=True)
                os.replace(target, backup)
                backups[target] = backup
            os.replace(staged[target], target)
            replaced.append(target)
    except Exception:
        for target in reversed(replaced):
            target.unlink(missing_ok=True)
            backup = backups.get(target)
            if backup is not None and backup.exists():
                os.replace(backup, target)
        for target, backup in backups.items():
            if backup.exists() and not target.exists():
                os.replace(backup, target)
        raise
    finally:
        for temp_path in staged.values():
            temp_path.unlink(missing_ok=True)
        for backup in backups.values():
            backup.unlink(missing_ok=True)


def build_terrain_package(
    config: AoiConfig,
    raster_paths: list[Path],
    source_manifest: dict[str, Any],
    verified_sources: list[dict[str, Any]],
    package_dir: Path,
    qa_path: Path,
    preview_path: Path,
) -> dict[str, Any]:
    """Generate and atomically publish a profile-specific real-data terrain package."""
    expected_size_m = 1000.0 if config.profile == "historical_1km" else 2000.0
    if config.width_m != expected_size_m or config.height_m != expected_size_m:
        raise TerrainExportError(
            f"profile '{config.profile}' requires exactly "
            f"{expected_size_m:,.0f} m × {expected_size_m:,.0f} m"
        )
    if (
        config.selection_status != "selected_pending_coverage"
        or config.coverage_status != "not_checked"
    ):
        raise TerrainExportError("AOI must remain selected_pending_coverage / not_checked")
    west, south, east, north = config.bbox_m
    center_e, center_n = config.center_bng_m
    if not (
        math.isclose((west + east) / 2, center_e, abs_tol=1e-7)
        and math.isclose((south + north) / 2, center_n, abs_tol=1e-7)
    ):
        raise TerrainExportError("AOI bounds are not centered on the configured postcode centroid")

    columns = int(round(config.width_m / OUTPUT_SPACING_M)) + 1
    rows = int(round(config.height_m / OUTPUT_SPACING_M)) + 1
    grid = resample_vertices(
        raster_paths,
        config.bbox_m,
        columns=columns,
        rows=rows,
        spacing_m=OUTPUT_SPACING_M,
    )
    relative = grid.elevations_m - grid.origin_elevation_m
    if not np.isfinite(relative).all():
        raise TerrainExportError("relative terrain contains non-finite values")
    encoded = np.asarray(relative, dtype="<f4", order="C")
    if encoded.shape != (rows, columns) or encoded.nbytes != rows * columns * 4:
        raise TerrainExportError(
            f"encoded output does not match the required {columns} × {rows} Float32 grid"
        )
    binary = encoded.tobytes(order="C")
    qa = _build_qa(grid, raster_paths, encoded)
    qa["aoiCoverageGate"] = {
        "selectionStatus": config.selection_status,
        "overallCoverageStatus": config.coverage_status,
        "measuredEaDtmCoverageWasRevalidated": True,
        "m2Complete": False,
        "note": (
            "EA DTM support was revalidated for every output contributor; "
            "OSM/OS feature checks remain pending."
        ),
    }
    provenance_sources = _provenance_sources(source_manifest, verified_sources)
    manifest = _manifest(config, grid, binary, qa, provenance_sources, source_manifest)
    preview_bytes = _render_preview(grid, preview_path, qa)
    manifest_bytes = _json_bytes(manifest)
    qa_bytes = _json_bytes(qa)
    manifest_path = package_dir / "manifest.json"
    binary_path = package_dir / "heightfield.f32"
    _publish_transaction(
        [
            (binary_path, binary),
            (qa_path, qa_bytes),
            (preview_path, preview_bytes),
            (manifest_path, manifest_bytes),
        ],
        manifest_path,
    )
    return {
        "manifest": manifest,
        "qa": qa,
        "paths": {
            "package": package_dir.as_posix(),
            "manifest": manifest_path.as_posix(),
            "heightfield": binary_path.as_posix(),
            "qa": qa_path.as_posix(),
            "preview": preview_path.as_posix(),
        },
    }
