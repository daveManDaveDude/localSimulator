"""Publish only a validated overview child package with rollback-safe replacement."""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from .overview_export import (
    DEFAULT_AOI_CONFIG,
    DEFAULT_AOI_GEOJSON,
    DEFAULT_BUILDINGS_DIR,
    DEFAULT_ROADS_DIR,
    DEFAULT_SOURCE_MANIFEST,
    DEFAULT_TERRAIN_DIR,
    OVERVIEW_ASSETS,
    ROOT,
    OverviewExportError,
    _repo_path,
    validate_overview_package,
)


class OverviewPublishError(ValueError):
    """Raised when a safe byte-identical overview publication cannot complete."""


def publish_overview_package(
    package_dir: Path,
    *,
    output_dir: Path,
    terrain_dir: Path = DEFAULT_TERRAIN_DIR,
    roads_dir: Path = DEFAULT_ROADS_DIR,
    buildings_dir: Path = DEFAULT_BUILDINGS_DIR,
    aoi_config_path: Path = DEFAULT_AOI_CONFIG,
    aoi_geojson_path: Path = DEFAULT_AOI_GEOJSON,
    source_manifest_path: Path = DEFAULT_SOURCE_MANIFEST,
) -> dict[str, Any]:
    package_dir, output_dir, terrain_dir, roads_dir, buildings_dir = map(
        _repo_path, (package_dir, output_dir, terrain_dir, roads_dir, buildings_dir)
    )
    aoi_config_path, aoi_geojson_path, source_manifest_path = map(
        _repo_path, (aoi_config_path, aoi_geojson_path, source_manifest_path)
    )
    if not terrain_dir.is_dir():
        raise OverviewPublishError(f"terrain package does not exist: {terrain_dir}")
    if output_dir == terrain_dir or terrain_dir.is_relative_to(output_dir):
        raise OverviewPublishError(
            "overview output must not replace or contain the terrain package"
        )
    if output_dir.is_relative_to(terrain_dir) and output_dir != terrain_dir / "overview":
        raise OverviewPublishError(
            "only the dedicated terrain/overview child may be published inside terrain"
        )
    for source in (package_dir, roads_dir, buildings_dir):
        if (
            output_dir == source
            or output_dir.is_relative_to(source)
            or source.is_relative_to(output_dir)
        ):
            raise OverviewPublishError(
                f"overview output '{output_dir}' overlaps protected source package '{source}'"
            )
    raw_root = (ROOT / "data/raw").resolve()
    if (
        output_dir == raw_root
        or output_dir.is_relative_to(raw_root)
        or raw_root.is_relative_to(output_dir)
    ):
        raise OverviewPublishError("overview output must not overlap raw source data")
    if output_dir.is_symlink():
        raise OverviewPublishError(f"refusing to replace symbolic-link output: {output_dir}")
    try:
        validation = validate_overview_package(
            package_dir,
            terrain_dir=terrain_dir,
            roads_dir=roads_dir,
            buildings_dir=buildings_dir,
            aoi_config_path=aoi_config_path,
            aoi_geojson_path=aoi_geojson_path,
            source_manifest_path=source_manifest_path,
        )
        contents = {name: (package_dir / name).read_bytes() for name in OVERVIEW_ASSETS}
    except (OverviewExportError, OSError) as exc:
        raise OverviewPublishError(f"source overview package validation failed: {exc}") from exc

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        stage = Path(tempfile.mkdtemp(prefix=".overview-stage-", dir=output_dir.parent))
    except OSError as exc:
        raise OverviewPublishError(f"cannot create overview staging directory: {exc}") from exc
    backup = output_dir.parent / f".overview-backup-{uuid.uuid4().hex}"
    moved_old = False
    try:
        # The checked manifest is staged last so a partially written pair is never published.
        for name in ("features.geojson", "manifest.json"):
            with (stage / name).open("xb") as handle:
                handle.write(contents[name])
                handle.flush()
                os.fsync(handle.fileno())
        for name in OVERVIEW_ASSETS:
            if (stage / name).read_bytes() != contents[name]:
                raise OverviewPublishError(f"staged {name} differs from its validated source bytes")
        validate_overview_package(
            stage,
            terrain_dir=terrain_dir,
            roads_dir=roads_dir,
            buildings_dir=buildings_dir,
            aoi_config_path=aoi_config_path,
            aoi_geojson_path=aoi_geojson_path,
            source_manifest_path=source_manifest_path,
        )
        if output_dir.exists():
            if not output_dir.is_dir():
                raise OverviewPublishError(f"overview output is not a directory: {output_dir}")
            os.replace(output_dir, backup)
            moved_old = True
        os.replace(stage, output_dir)
    except (OverviewExportError, OverviewPublishError, OSError) as exc:
        rollback_detail = ""
        if moved_old and backup.exists() and not output_dir.exists():
            try:
                os.replace(backup, output_dir)
            except OSError as rollback_error:
                rollback_detail = f"; restoring the previous overview failed: {rollback_error}"
        if isinstance(exc, OverviewPublishError):
            raise OverviewPublishError(f"{exc}{rollback_detail}") from exc
        raise OverviewPublishError(
            f"could not publish validated overview: {exc}{rollback_detail}"
        ) from exc
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
    if moved_old and backup.exists():
        shutil.rmtree(backup)
    return {
        "sourceValidation": validation,
        "outputDirectory": str(output_dir),
        "files": {name: {"byteLength": len(value)} for name, value in contents.items()},
        "status": "byte-identical verified overview published; candidate AOI remains pending",
    }
