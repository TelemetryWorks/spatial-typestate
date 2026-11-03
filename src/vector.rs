//! 3D vectors tagged with a coordinate frame and explicit unit.
//!
//! [`Vector3`] encodes the coordinate frame as a type parameter `F`, which
//! implements [`crate::frame::Frame`]. This matches the semantics of
//! [`crate::point::Point3`] but represents directions or differences rather
//! than absolute positions.
//!
//! ```rust
//! use spatial_typestate::{Meters, Frame, Vector3};
//!
//! struct Body;
//! impl Frame for Body {}
//!
//! let v: Vector3<Body, Meters> = Vector3::<_, Meters>::new(0.0, 1.0, 0.0);
//! ```

use core::marker::PhantomData;

use crate::frame::Frame;
use crate::units::{LinearLengthUnit, Unit, conversion_factor, convert_component};

/// A 3D vector tagged with coordinate frame `F` and unit `U`.
///
/// Vectors typically represent directions, velocities, or differences between
/// points. As with [`crate::point::Point3`], the frame is encoded in the
/// type parameter. `U` may be a length, [`crate::Dimensionless`], or an opaque
/// application unit such as velocity. Rotation preserves `U` without needing
/// conversion metadata. Raw/public components remain unvalidated assertions.
pub struct Vector3<F: Frame, U: Unit> {
    /// X component in frame `F`.
    pub x: f64,
    /// Y component in frame `F`.
    pub y: f64,
    /// Z component in frame `F`.
    pub z: f64,
    _frame: PhantomData<F>,
    _unit: PhantomData<U>,
}

impl<F: Frame, U: Unit> Vector3<F, U> {
    /// Construct a new vector in the frame `F`.
    #[inline]
    #[must_use]
    pub const fn new(x: f64, y: f64, z: f64) -> Self {
        Self {
            x,
            y,
            z,
            _frame: PhantomData,
            _unit: PhantomData,
        }
    }
}

impl<F: Frame, U: Unit> Copy for Vector3<F, U> {}

impl<F: Frame, U: Unit> Clone for Vector3<F, U> {
    fn clone(&self) -> Self {
        *self
    }
}

impl<F: Frame, U: Unit> core::fmt::Debug for Vector3<F, U> {
    fn fmt(&self, formatter: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        formatter
            .debug_struct("Vector3")
            .field("x", &self.x)
            .field("y", &self.y)
            .field("z", &self.z)
            .field("_frame", &self._frame)
            .field("_unit", &self._unit)
            .finish()
    }
}

impl<F: Frame, U: Unit> PartialEq for Vector3<F, U> {
    fn eq(&self, other: &Self) -> bool {
        self.x == other.x && self.y == other.y && self.z == other.z
    }
}

impl<F: Frame, U: LinearLengthUnit> Vector3<F, U> {
    /// Explicitly convert length components, preserving the frame.
    ///
    /// ```
    /// use spatial_typestate::{Dimensionless, Feet, Frame, Meters, Vector3};
    /// struct World;
    /// impl Frame for World {}
    /// let _ = Vector3::<World, Meters>::new(1.0, 2.0, 3.0).convert_to::<Feet>()?;
    /// # Ok::<(), spatial_typestate::SpatialError>(())
    /// ```
    /// Dimensionless vectors can rotate, but lengths cannot convert into them:
    /// ```compile_fail
    /// use spatial_typestate::{Dimensionless, Feet, Frame, Meters, Vector3};
    /// struct World;
    /// impl Frame for World {}
    /// let _ = Vector3::<World, Meters>::new(1.0, 2.0, 3.0).convert_to::<Dimensionless>()?;
    /// # Ok::<(), spatial_typestate::SpatialError>(())
    /// ```
    ///
    /// # Errors
    /// Uses the same metadata, representable-factor and finite-value checks as
    /// [`crate::Quantity::convert_to`]. Underflow/rounding are allowed.
    pub fn convert_to<V: LinearLengthUnit>(self) -> Result<Vector3<F, V>, crate::SpatialError> {
        let factor = conversion_factor::<U, V>()?;
        Ok(Vector3::new(
            convert_component(self.x, factor)?,
            convert_component(self.y, factor)?,
            convert_component(self.z, factor)?,
        ))
    }
}
