from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import osmium
import pytest
from shapely.geometry import Polygon, box

from torquay_pipeline.building_sources import inspect_building_source
from torquay_pipeline.config import load_aoi_config
from torquay_pipeline.coordinates import transform_bng_to_wgs84
from torquay_pipeline.road_config import RoadConfigError, load_road_config, parse_road_config
from torquay_pipeline.road_export import RoadExportError, build_road_package, validate_road_package
from torquay_pipeline.road_geometry import (
    _triangulate_polygon_component,
    build_display_polygons,
    tessellate_display_polygons,
)
from torquay_pipeline.road_preview import NORTH_ARROW_TAIL_AXES, NORTH_ARROW_TIP_AXES
from torquay_pipeline.roads import ground_skip_reason, import_osm_roads

ROOT = Path(__file__).resolve().parents[2]


def test_road_preview_north_arrow_points_up_for_negative_z_north():
    # Matplotlib axes fractions increase upward even though the plotted Z data
    # limits are inverted so negative Z is north.
    assert NORTH_ARROW_TIP_AXES[1] > NORTH_ARROW_TAIL_AXES[1]


def _write_osm_pbf(
    path: Path,
    ways: list[dict[str, object]],
    coordinate_map: dict[int, tuple[float, float]],
    *,
    omit_nodes: set[int] | None = None,
) -> dict[str, object]:
    omitted = omit_nodes or set()
    writer = osmium.SimpleWriter(str(path))
    for node_id, (longitude, latitude) in sorted(coordinate_map.items()):
        if node_id not in omitted:
            writer.add_node(osmium.osm.mutable.Node(id=node_id, location=(longitude, latitude)))
    for spec in ways:
        node_ids = spec["node_ids"]
        references = [
            osmium.osm.NodeRef(
                ref=node_id,
                location=osmium.osm.Location(*coordinate_map[node_id])
                if node_id in coordinate_map
                else osmium.osm.Location(),
            )
            for node_id in node_ids
        ]
        writer.add_way(osmium.osm.mutable.Way(id=spec["id"], nodes=references, tags=spec["tags"]))
    writer.close()
    observed = inspect_building_source(path)
    return {
        "osm": {
            "sources": [
                {
                    "filename": observed["filename"],
                    "size_bytes": observed["size_bytes"],
                    "sha256": observed["sha256"],
                    "publisher_md5": observed["md5"],
                    "pbf_header": observed["pbf_header"],
                }
            ]
        }
    }


def _road_config():
    return load_road_config(ROOT / "config" / "roads.torquay.json")[0]


def test_config_rejects_booleans_unknown_fields_and_unsafe_paths():
    raw = json.loads((ROOT / "config" / "roads.torquay.json").read_text())
    raw["surface_offset_m"] = True
    with pytest.raises(RoadConfigError, match="finite JSON number"):
        parse_road_config(raw)
    raw = json.loads((ROOT / "config" / "roads.torquay.json").read_text())
    raw["unknown"] = 1
    with pytest.raises(RoadConfigError, match="unknown"):
        parse_road_config(raw)
    raw = json.loads((ROOT / "config" / "roads.torquay.json").read_text())
    raw["package_path"] = "../outside"
    with pytest.raises(RoadConfigError, match="safe workspace-relative"):
        parse_road_config(raw)


@pytest.mark.parametrize(
    ("tags", "reason"),
    [
        ({"bridge": "yes"}, "bridge_yes"),
        ({"bridge": "no"}, None),
        ({"tunnel": "building_passage"}, "tunnel_building_passage"),
        ({"covered": "arcade"}, "covered_arcade"),
        ({"layer": "1"}, "nonzero_layer"),
        ({"layer": "0"}, None),
        ({"layer": "0;1"}, "ambiguous_layer"),
        ({"layer": ""}, "ambiguous_layer"),
    ],
)
def test_ground_vertical_tag_assumption_is_conservative(tags, reason):
    assert ground_skip_reason(tags) == reason


def test_actual_pyosmium_path_resolves_order_filters_classes_and_reports_exclusions(tmp_path):
    aoi = load_aoi_config(ROOT / "config" / "aoi.torquay.json")
    # Place a through-line across both AOI edges using the pinned inverse transform.
    xs = [aoi.center_bng_m[0] - 650, aoi.center_bng_m[0], aoi.center_bng_m[0] + 650]
    ys = [aoi.center_bng_m[1], aoi.center_bng_m[1] + 10, aoi.center_bng_m[1]]
    longitudes, latitudes, _ = transform_bng_to_wgs84(xs, ys)
    locations = {index + 1: (longitudes[index], latitudes[index]) for index in range(3)}
    # Add a separate east-west cycleway with explicit local coordinates.
    cycle_lon, cycle_lat, _ = transform_bng_to_wgs84(
        [aoi.center_bng_m[0] - 30, aoi.center_bng_m[0] + 30],
        [aoi.center_bng_m[1] - 30, aoi.center_bng_m[1] - 30],
    )
    locations[4] = (cycle_lon[0], cycle_lat[0])
    locations[5] = (cycle_lon[1], cycle_lat[1])
    ways = [
        {
            "id": 10,
            "node_ids": [1, 2, 3],
            "tags": {"highway": "residential", "name": "Fictional Test Way"},
        },
        {"id": 11, "node_ids": [3, 2, 1], "tags": {"highway": "residential", "name": "Duplicate"}},
        {"id": 12, "node_ids": [4, 5], "tags": {"highway": "cycleway"}},
        {"id": 13, "node_ids": [4, 5], "tags": {"highway": "service", "bridge": "yes"}},
        {"id": 14, "node_ids": [4, 5], "tags": {"highway": "steps"}},
        {"id": 15, "node_ids": [4, 5], "tags": {"highway": "residential", "layer": "1"}},
        {"id": 16, "node_ids": [4, 5], "tags": {"highway": "residential", "area": "yes"}},
        {"id": 17, "node_ids": [4, 5], "tags": {"highway": "made_up_class"}},
        {"id": 18, "node_ids": [4, 99], "tags": {"highway": "footway"}},
    ]
    source = tmp_path / "fixture.osm.pbf"
    source_manifest = tmp_path / "source.json"
    source_manifest.write_text(json.dumps(_write_osm_pbf(source, ways, locations)))
    result = import_osm_roads(
        source,
        source_manifest,
        aoi,
        _road_config(),
    )
    features = result.features
    ids = {feature["source"]["osmId"] for feature in features}
    assert ids == {10, 12}
    first = next(feature for feature in features if feature["source"]["osmId"] == 10)
    assert len(first["centerlinePartsXZ"]) == 1
    assert first["source"]["nodeIds"] == [1, 2, 3]
    assert first["duplicateWayIds"] == [11]
    assert first["sourceTags"]["name"] == "Fictional Test Way"
    assert result.qa["counts"]["duplicate_source_ways"] == 1
    assert result.qa["counts"]["excluded_ground_assumption"] == 2
    assert result.qa["counts"]["excluded_area_surfaces"] == 1
    assert result.qa["counts"]["excluded_classes"] == 2
    assert result.qa["counts"]["invalid_missing_locations"] == 1
    assert result.coordinate_operation["wgs84ToBng"]["reported_accuracy_m"] == 2.0


def test_reverse_and_collinear_duplicate_key_preserves_distinct_parallel_lines():
    from torquay_pipeline.roads import _canonical_line_key

    assert _canonical_line_key([(0, 0), (1, 0), (2, 0)]) == _canonical_line_key([(2, 0), (0, 0)])
    assert _canonical_line_key([(0, 0), (1, 0), (2, 0)]) != _canonical_line_key(
        [(0, 0.1), (2, 0.1)]
    )


def test_width_buffers_are_flat_capped_and_priority_groups_do_not_overlap():
    config = _road_config()
    aoi = load_aoi_config(ROOT / "config" / "aoi.torquay.json")
    features = [
        {
            "id": "way/1",
            "sourceCenterlineXZ": [[-10, 0], [10, 0]],
            "estimatedWidthM": 6.0,
            "displayGroup": "vehicular",
        },
        {
            "id": "way/2",
            "sourceCenterlineXZ": [[-10, 1], [10, 1]],
            "estimatedWidthM": 1.5,
            "displayGroup": "path",
        },
    ]
    display, areas = build_display_polygons(features, aoi, config)
    assert areas["vehicular"] == pytest.approx(120)
    assert display["vehicular"].intersection(display["path"]).area == 0
    assert display["path"].area < 30
    assert display["path"].is_valid


def test_terrain_triangle_tessellation_covers_cells_and_preserves_upward_winding():
    # A 4x4 m test grid, with one ribbon crossing the cell diagonal and both rows.
    surface = box(-1.37, -1.44, 1.81, 1.29)
    batches, areas, mesh_numerics = tessellate_display_polygons(
        {"vehicular": surface, "cycleway": Polygon(), "path": Polygon()},
        columns=3,
        rows=3,
        spacing_m=2.0,
        width_m=4.0,
        depth_m=4.0,
    )
    batch = batches["vehicular"]
    assert areas["vehicular"] == pytest.approx(surface.area)
    assert mesh_numerics["float32CollapsedSliverTriangleCount"] == 0
    assert len(batch["indices"]) == len(batch["terrainTriangles"])
    assert len(batch["indices"]) > 4
    for indices, cell in zip(batch["indices"], batch["terrainTriangles"], strict=True):
        assert 0 <= cell[0] < 2 and 0 <= cell[1] < 2 and cell[2] in {0, 1}
        points = [batch["verticesXZ"][index] for index in indices]
        signed = sum(
            points[index][0] * points[(index + 1) % 3][1]
            - points[(index + 1) % 3][0] * points[index][1]
            for index in range(3)
        )
        assert signed < 0  # Upward normal in Three.js X/Y/Z coordinates.
        assert all(-2 <= x <= 2 and -2 <= z <= 2 for x, z in points)


def test_tessellation_keeps_roundabout_hole_empty():
    outer = box(-1.5, -1.5, 1.5, 1.5)
    hole = box(-0.3, -0.3, 0.3, 0.3)
    ring = Polygon(outer.exterior.coords, [hole.exterior.coords])
    batches, areas, mesh_numerics = tessellate_display_polygons(
        {"vehicular": ring, "cycleway": Polygon(), "path": Polygon()},
        columns=3,
        rows=3,
        spacing_m=2.0,
        width_m=4.0,
        depth_m=4.0,
    )
    batch = batches["vehicular"]
    assert areas["vehicular"] == pytest.approx(ring.area)
    assert mesh_numerics["float32CollapsedSliverTriangleCount"] == 0
    for triangle in batch["indices"]:
        points = [batch["verticesXZ"][index] for index in triangle]
        assert Polygon(points).intersection(hole).area < 1e-10


def test_tessellation_audits_and_omits_sub_float32_sliver_faces():
    polygon = Polygon(
        [
            (319.9999859801303, -353.9999859801303),
            (320.0, -354.0),
            (319.99997858196247, -354.0),
            (319.9999859801303, -353.9999859801303),
        ]
    )
    output = {
        "verticesXZ": [],
        "indices": [],
        "terrainTriangles": [],
        "_vertexLookup": {},
        "_float32CollapsedSliverTriangleCount": 0,
        "_float32CollapsedSliverAreaM2": 0.0,
    }
    _triangulate_polygon_component(polygon, 72, 410, 1, output)
    assert output["indices"] == []
    assert output["verticesXZ"] == []
    assert output["_float32CollapsedSliverTriangleCount"] == 1
    assert 0 < output["_float32CollapsedSliverAreaM2"] < 1e-6


def test_package_validation_rederives_source_geometry_after_hashes_are_refreshed(
    tmp_path, monkeypatch
):
    from torquay_pipeline import road_export
    from torquay_pipeline.aoi import generate_selection
    from torquay_pipeline.building_export import _configured_aoi_ring

    aoi = load_aoi_config(ROOT / "config" / "aoi.torquay.json")
    config = _road_config()
    center_e, center_n = aoi.center_bng_m
    longitude, latitude, _operation = transform_bng_to_wgs84(
        [center_e - 30, center_e + 30], [center_n, center_n]
    )
    source = tmp_path / "fictional.osm.pbf"
    observed = _write_osm_pbf(
        source,
        [
            {
                "id": 100,
                "node_ids": [1, 2],
                "tags": {"highway": "residential", "name": "Fictional Test Way"},
            }
        ],
        {1: (longitude[0], latitude[0]), 2: (longitude[1], latitude[1])},
    )["osm"]["sources"][0]
    source_manifest_path = tmp_path / "source-manifest.json"
    source_manifest_path.write_text(
        json.dumps(
            {
                "osm": {
                    "product": {
                        "publisher": "Fictional test publisher",
                        "name": "Fictional test PBF",
                        "download_page_url": "https://example.invalid/source",
                        "licence": "Fictional test licence",
                        "licence_url": "https://example.invalid/licence",
                        "credit": "Fictional fixture only",
                        "attribution_requirement": "Test data only",
                        "metadata_note": "No geographic observations.",
                    },
                    "acquisition": {"source_storage": "temporary fixture"},
                    "sources": [
                        {
                            **observed,
                            "download_url": "https://example.invalid/fixture.pbf",
                            "publisher_checksum_url": "https://example.invalid/fixture.md5",
                            "download_date": "2026-01-01",
                            "downloaded_at_utc": "2026-01-01T00:00:00Z",
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    terrain_dir = tmp_path / "terrain"
    terrain_dir.mkdir()
    terrain_manifest = {
        "id": aoi.id,
        "origin": {"eastingM": center_e, "northingM": center_n, "elevationM": 0.0},
        "heightfield": {
            "path": "heightfield.f32",
            "sha256": "0" * 64,
            "byteLength": 36,
            "columns": 3,
            "rows": 3,
            "spacingM": 500.0,
        },
        "extentM": {"width": 1000.0, "depth": 1000.0},
        "axisConvention": "+X east, +Y up, -Z north",
        "aoi": {
            "boundsM": list(aoi.bbox_m),
            "selectionStatus": aoi.selection_status,
            "coverageStatus": aoi.coverage_status,
        },
        "provenance": {
            "verticalReference": "FICTIONAL TEST DATUM",
            "attribution": "Fictional test data",
            "catalogueUrl": "https://example.invalid/terrain",
        },
    }
    (terrain_dir / "manifest.json").write_text(json.dumps(terrain_manifest), encoding="utf-8")
    (terrain_dir / "heightfield.f32").write_bytes(struct.pack("<9f", *([0.0] * 9)))
    fake_identity = {
        "worldId": aoi.id,
        "origin": {"eastingM": center_e, "northingM": center_n, "elevationM": 0.0},
        "heightfieldPath": "heightfield.f32",
        "heightfieldSha256": "0" * 64,
        "heightfieldByteLength": 36,
        "heightfieldDimensions": [3, 3],
        "verticalReference": "FICTIONAL TEST DATUM",
    }
    monkeypatch.setattr(road_export, "_terrain_identity", lambda *_args: fake_identity)

    ring = _configured_aoi_ring(aoi)
    selection, _geojson, _markdown = generate_selection(aoi)
    geojson_path = tmp_path / "aoi.geojson"
    geojson_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Polygon", "coordinates": [ring]},
                        "properties": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    package = tmp_path / "package"
    external_qa = tmp_path / "external-qa.json"
    preview = tmp_path / Path(config.preview_path).name
    intermediate = tmp_path / "intermediate.json"
    imported = import_osm_roads(source, source_manifest_path, aoi, config)
    build_road_package(
        imported,
        aoi,
        config,
        source,
        source_manifest_path,
        terrain_dir,
        geojson_path,
        package,
        external_qa,
        preview,
        intermediate,
    )
    manifest_data = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    roads_data = json.loads((package / "roads.json").read_text(encoding="utf-8"))
    qa_data = json.loads((package / "qa.json").read_text(encoding="utf-8"))
    line_part_count = sum(len(feature["partIds"]) for feature in roads_data["features"])
    ribbon_component_count = sum(
        len(feature["ribbonPartIds"]) for feature in roads_data["features"]
    )
    assert manifest_data["counts"]["uniquePartIds"] == line_part_count
    assert manifest_data["counts"]["uniqueRibbonPartIds"] == ribbon_component_count
    assert (
        manifest_data["counts"]["float32CollapsedSliverTriangleCount"]
        == qa_data["meshNumerics"]["float32CollapsedSliverTriangleCount"]
    )
    assert qa_data["counts"]["uniquePartIds"] == line_part_count
    assert qa_data["displayBatches"]["vehicular"]["clippedCenterlinePartCount"] == line_part_count
    kwargs = {
        "expected_aoi": aoi,
        "expected_aoi_ring": ring,
        "terrain_package_path": terrain_dir,
        "source_path": source,
        "source_manifest_path": source_manifest_path,
        "aoi_geojson_path": geojson_path,
        "road_config": config,
    }
    assert validate_road_package(package, **kwargs)["featureCount"] == 1

    roads_path = package / "roads.json"
    manifest_path = package / "manifest.json"
    payload = json.loads(roads_path.read_text(encoding="utf-8"))
    payload["features"][0]["centerlinePartsXZ"][0][0][0] += 1.0
    roads_bytes = road_export._json_bytes(payload)
    roads_path.write_bytes(roads_bytes)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"]["roads"]["byteLength"] = len(roads_bytes)
    manifest["assets"]["roads"]["sha256"] = hashlib.sha256(roads_bytes).hexdigest()
    manifest_path.write_bytes(road_export._json_bytes(manifest))
    with pytest.raises(RoadExportError, match="does not match deterministic output re-derived"):
        validate_road_package(package, **kwargs)
