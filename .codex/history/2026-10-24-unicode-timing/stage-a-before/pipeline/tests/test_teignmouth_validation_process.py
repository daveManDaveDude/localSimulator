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

    def __init__(self, argv, root, **kwargs):
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
            "memory": {
                "constructionPeakBytes": self.result.get("resources", {}).get(
                    "peakConstructionBufferBytes", 0
                )
            },
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

    def wait_exit(self, deadline, *, clock):
        return self.exited() and self.empty()

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

    def reject(*args, **kwargs):
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


def test_startup_exception_retains_child_and_scratch_until_exit_confirmed(tmp_path):
    import shutil

    observed = {}
    job = SimpleNamespace(
        pid=123456,
        terminate=lambda: observed.update(terminated=True),
        wait_exit=lambda deadline, **kwargs: False,
        close=lambda: observed.update(closed=True),
    )

    def failed_start(argv, root, **kwargs):
        observed["scratch"] = Path(argv[-1])
        observed["deadline"] = kwargs["finalization_deadline"]
        raise process.ProcessStartupError(job, ValueError("assignment failed"))

    with pytest.raises(process.ProcessValidationError, match="exit unconfirmed"):
        process.supervise(
            tmp_path,
            request(),
            deadline=125,
            finalization_deadline=135,
            clock=lambda: 100,
            backend=failed_start,
        )
    assert observed["terminated"] and observed["deadline"] == 135
    assert "closed" not in observed and observed["scratch"].is_dir()
    shutil.rmtree(observed["scratch"])  # Fake backend has no actual child.


def test_native_startup_termination_and_wait_results_are_checked():
    job = object.__new__(process.WindowsJob)
    calls = []
    job.process, job.job, job.pid, job.assigned = 1, 2, 123456, False
    job.kernel = SimpleNamespace(
        WaitForSingleObject=lambda handle, milliseconds: calls.append(milliseconds) or 258,
        TerminateProcess=lambda *args: False,
        TerminateJobObject=lambda *args: True,
    )
    with pytest.raises(process.ProcessValidationError, match="TerminateProcess failed"):
        job.terminate()
    assert job.wait_exit(100.05, clock=lambda: 100) is False
    assert 0 <= calls[-1] <= 50  # No fixed one-second wait beyond remaining budget.
    job.kernel.WaitForSingleObject = lambda *args: 0xFFFFFFFF
    with pytest.raises(process.ProcessValidationError, match="cleanup wait failed"):
        job.wait_exit(100.05, clock=lambda: 100)


def test_request_budget_rejects_before_codec_allocates(tmp_path, monkeypatch):
    monkeypatch.setattr(process, "MAX_BYTES", 128)

    def no_allocation(*args):
        pytest.fail("encode must not allocate before preflight rejection")

    monkeypatch.setattr(process.Codec, "encode", no_allocation)
    with pytest.raises(process.ProcessValidationError, match="preallocation"):
        process.supervise(
            tmp_path,
            request(),
            deadline=125,
            finalization_deadline=135,
            clock=lambda: 100,
            backend=FakeJob,
        )


def test_result_budget_rejects_before_first_decode(tmp_path, monkeypatch):
    result = response(success=True)
    result["resources"]["peakConstructionBufferBytes"] = process.MAX_BYTES
    monkeypatch.setattr(FakeJob, "behavior", "normal")
    monkeypatch.setattr(FakeJob, "result", result)

    def no_decode(*args):
        pytest.fail("result decode must not allocate before combined rejection")

    monkeypatch.setattr(process.Codec, "decode", no_decode)
    with pytest.raises(process.ProcessValidationError, match="preallocation"):
        process.supervise(
            tmp_path,
            request(),
            deadline=125,
            finalization_deadline=135,
            clock=lambda: 100,
            backend=FakeJob,
        )


def test_probe_failure_records_case_cleanup_and_all_unrun_cases(monkeypatch):
    import runpy

    module = runpy.run_path(
        str(Path(__file__).parents[1] / "scripts/profile_teignmouth_process_validation_v1.py")
    )

    class FailedImmediate:
        def __init__(self, *args, **kwargs):
            self.pid = 123456

        def exited(self):
            return True

        def exit_code(self):
            return 2

        def empty(self):
            return True

        def terminate(self):
            pass

        def wait_exit(self, *args):
            return True

        def close(self):
            pass

    module["containment_probe"].__globals__["WindowsJob"] = FailedImmediate
    result = module["containment_probe"](Path.cwd())
    assert result["passes"] is False
    assert [item["case"] for item in result["cases"]] == list(module["PROBE_CASES"])
    assert result["cases"][0]["outcome"] == "fail"
    assert result["cases"][0]["exitCodeBeforeCleanup"] == 2
    assert result["cases"][0]["cleanupConfirmed"] is True
    assert all(item["outcome"] == "not_run" for item in result["cases"][1:])


def test_worker_request_rejects_before_decode(tmp_path, monkeypatch):
    envelope = {
        "protocol": process.PROTOCOL,
        "invocation": "synthetic",
        "request": {
            "tag": "bytes",
            "blob": {"file": "request-000000.bin", "bytes": process.MAX_BYTES, "sha256": "a" * 64},
        },
        "memory": {"baselineBytes": process.MAX_BYTES},
    }
    (tmp_path / "request.json").write_bytes(process.canonical(envelope))
    monkeypatch.setattr(process.Codec, "decode", lambda *args: pytest.fail("must preflight"))
    with pytest.raises(process.ProcessValidationError, match="allocation plan"):
        process.worker_main(tmp_path, tmp_path)


def test_worker_result_rejects_before_encoding(tmp_path, monkeypatch):
    encoded = process.Codec(tmp_path, "request").encode(request())
    envelope = {
        "protocol": process.PROTOCOL,
        "invocation": "synthetic",
        "request": encoded,
        "memory": {"baselineBytes": 100000},
    }
    (tmp_path / "request.json").write_bytes(process.canonical(envelope))
    result = response(success=True)
    result["resources"]["peakConstructionBufferBytes"] = process.MAX_BYTES
    monkeypatch.setattr(process, "execute_transaction", lambda *args, **kwargs: result)
    monkeypatch.setattr(process.Codec, "encode", lambda *args: pytest.fail("must preflight"))
    with pytest.raises(process.ProcessValidationError, match="preallocation"):
        process.worker_main(tmp_path, tmp_path)


def test_successful_assembly_budget_rejects_before_asset_allocation(monkeypatch):
    import runpy
    import sys

    import shapely

    from torquay_pipeline import road_surface_validation_v2 as validator

    root = Path(__file__).resolve().parents[2]
    wrapper = runpy.run_path(
        str(root / "pipeline/scripts/run_teignmouth_topology_validation_v2.py")
    )
    config_path = root / "config/road-surface-teignmouth-topology-transition-v2.json"
    config = json.loads(config_path.read_bytes())
    mesh = SimpleNamespace(
        vertices_xz=np.zeros((3, 2)),
        base_y=np.zeros(3),
        triangles=np.asarray([[0, 1, 2]], dtype="<u4"),
    )
    surface = SimpleNamespace(mesh=mesh, patch_heights=np.zeros(3, dtype="<f4"))
    bindings = {
        "runtimeHashes": {
            **wrapper["_runtime_code_hashes"](config, root),
            config_path.relative_to(root).as_posix(): process.digest(config_path.read_bytes()),
        },
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "shapely": shapely.__version__,
            "geos": shapely.geos_version_string,
        },
        "dataSourceManifestSha256": process.digest(
            (root / "data/source-manifest.json").read_bytes()
        ),
    }
    synthetic = {
        "surface": surface,
        "bindings": bindings,
        "candidateSha256": process.digest(surface.patch_heights.tobytes()),
        "influence": None,
        "constraints": [],
        "solver": {},
        "acceptedPreviewHashes": {},
        "deadline": 125,
        "_transportBaselineBytes": process.MAX_BYTES,
    }
    monkeypatch.setattr(
        validator,
        "validate_offline_candidate_v2",
        lambda *args, **kwargs: (
            {"passes": True, "roadPathReclip": {"groups": {}}},
            SimpleNamespace(gate_seconds={}),
        ),
    )
    monkeypatch.setattr(
        patch,
        "assemble_deterministic_candidate_assets",
        lambda *args: pytest.fail("assembly must not allocate after failed preflight"),
    )
    with pytest.raises(process.ProcessValidationError, match="preallocation"):
        process.execute_transaction(synthetic, root=root)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "ASCII",
        '"\\\n\r\t\b\f\x00\x1f',
        "caf\u00e9",
        "e\u0301",
        "\uffff",
        "\U00010000",
        "\U0001f600",
        "\U0010ffff",
        "\ud800",
        "\udfff",
        "a\U0001f600\ud800\u0301\\\n",
    ],
)
def test_unicode_string_bound_covers_unchanged_ascii_json_bytes(text):
    expected = json.dumps(text, ensure_ascii=True, allow_nan=False).encode("ascii")
    assert process.json_string_bound(text) >= len(expected)
    assert process.value_bound(text) == (0, process.json_string_bound(text))
    assert process.canonical(text) == expected


def test_supplementary_code_point_reserves_both_surrogate_escapes():
    assert process.json_string_bound("\U0001f600") == 14
    assert process.canonical("\U0001f600") == b'"\\ud83d\\ude00"'
    assert process.json_string_bound("\ud800") == 8


@pytest.mark.parametrize(
    "value",
    [
        Path("synthetic/\U0001f600/\U0010ffff"),
        {"\U0001f600": ["\U0010ffff", ("\ud800", "e\u0301")]},
        {(1, "\U0001f600"): {Path("\U0010ffff"): [None, True, 3, 1.25]}},
        {"path": Path("\ud800"), 3: "\uffff", False: "\U00010000"},
    ],
)
def test_unicode_paths_keys_and_nested_values_cover_encoded_structure(tmp_path, value):
    binary, metadata = process.value_bound(value)
    encoder = process.Codec(tmp_path, "request")
    encoded = encoder.encode(value)
    assert metadata >= len(process.canonical(encoded))
    assert binary >= encoder.byte_count


def test_unicode_bound_includes_dataclass_structure(tmp_path):
    mesh = _small_patch_surface().mesh
    binary, metadata = process.value_bound(mesh)
    encoder = process.Codec(tmp_path, "request")
    encoded = encoder.encode(mesh)
    assert metadata >= len(process.canonical(encoded))
    assert binary >= encoder.byte_count


def test_non_bmp_64_mib_boundary_rejects_before_transport_or_backend(tmp_path, monkeypatch):
    # Only the source string (~5.4 MiB) exists. Never allocate its escaped JSON,
    # any sidecar or worker/asset buffer. The production ceiling is not patched.
    assert process.MAX_BYTES == 64 * 1024 * 1024
    empty_metadata = process.value_bound({"payload": ""})[1]
    count = (process.MAX_BYTES // 4 - 1024 - empty_metadata) // 12 + 1
    payload = {"payload": "\U0001f600" * count}
    assert 4 * (empty_metadata + 6 * count + 1024) < process.MAX_BYTES
    _, metadata = process.value_bound(payload)
    assert 4 * (metadata + 1024) > process.MAX_BYTES

    def forbidden(*args, **kwargs):
        pytest.fail(
            "Unicode preflight must reject before serialization/transport/allocation/launch"
        )

    monkeypatch.setattr(process, "canonical", forbidden)
    for name in ("encode", "decode", "blob", "unblob"):
        monkeypatch.setattr(process.Codec, name, forbidden)
    monkeypatch.setattr(patch, "assemble_deterministic_candidate_assets", forbidden)
    with pytest.raises(process.ProcessValidationError, match="preallocation"):
        process.supervise(
            tmp_path,
            payload,
            deadline=125,
            finalization_deadline=135,
            clock=lambda: 100,
            backend=forbidden,
        )


def test_canonical_bytes_remain_identical_to_previous_serializer():
    value = {"\U0001f600": ["\ud800", "a\n\\", "\u0301", "\U0010ffff", 1.25, None]}
    before = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    assert process.canonical(value) == before
