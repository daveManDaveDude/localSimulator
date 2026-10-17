"""Measure EA DTM support on a deterministic 1 m grid aligned to the AOI."""

from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.windows import Window

from .config import AoiConfig
from .terrain_sources import inspect_raster

DEFAULT_MISSING_THRESHOLD = 0.01


class TerrainCoverageError(ValueError):
    """Raised when raster sources cannot be sampled on the requested AOI grid."""


@dataclass(frozen=True)
class CoverageResult:
    """Measured raster coverage and values sampled at AOI analysis-cell centers."""

    report: dict[str, Any]
    elevations_m: np.ndarray
    valid_mask: np.ndarray


def _source_valid(
    values: np.ndarray, mask: np.ndarray, nodata: float | None
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    finite = np.isfinite(values)
    nodata_values = np.zeros(values.shape, dtype=bool)
    if nodata is not None:
        nodata_values = np.isnan(values) if math.isnan(nodata) else values == nodata
    masked = (mask == 0) | nodata_values
    valid = (mask > 0) & finite & ~nodata_values
    nonfinite = (mask > 0) & ~finite & ~nodata_values
    return valid, masked, nonfinite


def _source_extent(dataset: rasterio.io.DatasetReader) -> tuple[float, float, float, float]:
    if dataset.crs is None or dataset.crs != CRS.from_epsg(27700):
        raise TerrainCoverageError(f"raster '{Path(dataset.name).name}' must use EPSG:27700")
    transform = dataset.transform
    if not (
        transform.a == 1.0
        and transform.e == -1.0
        and transform.b == 0.0
        and transform.d == 0.0
        and transform.c == round(transform.c)
        and transform.f == round(transform.f)
    ):
        raise TerrainCoverageError(
            f"raster '{Path(dataset.name).name}' must use the exact supported affine "
            "(a=1, b=0, d=0, e=-1) with integer-aligned origin"
        )
    bounds = dataset.bounds
    return bounds.left, bounds.bottom, bounds.right, bounds.top


def analyze_coverage(
    config: AoiConfig,
    raster_paths: list[Path],
    missing_threshold: float = DEFAULT_MISSING_THRESHOLD,
) -> CoverageResult:
    """Sample source pixels at AOI-cell centers, without interpolation or filling.

    Where source rasters overlap, filenames are sorted and the first valid sample
    wins. Coverage is counted once per AOI cell. This rule makes results stable
    when callers discover rasters in a different order.
    """
    if not raster_paths:
        raise TerrainCoverageError("no source rasters were provided")
    if not math.isfinite(missing_threshold) or not 0 <= missing_threshold <= 1:
        raise TerrainCoverageError("missing threshold must be between 0 and 1")
    columns = int(config.width_m)
    rows = int(config.height_m)
    if columns <= 0 or rows <= 0 or columns != config.width_m or rows != config.height_m:
        raise TerrainCoverageError("AOI dimensions must be positive whole metres for a 1 m grid")

    west, south, east, north = config.bbox_m
    if not all(math.isfinite(value) for value in (west, south, east, north)):
        raise TerrainCoverageError("AOI bounds must be finite EPSG:27700 coordinates")
    if not (west < east and south < north):
        raise TerrainCoverageError("AOI bounds must be ordered west < east and south < north")
    if not (
        math.isclose(east - west, columns, rel_tol=0, abs_tol=1e-7)
        and math.isclose(north - south, rows, rel_tol=0, abs_tol=1e-7)
    ):
        raise TerrainCoverageError("AOI bounds do not match the configured whole-metre dimensions")

    x_centers = west + (np.arange(columns, dtype=np.float64) + 0.5)
    y_centers = north - (np.arange(rows, dtype=np.float64) + 0.5)
    elevations = np.full((rows, columns), np.nan, dtype=np.float64)
    covered = np.zeros((rows, columns), dtype=bool)
    valid = np.zeros((rows, columns), dtype=bool)
    nodata_seen = np.zeros((rows, columns), dtype=bool)
    nonfinite_seen = np.zeros((rows, columns), dtype=bool)
    hit_count = np.zeros((rows, columns), dtype=np.uint16)
    conflicting_overlap = np.zeros((rows, columns), dtype=bool)
    source_records: list[dict[str, Any]] = []

    ordered_paths = sorted(
        (path.resolve() for path in raster_paths), key=lambda item: item.as_posix().casefold()
    )
    for path in ordered_paths:
        metadata, sidecar = inspect_raster(path)
        try:
            with rasterio.open(path) as dataset:
                left, _bottom, _right, top = _source_extent(dataset)
                col_indexes = np.floor(x_centers - left).astype(np.int64)
                row_indexes = np.floor(top - y_centers).astype(np.int64)
                valid_cols = np.flatnonzero((col_indexes >= 0) & (col_indexes < dataset.width))
                valid_rows = np.flatnonzero((row_indexes >= 0) & (row_indexes < dataset.height))
                if valid_cols.size == 0 or valid_rows.size == 0:
                    source_records.append(
                        {
                            "filename": path.name,
                            "sha256": metadata.sha256,
                            "aoi_cells_sampled": 0,
                            "metadata_sidecar": _sidecar_summary(sidecar),
                        }
                    )
                    continue

                # North-up, 1 m integer-aligned rasters have contiguous row/column
                # indexes over the AOI intersection, so read only that rectangle.
                col_start, col_end = int(valid_cols[0]), int(valid_cols[-1]) + 1
                row_start, row_end = int(valid_rows[0]), int(valid_rows[-1]) + 1
                window = Window(
                    int(col_indexes[col_start]),
                    int(row_indexes[row_start]),
                    col_end - col_start,
                    row_end - row_start,
                )
                samples = dataset.read(1, window=window)
                masks = dataset.read_masks(1, window=window)
                source_valid, source_nodata, source_nonfinite = _source_valid(
                    samples, masks, dataset.nodata
                )

                row_slice = slice(row_start, row_end)
                col_slice = slice(col_start, col_end)
                target_valid = valid[row_slice, col_slice]
                target_values = elevations[row_slice, col_slice]
                hit_count[row_slice, col_slice] += 1
                covered[row_slice, col_slice] = True
                nodata_seen[row_slice, col_slice] |= source_nodata
                nonfinite_seen[row_slice, col_slice] |= source_nonfinite

                both_valid = target_valid & source_valid
                if np.any(both_valid):
                    conflicting_overlap[row_slice, col_slice] |= both_valid & (
                        np.abs(target_values - samples) > 1e-6
                    )
                take_values = source_valid & ~target_valid
                target_values[take_values] = samples[take_values].astype(np.float64)
                target_valid[:] |= source_valid
                sampled_count = (row_end - row_start) * (col_end - col_start)
                source_records.append(
                    {
                        "filename": path.name,
                        "sha256": metadata.sha256,
                        "aoi_cells_sampled": sampled_count,
                        "metadata_sidecar": _sidecar_summary(sidecar),
                    }
                )
        except TerrainCoverageError:
            raise
        except Exception as exc:
            raise TerrainCoverageError(f"cannot sample raster '{path}': {exc}") from exc

    total = rows * columns
    valid_count = int(np.count_nonzero(valid))
    uncovered_mask = ~covered
    masked_only = covered & ~valid & nodata_seen
    nonfinite_only = covered & ~valid & ~nodata_seen & nonfinite_seen
    other_invalid = covered & ~valid & ~nodata_seen & ~nonfinite_seen
    missing_count = total - valid_count
    missing_fraction = missing_count / total
    elevations[~valid] = np.nan
    finite_values = elevations[valid]

    center_e, center_n = config.center_bng_m
    center_elevation: float | None = None
    center_source: str | None = None
    for path in ordered_paths:
        try:
            with rasterio.open(path) as dataset:
                left, bottom, right, top = _source_extent(dataset)
                if not (left <= center_e < right and bottom < center_n <= top):
                    continue
                col = int(math.floor(center_e - left))
                row = int(math.floor(top - center_n))
                sample = dataset.read(1, window=Window(col, row, 1, 1))[0, 0]
                mask = dataset.read_masks(1, window=Window(col, row, 1, 1))[0, 0]
                sample_valid, _sample_nodata, _sample_nonfinite = _source_valid(
                    np.asarray([[sample]]), np.asarray([[mask]]), dataset.nodata
                )
                if bool(sample_valid[0, 0]):
                    center_elevation = float(sample)
                    center_source = path.name
                    break
        except Exception as exc:
            raise TerrainCoverageError(
                f"cannot sample AOI center from raster '{path}': {exc}"
            ) from exc

    overlaps = hit_count > 1
    passed = missing_fraction <= missing_threshold
    report: dict[str, Any] = {
        "format_version": 1,
        "analysis": {
            "measurement_status": "completed",
            "ea_dtm_threshold_result": "pass" if passed else "fail",
            "ea_dtm_missing_threshold_fraction": missing_threshold,
            "selection_status": config.selection_status,
            "overall_aoi_coverage_status": config.coverage_status,
            "overall_status_note": (
                "The EA DTM check is independent of the broader AOI gate; "
                "OSM/OS building and road coverage remains unchecked."
            ),
        },
        "aoi": {
            "id": config.id,
            "crs": config.crs,
            "bounds_m": [west, south, east, north],
            "width_m": config.width_m,
            "height_m": config.height_m,
        },
        "analysis_grid": {
            "resolution_m": 1,
            "columns": columns,
            "rows": rows,
            "cell_count": total,
            "cell_area_m2": 1,
            "denominator_area_m2": total,
            "alignment": "AOI bounds; 1 m square cells sampled at their centers",
            "sampling": "containing source pixel; no interpolation, extrapolation, or filling",
            "boundary_rule": (
                "AOI cell center must fall within a source pixel footprint; "
                "east/south edges are exclusive"
            ),
        },
        "coverage": {
            "valid_cells": valid_count,
            "uncovered_cells": int(np.count_nonzero(uncovered_mask)),
            "masked_or_nodata_cells": int(np.count_nonzero(masked_only)),
            "nonfinite_only_cells": int(np.count_nonzero(nonfinite_only)),
            "other_invalid_cells": int(np.count_nonzero(other_invalid)),
            "missing_cells": missing_count,
            "missing_area_m2": missing_count,
            "missing_fraction": missing_fraction,
            "overlap_cells_counted_once": int(np.count_nonzero(overlaps)),
            "overlapping_source_value_conflicts": int(np.count_nonzero(conflicting_overlap)),
            "threshold_pass": passed,
        },
        "elevation_m": {
            "minimum": float(np.min(finite_values)) if finite_values.size else None,
            "maximum": float(np.max(finite_values)) if finite_values.size else None,
            "center": {
                "easting_m": center_e,
                "northing_m": center_n,
                "value_m": center_elevation,
                "source_filename": center_source,
                "method": "source pixel containing exact configured center; no interpolation",
            },
        },
        "sources": source_records,
    }
    return CoverageResult(report=report, elevations_m=elevations, valid_mask=valid)


def _sidecar_summary(sidecar: dict[str, Any] | None) -> dict[str, Any] | None:
    if sidecar is None:
        return None
    return {
        field: sidecar.get(field)
        for field in ("filename", "size_bytes", "sha256", "creation_date", "metadata_date")
    }


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    """Write deterministic JSON with a same-directory atomic replace."""
    content = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode(
        "utf-8"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
