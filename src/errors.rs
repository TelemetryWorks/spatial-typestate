//! Error types for spatial-typestate operations.
//!
//! [`SpatialError`] supports ordinary formatting and error propagation without
//! allocating or boxing errors inside the library.
//!
//! Callers can propagate the concrete error, or choose their own boxed error:
//! ```
//! use spatial_typestate::{UnitQuat, spatial_frames};
//! spatial_frames! { World }
//! fn main() -> Result<(), Box<dyn std::error::Error>> {
//!     let quaternion = UnitQuat::<World>::try_from_components(0.0, 0.0, 0.0, 2.0)?;
//!     assert_eq!(quaternion.w(), 1.0);
//!     Ok(())
//! }
//! ```

use core::fmt;

/// Errors that may occur in spatial operations.
///
/// This enum is exhaustive. Adding variants can break downstream exhaustive
/// matches and must be treated as a public API change.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SpatialError {
    /// A participating input or computed output component was non-finite
    /// (`NaN` or infinite), including floating-point overflow.
    NonFinite,

    /// All four quaternion components were zero (positive or negative zero).
    /// Finite nonzero components, including subnormals, are accepted.
    ZeroNormQuaternion,
    /// A finite raw transform failed affine or proper rigid-rotation checks.
    NonRigidTransform,
}

impl fmt::Display for SpatialError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::NonFinite => "non-finite component",
            Self::ZeroNormQuaternion => "all quaternion components are zero",
            Self::NonRigidTransform => "transform is not a proper rigid affine transform",
        })
    }
}

impl core::error::Error for SpatialError {}
