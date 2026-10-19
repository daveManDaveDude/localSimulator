from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

from torquay_pipeline.comparison_sources import (
    ComparisonSourceError,
    VerifiedComparisonSource,
    VerifiedTile,
    sha256_file,
    verify_comparison_source,
)


def _tile(
    path: Path, west: int, south: int, *, crs: str = "EPSG:27700", rotated: bool = False
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    transform = (
        Affine(1, 0.01, west, 0, -1, south + 2) if rotated else Affine(1, 0, west, 0, -1, south + 2)
    )
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=1,
        dtype="uint8",
        crs=crs,
        transform=transform,
    ) as dataset:
        dataset.write(np.asarray([[1, 2], [3, 4]], dtype=np.uint8), 1)
        dataset.write_colormap(1, {index: (index, index, index, 255) for index in range(256)})
        dataset.update_tags(AREA_OR_POINT="Area", TIFFTAG_IMAGEDESCRIPTION=f"test {path.name}")


def _raster_record(path: Path, member: str) -> dict[str, Any]:
    with rasterio.open(path) as dataset:
        bounds = dataset.bounds
        transform = dataset.transform
        return {
            "archiveMember": member,
            "relativePath": f"selected-members/{path.name}",
            "sizeBytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "crc32": "00000000",
            "raster": {
                "width": dataset.width,
                "height": dataset.height,
                "bandCount": dataset.count,
                "dtype": dataset.dtypes[0],
                "crs": dataset.crs.to_string(),
                "transform": [
                    transform.a,
                    transform.b,
                    transform.c,
                    transform.d,
                    transform.e,
                    transform.f,
                ],
                "boundsM": [bounds.left, bounds.bottom, bounds.right, bounds.top],
                "resolutionM": [abs(transform.a), abs(transform.e)],
                "colorInterpretation": [item.name for item in dataset.colorinterp],
                "pixelInterpretation": dataset.tags().get("AREA_OR_POINT", "Area"),
                "nodata": dataset.nodata,
                "paletteEntries": len(dataset.colormap(1)),
                "tags": dataset.tags(),
            },
        }


def _make_source(root: Path, *, tile_crs: str = "EPSG:27700", rotated: bool = False) -> Path:
    extracted = root / "selected-members"
    sw = extracted / "SYNTH_SW.tif"
    nw = extracted / "SYNTH_NW.tif"
    _tile(sw, 100, 0, crs=tile_crs, rotated=rotated)
    _tile(nw, 100, 2, crs=tile_crs, rotated=rotated)
    licence = extracted / "licence.txt"
    readme = extracted / "readme.txt"
    licence.write_text("Contains fictional test data", encoding="ascii")
    readme.write_text("Synthetic comparison fixture", encoding="ascii")

    archive_path = root / "fixture.zip"
    member_names = {
        "sw": "fixture/data/SYNTH_SW.tif",
        "nw": "fixture/data/SYNTH_NW.tif",
        "licence": "fixture/doc/licence.txt",
        "readme": "fixture/readme.txt",
    }
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(sw, member_names["sw"])
        archive.write(nw, member_names["nw"])
        archive.write(licence, member_names["licence"])
        archive.write(readme, member_names["readme"])
    with zipfile.ZipFile(archive_path) as archive:
        tile_records = []
        for path, key in ((sw, "sw"), (nw, "nw")):
            record = _raster_record(path, member_names[key])
            info = archive.getinfo(member_names[key])
            record["crc32"] = f"{info.CRC:08x}"
            tile_records.append(record)
        support_records = []
        for path, key in ((licence, "licence"), (readme, "readme")):
            info = archive.getinfo(member_names[key])
            support_records.append(
                {
                    "archiveMember": member_names[key],
                    "relativePath": f"selected-members/{path.name}",
                    "sizeBytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                    "crc32": f"{info.CRC:08x}",
                }
            )
        record = {
            "sourceId": "os-openmap-local-apr-2026-sx",
            "archive": {
                "relativePath": "fixture.zip",
                "sizeBytes": archive_path.stat().st_size,
                "sha256": sha256_file(archive_path),
                "httpStatus": 200,
                "contentLengthBytes": archive_path.stat().st_size,
                "advertisedSizeText": "349.41 MB",
                "archiveMemberCount": len(archive.infolist()),
            },
            "selectedTiles": tile_records,
            "supportFiles": support_records,
        }
    manifest = root / "comparison-source-manifest.json"
    manifest.write_text(
        json.dumps({"formatVersion": 1, "scope": "comparison-only", "sources": [record]}),
        encoding="utf-8",
    )
    return manifest


def _source(manifest_path: Path) -> VerifiedComparisonSource:
    return verify_comparison_source(manifest_path, manifest_path.parent)


def test_source_verifies_member_bindings_metadata_and_adjacent_tile_coverage(
    tmp_path: Path,
) -> None:
    manifest = _make_source(tmp_path)

    source = _source(manifest)

    assert [tile.member.rsplit("/", 1)[-1] for tile in source.tiles] == [
        "SYNTH_SW.tif",
        "SYNTH_NW.tif",
    ]
    assert source.cover((100.0, 0.0, 102.0, 4.0))
    assert not source.cover((100.0, 0.0, 102.0, 5.0))
    assert not source.cover((99.0, 0.0, 102.0, 4.0))


def test_source_rejects_missing_archive_and_unsafe_manifest_path(tmp_path: Path) -> None:
    manifest = _make_source(tmp_path)
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    archive_path = tmp_path / "fixture.zip"
    archive_path.unlink()
    with pytest.raises(ComparisonSourceError, match="comparison archive is missing"):
        _source(manifest)

    raw["sources"][0]["archive"]["relativePath"] = "../fixture.zip"
    manifest.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ComparisonSourceError, match="safe source-root-relative"):
        _source(manifest)


def test_source_rejects_extracted_tiff_that_differs_from_exact_zip_member(tmp_path: Path) -> None:
    manifest = _make_source(tmp_path)
    with (tmp_path / "selected-members" / "SYNTH_NW.tif").open("ab") as stream:
        stream.write(b"tampered")

    with pytest.raises(ComparisonSourceError, match="byte length differs from its extracted file"):
        _source(manifest)


def test_source_rejects_missing_selected_member(tmp_path: Path) -> None:
    manifest = _make_source(tmp_path)
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    raw["sources"][0]["selectedTiles"][0]["archiveMember"] = "missing.tif"
    manifest.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ComparisonSourceError, match="archiveMember is not an exact member"):
        _source(manifest)


@pytest.mark.parametrize(
    "tile_crs,rotated,message",
    [
        ("EPSG:4326", False, "expected EPSG:27700"),
        ("EPSG:27700", True, "exact north-up 1 m pixels"),
    ],
)
def test_source_rejects_unsupported_crs_and_affine(
    tmp_path: Path, tile_crs: str, rotated: bool, message: str
) -> None:
    manifest = _make_source(tmp_path, tile_crs=tile_crs, rotated=rotated)

    with pytest.raises(ComparisonSourceError, match=message):
        _source(manifest)


def test_source_rejects_archive_crc_corruption_after_archive_hash_is_refreshed(
    tmp_path: Path,
) -> None:
    manifest = _make_source(tmp_path)
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    archive_path = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive_path) as archive:
        info = archive.getinfo("fixture/data/SYNTH_SW.tif")
        crc_offset = archive_path.read_bytes().find(b"PK\x01\x02", info.header_offset) + 16
        assert crc_offset >= 16
    with archive_path.open("r+b") as stream:
        stream.seek(crc_offset)
        crc = int.from_bytes(stream.read(4), "little")
        stream.seek(crc_offset)
        stream.write((crc ^ 1).to_bytes(4, "little"))
    raw["sources"][0]["archive"]["sha256"] = sha256_file(archive_path)
    manifest.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ComparisonSourceError, match="CRC verification failed"):
        _source(manifest)


def test_coverage_union_detects_a_gap_between_selected_tiles(tmp_path: Path) -> None:
    tile_a = VerifiedTile(
        path=tmp_path / "a.tif",
        member="a",
        size_bytes=1,
        sha256="0" * 64,
        crc32="0" * 8,
        width=2,
        height=2,
        crs="EPSG:27700",
        transform=(1, 0, 0, 0, -1, 2),
        bounds=(0, 0, 2, 2),
        resolution=(1, 1),
        band_count=1,
        dtype="uint8",
        color_interpretation=("palette",),
        pixel_interpretation="Area",
        nodata=None,
        palette_entries=256,
        tags={},
    )
    tile_b = VerifiedTile(
        path=tmp_path / "b.tif",
        member="b",
        size_bytes=1,
        sha256="0" * 64,
        crc32="0" * 8,
        width=2,
        height=2,
        crs="EPSG:27700",
        transform=(1, 0, 0, 0, -1, 5),
        bounds=(0, 3, 2, 5),
        resolution=(1, 1),
        band_count=1,
        dtype="uint8",
        color_interpretation=("palette",),
        pixel_interpretation="Area",
        nodata=None,
        palette_entries=256,
        tags={},
    )
    source = VerifiedComparisonSource(
        manifest_path=tmp_path / "manifest.json",
        source_root=tmp_path,
        manifest={},
        record={},
        archive_path=tmp_path / "source.zip",
        tiles=(tile_a, tile_b),
        support_files=(),
    )

    assert not source.cover((0, 0, 2, 5))
