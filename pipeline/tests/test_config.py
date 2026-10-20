"""Config schema checks and actionable invalid-input errors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from torquay_pipeline.config import AoiConfigError, load_aoi_config

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "aoi.torquay.json"


def _write_config(tmp_path: Path, mutate: dict[str, object]) -> Path:
    value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    for key, replacement in mutate.items():
        if key.startswith("anchor."):
            value["anchor"][key.removeprefix("anchor.")] = replacement
        elif key.startswith("aoi."):
            value["aoi"][key.removeprefix("aoi.")] = replacement
        else:
            value[key] = replacement
    path = tmp_path / "aoi.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_loads_verified_postcode_candidate_config() -> None:
    config = load_aoi_config(CONFIG_PATH)

    assert config.anchor.postcode == "TQ1 4HN"
    assert config.anchor.longitude == -3.536013
    assert config.anchor.latitude == 50.477853
    assert config.crs == "EPSG:27700"
    assert config.profile == "current_2km"
    assert (config.width_m, config.height_m) == (2000, 2000)
    assert config.selection_status == "selected_pending_coverage"
    assert config.coverage_status == "not_checked"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("anchor.longitude", None, "anchor.longitude must be a finite number"),
        ("anchor.latitude", float("nan"), "anchor.latitude must be a finite number"),
        ("anchor.longitude", 181, "between -180 and 180"),
        ("anchor.latitude", -91, "between -90 and 90"),
        ("aoi.width_m", 1999, "exactly 2,000 m by 2,000 m"),
        ("aoi.height_m", 2001, "exactly 2,000 m by 2,000 m"),
        ("aoi.crs", "EPSG:3857", "aoi.crs must be EPSG:27700"),
        ("selection_status", "approved", "selected_pending_coverage"),
        ("coverage_status", "checked", "must remain 'not_checked'"),
        ("format_version", True, "format_version must be the integer 1"),
        ("format_version", 1.0, "format_version must be the integer 1"),
        ("anchor.quality", 0, "quality must be a positive integer"),
        ("profile", "unapproved", "profile must be"),
    ],
)
def test_rejects_invalid_config_values(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    with pytest.raises(AoiConfigError, match=message):
        load_aoi_config(_write_config(tmp_path, {field: value}))


def test_rejects_malformed_json_with_context(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{bad", encoding="utf-8")

    with pytest.raises(AoiConfigError, match="not valid JSON"):
        load_aoi_config(path)


def test_rejects_unknown_config_fields(tmp_path: Path) -> None:
    with pytest.raises(AoiConfigError, match="unsupported field.*unexpected"):
        load_aoi_config(_write_config(tmp_path, {"unexpected": True}))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("aoi.center_bng_m", None, "aoi.center_bng_m must contain exactly 2 finite numbers"),
        ("aoi.bbox_m", None, "aoi.bbox_m must contain exactly 4 finite numbers"),
        ("aoi.center_bng_m", [1, 2], "aoi.bbox_m easting midpoint"),
        ("aoi.bbox_m", [0, 0, 2000, 2000], "aoi.bbox_m easting midpoint"),
        ("aoi.bbox_m", [500, 0, 0, 500], "aoi.bbox_m must be ordered"),
    ],
)
def test_rejects_missing_or_malformed_stored_projected_values(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    with pytest.raises(AoiConfigError, match=message):
        load_aoi_config(_write_config(tmp_path, {field: value}))


def test_explicit_historical_one_kilometre_profile_is_accepted(tmp_path: Path) -> None:
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    raw["profile"] = "historical_1km"
    raw["aoi"]["width_m"] = 1000.0
    raw["aoi"]["height_m"] = 1000.0
    raw["aoi"]["bbox_m"] = [
        290608.9018176432,
        64853.48350844931,
        291608.9018176432,
        65853.48350844931,
    ]
    path = tmp_path / "historical-aoi.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    config = load_aoi_config(path)

    assert config.profile == "historical_1km"
    assert (config.width_m, config.height_m) == (1000, 1000)
    assert config.center_bng_m == (291108.9018176432, 65353.48350844931)
    assert config.bbox_m == (
        290608.9018176432,
        64853.48350844931,
        291608.9018176432,
        65853.48350844931,
    )


def test_missing_profile_defaults_to_current_two_kilometre_profile(tmp_path: Path) -> None:
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    raw.pop("profile")
    path = tmp_path / "unprofiled-current-aoi.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    config = load_aoi_config(path)

    assert config.profile == "current_2km"
    assert (config.width_m, config.height_m) == (2000, 2000)


@pytest.mark.parametrize(
    ("profile", "width", "height"),
    [("current_2km", 1000, 1000), ("historical_1km", 2000, 2000)],
)
def test_profile_requires_its_exact_square_dimensions(
    tmp_path: Path, profile: str, width: int, height: int
) -> None:
    with pytest.raises(AoiConfigError, match="profile.*requires exactly"):
        load_aoi_config(
            _write_config(
                tmp_path,
                {
                    "profile": profile,
                    "aoi.width_m": width,
                    "aoi.height_m": height,
                },
            )
        )
