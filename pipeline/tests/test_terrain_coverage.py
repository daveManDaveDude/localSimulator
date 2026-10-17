"""Coverage calculations use generated rasters only and never fetch data."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from torquay_pipeline.config import AoiConfig, load_aoi_config
from torquay_pipeline.terrain_coverage import (
    TerrainCoverageError,
    analyze_coverage,
    atomic_write_json,
)
from torquay_pipeline.terrain_preview import write_terrain_preview
from torquay_pipeline.terrain_sources import TerrainSourceError

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "aoi.torquay.json"


def small_config(
    width: int = 2,
    height: int = 2,
    west: float = 0.25,
    south: float = 0.5,
) -> AoiConfig:
    base = load_aoi_config(CONFIG)
    east = west + width
    north = south + height
    return replace(
        base,
        width_m=float(width),
        height_m=float(height),
        center_bng_m=((west + east) / 2, (south + north) / 2),
        bbox_m=(west, south, east, north),
    )


def write_raster(
    path: Path,
    values: np.ndarray,
    *,
    west: float = 0,
    north: float = 3,
    crs: str | None = "EPSG:27700",
    transform: Affine | None = None,
    nodata: float | None = None,
    valid_mask: np.ndarray | None = None,
    area_or_point: str | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    height, width = values.shape
    profile = {
        "driver": "GTiff",
        "width": width,
        "height": height,
        "count": 1,
        "dtype": "float32",
        "transform": transform or Affine(1, 0, west, 0, -1, north),
    }
    if crs is not None:
        profile["crs"] = crs
    if nodata is not None:
        profile["nodata"] = nodata
    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(np.asarray(values, dtype=np.float32), 1)
        if valid_mask is not None:
            dataset.write_mask(np.asarray(valid_mask, dtype=np.uint8) * 255)
        if area_or_point is not None:
            dataset.update_tags(AREA_OR_POINT=area_or_point)
    return path


def test_samples_aoi_cell_centers_without_interpolation_and_reports_center(
    tmp_path: Path,
) -> None:
    values = np.arange(16, dtype=np.float32).reshape(4, 4)
    path = write_raster(tmp_path / "sample.tif", values)

    result = analyze_coverage(small_config(), [path])

    assert result.elevations_m.tolist() == [[4.0, 5.0], [8.0, 9.0]]
    assert result.report["coverage"]["valid_cells"] == 4
    assert result.report["coverage"]["missing_cells"] == 0
    assert result.report["elevation_m"]["minimum"] == 4.0
    assert result.report["elevation_m"]["maximum"] == 9.0
    assert result.report["elevation_m"]["center"]["value_m"] == 5.0
    assert result.report["analysis"]["ea_dtm_threshold_result"] == "pass"
    assert result.report["analysis"]["overall_aoi_coverage_status"] == "not_checked"


def test_finite_zero_and_negative_elevations_are_valid(tmp_path: Path) -> None:
    values = np.zeros((4, 4), dtype=np.float32)
    values[1, 0] = -3.25
    values[2, 0] = 2.5
    values[2, 1] = 4.0
    path = write_raster(tmp_path / "signed.tif", values)

    result = analyze_coverage(small_config(), [path])

    assert result.elevations_m.tolist() == [[-3.25, 0.0], [2.5, 4.0]]
    assert result.report["coverage"]["valid_cells"] == 4
    assert result.report["elevation_m"]["minimum"] == -3.25
    assert result.report["elevation_m"]["maximum"] == 4.0


def test_adjacent_tiles_cover_grid_and_are_order_independent(tmp_path: Path) -> None:
    config = small_config(width=4)
    left = write_raster(tmp_path / "left.tif", np.asarray([[1, 2], [3, 4], [5, 6], [7, 8]]), west=0)
    right = write_raster(
        tmp_path / "right.tif", np.asarray([[11, 12], [13, 14], [15, 16], [17, 18]]), west=2
    )

    first = analyze_coverage(config, [left, right])
    reversed_input = analyze_coverage(config, [right, left])

    assert first.elevations_m.tolist() == [[3, 4, 13, 14], [5, 6, 15, 16]]
    assert reversed_input.elevations_m.tolist() == first.elevations_m.tolist()
    assert first.report["coverage"]["valid_cells"] == 8
    assert first.report["coverage"]["uncovered_cells"] == 0


def test_uncovered_and_nodata_counts_are_separate(tmp_path: Path) -> None:
    values = np.zeros((4, 4), dtype=np.float32)
    values[1, 0] = -999
    values[2, 1] = np.nan
    path = write_raster(tmp_path / "part.tif", values, nodata=-999)

    result = analyze_coverage(small_config(), [path])
    coverage = result.report["coverage"]

    assert coverage["valid_cells"] == 2
    assert coverage["masked_or_nodata_cells"] == 1
    assert coverage["nonfinite_only_cells"] == 1
    assert coverage["uncovered_cells"] == 0
    assert coverage["missing_cells"] == 2
    assert result.report["analysis"]["ea_dtm_threshold_result"] == "fail"


def test_explicit_raster_mask_is_counted_without_filling(tmp_path: Path) -> None:
    values = np.zeros((4, 4), dtype=np.float32)
    valid_mask = np.ones((4, 4), dtype=bool)
    valid_mask[1, 1] = False
    path = write_raster(tmp_path / "mask.tif", values, valid_mask=valid_mask)

    result = analyze_coverage(small_config(), [path])

    assert result.report["coverage"]["masked_or_nodata_cells"] == 1
    assert result.report["coverage"]["valid_cells"] == 3
    assert np.isnan(result.elevations_m[0, 1])


def test_positive_and_negative_infinity_are_invalid_samples(tmp_path: Path) -> None:
    values = np.zeros((4, 4), dtype=np.float32)
    values[1, 0] = np.inf
    values[1, 1] = -np.inf
    values[2, 1] = 2.0
    path = write_raster(tmp_path / "infinities.tif", values)

    result = analyze_coverage(small_config(), [path])

    assert result.report["coverage"]["valid_cells"] == 2
    assert result.report["coverage"]["nonfinite_only_cells"] == 2
    assert result.report["coverage"]["missing_cells"] == 2


def test_uncovered_cells_are_counted_and_preview_keeps_them_visible(tmp_path: Path) -> None:
    path = write_raster(tmp_path / "strip.tif", np.ones((4, 1), dtype=np.float32))
    result = analyze_coverage(small_config(), [path])
    coverage = result.report["coverage"]
    preview_path = tmp_path / "preview.png"

    preview = write_terrain_preview(result, preview_path)

    assert coverage["valid_cells"] == 2
    assert coverage["uncovered_cells"] == 2
    assert coverage["missing_area_m2"] == 2
    assert result.report["analysis"]["ea_dtm_threshold_result"] == "fail"
    assert preview["missing_cells_distinct"] is True
    assert preview_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.parametrize(("missing", "expected_pass"), [(1, True), (2, False)])
def test_missing_threshold_accepts_exactly_one_percent(
    tmp_path: Path, missing: int, expected_pass: bool
) -> None:
    values = np.zeros((10, 10), dtype=np.float32)
    values.flat[:missing] = -999
    path = write_raster(
        tmp_path / "threshold.tif",
        values,
        west=0,
        north=10,
        nodata=-999,
    )
    config = small_config(width=10, height=10, west=0, south=0)

    result = analyze_coverage(config, [path], missing_threshold=0.01)

    assert result.report["coverage"]["missing_cells"] == missing
    assert result.report["coverage"]["threshold_pass"] is expected_pass
    assert result.report["analysis"]["ea_dtm_threshold_result"] == (
        "pass" if expected_pass else "fail"
    )


def test_overlapping_tiles_are_counted_once_with_stable_source_priority(tmp_path: Path) -> None:
    first = write_raster(tmp_path / "a-first.tif", np.ones((4, 4), dtype=np.float32))
    second = write_raster(tmp_path / "b-second.tif", np.full((4, 4), 2, dtype=np.float32))

    result = analyze_coverage(small_config(), [second, first])

    assert result.report["coverage"]["valid_cells"] == 4
    assert result.report["coverage"]["overlap_cells_counted_once"] == 4
    assert result.report["coverage"]["overlapping_source_value_conflicts"] == 4
    assert result.elevations_m.tolist() == [[1, 1], [1, 1]]


@pytest.mark.parametrize(
    ("crs", "transform", "match"),
    [
        (None, Affine(1, 0, 0, 0, -1, 3), "missing a CRS"),
        ("EPSG:4326", Affine(1, 0, 0, 0, -1, 3), "expected EPSG:27700"),
        ("EPSG:27700", Affine(1, 0.2, 0, 0, -1, 3), "unsupported transform/resolution"),
    ],
)
def test_unsupported_raster_metadata_is_rejected(
    tmp_path: Path, crs: str | None, transform: Affine, match: str
) -> None:
    path = write_raster(
        tmp_path / "unsupported.tif",
        np.ones((4, 4), dtype=np.float32),
        crs=crs,
        transform=transform,
    )

    with pytest.raises(TerrainSourceError, match=match):
        analyze_coverage(small_config(), [path])


def test_missing_source_and_invalid_threshold_are_actionable(tmp_path: Path) -> None:
    with pytest.raises(TerrainCoverageError, match="no source rasters"):
        analyze_coverage(small_config(), [])
    with pytest.raises(TerrainCoverageError, match="between 0 and 1"):
        analyze_coverage(small_config(), [tmp_path / "absent.tif"], 2)


def test_point_registered_raster_is_rejected_for_cell_center_analysis(tmp_path: Path) -> None:
    path = write_raster(
        tmp_path / "point.tif",
        np.ones((4, 4), dtype=np.float32),
        area_or_point="Point",
    )

    with pytest.raises(TerrainSourceError, match="pixel registration"):
        analyze_coverage(small_config(), [path])


def test_report_writer_is_deterministic_and_preserves_previous_file_on_error(
    tmp_path: Path,
) -> None:
    path = write_raster(tmp_path / "stable.tif", np.ones((4, 4), dtype=np.float32))
    report = analyze_coverage(small_config(), [path]).report
    output = tmp_path / "coverage.json"

    atomic_write_json(output, report)
    original = output.read_bytes()
    atomic_write_json(output, report)

    assert output.read_bytes() == original
    with pytest.raises(ValueError):
        atomic_write_json(output, {"bad": float("nan")})
    assert output.read_bytes() == original
