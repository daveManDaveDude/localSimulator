"""Versioned Float32 local-frame contract for the Teignmouth prototype only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .road_surface_topology import TopologyError, _float32_bytes

FRAME_VERSION = "teignmouth-float32-local-v1"
ORIGIN_XYZ_M = (-140.0, 0.0, -95.0)
FRAME_UNITS = "metres"
AXIS_CONVENTION = "X east, Y up unchanged, Z south; world=origin+decoded_local_XZ"


class Float32FrameError(ValueError):
    """The local-frame metadata or stored coordinates violate the pinned contract."""


@dataclass(frozen=True)
class Float32LocalFrame:
    """Store local X/Z Float32 and unrebased Y Float32; decode world only as Float64."""

    version: str = FRAME_VERSION
    origin_xyz_m: tuple[float, float, float] = ORIGIN_XYZ_M
    units: str = FRAME_UNITS
    axis_convention: str = AXIS_CONVENTION

    def __post_init__(self) -> None:
        if self.version != FRAME_VERSION:
            raise Float32FrameError("unsupported Float32 frame version")
        if tuple(self.origin_xyz_m) != ORIGIN_XYZ_M:
            raise Float32FrameError("frame origin is frozen at [-140, 0, -95] metres")
        if self.units != FRAME_UNITS or self.axis_convention != AXIS_CONVENTION:
            raise Float32FrameError("frame units or axis convention was altered")

    def to_metadata(self) -> dict[str, Any]:
        return {
            "schema": "teignmouth-display-frame-v1",
            "version": self.version,
            "originXYZM": list(self.origin_xyz_m),
            "units": self.units,
            "axisConvention": self.axis_convention,
            "storedPosition": "local XYZ Float32; local X/Z, unrebased Y",
            "worldReconstruction": "origin X/Z + decoded local X/Z in Float64; Y unchanged",
            "immutable": True,
        }

    @classmethod
    def from_metadata(cls, value: Any) -> Float32LocalFrame:
        expected = cls().to_metadata()
        if not isinstance(value, dict) or value != expected:
            raise Float32FrameError("frame metadata does not match the exact versioned contract")
        return cls()

    def world_xz_to_local64(self, world_xz: np.ndarray) -> np.ndarray:
        points = _finite_matrix(world_xz, 2, "world X/Z")
        return points - np.asarray((self.origin_xyz_m[0], self.origin_xyz_m[2]))

    def local_xz_to_world64(self, local_xz: np.ndarray) -> np.ndarray:
        points = _finite_matrix(local_xz, 2, "local X/Z")
        return points + np.asarray((self.origin_xyz_m[0], self.origin_xyz_m[2]))

    def geometry_to_local(self, geometry: Any) -> Any:
        """Translate an immutable global Shapely geometry into this fixed local frame."""
        from shapely.affinity import translate

        return translate(geometry, xoff=-self.origin_xyz_m[0], yoff=-self.origin_xyz_m[2])

    def geometry_to_world64(self, geometry: Any) -> Any:
        """Reconstruct a local Shapely geometry in Float64 world X/Z coordinates."""
        from shapely.affinity import translate

        return translate(geometry, xoff=self.origin_xyz_m[0], yoff=self.origin_xyz_m[2])

    def store_xz(self, world_xz: np.ndarray) -> np.ndarray:
        """Encode X/Z only; caller must run the unchanged topology guard in this frame."""
        local = self.world_xz_to_local64(world_xz)
        with np.errstate(over="ignore", invalid="ignore"):
            stored = np.asarray(local, dtype="<f4")
        if not np.isfinite(stored).all():
            raise Float32FrameError("local X/Z overflows finite Float32")
        return np.ascontiguousarray(stored)

    def store_xyz(self, world_xyz: np.ndarray) -> np.ndarray:
        """Encode local X/Z and preserve the original, unrebased world Y values."""
        points = _finite_matrix(world_xyz, 3, "world XYZ")
        local = points.copy()
        local[:, 0] -= self.origin_xyz_m[0]
        local[:, 2] -= self.origin_xyz_m[2]
        with np.errstate(over="ignore", invalid="ignore"):
            stored = np.asarray(local, dtype="<f4")
        if not np.isfinite(stored).all():
            raise Float32FrameError("stored local XYZ overflows finite Float32")
        return np.ascontiguousarray(stored)

    def decode_xyz_to_world64(self, stored_xyz: np.ndarray) -> np.ndarray:
        """Decode the actual serialized Float32 values, then reconstruct in Float64."""
        stored = np.asarray(stored_xyz, dtype="<f4")
        if stored.ndim != 2 or stored.shape[1] != 3 or not np.isfinite(stored).all():
            raise Float32FrameError("stored positions must be finite N-by-3 Float32 values")
        world = stored.astype(np.float64)
        world[:, 0] += self.origin_xyz_m[0]
        world[:, 2] += self.origin_xyz_m[2]
        return world

    def assert_unique_local_xz(self, exact_local_xz: np.ndarray) -> None:
        """Apply the mesher's exact byte-key semantics to actual local coordinates."""
        points = _finite_matrix(exact_local_xz, 2, "exact local X/Z")
        key_to_point: dict[bytes, tuple[float, float]] = {}
        point_to_key: dict[tuple[float, float], bytes] = {}
        for x_value, z_value in points:
            point = (float(x_value), float(z_value))
            key = _float32_bytes(*point)
            prior = key_to_point.get(key)
            if prior is not None and prior != point:
                raise TopologyError(
                    "distinct Float64 topology vertices collide after Float32 conversion: "
                    f"{prior!r} and {point!r}"
                )
            key_to_point[key] = point
            point_to_key[point] = key
        if len(point_to_key) != len(key_to_point):
            raise TopologyError("local Float32 topology keys are not one-to-one")

    def maximum_round_trip_error_m(self, world_xz: np.ndarray) -> tuple[float, float]:
        original = _finite_matrix(world_xz, 2, "world X/Z")
        stored = self.store_xz(original)
        decoded = self.local_xz_to_world64(stored.astype(np.float64))
        error = np.max(np.abs(decoded - original), axis=0)
        return float(error[0]), float(error[1])


def _finite_matrix(value: np.ndarray, width: int, label: str) -> np.ndarray:
    points = np.asarray(value, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != width or not np.isfinite(points).all():
        raise Float32FrameError(f"{label} must be a finite N-by-{width} array")
    return points


def triangle_normal_y(local_xyz: np.ndarray, indices: np.ndarray) -> np.ndarray:
    """Return signed world-up normal component from actual stored vertices."""
    vertices = np.asarray(local_xyz, dtype="<f4").astype(np.float64)
    faces = np.asarray(indices, dtype=np.uint32)
    if faces.ndim != 2 or faces.shape[1] != 3 or (faces.size and faces.max() >= len(vertices)):
        raise Float32FrameError("triangle indices do not match stored vertices")
    triangle = vertices[faces]
    first, second = triangle[:, 1] - triangle[:, 0], triangle[:, 2] - triangle[:, 0]
    return first[:, 2] * second[:, 0] - first[:, 0] * second[:, 2]


def encode_indices(indices: np.ndarray) -> bytes:
    """Serialize validated triangle indices as little-endian unsigned 32-bit values."""
    faces = np.asarray(indices)
    if faces.ndim != 2 or faces.shape[1] != 3 or not np.issubdtype(faces.dtype, np.integer):
        raise Float32FrameError("indices must be an integer N-by-3 triangle array")
    if faces.size and (faces.min() < 0 or faces.max() > 0xFFFFFFFF):
        raise Float32FrameError("triangle indices exceed unsigned 32-bit range")
    return np.ascontiguousarray(faces, dtype="<u4").tobytes()
