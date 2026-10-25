from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from torquay_pipeline.road_surface_float32_frame import (
    Float32FrameError,
    Float32LocalFrame,
)
from torquay_pipeline.road_surface_topology import TopologyError, _float32_bytes

ROOT = Path(__file__).resolve().parents[2]


def test_fixed_frame_metadata_and_unrebased_y_round_trip() -> None:
    frame = Float32LocalFrame()
    assert Float32LocalFrame.from_metadata(frame.to_metadata()) == frame
    world = np.asarray([[-164.2316811012587, 12.25, -85.5]])
    stored = frame.store_xyz(world)
    decoded = frame.decode_xyz_to_world64(stored)
    assert stored.dtype == np.dtype("<f4")
    assert stored[0, 1] == np.float32(12.25)
    assert decoded[0, 1] == np.float64(stored[0, 1])
    assert np.max(np.abs(decoded[0, (0, 2)] - world[0, (0, 2)])) < 1e-5


def test_known_global_collision_is_distinct_in_fixed_local_frame() -> None:
    frame = Float32LocalFrame()
    pair = np.asarray(
        [[-164.2316811012587, -85.5], [-164.23167542853238, -85.5]],
        dtype=np.float64,
    )
    assert _float32_bytes(*pair[0]) == _float32_bytes(*pair[1])
    local = frame.world_xz_to_local64(pair)
    frame.assert_unique_local_xz(local)
    assert not np.array_equal(np.asarray(local[0], dtype="<f4"), np.asarray(local[1], dtype="<f4"))


def test_frame_rejects_local_float32_aliases_and_corrupt_metadata() -> None:
    frame = Float32LocalFrame()
    with pytest.raises(TopologyError, match="collide"):
        frame.assert_unique_local_xz(np.asarray([[24.0, 1.0], [24.0 + 1e-8, 1.0]]))
    changed = frame.to_metadata()
    changed["originXYZM"] = [-139.0, 0.0, -95.0]
    with pytest.raises(Float32FrameError, match="exact versioned contract"):
        Float32LocalFrame.from_metadata(changed)


def test_actual_candidate_config_loads_and_rejects_changed_origin(tmp_path: Path) -> None:
    from torquay_pipeline.teignmouth_float32_candidate import (
        load_candidate_config,
    )

    config_path = ROOT / "config" / "road-surface-teignmouth-float32.json"
    config = load_candidate_config(config_path)
    assert config.frame.origin_xyz_m == (-140.0, 0.0, -95.0)
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    payload["frame"]["originXYZM"][0] = -139.0
    altered = tmp_path / "altered.json"
    altered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(Float32FrameError):
        load_candidate_config(altered)


def test_nonfinite_and_float32_overflow_are_rejected() -> None:
    frame = Float32LocalFrame()
    with pytest.raises(Float32FrameError, match="finite"):
        frame.store_xz(np.asarray([[np.nan, 0.0]]))
    with pytest.raises(Float32FrameError, match="overflows"):
        frame.store_xz(np.asarray([[1e50, 0.0]]))
