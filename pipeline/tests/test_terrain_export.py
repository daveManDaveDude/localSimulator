"""Terrain exporter tests use only small test-generated GeoTIFFs."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from torquay_pipeline.config import AoiConfig, load_aoi_config
from torquay_pipeline.terrain_export import (
    TerrainExportError,
    _build_qa,
    _load_wgs84_aoi_boundary,
    _publish_transaction,
    resample_vertices,
)

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "aoi.torquay-1km.json"


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


def test_qa_derives_northing_seam_probes_from_adjacent_source_tiles(tmp_path: Path) -> None:
    west = 290000
    north_tile = write_raster(
        tmp_path / "north-large.tif", np.full((3, 6), 10, dtype=np.float32), west=west, north=65003
    )
    south_tile = write_raster(
        tmp_path / "south-large.tif", np.full((3, 6), 20, dtype=np.float32), west=west, north=65000
    )
    grid = resample_vertices(
        [south_tile, north_tile],
        (290001.0, 64998.0, 290005.0, 65002.0),
        columns=5,
        rows=5,
        spacing_m=1,
    )

    qa = _build_qa(grid, [south_tile, north_tile], grid.elevations_m - grid.origin_elevation_m)

    assert {probe["label"] for probe in qa["probes"]} >= {
        "source_seam_1_north",
        "source_seam_1_south",
    }
    assert qa["status"] == "pass"


def test_qa_for_a_single_tile_away_from_known_seam_has_no_seam_probes(tmp_path: Path) -> None:
    raster = write_raster(
        tmp_path / "single-tile-away-from-seam.tif",
        np.full((6, 6), 5, dtype=np.float32),
        west=0,
        north=2002,
    )
    grid = resample_vertices(
        [raster],
        (1.0, 1997.0, 5.0, 2001.0),
        columns=5,
        rows=5,
        spacing_m=1,
    )

    qa = _build_qa(grid, [raster], grid.elevations_m - grid.origin_elevation_m)

    labels = {probe["label"] for probe in qa["probes"]}
    assert qa["status"] == "pass"
    assert not any("seam" in label for label in labels)


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


def test_real_manifest_boundary_uses_generated_attributable_geojson_ring() -> None:
    config = load_aoi_config(CONFIG_PATH)
    geojson_path = (
        ROOT / "docs" / "milestones" / "artifacts" / "AOI-1km-selection" / "aoi-selection.geojson"
    )
    geojson = json.loads(geojson_path.read_text(encoding="utf-8"))
    aoi_feature = next(
        feature for feature in geojson["features"] if feature["id"] == f"{config.id}-aoi"
    )

    boundary = _load_wgs84_aoi_boundary(config, geojson_path)

    assert boundary["crs"] == "EPSG:4326"
    assert boundary["coordinateOrder"] == "longitude-latitude"
    assert boundary["geometryType"] == "Polygon"
    assert boundary["ring"] == aoi_feature["geometry"]["coordinates"][0]
    assert boundary["ring"][0] == boundary["ring"][-1]


def test_real_manifest_boundary_rejects_stale_geojson_ring(tmp_path: Path) -> None:
    config = load_aoi_config(CONFIG_PATH)
    source = json.loads(
        (
            ROOT
            / "docs"
            / "milestones"
            / "artifacts"
            / "AOI-1km-selection"
            / "aoi-selection.geojson"
        ).read_text(encoding="utf-8")
    )
    aoi_feature = next(
        feature for feature in source["features"] if feature["id"] == f"{config.id}-aoi"
    )
    aoi_feature["geometry"]["coordinates"][0][1][0] += 0.001
    stale_geojson = tmp_path / "stale-aoi-selection.geojson"
    stale_geojson.write_text(json.dumps(source), encoding="utf-8")

    with pytest.raises(TerrainExportError, match="does not match the configured AOI"):
        _load_wgs84_aoi_boundary(config, stale_geojson)
