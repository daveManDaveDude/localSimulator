"""One reserved, externally bounded Float32 arrangement diagnostic; never a build.

Preparation only until the coordinator freezes this script and authorizes invocation.
Required --input-manifest JSON schema:
  {"schema": "teignmouth-float32-diagnostic-input-v1",
   "issueId": "Teignmouth-float32-topology-representation-1",
   "diagnosticOrdinal": 1, "originXYZM": [-140, 0, -95],
   "files": [{"path": "repository/relative/path", "byteLength": 123,
              "sha256": "64 lowercase hexadecimal characters"}, ...]}

All required files, the exact interpreter/venv metadata, source descriptors
referenced by build 5, and every imported torquay_pipeline .py helper must be
bound. Freezing all pipeline/torquay_pipeline/*.py files is a conservative option.
The manifest must bind this script itself.
The parent creates only the fresh new diagnostic leaf, then supervises one worker.
The worker uses the unmodified predecessor mesher as an oracle, never patches it,
and separately enumerates its exact noded-face triangulation for a complete census.
Any successful oracle result is X/Z topology only: no candidate Y, roads or terrain
asset is constructed, serialized, published or served. The coordinator owns ledger
consumption, including failed/timeout invocations; this script never edits ledgers.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import json
import math
import os
import subprocess
import sys
import time
import traceback
from collections import Counter
from pathlib import Path


ISSUE = "Teignmouth-float32-topology-representation-1"
NEW_ROOT = "docs/milestones/artifacts/Teignmouth-float32-topology"
OLD_ROOT = "docs/milestones/artifacts/Teignmouth-corridor-prototype/continuation-1"
BUILD6 = f"{OLD_ROOT}/sol-correction-1/build-6"
BUILD5 = f"{OLD_ROOT}/correction-4/build-5"
SCRIPT = "pipeline/scripts/diagnose_teignmouth_float32_frame.py"
ORIGIN = (-140.0, 0.0, -95.0)
COLLISION = ((-164.2316811012587, -85.5), (-164.23167542853238, -85.5))
REQUIRED = {
    SCRIPT,
    f"{NEW_ROOT}/spec.md",
    f"{NEW_ROOT}/sol-plan.md",
    f"{NEW_ROOT}/coordinator-acceptance-1.md",
    "pipeline/.venv/Scripts/python.exe",
    "pipeline/.venv/pyvenv.cfg",
    "pipeline/.venv/Lib/site-packages/numpy-2.5.4.dist-info/METADATA",
    "pipeline/.venv/Lib/site-packages/shapely-2.2.0.dist-info/METADATA",
    "pipeline/.venv/Lib/site-packages/pyproj-3.8.0.dist-info/METADATA",
    "pipeline/pyproject.toml",
    "pipeline/torquay_pipeline/teignmouth_corridor_continuation.py",
    "pipeline/torquay_pipeline/teignmouth_corridor_prototype.py",
    "pipeline/torquay_pipeline/road_surface.py",
    "pipeline/torquay_pipeline/road_surface_topology.py",
    "config/road-surface-teignmouth-corridor-continuation.json",
    f"{BUILD6}/report.json",
    f"{BUILD6}/preservation-before.json",
    f"{BUILD6}/chart-xz.f64",
    f"{BUILD6}/chart-station-lateral.f64",
    f"{BUILD6}/chart-indices.u32",
    f"{BUILD5}/report.json",
    f"{OLD_ROOT}/diagnostic-1/full-field-earthwork.json",
    "node_modules/three/package.json",
    "node_modules/three/src/renderers/WebGLRenderer.js",
    "node_modules/three/src/renderers/shaders/ShaderChunk/project_vertex.glsl.js",
    "node_modules/three/src/renderers/shaders/ShaderChunk/worldpos_vertex.glsl.js",
    "node_modules/three/src/math/Matrix4.js",
    "src/app/alignmentQaCamera.ts",
    "src/app/createApp.ts",
    "src/scene/createHeightfieldWorld.ts",
}


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value: object) -> None:
    temporary = path.with_name(path.name + ".pending")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    temporary.replace(path)


def freeze_inputs(root: Path, manifest_path: Path) -> tuple[dict, dict]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema") != "teignmouth-float32-diagnostic-input-v1"
        or manifest.get("issueId") != ISSUE
        or manifest.get("diagnosticOrdinal") != 1
        or manifest.get("originXYZM") != list(ORIGIN)
    ):
        raise ValueError("wrong frozen diagnostic manifest identity/frame")
    bindings = {}
    for item in manifest["files"]:
        relative = item["path"]
        path = (root / relative).resolve(strict=True)
        if path.relative_to(root).as_posix() != relative or relative in bindings:
            raise ValueError(f"noncanonical, duplicate or external bound path: {relative}")
        if path.stat().st_size != item["byteLength"] or sha(path) != item["sha256"]:
            raise ValueError(f"frozen input mismatch: {relative}")
        bindings[relative] = item
    if missing := REQUIRED - bindings.keys():
        raise ValueError(f"missing mandatory input bindings: {sorted(missing)}")
    return manifest, bindings


def exact_linework(module, corridor, chart):
    """Reuse only the unmodified function prefix, stopping before mesher invocation."""
    source = inspect.getsource(module.assemble_corrected)
    tree = ast.parse(source)
    function = tree.body[0]
    prefix = []
    cutoff_count = 0
    for statement in function.body:
        if (
            isinstance(statement, ast.Assign)
            and isinstance(statement.value, ast.Call)
            and isinstance(statement.value.func, ast.Name)
            and statement.value.func.id == "build_constrained_mesh"
        ):
            if ast.unparse(statement) != "mesh = build_constrained_mesh(domain, lines)":
                raise ValueError("unexpected predecessor arrangement-to-mesher boundary")
            cutoff_count += 1
            break
        prefix.append(statement)
    if cutoff_count != 1:
        raise ValueError("cannot reuse exact predecessor linework; stop rather than substitute")
    prefix.append(ast.Return(ast.Tuple([ast.Name("domain", ast.Load()), ast.Name("lines", ast.Load())], ast.Load())))
    function.body = prefix
    function.name = "diagnostic_exact_linework"
    ast.fix_missing_locations(tree)
    namespace = dict(vars(module))
    exec(compile(tree, "<exact frozen arrangement prefix>", "exec"), namespace)
    domain, lines = namespace[function.name](corridor, chart, None)
    return domain, lines, hashlib.sha256(source.encode()).hexdigest()


def arrangement_census(topology, domain, lines, evidence: Path, name: str, origin, np, shapely):
    """Enumerate the same raw noded faces/triangles; collisions remain failures."""
    folder = evidence / name
    folder.mkdir()
    # These are the exact first three geometric operations of the frozen mesher.
    linework = topology._line_geometries(lines)
    faces = topology._noded_faces(domain, linework)
    triangulated = shapely.constrained_delaunay_triangles(np.asarray(faces, dtype=object))
    points = set()
    occurrences = []
    missing_edges = []
    expected_constraint_edges = set()
    raw_invalid = 0
    rounded_invalid = 0
    for face_id, (face, collection) in enumerate(zip(faces, triangulated, strict=True)):
        face_edges = topology._face_edges(face)
        expected_constraint_edges.update(face_edges)
        triangle_edges = set()
        for triangle in collection.geoms:
            corners = [(float(x), float(z)) for x, z in list(triangle.exterior.coords)[:-1]]
            if len(corners) != 3:
                raise ValueError("nontriangle construction face; no substitute triangulator")
            points.update(corners)
            occurrences.append(corners)
            actual = np.asarray(corners, dtype=np.float64)
            rounded = actual.astype(np.float32).astype(np.float64)
            raw = np.linalg.det(np.stack((actual[1] - actual[0], actual[2] - actual[0])))
            quantized = np.linalg.det(np.stack((rounded[1] - rounded[0], rounded[2] - rounded[0])))
            raw_invalid += int(not math.isfinite(raw) or raw == 0)
            rounded_invalid += int(not math.isfinite(quantized) or raw * quantized <= 0)
            triangle_edges.update(tuple(sorted((corners[i], corners[(i + 1) % 3]))) for i in range(3))
        missing_edges.extend({"faceId": face_id, "edge": edge} for edge in sorted(face_edges - triangle_edges))
    exact = np.asarray(sorted(points), dtype="<f8")
    exact.tofile(folder / "construction-unique-xz.f64")
    np.asarray(occurrences, dtype="<f8").tofile(folder / "triangle-corner-occurrences-xz.f64")
    buckets = {}
    for point in sorted(points):
        # Unchanged predecessor encoding, not a diagnostic replacement/tolerance.
        buckets.setdefault(topology._float32_bytes(*point), []).append(point)
    collisions = [values for _, values in sorted(buckets.items()) if len(values) > 1]
    decoded = exact.astype(np.float32).astype(np.float64)
    displacement = np.abs(decoded - exact)
    all_boundary = set()
    for face in faces:
        for first, second in topology._face_edges(face):
            if domain.boundary.covers(topology.LineString((first, second))):
                all_boundary.update((first, second))
    offset = np.asarray((origin[0], origin[2]), dtype=np.float64)
    global_boundary = sorted(tuple(np.asarray(point) + offset) for point in all_boundary)
    decoded_global_boundary = sorted({
        tuple(np.asarray(point, dtype=np.float32).astype(np.float64) + offset)
        for point in all_boundary
    })
    expected_boundary = {
        *((float(x), z) for x in range(-182, -97, 2) for z in (-136.0, -54.0)),
        *((x, float(z)) for z in range(-136, -53, 2) for x in (-182.0, -98.0)),
    }
    result = {
        "frame": name,
        "originXYZM": list(origin),
        "boundsStoredXZ": list(domain.bounds),
        "inputConstraintCount": len(linework),
        "polygonFaces": len(faces),
        "constructionTriangles": len(occurrences),
        "constructionUniqueVertices": len(points),
        "constructionCornerOccurrences": len(occurrences) * 3,
        "collisionGroups": collisions,
        "collisionGroupCount": len(collisions),
        "invalidRawTriangles": raw_invalid,
        "invalidOrWindingChangedAfterFloat32": rounded_invalid,
        "missingConstraintEdges": missing_edges,
        "maximumStoredAxisRoundTripErrorM": displacement.max(axis=0).tolist(),
        "boundaryGlobalXZ": global_boundary,
        "boundaryDecodedFloat32ReconstructedGlobalXZ": decoded_global_boundary,
        "exactOriginalBoundaryVerticesRawArrangement": set(global_boundary) == expected_boundary,
        "exactOriginalBoundaryVerticesDecodedFloat32": set(decoded_global_boundary) == expected_boundary,
        "decodedBoundaryMissingOriginalVertices": sorted(expected_boundary - set(decoded_global_boundary)),
        "decodedBoundaryUnexpectedVertices": sorted(set(decoded_global_boundary) - expected_boundary),
        "oracleCensusEquivalent": False,
        "notes": "Raw topology observations only; no candidate heights, road mesh or source overlay.",
    }
    # Invoke the actual unmodified guard/mesher as the oracle, not a monkeypatch.
    # Its returned PlanarMesh contains X/Z topology only and is not a terrain asset.
    try:
        oracle = topology.build_constrained_mesh(domain, lines)
        oracle_points = {tuple(float(value) for value in point) for point in oracle.vertices_xz}
        census_triangle_counts = Counter(tuple(sorted(corners)) for corners in occurrences)
        oracle_triangle_counts = Counter(
            tuple(sorted(tuple(float(value) for value in oracle.vertices_xz[index]) for index in triangle))
            for triangle in oracle.triangles
        )
        oracle_constraint_edges = {
            tuple(sorted(tuple(float(value) for value in oracle.vertices_xz[index]) for index in edge))
            for edge in oracle.constraint_edges
        }
        missing_triangles = census_triangle_counts - oracle_triangle_counts
        unexpected_triangles = oracle_triangle_counts - census_triangle_counts
        comparison = {
            "exactReturnedVertexSetMatchesCensus": oracle_points == points,
            "missingCensusVertices": sorted(points - oracle_points),
            "unexpectedOracleVertices": sorted(oracle_points - points),
            "triangleCountMatchesCensus": len(oracle.triangles) == len(occurrences),
            "exactTriangleMultisetMatchesCensus": census_triangle_counts == oracle_triangle_counts,
            "missingCensusTriangles": [
                {"corners": triangle, "multiplicity": count}
                for triangle, count in sorted(missing_triangles.items())
            ],
            "unexpectedOracleTriangles": [
                {"corners": triangle, "multiplicity": count}
                for triangle, count in sorted(unexpected_triangles.items())
            ],
            "exactConstraintEdgeSetMatchesCensus": oracle_constraint_edges == expected_constraint_edges,
            "missingCensusConstraintEdges": sorted(expected_constraint_edges - oracle_constraint_edges),
            "unexpectedOracleConstraintEdges": sorted(oracle_constraint_edges - expected_constraint_edges),
        }
        result["oracleCensusComparison"] = comparison
        result["oracleCensusEquivalent"] = bool(
            comparison["exactReturnedVertexSetMatchesCensus"]
            and comparison["triangleCountMatchesCensus"]
            and comparison["exactTriangleMultisetMatchesCensus"]
            and comparison["exactConstraintEdgeSetMatchesCensus"]
        )
        result["unchangedMesherOracle"] = {
            "passes": True,
            "vertices": len(oracle.vertices_xz),
            "triangles": len(oracle.triangles),
            "boundaryEdges": len(oracle.boundary_edges),
            "constraintEdges": len(oracle.constraint_edges),
        }
    except topology.TopologyError as exc:
        result["unchangedMesherOracle"] = {"passes": False, "type": type(exc).__name__, "message": str(exc)}
    result["passesStoredTopologyDiagnostic"] = bool(
        not collisions and not raw_invalid and not rounded_invalid and not missing_edges
        and result["exactOriginalBoundaryVerticesRawArrangement"]
        and result["exactOriginalBoundaryVerticesDecodedFloat32"]
        and result["unchangedMesherOracle"]["passes"]
        and result["oracleCensusEquivalent"]
    )
    write_json(folder / "observations.json", result)
    return result, exact


def runtime_probes(root: Path, exact_local, np):
    """CPU/Float32-equivalent numeric observations, not GPU or browser proof."""
    project = (root / "node_modules/three/src/renderers/shaders/ShaderChunk/project_vertex.glsl.js").read_text()
    world = (root / "node_modules/three/src/renderers/shaders/ShaderChunk/worldpos_vertex.glsl.js").read_text()
    renderer = (root / "node_modules/three/src/renderers/WebGLRenderer.js").read_text()
    camera_hook = (root / "src/app/alignmentQaCamera.ts").read_text()
    if (
        "modelViewMatrix * mvPosition" not in project
        or "modelMatrix * worldPosition" not in world
        or "object.modelViewMatrix.multiplyMatrices( camera.matrixWorldInverse, object.matrixWorld )" not in renderer
        or "YXZ" not in camera_hook
        or "-pose.bearingDegrees" not in camera_hook
    ):
        raise ValueError("bound runtime transform path differs; do not invent an equivalent")
    def multiply(matrix, points):
        matrix = matrix.astype(np.float32)
        points = points.astype(np.float32)
        output = np.zeros((len(points), 4), dtype=np.float32)
        for row in range(4):
            for column in range(4):
                output[:, row] = np.float32(output[:, row] + np.float32(points[:, column] * matrix[row, column]))
        return output
    local_points = np.column_stack((exact_local[:, 0], np.zeros(len(exact_local)), exact_local[:, 1], np.ones(len(exact_local))))
    translation = np.eye(4)
    translation[:3, 3] = ORIGIN
    source_world = local_points @ translation.T
    results = []
    for name, position, bearing, pitch in (
        ("original-circled", [-136.407629, 7.750687, 99.286006], 344.6, -24.0),
        ("close-oblique", [-156.818885, 6.073672, -77.695888], 43.526184, -17.129901),
    ):
        yaw, elevation = math.radians(-bearing), math.radians(pitch)
        ry = np.asarray([[math.cos(yaw), 0, math.sin(yaw)], [0, 1, 0], [-math.sin(yaw), 0, math.cos(yaw)]])
        rx = np.asarray([[1, 0, 0], [0, math.cos(elevation), -math.sin(elevation)], [0, math.sin(elevation), math.cos(elevation)]])
        rotation = ry @ rx
        view = np.eye(4)
        view[:3, :3] = rotation.T
        view[:3, 3] = -rotation.T @ np.asarray(position)
        actual_view = multiply(view @ translation, local_points)
        expected_view = source_world @ view.T
        model_world = multiply(translation, local_points)
        projection = np.zeros((4, 4))
        focal = 1.0 / math.tan(math.radians(54) / 2)
        projection[0, 0], projection[1, 1] = focal / 1.5, focal
        near, far = 0.1, 4400.0
        projection[2, 2] = -(far + near) / (far - near)
        projection[2, 3] = -2 * far * near / (far - near)
        projection[3, 2] = -1
        pair_world = np.asarray([[x, 0.0, z, 1.0] for x, z in COLLISION])
        pair_local = pair_world.copy()
        pair_local[:, :3] -= np.asarray(ORIGIN)
        results.append({
            "pose": name, "xyz": position, "bearingDegrees": bearing, "pitchDegrees": pitch,
            "maximumViewSpaceAxisErrorM": np.max(np.abs(actual_view.astype(np.float64) - expected_view), axis=0).tolist(),
            "maximumWorldPositionAxisErrorM": np.max(np.abs(model_world.astype(np.float64) - source_world), axis=0).tolist(),
            "knownPairLocalFloat32": pair_local.astype(np.float32).tolist(),
            "knownPairViewFloat32": multiply(view @ translation, pair_local).tolist(),
            "knownPairClipFloat32": multiply(projection, multiply(view @ translation, pair_local)).tolist(),
            "knownPairWorldPositionFloat32": multiply(translation, pair_local).tolist(),
            "modelViewUniformFloat32": (view @ translation).astype(np.float32).tolist(),
        })
    return {
        "staticPaths": {"projection": "modelViewMatrix then projectionMatrix", "optionalWorldPosition": "modelMatrix; enabled paths require separate care", "cpuComposition": "JavaScript matrixWorldInverse * matrixWorld"},
        "probes": results,
        "limitations": [
            "Y=0 probe plane, not candidate terrain heights; no rendered seam/contact certification.",
            "Sequential non-fused Float32 products/sums are an explicit emulation; GPU FMA/reordering/driver behavior is not certified.",
            "Projection uses registered FOV54, 1440x960, near0.1 and current2km far4400; no rasterization or screen-space topology claim.",
            "Optional global worldPosition can round distinct points together even if local positions remain distinct; never reconstruct global Float32 vertex buffers.",
        ],
    }


def worker(root: Path, manifest_path: Path, evidence: Path) -> int:
    started = time.perf_counter()
    report = {"issueId": ISSUE, "diagnosticOrdinal": 1, "status": "STOP_ERROR", "candidateBuilt": False, "candidateEligibleForServing": False}
    try:
        manifest, bindings = freeze_inputs(root, manifest_path)
        sys.path.insert(0, str(root / "pipeline"))
        import numpy as np
        import shapely
        from shapely.affinity import translate
        from shapely.strtree import STRtree
        from torquay_pipeline import road_surface_topology as topology
        from torquay_pipeline import teignmouth_corridor_continuation as continuation

        imported_local_sources = []
        for loaded in list(sys.modules.values()):
            filename = getattr(loaded, "__file__", None)
            if filename is None:
                continue
            path = Path(filename).resolve()
            if path.is_relative_to(root / "pipeline/torquay_pipeline") and path.suffix == ".py":
                relative = path.relative_to(root).as_posix()
                if relative not in bindings:
                    raise ValueError(f"imported source helper absent from frozen manifest: {relative}")
                imported_local_sources.append(relative)
        report["importedLocalSourceBindings"] = sorted(set(imported_local_sources))
        predecessor = json.loads((root / f"{BUILD6}/report.json").read_text())
        if not all(repr(point) in predecessor["primaryError"]["message"] for point in COLLISION):
            raise ValueError("bound build6 collision witness differs")
        source_report = json.loads((root / f"{BUILD5}/report.json").read_text())
        for descriptor in source_report["sourceHashes"].values():
            source_path = Path(descriptor["path"])
            relative = (source_path if source_path.is_absolute() else root / source_path).resolve().relative_to(root).as_posix()
            if relative not in bindings or bindings[relative]["sha256"] != descriptor.get("sha256", descriptor.get("readySha256")):
                raise ValueError(f"source not bound to predecessor: {relative}")
        corridor = continuation.load_corridor_continuation(root)
        original = json.loads((root / f"{BUILD6}/preservation-before.json").read_text())
        for relative in (
            "config/road-surface-teignmouth-corridor-continuation.json",
            "pipeline/torquay_pipeline/teignmouth_corridor_continuation.py",
            "pipeline/torquay_pipeline/teignmouth_corridor_prototype.py",
            "pipeline/torquay_pipeline/road_surface.py",
            "pipeline/torquay_pipeline/road_surface_topology.py",
        ):
            if bindings[relative]["sha256"] != original[relative]:
                raise ValueError(f"frozen arrangement input differs from build6: {relative}")
        chart_points = np.fromfile(root / f"{BUILD6}/chart-xz.f64", dtype="<f8").reshape(-1, 2)
        fields = np.fromfile(root / f"{BUILD6}/chart-station-lateral.f64", dtype="<f8").reshape(-1, 2)
        indices = np.fromfile(root / f"{BUILD6}/chart-indices.u32", dtype="<u4").reshape(-1, 3)
        polygons = shapely.polygons(chart_points[indices])
        chart = continuation.Chart(np.unique(fields[:, 0]), chart_points, fields, indices, polygons, STRtree(polygons))
        domain, lines, prefix_source_hash = exact_linework(continuation, corridor, chart)
        write_json(evidence / "arrangement-inputs.json", {"domainWkt": domain.wkt, "linesWkt": [line.wkt for line in lines], "exactPredecessorFunctionSourceSha256": prefix_source_hash})
        report.update({"inputManifestSha256": sha(manifest_path), "originXYZM": list(ORIGIN), "boundInputCount": len(bindings), "interpreter": {"executable": sys.executable, "version": sys.version}, "versions": {"numpy": np.__version__, "shapely": shapely.__version__}})
        baseline, exact_global = arrangement_census(topology, domain, lines, evidence, "global", (0, 0, 0), np, shapely)
        report["globalArrangement"] = baseline
        global_points = {tuple(point) for point in exact_global}
        baseline_reproduced = (
            all(point in global_points for point in COLLISION)
            and any(all(point in group for point in COLLISION) for group in baseline["collisionGroups"])
            and not baseline["unchangedMesherOracle"]["passes"]
            and all(repr(point) in baseline["unchangedMesherOracle"].get("message", "") for point in COLLISION)
        )
        report["exactBuild6CollisionReproduced"] = baseline_reproduced
        if not baseline_reproduced:
            raise ValueError("global arrangement does not reproduce exact bound build6 collision; no substitute allowed")
        write_json(evidence / "progress.json", report)
        local_domain = translate(domain, xoff=-ORIGIN[0], yoff=-ORIGIN[2])
        local_lines = [translate(line, xoff=-ORIGIN[0], yoff=-ORIGIN[2]) for line in lines]
        local, exact_local = arrangement_census(topology, local_domain, local_lines, evidence, "local", ORIGIN, np, shapely)
        report["localArrangement"] = local
        report["runtimeTransformObservations"] = runtime_probes(root, exact_local, np)
        freeze_inputs(root, manifest_path)
        report["boundInputsUnchangedAfter"] = True
        transform_error = max(
            max(probe["maximumViewSpaceAxisErrorM"][:3])
            for probe in report["runtimeTransformObservations"]["probes"]
        )
        report["numericViewSpaceProbeWithinExisting1mmTolerance"] = transform_error <= 0.001
        report["status"] = (
            "GO_FOR_COORDINATOR_CONTRACT_REVIEW"
            if local["passesStoredTopologyDiagnostic"] and transform_error <= 0.001
            else "NO_GO_LOCAL_REPRESENTATION"
        )
        report["omissions"] = ["No graded Y field, full candidate terrain/road asset, source overlay, gradients, buildings, walking or runtime/browser acceptance.", "Global and translated GEOS arrangements are separately noded; mathematical translation does not guarantee identical floating-point intersections/connectivity. Raw witnesses permit comparison; no equivalence is presumed."]
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    finally:
        report["workerWallSeconds"] = time.perf_counter() - started
        write_json(evidence / "report.json", report)
    return 0 if report["status"] == "GO_FOR_COORDINATOR_CONTRACT_REVIEW" else 2


def main() -> int:
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-manifest", type=Path, required=True)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if Path(sys.executable).resolve() != (root / "pipeline/.venv/Scripts/python.exe").resolve():
        raise ValueError("use the exact repository pipeline virtual environment")
    manifest_path = args.input_manifest.resolve(strict=True)
    if manifest_path != (root / NEW_ROOT / "input-manifest.json").resolve():
        raise ValueError("manifest must be the new issue's fixed input-manifest.json")
    evidence = root / NEW_ROOT / "diagnostic-1"
    if args.worker:
        if not (evidence / "attempt.json").is_file():
            raise ValueError("worker requires parent-created reserved attempt")
        return worker(root, manifest_path, evidence)
    if evidence.exists():
        raise ValueError("diagnostic leaf must be absent; no retry or overwrite")
    ledger = json.loads((root / NEW_ROOT / "attempt-ledger.json").read_text())
    budget = ledger["budget"]["diagnostics"]
    if ledger["issueId"] != ISSUE or budget["used"] != 0 or budget["reserved"] != 1:
        raise ValueError("diagnostic1 must be uniquely reserved before invocation")
    evidence.mkdir()
    write_json(evidence / "attempt.json", {"issueId": ISSUE, "diagnosticOrdinal": 1, "wallLimitSeconds": 120, "command": sys.argv, "interpreter": sys.executable})
    try:
        freeze_inputs(root, manifest_path)
        timeout = min(110.0, 120.0 - (time.perf_counter() - started) - 5.0)
        if timeout <= 0:
            raise TimeoutError("input verification exhausted diagnostic wall budget")
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--input-manifest", str(manifest_path), "--worker"], cwd=root, timeout=timeout, check=False)
        if not (evidence / "report.json").is_file():
            raise RuntimeError(f"worker exited {result.returncode} without a durable report")
        report = json.loads((evidence / "report.json").read_text())
        report["diagnosticTotalWallSeconds"] = time.perf_counter() - started
        report["coordinatorMustConsumeReservation"] = True
        write_json(evidence / "report.json", report)
        print(json.dumps({"status": report["status"], "evidence": str(evidence), "wallSeconds": report["diagnosticTotalWallSeconds"]}))
        return result.returncode
    except Exception as exc:
        write_json(evidence / "report.json", {"issueId": ISSUE, "diagnosticOrdinal": 1, "status": "STOP_TIMEOUT" if isinstance(exc, (subprocess.TimeoutExpired, TimeoutError)) else "STOP_ERROR", "error": {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}, "diagnosticTotalWallSeconds": time.perf_counter() - started, "partialEvidencePreserved": True, "coordinatorMustConsumeReservation": True, "candidateBuilt": False, "candidateEligibleForServing": False})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
