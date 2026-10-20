"""CLI smoke tests cover validation, output generation, and error codes."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from torquay_pipeline.cli import _aoi_geojson_path, main

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "aoi.torquay.json"


def test_validate_and_select_commands(tmp_path: Path, capsys) -> None:
    assert main(["validate-aoi", "--config", str(CONFIG)]) == 0
    assert "AOI config valid" in capsys.readouterr().err

    assert main(["select-aoi", "--config", str(CONFIG), "--output-dir", str(tmp_path)]) == 0
    result = json.loads((tmp_path / "aoi-selection.json").read_text(encoding="utf-8"))
    assert result["selection_status"] == "selected_pending_coverage"
    assert result["coverage_status"] == "not_checked"
    assert (tmp_path / "aoi-selection.geojson").is_file()
    assert (tmp_path / "aoi-selection.md").is_file()
    saved_config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert saved_config["aoi"]["bbox_m"] == result["aoi"]["bbox_m"]
    assert saved_config["aoi"]["center_bng_m"] == [
        result["aoi"]["center_easting_m"],
        result["aoi"]["center_northing_m"],
    ]
    assert result["profile"] == "current_2km"


def test_explicit_historical_profile_validates_and_regenerates_one_kilometre_snapshot(
    tmp_path: Path,
) -> None:
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    raw["profile"] = "historical_1km"
    raw["aoi"]["width_m"] = 1000.0
    raw["aoi"]["height_m"] = 1000.0
    raw["aoi"]["bbox_m"] = [
        290608.9018176432,
        64853.48350844931,
        291608.9018176432,
        65853.48350844931,
    ]
    config_path = tmp_path / "aoi.torquay-1km.json"
    config_path.write_text(json.dumps(raw), encoding="utf-8")
    output_dir = tmp_path / "historical-selection"

    assert main(["validate-aoi", "--config", str(config_path)]) == 0
    assert main(["select-aoi", "--config", str(config_path), "--output-dir", str(output_dir)]) == 0

    selection = json.loads((output_dir / "aoi-selection.json").read_text(encoding="utf-8"))
    assert selection["profile"] == "historical_1km"
    assert selection["aoi"]["width_m"] == selection["aoi"]["height_m"] == 1000
    assert selection["aoi"]["bbox_m"] == raw["aoi"]["bbox_m"]
    assert json.loads(config_path.read_text(encoding="utf-8"))["profile"] == "historical_1km"


def test_cli_selects_geojson_ring_for_matching_aoi_profile_and_honors_override(
    tmp_path: Path,
) -> None:
    historical_ring = ROOT / "docs/milestones/artifacts/AOI-1km-selection/aoi-selection.geojson"
    current_ring = ROOT / "docs/aoi-selection.geojson"
    assert _aoi_geojson_path("current_2km", None) == current_ring
    assert _aoi_geojson_path("historical_1km", None) == historical_ring

    override = tmp_path / "explicit-ring.geojson"
    override.write_text("{}", encoding="utf-8")
    assert _aoi_geojson_path("historical_1km", override) == override.resolve()


def test_invalid_config_returns_actionable_nonzero_status(tmp_path: Path, capsys) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")

    result = main(["validate-aoi", "--config", str(invalid)])

    assert result == 2
    assert "format_version" in capsys.readouterr().err


def test_inspect_sources_reports_missing_manifest(tmp_path: Path, capsys) -> None:
    result = main(
        [
            "inspect-sources",
            "--config",
            str(CONFIG),
            "--manifest",
            str(tmp_path / "missing-manifest.json"),
            "--source-dir",
            str(tmp_path / "raw"),
            "--report",
            str(tmp_path / "coverage.json"),
        ]
    )

    assert result == 2
    assert "source manifest is missing" in capsys.readouterr().err


def test_build_terrain_reports_unsupported_source_coverage_cleanly(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    import torquay_pipeline.cli as cli
    from torquay_pipeline.terrain_export import TerrainExportError

    monkeypatch.setattr(cli, "_verified_sources", lambda _manifest, _source: ({}, [], []))
    monkeypatch.setattr(
        cli,
        "analyze_coverage",
        lambda *_args: SimpleNamespace(report={"analysis": {"ea_dtm_threshold_result": "pass"}}),
    )

    def fail_build(*_args, **_kwargs):
        raise TerrainExportError(
            "source coverage cannot bilinearly support output vertices outside the available tiles"
        )

    monkeypatch.setattr(cli, "build_terrain_package", fail_build)
    result = main(
        [
            "build-terrain",
            "--config",
            str(CONFIG),
            "--manifest",
            str(tmp_path / "manifest.json"),
            "--source-dir",
            str(tmp_path / "raw"),
            "--package-dir",
            str(tmp_path / "package"),
            "--report",
            str(tmp_path / "qa.json"),
            "--preview",
            str(tmp_path / "preview.png"),
        ]
    )

    assert result == 2
    assert "source coverage cannot bilinearly support" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("center_bng_m", None, "aoi.center_bng_m"),
        ("bbox_m", None, "aoi.bbox_m"),
        ("center_bng_m", [1, 2], "aoi.bbox_m"),
        ("bbox_m", [0, 0, 2000, 2000], "aoi.bbox_m"),
    ],
)
def test_validate_rejects_invalid_or_stale_stored_projection(
    tmp_path: Path, capsys, field: str, value: object, message: str
) -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    config["aoi"][field] = value
    edited = tmp_path / "stale.json"
    edited.write_text(json.dumps(config), encoding="utf-8")

    assert main(["validate-aoi", "--config", str(edited)]) == 2
    assert message in capsys.readouterr().err


def test_changing_only_configured_anchor_regenerates_aoi_outputs(tmp_path: Path) -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    edited_config = tmp_path / "edited-aoi.json"
    output_dir = tmp_path / "output"
    edited_config.write_text(json.dumps(config), encoding="utf-8")

    assert (
        main(["select-aoi", "--config", str(edited_config), "--output-dir", str(output_dir)]) == 0
    )
    first_selection = json.loads((output_dir / "aoi-selection.json").read_text(encoding="utf-8"))
    first_geojson = (output_dir / "aoi-selection.geojson").read_bytes()

    config["anchor"]["longitude"] += 0.001
    edited_config.write_text(json.dumps(config), encoding="utf-8")
    assert (
        main(["select-aoi", "--config", str(edited_config), "--output-dir", str(output_dir)]) == 0
    )
    moved_selection = json.loads((output_dir / "aoi-selection.json").read_text(encoding="utf-8"))
    moved_geojson = (output_dir / "aoi-selection.geojson").read_bytes()

    assert moved_selection["aoi"]["bbox_m"] != first_selection["aoi"]["bbox_m"]
    assert moved_geojson != first_geojson
    assert main(["validate-aoi", "--config", str(edited_config)]) == 0
    refreshed = json.loads(edited_config.read_text(encoding="utf-8"))
    assert refreshed["aoi"]["bbox_m"] == moved_selection["aoi"]["bbox_m"]
    assert refreshed["aoi"]["center_bng_m"] == [
        moved_selection["aoi"]["center_easting_m"],
        moved_selection["aoi"]["center_northing_m"],
    ]
