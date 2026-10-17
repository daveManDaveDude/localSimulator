"""Strict loading and validation of the editable AOI selection config."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


class AoiConfigError(ValueError):
    """Raised when an AOI config is missing or contains invalid values."""


@dataclass(frozen=True)
class Anchor:
    postcode: str
    longitude: float
    latitude: float
    coordinate_meaning: str
    quality: int
    source_name: str
    source_url: str
    source_license: str
    retrieved_date: str


@dataclass(frozen=True)
class AoiConfig:
    format_version: int
    id: str
    name: str
    selection_status: str
    coverage_status: str
    anchor: Anchor
    crs: str
    width_m: float
    height_m: float
    center_bng_m: tuple[float, float]
    bbox_m: tuple[float, float, float, float]
    world_units: str


def _required_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AoiConfigError(f"{name} must be a JSON object")
    return value


def _check_keys(value: dict[str, Any], allowed: set[str], name: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise AoiConfigError(f"{name} contains unsupported field(s): {', '.join(unknown)}")


def _required_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AoiConfigError(f"{name} must be a non-empty string")
    return value.strip()


def _required_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AoiConfigError(f"{name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise AoiConfigError(f"{name} must be a finite number")
    return number


def load_aoi_config(path: Path) -> AoiConfig:
    """Read and validate a config file without performing a coordinate transform."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise AoiConfigError(f"cannot read AOI config '{path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AoiConfigError(f"AOI config '{path}' is not valid JSON: {exc}") from exc

    return parse_aoi_config(raw)


def parse_aoi_config(raw: Any) -> AoiConfig:
    """Validate an in-memory config mapping without transforming coordinates."""

    root = _required_mapping(raw, "config")
    _check_keys(
        root,
        {
            "format_version",
            "id",
            "name",
            "selection_status",
            "coverage_status",
            "anchor",
            "aoi",
            "world_units",
        },
        "config",
    )
    version = root.get("format_version")
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        raise AoiConfigError("format_version must be the integer 1")

    identifier = _required_string(root.get("id"), "id")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", identifier):
        raise AoiConfigError("id must contain lowercase letters, digits, and single hyphens")
    name = _required_string(root.get("name"), "name")

    selection_status = _required_string(root.get("selection_status"), "selection_status")
    if selection_status != "selected_pending_coverage":
        raise AoiConfigError("selection_status must be 'selected_pending_coverage'")
    coverage_status = _required_string(root.get("coverage_status"), "coverage_status")
    if coverage_status != "not_checked":
        raise AoiConfigError("coverage_status must remain 'not_checked' in TVW-006")

    anchor_raw = _required_mapping(root.get("anchor"), "anchor")
    _check_keys(
        anchor_raw,
        {
            "postcode",
            "longitude",
            "latitude",
            "coordinate_crs",
            "coordinate_meaning",
            "quality",
            "source_name",
            "source_url",
            "source_license",
            "retrieved_date",
        },
        "anchor",
    )
    postcode = _required_string(anchor_raw.get("postcode"), "anchor.postcode")
    if not re.fullmatch(r"[A-Z0-9]{2,4} ?[A-Z0-9]{3}", postcode.upper()):
        raise AoiConfigError("anchor.postcode must be a full UK postcode")
    if anchor_raw.get("coordinate_crs") != "EPSG:4326":
        raise AoiConfigError("anchor.coordinate_crs must be EPSG:4326")
    longitude = _required_number(anchor_raw.get("longitude"), "anchor.longitude")
    latitude = _required_number(anchor_raw.get("latitude"), "anchor.latitude")
    if not -180 <= longitude <= 180:
        raise AoiConfigError("anchor.longitude must be between -180 and 180 degrees")
    if not -90 <= latitude <= 90:
        raise AoiConfigError("anchor.latitude must be between -90 and 90 degrees")
    quality = anchor_raw.get("quality")
    if isinstance(quality, bool) or not isinstance(quality, int) or quality < 1:
        raise AoiConfigError("anchor.quality must be a positive integer")
    retrieved_date = _required_string(anchor_raw.get("retrieved_date"), "anchor.retrieved_date")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", retrieved_date):
        raise AoiConfigError("anchor.retrieved_date must use YYYY-MM-DD")
    try:
        date.fromisoformat(retrieved_date)
    except ValueError as exc:
        raise AoiConfigError("anchor.retrieved_date must be a valid YYYY-MM-DD date") from exc

    source_url = _required_string(anchor_raw.get("source_url"), "anchor.source_url")
    if not source_url.startswith("https://"):
        raise AoiConfigError("anchor.source_url must use HTTPS")

    anchor = Anchor(
        postcode=postcode.upper(),
        longitude=longitude,
        latitude=latitude,
        coordinate_meaning=_required_string(
            anchor_raw.get("coordinate_meaning"), "anchor.coordinate_meaning"
        ),
        quality=quality,
        source_name=_required_string(anchor_raw.get("source_name"), "anchor.source_name"),
        source_url=source_url,
        source_license=_required_string(anchor_raw.get("source_license"), "anchor.source_license"),
        retrieved_date=retrieved_date,
    )

    aoi_raw = _required_mapping(root.get("aoi"), "aoi")
    _check_keys(
        aoi_raw,
        {"crs", "width_m", "height_m", "center_bng_m", "bbox_m"},
        "aoi",
    )
    if aoi_raw.get("crs") != "EPSG:27700":
        raise AoiConfigError("aoi.crs must be EPSG:27700")
    width_m = _required_number(aoi_raw.get("width_m"), "aoi.width_m")
    height_m = _required_number(aoi_raw.get("height_m"), "aoi.height_m")
    if width_m != 500 or height_m != 500:
        raise AoiConfigError("TVW-006 candidate dimensions must be exactly 500 m by 500 m")
    stored_values: dict[str, tuple[float, ...]] = {}
    for field, count in (("center_bng_m", 2), ("bbox_m", 4)):
        values = aoi_raw.get(field)
        if not isinstance(values, list) or len(values) != count:
            raise AoiConfigError(f"aoi.{field} must contain exactly {count} finite numbers")
        stored_values[field] = tuple(
            _required_number(value, f"aoi.{field}[{index}]") for index, value in enumerate(values)
        )
    center = stored_values["center_bng_m"]
    bbox = stored_values["bbox_m"]
    west, south, east, north = bbox
    if not west < east or not south < north:
        raise AoiConfigError("aoi.bbox_m must be ordered as west < east and south < north")
    if not math.isclose(east - west, width_m, rel_tol=0, abs_tol=1e-7) or not math.isclose(
        north - south, height_m, rel_tol=0, abs_tol=1e-7
    ):
        raise AoiConfigError("aoi.bbox_m must describe the configured 500 m by 500 m square")
    if not math.isclose((west + east) / 2, center[0], rel_tol=0, abs_tol=1e-7):
        raise AoiConfigError("aoi.bbox_m easting midpoint must match aoi.center_bng_m[0]")
    if not math.isclose((south + north) / 2, center[1], rel_tol=0, abs_tol=1e-7):
        raise AoiConfigError("aoi.bbox_m northing midpoint must match aoi.center_bng_m[1]")
    world_units = _required_string(root.get("world_units"), "world_units")
    if world_units != "metres":
        raise AoiConfigError("world_units must be 'metres'")

    return AoiConfig(
        format_version=1,
        id=identifier,
        name=name,
        selection_status=selection_status,
        coverage_status=coverage_status,
        anchor=anchor,
        crs="EPSG:27700",
        width_m=width_m,
        height_m=height_m,
        center_bng_m=(center[0], center[1]),
        bbox_m=(west, south, east, north),
        world_units=world_units,
    )


def validate_stored_selection(
    config: AoiConfig,
    center_easting_m: float,
    center_northing_m: float,
    bbox_m: list[float] | tuple[float, float, float, float],
) -> None:
    """Reject stored projected values that do not match the configured WGS84 anchor."""
    tolerance_m = 1e-6
    if not (
        math.isclose(config.center_bng_m[0], center_easting_m, rel_tol=0, abs_tol=tolerance_m)
        and math.isclose(config.center_bng_m[1], center_northing_m, rel_tol=0, abs_tol=tolerance_m)
    ):
        raise AoiConfigError(
            "aoi.center_bng_m does not match the configured anchor transformed to EPSG:27700"
        )
    if len(bbox_m) != 4 or any(
        not math.isclose(stored, expected, rel_tol=0, abs_tol=tolerance_m)
        for stored, expected in zip(config.bbox_m, bbox_m, strict=True)
    ):
        raise AoiConfigError(
            "aoi.bbox_m does not match the configured anchor's 500 m EPSG:27700 square"
        )
