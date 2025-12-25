//! Type-level units and quantities.
//!
//! This module provides a minimal `Quantity<U>` type and marker unit types
//! (e.g. [`Meters`], [`Radians`], [`Degrees`]). The goal is to encode units in
//! the type system so that, for example, you cannot accidentally add angles to
//! lengths or mix radians and degrees without an explicit conversion.
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

/// Marker trait for angle units.
pub trait AngleUnit: Unit {}

/// Zero-sized marker type representing meters as a length unit.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Meters;

/// Zero-sized marker type representing radians as an angle unit.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Radians;

/// Zero-sized marker type representing degrees as an angle unit.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Degrees;

impl Unit for Meters {}
impl LengthUnit for Meters {}

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
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Quantity<U: Unit> {
    /// The numeric value of this quantity.
    pub value: f64,
    _unit: PhantomData<U>,
}

impl<U: Unit> Quantity<U> {
    /// Construct a new quantity with unit `U`.
    #[inline]
    pub const fn new(value: f64) -> Self {
        Self {
            value,
            _unit: PhantomData,
        }
    }

    /// Access the raw numeric value.
    #[inline]
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
