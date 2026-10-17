"""Terrain exporter tests use only small test-generated GeoTIFFs."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from torquay_pipeline.config import AoiConfig, load_aoi_config
from torquay_pipeline.terrain_export import (
    TerrainExportError,
    _publish_transaction,
    resample_vertices,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "aoi.torquay.json"


def small_config() -> AoiConfig:
    base = load_aoi_config(CONFIG_PATH)
    return replace(
        base,
        width_m=4.0,
        height_m=4.0,
        center_bng_m=(2.0, 2.0),
        bbox_m=(0.0, 0.0, 4.0, 4.0),
    )


def write_raster(
    path: Path,
    values: np.ndarray,
    *,
    west: int = 0,
    north: int = 4,
    nodata: float | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    height, width = values.shape
    profile: dict[str, object] = {
        "driver": "GTiff",
        "width": width,
        "height": height,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:27700",
        "transform": Affine(1, 0, west, 0, -1, north),
    }
    if nodata is not None:
        profile["nodata"] = nodata
    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(np.asarray(values, dtype=np.float32), 1)
    return path


def make_plane_tile(path: Path, *, west: int = 0, north: int = 4, height: int = 4) -> Path:
    rows = np.arange(height, dtype=np.float64)
    columns = np.arange(4, dtype=np.float64)
    northings = north - rows[:, None] - 0.5
    eastings = west + columns[None, :] + 0.5
    return write_raster(path, 2 * eastings + 3 * northings, west=west, north=north)


def test_bilinear_vertex_grid_interpolates_plane_and_includes_edges(tmp_path: Path) -> None:
    raster = make_plane_tile(tmp_path / "plane.tif")

    result = resample_vertices([raster], (1.0, 1.0, 3.0, 3.0), columns=3, rows=3, spacing_m=1)

    expected_northings = np.asarray([3.0, 2.0, 1.0])[:, None]
    expected_eastings = np.asarray([1.0, 2.0, 3.0])[None, :]
    np.testing.assert_allclose(result.elevations_m, 2 * expected_eastings + 3 * expected_northings)
    assert result.origin_elevation_m == pytest.approx(10.0)
    assert result.elevations_m.shape == (3, 3)


def test_bilinear_sampling_crosses_the_northing_65000_tile_seam(tmp_path: Path) -> None:
    west = 290000
    north_tile = make_plane_tile(tmp_path / "north.tif", west=west, north=65002, height=2)
    south_tile = make_plane_tile(tmp_path / "south.tif", west=west, north=65000, height=2)

    result = resample_vertices(
        [south_tile, north_tile],
        (290001.0, 64999.0, 290003.0, 65001.0),
        columns=3,
        rows=3,
        spacing_m=1,
    )

    expected = (
        2 * np.asarray([290001.0, 290002.0, 290003.0])[None, :]
        + 3 * np.asarray([65001.0, 65000.0, 64999.0])[:, None]
    )
    np.testing.assert_allclose(result.elevations_m, expected, atol=1e-9)


def test_nodata_with_positive_bilinear_weight_fails_without_filling(tmp_path: Path) -> None:
    values = np.full((4, 4), 5.0, dtype=np.float32)
    values[0, 0] = -999
    raster = write_raster(tmp_path / "nodata.tif", values, nodata=-999)

    with pytest.raises(TerrainExportError, match="NoData and uncovered inputs are not filled"):
        resample_vertices([raster], (1.0, 1.0, 3.0, 3.0), columns=3, rows=3, spacing_m=1)


def test_missing_source_support_fails_without_extrapolation(tmp_path: Path) -> None:
    # The source covers only the western half of the requested grid.
    raster = write_raster(tmp_path / "half.tif", np.ones((4, 2), dtype=np.float32))

    with pytest.raises(TerrainExportError, match="cannot bilinearly support"):
        resample_vertices([raster], (1.0, 1.0, 3.0, 3.0), columns=3, rows=3, spacing_m=1)


def test_publisher_transaction_restores_all_previous_outputs_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binary = tmp_path / "package" / "heightfield.f32"
    manifest = tmp_path / "package" / "manifest.json"
    report = tmp_path / "qa.json"
    binary.parent.mkdir()
    binary.write_bytes(b"old binary")
    manifest.write_bytes(b"old manifest")
    report.write_bytes(b"old report")

    import torquay_pipeline.terrain_export as module

    real_replace = module.os.replace
    failed = False

    def fail_once(source: str | Path, destination: str | Path) -> None:
        nonlocal failed
        if Path(destination) == report and not failed:
            failed = True
            raise OSError("injected publication failure")
        real_replace(source, destination)

    monkeypatch.setattr(module.os, "replace", fail_once)
    with pytest.raises(OSError, match="injected publication failure"):
        _publish_transaction(
            [(binary, b"new binary"), (report, b"new report"), (manifest, b"new manifest")],
            manifest,
        )

    assert binary.read_bytes() == b"old binary"
    assert report.read_bytes() == b"old report"
    assert manifest.read_bytes() == b"old manifest"
    assert not list(tmp_path.rglob("*.stage"))
    assert not list(tmp_path.rglob("*.backup"))


def test_fixture_config_remains_pending_and_exactly_one_kilometer() -> None:
    config = load_aoi_config(CONFIG_PATH)
    assert config.selection_status == "selected_pending_coverage"
    assert config.coverage_status == "not_checked"
    assert config.width_m == config.height_m == 1000
    assert config.bbox_m == (
        290608.9018176432,
        64853.48350844931,
        291608.9018176432,
        65853.48350844931,
    )
