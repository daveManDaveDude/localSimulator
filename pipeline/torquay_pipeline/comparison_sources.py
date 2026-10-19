"""Verification for comparison-only OS OpenMap–Local raster sources.

This module does not add the reference raster to the terrain or application
world. It verifies the separately downloaded, licensed archive and the exact
5 km GeoTIFF members selected for alignment review.
"""

from __future__ import annotations

import hashlib
import json
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import rasterio
from rasterio.crs import CRS


class ComparisonSourceError(ValueError):
    """Raised when comparison source bytes or raster metadata do not match."""


@dataclass(frozen=True)
class VerifiedTile:
    """One locally extracted GeoTIFF with ZIP member binding and measured metadata."""

    path: Path
    member: str
    size_bytes: int
    sha256: str
    crc32: str
    width: int
    height: int
    crs: str
    transform: tuple[float, float, float, float, float, float]
    bounds: tuple[float, float, float, float]
    resolution: tuple[float, float]
    band_count: int
    dtype: str
    color_interpretation: tuple[str, ...]
    pixel_interpretation: str
    nodata: float | None
    palette_entries: int | None
    tags: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "member": self.member,
            "filename": self.path.name,
            "sizeBytes": self.size_bytes,
            "sha256": self.sha256,
            "crc32": self.crc32,
            "crs": self.crs,
            "width": self.width,
            "height": self.height,
            "bandCount": self.band_count,
            "dtype": self.dtype,
            "transform": list(self.transform),
            "boundsM": list(self.bounds),
            "resolutionM": list(self.resolution),
            "colorInterpretation": list(self.color_interpretation),
            "pixelInterpretation": self.pixel_interpretation,
            "nodata": self.nodata,
            "paletteEntries": self.palette_entries,
            "tags": dict(sorted(self.tags.items())),
        }


@dataclass(frozen=True)
class VerifiedComparisonSource:
    """Verified source archive, selected raster members, and licence documents."""

    manifest_path: Path
    source_root: Path
    manifest: dict[str, Any]
    record: dict[str, Any]
    archive_path: Path
    tiles: tuple[VerifiedTile, ...]
    support_files: tuple[dict[str, Any], ...]

    def cover(self, bounds_m: tuple[float, float, float, float]) -> bool:
        """Return whether selected raster bounds cover the complete requested BNG extent."""
        left, bottom, right, top = bounds_m
        if not all(math.isfinite(value) for value in bounds_m) or left >= right or bottom >= top:
            return False
        # The selected tiles are edge-adjacent on an exact integer-metre grid.
        # Their union is rectangular here; checking the union envelope plus all
        # intersections against the required vertical seam avoids a false pass
        # when a future comparison window lies in a gap.
        ordered = sorted(self.tiles, key=lambda tile: (tile.bounds[1], tile.bounds[0]))
        coverage = [tile.bounds for tile in ordered]
        x_edges = sorted(
            {left, right}
            | {max(left, b[0]) for b in coverage}
            | {min(right, b[2]) for b in coverage}
        )
        y_edges = sorted(
            {bottom, top}
            | {max(bottom, b[1]) for b in coverage}
            | {min(top, b[3]) for b in coverage}
        )
        for y0, y1 in zip(y_edges, y_edges[1:], strict=False):
            if y1 <= y0:
                continue
            for x0, x1 in zip(x_edges, x_edges[1:], strict=False):
                if x1 <= x0:
                    continue
                if left <= x0 and x1 <= right and bottom <= y0 and y1 <= top:
                    if not any(
                        b[0] <= x0 and x1 <= b[2] and b[1] <= y0 and y1 <= b[3] for b in coverage
                    ):
                        return False
        return True


def sha256_file(path: Path) -> str:
    """Hash a file incrementally, avoiding large in-memory copies."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ComparisonSourceError(f"cannot read comparison source '{path}': {exc}") from exc
    return digest.hexdigest()


def _safe_path(root: Path, value: object, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ComparisonSourceError(f"{field} must be a non-empty relative path")
    portable = PurePosixPath(value)
    if portable.is_absolute() or any(part in {"", ".", ".."} for part in portable.parts):
        raise ComparisonSourceError(f"{field} must be a safe source-root-relative path")
    if "\\" in value or ":" in value:
        raise ComparisonSourceError(f"{field} must use a portable POSIX relative path")
    path = root.joinpath(*portable.parts).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ComparisonSourceError(f"{field} escapes the comparison source root") from exc
    return path


def _required_object(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ComparisonSourceError(f"{field} must be an object")
    return value


def _number_equal(actual: float, expected: object, field: str) -> None:
    if isinstance(expected, bool) or not isinstance(expected, (int, float)):
        raise ComparisonSourceError(f"source manifest {field} must be numeric")
    if not math.isfinite(float(expected)) or actual != float(expected):
        raise ComparisonSourceError(
            f"source manifest {field} mismatch: manifest={expected!r}, actual={actual!r}"
        )


def _inspect_tile(path: Path, record: dict[str, Any], member_info: zipfile.ZipInfo) -> VerifiedTile:
    try:
        with rasterio.open(path) as dataset:
            if dataset.crs is None:
                raise ComparisonSourceError(f"selected GeoTIFF '{path.name}' is missing a CRS")
            if dataset.crs != CRS.from_epsg(27700):
                raise ComparisonSourceError(
                    f"selected GeoTIFF '{path.name}' uses {dataset.crs}; expected EPSG:27700"
                )
            affine = dataset.transform
            transform = (affine.a, affine.b, affine.c, affine.d, affine.e, affine.f)
            if not all(math.isfinite(value) for value in transform):
                raise ComparisonSourceError(
                    f"selected GeoTIFF '{path.name}' has a non-finite affine"
                )
            if not (affine.a == 1.0 and affine.e == -1.0 and affine.b == 0.0 and affine.d == 0.0):
                raise ComparisonSourceError(
                    f"selected GeoTIFF '{path.name}' must use exact north-up 1 m pixels"
                )
            if not all(float(value).is_integer() for value in (affine.c, affine.f)):
                raise ComparisonSourceError(
                    f"selected GeoTIFF '{path.name}' has a non-integer EPSG:27700 origin"
                )
            if dataset.count != 1 or dataset.dtypes[0] != "uint8":
                raise ComparisonSourceError(
                    f"selected GeoTIFF '{path.name}' must have one uint8 full-colour index band"
                )
            color_interpretation = tuple(item.name for item in dataset.colorinterp)
            if color_interpretation != ("palette",):
                raise ComparisonSourceError(
                    f"selected GeoTIFF '{path.name}' is not a palette-rendered map raster"
                )
            try:
                palette_entries = len(dataset.colormap(1))
            except ValueError as exc:
                raise ComparisonSourceError(
                    f"selected GeoTIFF '{path.name}' is missing its color palette"
                ) from exc
            if palette_entries != 256:
                raise ComparisonSourceError(
                    f"selected GeoTIFF '{path.name}' has {palette_entries} palette entries; "
                    "expected 256"
                )
            bounds = dataset.bounds
            values = {
                "width": dataset.width,
                "height": dataset.height,
                "bandCount": dataset.count,
                "dtype": dataset.dtypes[0],
                "crs": dataset.crs.to_string(),
                "transform": list(transform),
                "boundsM": [bounds.left, bounds.bottom, bounds.right, bounds.top],
                "resolutionM": [abs(affine.a), abs(affine.e)],
                "colorInterpretation": list(color_interpretation),
                "pixelInterpretation": dataset.tags().get("AREA_OR_POINT", "Area"),
                "nodata": dataset.nodata,
                "paletteEntries": palette_entries,
            }
            expected = _required_object(record.get("raster"), f"tile {path.name}.raster")
            for field in (
                "width",
                "height",
                "bandCount",
                "dtype",
                "crs",
                "transform",
                "boundsM",
                "resolutionM",
                "colorInterpretation",
                "pixelInterpretation",
                "nodata",
                "paletteEntries",
            ):
                if values[field] != expected.get(field):
                    raise ComparisonSourceError(
                        f"tile {path.name} metadata {field} mismatch: "
                        f"manifest={expected.get(field)!r}, actual={values[field]!r}"
                    )
            size_bytes = path.stat().st_size
            expected_size = record.get("sizeBytes")
            if isinstance(expected_size, bool) or expected_size != size_bytes:
                raise ComparisonSourceError(
                    f"tile {path.name} byte length mismatch: manifest={expected_size!r}, "
                    f"actual={size_bytes}"
                )
            digest = sha256_file(path)
            if record.get("sha256") != digest:
                raise ComparisonSourceError(f"tile {path.name} SHA-256 mismatch")
            expected_crc = record.get("crc32")
            if (
                not isinstance(expected_crc, str)
                or expected_crc.lower() != f"{member_info.CRC:08x}"
            ):
                raise ComparisonSourceError(
                    f"tile {path.name} ZIP CRC32 mismatch: manifest={expected_crc!r}, "
                    f"archive={member_info.CRC:08x}"
                )
            tags = dict(dataset.tags())
            expected_tags = expected.get("tags")
            if not isinstance(expected_tags, dict) or tags != expected_tags:
                raise ComparisonSourceError(
                    f"tile {path.name} metadata tags mismatch: "
                    f"manifest={expected_tags!r}, actual={tags!r}"
                )
    except ComparisonSourceError:
        raise
    except Exception as exc:  # Rasterio driver errors vary by platform.
        raise ComparisonSourceError(f"cannot inspect selected GeoTIFF '{path}': {exc}") from exc

    return VerifiedTile(
        path=path,
        member=str(record.get("archiveMember")),
        size_bytes=size_bytes,
        sha256=digest,
        crc32=f"{member_info.CRC:08x}",
        width=dataset.width,
        height=dataset.height,
        crs="EPSG:27700",
        transform=transform,
        bounds=(bounds.left, bounds.bottom, bounds.right, bounds.top),
        resolution=(abs(affine.a), abs(affine.e)),
        band_count=dataset.count,
        dtype=dataset.dtypes[0],
        color_interpretation=color_interpretation,
        pixel_interpretation=values["pixelInterpretation"],
        nodata=dataset.nodata,
        palette_entries=palette_entries,
        tags=tags,
    )


def verify_comparison_source(manifest_path: Path, source_root: Path) -> VerifiedComparisonSource:
    """Verify archive identity, ZIP CRCs, selected member bindings, and GeoTIFF metadata."""
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ComparisonSourceError(
            f"cannot read comparison source manifest '{manifest_path}': {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ComparisonSourceError(
            f"comparison source manifest '{manifest_path}' is invalid JSON: {exc}"
        ) from exc
    if not isinstance(raw, dict) or raw.get("formatVersion") != 1:
        raise ComparisonSourceError(
            "comparison source manifest must be an object with formatVersion=1"
        )
    if raw.get("scope") != "comparison-only":
        raise ComparisonSourceError("comparison source manifest scope must be 'comparison-only'")
    records = raw.get("sources")
    if not isinstance(records, list) or len(records) != 1 or not isinstance(records[0], dict):
        raise ComparisonSourceError(
            "comparison source manifest must contain exactly one source record"
        )
    record = records[0]
    if record.get("sourceId") != "os-openmap-local-apr-2026-sx":
        raise ComparisonSourceError(
            "comparison source must identify the accepted April 2026 SX archive"
        )
    archive = _required_object(record.get("archive"), "source.archive")
    archive_path = _safe_path(source_root, archive.get("relativePath"), "archive.relativePath")
    if not archive_path.is_file():
        raise ComparisonSourceError(
            f"comparison archive is missing: '{archive_path}'. Restore the accepted SX ZIP under "
            "data/raw/comparison/os_openmap_local/ before running the comparison."
        )
    actual_size = archive_path.stat().st_size
    if isinstance(archive.get("sizeBytes"), bool) or archive.get("sizeBytes") != actual_size:
        raise ComparisonSourceError(
            f"comparison archive byte length mismatch: manifest={archive.get('sizeBytes')!r}, "
            f"actual={actual_size}"
        )
    digest = sha256_file(archive_path)
    if archive.get("sha256") != digest:
        raise ComparisonSourceError(
            f"comparison archive SHA-256 mismatch for '{archive_path.name}'"
        )
    if archive.get("httpStatus") != 200 or archive.get("contentLengthBytes") != actual_size:
        raise ComparisonSourceError(
            "comparison archive HTTP status or recorded content length does not match the download"
        )
    if archive.get("advertisedSizeText") != "349.41 MB":
        raise ComparisonSourceError("accepted SX archive advertised size must remain 349.41 MB")
    support_records = record.get("supportFiles")
    if not isinstance(support_records, list):
        raise ComparisonSourceError("source.supportFiles must be an array")
    tile_records = record.get("selectedTiles")
    if not isinstance(tile_records, list) or len(tile_records) != 2:
        raise ComparisonSourceError(
            "source.selectedTiles must list exactly the two AOI-covering 5 km tiles"
        )

    try:
        with zipfile.ZipFile(archive_path) as archive_file:
            if len(archive_file.infolist()) != archive.get("archiveMemberCount"):
                raise ComparisonSourceError("comparison ZIP member count differs from the manifest")
            names = archive_file.namelist()
            if len(names) != len(set(names)):
                raise ComparisonSourceError("comparison ZIP contains duplicate member names")
            corrupt = archive_file.testzip()
            if corrupt is not None:
                raise ComparisonSourceError(
                    f"comparison ZIP CRC verification failed at member '{corrupt}'"
                )
            tiles: list[VerifiedTile] = []
            support_files: list[dict[str, Any]] = []
            for index, tile_record_obj in enumerate(tile_records):
                tile_record = _required_object(tile_record_obj, f"source.selectedTiles[{index}]")
                member_name = tile_record.get("archiveMember")
                if not isinstance(member_name, str) or member_name not in names:
                    raise ComparisonSourceError(
                        f"selected tile {index} archiveMember is not an exact member in the SX ZIP"
                    )
                member_info = archive_file.getinfo(member_name)
                if member_info.is_dir():
                    raise ComparisonSourceError(
                        f"selected tile member '{member_name}' is a directory"
                    )
                extracted_path = _safe_path(
                    source_root,
                    tile_record.get("relativePath"),
                    f"selectedTiles[{index}].relativePath",
                )
                if not extracted_path.is_file():
                    raise ComparisonSourceError(f"selected tile is missing: '{extracted_path}'")
                if member_info.file_size != extracted_path.stat().st_size:
                    raise ComparisonSourceError(
                        f"selected tile '{member_name}' byte length differs from its extracted file"
                    )
                archive_hash = hashlib.sha256()
                streamed = 0
                with archive_file.open(member_info, "r") as source_member:
                    for chunk in iter(lambda: source_member.read(1024 * 1024), b""):
                        streamed += len(chunk)
                        archive_hash.update(chunk)
                extracted_hash = sha256_file(extracted_path)
                if streamed != member_info.file_size or archive_hash.hexdigest() != extracted_hash:
                    raise ComparisonSourceError(
                        f"selected tile '{member_name}' differs from its exact ZIP member bytes"
                    )
                if (
                    tile_record.get("sizeBytes") != streamed
                    or tile_record.get("sha256") != extracted_hash
                ):
                    raise ComparisonSourceError(
                        f"selected tile '{member_name}' manifest size/hash mismatch"
                    )
                tiles.append(_inspect_tile(extracted_path, tile_record, member_info))
            for index, support_obj in enumerate(support_records):
                support = _required_object(support_obj, f"source.supportFiles[{index}]")
                member = support.get("archiveMember")
                if not isinstance(member, str) or member not in names:
                    raise ComparisonSourceError(
                        f"support file {index} has no exact ZIP member binding"
                    )
                member_info = archive_file.getinfo(member)
                path = _safe_path(
                    source_root, support.get("relativePath"), f"supportFiles[{index}].relativePath"
                )
                if not path.is_file() or path.stat().st_size != member_info.file_size:
                    raise ComparisonSourceError(
                        f"support file '{member}' is missing or has a byte length mismatch"
                    )
                actual = sha256_file(path)
                if (
                    support.get("sizeBytes") != member_info.file_size
                    or support.get("sha256") != actual
                ):
                    raise ComparisonSourceError(
                        f"support file '{member}' manifest size/hash mismatch"
                    )
                expected_crc = support.get("crc32")
                if (
                    not isinstance(expected_crc, str)
                    or expected_crc.lower() != f"{member_info.CRC:08x}"
                ):
                    raise ComparisonSourceError(f"support file '{member}' ZIP CRC32 mismatch")
                member_digest = hashlib.sha256(archive_file.read(member)).hexdigest()
                if actual != member_digest:
                    raise ComparisonSourceError(
                        f"support file '{member}' differs from its ZIP member bytes"
                    )
                support_files.append({**support, "verifiedSha256": actual})
    except zipfile.BadZipFile as exc:
        raise ComparisonSourceError(f"comparison archive is not a valid ZIP file: {exc}") from exc
    except OSError as exc:
        raise ComparisonSourceError(
            f"cannot inspect comparison archive '{archive_path}': {exc}"
        ) from exc
    return VerifiedComparisonSource(
        manifest_path=manifest_path.resolve(),
        source_root=source_root.resolve(),
        manifest=raw,
        record=record,
        archive_path=archive_path,
        tiles=tuple(tiles),
        support_files=tuple(support_files),
    )
