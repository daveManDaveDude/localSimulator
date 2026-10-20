from __future__ import annotations

import json
from pathlib import Path

import pytest

from torquay_pipeline.scene_build import (
    PROJECT_ROOT,
    SceneBuildError,
    _cleanup_failed_stage,
    _measure_outer_annulus,
    _validate_output_path,
)


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
