"""Assess EA time-stamped DTM index footprints without claiming raster coverage."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

from shapely import get_coordinates
from shapely.geometry import box, shape
from shapely.geometry.base import BaseGeometry

from .config import AoiConfig


class ElevationIndexError(ValueError):
    """Raised when an EA elevation index snapshot or provenance is invalid."""


_WFS_ENDPOINT = "https://environment.data.gov.uk/spatialdata/survey-index-files/wfs"
_DATASET_ID = "dbadf364-0192-4bcf-a223-f3d403f08682"
_INDEX_RESOURCE_ID = "dataset-9f0fa3fc-a860-4729-adc9-47fe53f658d0"
_FEATURE_TYPE = f"{_INDEX_RESOURCE_ID}:LIDAR_DTM_Time_Stamped_Extents"
_CATALOGUE_URL = (
    "https://www.data.gov.uk/dataset/8275e71e-1516-42a1-bb0c-4fa73807fe2b/"
    "lidar-dtm-time-stamped-tiles"
)
_PUBLISHER_METADATA_URL = f"https://environment.data.gov.uk/dataset/{_DATASET_ID}"
_PUBLISHED_RESOLUTIONS_M = (0.25, 0.5, 1.0, 2.0)
_REQUEST_LIMIT = 1000
_MAX_RESPONSE_BYTES = 16 * 1024 * 1024
_REQUEST_TIMEOUT_SECONDS = 30


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ElevationIndexError(f"cannot read {label} '{path}': {exc}") from exc
    except UnicodeError as exc:
        raise ElevationIndexError(f"{label} '{path}' is not valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ElevationIndexError(f"{label} '{path}' is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ElevationIndexError(f"{label} must be a JSON object")
    return value


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ElevationIndexError(f"{field} must be a non-empty string")
    return value.strip()


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ElevationIndexError(f"{field} must be a finite number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ElevationIndexError(f"{field} must be a finite number") from exc
    if not math.isfinite(result):
        raise ElevationIndexError(f"{field} must be a finite number")
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ElevationIndexError(f"cannot read index snapshot '{path}': {exc}") from exc
    return digest.hexdigest()


def _validate_source_metadata(
    metadata: dict[str, Any], metadata_path: Path, index_path: Path, config: AoiConfig
) -> dict[str, Any]:
    required = {
        "formatVersion",
        "publisher",
        "product",
        "aoiProfile",
        "datasetId",
        "indexResourceId",
        "featureType",
        "endpoint",
        "service",
        "retrievedDate",
        "retrievedAtUtc",
        "catalogueUpdatedDate",
        "requestUrl",
        "query",
        "response",
        "pagination",
        "capturePolicy",
        "license",
        "licenseUrl",
        "attribution",
        "publisherVerticalReference",
        "publisherVerticalAccuracy",
        "metadataUrl",
        "publisherMetadataUrl",
        "productResolutionOptionsM",
    }
    missing = sorted(required - metadata.keys())
    if missing:
        raise ElevationIndexError(
            f"source metadata is missing required fields: {', '.join(missing)}"
        )
    if type(metadata["formatVersion"]) is not int or metadata["formatVersion"] != 1:
        raise ElevationIndexError("source metadata formatVersion must be integer 1")
    if metadata["publisher"] != "Environment Agency":
        raise ElevationIndexError("source metadata publisher must be Environment Agency")
    if metadata["product"] != "LIDAR DTM Time Stamped Tiles":
        raise ElevationIndexError("source metadata product is not the expected EA DTM index")
    if metadata["aoiProfile"] != config.profile:
        raise ElevationIndexError("source metadata aoiProfile does not match the configured AOI")
    dataset_id = _string(metadata["datasetId"], "source metadata datasetId")
    index_resource_id = _string(metadata["indexResourceId"], "source metadata indexResourceId")
    if dataset_id != _DATASET_ID:
        raise ElevationIndexError(
            "source metadata datasetId is not the EA DTM time-stamped product"
        )
    if index_resource_id != _INDEX_RESOURCE_ID:
        raise ElevationIndexError(
            "source metadata indexResourceId is not the EA DTM time-stamped layer"
        )
    feature_type = _string(metadata["featureType"], "source metadata featureType")
    if feature_type != _FEATURE_TYPE:
        raise ElevationIndexError("source metadata featureType does not match indexResourceId")
    endpoint = _string(metadata["endpoint"], "source metadata endpoint")
    if endpoint != _WFS_ENDPOINT:
        raise ElevationIndexError("source metadata endpoint is not the official EA WFS")
    if metadata["service"] != "OGC Web Feature Service 2.0.0 GetFeature":
        raise ElevationIndexError("source metadata service must identify WFS 2.0.0 GetFeature")
    try:
        retrieved = date.fromisoformat(_string(metadata["retrievedDate"], "retrievedDate"))
    except ValueError as exc:
        raise ElevationIndexError("source metadata retrievedDate must be YYYY-MM-DD") from exc
    if retrieved.isoformat() != metadata["retrievedDate"]:
        raise ElevationIndexError("source metadata retrievedDate must be YYYY-MM-DD")
    retrieved_at = _string(metadata["retrievedAtUtc"], "retrievedAtUtc")
    try:
        retrieved_timestamp = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ElevationIndexError(
            "source metadata retrievedAtUtc must be an ISO timestamp"
        ) from exc
    if (
        retrieved_timestamp.tzinfo is None
        or retrieved_timestamp.utcoffset() is None
        or retrieved_timestamp.date() != retrieved
    ):
        raise ElevationIndexError("source metadata retrievedAtUtc must match retrievedDate")
    try:
        catalogue_updated = date.fromisoformat(
            _string(metadata["catalogueUpdatedDate"], "catalogueUpdatedDate")
        )
    except ValueError as exc:
        raise ElevationIndexError(
            "source metadata catalogueUpdatedDate must be YYYY-MM-DD"
        ) from exc
    if catalogue_updated.isoformat() != metadata["catalogueUpdatedDate"]:
        raise ElevationIndexError("source metadata catalogueUpdatedDate must be YYYY-MM-DD")

    metadata_url = _string(metadata["metadataUrl"], "source metadata metadataUrl")
    if metadata_url != _CATALOGUE_URL:
        raise ElevationIndexError(
            "source metadata metadataUrl must identify the EA DTM product catalogue"
        )
    publisher_metadata_url = _string(
        metadata["publisherMetadataUrl"], "source metadata publisherMetadataUrl"
    )
    if publisher_metadata_url != _PUBLISHER_METADATA_URL:
        raise ElevationIndexError(
            "source metadata publisherMetadataUrl must match the EA dataset ID"
        )
    if metadata["license"] != "Open Government Licence v3.0":
        raise ElevationIndexError(
            "source metadata license must match the publisher's OGL v3.0 terms"
        )
    if (
        metadata["licenseUrl"]
        != "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
    ):
        raise ElevationIndexError(
            "source metadata licenseUrl must identify Open Government Licence v3.0"
        )
    if (
        metadata["attribution"]
        != "© Environment Agency copyright and/or database right 2020. All rights reserved."
    ):
        raise ElevationIndexError(
            "source metadata attribution must match the EA catalogue statement"
        )
    if metadata["publisherVerticalReference"] != "Ordnance Survey Newlyn":
        raise ElevationIndexError(
            "source metadata publisherVerticalReference must match the EA catalogue"
        )
    if metadata["publisherVerticalAccuracy"] != "±15 cm RMSE":
        raise ElevationIndexError(
            "source metadata publisherVerticalAccuracy must match the EA catalogue"
        )

    resolution_options = metadata["productResolutionOptionsM"]
    if not isinstance(resolution_options, list):
        raise ElevationIndexError("source metadata productResolutionOptionsM must be an array")
    parsed_options = tuple(
        _number(value, f"source metadata productResolutionOptionsM[{index}]")
        for index, value in enumerate(resolution_options)
    )
    if parsed_options != _PUBLISHED_RESOLUTIONS_M:
        raise ElevationIndexError(
            "source metadata productResolutionOptionsM does not match the catalogue"
        )

    query = metadata["query"]
    response = metadata["response"]
    if not isinstance(query, dict) or not isinstance(response, dict):
        raise ElevationIndexError("source metadata query and response must be JSON objects")
    if query.get("typeNames") != feature_type:
        raise ElevationIndexError("source metadata query typeNames does not match featureType")
    if query.get("bboxCrs") != "urn:ogc:def:crs:EPSG::27700":
        raise ElevationIndexError("source metadata query bboxCrs must identify EPSG:27700")
    if query.get("outputFormat") != "application/json":
        raise ElevationIndexError("source metadata query outputFormat must be application/json")
    if type(query.get("count")) is not int or query["count"] != 1000:
        raise ElevationIndexError("source metadata query count must be integer 1000")
    if type(query.get("startIndex")) is not int or query["startIndex"] != 0:
        raise ElevationIndexError("source metadata query startIndex must be integer 0")
    query_bounds = query.get("bboxM")
    if not isinstance(query_bounds, list) or len(query_bounds) != 4:
        raise ElevationIndexError("source metadata query bboxM must contain four numbers")
    numeric_bounds = [
        _number(value, f"source metadata query bboxM[{index}]")
        for index, value in enumerate(query_bounds)
    ]
    if tuple(numeric_bounds) != config.bbox_m:
        raise ElevationIndexError("source metadata query bboxM does not match the current AOI")

    request_url = _string(metadata["requestUrl"], "source metadata requestUrl")
    parsed_url = urlsplit(request_url)
    if (parsed_url.scheme, parsed_url.netloc, parsed_url.path) != (
        "https",
        "environment.data.gov.uk",
        "/spatialdata/survey-index-files/wfs",
    ) or parsed_url.fragment:
        raise ElevationIndexError(
            "source metadata requestUrl must target the official EA WFS endpoint"
        )
    try:
        actual_query = parse_qs(parsed_url.query, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise ElevationIndexError(
            "source metadata requestUrl has malformed query parameters"
        ) from exc
    expected_bbox = ",".join(str(value) for value in numeric_bounds) + "," + query["bboxCrs"]
    expected_query = {
        "service": ["WFS"],
        "version": ["2.0.0"],
        "request": ["GetFeature"],
        "typeNames": [feature_type],
        "bbox": [expected_bbox],
        "outputFormat": ["application/json"],
        "count": ["1000"],
    }
    if actual_query != expected_query:
        raise ElevationIndexError(
            "source metadata requestUrl parameters do not match the documented WFS query and AOI"
        )

    snapshot_file = _string(response.get("file"), "source metadata response.file")
    if Path(snapshot_file).name != snapshot_file:
        raise ElevationIndexError("source metadata response.file must be a local filename")
    expected_path = (metadata_path.resolve().parent / snapshot_file).resolve()
    if expected_path != index_path.resolve():
        raise ElevationIndexError(
            "index snapshot path does not match source metadata response.file"
        )
    try:
        size_bytes = index_path.stat().st_size
    except OSError as exc:
        raise ElevationIndexError(f"cannot stat index snapshot '{index_path}': {exc}") from exc
    if type(response.get("sizeBytes")) is not int or response["sizeBytes"] != size_bytes:
        raise ElevationIndexError("index snapshot byte length does not match source metadata")
    expected_hash = _string(response.get("sha256"), "source metadata response.sha256").lower()
    if len(expected_hash) != 64 or any(
        character not in "0123456789abcdef" for character in expected_hash
    ):
        raise ElevationIndexError("source metadata response.sha256 must be a SHA-256 hex digest")
    if _sha256(index_path) != expected_hash:
        raise ElevationIndexError("index snapshot SHA-256 does not match source metadata")
    matched = response.get("numberMatched")
    returned = response.get("numberReturned")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in (matched, returned)):
        raise ElevationIndexError("source metadata response feature counts must be integers")
    if matched != returned:
        raise ElevationIndexError("source metadata response must include all matched features")
    pagination = metadata["pagination"]
    capture_policy = metadata["capturePolicy"]
    if not isinstance(pagination, dict):
        raise ElevationIndexError("source metadata pagination must be an object")
    if not isinstance(capture_policy, dict):
        raise ElevationIndexError("source metadata capturePolicy must be an object")
    timeout = capture_policy.get("timeoutSeconds")
    byte_limit = capture_policy.get("maximumResponseBytes")
    if type(timeout) is not int or not 1 <= timeout <= 120:
        raise ElevationIndexError("source metadata capturePolicy timeoutSeconds is invalid")
    if (
        type(byte_limit) is not int
        or not 1 <= byte_limit <= 64 * 1024 * 1024
        or size_bytes > byte_limit
    ):
        raise ElevationIndexError("source metadata capturePolicy maximumResponseBytes is invalid")
    if (
        pagination.get("mode") != "single_page_fail_if_truncated"
        or type(pagination.get("pageCount")) is not int
        or pagination["pageCount"] != 1
        or type(pagination.get("startIndex")) is not int
        or pagination["startIndex"] != 0
        or type(pagination.get("pageSize")) is not int
        or pagination["pageSize"] != query["count"]
        or pagination.get("complete") is not True
        or pagination.get("numberMatched") != matched
        or pagination.get("numberReturned") != returned
    ):
        raise ElevationIndexError(
            "source metadata pagination must record one complete page matching response counts"
        )
    if matched > query["count"]:
        raise ElevationIndexError(
            "WFS response exceeds the single-page limit; use a bounded paginated capture"
        )
    if response.get("crs") != "urn:ogc:def:crs:EPSG::27700":
        raise ElevationIndexError("source metadata response CRS must be EPSG:27700")
    if type(response.get("httpStatus")) is not int or response["httpStatus"] != 200:
        raise ElevationIndexError("source metadata response httpStatus must be 200")
    content_type = _string(response.get("contentType"), "source metadata response.contentType")
    if not content_type.lower().startswith("application/json"):
        raise ElevationIndexError("source metadata response contentType must be JSON")
    response_timestamp = _string(response.get("timeStamp"), "source metadata response.timeStamp")
    try:
        parsed_timestamp = response_timestamp.replace("Z", "+00:00")
        timestamp = datetime.fromisoformat(parsed_timestamp)
    except ValueError as exc:
        raise ElevationIndexError(
            "source metadata response.timeStamp must be an ISO timestamp"
        ) from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ElevationIndexError("source metadata response.timeStamp must include a timezone")
    if _string(response.get("finalUrl"), "source metadata response.finalUrl") != request_url:
        raise ElevationIndexError("source metadata response.finalUrl does not match requestUrl")
    return metadata


def _atomic_create_pair(
    index_path: Path, source_path: Path, index_bytes: bytes, source_bytes: bytes
) -> None:
    """Create a raw response and its sidecar without replacing existing evidence."""
    if index_path.resolve() == source_path.resolve():
        raise ElevationIndexError("index response and source metadata must use different paths")
    if index_path.parent.resolve() != source_path.parent.resolve():
        raise ElevationIndexError(
            "index response and source metadata must share one output directory"
        )
    if index_path.exists() or source_path.exists():
        raise ElevationIndexError("capture outputs already exist; choose a new snapshot directory")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[Path, Path]] = []
    created: list[Path] = []
    try:
        for destination, content in ((index_path, index_bytes), (source_path, source_bytes)):
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{destination.name}.",
                suffix=".stage",
                dir=destination.parent,
                delete=False,
            ) as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
                staged.append((Path(handle.name), destination))
        for temporary, destination in staged:
            # Hard-link creation is atomic and fails if a destination appeared meanwhile.
            os.link(temporary, destination)
            created.append(destination)
    except OSError as exc:
        for destination in created:
            destination.unlink(missing_ok=True)
        raise ElevationIndexError(f"cannot save captured EA index evidence: {exc}") from exc
    finally:
        for temporary, _destination in staged:
            temporary.unlink(missing_ok=True)


def capture_ea_resolution_index(
    config: AoiConfig,
    index_path: Path,
    source_metadata_path: Path,
    *,
    timeout_seconds: int = _REQUEST_TIMEOUT_SECONDS,
    max_response_bytes: int = _MAX_RESPONSE_BYTES,
) -> dict[str, Any]:
    """Capture one bounded official WFS page; reject truncation rather than hiding it."""
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 120:
        raise ElevationIndexError("capture timeout must be an integer from 1 to 120 seconds")
    if type(max_response_bytes) is not int or not 1 <= max_response_bytes <= 64 * 1024 * 1024:
        raise ElevationIndexError("capture response limit must be from 1 byte to 64 MiB")
    west, south, east, north = config.bbox_m
    bbox = ",".join(str(value) for value in (west, south, east, north))
    bbox += ",urn:ogc:def:crs:EPSG::27700"
    query_pairs = [
        ("service", "WFS"),
        ("version", "2.0.0"),
        ("request", "GetFeature"),
        ("typeNames", _FEATURE_TYPE),
        ("bbox", bbox),
        ("outputFormat", "application/json"),
        ("count", str(_REQUEST_LIMIT)),
    ]
    request_url = f"{_WFS_ENDPOINT}?{urlencode(query_pairs)}"
    request = Request(request_url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status = response.status
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
            declared_length = response.headers.get("Content-Length")
            if declared_length is not None:
                try:
                    parsed_length = int(declared_length)
                except ValueError as exc:
                    raise ElevationIndexError("EA WFS Content-Length is not an integer") from exc
                if parsed_length < 0:
                    raise ElevationIndexError("EA WFS Content-Length must be nonnegative")
                if parsed_length > max_response_bytes:
                    raise ElevationIndexError(
                        f"EA WFS response exceeds the {max_response_bytes}-byte capture limit"
                    )
            raw_bytes = response.read(max_response_bytes + 1)
    except ElevationIndexError:
        raise
    except HTTPError as exc:
        raise ElevationIndexError(f"EA WFS request failed with HTTP {exc.code}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise ElevationIndexError(f"EA WFS request failed: {exc}") from exc
    if status != 200:
        raise ElevationIndexError(f"EA WFS request failed with HTTP {status}")
    if len(raw_bytes) > max_response_bytes:
        raise ElevationIndexError(
            f"EA WFS response exceeds the {max_response_bytes}-byte capture limit"
        )
    if not content_type.lower().startswith("application/json"):
        raise ElevationIndexError(f"EA WFS response is not JSON (Content-Type {content_type!r})")
    if final_url != request_url:
        raise ElevationIndexError("EA WFS redirected the request; final URL differs from query URL")
    try:
        index_data = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ElevationIndexError(f"EA WFS response is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(index_data, dict) or index_data.get("type") != "FeatureCollection":
        raise ElevationIndexError("EA WFS response is not a GeoJSON FeatureCollection")
    features = index_data.get("features")
    matched, returned = index_data.get("numberMatched"), index_data.get("numberReturned")
    if not isinstance(features, list):
        raise ElevationIndexError("EA WFS FeatureCollection features must be an array")
    if any(type(count) is not int or count < 0 for count in (matched, returned)):
        raise ElevationIndexError("EA WFS must return integer numberMatched and numberReturned")
    if returned != len(features):
        raise ElevationIndexError("EA WFS numberReturned does not match the features array")
    if matched != returned:
        raise ElevationIndexError(
            f"EA WFS response is truncated ({returned} of {matched} matched); "
            "no partial snapshot was saved"
        )
    if returned > _REQUEST_LIMIT:
        raise ElevationIndexError("EA WFS response exceeds the requested 1,000-feature page")
    crs = index_data.get("crs")
    if (
        not isinstance(crs, dict)
        or not isinstance(crs.get("properties"), dict)
        or crs["properties"].get("name") != "urn:ogc:def:crs:EPSG::27700"
    ):
        raise ElevationIndexError("EA WFS FeatureCollection CRS must be EPSG:27700")
    time_stamp = _string(index_data.get("timeStamp"), "EA WFS timeStamp")
    try:
        server_timestamp = datetime.fromisoformat(time_stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ElevationIndexError("EA WFS timeStamp must be an ISO timestamp") from exc
    if server_timestamp.tzinfo is None or server_timestamp.utcoffset() is None:
        raise ElevationIndexError("EA WFS timeStamp must include a timezone")
    captured_at = datetime.now(UTC).replace(microsecond=0)
    retrieved_at = captured_at.isoformat().replace("+00:00", "Z")
    retrieved_date = captured_at.date().isoformat()
    index_bytes = raw_bytes
    metadata = {
        "formatVersion": 1,
        "publisher": "Environment Agency",
        "product": "LIDAR DTM Time Stamped Tiles",
        "aoiProfile": config.profile,
        "datasetId": _DATASET_ID,
        "indexResourceId": _INDEX_RESOURCE_ID,
        "featureType": _FEATURE_TYPE,
        "endpoint": _WFS_ENDPOINT,
        "service": "OGC Web Feature Service 2.0.0 GetFeature",
        "retrievedDate": retrieved_date,
        "retrievedAtUtc": retrieved_at,
        "catalogueUpdatedDate": "2026-04-07",
        "publisherMetadataUrl": _PUBLISHER_METADATA_URL,
        "productResolutionOptionsM": list(_PUBLISHED_RESOLUTIONS_M),
        "requestUrl": request_url,
        "query": {
            "typeNames": _FEATURE_TYPE,
            "bboxM": [west, south, east, north],
            "bboxCrs": "urn:ogc:def:crs:EPSG::27700",
            "outputFormat": "application/json",
            "count": _REQUEST_LIMIT,
            "startIndex": 0,
        },
        "pagination": {
            "mode": "single_page_fail_if_truncated",
            "pageCount": 1,
            "startIndex": 0,
            "pageSize": _REQUEST_LIMIT,
            "complete": True,
            "numberMatched": matched,
            "numberReturned": returned,
        },
        "capturePolicy": {
            "timeoutSeconds": timeout_seconds,
            "maximumResponseBytes": max_response_bytes,
        },
        "response": {
            "file": index_path.name,
            "sizeBytes": len(index_bytes),
            "sha256": hashlib.sha256(index_bytes).hexdigest(),
            "numberMatched": matched,
            "numberReturned": returned,
            "crs": "urn:ogc:def:crs:EPSG::27700",
            "timeStamp": time_stamp,
            "httpStatus": status,
            "contentType": content_type,
            "finalUrl": final_url,
        },
        "license": "Open Government Licence v3.0",
        "licenseUrl": "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        "attribution": (
            "© Environment Agency copyright and/or database right 2020. All rights reserved."
        ),
        "publisherVerticalReference": "Ordnance Survey Newlyn",
        "publisherVerticalAccuracy": "±15 cm RMSE",
        "metadataUrl": _CATALOGUE_URL,
    }
    metadata_bytes = (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _atomic_create_pair(index_path, source_metadata_path, index_bytes, metadata_bytes)
    return metadata


def _feature_geometry(feature: dict[str, Any], index: int) -> BaseGeometry:
    geometry_value = feature.get("geometry")
    if not isinstance(geometry_value, dict):
        raise ElevationIndexError(f"index feature {index} geometry must be an object")
    try:
        geometry = shape(geometry_value)
    except Exception as exc:
        raise ElevationIndexError(f"index feature {index} has invalid geometry: {exc}") from exc
    coordinates = get_coordinates(geometry)
    if any(not math.isfinite(float(value)) for coordinate in coordinates for value in coordinate):
        raise ElevationIndexError(f"index feature {index} geometry coordinates must be finite")
    if (
        geometry.is_empty
        or not geometry.is_valid
        or not math.isfinite(geometry.area)
        or geometry.area <= 0
    ):
        raise ElevationIndexError(
            f"index feature {index} geometry must be valid and have positive area"
        )
    if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ElevationIndexError(f"index feature {index} geometry must be Polygon or MultiPolygon")
    return geometry


def assess_ea_resolution_index(
    config: AoiConfig, index_path: Path, source_metadata_path: Path
) -> dict[str, Any]:
    """Measure 0.5 m DTM index footprint intersection with the configured AOI.

    This measures published feature polygons only. It does not inspect raster
    pixels or establish that a downloadable, valid 0.5 m DTM covers the polygons.
    """
    source_metadata = _validate_source_metadata(
        _read_json(source_metadata_path, "source metadata"),
        source_metadata_path,
        index_path,
        config,
    )
    index_data = _read_json(index_path, "EA DTM index snapshot")
    if index_data.get("type") != "FeatureCollection":
        raise ElevationIndexError("EA DTM index must be a GeoJSON FeatureCollection")
    crs = index_data.get("crs")
    if not isinstance(crs, dict) or not isinstance(crs.get("properties"), dict):
        raise ElevationIndexError("EA DTM index snapshot must declare its CRS")
    crs_name = crs["properties"].get("name")
    if crs_name != "urn:ogc:def:crs:EPSG::27700":
        raise ElevationIndexError("EA DTM index snapshot must use EPSG:27700 coordinates")
    features = index_data.get("features")
    if not isinstance(features, list):
        raise ElevationIndexError("EA DTM index features must be an array")
    if (
        type(index_data.get("numberMatched")) is not int
        or type(index_data.get("numberReturned")) is not int
        or type(index_data.get("totalFeatures")) is not int
    ):
        raise ElevationIndexError("EA DTM index feature counts must be integers")
    if index_data["numberReturned"] != len(features):
        raise ElevationIndexError("EA DTM index numberReturned does not match its features array")
    if len(features) != source_metadata["response"]["numberReturned"]:
        raise ElevationIndexError("EA DTM index feature count does not match source metadata")
    if index_data.get("numberMatched") != source_metadata["response"]["numberMatched"]:
        raise ElevationIndexError("EA DTM index numberMatched does not match source metadata")
    if index_data.get("totalFeatures") != source_metadata["response"]["numberMatched"]:
        raise ElevationIndexError("EA DTM index totalFeatures does not match source metadata")
    if index_data.get("timeStamp") != source_metadata["response"]["timeStamp"]:
        raise ElevationIndexError("EA DTM index timeStamp does not match source metadata")

    west, south, east, north = config.bbox_m
    aoi = box(west, south, east, north)
    resolution_counts: dict[str, int] = {}
    selected: list[dict[str, Any]] = []
    selected_geometries: list[BaseGeometry] = []
    for index, feature in enumerate(features):
        if not isinstance(feature, dict):
            raise ElevationIndexError(f"index feature {index} must be an object")
        if feature.get("type") != "Feature":
            raise ElevationIndexError(f"index feature {index}.type must be Feature")
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            raise ElevationIndexError(f"index feature {index} properties must be an object")
        resolution = _number(properties.get("resolution"), f"index feature {index}.resolution")
        if resolution not in _PUBLISHED_RESOLUTIONS_M:
            raise ElevationIndexError(
                f"index feature {index}.resolution is not a published EA DTM resolution"
            )
        key = format(resolution, "g")
        resolution_counts[key] = resolution_counts.get(key, 0) + 1
        geometry = _feature_geometry(feature, index)
        clipped = geometry.intersection(aoi)
        if clipped.is_empty:
            clipped_area = 0.0
        else:
            clipped_area = clipped.area
        if not math.isfinite(clipped_area) or clipped_area < 0:
            raise ElevationIndexError(f"index feature {index} produced an invalid AOI intersection")
        if resolution != 0.5:
            continue
        record_id = _string(feature.get("id"), f"index feature {index}.id")
        dtm_name = _string(properties.get("dtm_name"), f"index feature {index}.dtm_name")
        os_tile = _string(properties.get("ostilename"), f"index feature {index}.ostilename")
        start_date = _string(properties.get("sdflown"), f"index feature {index}.sdflown")
        end_date = _string(properties.get("edflown"), f"index feature {index}.edflown")
        transform = _string(properties.get("transform"), f"index feature {index}.transform")
        geoid = _string(properties.get("geoid"), f"index feature {index}.geoid")
        year = properties.get("year")
        if isinstance(year, str) and len(year) == 4 and year.isdigit():
            year = int(year)
        if isinstance(year, bool) or not isinstance(year, int) or not 1900 <= year <= 2100:
            raise ElevationIndexError(f"index feature {index}.year must be a valid integer year")
        try:
            start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ElevationIndexError(
                f"index feature {index} survey dates must be ISO-8601 timestamps"
            ) from exc
        if start > end or start.year != year:
            raise ElevationIndexError(
                f"index feature {index} survey dates do not match its recorded year or order"
            )
        selected.append(
            {
                "featureId": record_id,
                "dtmName": dtm_name,
                "osTile": os_tile,
                "year": year,
                "surveyStart": start_date,
                "surveyEnd": end_date,
                "nominalResolutionM": resolution,
                "coordinateOperation": transform,
                "verticalReference": geoid,
                "aoiIntersectionAreaM2": clipped_area,
            }
        )
        if clipped_area > 0:
            selected_geometries.append(clipped)

    union = None
    if selected_geometries:
        from shapely.ops import unary_union

        union = unary_union(selected_geometries)
    aoi_area = config.width_m * config.height_m
    union_area = union.area if union is not None else 0.0
    transforms = sorted({item["coordinateOperation"] for item in selected})
    geoids = sorted({item["verticalReference"] for item in selected})
    survey_dates = sorted({(item["surveyStart"], item["surveyEnd"]) for item in selected})

    return {
        "formatVersion": 1,
        "assessment": "Environment Agency LIDAR DTM time-stamped index resolution assessment",
        "measurementStatus": "completed",
        "interpretation": "metadata_footprint_only",
        "aoi": {
            "id": config.id,
            "profile": config.profile,
            "crs": config.crs,
            "boundsM": [west, south, east, north],
            "widthM": config.width_m,
            "heightM": config.height_m,
            "areaM2": aoi_area,
            "selectionStatus": config.selection_status,
            "overallCoverageStatus": config.coverage_status,
        },
        "source": source_metadata,
        "publisherProductMetadata": {
            "catalogueUpdatedDate": source_metadata["catalogueUpdatedDate"],
            "documentedOutputResolutionsM": source_metadata["productResolutionOptionsM"],
            "verticalReferenceClaim": source_metadata["publisherVerticalReference"],
            "verticalAccuracyClaim": source_metadata["publisherVerticalAccuracy"],
            "claimsAreCatalogueLevelNotPerRasterMetadata": True,
        },
        "indexSummary": {
            "matchedFeatureCount": len(features),
            "resolutionFeatureCounts": dict(sorted(resolution_counts.items())),
            "sourceCrs": "EPSG:27700",
            "resolutionFieldMeaning": "published nominal DTM output cell size in metres",
            "publisherDocumentedProductResolutionsM": list(_PUBLISHED_RESOLUTIONS_M),
            "indexFeatureResolutionCountsAreAOIQueryResults": True,
        },
        "halfMetreIndexFootprint": {
            "status": "partial_metadata_footprint" if selected else "no_metadata_footprint",
            "featureCount": len(selected),
            "coveredUnionAreaM2": union_area,
            "aoiAreaM2": aoi_area,
            "aoiFraction": union_area / aoi_area,
            "aoiPercent": union_area / aoi_area * 100,
            "surveyDateRanges": [list(item) for item in survey_dates],
            "coordinateOperations": transforms,
            "verticalReferences": geoids,
            "features": selected,
            "overlapUnionCountsAreaOnce": True,
        },
        "limits": [
            "Index polygons are published footprints, not raster-pixel coverage.",
            "No 0.5 m raster was acquired; pixel validity and availability are unknown.",
            "Raster-cell coverage requires the separate 1 m source-raster assessment.",
            "Point-cloud spacing is separate and was not assessed by this DTM resolution query.",
            "Existing GIS browser packages remain 1 km and do not represent this AOI.",
            "The AOI remains pending; OSM/OS feature coverage and approval are outstanding.",
        ],
    }
