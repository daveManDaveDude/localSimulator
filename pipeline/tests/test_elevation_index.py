"""Offline tests for the official EA time-stamped DTM resolution-index assessment."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlencode

import pytest
from shapely.geometry import Polygon, mapping

from torquay_pipeline.config import load_aoi_config
from torquay_pipeline.elevation_index import ElevationIndexError, assess_ea_resolution_index

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "aoi.torquay.json"
INDEX_PATH = ROOT / "data/elevation-index/ea-dtm-time-stamped-2km-2026-10-20.geojson"
SOURCE_PATH = ROOT / "data/elevation-index/ea-dtm-time-stamped-2km-2026-10-20.source.json"
TIMESTAMP = "2026-10-20T12:00:00Z"
WFS_ENDPOINT = "https://environment.data.gov.uk/spatialdata/survey-index-files/wfs"


def _small_config():
    config = load_aoi_config(CONFIG_PATH)
    return replace(
        config,
        width_m=10.0,
        height_m=10.0,
        center_bng_m=(5.0, 5.0),
        bbox_m=(0.0, 0.0, 10.0, 10.0),
    )


def _feature(identifier: str, geometry: Polygon, resolution: float = 0.5) -> dict:
    properties = {"resolution": resolution}
    if resolution == 0.5:
        properties.update(
            {
                "dtm_name": f"DTM_{identifier}",
                "ostilename": "SX0000",
                "year": 2010,
                "sdflown": "2010-04-04T00:00:00Z",
                "edflown": "2010-04-04T00:00:00Z",
                "transform": "OSTN'02",
                "geoid": "OSGM'02",
            }
        )
    return {
        "type": "Feature",
        "id": identifier,
        "geometry": mapping(geometry),
        "properties": properties,
    }


def _write_fixture(
    directory: Path,
    config,
    features: list[dict],
    *,
    allow_nan: bool = False,
) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    index_path = directory / "index.geojson"
    metadata_path = directory / "source.json"
    index_data = {
        "type": "FeatureCollection",
        "numberMatched": len(features),
        "numberReturned": len(features),
        "totalFeatures": len(features),
        "timeStamp": TIMESTAMP,
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::27700"}},
        "features": features,
    }
    index_bytes = (
        json.dumps(index_data, separators=(",", ":"), allow_nan=allow_nan) + "\n"
    ).encode()
    index_path.write_bytes(index_bytes)

    metadata = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    metadata["retrievedDate"] = TIMESTAMP[:10]
    metadata["query"]["bboxM"] = list(config.bbox_m)
    metadata["query"]["startIndex"] = 0
    expected_bbox = ",".join(str(value) for value in config.bbox_m)
    expected_bbox += ",urn:ogc:def:crs:EPSG::27700"
    query_parameters = [
        ("service", "WFS"),
        ("version", "2.0.0"),
        ("request", "GetFeature"),
        ("typeNames", metadata["featureType"]),
        ("bbox", expected_bbox),
        ("outputFormat", "application/json"),
        ("count", "1000"),
    ]
    request_url = f"{WFS_ENDPOINT}?{urlencode(query_parameters)}"
    metadata["requestUrl"] = request_url
    metadata["response"].update(
        {
            "file": index_path.name,
            "sizeBytes": len(index_bytes),
            "sha256": hashlib.sha256(index_bytes).hexdigest(),
            "numberMatched": len(features),
            "numberReturned": len(features),
            "crs": "urn:ogc:def:crs:EPSG::27700",
            "timeStamp": TIMESTAMP,
            "httpStatus": 200,
            "contentType": "application/json;charset=UTF-8",
            "finalUrl": request_url,
        }
    )
    metadata["retrievedAtUtc"] = TIMESTAMP
    metadata["pagination"] = {
        "mode": "single_page_fail_if_truncated",
        "pageCount": 1,
        "startIndex": 0,
        "pageSize": 1000,
        "complete": True,
        "numberMatched": len(features),
        "numberReturned": len(features),
    }
    metadata["capturePolicy"] = {"timeoutSeconds": 30, "maximumResponseBytes": 16 * 1024 * 1024}
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return index_path, metadata_path


def _write_mutated_fixture_metadata(index_path: Path, metadata_path: Path, metadata: dict) -> None:
    index_bytes = index_path.read_bytes()
    metadata["response"]["sizeBytes"] = len(index_bytes)
    metadata["response"]["sha256"] = hashlib.sha256(index_bytes).hexdigest()
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def test_actual_official_index_has_50_features_and_partial_half_metre_footprint() -> None:
    report = assess_ea_resolution_index(load_aoi_config(CONFIG_PATH), INDEX_PATH, SOURCE_PATH)

    assert report["aoi"]["boundsM"] == [
        290108.9018176432,
        64353.48350844931,
        292108.9018176432,
        66353.48350844931,
    ]
    assert report["aoi"]["areaM2"] == 4_000_000
    assert report["aoi"]["selectionStatus"] == "selected_pending_coverage"
    assert report["aoi"]["overallCoverageStatus"] == "not_checked"
    assert report["indexSummary"]["matchedFeatureCount"] == 50
    assert report["indexSummary"]["resolutionFeatureCounts"] == {"0.5": 4, "1": 42, "2": 4}
    footprint = report["halfMetreIndexFootprint"]
    assert footprint["status"] == "partial_metadata_footprint"
    assert footprint["featureCount"] == 4
    assert footprint["coveredUnionAreaM2"] == pytest.approx(397628.69577878254, abs=1e-6)
    assert footprint["aoiFraction"] == pytest.approx(0.09940717394469563, abs=1e-12)
    assert footprint["surveyDateRanges"] == [["2010-04-04T00:00:00Z", "2010-04-04T00:00:00Z"]]
    assert footprint["coordinateOperations"] == ["OSTN'02"]
    assert footprint["verticalReferences"] == ["OSGM'02"]
    assert report["publisherProductMetadata"]["verticalReferenceClaim"] == "Ordnance Survey Newlyn"
    assert report["source"]["response"]["sha256"] == (
        "cda7ce43af709ac2177cf000b404525d59476426ab22ad8a7404498d39a71de4"
    )
    assert "not raster-pixel coverage" in " ".join(report["limits"])
    assert "not assessed" in " ".join(report["limits"])


def test_assessment_is_deterministic_and_unions_overlap_and_holes_once(tmp_path: Path) -> None:
    config = _small_config()
    first = Polygon(
        [(0, 0), (6, 0), (6, 10), (0, 10), (0, 0)],
        holes=[[(2, 2), (4, 2), (4, 4), (2, 4), (2, 2)]],
    )
    second = Polygon([(4, 0), (10, 0), (10, 10), (4, 10), (4, 0)])
    features = [
        _feature("first", first),
        _feature("second", second),
        _feature("one-metre", Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]), 1),
        _feature("two-metre", Polygon([(9, 9), (10, 9), (10, 10), (9, 10), (9, 9)]), 2),
    ]
    index, source = _write_fixture(tmp_path, config, features)

    first_report = assess_ea_resolution_index(config, index, source)
    second_report = assess_ea_resolution_index(config, index, source)

    assert first_report == second_report
    assert first_report["indexSummary"]["resolutionFeatureCounts"] == {"0.5": 2, "1": 1, "2": 1}
    assert first_report["halfMetreIndexFootprint"]["coveredUnionAreaM2"] == pytest.approx(96)
    assert first_report["halfMetreIndexFootprint"]["aoiFraction"] == pytest.approx(0.96)


def test_survey_dates_accept_naive_date_and_timezone_aware_datetime_and_normalize_utc(
    tmp_path: Path,
) -> None:
    config = _small_config()
    feature = _feature(
        "mixed-timezones",
        Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]),
    )
    feature["properties"]["sdflown"] = "2010-04-04"
    feature["properties"]["edflown"] = "2010-04-04T23:30:00-01:00"
    index, source = _write_fixture(tmp_path, config, [feature])

    report = assess_ea_resolution_index(config, index, source)

    assert report["halfMetreIndexFootprint"]["surveyDateRanges"] == [
        ["2010-04-04T00:00:00Z", "2010-04-05T00:30:00Z"]
    ]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.pop("publisherMetadataUrl"), "publisherMetadataUrl"),
        (lambda value: value.update(aoiProfile="historical_1km"), "aoiProfile"),
        (lambda value: value.update(metadataUrl="https://example.com/catalogue"), "metadataUrl"),
        (lambda value: value.update(license="other"), "license"),
        (lambda value: value.update(attribution="other"), "attribution"),
        (lambda value: value["query"].update(bboxM=[-1, 0, 9, 10]), "bboxM does not match"),
        (lambda value: value.update(catalogueUpdatedDate="not-a-date"), "catalogueUpdatedDate"),
        (lambda value: value["response"].update(timeStamp="not-a-timestamp"), "timeStamp"),
        (lambda value: value["response"].update(httpStatus=500), "httpStatus"),
        (lambda value: value.update(formatVersion=1.0), "formatVersion"),
        (lambda value: value["query"].update(count=1000.0), "count must be integer"),
        (lambda value: value["query"].update(startIndex=1), "startIndex must be integer 0"),
        (lambda value: value.pop("pagination"), "pagination"),
        (lambda value: value["pagination"].update(complete=False), "one complete page"),
        (lambda value: value.pop("capturePolicy"), "capturePolicy"),
        (lambda value: value.update(retrievedAtUtc="bad-time"), "retrievedAtUtc"),
        (lambda value: value["response"].update(sizeBytes=1.0), "byte length"),
        (lambda value: value["response"].update(sha256="0" * 64), "SHA-256"),
        (lambda value: value["response"].update(file="..\\outside.geojson"), "local filename"),
        (lambda value: value["response"].update(crs="EPSG:4326"), "response CRS"),
        (
            lambda value: value.update(productResolutionOptionsM=[0.25, 0.5, 1, 2, True]),
            "finite number",
        ),
    ],
)
def test_rejects_inconsistent_or_incomplete_source_metadata(
    tmp_path: Path, mutation, message: str
) -> None:
    feature = _feature("one", Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]))
    index, source = _write_fixture(tmp_path, _small_config(), [feature])
    metadata = json.loads(source.read_text(encoding="utf-8"))
    mutation(metadata)
    source.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    with pytest.raises(ElevationIndexError, match=message):
        assess_ea_resolution_index(_small_config(), index, source)


def test_rejects_request_url_that_does_not_encode_the_configured_aoi(tmp_path: Path) -> None:
    config = _small_config()
    feature = _feature("one", Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]))
    index, source = _write_fixture(tmp_path, config, [feature])
    metadata = json.loads(source.read_text(encoding="utf-8"))
    mutated_url = metadata["requestUrl"].replace("10.0%2C10.0", "9.0%2C10.0")
    metadata["requestUrl"] = mutated_url
    metadata["response"]["finalUrl"] = mutated_url
    source.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    with pytest.raises(ElevationIndexError, match="requestUrl parameters do not match"):
        assess_ea_resolution_index(config, index, source)


@pytest.mark.parametrize(
    "mutate_index",
    [
        lambda value: value.update(crs={"type": "name", "properties": {"name": "EPSG:4326"}}),
        lambda value: value.update(numberMatched=999),
        lambda value: value.update(numberReturned=999),
        lambda value: value.update(totalFeatures=999),
        lambda value: value.update(timeStamp="2026-10-20T12:00:01Z"),
        lambda value: value["features"][0]["properties"].update(resolution=True),
        lambda value: value["features"][0].update(type="NotFeature"),
        lambda value: value["features"][0].update(geometry=None),
    ],
)
def test_rejects_malformed_index_snapshot_after_integrity_refresh(
    tmp_path: Path, mutate_index
) -> None:
    config = _small_config()
    feature = _feature("one", Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]))
    index, source = _write_fixture(tmp_path, config, [feature])
    index_data = json.loads(index.read_text(encoding="utf-8"))
    mutate_index(index_data)
    index.write_text(json.dumps(index_data, separators=(",", ":")) + "\n", encoding="utf-8")
    metadata = json.loads(source.read_text(encoding="utf-8"))
    _write_mutated_fixture_metadata(index, source, metadata)

    with pytest.raises(ElevationIndexError):
        assess_ea_resolution_index(config, index, source)


def test_rejects_hash_mismatch_without_mutating_snapshot(tmp_path: Path) -> None:
    config = _small_config()
    index, source = _write_fixture(
        tmp_path,
        config,
        [_feature("one", Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]))],
    )
    before = index.read_bytes()
    index.write_bytes(before + b" ")

    with pytest.raises(ElevationIndexError, match="byte length"):
        assess_ea_resolution_index(config, index, source)


def test_records_zero_area_boundary_touch_without_counting_it_as_coverage(tmp_path: Path) -> None:
    config = _small_config()
    touching = Polygon([(10, 0), (11, 0), (11, 10), (10, 10), (10, 0)])
    index, source = _write_fixture(tmp_path, config, [_feature("touching", touching)])

    report = assess_ea_resolution_index(config, index, source)

    assert report["halfMetreIndexFootprint"]["featureCount"] == 1
    assert report["halfMetreIndexFootprint"]["features"][0]["aoiIntersectionAreaM2"] == 0
    assert report["halfMetreIndexFootprint"]["coveredUnionAreaM2"] == 0


def test_rejects_nonfinite_geometry_coordinates(tmp_path: Path) -> None:
    config = _small_config()
    feature = _feature("infinite", Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]))
    feature["geometry"] = json.loads(json.dumps(feature["geometry"]))
    feature["geometry"]["coordinates"][0][1][0] = float("inf")
    index, source = _write_fixture(tmp_path, config, [feature], allow_nan=True)
    index_data = json.loads(index.read_text(encoding="utf-8"))
    index_data["features"][0] = feature
    index.write_text(json.dumps(index_data, allow_nan=True), encoding="utf-8")
    metadata = json.loads(source.read_text(encoding="utf-8"))
    _write_mutated_fixture_metadata(index, source, metadata)

    with pytest.raises(ElevationIndexError, match="coordinates must be finite"):
        assess_ea_resolution_index(config, index, source)


def test_cli_writes_index_assessment_without_changing_overall_aoi_status(tmp_path: Path) -> None:
    from torquay_pipeline.cli import main

    report_path = tmp_path / "resolution-report.json"
    assert (
        main(
            [
                "assess-resolution-index",
                "--config",
                str(CONFIG_PATH),
                "--index",
                str(INDEX_PATH),
                "--source-metadata",
                str(SOURCE_PATH),
                "--report",
                str(report_path),
            ]
        )
        == 0
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["halfMetreIndexFootprint"]["status"] == "partial_metadata_footprint"
    assert report["aoi"]["selectionStatus"] == "selected_pending_coverage"
    assert report["aoi"]["overallCoverageStatus"] == "not_checked"


class _FakeHttpResponse:
    def __init__(self, body: bytes, request_url: str):
        self.body = body
        self.status = 200
        self.headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Content-Length": str(len(body)),
        }
        self.request_url = request_url

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def geturl(self):
        return self.request_url

    def read(self, limit: int) -> bytes:
        return self.body[:limit]


def test_explicit_capture_saves_raw_wfs_response_and_offline_verifiable_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import torquay_pipeline.elevation_index as module

    raw_bytes = INDEX_PATH.read_bytes()
    config = load_aoi_config(CONFIG_PATH)
    observed = {}

    def fake_urlopen(request, timeout):
        observed["url"] = request.full_url
        observed["headers"] = request.header_items()
        observed["timeout"] = timeout
        return _FakeHttpResponse(raw_bytes, request.full_url)

    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    output = tmp_path / "snapshot"
    output.mkdir()
    index_path = output / "raw.geojson"
    source_path = output / "raw.source.json"

    metadata = module.capture_ea_resolution_index(config, index_path, source_path)
    assessment = assess_ea_resolution_index(config, index_path, source_path)

    assert index_path.read_bytes() == raw_bytes
    assert metadata["query"]["count"] == 1000
    assert metadata["query"]["startIndex"] == 0
    assert metadata["pagination"]["mode"] == "single_page_fail_if_truncated"
    assert metadata["pagination"]["complete"] is True
    assert metadata["capturePolicy"] == {
        "timeoutSeconds": 30,
        "maximumResponseBytes": 16 * 1024 * 1024,
    }
    assert metadata["response"]["numberMatched"] == 50
    assert assessment["halfMetreIndexFootprint"]["aoiPercent"] == pytest.approx(9.940717394469563)
    assert observed["timeout"] == 30
    assert "count=1000" in observed["url"]
    assert "startIndex" not in observed["url"]  # WFS default is the explicitly recorded 0.


def test_capture_cli_uses_current_profile_and_writes_under_explicit_output_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    import torquay_pipeline.elevation_index as module
    from torquay_pipeline.cli import main

    raw_bytes = INDEX_PATH.read_bytes()
    observed: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        observed["url"] = request.full_url
        observed["timeout"] = timeout
        return _FakeHttpResponse(raw_bytes, request.full_url)

    monkeypatch.setattr(module, "urlopen", fake_urlopen)
    output_dir = tmp_path / "captured-index"

    result = main(
        [
            "capture-resolution-index",
            "--config",
            str(CONFIG_PATH),
            "--output-dir",
            str(output_dir),
            "--timeout-seconds",
            "20",
        ]
    )

    assert result == 0
    output = capsys.readouterr().out
    assert "50 of 50 records" in output
    assert "no raster coverage claim" in output
    captured_files = list(output_dir.iterdir())
    assert {path.suffix for path in captured_files} == {".geojson", ".json"}
    assert observed["timeout"] == 20
    assert "bbox=290108.9018176432%2C64353.48350844931" in observed["url"]
    assert "count=1000" in observed["url"]


def test_explicit_capture_rejects_truncated_response_without_writing_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import torquay_pipeline.elevation_index as module

    response = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    response["numberMatched"] = 1001
    body = json.dumps(response).encode("utf-8")
    monkeypatch.setattr(
        module, "urlopen", lambda request, timeout: _FakeHttpResponse(body, request.full_url)
    )
    index_path = tmp_path / "snapshot" / "raw.geojson"
    source_path = index_path.with_name("raw.source.json")

    with pytest.raises(ElevationIndexError, match="truncated.*no partial snapshot"):
        module.capture_ea_resolution_index(load_aoi_config(CONFIG_PATH), index_path, source_path)

    assert not index_path.exists()
    assert not source_path.exists()


def test_explicit_capture_enforces_response_size_limit_and_preserves_existing_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import torquay_pipeline.elevation_index as module

    raw_bytes = INDEX_PATH.read_bytes()
    monkeypatch.setattr(
        module,
        "urlopen",
        lambda request, timeout: _FakeHttpResponse(raw_bytes, request.full_url),
    )
    index_path = tmp_path / "snapshot" / "raw.geojson"
    source_path = index_path.with_name("raw.source.json")

    with pytest.raises(ElevationIndexError, match="capture limit"):
        module.capture_ea_resolution_index(
            load_aoi_config(CONFIG_PATH),
            index_path,
            source_path,
            max_response_bytes=10,
        )
    assert not index_path.exists()
    assert not source_path.exists()

    index_path.parent.mkdir(parents=True)
    index_path.write_bytes(b"preserve")
    with pytest.raises(ElevationIndexError, match="already exist"):
        module.capture_ea_resolution_index(load_aoi_config(CONFIG_PATH), index_path, source_path)
    assert index_path.read_bytes() == b"preserve"
