//! 3D points tagged with a coordinate frame.
//!
//! [`Point3`] encodes the coordinate frame as a type parameter `F`, which
//! implements [`crate::frame::Frame`]. This prevents mixing frames by accident.
//!
//! ```rust
//! use spatial_typestate::{Frame, Point3};
//!
//! struct World;
//! impl Frame for World {}
//!
//! let p: Point3<World> = Point3::new(1.0, 2.0, 3.0);
//! ```

use core::marker::PhantomData;

use crate::frame::Frame;

/// A 3D point tagged with a coordinate frame `F`.
///
/// The coordinates (`x`, `y`, `z`) are stored as `f64` and are interpreted
/// according to your domain conventions (e.g. meters, right-handed).
///
/// By encoding the frame in the type parameter `F`, the compiler enforces that
/// you cannot accidentally mix points from different frames.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Point3<F: Frame> {
    /// X coordinate in frame `F`.
    pub x: f64,
    /// Y coordinate in frame `F`.
    pub y: f64,
    /// Z coordinate in frame `F`.
    pub z: f64,
    _frame: PhantomData<F>,
}

impl<F: Frame> Point3<F> {
    /// Construct a new point in the frame `F`.
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
