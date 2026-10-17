"""OSM PBF integrity checks and publisher/source metadata helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import osmium


class BuildingSourceError(ValueError):
    """Raised when a downloaded OSM source is missing, corrupt, or unexpected."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise BuildingSourceError(f"cannot read OSM source '{path}': {exc}") from exc
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    try:
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise BuildingSourceError(f"cannot read OSM source '{path}': {exc}") from exc
    return digest.hexdigest()


def read_pbf_header(path: Path) -> dict[str, Any]:
    """Read the PBF header without scanning its OSM objects."""
    if not path.is_file():
        raise BuildingSourceError(f"OSM PBF source does not exist: {path}")
    if path.stat().st_size <= 0:
        raise BuildingSourceError(f"OSM PBF source is empty: {path}")
    reader: osmium.io.Reader | None = None
    try:
        reader = osmium.io.Reader(str(path))
        header = reader.header()
        bounds = header.box()
        bbox = None
        if bounds.valid():
            bbox = [
                float(bounds.bottom_left.lon),
                float(bounds.bottom_left.lat),
                float(bounds.top_right.lon),
                float(bounds.top_right.lat),
            ]
        return {
            "format": "PBF",
            "generator": header.get("generator") or None,
            "replication_timestamp": header.get("osmosis_replication_timestamp") or None,
            "replication_sequence_number": header.get("osmosis_replication_sequence_number")
            or None,
            "bounds_wgs84_lon_lat": bbox,
        }
    except Exception as exc:
        raise BuildingSourceError(f"cannot read OSM PBF header from '{path}': {exc}") from exc
    finally:
        if reader is not None:
            reader.close()


def inspect_building_source(path: Path) -> dict[str, Any]:
    """Return observed file integrity and PBF-header metadata."""
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise BuildingSourceError(f"cannot stat OSM source '{path}': {exc}") from exc
    return {
        "filename": path.name,
        "size_bytes": size,
        "sha256": sha256_file(path),
        "md5": md5_file(path),
        "pbf_header": read_pbf_header(path),
    }


def read_source_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise BuildingSourceError(f"cannot read source manifest '{path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise BuildingSourceError(f"source manifest '{path}' is invalid JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise BuildingSourceError("data/source-manifest.json must be a JSON object")
    return manifest


def verify_building_source(path: Path, source_manifest_path: Path) -> dict[str, Any]:
    """Check OSM bytes against the separately namespaced source manifest entry."""
    manifest = read_source_manifest(source_manifest_path)
    osm_record = manifest.get("osm")
    if not isinstance(osm_record, dict):
        raise BuildingSourceError("source manifest has no 'osm' namespace for building sources")
    sources = osm_record.get("sources")
    if not isinstance(sources, list) or len(sources) != 1 or not isinstance(sources[0], dict):
        raise BuildingSourceError("source manifest osm.sources must contain exactly one PBF record")
    expected = sources[0]
    if expected.get("filename") != path.name:
        raise BuildingSourceError(
            f"OSM source filename '{path.name}' does not match manifest filename "
            f"'{expected.get('filename')}'; select the recorded dated extract explicitly"
        )
    observed = inspect_building_source(path)
    if observed["size_bytes"] != expected.get("size_bytes"):
        raise BuildingSourceError(
            f"OSM source size mismatch: expected {expected.get('size_bytes')} bytes, "
            f"observed {observed['size_bytes']}"
        )
    if observed["sha256"] != expected.get("sha256"):
        raise BuildingSourceError(
            f"OSM source SHA-256 mismatch for '{path.name}'; restore the recorded Geofabrik file"
        )
    expected_md5 = expected.get("publisher_md5")
    if expected_md5 and observed["md5"] != expected_md5:
        raise BuildingSourceError(
            f"OSM source MD5 mismatch for '{path.name}' against the publisher checksum"
        )
    expected_header = expected.get("pbf_header")
    if isinstance(expected_header, dict):
        for key in ("generator", "replication_timestamp", "bounds_wgs84_lon_lat"):
            if observed["pbf_header"].get(key) != expected_header.get(key):
                raise BuildingSourceError(
                    f"OSM source PBF header field '{key}' differs from the source manifest"
                )
    return observed
