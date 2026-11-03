//! Finite arithmetic is the default contract for transform operations.
use proptest::prelude::*;
use spatial_typestate::{Frame, Meters, Point3, SpatialError, Transform, Vector3};

struct Sensor;
struct Aircraft;
struct World;
impl Frame for Sensor {}
impl Frame for Aircraft {}
impl Frame for World {}

#[test]
fn point_overflow_returns_an_error() {
    let transform = Transform::<Sensor, World, Meters>::from_translation(f64::MAX, 0.0, 0.0);
    assert!(matches!(
        transform.apply_point(Point3::<_, Meters>::new(f64::MAX, 0.0, 0.0)),
        Err(SpatialError::NonFinite)
    ));
}

#[test]
fn vector_overflow_returns_an_error() {
    let mut transform = Transform::<Sensor, World, Meters>::identity();
    transform.matrix[0][0] = 2.0;
    assert!(matches!(
        transform.apply_vector(Vector3::<_, Meters>::new(f64::MAX, 0.0, 0.0)),
        Err(SpatialError::NonFinite)
    ));
}

#[test]
fn composition_overflow_returns_an_error() {
    let first = Transform::<Sensor, Aircraft, Meters>::from_translation(f64::MAX, 0.0, 0.0);
    let next = Transform::<Aircraft, World, Meters>::from_translation(f64::MAX, 0.0, 0.0);
    assert!(matches!(first.then(next), Err(SpatialError::NonFinite)));
    let mut first = Transform::<Sensor, Aircraft, Meters>::identity();
    first.matrix[0][0] = f64::MAX;
    let mut next = Transform::<Aircraft, World, Meters>::identity();
    next.matrix[0][0] = 2.0;
    assert!(matches!(first.then(next), Err(SpatialError::NonFinite)));
}

#[test]
fn point_rejects_every_non_finite_participating_input() {
    for invalid in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        for axis in 0..3 {
            let mut point = [0.0; 3];
            point[axis] = invalid;
            assert!(matches!(
                Transform::<Sensor, World, Meters>::identity()
                    .apply_point(Point3::<_, Meters>::new(point[0], point[1], point[2])),
                Err(SpatialError::NonFinite)
            ));
        }
        for index in 0..12 {
            let mut transform = Transform::<Sensor, World, Meters>::identity();
            transform.matrix[index / 4][index % 4] = invalid;
            assert!(matches!(
                transform.apply_point(Point3::<_, Meters>::new(1.0, 2.0, 3.0)),
                Err(SpatialError::NonFinite)
            ));
        }
    }
}

#[test]
fn vector_rejects_every_non_finite_participating_input() {
    for invalid in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        for axis in 0..3 {
            let mut vector = [0.0; 3];
            vector[axis] = invalid;
            assert!(matches!(
                Transform::<Sensor, World, Meters>::identity()
                    .apply_vector(Vector3::<_, Meters>::new(vector[0], vector[1], vector[2])),
                Err(SpatialError::NonFinite)
            ));
        }
        for index in 0..9 {
            let mut transform = Transform::<Sensor, World, Meters>::identity();
            transform.matrix[index / 3][index % 3] = invalid;
            assert!(matches!(
                transform.apply_vector(Vector3::<_, Meters>::new(1.0, 2.0, 3.0)),
                Err(SpatialError::NonFinite)
            ));
        }
    }
}

#[test]
fn composition_rejects_every_non_finite_participating_entry() {
    for invalid in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        for index in 0..12 {
            let mut first = Transform::<Sensor, Aircraft, Meters>::identity();
            first.matrix[index / 4][index % 4] = invalid;
            assert!(matches!(
                first.then(Transform::<Aircraft, World, Meters>::identity()),
                Err(SpatialError::NonFinite)
            ));
            let mut next = Transform::<Aircraft, World, Meters>::identity();
            next.matrix[index / 4][index % 4] = invalid;
            assert!(matches!(
                Transform::<Sensor, Aircraft, Meters>::identity().then(next),
                Err(SpatialError::NonFinite)
            ));
        }
    }
}

#[test]
fn ignored_entries_do_not_become_new_validation_inputs() {
    let mut first = Transform::<Sensor, Aircraft, Meters>::from_translation(1.0, 2.0, 3.0);
    first.matrix[3] = [f64::NAN, f64::INFINITY, f64::NEG_INFINITY, 0.0];
    assert_eq!(
        first
            .apply_point(Point3::<_, Meters>::new(2.0, 3.0, 4.0))
            .unwrap(),
        Point3::<Aircraft, Meters>::new(3.0, 5.0, 7.0)
    );
    let mut next = Transform::<Aircraft, World, Meters>::identity();
    next.matrix[3] = [f64::INFINITY, f64::NAN, 3.0, -1.0];
    let composed = first.then(next).unwrap();
    assert_eq!(composed.matrix[3], [0.0, 0.0, 0.0, 1.0]);
    for invalid in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        first.matrix[0][3] = invalid;
        first.matrix[1][3] = invalid;
        first.matrix[2][3] = invalid;
        assert_eq!(
            first
                .apply_vector(Vector3::<_, Meters>::new(2.0, 3.0, 4.0))
                .unwrap(),
            Vector3::<Aircraft, Meters>::new(2.0, 3.0, 4.0)
        );
    }
}

#[test]
fn finite_checks_do_not_require_rigidity() {
    let raw = Transform::<Sensor, World, Meters>::from_matrix([
        [2.0, 1.0, 0.0, 10.0],
        [0.0, 3.0, 0.0, 20.0],
        [0.0, 0.0, -1.0, 30.0],
        [0.0, 0.0, 0.0, 1.0],
    ]);
    assert_eq!(
        raw.apply_point(Point3::<_, Meters>::new(1.0, 2.0, 3.0))
            .unwrap(),
        Point3::<_, Meters>::new(14.0, 26.0, 27.0)
    );
    assert_eq!(
        raw.apply_vector(Vector3::<_, Meters>::new(1.0, 2.0, 3.0))
            .unwrap(),
        Vector3::<_, Meters>::new(4.0, 6.0, -3.0)
    );
    assert!(
        raw.then(Transform::<World, World, Meters>::identity())
            .is_ok()
    );
    assert!(matches!(
        raw.try_inverse(),
        Err(SpatialError::NonRigidTransform)
    ));
}

#[test]
fn finite_extremes_subnormals_and_signed_zeros_keep_evaluation_order() {
    for input in [
        [f64::MAX, -f64::MAX, f64::from_bits(1)],
        [-0.0, 0.0, -f64::MIN_POSITIVE],
    ] {
        let transform =
            Transform::<Sensor, World, Meters>::from_translation(-input[0], -input[1], 0.0);
        let result = transform
            .apply_point(Point3::<_, Meters>::new(input[0], input[1], input[2]))
            .unwrap();
        let expected = [
            input[0] + 0.0 * input[1] + 0.0 * input[2] - input[0],
            0.0 * input[0] + input[1] + 0.0 * input[2] - input[1],
            0.0 * input[0] + 0.0 * input[1] + input[2] + 0.0,
        ];
        for (actual, expected) in [result.x, result.y, result.z].into_iter().zip(expected) {
            assert_eq!(actual.to_bits(), expected.to_bits());
        }
    }
}

#[test]
fn intermediate_overflow_is_an_error_despite_real_number_cancellation() {
    let raw = Transform::<Sensor, World, Meters>::from_matrix([
        [2.0, -2.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]);
    assert!(matches!(
        raw.apply_point(Point3::<_, Meters>::new(f64::MAX, f64::MAX, 0.0)),
        Err(SpatialError::NonFinite)
    ));
    assert!(matches!(
        raw.apply_vector(Vector3::<_, Meters>::new(f64::MAX, f64::MAX, 0.0)),
        Err(SpatialError::NonFinite)
    ));
}

#[test]
fn sequential_and_composed_operations_check_different_intermediates() {
    let first = Transform::<Sensor, Aircraft, Meters>::from_translation(f64::MAX, 0.0, 0.0);
    let next = Transform::<Aircraft, World, Meters>::from_translation(-f64::MAX, 0.0, 0.0);
    let point = Point3::<Sensor, Meters>::new(f64::MAX, 0.0, 0.0);
    assert!(matches!(
        first.apply_point(point),
        Err(SpatialError::NonFinite)
    ));
    let composed = first.then(next).unwrap();
    assert_eq!(composed.apply_point(point).unwrap().x, f64::MAX);
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(1024))]
    #[test]
    fn finite_bit_patterns_obey_point_vector_and_composition_contract(
        input in any::<[u64; 27]>().prop_map(|bits| bits.map(f64::from_bits))
            .prop_filter("finite affine inputs", |values| values.iter().all(|value| value.is_finite()))
    ) {
        let first_matrix: [[f64;4];4] = core::array::from_fn(|row| core::array::from_fn(|column| if row < 3 { input[row*4+column] } else if column == 3 { 1.0 } else { 0.0 }));
        let next_matrix: [[f64;4];4] = core::array::from_fn(|row| core::array::from_fn(|column| if row < 3 { input[12+row*4+column] } else if column == 3 { 1.0 } else { 0.0 }));
        let first = Transform::<Sensor, Aircraft, Meters>::from_matrix(first_matrix);
        let next = Transform::<Aircraft, World, Meters>::from_matrix(next_matrix);
        let point = [input[24], input[25], input[26]];
        let linear: [f64;3] = core::array::from_fn(|row| first_matrix[row][0]*point[0] + first_matrix[row][1]*point[1] + first_matrix[row][2]*point[2]);
        let expected_point: [f64;3] = core::array::from_fn(|row| linear[row]+first_matrix[row][3]);
        let actual_point = first.apply_point(Point3::<_, Meters>::new(point[0], point[1], point[2]));
        if expected_point.into_iter().all(f64::is_finite) {
            let actual = actual_point.unwrap();
            prop_assert_eq!([actual.x,actual.y,actual.z].map(f64::to_bits), expected_point.map(f64::to_bits));
        } else { prop_assert!(matches!(actual_point, Err(SpatialError::NonFinite))); }
        let actual_vector = first.apply_vector(Vector3::<_, Meters>::new(point[0],point[1],point[2]));
        if linear.into_iter().all(f64::is_finite) {
            let actual = actual_vector.unwrap();
            prop_assert_eq!([actual.x,actual.y,actual.z].map(f64::to_bits), linear.map(f64::to_bits));
        } else { prop_assert!(matches!(actual_vector, Err(SpatialError::NonFinite))); }
        let expected_matrix: [[f64;4];3] = core::array::from_fn(|row| core::array::from_fn(|column| {
            let linear = next_matrix[row][0]*first_matrix[0][column] + next_matrix[row][1]*first_matrix[1][column] + next_matrix[row][2]*first_matrix[2][column];
            if column == 3 { linear+next_matrix[row][3] } else { linear }
        }));
        let composed = first.then(next);
        if expected_matrix.iter().flatten().all(|entry| entry.is_finite()) {
            let actual = composed.unwrap();
            for (row,expected) in expected_matrix.iter().enumerate() { prop_assert_eq!(actual.matrix[row].map(f64::to_bits), expected.map(f64::to_bits)); }
        } else { prop_assert!(matches!(composed, Err(SpatialError::NonFinite))); }
    }
}
