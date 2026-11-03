//! Isolated borrowed-validation prototype. Not exported by the library.
#![deny(unsafe_code)]
use spatial_typestate::{Frame, LengthUnit, Point3, SpatialError, Transform, Unit, Vector3};

/// A private shared borrow keeps all twelve validated affine entries immutable.
pub struct BorrowedPoint<'a, F: Frame, T: Frame, L: LengthUnit> {
    map: &'a Transform<F, T, L>,
}
impl<'a, F: Frame, T: Frame, L: LengthUnit> BorrowedPoint<'a, F, T, L> {
    pub fn prepare(map: &'a Transform<F, T, L>) -> Result<Self, SpatialError> {
        if !point_matrix_finite(map) {
            return Err(SpatialError::NonFinite);
        }
        Ok(Self { map })
    }
    pub fn apply_point(&self, point: Point3<F, L>) -> Result<Point3<T, L>, SpatialError> {
        point_checked_value(&self.map.matrix, point)
    }
}

/// A separate scope: translation and bottom row never participate for vectors.
pub struct BorrowedVector<'a, F: Frame, T: Frame, L: LengthUnit> {
    map: &'a Transform<F, T, L>,
}
impl<'a, F: Frame, T: Frame, L: LengthUnit> BorrowedVector<'a, F, T, L> {
    pub fn prepare(map: &'a Transform<F, T, L>) -> Result<Self, SpatialError> {
        if !vector_matrix_finite(map) {
            return Err(SpatialError::NonFinite);
        }
        Ok(Self { map })
    }
    pub fn apply_vector<U: Unit>(
        &self,
        vector: Vector3<F, U>,
    ) -> Result<Vector3<T, U>, SpatialError> {
        vector_checked_value(&self.map.matrix, vector)
    }
}

fn point_matrix_finite<F: Frame, T: Frame, L: LengthUnit>(map: &Transform<F, T, L>) -> bool {
    map.matrix.iter().take(3).flatten().all(|v| v.is_finite())
}
fn vector_matrix_finite<F: Frame, T: Frame, L: LengthUnit>(map: &Transform<F, T, L>) -> bool {
    map.matrix
        .iter()
        .take(3)
        .all(|row| row.iter().take(3).all(|v| v.is_finite()))
}

// Private: callers must establish matrix validation in this module. Never an
// externally callable unchecked mapping, even in this experimental module.
#[inline]
fn point_checked_value<F: Frame, T: Frame, L: LengthUnit>(
    m: &[[f64; 4]; 4],
    p: Point3<F, L>,
) -> Result<Point3<T, L>, SpatialError> {
    if ![p.x, p.y, p.z].into_iter().all(f64::is_finite) {
        return Err(SpatialError::NonFinite);
    }
    let (x, y, z) = (p.x, p.y, p.z);
    let xp = m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3];
    let yp = m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3];
    let zp = m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3];
    if ![xp, yp, zp].into_iter().all(f64::is_finite) {
        return Err(SpatialError::NonFinite);
    }
    Ok(Point3::new(xp, yp, zp))
}
#[inline]
fn vector_checked_value<F: Frame, T: Frame, U: Unit>(
    m: &[[f64; 4]; 4],
    v: Vector3<F, U>,
) -> Result<Vector3<T, U>, SpatialError> {
    if ![v.x, v.y, v.z].into_iter().all(f64::is_finite) {
        return Err(SpatialError::NonFinite);
    }
    let out = Vector3::new(
        m[0][0] * v.x + m[0][1] * v.y + m[0][2] * v.z,
        m[1][0] * v.x + m[1][1] * v.y + m[1][2] * v.z,
        m[2][0] * v.x + m[2][1] * v.y + m[2][2] * v.z,
    );
    if ![out.x, out.y, out.z].into_iter().all(f64::is_finite) {
        return Err(SpatialError::NonFinite);
    }
    Ok(out)
}

/// Matched caller-local hoisting, without constructing a prepared value.
/// Experiment-only fixture protocol: equal lengths or panic; bad matrix returns
/// before any writes; valid matrix writes one Result per input, including errors.
/// This does not select a public batch API contract.
pub fn caller_local_points<F: Frame, T: Frame, L: LengthUnit>(
    map: &Transform<F, T, L>,
    inputs: &[Point3<F, L>],
    outputs: &mut [Result<Point3<T, L>, SpatialError>],
) -> Result<(), SpatialError> {
    assert_eq!(inputs.len(), outputs.len());
    if !point_matrix_finite(map) {
        return Err(SpatialError::NonFinite);
    }
    for (output, input) in outputs.iter_mut().zip(inputs) {
        *output = point_checked_value(&map.matrix, *input);
    }
    Ok(())
}
/// Vector counterpart with only the nine used coefficients validated once.
pub fn caller_local_vectors<F: Frame, T: Frame, L: LengthUnit, U: Unit>(
    map: &Transform<F, T, L>,
    inputs: &[Vector3<F, U>],
    outputs: &mut [Result<Vector3<T, U>, SpatialError>],
) -> Result<(), SpatialError> {
    assert_eq!(inputs.len(), outputs.len());
    if !vector_matrix_finite(map) {
        return Err(SpatialError::NonFinite);
    }
    for (output, input) in outputs.iter_mut().zip(inputs) {
        *output = vector_checked_value(&map.matrix, *input);
    }
    Ok(())
}
