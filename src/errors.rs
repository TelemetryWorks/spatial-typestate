//! Error types for spatial-typestate operations.
//!
//! This module currently defines a single [`SpatialError`] enum, which will
//! grow as more checked operations are added (e.g. for unit quaternions,
//! normalization failures, invalid inputs, etc.).

/// Errors that may occur in spatial operations.
///
/// The set of error variants is intentionally small for now, but can be
/// extended in a backward-compatible way as the library evolves.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SpatialError {
    /// A value was non-finite (`NaN` or infinite) where a finite number was
    /// required.
    NonFinite,

    /// A quaternion with zero (or effectively zero) norm was provided where
    /// a unit quaternion was required.
    ZeroNormQuaternion,
}
