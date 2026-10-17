"""AOI dimensions, RFC 7946 ring orientation, and deterministic outputs."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from torquay_pipeline.aoi import generate_selection, signed_ring_area, write_selection
from torquay_pipeline.config import load_aoi_config

ROOT = Path(__file__).resolve().parents[2]


def test_selection_is_exact_square_with_closed_counter_clockwise_geojson() -> None:
    selection, geojson, _markdown = generate_selection(
        load_aoi_config(ROOT / "config" / "aoi.torquay.json")
    )
    west, south, east, north = selection["aoi"]["bbox_m"]
    ring = geojson["features"][0]["geometry"]["coordinates"][0]
    point = geojson["features"][1]["geometry"]["coordinates"]

    assert east - west == 1000
    assert north - south == 1000
    assert selection["aoi"]["center_easting_m"] == 291108.9018176432
    assert selection["aoi"]["center_northing_m"] == 65353.48350844931
    assert selection["aoi"]["bbox_m"] == [
        290608.9018176432,
        64853.48350844931,
        291608.9018176432,
        65853.48350844931,
    ]
    assert ring[0] == ring[-1]
    assert len(ring) == 5
    assert signed_ring_area(ring) > 0
    assert point == [-3.536013, 50.477853]
    assert geojson["type"] == "FeatureCollection"
    assert selection["selection_status"] == "selected_pending_coverage"
    assert selection["coverage_status"] == "not_checked"
    assert selection["transformations"]["network_grids_enabled"] is False


def test_generation_is_deterministic_and_anchor_change_regenerates_outputs(tmp_path: Path) -> None:
    config = load_aoi_config(ROOT / "config" / "aoi.torquay.json")
    first = generate_selection(config)
    second = generate_selection(config)
    moved = replace(
        config, anchor=replace(config.anchor, longitude=config.anchor.longitude + 0.001)
    )
    moved_result = generate_selection(moved)

    assert first == second
    assert first[0]["aoi"]["bbox_m"] != moved_result[0]["aoi"]["bbox_m"]
    assert first[1] != moved_result[1]

    write_selection(tmp_path, *first)
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    write_selection(tmp_path, *second)
    after = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    assert before == after
    assert set(before) == {"aoi-selection.json", "aoi-selection.geojson", "aoi-selection.md"}
    assert not list(tmp_path.glob("*.tmp"))


def test_geojson_coordinates_are_wgs84_ranges() -> None:
    _selection, geojson, _markdown = generate_selection(
        load_aoi_config(ROOT / "config" / "aoi.torquay.json")
    )
    ring = geojson["features"][0]["geometry"]["coordinates"][0]
    assert all(-180 <= longitude <= 180 and -90 <= latitude <= 90 for longitude, latitude in ring)


def test_generated_report_uses_configured_center_without_fixed_road_claims() -> None:
    config = load_aoi_config(ROOT / "config" / "aoi.torquay.json")
    moved = replace(config, anchor=replace(config.anchor, longitude=-3.4, latitude=50.5))
    _selection, _geojson, markdown = generate_selection(moved)

    assert "?mlat=50.50000000&mlon=-3.40000000#map=16/50.50000000/-3.40000000" in markdown
    assert "Wrights Lane" not in markdown
    assert "Haslam Road" not in markdown
    assert "generated from the configured WGS84 anchor" in markdown
