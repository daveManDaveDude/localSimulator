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
        _assert_disjoint_paths(source / "overview", input_directories=[source], input_files=[])
    with pytest.raises(OverviewExportError, match="overlaps"):
        _assert_disjoint_paths(source, input_directories=[], input_files=[source / "roads.json"])


def test_build_rejects_all_protected_locations_before_deriving_or_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    aoi_json = overview_export.DEFAULT_AOI_GEOJSON.read_bytes()
    source_manifest = overview_export.DEFAULT_SOURCE_MANIFEST.read_bytes()
    terrain_manifest = (overview_export.DEFAULT_TERRAIN_DIR / "manifest.json").read_bytes()
    terrain_heightfield = (overview_export.DEFAULT_TERRAIN_DIR / "heightfield.f32").read_bytes()
    dangerous_outputs = [
        overview_export.ROOT / "docs",
        overview_export.ROOT / "docs" / "m8-must-not-exist",
        overview_export.DEFAULT_AOI_CONFIG,
        overview_export.DEFAULT_AOI_GEOJSON,
        overview_export.DEFAULT_ROAD_CONFIG,
        overview_export.DEFAULT_BUILDING_CONFIG,
        overview_export.ROOT / "config",
        overview_export.ROOT / "data" / "source-manifest.json",
        overview_export.ROOT / "data" / "raw",
        overview_export.ROOT / "data" / "raw" / "m8-must-not-exist",
        overview_export.DEFAULT_TERRAIN_DIR,
        overview_export.DEFAULT_TERRAIN_DIR / "manifest.json",
        overview_export.DEFAULT_TERRAIN_DIR / "heightfield.f32",
        overview_export.DEFAULT_ROADS_DIR,
        overview_export.DEFAULT_BUILDINGS_DIR,
    ]

    def unexpected_derive(**_kwargs: object) -> dict[str, bytes]:
        pytest.fail("path safety must reject before reading or deriving package inputs")

    monkeypatch.setattr(overview_export, "_derive_package", unexpected_derive)
    for output in dangerous_outputs:
        with pytest.raises(OverviewExportError, match="overlap"):
            overview_export.build_overview_package(layers=("aoi",), output_dir=output)
    assert overview_export.DEFAULT_AOI_GEOJSON.read_bytes() == aoi_json
    assert overview_export.DEFAULT_SOURCE_MANIFEST.read_bytes() == source_manifest
    assert (overview_export.DEFAULT_TERRAIN_DIR / "manifest.json").read_bytes() == terrain_manifest
    assert (
        overview_export.DEFAULT_TERRAIN_DIR / "heightfield.f32"
    ).read_bytes() == terrain_heightfield
    assert not (overview_export.ROOT / "docs" / "m8-must-not-exist").exists()
    assert not (overview_export.ROOT / "data" / "raw" / "m8-must-not-exist").exists()
    assert not (overview_export.DEFAULT_ROADS_DIR / "m8-must-not-exist").exists()


def test_output_symlink_or_junction_component_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    linked_parent = tmp_path / "linked-parent"
    real_check = overview_export._is_symlink_or_junction
    monkeypatch.setattr(
        overview_export,
        "_is_symlink_or_junction",
        lambda path: path == linked_parent or real_check(path),
    )
    with pytest.raises(OverviewExportError, match="symbolic-link/junction"):
        overview_export._safe_output_path(linked_parent / "new-output")


def test_atomic_package_write_restores_previous_bytes_if_install_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "overview"
    output.mkdir()
    (output / "manifest.json").write_bytes(b"previous manifest\n")
    (output / "features.geojson").write_bytes(b"previous features\n")
    before = {path.name: path.read_bytes() for path in output.iterdir()}
    unowned_backup = tmp_path / ".overview-backup"
    unowned_backup.mkdir()
    (unowned_backup / "keep.txt").write_bytes(b"unowned backup")
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
    assert (unowned_backup / "keep.txt").read_bytes() == b"unowned backup"


def test_fixed_name_unowned_backup_is_preserved_during_successful_build(
    tmp_path: Path,
) -> None:
    output = tmp_path / "overview"
    output.mkdir()
    (output / "old.txt").write_bytes(b"old output")
    unowned_backup = tmp_path / ".overview-backup"
    unowned_backup.mkdir()
    (unowned_backup / "keep.txt").write_bytes(b"unowned backup")

    _write_package(output, {"features.geojson": b"features", "manifest.json": b"manifest"})

    assert (output / "manifest.json").read_bytes() == b"manifest"
    assert (unowned_backup / "keep.txt").read_bytes() == b"unowned backup"


def test_build_fails_safely_when_unique_backup_name_is_already_owned_elsewhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "overview"
    output.mkdir()
    (output / "old.txt").write_bytes(b"old output")
    existing_backup = tmp_path / ".overview-backup-reserved"
    existing_backup.mkdir()
    (existing_backup / "keep.txt").write_bytes(b"unowned")

    class FixedUuid:
        hex = "reserved"

    monkeypatch.setattr(overview_export.uuid, "uuid4", lambda: FixedUuid())
    with pytest.raises(OverviewExportError, match="pre-existing overview backup path"):
        _write_package(output, {"features.geojson": b"features", "manifest.json": b"manifest"})

    assert (output / "old.txt").read_bytes() == b"old output"
    assert (existing_backup / "keep.txt").read_bytes() == b"unowned"


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
    unowned_backup = output.parent / ".overview-backup"
    unowned_backup.mkdir()
    (unowned_backup / "keep.txt").write_bytes(b"unowned backup")

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
    assert (unowned_backup / "keep.txt").read_bytes() == b"unowned backup"


def test_publish_rejects_protected_outputs_before_validation_or_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "source-overview"
    package.mkdir()
    (package / "manifest.json").write_bytes(b"source manifest")
    (package / "features.geojson").write_bytes(b"source features")
    aoi_json = DEFAULT_AOI_GEOJSON.read_bytes()
    source_manifest = overview_export.DEFAULT_SOURCE_MANIFEST.read_bytes()
    terrain_manifest = (overview_export.DEFAULT_TERRAIN_DIR / "manifest.json").read_bytes()
    terrain_heightfield = (overview_export.DEFAULT_TERRAIN_DIR / "heightfield.f32").read_bytes()
    dangerous_outputs = [
        overview_export.ROOT / "docs",
        overview_export.DEFAULT_AOI_CONFIG,
        overview_export.DEFAULT_AOI_GEOJSON,
        overview_export.DEFAULT_ROAD_CONFIG,
        overview_export.DEFAULT_BUILDING_CONFIG,
        overview_export.ROOT / "config",
        overview_export.ROOT / "data" / "source-manifest.json",
        overview_export.ROOT / "data" / "raw",
        overview_export.ROOT / "data" / "raw" / "m8-publish-must-not-exist",
        overview_export.DEFAULT_TERRAIN_DIR,
        overview_export.DEFAULT_TERRAIN_DIR / "manifest.json",
        overview_export.DEFAULT_TERRAIN_DIR / "heightfield.f32",
        overview_export.DEFAULT_ROADS_DIR,
        overview_export.DEFAULT_BUILDINGS_DIR,
        overview_export.DEFAULT_TERRAIN_DIR / "overview" / "nested",
        package,
        tmp_path,
    ]

    def unexpected_validation(*_args: object, **_kwargs: object) -> dict[str, str]:
        pytest.fail("path safety must reject before package validation")

    monkeypatch.setattr(overview_publish, "validate_overview_package", unexpected_validation)
    for output in dangerous_outputs:
        with pytest.raises(overview_publish.OverviewPublishError, match="overlap"):
            overview_publish.publish_overview_package(
                package,
                output_dir=output,
            )
    shared_source_parent = tmp_path / "shared-source-parent"
    shared_source_parent.mkdir()
    with pytest.raises(overview_publish.OverviewPublishError, match="overlap"):
        overview_publish.publish_overview_package(
            package,
            output_dir=shared_source_parent / "overview",
            terrain_dir=shared_source_parent,
            roads_dir=shared_source_parent,
            buildings_dir=tmp_path / "buildings",
        )
    assert (package / "manifest.json").read_bytes() == b"source manifest"
    assert (package / "features.geojson").read_bytes() == b"source features"
    assert DEFAULT_AOI_GEOJSON.read_bytes() == aoi_json
    assert overview_export.DEFAULT_SOURCE_MANIFEST.read_bytes() == source_manifest
    assert (overview_export.DEFAULT_TERRAIN_DIR / "manifest.json").read_bytes() == terrain_manifest
    assert (
        overview_export.DEFAULT_TERRAIN_DIR / "heightfield.f32"
    ).read_bytes() == terrain_heightfield
    assert not (overview_export.ROOT / "data" / "raw" / "m8-publish-must-not-exist").exists()
    assert not (shared_source_parent / "overview").exists()


def test_publish_fails_safely_on_unowned_backup_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "source"
    package.mkdir()
    (package / "manifest.json").write_bytes(b"manifest")
    (package / "features.geojson").write_bytes(b"features")
    terrain = tmp_path / "terrain"
    terrain.mkdir()
    output = terrain / "overview"
    output.mkdir()
    (output / "old.txt").write_bytes(b"old output")
    existing_backup = terrain / ".overview-backup-reserved"
    existing_backup.mkdir()
    (existing_backup / "keep.txt").write_bytes(b"unowned")
    monkeypatch.setattr(
        overview_publish,
        "validate_overview_package",
        lambda *_args, **_kwargs: {"status": "valid"},
    )

    class FixedUuid:
        hex = "reserved"

    monkeypatch.setattr(overview_publish.uuid, "uuid4", lambda: FixedUuid())
    with pytest.raises(
        overview_publish.OverviewPublishError, match="pre-existing overview backup path"
    ):
        overview_publish.publish_overview_package(
            package,
            output_dir=output,
            terrain_dir=terrain,
            roads_dir=terrain / "roads",
            buildings_dir=terrain / "buildings",
            aoi_config_path=overview_export.DEFAULT_AOI_CONFIG,
            aoi_geojson_path=overview_export.DEFAULT_AOI_GEOJSON,
            source_manifest_path=overview_export.DEFAULT_SOURCE_MANIFEST,
        )

    assert (output / "old.txt").read_bytes() == b"old output"
    assert (existing_backup / "keep.txt").read_bytes() == b"unowned"


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
