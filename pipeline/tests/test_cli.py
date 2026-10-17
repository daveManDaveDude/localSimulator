"""CLI smoke tests cover validation, output generation, and error codes."""

from __future__ import annotations

import json
from pathlib import Path

from torquay_pipeline.cli import main

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


def test_invalid_config_returns_actionable_nonzero_status(tmp_path: Path, capsys) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")

    result = main(["validate-aoi", "--config", str(invalid)])

    assert result == 2
    assert "format_version" in capsys.readouterr().err


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
