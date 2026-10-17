import hashlib
import json
from pathlib import Path

import pytest

import torquay_pipeline.building_sources as building_source_module
from torquay_pipeline.building_sources import (
    BuildingSourceError,
    inspect_building_source,
    verify_building_source,
)

HEADER = {
    "format": "PBF",
    "generator": "test/libosmium",
    "replication_timestamp": "2026-01-01T00:00:00Z",
    "replication_sequence_number": "1",
    "bounds_wgs84_lon_lat": [-4.0, 50.0, -3.0, 51.0],
}


def _write_manifest(path: Path, source: Path, content: bytes) -> None:
    manifest = {
        "osm": {
            "sources": [
                {
                    "filename": source.name,
                    "size_bytes": len(content),
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "publisher_md5": hashlib.md5(content, usedforsecurity=False).hexdigest(),
                    "pbf_header": HEADER,
                }
            ]
        }
    }
    path.write_text(json.dumps(manifest), encoding="utf-8")


def test_source_integrity_and_pbf_header_are_checked(tmp_path, monkeypatch):
    source = tmp_path / "devon-test.osm.pbf"
    content = b"offline PBF fixture bytes"
    source.write_bytes(content)
    manifest_path = tmp_path / "source-manifest.json"
    _write_manifest(manifest_path, source, content)
    monkeypatch.setattr(building_source_module, "read_pbf_header", lambda _path: HEADER)
    observed = inspect_building_source(source)
    assert observed["size_bytes"] == len(content)
    assert observed["pbf_header"]["replication_timestamp"] == HEADER["replication_timestamp"]
    assert verify_building_source(source, manifest_path) == observed


def test_source_verification_rejects_modified_bytes(tmp_path, monkeypatch):
    source_copy = tmp_path / "devon-test.osm.pbf"
    content = b"offline PBF fixture bytes"
    source_copy.write_bytes(content)
    manifest_path = tmp_path / "source-manifest.json"
    _write_manifest(manifest_path, source_copy, content)
    source_copy.write_bytes(content + b"damage")
    monkeypatch.setattr(building_source_module, "read_pbf_header", lambda _path: HEADER)
    with pytest.raises(BuildingSourceError, match="size mismatch"):
        verify_building_source(source_copy, manifest_path)


def test_publisher_header_mismatch_is_rejected(tmp_path, monkeypatch):
    source = tmp_path / "devon-test.osm.pbf"
    content = b"offline PBF fixture bytes"
    source.write_bytes(content)
    manifest_path = tmp_path / "source-manifest.json"
    _write_manifest(manifest_path, source, content)
    changed = dict(HEADER, replication_timestamp="2026-01-02T00:00:00Z")
    monkeypatch.setattr(building_source_module, "read_pbf_header", lambda _path: changed)
    with pytest.raises(BuildingSourceError, match="replication_timestamp"):
        verify_building_source(source, manifest_path)
