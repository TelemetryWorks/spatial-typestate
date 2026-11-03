//! Frame mappings, with checked rigid construction/inversion and raw compatibility.
//!
//! [`Transform<From, To>`] represents a rigid transformation from frame
//! `From` to frame `To` when built through the checked rotation/translation
//! constructor; raw public matrices are unvalidated. Applying the transform to a [`crate::point::Point3`]
//! tagged with `From` returns a `Result` whose successful point is tagged with `To`.
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
//! let p_world = t_body_world.apply_point(p_body).unwrap();
//! ```

use core::marker::PhantomData;

use crate::frame::Frame;
use crate::point::Point3;
use crate::{SpatialError, UnitQuat, Vector3};

// Absolute tolerance for affine row, rotation row dot products, and det(R)=+1.
const RIGID_TOLERANCE: f64 = 1e-10;

/// A frame mapping from `From` to `To`, rigid when built from checked rotation
/// and translation. Public raw matrix construction and mutation are unvalidated.
///
/// Conceptually, this encodes a rotation and translation that converts
/// coordinates expressed in `From` into coordinates expressed in `To`.
///
/// The current implementation uses a minimal 4×4 matrix representation.
/// The exact storage may change in future versions as we integrate with a
/// math backend, but the **type-level frame parameters** are intended to
/// remain stable.
pub struct Transform<From: Frame, To: Frame> {
    /// Row-major 4×4 matrix, indexed as `matrix[row][column]`.
    ///
    /// Points are column vectors: the first three rows multiply `[x, y, z, 1]`.
    /// Translation is in `matrix[0][3]`, `matrix[1][3]`, and `matrix[2][3]`. Affine transforms
    /// conventionally have bottom row `[0, 0, 0, 1]`, but this public storage is
    /// unvalidated and [`Self::apply_point`] ignores that row entirely.
    pub matrix: [[f64; 4]; 4],
    _from: PhantomData<From>,
    _to: PhantomData<To>,
}

impl<From: Frame, To: Frame> Transform<From, To> {
    /// Construct an identity transform (no rotation, no translation).
    #[inline]
    #[must_use]
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
    /// transform if that is required by the domain. No finiteness, affine, or
    /// orthonormality checks are performed.
    ///
    /// ```
    /// use spatial_typestate::{Point3, Transform, spatial_frames};
    /// spatial_frames! { World, Body }
    /// let transform = Transform::<World, Body>::from_matrix([
    ///     [0.0, -1.0, 0.0, 10.0],
    ///     [1.0,  0.0, 0.0, 20.0],
    ///     [0.0,  0.0, 1.0, 30.0],
    ///     [0.0,  0.0, 0.0,  1.0],
    /// ]);
    /// let result: Point3<Body> = transform.apply_point(Point3::<World>::new(2.0, 3.0, 4.0)).unwrap();
    /// assert_eq!([result.x, result.y, result.z], [7.0, 22.0, 34.0]);
    /// ```
    #[inline]
    #[must_use]
    pub const fn from_matrix(matrix: [[f64; 4]; 4]) -> Self {
        Self {
            matrix,
            _from: PhantomData,
            _to: PhantomData,
        }
    }

    /// Construct a pure translation transform (no rotation).
    #[inline]
    #[must_use]
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

    /// Construct `R(rotation) * point + translation` from `From` into `To`.
    ///
    /// Uses the right-handed active quaternion rotation formula, column vectors,
    /// and row storage. The translation is expressed in the target frame `To`.
    /// Hamilton quaternion components are ordered `(x, y, z, w)`. The columns
    /// of `R` are the source basis vectors expressed in `To`; `translation` is
    /// the source origin expressed in `To`. `UnitQuat<To>` does not encode the
    /// source frame by itself.
    /// The caller asserts that this rotation relates the chosen physical frames;
    /// frame markers cannot verify calibration. The bottom row is canonical.
    ///
    /// ```
    /// use spatial_typestate::{Point3, Transform, UnitQuat, Vector3, spatial_frames};
    /// spatial_frames! { Sensor, Aircraft }
    /// let transform = Transform::<Sensor, Aircraft>::try_from_rotation_translation(
    ///     UnitQuat::try_from_components(0.0, 0.0, 1.0, 1.0)?,
    ///     Vector3::new(1.0, 2.0, 3.0),
    /// )?;
    /// let result = transform.apply_point(Point3::new(2.0, 0.0, 1.0)).unwrap();
    /// assert!((result.x - 1.0).abs() < 1e-12);
    /// assert!((result.y - 4.0).abs() < 1e-12);
    /// assert!((result.z - 4.0).abs() < 1e-12);
    /// # Ok::<(), spatial_typestate::SpatialError>(())
    /// ```
    ///
    /// # Errors
    /// Returns [`SpatialError::NonFinite`] for a non-finite translation.
    pub fn try_from_rotation_translation(
        rotation: UnitQuat<To>,
        translation: Vector3<To>,
    ) -> Result<Self, SpatialError> {
        if !translation.x.is_finite() || !translation.y.is_finite() || !translation.z.is_finite() {
            return Err(SpatialError::NonFinite);
        }
        let (x, y, z, w) = (rotation.x(), rotation.y(), rotation.z(), rotation.w());
        Ok(Self::from_matrix([
            [
                1.0 - 2.0 * (y * y + z * z),
                2.0 * (x * y - z * w),
                2.0 * (x * z + y * w),
                translation.x,
            ],
            [
                2.0 * (x * y + z * w),
                1.0 - 2.0 * (x * x + z * z),
                2.0 * (y * z - x * w),
                translation.y,
            ],
            [
                2.0 * (x * z - y * w),
                2.0 * (y * z + x * w),
                1.0 - 2.0 * (x * x + y * y),
                translation.z,
            ],
            [0.0, 0.0, 0.0, 1.0],
        ]))
    }

    /// Apply this transform, then `next`: the result is `next(self(point))`.
    ///
    /// Composes the affine maps defined by the first three rows; both raw bottom
    /// rows are ignored, consistently with [`Self::apply_point`]. The result has
    /// canonical bottom row `[0, 0, 0, 1]`. Composition checks finite inputs and
    /// output, but does not certify raw inputs as rigid. Evaluation order is
    /// unchanged; overflow is an error even if another evaluation could cancel it.
    /// Sequential point application and composition check different intermediate
    /// values, so they can differ in which calls overflow and return an error.
    ///
    /// # Errors
    /// Returns [`SpatialError::NonFinite`] for any non-finite entry in either
    /// first-three-row affine map, or non-finite computed output. Ignored raw
    /// bottom rows are not validated.
    pub fn then<Next: Frame>(
        &self,
        next: Transform<To, Next>,
    ) -> Result<Transform<From, Next>, SpatialError> {
        if !self
            .matrix
            .iter()
            .take(3)
            .flatten()
            .all(|entry| entry.is_finite())
            || !next
                .matrix
                .iter()
                .take(3)
                .flatten()
                .all(|entry| entry.is_finite())
        {
            return Err(SpatialError::NonFinite);
        }
        let mut matrix = [[0.0; 4]; 4];
        for (row, output) in matrix.iter_mut().take(3).enumerate() {
            for (column, entry) in output.iter_mut().enumerate() {
                *entry = next.matrix[row][0] * self.matrix[0][column]
                    + next.matrix[row][1] * self.matrix[1][column]
                    + next.matrix[row][2] * self.matrix[2][column];
                if column == 3 {
                    *entry += next.matrix[row][3];
                }
            }
        }
        matrix[3][3] = 1.0;
        if !matrix.iter().flatten().all(|entry| entry.is_finite()) {
            return Err(SpatialError::NonFinite);
        }
        Ok(Transform::from_matrix(matrix))
    }

    /// Apply only the linear part to a vector, without adding translation.
    ///
    /// Checks only participating values: the vector and linear 3x3 matrix.
    /// Translation and bottom row are ignored, even if they contain NaN/Inf.
    /// Finiteness does not establish rigidity or physical frame correctness.
    ///
    /// # Errors
    /// Returns [`SpatialError::NonFinite`] for any non-finite participating input
    /// or computed component, including floating-point overflow.
    #[inline]
    pub fn apply_vector(&self, vector: Vector3<From>) -> Result<Vector3<To>, SpatialError> {
        if ![vector.x, vector.y, vector.z]
            .into_iter()
            .all(f64::is_finite)
            || !self
                .matrix
                .iter()
                .take(3)
                .all(|row| row.iter().take(3).all(|entry| entry.is_finite()))
        {
            return Err(SpatialError::NonFinite);
        }
        let matrix = &self.matrix;
        let result = Vector3::new(
            matrix[0][0] * vector.x + matrix[0][1] * vector.y + matrix[0][2] * vector.z,
            matrix[1][0] * vector.x + matrix[1][1] * vector.y + matrix[1][2] * vector.z,
            matrix[2][0] * vector.x + matrix[2][1] * vector.y + matrix[2][2] * vector.z,
        );
        if ![result.x, result.y, result.z]
            .into_iter()
            .all(f64::is_finite)
        {
            return Err(SpatialError::NonFinite);
        }
        Ok(result)
    }

    /// Validate and invert an approximately rigid affine transform.
    ///
    /// Checks all entries are finite, the bottom row is `[0, 0, 0, 1]`, rotation
    /// row dot products match the identity, and determinant is +1, each within
    /// absolute tolerance `1e-10`. Computes `R^T` and `-R^T * translation` and
    /// returns a canonical affine bottom row. Near-rigid raw inputs are accepted
    /// within tolerance, so roundtrips are approximate. This is not a general
    /// inverse for scaling, shear, reflection, or projective matrices.
    /// Roundtrip error scales with coordinate/translation magnitude and may
    /// accumulate over long composition chains; no uniform absolute bound is
    /// promised for arbitrary inputs.
    ///
    /// # Errors
    /// Returns [`SpatialError::NonFinite`] for any non-finite input or output
    /// (including overflow in inverse translation), or [`SpatialError::NonRigidTransform`]
    /// if finite input fails the rigidity/affine checks.
    pub fn try_inverse(&self) -> Result<Transform<To, From>, SpatialError> {
        let matrix = &self.matrix;
        if !matrix.iter().flatten().all(|entry| entry.is_finite()) {
            return Err(SpatialError::NonFinite);
        }
        for (column, entry) in matrix[3].iter().enumerate() {
            let expected = if column == 3 { 1.0 } else { 0.0 };
            if (entry - expected).abs() > RIGID_TOLERANCE {
                return Err(SpatialError::NonRigidTransform);
            }
        }
        for (row_index, row) in matrix.iter().take(3).enumerate() {
            for (other_index, other) in matrix.iter().take(3).enumerate() {
                let dot = row[0] * other[0] + row[1] * other[1] + row[2] * other[2];
                let expected = if row_index == other_index { 1.0 } else { 0.0 };
                if !dot.is_finite() || (dot - expected).abs() > RIGID_TOLERANCE {
                    return Err(SpatialError::NonRigidTransform);
                }
            }
        }
        let determinant = matrix[0][0]
            * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
            - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
            + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0]);
        if (determinant - 1.0).abs() > RIGID_TOLERANCE {
            return Err(SpatialError::NonRigidTransform);
        }
        let mut inverse = [[0.0; 4]; 4];
        for (row, output) in inverse.iter_mut().take(3).enumerate() {
            for (column, entry) in output.iter_mut().take(3).enumerate() {
                *entry = matrix[column][row];
            }
            output[3] =
                -(output[0] * matrix[0][3] + output[1] * matrix[1][3] + output[2] * matrix[2][3]);
        }
        inverse[3][3] = 1.0;
        if !inverse.iter().flatten().all(|entry| entry.is_finite()) {
            return Err(SpatialError::NonFinite);
        }
        Ok(Transform::from_matrix(inverse))
    }

    /// Apply this transform to a point in the `From` frame, producing a point
    /// in the `To` frame.
    ///
    /// Multiplies the first three matrix rows by the column vector `[x, y, z, 1]`.
    /// The bottom row is not read and no perspective division is performed;
    /// callers should supply an affine matrix. Checks the point, first three
    /// matrix rows and output for finiteness, without validating rigidity.
    /// Evaluation order is unchanged; no compensated arithmetic is used.
    ///
    /// # Errors
    /// Returns [`SpatialError::NonFinite`] for a non-finite participating input
    /// or computed component, including floating-point overflow. Ignored bottom
    /// row values are not validated.
    #[inline]
    pub fn apply_point(&self, p: Point3<From>) -> Result<Point3<To>, SpatialError> {
        if ![p.x, p.y, p.z].into_iter().all(f64::is_finite)
            || !self
                .matrix
                .iter()
                .take(3)
                .flatten()
                .all(|entry| entry.is_finite())
        {
            return Err(SpatialError::NonFinite);
        }
        let matrix = &self.matrix;
        let x = p.x;
        let y = p.y;
        let z = p.z;

        let xp = matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * z + matrix[0][3];
        let yp = matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * z + matrix[1][3];
        let zp = matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * z + matrix[2][3];

        if ![xp, yp, zp].into_iter().all(f64::is_finite) {
            return Err(SpatialError::NonFinite);
        }
        Ok(Point3::<To>::new(xp, yp, zp))
    }
}

impl<From: Frame, To: Frame> Copy for Transform<From, To> {}

impl<From: Frame, To: Frame> Clone for Transform<From, To> {
    fn clone(&self) -> Self {
        *self
    }
}

impl<From: Frame, To: Frame> core::fmt::Debug for Transform<From, To> {
    fn fmt(&self, formatter: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        formatter
            .debug_struct("Transform")
            .field("matrix", &self.matrix)
            .field("_from", &self._from)
            .field("_to", &self._to)
            .finish()
    }
}

impl<From: Frame, To: Frame> PartialEq for Transform<From, To> {
    fn eq(&self, other: &Self) -> bool {
        self.matrix == other.matrix
    }
}
