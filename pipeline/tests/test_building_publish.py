"""Atomic local publication tests use tiny offline package bytes."""

from __future__ import annotations

from pathlib import Path

import pytest

import torquay_pipeline.building_publish as publisher
from torquay_pipeline.building_export import BuildingExportError
from torquay_pipeline.config import load_aoi_config

ROOT = Path(__file__).resolve().parents[2]
AOI = load_aoi_config(ROOT / "config" / "aoi.torquay-1km.json")
FILES = {
    "manifest.json": b'{"formatVersion":1}',
    "buildings.json": b'{"buildings":[]}',
    "qa.json": b'{"counts":{}}',
}


def _package(path: Path) -> None:
    path.mkdir(parents=True)
    for name, content in FILES.items():
        (path / name).write_bytes(content)


def _validate(_path: Path, **_kwargs) -> dict[str, str]:
    return {"status": "valid"}


def _publish(source: Path, terrain: Path) -> dict[str, object]:
    return publisher.publish_building_package(
        source,
        terrain,
        expected_aoi=AOI,
        expected_aoi_ring=[],
        source_path=Path("source.pbf"),
        source_manifest_path=Path("source-manifest.json"),
    )


def test_publish_copies_validated_files_byte_for_byte_and_preserves_terrain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source-package"
    terrain = tmp_path / "terrain"
    _package(source)
    terrain.mkdir()
    (terrain / "manifest.json").write_bytes(b"terrain manifest stays intact")
    (terrain / "heightfield.f32").write_bytes(b"terrain bytes")
    calls: list[Path] = []

    def validate(path: Path, **_kwargs) -> dict[str, str]:
        calls.append(path)
        return {"status": "valid"}

    monkeypatch.setattr(publisher, "validate_building_package", validate)

    result = _publish(source, terrain)

    output = terrain / "buildings"
    assert result["outputDirectory"] == str(output)
    assert len(calls) == 2
    for name, content in FILES.items():
        assert (output / name).read_bytes() == content
        assert (source / name).read_bytes() == content
    assert (terrain / "manifest.json").read_bytes() == b"terrain manifest stays intact"
    assert (terrain / "heightfield.f32").read_bytes() == b"terrain bytes"


def test_failed_stage_validation_preserves_existing_published_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source-package"
    terrain = tmp_path / "terrain"
    output = terrain / "buildings"
    _package(source)
    terrain.mkdir()
    _package(output)
    old_bytes = {name: (output / name).read_bytes() for name in FILES}
    calls = 0

    def validate(_path: Path, **_kwargs) -> dict[str, str]:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise BuildingExportError("injected stage validation failure")
        return {"status": "valid"}

    monkeypatch.setattr(publisher, "validate_building_package", validate)

    with pytest.raises(publisher.BuildingPublishError, match="injected stage validation"):
        _publish(source, terrain)

    assert {name: (output / name).read_bytes() for name in FILES} == old_bytes
    assert not list(terrain.glob(".buildings-stage-*"))
    assert not list(terrain.glob(".buildings-backup-*"))


def test_failed_directory_swap_rolls_back_previous_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source-package"
    terrain = tmp_path / "terrain"
    output = terrain / "buildings"
    _package(source)
    terrain.mkdir()
    _package(output)
    old_bytes = {name: (output / name).read_bytes() for name in FILES}
    monkeypatch.setattr(publisher, "validate_building_package", _validate)
    original_replace = publisher.os.replace
    failed = False

    def replace_with_one_failure(source_path: Path, target_path: Path) -> None:
        nonlocal failed
        if (
            source_path.name.startswith(".buildings-stage-")
            and target_path == output
            and not failed
        ):
            failed = True
            raise OSError("injected atomic swap failure")
        original_replace(source_path, target_path)

    monkeypatch.setattr(publisher.os, "replace", replace_with_one_failure)

    with pytest.raises(publisher.BuildingPublishError, match="injected atomic swap failure"):
        _publish(source, terrain)

    assert failed
    assert {name: (output / name).read_bytes() for name in FILES} == old_bytes
    assert not list(terrain.glob(".buildings-stage-*"))
    assert not list(terrain.glob(".buildings-backup-*"))


@pytest.mark.parametrize("source_is_nested", [True, False])
def test_publish_rejects_nested_source_and_preserves_all_input_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source_is_nested: bool
) -> None:
    terrain = tmp_path / "terrain"
    terrain.mkdir()
    (terrain / "manifest.json").write_bytes(b"terrain manifest")
    (terrain / "heightfield.f32").write_bytes(b"terrain data")
    if source_is_nested:
        source = terrain / "buildings" / "source"
        _package(source)
    else:
        source = tmp_path / "source"
        _package(source)
        nested_terrain = source / "terrain"
        nested_terrain.mkdir()
        terrain = nested_terrain
        (terrain / "manifest.json").write_bytes(b"terrain manifest")
        (terrain / "heightfield.f32").write_bytes(b"terrain data")
    monkeypatch.setattr(publisher, "validate_building_package", _validate)
    source_before = {
        path.relative_to(source): path.read_bytes() for path in source.rglob("*") if path.is_file()
    }
    terrain_before = {
        path.relative_to(terrain): path.read_bytes()
        for path in terrain.rglob("*")
        if path.is_file()
    }

    with pytest.raises(publisher.BuildingPublishError, match="non-nested"):
        _publish(source, terrain)

    assert {
        path.relative_to(source): path.read_bytes() for path in source.rglob("*") if path.is_file()
    } == source_before
    assert {
        path.relative_to(terrain): path.read_bytes()
        for path in terrain.rglob("*")
        if path.is_file()
    } == terrain_before
    assert not list(terrain.glob(".buildings-stage-*"))
