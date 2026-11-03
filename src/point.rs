//! 3D positions tagged with a coordinate frame and explicit length unit.
//!
//! [`Point3`] encodes the coordinate frame as a type parameter `F`, which
//! implements [`crate::frame::Frame`]. This prevents mixing frames by accident.
//!
//! ```rust
//! use spatial_typestate::{Meters, Frame, Point3};
//!
//! struct World;
//! impl Frame for World {}
//!
//! let p: Point3<World, Meters> = Point3::<_, Meters>::new(1.0, 2.0, 3.0);
//! ```

use core::marker::PhantomData;

use crate::frame::Frame;
use crate::units::{LengthUnit, LinearLengthUnit, conversion_factor, convert_component};

/// A 3D point tagged with coordinate frame `F` and length unit `L`.
///
/// The coordinates (`x`, `y`, `z`) are stored as `f64` and are interpreted
/// in `L`. Raw construction/public mutation asserts units without validating
/// physical meaning or finiteness. There is no default unit.
///
/// By encoding the frame in the type parameter `F`, the compiler enforces that
/// you cannot accidentally mix points from different frames.
///
/// Positions require lengths, unlike vectors which may be dimensionless:
/// ```
/// use spatial_typestate::{Dimensionless, Frame, Meters, Point3};
/// struct World;
/// impl Frame for World {}
/// let _ = Point3::<World, Meters>::new(1.0, 2.0, 3.0);
/// ```
/// ```compile_fail
/// use spatial_typestate::{Dimensionless, Frame, Meters, Point3};
/// struct World;
/// impl Frame for World {}
/// let _ = Point3::<World, Dimensionless>::new(1.0, 2.0, 3.0);
/// ```
pub struct Point3<F: Frame, L: LengthUnit> {
    /// X coordinate in frame `F`.
    pub x: f64,
    /// Y coordinate in frame `F`.
    pub y: f64,
    /// Z coordinate in frame `F`.
    pub z: f64,
    _frame: PhantomData<F>,
    _unit: PhantomData<L>,
}

impl<F: Frame, L: LengthUnit> Point3<F, L> {
    /// Construct a new point in the frame `F`.
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

impl<F: Frame, L: LengthUnit> Copy for Point3<F, L> {}

impl<F: Frame, L: LengthUnit> Clone for Point3<F, L> {
    fn clone(&self) -> Self {
        *self
    }
}

impl<F: Frame, L: LengthUnit> core::fmt::Debug for Point3<F, L> {
    fn fmt(&self, formatter: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        formatter
            .debug_struct("Point3")
            .field("x", &self.x)
            .field("y", &self.y)
            .field("z", &self.z)
            .field("_frame", &self._frame)
            .field("_unit", &self._unit)
            .finish()
    }
}

impl<F: Frame, L: LengthUnit> PartialEq for Point3<F, L> {
    fn eq(&self, other: &Self) -> bool {
        self.x == other.x && self.y == other.y && self.z == other.z
    }
}

impl<F: Frame, L: LinearLengthUnit> Point3<F, L> {
    /// Explicitly convert length components, preserving the frame.
    ///
    /// # Errors
    /// Uses the same metadata, representable-factor and finite-value checks as
    /// [`crate::Quantity::convert_to`]. Underflow/rounding are allowed.
    pub fn convert_to<V: LinearLengthUnit>(self) -> Result<Point3<F, V>, crate::SpatialError> {
        let factor = conversion_factor::<L, V>()?;
        Ok(Point3::new(
            convert_component(self.x, factor)?,
            convert_component(self.y, factor)?,
            convert_component(self.z, factor)?,
        ))
    }
}
