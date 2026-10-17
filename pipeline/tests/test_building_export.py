from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import torquay_pipeline.building_export as export_module
from torquay_pipeline.building_export import (
    BuildingExportError,
    build_building_package,
    validate_building_package,
)
from torquay_pipeline.buildings import BuildingImportResult
from torquay_pipeline.config import load_aoi_config

REPO_ROOT = Path(__file__).resolve().parents[2]


def _fixture_result():
    polygon = {
        "exteriorXZ": [[-2.0, -3.0], [2.0, -3.0], [2.0, 3.0], [-2.0, 3.0], [-2.0, -3.0]],
        "interiorRingsXZ": [],
    }
    feature = {
        "id": "osm:way:101",
        "source": {"objectType": "way", "osmId": 101, "version": 2, "timestamp": None},
        "geometry": {"type": "MultiPolygon", "polygons": [polygon]},
        "heightM": 8.0,
        "heightMethod": "estimated_default",
        "heightConfidence": "visual_default_estimate",
        "heightProvenance": {"rawHeight": None, "rawLevels": None, "clamp": None},
        "footprintAreaM2": 24.0,
        "clippedToAoi": False,
        "qualityFlags": [],
        "duplicateReferences": [],
        "tags": {"building": "yes"},
    }
    return BuildingImportResult(
        [feature],
        {"type": "FeatureCollection", "features": []},
        {
            "formatVersion": 1,
            "source": {"filename": "devon-test.osm.pbf", "sha256": "a" * 64, "size_bytes": 1},
            "coordinateOperation": {},
            "counts": {"exported_buildings": 1},
            "quality": {"heightMethodCounts": {"estimated_default": 1}},
            "summary": {
                "buildingFootprintAreaM2": 24.0,
                "footprintAreaPerAoiKm2": 0.000024,
            },
        },
    )


def _write_fixtures(tmp_path, monkeypatch):
    source_path = tmp_path / "devon-test.osm.pbf"
    source_path.write_bytes(b"test source")
    terrain_path = tmp_path / "terrain"
    terrain_path.mkdir()
    heightfield = b"\0\0\0\0"
    (terrain_path / "heightfield.f32").write_bytes(heightfield)
    terrain_manifest = {
        "id": "torquay-poc-001",
        "origin": {
            "eastingM": 291108.9018176432,
            "northingM": 65353.48350844931,
            "elevationM": 47.5,
        },
        "heightfield": {
            "sha256": hashlib.sha256(heightfield).hexdigest(),
            "byteLength": len(heightfield),
        },
        "aoi": {
            "boundsM": [
                290608.9018176432,
                64853.48350844931,
                291608.9018176432,
                65853.48350844931,
            ],
            "selectionStatus": "selected_pending_coverage",
            "coverageStatus": "not_checked",
        },
        "provenance": {"verticalReference": "Ordnance Survey Newlyn"},
    }
    (terrain_path / "manifest.json").write_text(json.dumps(terrain_manifest), encoding="utf-8")
    source_manifest = {
        "osm": {
            "product": {
                "publisher": "OpenStreetMap contributors; extract prepared by Geofabrik",
                "name": "OpenStreetMap regional extract — Devon",
                "download_page_url": "https://download.geofabrik.de/example",
                "licence": "Open Database Licence 1.0 (ODbL)",
                "licence_url": "https://www.openstreetmap.org/copyright",
                "credit": "Geofabrik GmbH",
            },
            "acquisition": {"download_date": "2026-01-01"},
            "sources": [
                {
                    "filename": source_path.name,
                    "download_url": "https://download.geofabrik.de/example/devon.osm.pbf",
                    "publisher_md5": "b" * 32,
                }
            ],
        }
    }
    source_manifest_path = tmp_path / "source-manifest.json"
    source_manifest_path.write_text(json.dumps(source_manifest), encoding="utf-8")
    monkeypatch.setattr(
        export_module,
        "verify_building_source",
        lambda *_args: {
            "filename": source_path.name,
            "size_bytes": source_path.stat().st_size,
            "sha256": "a" * 64,
            "md5": "b" * 32,
            "pbf_header": {"replication_timestamp": "2026-01-01T00:00:00Z"},
        },
    )
    return source_path, source_manifest_path, terrain_path


def test_building_package_hashes_actual_payload_and_is_deterministic(tmp_path, monkeypatch):
    source_path, source_manifest_path, terrain_path = _write_fixtures(tmp_path, monkeypatch)
    aoi = load_aoi_config(REPO_ROOT / "config/aoi.torquay.json")
    package = tmp_path / "package"
    qa_path = tmp_path / "qa.json"
    preview_path = tmp_path / "preview.png"
    intermediate_path = tmp_path / "buffered.geojson"
    kwargs = {
        "result": _fixture_result(),
        "aoi_config": aoi,
        "source_path": source_path,
        "source_manifest_path": source_manifest_path,
        "terrain_package_path": terrain_path,
        "aoi_geojson_path": REPO_ROOT / "docs/aoi-selection.geojson",
        "package_path": package,
        "qa_path": qa_path,
        "preview_path": preview_path,
        "intermediate_path": intermediate_path,
    }
    first = build_building_package(**kwargs)
    before = {
        path.name: path.read_bytes()
        for path in (
            package / "manifest.json",
            package / "buildings.json",
            qa_path,
            preview_path,
            intermediate_path,
        )
    }
    build_building_package(**kwargs)
    after = {
        path.name: path.read_bytes()
        for path in (
            package / "manifest.json",
            package / "buildings.json",
            qa_path,
            preview_path,
            intermediate_path,
        )
    }
    assert before == after
    assert (
        first["manifest"]["aoi"]["boundaryWgs84"]["ring"][0]
        == first["manifest"]["aoi"]["boundaryWgs84"]["ring"][-1]
    )
    validated = validate_building_package(package)
    assert validated["buildingCount"] == 1
    assert (
        first["manifest"]["terrainIdentity"]["heightfieldSha256"]
        == hashlib.sha256((terrain_path / "heightfield.f32").read_bytes()).hexdigest()
    )


def test_building_package_detects_corrupt_payload(tmp_path, monkeypatch):
    source_path, source_manifest_path, terrain_path = _write_fixtures(tmp_path, monkeypatch)
    package = tmp_path / "package"
    build_building_package(
        _fixture_result(),
        load_aoi_config(REPO_ROOT / "config/aoi.torquay.json"),
        source_path,
        source_manifest_path,
        terrain_path,
        REPO_ROOT / "docs/aoi-selection.geojson",
        package,
        tmp_path / "qa.json",
        tmp_path / "preview.png",
        tmp_path / "intermediate.geojson",
    )
    with (package / "buildings.json").open("ab") as stream:
        stream.write(b"corrupt")
    with pytest.raises(BuildingExportError, match="byteLength"):
        validate_building_package(package)


def test_atomic_publish_rolls_back_when_a_later_replace_fails(tmp_path, monkeypatch):
    first = tmp_path / "first.json"
    manifest = tmp_path / "manifest.json"
    first.write_bytes(b"old-first")
    manifest.write_bytes(b"old-manifest")
    real_replace = export_module.os.replace
    replace_count = 0

    def fail_on_fourth_replace(source, target):
        nonlocal replace_count
        replace_count += 1
        if replace_count == 4:
            raise OSError("simulated filesystem failure")
        return real_replace(source, target)

    monkeypatch.setattr(export_module.os, "replace", fail_on_fourth_replace)
    with pytest.raises(OSError, match="simulated"):
        export_module._publish_transaction(
            [(first, b"new-first"), (manifest, b"new-manifest")], manifest
        )
    assert first.read_bytes() == b"old-first"
    assert manifest.read_bytes() == b"old-manifest"
