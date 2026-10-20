"""Build two isolated current_2km packages and record a file-level comparison.

The script never publishes to the repository's active package. Each build root
must be a new, explicit directory outside the repository and is retained for
inspection. The report is written only after both builds and all hash checks
complete successfully.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "pipeline"))

from torquay_pipeline.scene_build import build_scene_package  # noqa: E402
from torquay_pipeline.scene_release import (  # noqa: E402
    INVENTORY_FILENAME,
    READY_FILENAME,
    RUNTIME_FILES,
    assert_no_reparse_components,
)

PROFILE = "current_2km"
WORLD_ID = "torquay-poc-001"
PACKAGE_RELATIVE = Path("public/worlds/torquay-poc-001-2km")


class ComparisonError(RuntimeError):
    """Raised when a deterministic comparison cannot be safely completed."""


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def file_identity(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    byte_length = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            byte_length += len(chunk)
            digest.update(chunk)
    return {"byteLength": byte_length, "sha256": digest.hexdigest()}


def _same_file_bytes(first: dict[str, Any], second: dict[str, Any]) -> bool:
    return all(first.get(key) == second.get(key) for key in ("byteLength", "sha256"))


def _json_file(path: Path, label: str) -> tuple[bytes, dict[str, Any]]:
    try:
        raw_bytes = path.read_bytes()
        value = json.loads(raw_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ComparisonError(f"cannot read {label} at '{path}': {exc}") from exc
    if not isinstance(value, dict):
        raise ComparisonError(f"{label} at '{path}' must be a JSON object")
    return raw_bytes, value


def _inspect_package(package_root: Path, label: str) -> dict[str, Any]:
    ready_path = package_root / READY_FILENAME
    ready_bytes, ready = _json_file(ready_path, f"{label} readiness pointer")
    expected_ready_fields = {
        "formatVersion",
        "worldId",
        "sceneProfile",
        "releaseId",
        "inventoryPath",
        "inventoryByteLength",
        "inventorySha256",
    }
    if set(ready) != expected_ready_fields:
        raise ComparisonError(f"{label} readiness pointer has unexpected fields")
    release_id = ready.get("releaseId")
    if (
        ready.get("formatVersion") != 1
        or ready.get("worldId") != WORLD_ID
        or ready.get("sceneProfile") != PROFILE
        or not isinstance(release_id, str)
        or len(release_id) != 64
    ):
        raise ComparisonError(f"{label} readiness identity is invalid")

    release_root = package_root / "releases" / release_id
    inventory_path = release_root / INVENTORY_FILENAME
    expected_inventory_path = f"releases/{release_id}/{INVENTORY_FILENAME}"
    inventory_bytes, inventory = _json_file(inventory_path, f"{label} inventory")
    if ready.get("inventoryPath") != expected_inventory_path:
        raise ComparisonError(f"{label} readiness pointer names an unexpected inventory path")
    if ready.get("inventoryByteLength") != len(inventory_bytes) or ready.get(
        "inventorySha256"
    ) != sha256_bytes(inventory_bytes):
        raise ComparisonError(f"{label} readiness pointer does not bind its inventory bytes")
    if (
        inventory.get("worldId") != WORLD_ID
        or inventory.get("sceneProfile") != PROFILE
        or inventory.get("releaseId") != release_id
        or set(inventory) != {"formatVersion", "worldId", "sceneProfile", "files", "releaseId"}
    ):
        raise ComparisonError(f"{label} inventory identity does not match readiness")

    entries = inventory.get("files")
    if not isinstance(entries, list):
        raise ComparisonError(f"{label} inventory files must be an array")
    by_path: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "byteLength", "sha256"}:
            raise ComparisonError(f"{label} inventory contains an invalid file descriptor")
        relative = entry.get("path")
        if not isinstance(relative, str) or relative in by_path:
            raise ComparisonError(f"{label} inventory contains a duplicate or invalid path")
        posix = PurePosixPath(relative)
        if posix.is_absolute() or ".." in posix.parts or "\\" in relative:
            raise ComparisonError(f"{label} inventory path is unsafe: '{relative}'")
        if relative not in RUNTIME_FILES:
            raise ComparisonError(
                f"{label} inventory contains unexpected runtime path '{relative}'"
            )
        path = release_root.joinpath(*posix.parts)
        assert_no_reparse_components(path)
        actual = file_identity(path)
        if actual != {"byteLength": entry.get("byteLength"), "sha256": entry.get("sha256")}:
            raise ComparisonError(f"{label} runtime file differs from inventory: '{relative}'")
        by_path[relative] = actual
    if set(by_path) != set(RUNTIME_FILES):
        missing = sorted(set(RUNTIME_FILES) - set(by_path))
        raise ComparisonError(f"{label} inventory is missing runtime files: {missing}")

    expected_release_id = sha256_bytes(
        json.dumps(
            {
                "formatVersion": inventory.get("formatVersion"),
                "worldId": inventory.get("worldId"),
                "sceneProfile": inventory.get("sceneProfile"),
                "files": entries,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    if expected_release_id != release_id:
        raise ComparisonError(f"{label} content-addressed release id is invalid")

    return {
        "packageRoot": str(package_root),
        "releaseId": release_id,
        "ready": {
            **file_identity(ready_path),
            "path": str(ready_path),
        },
        "inventory": {
            **file_identity(inventory_path),
            "path": str(inventory_path),
        },
        "runtimeFiles": by_path,
    }


def _prepare_build_root(root: Path, source_geojson: Path) -> Path:
    try:
        lexical = assert_no_reparse_components(root)
    except Exception as exc:
        raise ComparisonError(f"unsafe build root '{root}': {exc}") from exc
    resolved = lexical.resolve(strict=False)
    if resolved.exists():
        raise ComparisonError(
            f"refusing to reuse existing build root '{resolved}'; choose a new explicit path"
        )
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents or resolved in REPO_ROOT.parents:
        raise ComparisonError("isolated build roots must be outside the repository")
    root.mkdir(parents=True, exist_ok=False)
    docs_dir = root / "docs"
    docs_dir.mkdir()
    shutil.copyfile(source_geojson, docs_dir / "aoi-selection.geojson")
    (root / "public/worlds").mkdir(parents=True)
    if file_identity(source_geojson) != file_identity(docs_dir / "aoi-selection.geojson"):
        raise ComparisonError(f"AOI GeoJSON copy verification failed for '{root}'")
    return root


def _build_one(root: Path, *, source_geojson: Path) -> dict[str, Any]:
    root = _prepare_build_root(root, source_geojson)
    package_root = root / PACKAGE_RELATIVE
    started_at = datetime.now(UTC)
    timer = time.perf_counter()
    result = build_scene_package(
        aoi_config_path=REPO_ROOT / "config/aoi.torquay.json",
        source_manifest_path=REPO_ROOT / "data/source-manifest.json",
        source_dir=REPO_ROOT / "data/raw/ea_dtm",
        source_path=REPO_ROOT / "data/raw/osm/devon-261016.osm.pbf",
        buildings_config_path=REPO_ROOT / "config/buildings.torquay-2km.json",
        roads_config_path=REPO_ROOT / "config/roads.torquay-2km.json",
        output_dir=package_root,
        project_root=root,
        missing_threshold=0.01,
    )
    elapsed = time.perf_counter() - timer
    inspected = _inspect_package(package_root, root.name)
    if result.get("releaseId") != inspected["releaseId"]:
        raise ComparisonError(f"{root.name} build result and ready pointer release IDs differ")
    return {
        **inspected,
        "startedAtUtc": started_at.isoformat().replace("+00:00", "Z"),
        "durationSeconds": round(elapsed, 3),
        "buildResult": {
            "status": "pass",
            "sceneProfile": result.get("sceneProfile"),
            "worldId": result.get("worldId"),
            "terrainBuild": result.get("terrainBuild"),
            "validation": (
                "source stage and published release both validated by build_scene_package"
            ),
        },
    }


def _input_identities() -> dict[str, Any]:
    manifest_path = REPO_ROOT / "data/source-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    aoi_config_path = REPO_ROOT / "config/aoi.torquay.json"
    aoi_config = json.loads(aoi_config_path.read_text(encoding="utf-8"))
    ea_inputs = []
    for source in manifest["sources"]:
        paths = {
            "archive": REPO_ROOT / "data/raw/ea_dtm" / source["archive_filename"],
            "raster": REPO_ROOT / "data/raw/ea_dtm" / source["raster_relative_path"],
            "xml": REPO_ROOT / "data/raw/ea_dtm" / source["metadata_sidecar_relative_path"],
        }
        ea_inputs.append(
            {
                "tileName": source["tile_name"],
                "files": {
                    role: {"path": str(path), **file_identity(path)} for role, path in paths.items()
                },
            }
        )
    osm = manifest["osm"]["sources"][0]
    osm_path = REPO_ROOT / osm["relative_path"]
    input_files = [
        REPO_ROOT / "data/source-manifest.json",
        aoi_config_path,
        REPO_ROOT / "config/buildings.torquay-2km.json",
        REPO_ROOT / "config/roads.torquay-2km.json",
        REPO_ROOT / "docs/aoi-selection.geojson",
        osm_path,
    ]
    return {
        "sourceManifest": {
            "path": str(manifest_path),
            **file_identity(manifest_path),
        },
        "aoiConfig": {"path": str(input_files[1]), **file_identity(input_files[1])},
        "buildingConfig": {"path": str(input_files[2]), **file_identity(input_files[2])},
        "roadConfig": {"path": str(input_files[3]), **file_identity(input_files[3])},
        "aoiGeoJson": {"path": str(input_files[4]), **file_identity(input_files[4])},
        "osmPbf": {
            "path": str(osm_path),
            "expectedSha256": osm.get("sha256"),
            "expectedByteLength": osm.get("size_bytes"),
            **file_identity(osm_path),
        },
        "eaTiles": ea_inputs,
        "aoiStatus": {
            "selectionStatus": aoi_config.get("selection_status"),
            "coverageStatus": aoi_config.get("coverage_status"),
            "boundsM": aoi_config.get("aoi", {}).get("bbox_m"),
            "note": "AOI approval/completeness is not asserted by a build hash comparison.",
        },
    }


def _atomic_write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    content = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    try:
        with temp.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-a-root", type=Path, required=True)
    parser.add_argument("--run-b-root", type=Path, required=True)
    parser.add_argument(
        "--report",
        type=Path,
        default=REPO_ROOT / "docs/milestones/artifacts/Torquay-2km-determinism.json",
    )
    args = parser.parse_args()
    try:
        run_a = assert_no_reparse_components(args.run_a_root).resolve(strict=False)
        run_b = assert_no_reparse_components(args.run_b_root).resolve(strict=False)
        if run_a == run_b or run_a in run_b.parents or run_b in run_a.parents:
            raise ComparisonError("run A and run B must use distinct, non-overlapping roots")
        source_geojson = REPO_ROOT / "docs/aoi-selection.geojson"
        started = datetime.now(UTC)
        command = subprocess.list2cmdline(
            [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]
        )
        active_root = REPO_ROOT / PACKAGE_RELATIVE
        active_before = _inspect_package(active_root, "active package before builds")
        pipeline_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--short"], cwd=REPO_ROOT, text=True
        ).splitlines()
        pipeline_status = subprocess.check_output(
            [
                "git",
                "status",
                "--short",
                "--",
                "pipeline/torquay_pipeline",
                "pipeline/scripts",
            ],
            cwd=REPO_ROOT,
            text=True,
        ).splitlines()
        print(f"pipeline commit: {pipeline_commit}", flush=True)
        print(f"run A root: {run_a}", flush=True)
        print("building run A (full current_2km source generation)...", flush=True)
        run_a_result = _build_one(run_a, source_geojson=source_geojson)
        print(
            f"run A validated: {run_a_result['releaseId']} "
            f"({run_a_result['durationSeconds']} seconds)",
            flush=True,
        )
        print(f"run B root: {run_b}", flush=True)
        print("building run B (full current_2km source generation)...", flush=True)
        run_b_result = _build_one(run_b, source_geojson=source_geojson)
        print(
            f"run B validated: {run_b_result['releaseId']} "
            f"({run_b_result['durationSeconds']} seconds)",
            flush=True,
        )
        active = _inspect_package(active_root, "active package")
        per_file = []
        for relative in sorted(RUNTIME_FILES):
            a = run_a_result["runtimeFiles"][relative]
            b = run_b_result["runtimeFiles"][relative]
            c = active["runtimeFiles"][relative]
            per_file.append(
                {
                    "path": relative,
                    "runA": a,
                    "runB": b,
                    "active": c,
                    "runAEqualsRunB": a == b,
                    "runAEqualsActive": a == c,
                    "runBEqualsActive": b == c,
                }
            )
        same_runtime = all(
            item["runAEqualsRunB"] and item["runAEqualsActive"] and item["runBEqualsActive"]
            for item in per_file
        )
        same_release = run_a_result["releaseId"] == run_b_result["releaseId"] == active["releaseId"]
        same_ready = all(
            _same_file_bytes(first, second)
            for first, second in (
                (run_a_result["ready"], run_b_result["ready"]),
                (run_a_result["ready"], active["ready"]),
            )
        )
        same_inventory = all(
            _same_file_bytes(first, second)
            for first, second in (
                (run_a_result["inventory"], run_b_result["inventory"]),
                (run_a_result["inventory"], active["inventory"]),
            )
        )
        active_unchanged = (
            active_before["releaseId"] == active["releaseId"]
            and _same_file_bytes(active_before["ready"], active["ready"])
            and _same_file_bytes(active_before["inventory"], active["inventory"])
            and active_before["runtimeFiles"] == active["runtimeFiles"]
        )
        same_ready = same_ready and active_unchanged
        same_inventory = same_inventory and active_unchanged
        same_runtime = same_runtime and active_unchanged
        report = {
            "formatVersion": 1,
            "purpose": (
                "Auditable byte-for-byte repeatability comparison for the isolated "
                "current_2km scene build."
            ),
            "comparisonStatus": "pass"
            if same_runtime and same_release and same_ready and same_inventory
            else "fail",
            "generatedAtUtc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "execution": {
                "startedAtUtc": started.isoformat().replace("+00:00", "Z"),
                "completedAtUtc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "workingDirectory": str(REPO_ROOT),
                "shell": "PowerShell",
                "command": command,
                "reportOutputPath": str(args.report.resolve(strict=False)),
                "implementation": (
                    "pipeline.scripts.compare_current_2km_builds.main -> "
                    "torquay_pipeline.scene_build.build_scene_package"
                ),
                "parameters": {
                    "profile": PROFILE,
                    "missingThreshold": 0.01,
                    "builds": 2,
                    "outputsRetained": True,
                },
            },
            "pipeline": {
                "gitCommit": pipeline_commit,
                "workingTreeShortStatus": status,
                "pipelineSourceFilesClean": not pipeline_status,
                "pipelineSourceShortStatus": pipeline_status,
                "scriptPath": str(Path(__file__).resolve()),
                "scriptSha256": file_identity(Path(__file__).resolve())["sha256"],
                "pythonVersion": sys.version,
                "versions": {
                    name: _version(name)
                    for name in ("rasterio", "numpy", "pyproj", "osmium", "shapely")
                },
            },
            "inputIdentities": _input_identities(),
            "runs": {
                "runA": run_a_result,
                "runB": run_b_result,
                "activeBefore": active_before,
                "active": active,
            },
            "comparison": {
                "releaseIdSameAcrossAll": same_release,
                "readyBytesSameAcrossAll": same_ready,
                "inventoryBytesSameAcrossAll": same_inventory,
                "runtimeFilesSameAcrossAll": same_runtime,
                "activePackageUnchangedDuringBuilds": active_unchanged,
                "runtimeFileCount": len(per_file),
                "runtimeByteLengthTotal": sum(item["runA"]["byteLength"] for item in per_file),
                "files": per_file,
            },
            "scopeNote": (
                "A deterministic package comparison does not approve the AOI, establish "
                "source completeness, or change selected_pending_coverage / not_checked."
            ),
        }
        _atomic_write_json(args.report.resolve(strict=False), report)
        print(f"comparison status: {report['comparisonStatus']}", flush=True)
        print(f"report: {args.report.resolve(strict=False)}", flush=True)
        print(f"retained run A: {run_a_result['packageRoot']}", flush=True)
        print(f"retained run B: {run_b_result['packageRoot']}", flush=True)
        return 0 if report["comparisonStatus"] == "pass" else 1
    except (ComparisonError, OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"determinism comparison failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
