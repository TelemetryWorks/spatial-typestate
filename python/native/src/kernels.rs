//! Python-free loops: runtime tags dispatch once, existing checked core does math.
use super::{Kind, Next, Source, Target};
use spatial_typestate::{
    Dimensionless, Feet, LengthUnit, LinearLengthUnit, Meters, Point3, SpatialError, Transform,
    Unit, UnitQuat, Vector3,
};

type Matrix = [[f64; 4]; 4];
type BatchResult = Result<Vec<f64>, (usize, SpatialError)>;

pub(super) fn points(matrix: Matrix, unit: Kind, values: &[f64]) -> BatchResult {
    match unit {
        Kind::Meters => map_points::<Meters>(matrix, values),
        Kind::Feet => map_points::<Feet>(matrix, values),
        Kind::Dimensionless => unreachable!("point length checked at boundary"),
    }
}
fn map_points<L: LengthUnit>(matrix: Matrix, values: &[f64]) -> BatchResult {
    let map = Transform::<Source, Target, L>::from_matrix(matrix);
    let mut out = Vec::with_capacity(values.len());
    for (i, row) in values.chunks_exact(3).enumerate() {
        let p = map
            .apply_point(Point3::new(row[0], row[1], row[2]))
            .map_err(|e| (i, e))?;
        out.extend_from_slice(&[p.x, p.y, p.z]);
    }
    Ok(out)
}
pub(super) fn vectors(matrix: Matrix, unit: Kind, values: &[f64]) -> BatchResult {
    match unit {
        Kind::Meters => map_vectors::<Meters>(matrix, values),
        Kind::Feet => map_vectors::<Feet>(matrix, values),
        Kind::Dimensionless => map_vectors::<Dimensionless>(matrix, values),
    }
}
fn map_vectors<U: Unit>(matrix: Matrix, values: &[f64]) -> BatchResult {
    // Translation length is irrelevant to vector math. Runtime vector U is retained.
    let map = Transform::<Source, Target, Meters>::from_matrix(matrix);
    let mut out = Vec::with_capacity(values.len());
    for (i, row) in values.chunks_exact(3).enumerate() {
        let v = map
            .apply_vector(Vector3::<Source, U>::new(row[0], row[1], row[2]))
            .map_err(|e| (i, e))?;
        out.extend_from_slice(&[v.x, v.y, v.z]);
    }
    Ok(out)
}

pub(super) fn construct(
    unit: Kind,
    q: UnitQuat<Target>,
    t: [f64; 3],
) -> Result<Matrix, SpatialError> {
    match unit {
        Kind::Meters => construct_typed::<Meters>(q, t),
        Kind::Feet => construct_typed::<Feet>(q, t),
        Kind::Dimensionless => unreachable!("length checked"),
    }
}
fn construct_typed<L: LengthUnit>(
    q: UnitQuat<Target>,
    t: [f64; 3],
) -> Result<Matrix, SpatialError> {
    Ok(
        Transform::<Source, Target, L>::try_from_rotation_translation(
            q,
            Vector3::new(t[0], t[1], t[2]),
        )?
        .matrix,
    )
}
pub(super) fn compose(a: Matrix, b: Matrix, unit: Kind) -> Result<Matrix, SpatialError> {
    match unit {
        Kind::Meters => compose_typed::<Meters>(a, b),
        Kind::Feet => compose_typed::<Feet>(a, b),
        Kind::Dimensionless => unreachable!("length checked"),
    }
}
fn compose_typed<L: LengthUnit>(a: Matrix, b: Matrix) -> Result<Matrix, SpatialError> {
    Ok(Transform::<Source, Target, L>::from_matrix(a)
        .then(Transform::<Target, Next, L>::from_matrix(b))?
        .matrix)
}
pub(super) fn inverse(matrix: Matrix, unit: Kind) -> Result<Matrix, SpatialError> {
    match unit {
        Kind::Meters => inverse_typed::<Meters>(matrix),
        Kind::Feet => inverse_typed::<Feet>(matrix),
        Kind::Dimensionless => unreachable!("length checked"),
    }
}
fn inverse_typed<L: LengthUnit>(matrix: Matrix) -> Result<Matrix, SpatialError> {
    Ok(Transform::<Source, Target, L>::from_matrix(matrix)
        .try_inverse()?
        .matrix)
}

pub(super) fn convert(values: &[f64], from: Kind, to: Kind) -> BatchResult {
    match (from, to) {
        (Kind::Meters, Kind::Meters) => convert_values::<Meters, Meters>(values),
        (Kind::Meters, Kind::Feet) => convert_values::<Meters, Feet>(values),
        (Kind::Feet, Kind::Meters) => convert_values::<Feet, Meters>(values),
        (Kind::Feet, Kind::Feet) => convert_values::<Feet, Feet>(values),
        _ => unreachable!("lengths checked"),
    }
}
fn convert_values<F: LinearLengthUnit, T: LinearLengthUnit>(values: &[f64]) -> BatchResult {
    let mut out = Vec::with_capacity(values.len());
    for (i, row) in values.chunks_exact(3).enumerate() {
        let p = Point3::<Source, F>::new(row[0], row[1], row[2])
            .convert_to::<T>()
            .map_err(|e| (i, e))?;
        out.extend_from_slice(&[p.x, p.y, p.z]);
    }
    Ok(out)
}
pub(super) fn convert_transform(
    matrix: Matrix,
    from: Kind,
    to: Kind,
) -> Result<Matrix, SpatialError> {
    match (from, to) {
        (Kind::Meters, Kind::Meters) => convert_map::<Meters, Meters>(matrix),
        (Kind::Meters, Kind::Feet) => convert_map::<Meters, Feet>(matrix),
        (Kind::Feet, Kind::Meters) => convert_map::<Feet, Meters>(matrix),
        (Kind::Feet, Kind::Feet) => convert_map::<Feet, Feet>(matrix),
        _ => unreachable!("lengths checked"),
    }
}
fn convert_map<F: LinearLengthUnit, T: LinearLengthUnit>(
    matrix: Matrix,
) -> Result<Matrix, SpatialError> {
    Ok(Transform::<Source, Target, F>::from_matrix(matrix)
        .convert_to::<T>()?
        .matrix)
}

#[cfg(test)]
mod tests {
    use super::*;
    const ID: Matrix = [
        [1., 0., 0., 0.],
        [0., 1., 0., 0.],
        [0., 0., 1., 0.],
        [0., 0., 0., 1.],
    ];
    fn bits(a: BatchResult, b: BatchResult) {
        match (a, b) {
            (Ok(a), Ok(b)) => assert_eq!(
                a.iter().map(|x| x.to_bits()).collect::<Vec<_>>(),
                b.iter().map(|x| x.to_bits()).collect::<Vec<_>>()
            ),
            (Err(a), Err(b)) => assert_eq!(a, b),
            _ => panic!("different result class"),
        }
    }
    #[test]
    fn sampled_bits_match_checked_core_including_errors() {
        let mut state = 0x9183ab16d2715f03_u64;
        let mut sample = || {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            f64::from_bits(state)
        };
        for _ in 0..4096 {
            let mut matrix = ID;
            for row in &mut matrix {
                for v in row {
                    *v = sample();
                }
            }
            let p = [sample(), sample(), sample()];
            for unit in [Kind::Meters, Kind::Feet] {
                let expected = if unit == Kind::Meters {
                    Transform::<Source, Target, Meters>::from_matrix(matrix)
                        .apply_point(Point3::new(p[0], p[1], p[2]))
                        .map(|p| vec![p.x, p.y, p.z])
                } else {
                    Transform::<Source, Target, Feet>::from_matrix(matrix)
                        .apply_point(Point3::new(p[0], p[1], p[2]))
                        .map(|p| vec![p.x, p.y, p.z])
                };
                bits(points(matrix, unit, &p), expected.map_err(|e| (0, e)));
            }
            let expected = Transform::<Source, Target, Meters>::from_matrix(matrix)
                .apply_vector(Vector3::<Source, Dimensionless>::new(p[0], p[1], p[2]))
                .map(|p| vec![p.x, p.y, p.z]);
            bits(
                vectors(matrix, Kind::Dimensionless, &p),
                expected.map_err(|e| (0, e)),
            );
        }
    }
    #[test]
    fn nonfinite_entries_ignored_scope_and_first_error() {
        for bad in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
            for r in 0..4 {
                for c in 0..4 {
                    let mut m = ID;
                    m[r][c] = bad;
                    assert_eq!(points(m, Kind::Meters, &[1., 2., 3.]).is_err(), r < 3);
                    assert_eq!(
                        vectors(m, Kind::Feet, &[1., 2., 3.]).is_err(),
                        r < 3 && c < 3
                    );
                }
            }
            for axis in 0..3 {
                let mut p = vec![1.; 9];
                p[3 + axis] = bad;
                assert_eq!(
                    points(ID, Kind::Meters, &p),
                    Err((1, SpatialError::NonFinite))
                );
                assert_eq!(
                    vectors(ID, Kind::Feet, &p),
                    Err((1, SpatialError::NonFinite))
                );
            }
        }
        let mut m = ID;
        m[0][0] = f64::MAX;
        assert_eq!(
            points(m, Kind::Meters, &[0., 0., 0., 2., 0., 0.]),
            Err((1, SpatialError::NonFinite))
        );
        m[0][0] = f64::NAN;
        assert_eq!(points(m, Kind::Meters, &[]), Ok(vec![]));
    }
    #[test]
    fn conversion_bits_and_rigid_workflow_delegate_to_core() {
        let values = [
            -0.0,
            f64::from_bits(1),
            f64::MIN_POSITIVE,
            f64::MAX,
            1.,
            -1.,
        ];
        bits(
            convert(&values, Kind::Feet, Kind::Feet),
            Ok(values.to_vec()),
        );
        for &(from, to) in &[(Kind::Feet, Kind::Meters), (Kind::Meters, Kind::Feet)] {
            let expected =
                values
                    .chunks_exact(3)
                    .enumerate()
                    .try_fold(Vec::new(), |mut out, (i, p)| {
                        let v = if from == Kind::Feet {
                            Point3::<Source, Feet>::new(p[0], p[1], p[2])
                                .convert_to::<Meters>()
                                .map(|p| [p.x, p.y, p.z])
                        } else {
                            Point3::<Source, Meters>::new(p[0], p[1], p[2])
                                .convert_to::<Feet>()
                                .map(|p| [p.x, p.y, p.z])
                        };
                        out.extend(v.map_err(|e| (i, e))?);
                        Ok(out)
                    });
            bits(convert(&values, from, to), expected);
        }
        let q = UnitQuat::<Target>::try_from_components(0., 0., 1., 1.).unwrap();
        let expected = Transform::<Source, Target, Feet>::try_from_rotation_translation(
            q,
            Vector3::new(10., 20., 30.),
        )
        .unwrap();
        assert_eq!(
            construct(Kind::Feet, q, [10., 20., 30.]),
            Ok(expected.matrix)
        );
        assert_eq!(
            inverse(expected.matrix, Kind::Feet),
            expected.try_inverse().map(|t| t.matrix)
        );
        assert_eq!(
            convert_transform(expected.matrix, Kind::Feet, Kind::Meters),
            expected.convert_to::<Meters>().map(|t| t.matrix)
        );
        assert_eq!(
            compose(expected.matrix, ID, Kind::Feet),
            expected
                .then(Transform::<Target, Next, Feet>::from_matrix(ID))
                .map(|t| t.matrix)
        );
    }
}
