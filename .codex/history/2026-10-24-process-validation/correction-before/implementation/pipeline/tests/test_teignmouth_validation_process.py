"""Synthetic protocol/supervision tests; real containment runs only in one probe."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from shapely.geometry import Polygon
from test_road_surface_validation_v1 import _small_patch_surface

from torquay_pipeline import road_surface_patch as patch
from torquay_pipeline import road_surface_validation_process_v1 as process


def request():
    return {"bindings": {"test": "synthetic-only"}, "candidateSha256": "a" * 64}


def response(*, success=False, complete=True):
    report = {name: {"passes": success} for name in patch.PATCH_OFFLINE_GATE_NAMES}
    report.update(
        gateNames=list(patch.PATCH_OFFLINE_GATE_NAMES),
        candidateFloat32Sha256="a" * 64,
        passes=success,
        validationComplete=complete,
    )
    result = {
        "bindings": request()["bindings"],
        "report": report,
        "gateSeconds": {},
        "operations": list(process.OPERATIONS) if success else [process.OPERATIONS[0]],
    }
    if success:
        first = {name: name.encode() for name in patch.PATCH_OUTPUT_FILES}
        second = dict(first)
        result.update(
            firstAssets=first,
            secondAssets=second,
            resources={"peakConstructionBufferBytes": 100},
            hashes={
                "first": {k: process.digest(v) for k, v in sorted(first.items())},
                "second": {k: process.digest(v) for k, v in sorted(second.items())},
            },
        )
    return result


def test_codec_roundtrip_preserves_mesh_and_canonical_arrays(tmp_path):
    surface = _small_patch_surface()
    original = {
        ("tuple", 1): (
            surface.mesh,
            np.asarray([1, 2], dtype=">i4"),
            Polygon([(0, 0), (1, 0), (0, 1)]),
            b"bytes",
            Path("synthetic"),
        )
    }
    encoded = process.Codec(tmp_path, "request").encode(original)
    decoded = process.Codec(tmp_path, "request").decode(json.loads(process.canonical(encoded)))
    mesh, array, polygon, payload, path = decoded[("tuple", 1)]
    assert np.array_equal(mesh.triangles, surface.mesh.triangles)
    assert mesh.edge_counts == surface.mesh.edge_counts
    assert array.dtype.str == "<i4"
    assert array.tolist() == [1, 2]
    assert polygon.equals(original[("tuple", 1)][2])
    assert payload == b"bytes" and path == Path("synthetic")


def test_codec_reconstructs_ordered_geometry_index(tmp_path):
    from dataclasses import replace

    from shapely.strtree import STRtree

    mesh = _small_patch_surface().mesh
    polygons = tuple(Polygon(mesh.vertices_xz[face]) for face in mesh.triangles)
    mesh = replace(mesh, triangle_geometries=polygons, triangle_tree=STRtree(polygons))
    result = process.Codec(tmp_path, "request").decode(
        process.Codec(tmp_path, "request").encode(mesh)
    )
    assert len(result.triangle_tree.geometries) == len(polygons)
    assert all(
        a.equals_exact(b, 0) for a, b in zip(result.triangle_geometries, polygons, strict=True)
    )


@pytest.mark.parametrize(
    "value",
    [
        object(),
        SimpleNamespace(x=1),
        np.asarray([float("nan")]),
        np.asarray([object()]),
        float("inf"),
    ],
)
def test_codec_rejects_unsupported_or_nonfinite_values(tmp_path, value):
    with pytest.raises(process.ProcessValidationError):
        process.Codec(tmp_path, "request").encode(value)


def test_blob_mutation_shape_traversal_and_oversize_fail(tmp_path, monkeypatch):
    node = process.Codec(tmp_path, "request").encode(np.asarray([1, 2], dtype="<f4"))
    broken = deepcopy(node)
    broken["shape"] = [100]
    with pytest.raises(process.ProcessValidationError, match="shape"):
        process.Codec(tmp_path, "request").decode(broken)
    (tmp_path / node["blob"]["file"]).write_bytes(b"mutation")
    with pytest.raises(process.ProcessValidationError, match="identity"):
        process.Codec(tmp_path, "request").decode(node)
    with pytest.raises(process.ProcessValidationError, match="basename"):
        process.safe_file(tmp_path, "../other")
    monkeypatch.setattr(process, "MAX_BYTES", 1)
    with pytest.raises(process.ProcessValidationError, match="ceiling"):
        process.Codec(tmp_path, "request").encode(b"xx")


def test_gate_failure_and_cooperative_partial_are_diagnostics_only():
    for result in (response(), response(complete=False)):
        process.verify_response(request(), result)
        assert not result["report"]["passes"]


@pytest.mark.parametrize(
    "change",
    [
        "operations",
        "candidate",
        "bindings",
        "missing-gate",
        "partial-success",
        "shared-assets",
        "hashes",
    ],
)
def test_incomplete_replayed_or_reordered_results_rejected(change):
    result = response(success=True)
    if change == "operations":
        result["operations"].append("resources")
    elif change == "candidate":
        result["report"]["candidateFloat32Sha256"] = "b" * 64
    elif change == "bindings":
        result["bindings"] = {}
    elif change == "missing-gate":
        del result["report"][patch.PATCH_OFFLINE_GATE_NAMES[-1]]
    elif change == "partial-success":
        result["report"]["validationComplete"] = False
    elif change == "shared-assets":
        result["secondAssets"] = result["firstAssets"]
    else:
        result["hashes"] = {}
    with pytest.raises(process.ProcessValidationError):
        process.verify_response(request(), result)


def test_late_wait_and_exact_cutoff_are_rejected():
    job = SimpleNamespace(exited=lambda: True, exit_code=lambda: 0)
    with pytest.raises(process.ProcessValidationError, match="after"):
        process.wait_worker(job, 125, clock=lambda: 125)
    assert process.wait_worker(job, 125, clock=lambda: 124) == 0


class FakeJob:
    result = None
    behavior = "normal"
    last = None

    def __init__(self, argv, root):
        type(self).last = self
        self.terminated = self.closed = False
        self.scratch = Path(argv[-1])
        if self.behavior == "assignment-failure":
            raise process.ProcessValidationError("synthetic assignment failure")
        envelope = json.loads((self.scratch / "request.json").read_bytes())
        result = {
            "protocol": process.PROTOCOL,
            "invocation": envelope["invocation"],
            "requestSha256": process.digest((self.scratch / "request.json").read_bytes()),
            "response": process.Codec(self.scratch, "result").encode(self.result),
        }
        if self.behavior == "replay":
            result["invocation"] = "another-invocation"
        (self.scratch / "result.json").write_bytes(
            b"{" if self.behavior == "truncated" else process.canonical(result)
        )

    def exited(self):
        return self.behavior != "blocked" or self.terminated

    def empty(self):
        return self.terminated

    def exit_code(self):
        return 2 if self.behavior == "crash" else 0

    def terminate(self):
        self.terminated = True

    def close(self):
        self.closed = True


@pytest.mark.parametrize(
    "behavior", ["normal", "crash", "replay", "truncated", "blocked", "assignment-failure"]
)
def test_supervisor_lifecycle_and_cleanup(tmp_path, monkeypatch, behavior):
    monkeypatch.setattr(FakeJob, "behavior", behavior)
    monkeypatch.setattr(FakeJob, "result", response())
    ticks = iter([100, 100, 100, 126, 126, 126, 126, 126]) if behavior == "blocked" else None
    clock = (lambda: next(ticks, 126)) if ticks else lambda: 100
    if behavior == "normal":
        result = process.supervise(
            tmp_path,
            request(),
            deadline=125,
            finalization_deadline=135,
            clock=clock,
            backend=FakeJob,
        )
        assert result["report"]["validationComplete"] is True
    else:
        with pytest.raises((process.ProcessValidationError, json.JSONDecodeError)):
            process.supervise(
                tmp_path,
                request(),
                deadline=125,
                finalization_deadline=135,
                clock=clock,
                backend=FakeJob,
            )
    assert not FakeJob.last.scratch.exists()
    if behavior != "assignment-failure":
        assert FakeJob.last.terminated and FakeJob.last.closed


def test_combined_transfer_resource_peak_is_not_hidden(tmp_path, monkeypatch):
    result = response(success=True)
    result["resources"]["peakConstructionBufferBytes"] = process.MAX_BYTES
    monkeypatch.setattr(FakeJob, "behavior", "normal")
    monkeypatch.setattr(FakeJob, "result", result)
    with pytest.raises(process.ProcessValidationError, match="combined"):
        process.supervise(
            tmp_path,
            request(),
            deadline=125,
            finalization_deadline=135,
            clock=lambda: 100,
            backend=FakeJob,
        )


def test_containment_failure_has_no_uncontained_fallback(tmp_path):
    calls = []

    def reject(*args):
        calls.append(args)
        raise process.ProcessValidationError("containment unavailable")

    with pytest.raises(process.ProcessValidationError, match="containment unavailable"):
        process.supervise(
            tmp_path,
            request(),
            deadline=125,
            finalization_deadline=135,
            clock=lambda: 100,
            backend=reject,
        )
    assert len(calls) == 1
