"""Safely publish a validated local roads child package."""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from .aoi import AoiConfig
from .road_config import RoadConfig
from .road_export import RoadExportError, validate_road_package


class RoadPublishError(ValueError):
    """Raised when a roads-only package cannot be safely staged or swapped."""


PUBLISHED_FILES = ("manifest.json", "roads.json", "qa.json")


def publish_road_package(
    source_package_path: Path,
    terrain_package_path: Path,
    *,
    expected_aoi: AoiConfig,
    expected_aoi_ring: list[list[float]],
    source_path: Path,
    source_manifest_path: Path,
    aoi_geojson_path: Path | None = None,
    road_config: RoadConfig | None = None,
) -> dict[str, Any]:
    """Validate and replace only terrain/roads; never replace the real-world root."""
    terrain_root = terrain_package_path.resolve()
    source_root = source_package_path.resolve()
    output_root = terrain_root / "roads"
    if (
        source_root == terrain_root
        or source_root.is_relative_to(terrain_root)
        or terrain_root.is_relative_to(source_root)
    ):
        raise RoadPublishError(
            "source package and terrain root must be separate, non-nested directories"
        )
    if output_root.is_symlink():
        raise RoadPublishError(f"refusing to replace a symbolic-link roads target: {output_root}")
    if not terrain_root.is_dir():
        raise RoadPublishError(f"terrain package does not exist: {terrain_root}")
    try:
        source_validation = validate_road_package(
            source_root,
            expected_aoi=expected_aoi,
            expected_aoi_ring=expected_aoi_ring,
            terrain_package_path=terrain_root,
            source_path=source_path,
            source_manifest_path=source_manifest_path,
            aoi_geojson_path=aoi_geojson_path,
            road_config=road_config,
        )
        contents = {name: (source_root / name).read_bytes() for name in PUBLISHED_FILES}
    except (RoadExportError, OSError) as exc:
        raise RoadPublishError(f"roads source package validation/read failed: {exc}") from exc

    try:
        stage_root = Path(tempfile.mkdtemp(prefix=".roads-stage-", dir=terrain_root))
    except OSError as exc:
        raise RoadPublishError(f"cannot create roads staging directory: {exc}") from exc
    backup_root = terrain_root / f".roads-backup-{uuid.uuid4().hex}"
    previous_moved = False
    try:
        for filename, content in contents.items():
            target = stage_root / filename
            with target.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        for filename, content in contents.items():
            if (stage_root / filename).read_bytes() != content:
                raise RoadPublishError(f"staged {filename} differs from the validated source bytes")
        if output_root.exists():
            if not output_root.is_dir():
                raise RoadPublishError(f"roads target is not a directory: {output_root}")
            os.replace(output_root, backup_root)
            previous_moved = True
        os.replace(stage_root, output_root)
    except (RoadExportError, RoadPublishError, OSError) as exc:
        rollback_detail = ""
        if previous_moved and backup_root.exists() and not output_root.exists():
            try:
                os.replace(backup_root, output_root)
            except OSError as rollback_error:
                rollback_detail = f"; restoring the prior roads package failed: {rollback_error}"
        if isinstance(exc, RoadPublishError):
            raise RoadPublishError(f"{exc}{rollback_detail}") from exc
        raise RoadPublishError(
            f"could not publish the validated roads package: {exc}{rollback_detail}"
        ) from exc
    finally:
        if stage_root.exists():
            shutil.rmtree(stage_root, ignore_errors=True)
    if previous_moved:
        shutil.rmtree(backup_root)
    return {
        "sourceValidation": source_validation,
        "publishedValidation": {
            "status": "byte-identical staged copy of the source-validated package",
            "roadsSha256": source_validation["roadsSha256"],
            "qaSha256": source_validation["qaSha256"],
        },
        "outputDirectory": str(output_root),
        "files": {filename: {"byteLength": len(content)} for filename, content in contents.items()},
    }
