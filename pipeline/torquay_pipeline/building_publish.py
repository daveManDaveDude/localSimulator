"""Safely publish the validated OSM building package beside the EA terrain."""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from .aoi import AoiConfig
from .building_export import BuildingExportError, validate_building_package

PUBLISHED_FILES = ("manifest.json", "buildings.json", "qa.json")


class BuildingPublishError(ValueError):
    """Raised when a validated building package cannot be safely published."""


def _write_staged_file(path: Path, content: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def publish_building_package(
    source_package_path: Path,
    terrain_package_path: Path,
    *,
    expected_aoi: AoiConfig,
    expected_aoi_ring: list[list[float]],
    source_path: Path,
    source_manifest_path: Path,
) -> dict[str, Any]:
    """Validate, stage, revalidate, and replace only ``terrain/buildings``.

    The generated publisher output is intentionally kept outside the terrain
    package's root files. A failed stage or directory swap leaves the previous
    ``buildings`` directory in place; terrain files are never part of the move.
    """
    terrain_root = terrain_package_path.resolve()
    source_root = source_package_path.resolve()
    output_root = terrain_root / "buildings"
    if source_root == output_root or source_root == terrain_root:
        raise BuildingPublishError("source package must be separate from the terrain output")
    if not terrain_root.is_dir():
        raise BuildingPublishError(f"terrain package does not exist: {terrain_root}")
    if output_root.exists() and output_root.is_symlink():
        raise BuildingPublishError(f"refusing to replace a symbolic-link output: {output_root}")

    try:
        source_validation = validate_building_package(
            source_root,
            expected_aoi=expected_aoi,
            expected_aoi_ring=expected_aoi_ring,
            terrain_package_path=terrain_root,
            source_path=source_path,
            source_manifest_path=source_manifest_path,
        )
    except BuildingExportError as exc:
        raise BuildingPublishError(f"source package validation failed: {exc}") from exc

    try:
        content = {name: (source_root / name).read_bytes() for name in PUBLISHED_FILES}
    except OSError as exc:
        raise BuildingPublishError(f"cannot read validated source package: {exc}") from exc

    try:
        stage_root = Path(tempfile.mkdtemp(prefix=".buildings-stage-", dir=terrain_root))
    except OSError as exc:
        raise BuildingPublishError(f"cannot create staging directory: {exc}") from exc

    backup_root = terrain_root / f".buildings-backup-{uuid.uuid4().hex}"
    previous_moved = False
    try:
        for name, data in content.items():
            _write_staged_file(stage_root / name, data)

        staged_validation = validate_building_package(
            stage_root,
            expected_aoi=expected_aoi,
            expected_aoi_ring=expected_aoi_ring,
            terrain_package_path=terrain_root,
            source_path=source_path,
            source_manifest_path=source_manifest_path,
        )
        for name in PUBLISHED_FILES:
            if (stage_root / name).read_bytes() != (source_root / name).read_bytes():
                raise BuildingPublishError(f"staged {name} is not byte-identical to its source")

        if output_root.exists():
            if not output_root.is_dir():
                raise BuildingPublishError(f"published output is not a directory: {output_root}")
            os.replace(output_root, backup_root)
            previous_moved = True
        os.replace(stage_root, output_root)
    except (BuildingExportError, BuildingPublishError, OSError) as exc:
        rollback_detail = ""
        if previous_moved and backup_root.exists() and not output_root.exists():
            try:
                os.replace(backup_root, output_root)
            except OSError as rollback_error:
                rollback_detail = f"; restoring the previous output also failed: {rollback_error}"
        if isinstance(exc, BuildingPublishError):
            raise BuildingPublishError(f"{exc}{rollback_detail}") from exc
        raise BuildingPublishError(
            f"could not publish validated building package: {exc}{rollback_detail}"
        ) from exc
    finally:
        if stage_root.exists():
            shutil.rmtree(stage_root, ignore_errors=True)

    if previous_moved:
        shutil.rmtree(backup_root)

    return {
        "sourceValidation": source_validation,
        "publishedValidation": staged_validation,
        "outputDirectory": str(output_root),
        "files": {name: {"byteLength": len(data)} for name, data in content.items()},
    }
