from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from torquay_pipeline import overview_export, overview_publish
from torquay_pipeline.overview_export import (
    DEFAULT_AOI_GEOJSON,
    OverviewExportError,
    _assert_disjoint_paths,
    _build_features,
    _coordinate_transformer,
    _CoordinateWriter,
    _layer_identity,
    _load_aoi_ring,
    _normalize_ring,
    _write_package,
)


def _writer() -> _CoordinateWriter:
    inverse, forward, _metadata = _coordinate_transformer()
    return _CoordinateWriter(
        {
            "eastingM": 291108.9018176432,
            "northingM": 65353.48350844931,
            "elevationM": 47.59241548392676,
        },
        inverse,
        forward,
    )


def test_local_xz_in_all_quadrants_maps_east_right_and_north_up() -> None:
    writer = _writer()
    northwest = writer.point(-250, -250, "northwest")
    northeast = writer.point(250, -250, "northeast")
    southwest = writer.point(-250, 250, "southwest")
    southeast = writer.point(250, 250, "southeast")

    assert northeast[0] > northwest[0]
    assert southeast[0] > southwest[0]
    assert northwest[1] > southwest[1]
    assert northeast[1] > southeast[1]
    assert writer.maximum_roundtrip_m <= 0.02


@pytest.mark.parametrize("x,z", [(True, 0), (0, False), (math.inf, 1), (1, math.nan)])
def test_local_transform_rejects_bool_and_nonfinite_coordinates(x: object, z: object) -> None:
    with pytest.raises(OverviewExportError, match="finite numeric local XZ"):
        _writer().point(x, z, "fixture")


def test_ring_winding_is_normalized_and_closed() -> None:
    clockwise = [[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]
    normalized = _normalize_ring(clockwise, exterior=True)
    signed_area = sum(
        left[0] * right[1] - right[0] * left[1]
        for left, right in zip(normalized[:-1], normalized[1:], strict=True)
    )
    assert signed_area > 0
    assert normalized[0] == normalized[-1]


def test_feature_conversion_preserves_disconnected_roads_components_and_holes() -> None:
    ring = _load_aoi_ring(DEFAULT_AOI_GEOJSON)
    inverse, forward, _metadata = _coordinate_transformer()
    origin = {
        "eastingM": 291108.9018176432,
        "northingM": 65353.48350844931,
        "elevationM": 47.59241548392676,
    }
    roads = [
        {
            "id": "30480035",
            "highway": "residential",
            "displayGroup": "vehicular",
            "sourceTags": {"name": "Example Road"},
            "centerlinePartsXZ": [
                [[-40, -40], [-30, -30]],
                [[30, 30], [40, 40]],
            ],
        },
        {
            "id": "no-clipped-centreline",
            "highway": "residential",
            "displayGroup": "vehicular",
            "sourceTags": {},
            "centerlinePartsXZ": [],
        },
    ]
    buildings = [
        {
            "id": "way/100",
            "source": {"osmId": 100},
            "geometry": {
                "polygons": [
                    {
                        "exteriorXZ": [
                            [-20, -20],
                            [20, -20],
                            [20, 20],
                            [-20, 20],
                            [-20, -20],
                        ],
                        "interiorRingsXZ": [
                            [
                                [-4, -4],
                                [-4, 4],
                                [4, 4],
                                [4, -4],
                                [-4, -4],
                            ]
                        ],
                    },
                    {
                        "exteriorXZ": [
                            [40, -20],
                            [50, -20],
                            [50, -10],
                            [40, -10],
                            [40, -20],
                        ],
                        "interiorRingsXZ": [],
                    },
                ]
            },
        }
    ]
    payload, counts, positions, max_roundtrip = _build_features(
        ring, origin, roads, buildings, inverse, forward
    )

    road = payload["features"][1]
    building = payload["features"][2]
    assert road["geometry"]["type"] == "MultiLineString"
    assert len(road["geometry"]["coordinates"]) == 2
    assert building["geometry"]["type"] == "MultiPolygon"
    assert len(building["geometry"]["coordinates"]) == 2
    assert len(building["geometry"]["coordinates"][0]) == 2
    assert counts["roadsWithoutAoiCenterline"] == 1
    assert positions["total"] == sum(positions[key] for key in ("aoi", "roads", "buildings"))
    assert max_roundtrip <= 0.02


def test_output_cannot_overlap_any_source_or_raw_data(tmp_path: Path) -> None:
    source = tmp_path / "roads"
    source.mkdir()
    with pytest.raises(OverviewExportError, match="overlaps"):
        _assert_disjoint_paths(source / "overview", [source])
    with pytest.raises(OverviewExportError, match="overlaps"):
        _assert_disjoint_paths(source, [source / "roads.json"])


def test_atomic_package_write_restores_previous_bytes_if_install_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "overview"
    output.mkdir()
    (output / "manifest.json").write_bytes(b"previous manifest\n")
    (output / "features.geojson").write_bytes(b"previous features\n")
    before = {path.name: path.read_bytes() for path in output.iterdir()}
    real_replace = overview_export.os.replace
    replace_count = 0

    def fail_stage_install(source: Path, destination: Path) -> None:
        nonlocal replace_count
        replace_count += 1
        if replace_count == 2:
            raise OSError("injected stage install failure")
        real_replace(source, destination)

    monkeypatch.setattr(overview_export.os, "replace", fail_stage_install)
    with pytest.raises(OverviewExportError, match="injected stage install failure"):
        _write_package(
            output,
            {"features.geojson": b"new feature", "manifest.json": b"new manifest"},
        )
    assert {path.name: path.read_bytes() for path in output.iterdir()} == before


def test_publication_rollback_keeps_previous_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "source-overview"
    package.mkdir()
    (package / "features.geojson").write_bytes(b"features")
    (package / "manifest.json").write_bytes(b"manifest")
    terrain = tmp_path / "terrain"
    terrain.mkdir()
    roads = terrain / "roads"
    buildings = terrain / "buildings"
    output = terrain / "overview"
    output.mkdir()
    (output / "sentinel").write_bytes(b"old data")
    before = {path.name: path.read_bytes() for path in output.iterdir()}

    monkeypatch.setattr(
        overview_publish,
        "validate_overview_package",
        lambda *_args, **_kwargs: {"status": "valid"},
    )
    real_replace = overview_publish.os.replace
    replace_count = 0

    def fail_publish_install(source: Path, destination: Path) -> None:
        nonlocal replace_count
        replace_count += 1
        if replace_count == 2:
            raise OSError("injected publish install failure")
        real_replace(source, destination)

    monkeypatch.setattr(overview_publish.os, "replace", fail_publish_install)
    with pytest.raises(
        overview_publish.OverviewPublishError, match="injected publish install failure"
    ):
        overview_publish.publish_overview_package(
            package,
            output_dir=output,
            terrain_dir=terrain,
            roads_dir=roads,
            buildings_dir=buildings,
        )
    assert {path.name: path.read_bytes() for path in output.iterdir()} == before


def test_cli_output_json_is_deterministic_without_runtime_timestamp() -> None:
    # The byte-for-byte source-backed build is run as an acceptance command; this
    # focused check pins the serializer's stable newline and key behavior.
    content = overview_export._json_bytes({"b": 2, "a": 1})
    assert content == b'{"b":2,"a":1}\n'
    assert json.loads(content) == {"b": 2, "a": 1}


@pytest.mark.parametrize("kind", ["roads", "buildings"])
def test_layer_identity_uses_the_package_specific_terrain_manifest_hash(
    tmp_path: Path, kind: str
) -> None:
    package = tmp_path / kind
    package.mkdir()
    payload_name = "roads.json" if kind == "roads" else "buildings.json"
    payload_bytes = b'{"features":[]}'
    qa_bytes = b'{"status":"valid"}'
    (package / payload_name).write_bytes(payload_bytes)
    (package / "qa.json").write_bytes(qa_bytes)
    payload_identity = {
        "byteLength": len(payload_bytes),
        "sha256": hashlib.sha256(payload_bytes).hexdigest(),
    }
    qa_identity = {
        "path": "qa.json",
        "byteLength": len(qa_bytes),
        "sha256": hashlib.sha256(qa_bytes).hexdigest(),
    }
    terrain_sha = "a" * 64 if kind == "roads" else "b" * 64
    manifest: dict[str, object] = {}
    if kind == "roads":
        manifest.update(
            {
                "assets": {"roads": payload_identity, "qa": qa_identity},
                "source": {"sha256": "c" * 64},
                "terrainIdentity": {"manifestSha256": terrain_sha},
            }
        )
    else:
        manifest.update(
            {
                "buildings": payload_identity,
                "qaReport": qa_identity,
                "provenance": {"sha256": "d" * 64},
                "terrainManifestSha256": terrain_sha,
            }
        )
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    identity = _layer_identity(package, kind, terrain_sha)

    assert identity["terrainManifestSha256"] == terrain_sha


def test_layer_identity_rejects_roads_bound_to_another_terrain(tmp_path: Path) -> None:
    package = tmp_path / "roads"
    package.mkdir()
    payload_bytes = b'{"features":[]}'
    qa_bytes = b'{"status":"valid"}'
    (package / "roads.json").write_bytes(payload_bytes)
    (package / "qa.json").write_bytes(qa_bytes)
    manifest = {
        "assets": {
            "roads": {
                "byteLength": len(payload_bytes),
                "sha256": hashlib.sha256(payload_bytes).hexdigest(),
            },
            "qa": {
                "path": "qa.json",
                "byteLength": len(qa_bytes),
                "sha256": hashlib.sha256(qa_bytes).hexdigest(),
            },
        },
        "source": {},
        "terrainIdentity": {"manifestSha256": "a" * 64},
    }
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(OverviewExportError, match="different terrain package"):
        _layer_identity(package, "roads", "b" * 64)
