//! Rigid transforms between coordinate frames.
//!
//! [`Transform<From, To>`] represents a rigid transformation from frame
//! `From` to frame `To`. Applying the transform to a [`crate::point::Point3`]
//! tagged with `From` yields a point tagged with `To`.
//!
//! ```rust
//! use spatial_typestate::{Frame, Point3, Transform};
//!
//! struct World;
//! struct Body;
//! impl Frame for World {}
//! impl Frame for Body {}
//!
//! let p_body = Point3::<Body>::new(1.0, 0.0, 0.0);
//! let t_body_world: Transform<Body, World> = Transform::identity();
//!
//! let p_world = t_body_world.apply_point(p_body);
//! ```

use core::marker::PhantomData;

use crate::frame::Frame;
use crate::point::Point3;

/// A rigid transform from frame `From` to frame `To`.
///
/// Conceptually, this encodes a rotation and translation that converts
/// coordinates expressed in `From` into coordinates expressed in `To`.
///
/// The current implementation uses a minimal 4×4 matrix representation.
/// The exact storage may change in future versions as we integrate with a
/// math backend, but the **type-level frame parameters** are intended to
/// remain stable.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Transform<From: Frame, To: Frame> {
    /// Column-major 4×4 transform matrix.
    ///
    /// This is intentionally simple and explicit. In future versions, this may
    /// be replaced by or wrap a math-backend-specific type while preserving
    /// the public API guarantees.
    pub matrix: [[f64; 4]; 4],
    _from: PhantomData<From>,
    _to: PhantomData<To>,
}

impl<From: Frame, To: Frame> Transform<From, To> {
    /// Construct an identity transform (no rotation, no translation).
    #[inline]
    pub const fn identity() -> Self {
        Self {
            matrix: [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            _from: PhantomData,
            _to: PhantomData,
        }
    }

    /// Construct from a raw 4×4 matrix.
    ///
    /// The caller is responsible for ensuring this represents a valid rigid
    /// transform if that is required by the domain.
    #[inline]
    pub const fn from_matrix(matrix: [[f64; 4]; 4]) -> Self {
        Self {
            matrix,
            _from: PhantomData,
            _to: PhantomData,
        }
    }

    /// Construct a pure translation transform (no rotation).
    #[inline]
    pub fn from_translation(tx: f64, ty: f64, tz: f64) -> Self {
        let mut m = [[0.0_f64; 4]; 4];
        m[0][0] = 1.0;
        m[1][1] = 1.0;
        m[2][2] = 1.0;
        m[3][3] = 1.0;
        m[0][3] = tx;
        m[1][3] = ty;
        m[2][3] = tz;

        Self::from_matrix(m)
    }

    /// Apply this transform to a point in the `From` frame, producing a point
    /// in the `To` frame.
    ///
    /// This uses homogeneous coordinates (`w = 1`) under the hood.
    #[inline]
    pub fn apply_point(&self, p: Point3<From>) -> Point3<To> {
        let m = &self.matrix;
        let x = p.x;
        let y = p.y;
        let z = p.z;

        let xp = m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3];
        let yp = m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3];
        let zp = m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3];

        Point3::<To>::new(xp, yp, zp)
    }
}
