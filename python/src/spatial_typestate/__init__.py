"""Immutable batches with runtime frame/unit checks; numeric work runs in Rust."""
import sysconfig

if sysconfig.get_config_var("Py_GIL_DISABLED"):
    raise ImportError("spatial_typestate requires GIL-enabled CPython")

from ._native import (  # noqa: E402
    DIMENSIONLESS, FEET, METERS, Frame, Points, Quaternion, SpatialError,
    Transform, Unit, Vectors,
)

__all__ = [
    "DIMENSIONLESS", "FEET", "METERS", "Frame", "Points", "Quaternion",
    "SpatialError", "Transform", "Unit", "Vectors",
]
