from __future__ import annotations

import copy
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
from torquay_pipeline.building_heights import HeightPolicy, resolve_building_height
from torquay_pipeline.buildings import BuildingImportResult
from torquay_pipeline.config import load_aoi_config
from torquay_pipeline.coordinates import pinned_transformer

REPO_ROOT = Path(__file__).resolve().parents[2]


def _fixture_result():
    _to_bng, to_bng_info = pinned_transformer(4326, 27700)
    _to_wgs, to_wgs_info = pinned_transformer(27700, 4326)
    polygon = {
        "exteriorXZ": [[-2.0, -3.0], [2.0, -3.0], [2.0, 3.0], [-2.0, 3.0], [-2.0, -3.0]],
        "interiorRingsXZ": [],
    }
    feature = {
        "id": "osm:way:101",
        "source": {
            "dataset": "Geofabrik Devon OpenStreetMap extract",
            "objectType": "way",
            "osmId": 101,
            "version": 2,
            "timestamp": None,
        },
        "geometry": {"type": "MultiPolygon", "polygons": [polygon]},
        "heightM": 8.0,
        "heightMethod": "estimated_default",
        "heightConfidence": "visual_default_estimate",
        "heightProvenance": {
            "heightM": 8.0,
            "method": "estimated_default",
            "confidence": "visual_default_estimate",
            "rawHeight": None,
            "parsedHeightM": None,
            "parsedUnit": None,
            "rawLevels": None,
            "clamp": None,
            "fallbackReason": "no usable height or building:levels tag",
        },
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
            "aoiId": "torquay-poc-001",
            "selectionStatus": "selected_pending_coverage",
            "coverageStatus": "not_checked",
            "acquisitionBufferM": 50.0,
            "minimumClippedAreaM2": 1.0,
            "source": {
                "filename": "devon-test.osm.pbf",
                "size_bytes": len(b"test source"),
                "sha256": "a" * 64,
                "md5": "b" * 32,
                "pbf_header": {"replication_timestamp": "2026-01-01T00:00:00Z"},
            },
            "coordinateOperation": {
                "axisOrder": "longitude-latitude for geographic input; easting-northing for BNG",
                "wgs84ToBng": to_bng_info.as_dict(),
                "bngToWgs84": to_wgs_info.as_dict(),
            },
            "heightPolicy": {
                "version": 1,
                "levelsToMetres": 3.0,
                "defaultHeightM": 8.0,
                "minimumHeightM": 1.0,
                "maximumHeightM": 150.0,
                "precedence": ["height", "building:levels", "configured_default"],
                "taggedHeightConfidence": "tagged_but_unverified",
                "defaultConfidence": "visual_default_estimate",
            },
            "geometryPolicy": {
                "version": 1,
                "acquisitionBufferM": 50.0,
                "minimumClippedAreaM2": 1.0,
                "coordinateQuantizationM": 0.001,
                "exteriorWinding": "counter-clockwise in local XZ coordinates",
                "interiorWinding": "clockwise in local XZ coordinates",
                "invalidGeometryPolicy": "reject without automatic repair",
                "duplicatePolicy": (
                    "prefer relation then stable identity; collapse exact canonical geometry"
                ),
                "nearOverlapPolicy": "report; do not merge",
            },
            "counts": {"exported_buildings": 1, "relation_area_assembly_failures": 0},
            "quality": {
                "rejectedGeometryCount": 0,
                "candidateGeometryRejectionCount": 0,
                "rejectedGeometrySamples": [],
                "relationAreaAssemblyFailures": 0,
                "unsupportedBuildingRelations": [],
                "areaGeometryErrorScope": "Synthetic test fixture; no source area errors.",
                "exactDuplicateConflicts": [],
                "nearOverlapCount": 0,
                "nearOverlapSamples": [],
                "heightMethodCounts": {"estimated_default": 1},
                "heightClampCounts": {},
                "taggedHeightsAreUnverified": True,
            },
            "summary": {
                "aoiAreaM2": 1000000.0,
                "buildingFootprintAreaM2": 24.0,
                "footprintAreaPerAoiKm2": 0.000024,
                "densityInterpretation": (
                    "Mapped OSM coverage only; this is not a completeness estimate."
                ),
                "minimumHeightM": 8.0,
                "maximumHeightM": 8.0,
                "meanHeightM": 8.0,
            },
            "mapComparisonCandidates": [],
        },
    )


def _write_fixtures(tmp_path, monkeypatch):
    source_path = tmp_path / "devon-test.osm.pbf"
    source_path.write_bytes(b"test source")
    terrain_path = tmp_path / "terrain"
    terrain_path.mkdir()
    heightfield = b"\0\0\0\0" * (501 * 501)
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
            "path": "heightfield.f32",
            "columns": 501,
            "rows": 501,
            "spacingM": 2.0,
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


def _dump_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )


def _build_fixture_package(tmp_path, monkeypatch):
    source_path, source_manifest_path, terrain_path = _write_fixtures(tmp_path, monkeypatch)
    aoi = load_aoi_config(REPO_ROOT / "config/aoi.torquay-1km.json")
    package = tmp_path / "package"
    build_building_package(
        _fixture_result(),
        aoi,
        source_path,
        source_manifest_path,
        terrain_path,
        REPO_ROOT / "docs/milestones/artifacts/AOI-1km-selection/aoi-selection.geojson",
        package,
        tmp_path / "qa.json",
        tmp_path / "preview.png",
        tmp_path / "intermediate.geojson",
    )
    return package, aoi, terrain_path, source_path, source_manifest_path


def _set_resolved_height(feature: dict, raw_height: str) -> None:
    feature["tags"]["height"] = raw_height
    resolved = resolve_building_height(feature["tags"], HeightPolicy())
    feature["heightM"] = resolved.height_m
    feature["heightMethod"] = resolved.method
    feature["heightConfidence"] = resolved.confidence
    feature["heightProvenance"] = resolved.as_dict()


def _refresh_building_package_integrity(package: Path) -> None:
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    data = json.loads((package / "buildings.json").read_text(encoding="utf-8"))
    content = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False).encode() + b"\n"
    (package / "buildings.json").write_bytes(content)
    manifest["buildings"]["byteLength"] = len(content)
    manifest["buildings"]["sha256"] = hashlib.sha256(content).hexdigest()
    qa = json.loads((package / "qa.json").read_text(encoding="utf-8"))
    qa["package"]["buildingsByteLength"] = len(content)
    qa["package"]["buildingsSha256"] = manifest["buildings"]["sha256"]
    qa_content = json.dumps(qa, indent=2, ensure_ascii=False, allow_nan=False).encode() + b"\n"
    (package / "qa.json").write_bytes(qa_content)
    manifest["qaReport"]["byteLength"] = len(qa_content)
    manifest["qaReport"]["sha256"] = hashlib.sha256(qa_content).hexdigest()
    _dump_json(package / "manifest.json", manifest)


def test_building_package_hashes_actual_payload_and_is_deterministic(tmp_path, monkeypatch):
    source_path, source_manifest_path, terrain_path = _write_fixtures(tmp_path, monkeypatch)
    aoi = load_aoi_config(REPO_ROOT / "config/aoi.torquay-1km.json")
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
        "aoi_geojson_path": REPO_ROOT
        / "docs/milestones/artifacts/AOI-1km-selection/aoi-selection.geojson",
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
            package / "qa.json",
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
            package / "qa.json",
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
    validated = validate_building_package(
        package,
        expected_aoi=aoi,
        expected_aoi_ring=export_module._load_aoi_ring(
            REPO_ROOT / "docs/milestones/artifacts/AOI-1km-selection/aoi-selection.geojson"
        ),
        terrain_package_path=terrain_path,
        source_path=source_path,
        source_manifest_path=source_manifest_path,
    )
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
        load_aoi_config(REPO_ROOT / "config/aoi.torquay-1km.json"),
        source_path,
        source_manifest_path,
        terrain_path,
        REPO_ROOT / "docs/milestones/artifacts/AOI-1km-selection/aoi-selection.geojson",
        package,
        tmp_path / "qa.json",
        tmp_path / "preview.png",
        tmp_path / "intermediate.geojson",
    )
    with (package / "buildings.json").open("ab") as stream:
        stream.write(b"corrupt")
    with pytest.raises(BuildingExportError, match="byteLength"):
        validate_building_package(
            package,
            expected_aoi=load_aoi_config(REPO_ROOT / "config/aoi.torquay-1km.json"),
            expected_aoi_ring=export_module._load_aoi_ring(
                REPO_ROOT / "docs/milestones/artifacts/AOI-1km-selection/aoi-selection.geojson"
            ),
            terrain_package_path=terrain_path,
            source_path=source_path,
            source_manifest_path=source_manifest_path,
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing-height-provenance", "heightProvenance"),
        ("boolean-height", "heightM"),
        ("null-geometry", "geometry"),
        ("boolean-height-source-id", "osmId"),
        ("boolean-geometry-coordinate", "finite JSON number"),
        ("inconsistent-height-confidence", "heightConfidence does not match"),
        ("unhashable-height-method", "heightMethod"),
        ("unhashable-parsed-unit", "heightProvenance.parsedUnit differs"),
        ("unhashable-source-type", "source.objectType"),
        ("tag-inconsistent-default", "heightMethod does not match"),
        ("tagged-height-reported-as-eight", "heightM does not match"),
        ("parsed-height-only-mismatch", "heightProvenance.parsedHeightM"),
    ],
)
def test_validator_rejects_adversarial_feature_copies(tmp_path, monkeypatch, mutation, message):
    package, aoi, terrain, source, source_manifest = _build_fixture_package(tmp_path, monkeypatch)
    data = json.loads((package / "buildings.json").read_text(encoding="utf-8"))
    feature = data["buildings"][0]
    if mutation == "missing-height-provenance":
        feature.pop("heightProvenance")
    elif mutation == "boolean-height":
        feature["heightM"] = True
    elif mutation == "null-geometry":
        feature["geometry"] = None
    elif mutation == "boolean-height-source-id":
        feature["source"]["osmId"] = True
    elif mutation == "boolean-geometry-coordinate":
        feature["geometry"]["polygons"][0]["exteriorXZ"][0][0] = True
    elif mutation == "unhashable-height-method":
        feature["heightMethod"] = []
    elif mutation == "unhashable-parsed-unit":
        feature["heightProvenance"]["parsedUnit"] = []
    elif mutation == "unhashable-source-type":
        feature["source"]["objectType"] = []
    elif mutation == "tag-inconsistent-default":
        feature["tags"]["height"] = "100"
        feature["heightProvenance"]["rawHeight"] = "100"
    elif mutation == "tagged-height-reported-as-eight":
        feature["tags"]["height"] = "100"
        feature["heightMethod"] = "osm_height"
        feature["heightConfidence"] = "tagged_but_unverified"
        feature["heightProvenance"].update(
            {
                "method": "osm_height",
                "confidence": "tagged_but_unverified",
                "rawHeight": "100",
                "parsedHeightM": 8.0,
                "parsedUnit": "metres",
                "fallbackReason": None,
            }
        )
    elif mutation == "parsed-height-only-mismatch":
        _set_resolved_height(feature, "100")
        feature["heightProvenance"]["parsedHeightM"] = 8.0
    else:
        feature["heightConfidence"] = "estimated_from_tagged_levels"
    _dump_json(package / "buildings.json", data)
    _refresh_building_package_integrity(package)
    with pytest.raises(BuildingExportError, match=message):
        validate_building_package(
            package,
            expected_aoi=aoi,
            expected_aoi_ring=export_module._load_aoi_ring(
                REPO_ROOT / "docs/milestones/artifacts/AOI-1km-selection/aoi-selection.geojson"
            ),
            terrain_package_path=terrain,
            source_path=source,
            source_manifest_path=source_manifest,
        )


def test_finite_number_rejects_integer_outside_float_range():
    with pytest.raises(BuildingExportError, match="finite JSON number"):
        export_module._finite_number(10**1000, "fixture.number")


@pytest.mark.parametrize(
    ("distribution", "message"),
    [
        ("method", "qa.quality.heightMethodCounts"),
        ("clamp", "qa.quality.heightClampCounts"),
    ],
)
def test_validator_recomputes_height_distributions_from_features(
    tmp_path, monkeypatch, distribution, message
):
    package, aoi, terrain, source, source_manifest = _build_fixture_package(tmp_path, monkeypatch)
    data = json.loads((package / "buildings.json").read_text(encoding="utf-8"))
    qa = json.loads((package / "qa.json").read_text(encoding="utf-8"))
    feature = data["buildings"][0]
    _set_resolved_height(feature, "100" if distribution == "method" else "200")
    if distribution == "clamp":
        qa["quality"]["heightMethodCounts"] = {"osm_height": 1}
    resolved_height = feature["heightM"]
    qa["summary"].update(
        {
            "minimumHeightM": resolved_height,
            "maximumHeightM": resolved_height,
            "meanHeightM": resolved_height,
        }
    )
    _dump_json(package / "buildings.json", data)
    _dump_json(package / "qa.json", qa)
    _refresh_building_package_integrity(package)
    with pytest.raises(BuildingExportError, match=message):
        validate_building_package(
            package,
            expected_aoi=aoi,
            expected_aoi_ring=export_module._load_aoi_ring(
                REPO_ROOT / "docs/milestones/artifacts/AOI-1km-selection/aoi-selection.geojson"
            ),
            terrain_package_path=terrain,
            source_path=source,
            source_manifest_path=source_manifest,
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("terrain-origin", "terrain identity"),
        ("unrelated-ring", "approved GeoJSON ring"),
        ("aoi-bounds", "approved project AOI"),
        ("terrain-hash", "terrain identity"),
        ("boolean-policy-number", "finite JSON number"),
        ("missing-qa", "qa.json"),
        ("missing-policy", "policies.geometry.coordinateQuantizationM"),
        ("missing-coordinate-operation", "coordinateOperation"),
    ],
)
def test_validator_binds_manifest_aoi_terrain_policies_and_qa(
    tmp_path, monkeypatch, mutation, message
):
    package, aoi, terrain, source, source_manifest = _build_fixture_package(tmp_path, monkeypatch)
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    if mutation == "terrain-origin":
        manifest["terrainIdentity"]["origin"]["eastingM"] += 1000
    elif mutation == "unrelated-ring":
        manifest["aoi"]["boundaryWgs84"]["ring"] = [
            [-1.0, 50.0],
            [-0.9, 50.0],
            [-0.9, 50.1],
            [-1.0, 50.1],
            [-1.0, 50.0],
        ]
    elif mutation == "aoi-bounds":
        manifest["aoi"]["boundsM"][0] += 1000
    elif mutation == "terrain-hash":
        manifest["terrainIdentity"]["heightfieldSha256"] = "0" * 64
    elif mutation == "boolean-policy-number":
        manifest["policies"]["height"]["defaultHeightM"] = True
    elif mutation == "missing-qa":
        manifest["qaReport"]["path"] = "../missing.json"
    elif mutation == "missing-policy":
        manifest["policies"]["geometry"].pop("coordinateQuantizationM")
    else:
        manifest.pop("coordinateOperation")
    _dump_json(package / "manifest.json", manifest)
    with pytest.raises(BuildingExportError, match=message):
        validate_building_package(
            package,
            expected_aoi=aoi,
            expected_aoi_ring=export_module._load_aoi_ring(
                REPO_ROOT / "docs/milestones/artifacts/AOI-1km-selection/aoi-selection.geojson"
            ),
            terrain_package_path=terrain,
            source_path=source,
            source_manifest_path=source_manifest,
        )


def test_package_validator_detects_modified_local_terrain_origin(tmp_path, monkeypatch):
    source_path, source_manifest_path, terrain_path = _write_fixtures(tmp_path, monkeypatch)
    terrain_manifest_path = terrain_path / "manifest.json"
    terrain_manifest = json.loads(terrain_manifest_path.read_text(encoding="utf-8"))
    terrain_manifest["origin"]["eastingM"] += 1000
    _dump_json(terrain_manifest_path, terrain_manifest)
    aoi = load_aoi_config(REPO_ROOT / "config/aoi.torquay-1km.json")
    with pytest.raises(BuildingExportError, match="origin eastingM"):
        build_building_package(
            _fixture_result(),
            aoi,
            source_path,
            source_manifest_path,
            terrain_path,
            REPO_ROOT / "docs/milestones/artifacts/AOI-1km-selection/aoi-selection.geojson",
            tmp_path / "package",
            tmp_path / "qa.json",
            tmp_path / "preview.png",
            tmp_path / "intermediate.geojson",
        )


def test_package_validator_detects_corrupted_package_qa(tmp_path, monkeypatch):
    package, aoi, terrain, source, source_manifest = _build_fixture_package(tmp_path, monkeypatch)
    with (package / "qa.json").open("ab") as stream:
        stream.write(b"corrupt")
    with pytest.raises(BuildingExportError, match="qa.json byteLength"):
        validate_building_package(
            package,
            expected_aoi=aoi,
            expected_aoi_ring=export_module._load_aoi_ring(
                REPO_ROOT / "docs/milestones/artifacts/AOI-1km-selection/aoi-selection.geojson"
            ),
            terrain_package_path=terrain,
            source_path=source,
            source_manifest_path=source_manifest,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-height-provenance",
        "null-geometry",
        "boolean-height",
        "boolean-policy-number",
        "tag-inconsistent-default",
        "tagged-height-reported-as-eight",
        "parsed-height-only-mismatch",
    ],
)
def test_build_side_rejects_mutated_feature_before_publishing(tmp_path, monkeypatch, mutation):
    source_path, source_manifest_path, terrain_path = _write_fixtures(tmp_path, monkeypatch)
    result = _fixture_result()
    result = copy.deepcopy(result)
    feature = result.buildings[0]
    if mutation == "missing-height-provenance":
        feature.pop("heightProvenance")
        expected_message = "heightProvenance"
    elif mutation == "null-geometry":
        feature["geometry"] = None
        expected_message = "geometry"
    elif mutation == "boolean-policy-number":
        result.qa["heightPolicy"]["defaultHeightM"] = True
        expected_message = "finite JSON number"
    elif mutation == "tag-inconsistent-default":
        feature["tags"]["height"] = "100"
        feature["heightProvenance"]["rawHeight"] = "100"
        expected_message = "heightMethod does not match"
    elif mutation == "tagged-height-reported-as-eight":
        feature["tags"]["height"] = "100"
        feature["heightMethod"] = "osm_height"
        feature["heightConfidence"] = "tagged_but_unverified"
        feature["heightProvenance"].update(
            {
                "method": "osm_height",
                "confidence": "tagged_but_unverified",
                "rawHeight": "100",
                "parsedHeightM": 8.0,
                "parsedUnit": "metres",
                "fallbackReason": None,
            }
        )
        expected_message = "heightM does not match"
    elif mutation == "parsed-height-only-mismatch":
        _set_resolved_height(feature, "100")
        feature["heightProvenance"]["parsedHeightM"] = 8.0
        expected_message = "heightProvenance.parsedHeightM"
    else:
        feature["heightM"] = True
        expected_message = "heightM"
    aoi = load_aoi_config(REPO_ROOT / "config/aoi.torquay-1km.json")
    package = tmp_path / "package"
    with pytest.raises(BuildingExportError, match=expected_message):
        build_building_package(
            result,
            aoi,
            source_path,
            source_manifest_path,
            terrain_path,
            REPO_ROOT / "docs/milestones/artifacts/AOI-1km-selection/aoi-selection.geojson",
            package,
            tmp_path / "qa.json",
            tmp_path / "preview.png",
            tmp_path / "intermediate.geojson",
        )
    assert not package.exists()


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
