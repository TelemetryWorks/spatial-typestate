//! Type-level units and quantities.
//!
//! This module provides a minimal `Quantity<U>` type and marker unit types
//! (e.g. [`Meters`], [`Radians`], [`Degrees`]). The goal is to encode units in
//! the type system so that, for example, you cannot accidentally add angles to
//! lengths. Conversions are explicit and currently limited to linear lengths;
//! no angle conversion or dimensional algebra is implemented. Raw quantity
//! construction/public mutation and same-unit arithmetic remain unvalidated.
//!
//! ```rust
//! use spatial_typestate::{Quantity, Meters, Radians};
//!
//! let altitude: Quantity<Meters> = Quantity::new(1500.0);
//! let angle: Quantity<Radians> = Quantity::new(1.5708);
//! ```

use core::marker::PhantomData;
use core::ops::{Add, Sub};

/// Marker trait for a physical unit.
///
/// Unit types are typically zero-sized marker types such as [`Meters`],
/// [`Radians`], or [`Degrees`]. The trait is intentionally empty; semantics
/// are carried by the type itself.
pub trait Unit: 'static {}

/// Marker trait for length units.
pub trait LengthUnit: Unit {}

/// Opt-in conversion metadata for linear length units only.
///
/// The caller declares the physical meaning: the library cannot verify it.
/// Scales must be positive and finite; conversion validates both declarations
/// and their representable ratio. Offset units and dimensional algebra are
/// outside this trait. Opaque length units need not implement it.
pub trait LinearLengthUnit: LengthUnit {
    /// Number of meters in one unit. Must be positive and finite.
    const METERS_PER_UNIT: f64;
}

/// Marker trait for angle units.
pub trait AngleUnit: Unit {}

/// Zero-sized marker type representing meters as a length unit.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Meters;

/// International feet (one foot is exactly 0.3048 meters by definition).
/// Floating-point conversions still round; this is not the U.S. survey foot.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Feet;

/// A dimensionless vector/scalar tag; it is not a length unit.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Dimensionless;

/// Zero-sized marker type representing radians as an angle unit.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Radians;

/// Zero-sized marker type representing degrees as an angle unit.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Degrees;

impl Unit for Meters {}
impl LengthUnit for Meters {}
impl LinearLengthUnit for Meters {
    const METERS_PER_UNIT: f64 = 1.0;
}
impl Unit for Feet {}
impl LengthUnit for Feet {}
impl LinearLengthUnit for Feet {
    const METERS_PER_UNIT: f64 = 0.3048;
}
impl Unit for Dimensionless {}

impl Unit for Radians {}
impl AngleUnit for Radians {}

impl Unit for Degrees {}
impl AngleUnit for Degrees {}

/// A scalar quantity tagged with a unit `U`.
///
/// The underlying numeric type is `f64` for now. This can be generalized to
/// other types later if needed.
///
/// ```rust
/// use spatial_typestate::{Quantity, Meters};
///
/// let distance: Quantity<Meters> = Quantity::new(42.0);
/// ```
pub struct Quantity<U: Unit> {
    /// The numeric value of this quantity.
    pub value: f64,
    _unit: PhantomData<U>,
}

impl<U: LinearLengthUnit> Quantity<U> {
    /// Explicitly convert a length without changing its physical meaning.
    ///
    /// ```
    /// use spatial_typestate::{Feet, Meters, Quantity, Radians};
    /// let _ = Quantity::<Meters>::new(1.0).convert_to::<Feet>()?;
    /// # Ok::<(), spatial_typestate::SpatialError>(())
    /// ```
    ///
    /// Lengths cannot convert to angles. The matching success example above
    /// exercises the same setup; the following fails at the conversion bound:
    /// ```compile_fail
    /// use spatial_typestate::{Feet, Meters, Quantity, Radians};
    /// let _ = Quantity::<Meters>::new(1.0).convert_to::<Radians>()?;
    /// # Ok::<(), spatial_typestate::SpatialError>(())
    /// ```
    ///
    /// The factor is `U::METERS_PER_UNIT / V::METERS_PER_UNIT`, followed by
    /// one multiply per component. Metadata is checked before values. Finite
    /// same-unit conversions preserve bits, including signed zero. Ratios
    /// are not rearranged to rescue extreme inputs.
    ///
    /// # Errors
    /// Invalid scale metadata returns [`crate::SpatialError::InvalidUnitScale`];
    /// a zero/infinite rounded ratio returns
    /// [`crate::SpatialError::UnrepresentableUnitConversion`]. Non-finite input
    /// or output returns [`crate::SpatialError::NonFinite`]. Ordinary underflow
    /// and rounding are allowed. No exact roundtrip guarantee is made.
    pub fn convert_to<V: LinearLengthUnit>(self) -> Result<Quantity<V>, crate::SpatialError> {
        let factor = conversion_factor::<U, V>()?;
        Ok(Quantity::new(convert_component(self.value, factor)?))
    }
}

impl<U: Unit> Copy for Quantity<U> {}
impl<U: Unit> Clone for Quantity<U> {
    fn clone(&self) -> Self {
        *self
    }
}
impl<U: Unit> core::fmt::Debug for Quantity<U> {
    fn fmt(&self, formatter: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        formatter
            .debug_struct("Quantity")
            .field("value", &self.value)
            .field("_unit", &self._unit)
            .finish()
    }
}
impl<U: Unit> PartialEq for Quantity<U> {
    fn eq(&self, other: &Self) -> bool {
        self.value == other.value
    }
}

pub(crate) fn conversion_factor<U: LinearLengthUnit, V: LinearLengthUnit>()
-> Result<f64, crate::SpatialError> {
    let source = U::METERS_PER_UNIT;
    let target = V::METERS_PER_UNIT;
    if !source.is_finite() || source <= 0.0 || !target.is_finite() || target <= 0.0 {
        return Err(crate::SpatialError::InvalidUnitScale);
    }
    let factor = source / target;
    if !factor.is_finite() || factor <= 0.0 {
        return Err(crate::SpatialError::UnrepresentableUnitConversion);
    }
    Ok(factor)
}

pub(crate) fn convert_component(value: f64, factor: f64) -> Result<f64, crate::SpatialError> {
    if !value.is_finite() {
        return Err(crate::SpatialError::NonFinite);
    }
    let result = value * factor;
    if !result.is_finite() {
        return Err(crate::SpatialError::NonFinite);
    }
    Ok(result)
}

impl<U: Unit> Quantity<U> {
    /// Construct a new quantity with unit `U`.
    #[inline]
    #[must_use]
    pub const fn new(value: f64) -> Self {
        Self {
            value,
            _unit: PhantomData,
        }
    }

    /// Access the raw numeric value.
    #[inline]
    #[must_use]
    pub const fn get(self) -> f64 {
        self.value
    }
}

impl<U: Unit> Add for Quantity<U> {
    type Output = Self;

    #[inline]
    fn add(self, rhs: Self) -> Self::Output {
        Self::new(self.value + rhs.value)
    }
}

impl<U: Unit> Sub for Quantity<U> {
    type Output = Self;

    #[inline]
    fn sub(self, rhs: Self) -> Self::Output {
        Self::new(self.value - rhs.value)
    }
}
