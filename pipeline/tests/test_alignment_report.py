"""Focused checks for alignment outcome, attribution and evidence binding."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from torquay_pipeline.alignment_report import (
    AOI_BOUNDS_M,
    OS_ATTRIBUTION,
    OS_LICENCE_URL,
    AlignmentReportError,
    _load_config,
    validate_alignment_report,
)

SOURCE_CREDITS = [
    "Contains Environment Agency copyright and/or database right 2022 (DTM)",
    f"{OS_ATTRIBUTION} (OS OpenMap Local)",
    "© OpenStreetMap contributors; extract provided by Geofabrik GmbH",
]


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _report_fixture(root: Path) -> dict:
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
    browser_path = root / "docs" / "milestones" / "artifacts" / "browser.json"
    browser_path.parent.mkdir(parents=True)
    browser_path.write_bytes(browser_bytes)

    spots = []
    for spot_id, status in (
        ("ne-second-main", "pass"),
        ("nw-audley-pencorse", "pass"),
        ("sw-teignmouth-snowberry", "inconclusive"),
    ):
        evidence = []
        for kind in ("reference", "overlay", "package", "scene"):
            relative = f"docs/milestones/screenshots/{spot_id}-{kind}.png"
            image = (spot_id + kind).encode()
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(image)
            evidence.append(
                {"kind": kind, "path": relative, "byteLength": len(image), "sha256": _sha(image)}
            )
        spots.append(
            {
                "id": spot_id,
                "debugContextId": spot_id,
                "alignmentStatus": status,
                "manualObservation": {
                    "summary": "Visual comparison reviewed; outcome retained explicitly.",
                    "reviewedBy": "test reviewer",
                },
                "browserSession": {
                    "expectedContextId": spot_id,
                    "sourceCredits": SOURCE_CREDITS.copy(),
                },
                "evidence": evidence,
            }
        )
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
        "sourceIndependence": "independent_publisher_os_openmap_local",
        "source": {
            "sourceId": "os-openmap-local-apr-2026-sx",
            "publisher": "Ordnance Survey",
            "product": "OS OpenMap–Local GeoTIFF Full Colour",
            "edition": "April 2026",
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
        "aoi": {
            "boundsM": list(AOI_BOUNDS_M),
            "selectionStatus": "selected_pending_coverage",
            "coverageStatus": "not_checked",
        },
        "spots": spots,
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
