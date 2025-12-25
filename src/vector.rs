//! 3D vectors tagged with a coordinate frame.
//!
//! [`Vector3`] encodes the coordinate frame as a type parameter `F`, which
//! implements [`crate::frame::Frame`]. This matches the semantics of
//! [`crate::point::Point3`] but represents directions or differences rather
//! than absolute positions.
//!
//! ```rust
//! use spatial_typestate::{Frame, Vector3};
//!
//! struct Body;
//! impl Frame for Body {}
//!
//! let v: Vector3<Body> = Vector3::new(0.0, 1.0, 0.0);
//! ```

use core::marker::PhantomData;

use crate::frame::Frame;

/// A 3D vector tagged with a coordinate frame `F`.
///
/// Vectors typically represent directions, velocities, or differences between
/// points. As with [`crate::point::Point3`], the frame is encoded in the
/// type parameter.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Vector3<F: Frame> {
    /// X component in frame `F`.
    pub x: f64,
    /// Y component in frame `F`.
    pub y: f64,
    /// Z component in frame `F`.
    pub z: f64,
    _frame: PhantomData<F>,
}

impl<F: Frame> Vector3<F> {
    /// Construct a new vector in the frame `F`.
    #[inline]
    pub const fn new(x: f64, y: f64, z: f64) -> Self {
        Self {
            x,
            y,
            z,
            _frame: PhantomData,
        }
    }
}
