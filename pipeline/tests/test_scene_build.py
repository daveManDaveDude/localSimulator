from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from torquay_pipeline.scene_build import (
    PROJECT_ROOT,
    SceneBuildError,
    _cleanup_failed_stage,
    _measure_outer_annulus,
    _validate_output_path,
    build_scene_package,
)
from torquay_pipeline.scene_release import (
    SceneReleaseError,
    assert_no_reparse_components,
)


def _make_directory_junction(path: Path, target: Path) -> None:
    if os.name != "nt":
        pytest.skip("Windows directory junction regression requires Windows")
    path.parent.mkdir(parents=True, exist_ok=True)
    target.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["cmd.exe", "/c", f"mklink /J {path} {target}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not path.is_junction():
        pytest.skip(f"this Windows filesystem cannot create a junction: {result.stderr}")


def test_current_package_destination_is_safe_and_historic_package_is_protected(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    output = root / "public" / "worlds" / "torquay-poc-001-2km"

    assert (
        _validate_output_path(
            output,
            project_root=root,
            protected_inputs=[root / "data/raw/osm/source.osm.pbf"],
        )
        == output.resolve()
    )
    with pytest.raises(SceneBuildError, match="overlaps protected input"):
        _validate_output_path(
            root / "public" / "worlds" / "torquay-poc-001",
            project_root=root,
            protected_inputs=[],
        )


@pytest.mark.parametrize(
    "relative_target",
    [
        Path("docs"),
        Path("config"),
        Path("config/buildings.torquay-2km.json"),
        Path("data/raw"),
        Path("data/raw/osm/devon-261016.osm.pbf"),
        Path("public/worlds/torquay-poc-001"),
    ],
)
def test_output_rejects_protected_ancestors_and_exact_inputs(
    tmp_path: Path, relative_target: Path
) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    with pytest.raises(SceneBuildError, match="overlaps protected input"):
        _validate_output_path(
            root / relative_target,
            project_root=root,
            protected_inputs=[root / "config/buildings.torquay-2km.json"],
        )


def test_output_junction_is_rejected_before_any_write(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    protected_target = tmp_path / "protected-target"
    root.mkdir()
    protected_target.mkdir()
    sentinel = protected_target / "sentinel.txt"
    sentinel.write_text("preserve", encoding="utf-8")
    public_junction = root / "public"
    _make_directory_junction(public_junction, protected_target)

    with pytest.raises(SceneBuildError, match="junction/reparse"):
        _validate_output_path(
            public_junction / "worlds" / "torquay-poc-001-2km",
            project_root=root,
            protected_inputs=[root / "config/aoi.json"],
        )

    assert sentinel.read_text(encoding="utf-8") == "preserve"
    assert not (protected_target / "worlds").exists()


def test_lexical_junction_is_rejected_before_parent_segments_are_normalized(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    target = tmp_path / "junction-target"
    root.mkdir()
    target.mkdir()
    link = root / "linked"
    _make_directory_junction(link, target)
    lexical_path = link / ".." / "outside.txt"

    with pytest.raises(SceneReleaseError, match="junction/reparse"):
        assert_no_reparse_components(lexical_path)


@pytest.mark.parametrize("junction_argument", ["source_dir", "aoi_config_path"])
def test_build_rejects_junction_inputs_before_generation_or_output_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, junction_argument: str
) -> None:
    root = tmp_path / "workspace"
    target = tmp_path / "protected-source"
    root.mkdir()
    target.mkdir()
    sentinel = target / "sentinel.txt"
    sentinel.write_text("source remains intact", encoding="utf-8")
    link = root / "source-link"
    _make_directory_junction(link, target)
    output = root / "public/worlds/torquay-poc-001-2km"
    kwargs = {
        "aoi_config_path": root / "config/aoi.json",
        "source_manifest_path": root / "data/source-manifest.json",
        "source_dir": root / "data/raw/ea_dtm",
        "source_path": root / "data/raw/osm/source.osm.pbf",
        "buildings_config_path": root / "config/buildings.json",
        "roads_config_path": root / "config/roads.json",
        "output_dir": output,
        "project_root": root,
    }
    kwargs[junction_argument] = link if junction_argument == "source_dir" else link / "aoi.json"

    with pytest.raises(SceneBuildError, match="junction/reparse"):
        build_scene_package(**kwargs)

    assert sentinel.read_text(encoding="utf-8") == "source remains intact"
    assert not output.exists()


@pytest.mark.parametrize("junction_kind", ["output", "source"])
def test_build_scene_cli_rejects_junction_before_calling_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    junction_kind: str,
) -> None:
    from torquay_pipeline import cli

    root = tmp_path / "workspace"
    target = tmp_path / "target"
    root.mkdir()
    target.mkdir()
    sentinel = target / "sentinel.txt"
    sentinel.write_text("preserve", encoding="utf-8")
    link = root / ("public" if junction_kind == "output" else "raw-link")
    _make_directory_junction(link, target)
    monkeypatch.setattr(cli, "PROJECT_ROOT", root)
    monkeypatch.setattr(
        cli,
        "build_scene_package",
        lambda **_kwargs: pytest.fail("builder must not run for a junction path"),
    )
    monkeypatch.chdir(root)
    output = link / "torquay-poc-001-2km" if junction_kind == "output" else root / "output"
    source_dir = link if junction_kind == "source" else root / "data/raw/ea_dtm"

    result = cli.main(
        [
            "build-scene",
            "--aoi-config",
            str(root / "config/aoi.json"),
            "--source-manifest",
            str(root / "data/source-manifest.json"),
            "--source-dir",
            str(source_dir),
            "--source",
            str(source_dir / "source.osm.pbf"),
            "--buildings-config",
            str(root / "config/buildings.json"),
            "--roads-config",
            str(root / "config/roads.json"),
            "--output-dir",
            str(output),
        ]
    )

    assert result == 2
    assert "junction/reparse" in capsys.readouterr().err
    assert sentinel.read_text(encoding="utf-8") == "preserve"
    assert not (root / "output").exists()


def test_failed_unvalidated_stage_is_removed(tmp_path: Path) -> None:
    stage = tmp_path / ".scene.stage-owned"
    stage.mkdir()
    (stage / "manifest.json").write_text('{"partial":true}\n', encoding="utf-8")

    preserved = _cleanup_failed_stage(stage, validated=False)

    assert not preserved
    assert not stage.exists()


def test_failed_validated_stage_is_preserved_for_publication_retry(tmp_path: Path) -> None:
    stage = tmp_path / ".scene.stage-owned"
    stage.mkdir()
    (stage / "manifest.json").write_text('{"validated":true}\n', encoding="utf-8")

    preserved = _cleanup_failed_stage(stage, validated=True)

    assert preserved
    assert (stage / "manifest.json").read_text(encoding="utf-8") == '{"validated":true}\n'


def test_outer_annulus_is_measured_from_emitted_buildings_and_roads(
    tmp_path: Path,
) -> None:
    package = tmp_path / "package"
    (package / "buildings").mkdir(parents=True)
    (package / "roads").mkdir()
    (package / "buildings/buildings.json").write_text(
        json.dumps(
            {
                "buildings": [
                    {
                        "id": "way/annulus",
                        "geometry": {
                            "polygons": [
                                {
                                    "exteriorXZ": [
                                        [600, 600],
                                        [610, 600],
                                        [610, 610],
                                        [600, 610],
                                        [600, 600],
                                    ],
                                    "interiorRingsXZ": [],
                                }
                            ]
                        },
                    },
                    {
                        "id": "way/old-square",
                        "geometry": {
                            "polygons": [
                                {
                                    "exteriorXZ": [
                                        [10, 10],
                                        [20, 10],
                                        [20, 20],
                                        [10, 20],
                                        [10, 10],
                                    ],
                                    "interiorRingsXZ": [],
                                }
                            ]
                        },
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (package / "roads/roads.json").write_text(
        json.dumps(
            {
                "features": [
                    {
                        "source": {"osmId": 9001},
                        "centerlinePartsXZ": [[[700, 700], [800, 800]]],
                    },
                    {
                        "source": {"osmId": 9002},
                        "centerlinePartsXZ": [[[10, 10], [20, 20]]],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    report = _measure_outer_annulus(package)

    assert report["buildingFeatureCount"] == 1
    assert report["buildingFeatureIdsSample"] == ["way/annulus"]
    assert report["roadWayCount"] == 1
    assert report["roadWayIdsSample"] == ["way/9001"]


def test_default_project_root_is_the_checkout() -> None:
    assert (PROJECT_ROOT / "docs/project-plan.md").is_file()
