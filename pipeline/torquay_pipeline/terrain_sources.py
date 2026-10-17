"""Discovery, validation, and provenance checks for local EA raster sources."""

from __future__ import annotations

import hashlib
import json
import math
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from math import isclose, isfinite, isnan
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
import rasterio
from rasterio.crs import CRS


class TerrainSourceError(ValueError):
    """Raised when a local source raster or its provenance is missing or unsupported."""


@dataclass(frozen=True)
class RasterMetadata:
    """Measured GeoTIFF metadata and a streaming content digest."""

    path: Path
    size_bytes: int
    sha256: str
    width: int
    height: int
    band_count: int
    dtype: str
    crs: str
    pixel_interpretation: str
    transform: tuple[float, float, float, float, float, float]
    bounds: tuple[float, float, float, float]
    resolution: tuple[float, float]
    nodata: float | None
    mask_flags: tuple[str, ...]
    block_shape: tuple[int, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.path.name,
            "relative_path": self.path.name,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "width_pixels": self.width,
            "height_pixels": self.height,
            "band_count": self.band_count,
            "dtype": self.dtype,
            "crs": self.crs,
            "pixel_interpretation": self.pixel_interpretation,
            "transform": list(self.transform),
            "bounds_m": list(self.bounds),
            "resolution_m": list(self.resolution),
            "nodata": self.nodata,
            "mask_flags": list(self.mask_flags),
            "block_shape_pixels": list(self.block_shape),
        }


def sha256_file(path: Path) -> str:
    """Return a file's SHA-256 digest without reading it all into memory."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise TerrainSourceError(f"cannot read source file '{path}': {exc}") from exc
    return digest.hexdigest()


def _metadata_sidecar(path: Path) -> dict[str, Any] | None:
    sidecar = path.with_suffix(path.suffix + ".xml")
    if not sidecar.is_file():
        return None
    try:
        root = ET.parse(sidecar).getroot()
    except (ET.ParseError, OSError) as exc:
        raise TerrainSourceError(f"invalid metadata sidecar '{sidecar}': {exc}") from exc

    def values(local_name: str) -> list[str]:
        return [
            (element.text or "").strip()
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == local_name and (element.text or "").strip()
        ]

    abstracts = values("idAbs")
    limits = values("useLimit")
    return {
        "filename": sidecar.name,
        "size_bytes": sidecar.stat().st_size,
        "sha256": sha256_file(sidecar),
        "creation_date": next(iter(values("CreaDate")), None),
        "metadata_date": next(iter(values("mdDateSt")), None),
        "native_extent": values("nativeExtBox"),
        "nodata_values": values("NoDataValue"),
        "abstract": abstracts[0] if abstracts else None,
        "reuse_statement": next((item for item in limits if item), None),
    }


def inspect_raster(path: Path) -> tuple[RasterMetadata, dict[str, Any] | None]:
    """Read a raster's structural metadata and validate its supported grid shape."""
    if not path.is_file():
        raise TerrainSourceError(f"raster file does not exist: '{path}'")
    try:
        size_bytes = path.stat().st_size
        digest = sha256_file(path)
        with rasterio.open(path) as dataset:
            if dataset.crs is None:
                raise TerrainSourceError(f"raster '{path.name}' is missing a CRS")
            if dataset.crs != CRS.from_epsg(27700):
                raise TerrainSourceError(
                    f"raster '{path.name}' uses {dataset.crs}; expected EPSG:27700"
                )
            if dataset.count != 1:
                raise TerrainSourceError(
                    f"raster '{path.name}' has {dataset.count} bands; expected one DTM band"
                )
            if dataset.width < 1 or dataset.height < 1:
                raise TerrainSourceError(f"raster '{path.name}' has an empty pixel grid")
            transform = dataset.transform
            values = (transform.a, transform.b, transform.c, transform.d, transform.e, transform.f)
            if not all(math.isfinite(value) for value in values):
                raise TerrainSourceError(f"raster '{path.name}' has a non-finite transform")
            if not (
                transform.a == 1.0
                and transform.e == -1.0
                and transform.b == 0.0
                and transform.d == 0.0
            ):
                raise TerrainSourceError(
                    f"raster '{path.name}' has unsupported transform/resolution; "
                    "expected exact north-up, unrotated 1 m pixels "
                    "(a=1, b=0, d=0, e=-1)"
                )
            if not all(value == round(value) for value in (transform.c, transform.f)):
                raise TerrainSourceError(
                    f"raster '{path.name}' origin is not aligned to integer EPSG:27700 metres"
                )
            dtype = dataset.dtypes[0]
            if not dtype.startswith("float"):
                raise TerrainSourceError(
                    f"raster '{path.name}' has unsupported {dtype} samples; expected floating point"
                )
            pixel_interpretation = dataset.tags().get("AREA_OR_POINT", "Area")
            if pixel_interpretation.lower() != "area":
                raise TerrainSourceError(
                    f"raster '{path.name}' uses {pixel_interpretation!r} pixel registration; "
                    "AOI cell-center sampling requires area pixels"
                )
            nodata_value = dataset.nodata
            nodata = float(nodata_value) if nodata_value is not None else None
            if nodata is not None and math.isnan(nodata):
                nodata = float("nan")
            flags = tuple(sorted(flag.name for flag in dataset.mask_flag_enums[0]))
            block_shape = dataset.block_shapes[0]
            bounds = dataset.bounds
            metadata = RasterMetadata(
                path=path,
                size_bytes=size_bytes,
                sha256=digest,
                width=dataset.width,
                height=dataset.height,
                band_count=dataset.count,
                dtype=dtype,
                crs=dataset.crs.to_string(),
                pixel_interpretation=pixel_interpretation,
                transform=values,
                bounds=(bounds.left, bounds.bottom, bounds.right, bounds.top),
                resolution=(abs(transform.a), abs(transform.e)),
                nodata=nodata,
                mask_flags=flags,
                block_shape=(block_shape[0], block_shape[1]),
            )
    except TerrainSourceError:
        raise
    except Exception as exc:  # Rasterio raises several driver-specific exceptions.
        raise TerrainSourceError(f"cannot inspect raster '{path}': {exc}") from exc
    return metadata, _metadata_sidecar(path)


def measure_raster_values(path: Path) -> dict[str, Any]:
    """Count masked/non-finite cells and measure finite valid elevations in chunks."""
    if not path.is_file():
        raise TerrainSourceError(f"raster file does not exist: '{path}'")
    count = 0
    masked_count = 0
    nonfinite_count = 0
    minimum = float("inf")
    maximum = float("-inf")
    try:
        with rasterio.open(path) as dataset:
            nodata = dataset.nodata
            chunk_rows = max(1, min(256, dataset.height))
            for row_start in range(0, dataset.height, chunk_rows):
                row_count = min(chunk_rows, dataset.height - row_start)
                window = rasterio.windows.Window(0, row_start, dataset.width, row_count)
                values = dataset.read(1, window=window)
                mask = dataset.read_masks(1, window=window)
                finite = np.isfinite(values)
                is_nodata = np.zeros(values.shape, dtype=bool)
                if nodata is not None:
                    is_nodata = np.isnan(values) if isnan(float(nodata)) else values == nodata
                masked = (mask == 0) | is_nodata
                valid = (mask > 0) & finite & ~is_nodata
                count += int(values.size)
                masked_count += int(np.count_nonzero(masked))
                nonfinite_count += int(np.count_nonzero((mask > 0) & ~finite & ~is_nodata))
                if np.any(valid):
                    minimum = min(minimum, float(np.min(values[valid])))
                    maximum = max(maximum, float(np.max(values[valid])))
    except Exception as exc:
        raise TerrainSourceError(f"cannot measure raster values in '{path}': {exc}") from exc
    return {
        "total_pixels": count,
        "masked_pixels": masked_count,
        "nonfinite_pixels": nonfinite_count,
        "minimum_m": minimum if isfinite(minimum) else None,
        "maximum_m": maximum if isfinite(maximum) else None,
    }


def _safe_file_path(root: Path, relative: object, label: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise TerrainSourceError(f"source manifest {label} must be a non-empty relative path")
    portable = PurePosixPath(relative)
    if portable.is_absolute() or any(part in {"", ".", ".."} for part in portable.parts):
        raise TerrainSourceError(f"source manifest {label} contains an unsafe relative path")
    if "\\" in relative or ":" in relative:
        raise TerrainSourceError(f"source manifest {label} must use safe POSIX relative paths")
    path = root.joinpath(*portable.parts).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise TerrainSourceError(f"source manifest {label} escapes its source directory") from exc
    return path


def _verify_archive_member_binding(
    archive_file: zipfile.ZipFile,
    archive_path: Path,
    member_name: object,
    extracted_path: Path,
    label: str,
) -> dict[str, Any]:
    """Stream a ZIP member digest and require its extracted copy to match byte-for-byte."""
    if not isinstance(member_name, str) or not member_name.strip():
        raise TerrainSourceError(f"{label} must name an exact ZIP archive member")
    try:
        member = archive_file.getinfo(member_name)
    except KeyError as exc:
        raise TerrainSourceError(
            f"{label} ZIP member '{member_name}' is missing from '{archive_path.name}'"
        ) from exc
    if member.is_dir():
        raise TerrainSourceError(f"{label} ZIP member '{member_name}' is a directory")

    extracted_size = extracted_path.stat().st_size
    if member.file_size != extracted_size:
        raise TerrainSourceError(
            f"{label} byte length mismatch: ZIP member '{member_name}' has "
            f"{member.file_size} bytes but extracted '{extracted_path.name}' has "
            f"{extracted_size} bytes"
        )

    digest = hashlib.sha256()
    streamed_size = 0
    try:
        with archive_file.open(member, "r") as source_member:
            for chunk in iter(lambda: source_member.read(1024 * 1024), b""):
                streamed_size += len(chunk)
                digest.update(chunk)
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise TerrainSourceError(
            f"cannot hash ZIP member '{member_name}' in '{archive_path.name}': {exc}"
        ) from exc
    if streamed_size != member.file_size:
        raise TerrainSourceError(
            f"{label} streamed byte length mismatch for ZIP member '{member_name}': "
            f"directory lists {member.file_size} bytes, stream produced {streamed_size}"
        )

    member_sha256 = digest.hexdigest()
    extracted_sha256 = sha256_file(extracted_path)
    if extracted_sha256 != member_sha256:
        raise TerrainSourceError(
            f"{label} SHA-256 mismatch between ZIP member '{member_name}' and "
            f"extracted file '{extracted_path.name}'"
        )
    return {
        "member": member_name,
        "size_bytes": streamed_size,
        "sha256": member_sha256,
    }


def verify_source_manifest(
    manifest_path: Path, source_dir: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Verify the committed provenance manifest against local archives and GeoTIFFs."""
    if not manifest_path.is_file():
        raise TerrainSourceError(f"source manifest is missing: '{manifest_path}'")
    try:
        raw: Any = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise TerrainSourceError(f"cannot read source manifest '{manifest_path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise TerrainSourceError(
            f"source manifest '{manifest_path}' is not valid JSON: {exc}"
        ) from exc
    if not isinstance(raw, dict) or raw.get("format_version") != 1:
        raise TerrainSourceError("source manifest format_version must be 1")
    source_records = raw.get("sources")
    if not isinstance(source_records, list) or not source_records:
        raise TerrainSourceError("source manifest must contain a non-empty sources array")

    verified: list[dict[str, Any]] = []
    for index, record in enumerate(source_records):
        label = f"sources[{index}]"
        if not isinstance(record, dict):
            raise TerrainSourceError(f"source manifest {label} must be an object")
        archive_path = _safe_file_path(
            source_dir, record.get("archive_filename"), f"{label}.archive_filename"
        )
        raster_path = _safe_file_path(
            source_dir, record.get("raster_relative_path"), f"{label}.raster_relative_path"
        )
        for key, path in (("archive", archive_path), ("GeoTIFF", raster_path)):
            if not path.is_file():
                raise TerrainSourceError(
                    f"source manifest {label} {key} is missing: '{path}'. "
                    "Restore the local files using docs/data-sources.md."
                )

        archive = record.get("archive")
        raster_expected = record.get("raster")
        if not isinstance(archive, dict) or not isinstance(raster_expected, dict):
            raise TerrainSourceError(
                f"source manifest {label} must describe archive and raster metadata"
            )
        for kind, path, expected in (
            ("archive", archive_path, archive),
            ("GeoTIFF", raster_path, raster_expected),
        ):
            actual_size = path.stat().st_size
            actual_sha = sha256_file(path)
            if expected.get("size_bytes") != actual_size:
                raise TerrainSourceError(
                    f"{label} {kind} size mismatch for '{path.name}': "
                    f"manifest {expected.get('size_bytes')}, actual {actual_size}"
                )
            expected_sha = expected.get("sha256")
            if not isinstance(expected_sha, str) or expected_sha.lower() != actual_sha:
                raise TerrainSourceError(f"{label} {kind} SHA-256 mismatch for '{path.name}'")
        portal_response = record.get("portal_response")
        if isinstance(portal_response, dict):
            if portal_response.get("http_status") != 200:
                raise TerrainSourceError(f"{label} portal response status must be HTTP 200")
            if portal_response.get("content_length_bytes") != archive_path.stat().st_size:
                raise TerrainSourceError(
                    f"{label} portal response content length differs from the downloaded archive"
                )

        expected_members = record.get("archive_members")
        if not isinstance(expected_members, list) or not all(
            isinstance(item, str) for item in expected_members
        ):
            raise TerrainSourceError(f"{label}.archive_members must be an array of filenames")
        try:
            with zipfile.ZipFile(archive_path) as archive_file:
                actual_members = sorted(archive_file.namelist())
                if actual_members != sorted(expected_members):
                    raise TerrainSourceError(
                        f"{label} archive member list differs from the source manifest"
                    )
                if len(actual_members) != len(set(actual_members)):
                    raise TerrainSourceError(f"{label} archive contains duplicate member names")
                corrupt_member = archive_file.testzip()
                if corrupt_member is not None:
                    raise TerrainSourceError(
                        f"{label} archive CRC check failed for member '{corrupt_member}'"
                    )
                raster_binding = _verify_archive_member_binding(
                    archive_file,
                    archive_path,
                    record.get("raster_archive_member"),
                    raster_path,
                    f"{label} extracted GeoTIFF",
                )
                sidecar_expected = record.get("metadata_sidecar")
                if not isinstance(sidecar_expected, dict):
                    raise TerrainSourceError(
                        f"{label}.metadata_sidecar must identify the required XML sidecar"
                    )
                sidecar_member = sidecar_expected.get("archive_member")
                sidecar_relative_path = record.get("metadata_sidecar_relative_path")
                sidecar_path = _safe_file_path(
                    source_dir,
                    sidecar_relative_path,
                    f"{label}.metadata_sidecar_relative_path",
                )
                inferred_sidecar_path = raster_path.with_suffix(raster_path.suffix + ".xml")
                if sidecar_path != inferred_sidecar_path:
                    raise TerrainSourceError(
                        f"{label}.metadata_sidecar_relative_path must identify the XML sidecar "
                        f"next to '{raster_path.name}'"
                    )
                if not sidecar_path.is_file():
                    raise TerrainSourceError(
                        f"{label} XML metadata sidecar is missing: '{sidecar_path}'"
                    )
                sidecar_binding = _verify_archive_member_binding(
                    archive_file,
                    archive_path,
                    sidecar_member,
                    sidecar_path,
                    f"{label} XML metadata sidecar",
                )
        except (OSError, zipfile.BadZipFile) as exc:
            raise TerrainSourceError(f"cannot read source archive '{archive_path}': {exc}") from exc

        metadata, sidecar = inspect_raster(raster_path)
        actual = metadata.to_dict()
        for field in (
            "width_pixels",
            "height_pixels",
            "band_count",
            "crs",
            "pixel_interpretation",
            "dtype",
            "transform",
            "bounds_m",
            "resolution_m",
            "nodata",
            "mask_flags",
            "block_shape_pixels",
        ):
            if field in raster_expected and actual[field] != raster_expected[field]:
                raise TerrainSourceError(
                    f"{label} GeoTIFF metadata mismatch for {field}: "
                    f"manifest {raster_expected[field]}, actual {actual[field]}"
                )
        expected_sidecar = record.get("metadata_sidecar")
        if sidecar is None:
            raise TerrainSourceError(f"{label} expected its XML metadata sidecar but none exists")
        sidecar["archive_member"] = sidecar_binding["member"]
        for field in ("filename", "size_bytes", "sha256"):
            if field in expected_sidecar and sidecar.get(field) != expected_sidecar[field]:
                raise TerrainSourceError(
                    f"{label} metadata sidecar mismatch for {field}: "
                    f"manifest {expected_sidecar[field]}, actual {sidecar.get(field)}"
                )
        measured = measure_raster_values(raster_path)
        expected_measurement = raster_expected.get("measured_full_tile")
        if isinstance(expected_measurement, dict):
            for field, expected_value in expected_measurement.items():
                actual_value = measured.get(field)
                if isinstance(expected_value, (int, float)) and isinstance(
                    actual_value, (int, float)
                ):
                    matches = isclose(
                        float(actual_value), float(expected_value), rel_tol=0, abs_tol=1e-9
                    )
                else:
                    matches = actual_value == expected_value
                if not matches:
                    raise TerrainSourceError(
                        f"{label} GeoTIFF measured value mismatch for {field}: "
                        f"manifest {expected_value}, actual {actual_value}"
                    )
        verified.append(
            {
                "tile_name": record.get("tile_name"),
                "download_url": record.get("download_url"),
                "download_date": record.get("download_date"),
                "archive": {
                    "filename": archive_path.name,
                    "size_bytes": archive_path.stat().st_size,
                    "sha256": sha256_file(archive_path),
                    "members": actual_members,
                    "raster_member": raster_binding,
                    "metadata_sidecar_member": sidecar_binding,
                },
                "raster": actual,
                "measured_full_tile": measured,
                "metadata_sidecar": sidecar,
            }
        )
    return raw, verified


def discover_rasters(source_dir: Path) -> list[Path]:
    """Find supported GeoTIFF inputs in a source directory in stable order."""
    if not source_dir.is_dir():
        raise TerrainSourceError(f"source directory does not exist: '{source_dir}'")
    paths = sorted(
        path
        for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".tif", ".tiff"}
    )
    if not paths:
        raise TerrainSourceError(
            f"no GeoTIFF source files found under '{source_dir}'; download the required EA tiles "
            "using the instructions in docs/data-sources.md"
        )
    return paths
