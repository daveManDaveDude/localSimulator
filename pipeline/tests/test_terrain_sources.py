"""Source manifest tests use temporary, test-generated GeoTIFFs and ZIPs."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from torquay_pipeline.terrain_sources import (
    TerrainSourceError,
    discover_rasters,
    inspect_raster,
    measure_raster_values,
    sha256_file,
    verify_source_manifest,
)


def make_source(source_dir: Path) -> tuple[Path, Path, dict[str, object]]:
    raster_path = source_dir / "tile" / "test.tif"
    raster_path.parent.mkdir(parents=True)
    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=1,
        dtype="float32",
        crs="EPSG:27700",
        transform=Affine(1, 0, 100, 0, -1, 200),
    ) as dataset:
        dataset.write(np.asarray([[-1.25, 0.0], [2.5, 3.75]], dtype=np.float32), 1)
    sidecar_path = raster_path.with_suffix(raster_path.suffix + ".xml")
    sidecar_path.write_text(
        "<metadata><idAbs>sample</idAbs><useLimit>test</useLimit></metadata>",
        encoding="utf-8",
    )
    archive_path = source_dir / "tile.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(raster_path, arcname="test.tif")
        archive.write(sidecar_path, arcname="test.tif.xml")
    metadata, sidecar = inspect_raster(raster_path)
    assert sidecar is not None
    measured = measure_raster_values(raster_path)
    record: dict[str, object] = {
        "archive_filename": "tile.zip",
        "raster_relative_path": "tile/test.tif",
        "raster_archive_member": "test.tif",
        "metadata_sidecar_relative_path": "tile/test.tif.xml",
        "archive": {
            "size_bytes": archive_path.stat().st_size,
            "sha256": sha256_file(archive_path),
        },
        "archive_members": ["test.tif", "test.tif.xml"],
        "raster": {**metadata.to_dict(), "measured_full_tile": measured},
        "metadata_sidecar": {**sidecar, "archive_member": "test.tif.xml"},
        "download_url": "https://example.invalid/test",
        "download_date": "2026-01-01",
        "tile_name": "test",
    }
    return archive_path, raster_path, record


def test_manifest_verifies_archive_tiff_metadata_and_measured_samples(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    _archive, _raster, record = make_source(source_dir)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"format_version": 1, "sources": [record]}), encoding="utf-8"
    )

    manifest, verified = verify_source_manifest(manifest_path, source_dir)

    assert manifest["format_version"] == 1
    assert verified[0]["archive"]["members"] == ["test.tif", "test.tif.xml"]
    assert verified[0]["archive"]["raster_member"]["member"] == "test.tif"
    assert verified[0]["archive"]["metadata_sidecar_member"]["member"] == "test.tif.xml"
    assert verified[0]["measured_full_tile"] == {
        "total_pixels": 4,
        "masked_pixels": 0,
        "nonfinite_pixels": 0,
        "minimum_m": -1.25,
        "maximum_m": 3.75,
    }


def test_manifest_rejects_extracted_tiff_even_if_manifest_is_refreshed(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    _archive_path, raster_path, record = make_source(source_dir)
    manifest_path = tmp_path / "manifest.json"

    with rasterio.open(raster_path, "r+") as dataset:
        values = dataset.read(1)
        values[0, 0] = 9.25
        dataset.write(values, 1)
    metadata, _sidecar = inspect_raster(raster_path)
    record["raster"] = {
        **metadata.to_dict(),
        "measured_full_tile": measure_raster_values(raster_path),
    }
    manifest_path.write_text(
        json.dumps({"format_version": 1, "sources": [record]}), encoding="utf-8"
    )

    with pytest.raises(TerrainSourceError, match="SHA-256 mismatch between ZIP member 'test.tif'"):
        verify_source_manifest(manifest_path, source_dir)


@pytest.mark.parametrize(
    ("replacement", "message"),
    [(b"simple", "SHA-256 mismatch"), (b"sample plus", "byte length mismatch")],
)
def test_manifest_rejects_extracted_xml_that_differs_from_zip(
    tmp_path: Path, replacement: bytes, message: str
) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    _archive_path, raster_path, record = make_source(source_dir)
    sidecar_path = raster_path.with_suffix(raster_path.suffix + ".xml")
    original = sidecar_path.read_bytes()
    sidecar_path.write_bytes(original.replace(b"sample", replacement))
    sidecar = record["metadata_sidecar"]
    assert isinstance(sidecar, dict)
    sidecar["size_bytes"] = sidecar_path.stat().st_size
    sidecar["sha256"] = sha256_file(sidecar_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"format_version": 1, "sources": [record]}), encoding="utf-8"
    )

    with pytest.raises(TerrainSourceError, match=message):
        verify_source_manifest(manifest_path, source_dir)


def test_manifest_requires_explicit_archive_member_identifiers(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    _archive_path, _raster_path, record = make_source(source_dir)
    record["raster_archive_member"] = "missing.tif"
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"format_version": 1, "sources": [record]}), encoding="utf-8"
    )

    with pytest.raises(TerrainSourceError, match="ZIP member 'missing.tif' is missing"):
        verify_source_manifest(manifest_path, source_dir)


def test_manifest_rejects_hash_mismatch_traversal_and_member_corruption(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    archive_path, _raster_path, record = make_source(source_dir)
    manifest_path = tmp_path / "manifest.json"

    bad_hash = json.loads(json.dumps(record))
    bad_hash["archive"]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps({"format_version": 1, "sources": [bad_hash]}), encoding="utf-8"
    )
    with pytest.raises(TerrainSourceError, match="SHA-256 mismatch"):
        verify_source_manifest(manifest_path, source_dir)

    traversal = json.loads(json.dumps(record))
    traversal["raster_relative_path"] = "../outside.tif"
    manifest_path.write_text(
        json.dumps({"format_version": 1, "sources": [traversal]}), encoding="utf-8"
    )
    with pytest.raises(TerrainSourceError, match="unsafe relative path"):
        verify_source_manifest(manifest_path, source_dir)

    archive_path.write_bytes(b"not a ZIP archive")
    corrupted = json.loads(json.dumps(record))
    corrupted["archive"]["size_bytes"] = archive_path.stat().st_size
    corrupted["archive"]["sha256"] = sha256_file(archive_path)
    manifest_path.write_text(
        json.dumps({"format_version": 1, "sources": [corrupted]}), encoding="utf-8"
    )
    with pytest.raises(TerrainSourceError, match="cannot read source archive"):
        verify_source_manifest(manifest_path, source_dir)


def test_full_tile_measurement_accepts_finite_negative_and_zero(tmp_path: Path) -> None:
    _archive, raster_path, _record = make_source(tmp_path)

    measured = measure_raster_values(raster_path)

    assert measured["masked_pixels"] == 0
    assert measured["nonfinite_pixels"] == 0
    assert measured["minimum_m"] == -1.25
    assert measured["maximum_m"] == 3.75


def test_discovery_has_actionable_missing_source_error(tmp_path: Path) -> None:
    with pytest.raises(TerrainSourceError, match="no GeoTIFF source files found"):
        discover_rasters(tmp_path)
