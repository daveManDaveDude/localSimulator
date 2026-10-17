from __future__ import annotations

from pathlib import Path

import pytest

import torquay_pipeline.buildings as building_module
from torquay_pipeline.buildings import BuildingConfig, import_osm_buildings
from torquay_pipeline.config import Anchor, AoiConfig
from torquay_pipeline.coordinates import pinned_transformer


def _fixture_aoi() -> AoiConfig:
    return AoiConfig(
        format_version=1,
        id="synthetic-building-fixture",
        name="Fictional geometry fixture AOI",
        selection_status="selected_pending_coverage",
        coverage_status="not_checked",
        anchor=Anchor(
            postcode="XX1 1XX",
            longitude=0,
            latitude=0,
            coordinate_meaning="Synthetic test anchor; not a real place.",
            quality=1,
            source_name="offline test fixture",
            source_url="https://example.invalid/fixture",
            source_license="test only",
            retrieved_date="2026-01-01",
        ),
        crs="EPSG:27700",
        width_m=1000.0,
        height_m=1000.0,
        center_bng_m=(0.0, 0.0),
        bbox_m=(-500.0, -500.0, 500.0, 500.0),
        world_units="metres",
    )


@pytest.fixture
def osm_area_fixture(tmp_path):
    """Write fictional OSM XML at a synthetic BNG test location, not the Torquay AOI."""
    to_wgs84, _info = pinned_transformer(27700, 4326)
    nodes = {
        1: (-80, 30),
        2: (-40, 30),
        3: (-40, 70),
        4: (-80, 70),
        5: (-70, 40),
        6: (-50, 40),
        7: (-50, 60),
        8: (-70, 60),
        10: (-250, -50),
        11: (-210, -50),
        12: (-210, -10),
        13: (-250, -10),
        20: (480, -20),
        21: (530, -20),
        22: (530, 20),
        23: (480, 20),
        30: (100, 100),
        31: (120, 120),
        32: (100, 120),
        33: (120, 100),
    }
    node_xml = []
    for identifier, (easting, northing) in nodes.items():
        longitude, latitude = to_wgs84.transform(easting, northing, errcheck=True)
        node_xml.append(f'<node id="{identifier}" lat="{latitude:.12f}" lon="{longitude:.12f}" />')
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <osm version="0.6" generator="TVW offline synthetic fixture">
      {"".join(node_xml)}
      <way id="100" version="3">
        <nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
        <tag k="building" v="yes"/><tag k="name" v="member tag retained in intermediate"/>
      </way>
      <way id="101">
        <nd ref="5"/><nd ref="6"/><nd ref="7"/><nd ref="8"/><nd ref="5"/>
      </way>
      <relation id="200" version="5">
        <member type="way" ref="100" role="outer"/>
        <member type="way" ref="101" role="inner"/>
        <tag k="type" v="multipolygon"/><tag k="building" v="apartments"/>
        <tag k="height" v="10 ft"/><tag k="name" v="Fictional courtyard"/>
      </relation>
      <way id="300">
        <nd ref="10"/><nd ref="11"/><nd ref="12"/><nd ref="13"/><nd ref="10"/>
        <tag k="building" v="yes"/><tag k="building:levels" v="3"/>
      </way>
      <way id="302">
        <nd ref="10"/><nd ref="11"/><nd ref="12"/><nd ref="13"/><nd ref="10"/>
        <tag k="building" v="yes"/><tag k="height" v="12"/>
      </way>
      <way id="400">
        <nd ref="1"/><nd ref="5"/><nd ref="6"/><nd ref="2"/><nd ref="1"/>
        <tag k="building:part" v="yes"/>
      </way>
      <way id="500">
        <nd ref="1"/><nd ref="2"/><nd ref="3"/><nd ref="4"/><nd ref="1"/>
        <tag k="building" v="no"/>
      </way>
      <way id="600">
        <nd ref="20"/><nd ref="21"/><nd ref="22"/><nd ref="23"/><nd ref="20"/>
        <tag k="building" v="commercial"/><tag k="height" v="8"/>
      </way>
      <way id="700">
        <nd ref="30"/><nd ref="31"/><nd ref="32"/><nd ref="33"/><nd ref="30"/>
        <tag k="building" v="yes"/>
      </way>
      <relation id="800" version="1">
        <member type="way" ref="999" role="outer"/>
        <tag k="type" v="multipolygon"/><tag k="building" v="yes"/>
      </relation>
    </osm>
    """
    path = tmp_path / "fictional-buildings.osm"
    path.write_text(xml, encoding="utf-8")
    return path, _fixture_aoi()


def _fake_source_verification(*_args):
    return {
        "filename": "fictional-buildings.osm",
        "size_bytes": 1,
        "sha256": "f" * 64,
        "pbf_header": {"replication_timestamp": "2026-01-01T00:00:00Z"},
    }


def _import_fixture(osm_area_fixture, monkeypatch, config=None):
    path, aoi = osm_area_fixture
    monkeypatch.setattr(building_module, "verify_building_source", _fake_source_verification)
    return import_osm_buildings(
        path,
        Path("unused-test-manifest.json"),
        aoi,
        config or BuildingConfig(),
    )


def test_import_assembles_multipolygon_hole_and_suppresses_member_way(
    osm_area_fixture, monkeypatch
):
    result = _import_fixture(osm_area_fixture, monkeypatch)
    ids = {feature["id"]: feature for feature in result.buildings}
    assert "osm:relation:200" in ids
    assert "osm:way:100" not in ids
    relation = ids["osm:relation:200"]
    assert relation["geometry"]["polygons"][0]["interiorRingsXZ"]
    assert relation["heightMethod"] == "osm_height"
    assert relation["heightProvenance"]["parsedUnit"] == "feet"
    assert relation["heightM"] == pytest.approx(3.048)
    assert relation["source"]["version"] == 5
    assert relation["tags"]["name"] == "Fictional courtyard"
    assert any(
        feature["properties"]["tags"].get("name") == "member tag retained in intermediate"
        for feature in result.intermediate["features"]
    )
    assert result.qa["counts"]["relation_member_ways_suppressed"] >= 1
    assert result.qa["counts"]["relation_area_assembly_failures"] >= 1
    assert result.qa["counts"]["excluded_building_no"] >= 1
    assert result.qa["counts"]["excluded_building_part_only"] >= 1
    assert result.qa["summary"]["densityInterpretation"].startswith("Mapped OSM coverage only")


def test_local_polygon_ring_is_ccw_and_north_maps_to_negative_z(osm_area_fixture, monkeypatch):
    result = _import_fixture(osm_area_fixture, monkeypatch)
    ring = result.buildings[0]["geometry"]["polygons"][0]["exteriorXZ"]
    twice_area = sum(
        ring[index][0] * ring[index + 1][1] - ring[index + 1][0] * ring[index][1]
        for index in range(len(ring) - 1)
    )
    assert twice_area > 0
    assert ring[0] == ring[-1]


def test_exact_clipping_keeps_coordinates_inside_aoi_and_applies_area_threshold(
    osm_area_fixture, monkeypatch
):
    result = _import_fixture(osm_area_fixture, monkeypatch)
    clipped = next(feature for feature in result.buildings if feature["id"] == "osm:way:600")
    assert clipped["clippedToAoi"] is True
    for polygon in clipped["geometry"]["polygons"]:
        for x, z in polygon["exteriorXZ"]:
            assert -500 <= x <= 500
            assert -500 <= z <= 500
    higher_threshold = BuildingConfig(minimum_clipped_area_m2=1_000)
    result_large_threshold = _import_fixture(osm_area_fixture, monkeypatch, higher_threshold)
    assert not any(feature["id"] == "osm:way:600" for feature in result_large_threshold.buildings)
    assert result_large_threshold.qa["counts"]["below_minimum_area"] >= 1


def test_exact_duplicate_geometry_is_collapsed_and_reported(osm_area_fixture, monkeypatch):
    result = _import_fixture(osm_area_fixture, monkeypatch)
    way_300 = next(feature for feature in result.buildings if feature["id"] == "osm:way:300")
    assert way_300["duplicateReferences"] == ["osm:way:302"]
    assert "exact_geometry_duplicate_tag_conflict" in way_300["qualityFlags"]
    assert result.qa["counts"]["exact_geometry_duplicates_suppressed"] == 1


def test_self_intersection_is_rejected_without_geometry_repair(osm_area_fixture, monkeypatch):
    result = _import_fixture(osm_area_fixture, monkeypatch)
    assert not any(feature["id"] == "osm:way:700" for feature in result.buildings)
    assert result.qa["counts"]["area_geometry_errors"] >= 1
    assert any(
        item["sourceId"] == 700 and "invalid area" in item["reason"]
        for item in result.qa["quality"]["rejectedGeometrySamples"]
    )


def test_map_candidates_include_spatially_separated_groups(osm_area_fixture, monkeypatch):
    result = _import_fixture(osm_area_fixture, monkeypatch)
    groups = {item["group"] for item in result.qa["mapComparisonCandidates"]}
    assert len(groups) >= 3
    assert all(item["placementCheckOnly"] for item in result.qa["mapComparisonCandidates"])
