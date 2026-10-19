"""Focused checks for alignment outcome, attribution and evidence binding."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from torquay_pipeline.alignment_report import (
    AOI_BOUNDS_M,
    AXIS_MAPPING,
    OS_ATTRIBUTION,
    OS_LICENCE_URL,
    RASTER_REGISTRATION,
    AlignmentReportError,
    _load_config,
    _markdown_report,
    _package_summary,
    _validated_control,
    _write_validated_alignment_report,
    load_local_packages,
    validate_alignment_report,
)
from torquay_pipeline.coordinates import pinned_transformer

SOURCE_CREDITS = [
    "Contains Environment Agency copyright and/or database right 2022 (DTM)",
    f"{OS_ATTRIBUTION} (OS OpenMap Local)",
    "© OpenStreetMap contributors; extract provided by Geofabrik GmbH",
]


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _report_fixture(root: Path) -> dict:
    project = Path(__file__).resolve().parents[2]
    config = json.loads((project / "config/alignment.torquay.json").read_text(encoding="utf-8"))
    config["spots"][2]["alignment_status"] = "inconclusive"
    config_path = root / "config" / "alignment.torquay.json"
    config_path.parent.mkdir(parents=True)
    config_bytes = json.dumps(config, sort_keys=True).encode()
    config_path.write_bytes(config_bytes)

    manifest = {
        "sources": [
            {
                "sourceId": "os-openmap-local-apr-2026-sx",
                "product": "OS OpenMap–Local GeoTIFF Full Colour",
                "edition": "April 2026",
                "licence": {
                    "name": "Open Government Licence v3.0",
                    "url": OS_LICENCE_URL,
                    "requiredAttribution": OS_ATTRIBUTION,
                },
            }
        ]
    }
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode()
    manifest_path = root / "data" / "comparison-source-manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_bytes(manifest_bytes)
    browser_bytes = b'{"consoleErrors":[],"pageErrors":[],"failedRequests":[]}'

    terrain_dir = root / "public" / "worlds" / "torquay-poc-001"
    road_dir = terrain_dir / "roads"
    building_dir = terrain_dir / "buildings"
    for directory in (terrain_dir, road_dir, building_dir):
        directory.mkdir(parents=True, exist_ok=True)
    origin = {"eastingM": 291108.9018176432, "northingM": 65353.48350844931, "elevationM": 47.5}
    heightfield_bytes = b"fixture-heightfield"
    (terrain_dir / "heightfield.f32").write_bytes(heightfield_bytes)
    terrain_manifest = {
        "id": "torquay-poc-001",
        "worldType": "real",
        "origin": origin,
        "heightfield": {"path": "heightfield.f32", "sha256": _sha(heightfield_bytes)},
    }
    (terrain_dir / "manifest.json").write_text(json.dumps(terrain_manifest), encoding="utf-8")

    operation = pinned_transformer(4326, 27700)[1].as_dict()
    aoi_record = {
        "boundsM": list(AOI_BOUNDS_M),
        "selectionStatus": "selected_pending_coverage",
        "coverageStatus": "not_checked",
    }
    road_features = []
    for spot in config["spots"]:
        control = spot["control"]
        x, z = control["local_xz_m"]
        for way_id in control["osm_way_ids"]:
            road_features.append(
                {
                    "id": f"way/{way_id}",
                    "source": {"nodeIds": [control["osm_node_id"]]},
                    "centerlinePartsXZ": [
                        [
                            [x, z],
                            [x + 1.0, z + 1.0],
                        ]
                    ],
                }
            )
    road_payload = {"features": road_features}
    road_payload_bytes = json.dumps(road_payload).encode()
    road_qa_bytes = b"{}"
    (road_dir / "roads.json").write_bytes(road_payload_bytes)
    (road_dir / "qa.json").write_bytes(road_qa_bytes)
    terrain_identity = {
        "worldId": "torquay-poc-001",
        "heightfieldSha256": _sha(heightfield_bytes),
        "origin": origin,
    }
    road_manifest = {
        "worldId": "torquay-poc-001",
        "sourceCrs": "EPSG:27700",
        "aoi": aoi_record,
        "terrainIdentity": terrain_identity,
        "coordinateOperation": {"wgs84ToBng": operation},
        "assets": {
            "roads": {
                "path": "roads.json",
                "byteLength": len(road_payload_bytes),
                "sha256": _sha(road_payload_bytes),
            },
            "qa": {
                "path": "qa.json",
                "byteLength": len(road_qa_bytes),
                "sha256": _sha(road_qa_bytes),
            },
        },
    }
    (road_dir / "manifest.json").write_text(json.dumps(road_manifest), encoding="utf-8")

    building_ids = {
        f"osm:way:{spot['original_context']['building_way_id']}"
        for spot in config["spots"]
        if isinstance(spot.get("original_context", {}).get("building_way_id"), int)
    }
    building_payload = {"buildings": [{"id": item} for item in sorted(building_ids)]}
    building_payload_bytes = json.dumps(building_payload).encode()
    building_qa_bytes = b"{}"
    (building_dir / "buildings.json").write_bytes(building_payload_bytes)
    (building_dir / "qa.json").write_bytes(building_qa_bytes)
    building_manifest = {
        "worldId": "torquay-poc-001",
        "sourceCrs": "EPSG:27700",
        "aoi": aoi_record,
        "terrainIdentity": terrain_identity,
        "buildings": {
            "path": "buildings.json",
            "byteLength": len(building_payload_bytes),
            "sha256": _sha(building_payload_bytes),
        },
        "qaReport": {
            "path": "qa.json",
            "byteLength": len(building_qa_bytes),
            "sha256": _sha(building_qa_bytes),
        },
    }
    (building_dir / "manifest.json").write_text(json.dumps(building_manifest), encoding="utf-8")

    packages = load_local_packages(terrain_dir, road_dir, building_dir)

    spots = []
    browser_records = []
    for source_spot in config["spots"]:
        spot_id = source_spot["id"]
        status = source_spot["alignment_status"]
        evidence = []
        scene_path = None
        for kind in ("reference", "overlay", "package", "scene"):
            relative = f"docs/milestones/screenshots/{spot_id}-{kind}.png"
            image = (spot_id + kind).encode()
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(image)
            evidence.append(
                {"kind": kind, "path": relative, "byteLength": len(image), "sha256": _sha(image)}
            )
            if kind == "scene":
                scene_path = path
        control = source_spot["control"]
        target = control["local_xz_m"]
        sampled_ground = 40.0
        camera = {
            "x": target[0] + 40.0,
            "y": sampled_ground + 35.0,
            "z": target[1],
            "bearing": 45.0,
            "pitch": -35.0,
        }
        raw_record = {
            "screenshotPath": str(scene_path.resolve()),
            "camera": camera,
            "sampledGroundHeightM": sampled_ground,
            "eyeHeightAboveTerrainM": 35.0,
            "targetLocalXZMetres": target,
            "cameraOffsetM": 40.0,
            "poseMethod": "development-only QA camera pose setter; no camera travel is implied",
            "expectedContextId": spot_id,
            "runtime": {
                "renderer": "fixture renderer",
                "canvas": {"cssWidth": 1440, "cssHeight": 900, "width": 1440, "height": 900},
            },
            "browserName": "chromium",
            "browserVersion": "test",
            "viewport": {"width": 1440, "height": 900, "devicePixelRatio": 1.5},
        }
        browser_records.append(raw_record)
        raw_observation = source_spot.get("manual_observation")
        report_observation = (
            {
                "summary": raw_observation.get("summary"),
                "reviewedBy": raw_observation.get("reviewed_by"),
                "method": raw_observation.get("method"),
                "confidence": raw_observation.get("confidence"),
                "referencePointBngM": raw_observation.get("reference_point_bng_m"),
                "screeningAssessment": raw_observation.get("screening_assessment"),
            }
            if isinstance(raw_observation, dict)
            else None
        )
        spots.append(
            {
                "id": spot_id,
                "label": source_spot["label"],
                "selectionStatus": source_spot["selection_status"],
                "selectionRationale": source_spot["selection_rationale"],
                "debugContextId": source_spot["debug_context_id"],
                "alignmentStatus": status,
                "manualObservation": report_observation,
                "control": {
                    "featureRole": control["feature_role"],
                    "osmNodeId": control["osm_node_id"],
                    "osmWayIds": control["osm_way_ids"],
                    "roadNames": control["road_names"],
                    "localXZMetres": control["local_xz_m"],
                    "bngENMetres": control["bng_e_n_m"],
                    "wgs84LonLat": control["wgs84_lon_lat"],
                },
                "comparisonWindow": {
                    "bngBoundsM": source_spot["window_bounds_bng_m"],
                    "actualRasterPixelEdgeBoundsM": source_spot["window_bounds_bng_m"],
                    "widthPixels": 200,
                    "heightPixels": 200,
                    "tileNames": ["SX96NW.tif"],
                },
                "browserSession": {
                    "expectedContextId": spot_id,
                    "cameraPoseLocalMetres": camera,
                    "sampledGroundHeightM": sampled_ground,
                    "eyeHeightAboveTerrainM": 35.0,
                    "targetLocalXZMetres": target,
                    "cameraOffsetM": 40.0,
                    "poseMethod": raw_record["poseMethod"],
                    "viewport": raw_record["viewport"],
                    "renderer": raw_record["runtime"]["renderer"],
                    "canvas": raw_record["runtime"]["canvas"],
                    "sourceCredits": SOURCE_CREDITS.copy(),
                },
                "evidence": evidence,
            }
        )
    browser_path = root / "docs" / "milestones" / "artifacts" / "browser.json"
    browser_path.parent.mkdir(parents=True)
    browser_bytes = json.dumps(
        {"consoleErrors": [], "pageErrors": [], "failedRequests": [], "evidence": browser_records}
    ).encode()
    browser_path.write_bytes(browser_bytes)
    prior_id = "sw-st-vincent-chapel"
    prior_evidence = []
    for kind in ("reference", "overlay", "package", "scene"):
        relative = f"docs/milestones/screenshots/prior-{prior_id}-{kind}.png"
        image = ("prior" + kind).encode()
        path = root / relative
        path.write_bytes(image)
        prior_evidence.append(
            {"kind": kind, "path": relative, "byteLength": len(image), "sha256": _sha(image)}
        )
    prior_record = {
        "id": prior_id,
        "label": "SW · St Vincent’s Road / Chapel Court candidate",
        "alignmentStatus": "inconclusive",
        "manualObservation": {
            "summary": "OS labels and OSM names do not support confident correspondence.",
            "reviewedBy": "test reviewer",
        },
        "browserSession": {"expectedContextId": prior_id},
        "evidence": prior_evidence,
    }
    prior_payload = {
        "formatVersion": 1,
        "candidateRole": "inconclusive prior candidate; not counted among active comparison spots",
        "record": prior_record,
    }
    prior_bytes = json.dumps(prior_payload, sort_keys=True).encode()
    prior_path = root / "docs" / "milestones" / "artifacts" / "prior-sw.json"
    prior_path.write_bytes(prior_bytes)
    return {
        "formatVersion": 1,
        "reportId": config["report_id"],
        "sourceIndependence": "independent_publisher_os_openmap_local",
        "source": {
            "sourceId": "os-openmap-local-apr-2026-sx",
            "publisher": "Ordnance Survey",
            "product": "OS OpenMap–Local GeoTIFF Full Colour",
            "edition": "April 2026",
            "archiveFilename": "fixture.zip",
            "archiveBytes": 1,
            "archiveSha256": "a" * 64,
            "licence": {
                "name": "Open Government Licence v3.0",
                "url": OS_LICENCE_URL,
                "requiredAttribution": OS_ATTRIBUTION,
            },
        },
        "sourceManifest": {
            "path": "data/comparison-source-manifest.json",
            "sha256": _sha(manifest_bytes),
        },
        "browserSessionEvidence": {
            "path": "docs/milestones/artifacts/browser.json",
            "byteLength": len(browser_bytes),
            "sha256": _sha(browser_bytes),
        },
        "alignmentConfig": {
            "path": "config/alignment.torquay.json",
            "sha256": _sha(config_bytes),
        },
        "aoi": {
            "boundsM": list(AOI_BOUNDS_M),
            "selectionStatus": "selected_pending_coverage",
            "coverageStatus": "not_checked",
        },
        "spots": spots,
        "coordinateReference": {
            "crs": "EPSG:27700",
            "aoi": {
                "boundsM": list(AOI_BOUNDS_M),
                "selectionStatus": "selected_pending_coverage",
                "coverageStatus": "not_checked",
            },
            "axisMapping": AXIS_MAPPING,
            "rasterRegistration": RASTER_REGISTRATION,
            "localCoordinateOperation": operation,
            "uncertaintyComponents": ["Screening comparison only."],
        },
        "localPackages": {
            **_package_summary(packages),
            "packagePaths": {
                "terrain": "public/worlds/torquay-poc-001",
                "roads": "public/worlds/torquay-poc-001/roads",
                "buildings": "public/worlds/torquay-poc-001/buildings",
            },
        },
        "priorCandidates": [
            {
                "path": "docs/milestones/artifacts/prior-sw.json",
                "byteLength": len(prior_bytes),
                "sha256": _sha(prior_bytes),
                "record": prior_record,
            }
        ],
        "issueStatus": "in_progress",
        "alignmentGateStatus": "inconclusive",
        "combinedM5Status": "pending",
    }


def test_report_keeps_inconclusive_spot_from_passing_alignment_gate(tmp_path: Path) -> None:
    report = _report_fixture(tmp_path)

    result = validate_alignment_report(report, tmp_path)

    assert result["spotCount"] == 3
    assert result["evidenceFileCount"] == 12
    assert result["spotStatuses"] == ["inconclusive", "pass"]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda report: report["spots"][2].update(alignmentStatus=None), "alignmentStatus"),
        (
            lambda report: report["spots"][1].update(debugContextId="nw-baron-lindfield"),
            "debugContextId",
        ),
        (
            lambda report: report["spots"][0]["browserSession"].update(
                expectedContextId="wrong-spot"
            ),
            "context id",
        ),
        (
            lambda report: report["spots"][0]["browserSession"].update(sourceCredits=[]),
            "attribution",
        ),
        (lambda report: report["source"]["licence"].update(requiredAttribution=""), "attribution"),
        (lambda report: report["aoi"].update(boundsM=[float("nan"), 0, 1, 1]), "pending AOI"),
        (lambda report: report["source"].update(publisher=None), "source.publisher"),
    ],
)
def test_report_rejects_malformed_identity_attribution_and_aoi(
    tmp_path: Path, mutate, message: str
) -> None:
    report = _report_fixture(tmp_path)
    mutate(report)

    with pytest.raises(AlignmentReportError, match=message):
        validate_alignment_report(report, tmp_path)


def test_report_rejects_stale_evidence_integrity(tmp_path: Path) -> None:
    report = _report_fixture(tmp_path)
    evidence = report["spots"][0]["evidence"][0]
    (tmp_path / evidence["path"]).write_bytes(b"changed")

    with pytest.raises(AlignmentReportError, match="hash/length mismatch"):
        validate_alignment_report(report, tmp_path)


def test_report_rejects_stale_source_manifest_integrity(tmp_path: Path) -> None:
    report = _report_fixture(tmp_path)
    manifest_path = tmp_path / report["sourceManifest"]["path"]
    manifest_bytes = manifest_path.read_bytes()
    manifest_path.write_bytes(b"x" * len(manifest_bytes))

    with pytest.raises(AlignmentReportError, match="sourceManifest.*SHA-256"):
        validate_alignment_report(report, tmp_path)


def test_report_rejects_stale_browser_session_integrity(tmp_path: Path) -> None:
    report = _report_fixture(tmp_path)
    evidence_path = tmp_path / report["browserSessionEvidence"]["path"]
    evidence_bytes = evidence_path.read_bytes()
    evidence_path.write_bytes(b"x" * len(evidence_bytes))

    with pytest.raises(AlignmentReportError, match="browser session evidence SHA-256"):
        validate_alignment_report(report, tmp_path)


def test_report_rejects_duplicate_active_spot_ids(tmp_path: Path) -> None:
    report = _report_fixture(tmp_path)
    report["spots"][2]["id"] = report["spots"][0]["id"]

    with pytest.raises(AlignmentReportError, match="id must be nonempty and unique"):
        validate_alignment_report(report, tmp_path)


def test_report_rejects_stale_prior_candidate_record(tmp_path: Path) -> None:
    report = _report_fixture(tmp_path)
    prior = report["priorCandidates"][0]
    prior_path = tmp_path / prior["path"]
    prior_bytes = prior_path.read_bytes()
    prior_path.write_bytes(b"x" * len(prior_bytes))

    with pytest.raises(AlignmentReportError, match="prior candidate record SHA-256"):
        validate_alignment_report(report, tmp_path)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda report: report["spots"][0].pop("control"), "control is missing"),
        (
            lambda report: report["spots"][0]["control"].update(bngENMetres=[0.0, 0.0]),
            "control does not match",
        ),
        (lambda report: report.pop("coordinateReference"), "coordinateReference"),
        (
            lambda report: report["localPackages"]["roads"].update(payloadSha256="0" * 64),
            "localPackages hashes/counts",
        ),
        (
            lambda report: report["spots"][0]["browserSession"]["cameraPoseLocalMetres"].update(
                x=999999.0
            ),
            "pose/target",
        ),
    ],
)
def test_report_rejects_unbound_control_package_and_pose_mutations(
    tmp_path: Path, mutate, message: str
) -> None:
    report = _report_fixture(tmp_path)
    mutate(report)

    with pytest.raises(AlignmentReportError, match=message):
        validate_alignment_report(report, tmp_path)


def test_validated_control_rejects_wgs84_zero_zero(tmp_path: Path) -> None:
    _report_fixture(tmp_path)
    config, _ = _load_config(tmp_path / "config/alignment.torquay.json")
    packages = load_local_packages(
        tmp_path / "public/worlds/torquay-poc-001",
        tmp_path / "public/worlds/torquay-poc-001/roads",
        tmp_path / "public/worlds/torquay-poc-001/buildings",
    )
    config["spots"][0]["control"]["wgs84_lon_lat"] = [0.0, 0.0]

    with pytest.raises(AlignmentReportError, match="WGS84 coordinates do not match"):
        _validated_control(config, packages)


def test_report_rejects_raw_browser_camera_far_from_registered_target(tmp_path: Path) -> None:
    report = _report_fixture(tmp_path)
    descriptor = report["browserSessionEvidence"]
    browser_path = tmp_path / descriptor["path"]
    browser = json.loads(browser_path.read_text(encoding="utf-8"))
    browser["evidence"][0]["camera"]["x"] = 999999.0
    browser_bytes = json.dumps(browser).encode()
    browser_path.write_bytes(browser_bytes)
    descriptor["byteLength"] = len(browser_bytes)
    descriptor["sha256"] = _sha(browser_bytes)
    report["spots"][0]["browserSession"]["cameraPoseLocalMetres"]["x"] = 999999.0

    with pytest.raises(AlignmentReportError, match="pose/target"):
        validate_alignment_report(report, tmp_path)


def test_report_markdown_links_are_relative_to_milestone_directory(tmp_path: Path) -> None:
    report = _report_fixture(tmp_path)

    markdown = _markdown_report(report)

    assert "(screenshots/ne-second-main-reference.png)" in markdown
    assert "(artifacts/TVW-012-prior-sw-inconclusive.json)" in markdown
    assert "(docs/milestones/screenshots/" not in markdown


def test_failed_report_validation_preserves_existing_panels_report_and_markdown(
    tmp_path: Path,
) -> None:
    report = _report_fixture(tmp_path)
    panel = report["spots"][0]["evidence"][0]
    panel_path = tmp_path / panel["path"]
    original_panel = panel_path.read_bytes()
    panel_bytes = b"candidate-regenerated-panel"
    panel["byteLength"] = len(panel_bytes)
    panel["sha256"] = _sha(panel_bytes)
    report.pop("coordinateReference")
    report_path = tmp_path / "docs/milestones/artifacts/TVW-012-alignment.json"
    markdown_path = tmp_path / "docs/milestones/TVW-012.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(b"existing report")
    markdown_path.write_bytes(b"existing markdown")

    with pytest.raises(AlignmentReportError, match="coordinateReference"):
        _write_validated_alignment_report(report, {panel_path: panel_bytes}, tmp_path)

    assert panel_path.read_bytes() == original_panel
    assert report_path.read_bytes() == b"existing report"
    assert markdown_path.read_bytes() == b"existing markdown"


def test_report_does_not_let_inconclusive_be_marked_as_pass(tmp_path: Path) -> None:
    report = _report_fixture(tmp_path)
    report["alignmentGateStatus"] = "pass"

    with pytest.raises(AlignmentReportError, match="per-spot outcomes"):
        validate_alignment_report(report, tmp_path)


def test_alignment_config_requires_active_debug_context_to_match_spot(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    config = json.loads(
        (project_root / "config/alignment.torquay.json").read_text(encoding="utf-8")
    )
    config["spots"][1]["debug_context_id"] = "nw-baron-lindfield"
    config_path = tmp_path / "alignment.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(AlignmentReportError, match="debug_context_id"):
        _load_config(config_path)


def test_alignment_config_rejects_null_review_metadata(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[2]
    config = json.loads(
        (project_root / "config/alignment.torquay.json").read_text(encoding="utf-8")
    )
    config["manual_review"]["reviewed_by"] = None
    config_path = tmp_path / "alignment.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(AlignmentReportError, match="manual_review.reviewed_by"):
        _load_config(config_path)
