//! Isolated hypotheses, not public library APIs or approved replacements.
use spatial_typestate::{Frame, LengthUnit, Point3, SpatialError, Transform};

/// Bench-only owned immutable validation boundary. Not a proposed public API.
pub struct Prepared<F: Frame, T: Frame, L: LengthUnit> {
    map: Transform<F, T, L>,
}
impl<F: Frame, T: Frame, L: LengthUnit> Prepared<F, T, L> {
    pub fn new(map: Transform<F, T, L>) -> Result<Self, SpatialError> {
        if !map.matrix.iter().take(3).flatten().all(|v| v.is_finite()) {
            return Err(SpatialError::NonFinite);
        }
        Ok(Self { map })
    }
    pub fn apply(&self, point: Point3<F, L>) -> Result<Point3<T, L>, SpatialError> {
        if ![point.x, point.y, point.z].into_iter().all(f64::is_finite) {
            return Err(SpatialError::NonFinite);
        }
        let m = &self.map.matrix;
        let (x, y, z) = (point.x, point.y, point.z);
        let out = Point3::new(
            m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3],
            m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3],
            m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3],
        );
        if ![out.x, out.y, out.z].into_iter().all(f64::is_finite) {
            return Err(SpatialError::NonFinite);
        }
        Ok(out)
    }
}

/// Eager boolean reduction may let the compiler pack independent finite checks.
pub fn point_eager<F: Frame, T: Frame, L: LengthUnit>(
    map: &Transform<F, T, L>,
    point: Point3<F, L>,
) -> Result<Point3<T, L>, SpatialError> {
    let inputs_finite = [point.x, point.y, point.z]
        .into_iter()
        .fold(true, |finite, value| finite & value.is_finite())
        & map
            .matrix
            .iter()
            .take(3)
            .flatten()
            .fold(true, |finite, value| finite & value.is_finite());
    if !inputs_finite {
        return Err(SpatialError::NonFinite);
    }
    let m = &map.matrix;
    let (x, y, z) = (point.x, point.y, point.z);
    let result = Point3::new(
        m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3],
        m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3],
        m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3],
    );
    if ![result.x, result.y, result.z]
        .into_iter()
        .fold(true, |finite, value| finite & value.is_finite())
    {
        return Err(SpatialError::NonFinite);
    }
    Ok(result)
}

/// Fuse each row's validation, unchanged arithmetic, and output check.
pub fn point_rows<F: Frame, T: Frame, L: LengthUnit>(
    map: &Transform<F, T, L>,
    point: Point3<F, L>,
) -> Result<Point3<T, L>, SpatialError> {
    if ![point.x, point.y, point.z].into_iter().all(f64::is_finite) {
        return Err(SpatialError::NonFinite);
    }
    let mut out = [0.0; 3];
    for (row, output) in map.matrix.iter().take(3).zip(&mut out) {
        if !row.iter().all(|value| value.is_finite()) {
            return Err(SpatialError::NonFinite);
        }
        *output = row[0] * point.x + row[1] * point.y + row[2] * point.z + row[3];
        if !output.is_finite() {
            return Err(SpatialError::NonFinite);
        }
    }
    Ok(Point3::new(out[0], out[1], out[2]))
}

/// Full quaternion replay for comparing step counts, never a public bypass.
/// The library's documented eight-step no-std implementation remains unchanged.
pub fn normalize_steps<const STEPS: usize>(input: [f64; 4]) -> Result<[f64; 4], SpatialError> {
    let [x, y, z, w] = input;
    if !input.into_iter().all(f64::is_finite) {
        return Err(SpatialError::NonFinite);
    }
    let scale = x.abs().max(y.abs()).max(z.abs()).max(w.abs());
    if scale == 0.0 {
        return Err(SpatialError::ZeroNormQuaternion);
    }
    let (x, y, z, w) = (x / scale, y / scale, z / scale, w / scale);
    let squared = x * x + y * y + z * z + w * w;
    let norm = sqrt_steps::<STEPS>(squared);
    Ok([x / norm, y / norm, z / norm, w / norm])
}

/// Bounded [1,4] experimental norm helper; no claim of correct rounding.
pub fn sqrt_steps<const STEPS: usize>(value: f64) -> f64 {
    debug_assert!((1.0..=4.0).contains(&value));
    let mut estimate = 2.0;
    for _ in 0..STEPS {
        estimate -= 0.5 * (estimate - value / estimate);
    }
    estimate
}

// Control: unchanged validation and arithmetic copied from public apply_point.
// Only function signature/receiver naming and inlining hints differ.
#[inline]
pub fn point_local<F: Frame, To: Frame, L: LengthUnit>(
    map: &Transform<F, To, L>,
    p: Point3<F, L>,
) -> Result<Point3<To, L>, SpatialError> {
    if ![p.x, p.y, p.z].into_iter().all(f64::is_finite)
        || !map
            .matrix
            .iter()
            .take(3)
            .flatten()
            .all(|entry| entry.is_finite())
    {
        return Err(SpatialError::NonFinite);
    }
    let matrix = &map.matrix;
    let x = p.x;
    let y = p.y;
    let z = p.z;

    let xp = matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * z + matrix[0][3];
    let yp = matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * z + matrix[1][3];
    let zp = matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * z + matrix[2][3];

    if ![xp, yp, zp].into_iter().all(f64::is_finite) {
        return Err(SpatialError::NonFinite);
    }
    Ok(Point3::<To, L>::new(xp, yp, zp))
}

// Forces only the control's inlining; never changes production attributes.
#[inline(always)]
pub fn point_forced<F: Frame, To: Frame, L: LengthUnit>(
    map: &Transform<F, To, L>,
    p: Point3<F, L>,
) -> Result<Point3<To, L>, SpatialError> {
    if ![p.x, p.y, p.z].into_iter().all(f64::is_finite)
        || !map
            .matrix
            .iter()
            .take(3)
            .flatten()
            .all(|entry| entry.is_finite())
    {
        return Err(SpatialError::NonFinite);
    }
    let matrix = &map.matrix;
    let x = p.x;
    let y = p.y;
    let z = p.z;

    let xp = matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * z + matrix[0][3];
    let yp = matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * z + matrix[1][3];
    let zp = matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * z + matrix[2][3];

    if ![xp, yp, zp].into_iter().all(f64::is_finite) {
        return Err(SpatialError::NonFinite);
    }
    Ok(Point3::<To, L>::new(xp, yp, zp))
}
