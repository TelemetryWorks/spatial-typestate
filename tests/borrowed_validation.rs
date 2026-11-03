//! Contract evidence for an isolated prototype, not a production API.
#![deny(unsafe_code)]
#[path = "../benches/support/borrowed.rs"]
mod borrowed;
use borrowed::{BorrowedPoint, BorrowedVector, caller_local_points, caller_local_vectors};
use proptest::prelude::*;
use spatial_typestate::{
    Dimensionless, Frame, Meters, Point3, SpatialError, Transform, Unit, Vector3,
};
struct From;
struct To;
impl Frame for From {}
impl Frame for To {}
struct Velocity;
impl Unit for Velocity {}

fn point_equal(
    a: Result<Point3<To, Meters>, SpatialError>,
    b: Result<Point3<To, Meters>, SpatialError>,
) {
    match (a, b) {
        (Ok(a), Ok(b)) => assert_eq!(
            [a.x, a.y, a.z].map(f64::to_bits),
            [b.x, b.y, b.z].map(f64::to_bits)
        ),
        (Err(a), Err(b)) => assert_eq!(a, b),
        _ => panic!("point classification differs"),
    }
}
fn vector_equal(
    a: Result<Vector3<To, Velocity>, SpatialError>,
    b: Result<Vector3<To, Velocity>, SpatialError>,
) {
    match (a, b) {
        (Ok(a), Ok(b)) => assert_eq!(
            [a.x, a.y, a.z].map(f64::to_bits),
            [b.x, b.y, b.z].map(f64::to_bits)
        ),
        (Err(a), Err(b)) => assert_eq!(a, b),
        _ => panic!("vector classification differs"),
    }
}
fn compare(map: Transform<From, To, Meters>, xyz: [f64; 3]) {
    let p = Point3::new(xyz[0], xyz[1], xyz[2]);
    let v = Vector3::new(xyz[0], xyz[1], xyz[2]);
    let point = BorrowedPoint::prepare(&map).and_then(|b| b.apply_point(p));
    point_equal(map.apply_point(p), point);
    let vector = BorrowedVector::prepare(&map).and_then(|b| b.apply_vector(v));
    vector_equal(map.apply_vector(v), vector);
    let mut ps = [Ok(Point3::new(99.0, 99.0, 99.0))];
    match caller_local_points(&map, &[p], &mut ps) {
        Ok(()) => point_equal(map.apply_point(p), ps[0]),
        Err(e) => point_equal(map.apply_point(p), Err(e)),
    }
    let mut vs = [Ok(Vector3::new(99.0, 99.0, 99.0))];
    match caller_local_vectors(&map, &[v], &mut vs) {
        Ok(()) => vector_equal(map.apply_vector(v), vs[0]),
        Err(e) => vector_equal(map.apply_vector(v), Err(e)),
    }
}

#[test]
fn every_nonfinite_position_and_ignored_scope() {
    for bad in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        for index in 0..16 {
            let mut m = Transform::identity();
            m.matrix[index / 4][index % 4] = bad;
            compare(m, [1.0, 2.0, 3.0]);
        }
        for axis in 0..3 {
            let mut p = [1.0; 3];
            p[axis] = bad;
            compare(Transform::identity(), p);
        }
        let mut m = Transform::<From, To, Meters>::identity();
        m.matrix[0][3] = bad;
        m.matrix[3] = [bad; 4];
        assert!(matches!(
            BorrowedPoint::prepare(&m),
            Err(SpatialError::NonFinite)
        ));
        let v: Vector3<To, Dimensionless> = BorrowedVector::prepare(&m)
            .unwrap()
            .apply_vector(Vector3::<From, Dimensionless>::new(1.0, 2.0, 3.0))
            .unwrap();
        assert_eq!(
            [v.x, v.y, v.z].map(f64::to_bits),
            [1.0_f64, 2.0, 3.0].map(f64::to_bits)
        );
    }
}
#[test]
fn raw_nonrigid_zero_bits_extremes_and_overflow() {
    for value in [
        0.0,
        -0.0,
        f64::from_bits(1),
        -f64::from_bits(1),
        f64::MIN_POSITIVE,
        f64::MAX,
        -f64::MAX,
    ] {
        compare(Transform::identity(), [value, -value, value]);
        compare(
            Transform::from_translation(value, -value, value),
            [value, value, -value],
        );
    }
    let mut m = Transform::identity();
    m.matrix[0][0] = 2.0;
    m.matrix[1][0] = 0.25;
    assert!(BorrowedPoint::prepare(&m).is_ok());
    assert!(BorrowedVector::prepare(&m).is_ok());
    compare(m, [f64::MAX, 1.0, -0.0]);
}
#[test]
fn batch_fixture_keeps_per_element_results_and_prep_failure_writes_nothing() {
    let m = Transform::<From, To, Meters>::identity();
    let points = [
        Point3::new(1.0, 2.0, 3.0),
        Point3::new(f64::NAN, 1.0, 2.0),
        Point3::new(-0.0, 0.0, 1.0),
    ];
    let mut output = [Err(SpatialError::NonRigidTransform); 3];
    caller_local_points(&m, &points, &mut output).unwrap();
    for (input, output) in points.into_iter().zip(output) {
        point_equal(m.apply_point(input), output);
    }
    let vectors = points.map(|p| Vector3::<From, Velocity>::new(p.x, p.y, p.z));
    let mut vector_output = [Err(SpatialError::NonRigidTransform); 3];
    caller_local_vectors(&m, &vectors, &mut vector_output).unwrap();
    for (input, output) in vectors.into_iter().zip(vector_output) {
        vector_equal(m.apply_vector(input), output);
    }
    let mut bad = m;
    bad.matrix[0][0] = f64::NAN;
    let mut output = [Err(SpatialError::NonRigidTransform); 3];
    assert_eq!(
        caller_local_points(&bad, &points, &mut output),
        Err(SpatialError::NonFinite)
    );
    assert!(
        output
            .into_iter()
            .all(|v| matches!(v, Err(SpatialError::NonRigidTransform)))
    );
    let empty: [Point3<From, Meters>; 0] = [];
    let mut empty_out = [];
    assert_eq!(
        caller_local_points(&bad, &empty, &mut empty_out),
        Err(SpatialError::NonFinite)
    );
}

#[test]
#[should_panic(expected = "assertion `left == right` failed")]
fn fixture_length_mismatch_is_an_explicit_precondition_not_silent_zip() {
    let m = Transform::<From, To, Meters>::identity();
    let inputs = [Point3::new(1.0, 2.0, 3.0)];
    let mut outputs = [];
    let _ = caller_local_points(&m, &inputs, &mut outputs);
}
#[test]
fn borrow_ends_after_last_use_and_updates_require_repreparation() {
    let mut m = Transform::<From, To, Meters>::identity();
    let b = BorrowedPoint::prepare(&m).unwrap();
    assert!(b.apply_point(Point3::new(1.0, 2.0, 3.0)).is_ok());
    m.matrix[0][0] = f64::NAN;
    assert!(matches!(
        BorrowedPoint::prepare(&m),
        Err(SpatialError::NonFinite)
    ));
}
proptest! {
    #![proptest_config(ProptestConfig {cases:4096,failure_persistence:Some(Box::new(proptest::test_runner::FileFailurePersistence::Direct("tests/borrowed_validation.proptest-regressions"))),..ProptestConfig::default()})]
    #[test]
    fn all_bit_patterns_match_reference(matrix in any::<[[u64;4];4]>(),xyz in any::<[u64;3]>()) {
        compare(Transform::from_matrix(matrix.map(|r|r.map(f64::from_bits))),xyz.map(f64::from_bits));
    }
}
