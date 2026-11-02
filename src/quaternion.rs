//! Frame-tagged unit quaternions.
//!
//! [`UnitQuat<F>`] represents a unit quaternion associated with a coordinate
//! frame `F`. It can be used for rotations within that frame or as part of
//! rigid transforms.
//!
//! The type provides a checked constructor [`UnitQuat::try_from_components`]
//! that accepts every finite, nonzero input quaternion, including subnormals,
//! and normalizes it without overflowing the norm calculation. Components are
//! private and available through read-only accessors.

use core::marker::PhantomData;

use crate::errors::SpatialError;
use crate::frame::Frame;

// Private to the scaled quaternion norm: finite input in [1, 4] only.
// For exact arithmetic, relative error e from an overestimate obeys
// e_next = e*e / (2*(1+e)). Starting at 2 gives e <= 1, then <= 1/4,
// 1/40, 1/3280, ~4.65e-8, ~1.08e-15, ~5.9e-31 after six steps.
// Eight steps allow rounding to settle; this is NOT a correctly-rounded sqrt
// guarantee. Tests allow 4*EPSILON relative error and 8*EPSILON relative residual.
#[cfg(any(not(feature = "std"), test))]
fn sqrt_bounded(value: f64) -> f64 {
    debug_assert!((1.0..=4.0).contains(&value));
    let mut estimate = 2.0;
    for _ in 0..8 {
        estimate -= 0.5 * (estimate - value / estimate);
    }
    estimate
}

/// A unit quaternion associated with a coordinate frame `F`.
///
/// The quaternion is stored in `(x, y, z, w)` form, with the invariant that
/// `x^2 + y^2 + z^2 + w^2 == 1` (within numerical tolerance).
/// Public construction and read-only access preserve finite components and
/// approximate unit length; this does not certify a physical frame or rotation.
/// Components use Hamilton order `(x, y, z, w)`. Equality compares components,
/// so antipodal quaternions `q` and `-q` are unequal even when their rotations
/// are equivalent. The single frame tag does not encode a source/target pair.
///
/// Checked construction with a bare frame setup succeeds:
/// ```
/// use spatial_typestate::{UnitQuat, spatial_frames};
/// spatial_frames! { World }
/// let _ = UnitQuat::<World>::try_from_components(0.0, 0.0, 0.0, 1.0).unwrap();
/// ```
/// The same setup cannot bypass validation with the removed constructor:
/// ```compile_fail
/// use spatial_typestate::{UnitQuat, spatial_frames};
/// spatial_frames! { World }
/// let _ = UnitQuat::<World>::new_unchecked(0.0, 0.0, 0.0, 0.0);
/// ```
pub struct UnitQuat<F: Frame> {
    /// X component of the quaternion.
    x: f64,
    /// Y component of the quaternion.
    y: f64,
    /// Z component of the quaternion.
    z: f64,
    /// W component (scalar part) of the quaternion.
    w: f64,
    _frame: PhantomData<F>,
}

impl<F: Frame> UnitQuat<F> {
    /// Construct a unit quaternion from raw components, normalizing them.
    ///
    /// Accepts all finite inputs except an all-zero quaternion (including signed
    /// zeros). Scaling by the largest absolute component keeps the squared norm
    /// in `[1, 4]`, even for subnormal inputs or components near [`f64::MAX`].
    /// Very small components relative to the largest may round to signed zero;
    /// the resulting norm is one within floating-point rounding error.
    /// With `std`, the bounded norm uses native `f64::sqrt`. Without `std`, a
    /// private eight-step Newton approximation is used only on `[1, 4]`; it
    /// is not a general-purpose or correctly-rounded square-root API.
    ///
    /// ```
    /// use spatial_typestate::{UnitQuat, spatial_frames};
    /// spatial_frames! { World }
    /// let q = UnitQuat::<World>::try_from_components(f64::MAX, 0.0, 0.0, 0.0)?;
    /// assert_eq!(q.x(), 1.0);
    /// # Ok::<(), spatial_typestate::SpatialError>(())
    /// ```
    ///
    /// # Errors
    ///
    /// Returns [`SpatialError::NonFinite`] if any component is non-finite, or
    /// [`SpatialError::ZeroNormQuaternion`] if all four components are zero.
    pub fn try_from_components(x: f64, y: f64, z: f64, w: f64) -> Result<Self, SpatialError> {
        if !x.is_finite() || !y.is_finite() || !z.is_finite() || !w.is_finite() {
            return Err(SpatialError::NonFinite);
        }

        let scale = x.abs().max(y.abs()).max(z.abs()).max(w.abs());
        if scale == 0.0 {
            return Err(SpatialError::ZeroNormQuaternion);
        }

        let x = x / scale;
        let y = y / scale;
        let z = z / scale;
        let w = w / scale;
        // At least one scaled component has magnitude one; none exceeds one.
        // Divide by this bounded norm directly, never by scale * norm.
        let norm_sq = x * x + y * y + z * z + w * w;
        #[cfg(feature = "std")]
        let norm = norm_sq.sqrt();
        #[cfg(not(feature = "std"))]
        let norm = sqrt_bounded(norm_sq);
        Ok(Self {
            x: x / norm,
            y: y / norm,
            z: z / norm,
            w: w / norm,
            _frame: PhantomData,
        })
    }

    /// X component of the normalized quaternion.
    #[inline]
    #[must_use]
    pub const fn x(&self) -> f64 {
        self.x
    }

    /// Y component of the normalized quaternion.
    #[inline]
    #[must_use]
    pub const fn y(&self) -> f64 {
        self.y
    }

    /// Z component of the normalized quaternion.
    #[inline]
    #[must_use]
    pub const fn z(&self) -> f64 {
        self.z
    }

    /// W component (scalar part) of the normalized quaternion.
    #[inline]
    #[must_use]
    pub const fn w(&self) -> f64 {
        self.w
    }

    /// The identity rotation quaternion.
    #[inline]
    #[must_use]
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

impl<F: Frame> Copy for UnitQuat<F> {}

impl<F: Frame> Clone for UnitQuat<F> {
    fn clone(&self) -> Self {
        *self
    }
}

impl<F: Frame> core::fmt::Debug for UnitQuat<F> {
    fn fmt(&self, formatter: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        formatter
            .debug_struct("UnitQuat")
            .field("x", &self.x)
            .field("y", &self.y)
            .field("z", &self.z)
            .field("w", &self.w)
            .field("_frame", &self._frame)
            .finish()
    }
}

impl<F: Frame> PartialEq for UnitQuat<F> {
    fn eq(&self, other: &Self) -> bool {
        self.x == other.x && self.y == other.y && self.z == other.z && self.w == other.w
    }
}

#[cfg(test)]
mod tests {
    // Link std only in the test harness to obtain an independent native sqrt
    // reference. This does not enable the library's `std` feature or norm path.
    #[cfg(not(feature = "std"))]
    extern crate std;

    use super::sqrt_bounded;

    fn check_sqrt(value: f64) {
        let actual = sqrt_bounded(value);
        let reference = value.sqrt();
        assert!(actual.is_finite());
        assert!((actual - reference).abs() <= 4.0 * f64::EPSILON * reference);
        assert!((actual * actual - value).abs() <= 8.0 * f64::EPSILON * value);
    }

    #[test]
    fn bounded_sqrt_interval_edges_and_neighbors() {
        for value in [1.0_f64, 2.0, 3.0, 4.0] {
            check_sqrt(value);
            if value > 1.0 {
                check_sqrt(f64::from_bits(value.to_bits() - 1));
            }
            if value < 4.0 {
                check_sqrt(f64::from_bits(value.to_bits() + 1));
            }
        }
    }

    #[test]
    fn bounded_sqrt_dense_interval() {
        for index in 0..=100_000 {
            check_sqrt(1.0 + 3.0 * f64::from(index) / 100_000.0);
        }
    }

    #[test]
    fn bounded_sqrt_randomized_bit_patterns() {
        let first = 1.0_f64.to_bits();
        let count = 4.0_f64.to_bits() - first + 1;
        let mut state = 0x4d59_5df4_d0f3_3173_u64;
        for _ in 0..100_000 {
            // A reproducible sampler over both exponents in [1, 4].
            state = state
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1);
            check_sqrt(f64::from_bits(first + state % count));
        }
    }
}
