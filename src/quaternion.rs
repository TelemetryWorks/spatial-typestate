//! Frame-tagged unit quaternions.
//!
//! [`UnitQuat<F>`] represents a unit quaternion associated with a coordinate
//! frame `F`. It can be used for rotations within that frame or as part of
//! rigid transforms.
//!
//! The type provides a checked constructor [`UnitQuat::try_from_components`]
//! that normalizes the quaternion and rejects non-finite or zero-norm inputs.

use core::marker::PhantomData;

use crate::errors::SpatialError;
use crate::frame::Frame;

/// A unit quaternion associated with a coordinate frame `F`.
///
/// The quaternion is stored in `(x, y, z, w)` form, with the invariant that
/// `x^2 + y^2 + z^2 + w^2 == 1` (within numerical tolerance).
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct UnitQuat<F: Frame> {
    /// X component of the quaternion.
    pub x: f64,
    /// Y component of the quaternion.
    pub y: f64,
    /// Z component of the quaternion.
    pub z: f64,
    /// W component (scalar part) of the quaternion.
    pub w: f64,
    _frame: PhantomData<F>,
}

impl<F: Frame> UnitQuat<F> {
    /// Construct a unit quaternion from raw components, normalizing them.
    ///
    /// Returns an error if any component is non-finite or if the norm is
    /// too close to zero to be normalized safely.
    pub fn try_from_components(x: f64, y: f64, z: f64, w: f64) -> Result<Self, SpatialError> {
        if !x.is_finite() || !y.is_finite() || !z.is_finite() || !w.is_finite() {
            return Err(SpatialError::NonFinite);
        }

        let norm_sq = x * x + y * y + z * z + w * w;
        if norm_sq == 0.0 {
            return Err(SpatialError::ZeroNormQuaternion);
        }

        let norm = norm_sq.sqrt();
        Ok(Self {
            x: x / norm,
            y: y / norm,
            z: z / norm,
            w: w / norm,
            _frame: PhantomData,
        })
    }

    /// Construct a unit quaternion directly, without normalization.
    ///
    /// # Safety
    ///
    /// The caller must guarantee that `(x, y, z, w)` already form a unit
    /// quaternion. This constructor does **not** check or normalize the input
    /// and is intended for advanced use cases where the invariant is already
    /// established externally.
    pub const fn new_unchecked(x: f64, y: f64, z: f64, w: f64) -> Self {
        Self {
            x,
            y,
            z,
            w,
            _frame: PhantomData,
        }
    }

    /// The identity rotation quaternion.
    #[inline]
    pub const fn identity() -> Self {
        Self {
            x: 0.0,
            y: 0.0,
            z: 0.0,
            w: 1.0,
            _frame: PhantomData,
        }
    }
}
