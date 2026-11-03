//! Analytic oracles and bounded properties for requirements ST-001..ST-010.
use proptest::prelude::*;
use spatial_typestate::{Frame, Point3, SpatialError, Transform, UnitQuat, Vector3};

struct Sensor;
struct Aircraft;
struct World;
impl Frame for Sensor {}
impl Frame for Aircraft {}
impl Frame for World {}

fn close(actual: f64, expected: f64) {
    assert!((actual - expected).abs() <= 1e-9, "{actual} != {expected}");
}

#[test]
fn right_handed_active_quarter_turn_oracles() {
    for (components, input, expected) in [
        ([0.0, 0.0, 1.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]),
        ([1.0, 0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]),
        ([0.0, 1.0, 0.0, 1.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0]),
        ([1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, -1.0, 0.0]),
    ] {
        let rotation = UnitQuat::<World>::try_from_components(
            components[0],
            components[1],
            components[2],
            components[3],
        )
        .unwrap();
        let transform = Transform::<Sensor, World>::try_from_rotation_translation(
            rotation,
            Vector3::new(0.0, 0.0, 0.0),
        )
        .unwrap();
        let result = transform
            .apply_point(Point3::new(input[0], input[1], input[2]))
            .unwrap();
        for (actual, expected) in [result.x, result.y, result.z].into_iter().zip(expected) {
            close(actual, expected);
        }
    }
}

#[test]
fn rational_quaternion_has_independent_matrix_oracle() {
    // q=(1,2,2,4)/5. R=[[9,-12,20],[20,15,0],[-12,16,15]]/25.
    let rotation = UnitQuat::<World>::try_from_components(1.0, 2.0, 2.0, 4.0).unwrap();
    let transform = Transform::<Sensor, World>::try_from_rotation_translation(
        rotation,
        Vector3::new(0.0, 0.0, 0.0),
    )
    .unwrap();
    let result = transform.apply_point(Point3::new(1.0, 2.0, 3.0)).unwrap();
    close(result.x, 1.8);
    close(result.y, 2.0);
    close(result.z, 2.6);
}

#[test]
fn sensor_aircraft_world_workflow() {
    let sensor_aircraft = Transform::<Sensor, Aircraft>::try_from_rotation_translation(
        UnitQuat::try_from_components(0.0, 0.0, 1.0, 1.0).unwrap(),
        Vector3::new(1.0, 2.0, 3.0),
    )
    .unwrap();
    let aircraft_world = Transform::<Aircraft, World>::try_from_rotation_translation(
        UnitQuat::try_from_components(1.0, 0.0, 0.0, 1.0).unwrap(),
        Vector3::new(10.0, 20.0, 30.0),
    )
    .unwrap();
    let point = Point3::<Sensor>::new(2.0, 0.0, 1.0);
    let intermediate = sensor_aircraft.apply_point(point).unwrap();
    close(intermediate.x, 1.0);
    close(intermediate.y, 4.0);
    close(intermediate.z, 4.0);
    let sequential = aircraft_world.apply_point(intermediate).unwrap();
    let composed = sensor_aircraft.then(aircraft_world).unwrap();
    let result: Point3<World> = composed.apply_point(point).unwrap();
    for (actual, expected) in [
        (result.x, 11.0),
        (result.y, 16.0),
        (result.z, 34.0),
        (result.x, sequential.x),
        (result.y, sequential.y),
        (result.z, sequential.z),
    ] {
        close(actual, expected);
    }
    let restored = composed.try_inverse().unwrap().apply_point(result).unwrap();
    close(restored.x, point.x);
    close(restored.y, point.y);
    close(restored.z, point.z);
    let vector = composed
        .apply_vector(Vector3::<Sensor>::new(2.0, 0.0, 1.0))
        .unwrap();
    close(vector.x, 0.0);
    close(vector.y, -1.0);
    close(vector.z, 2.0);
}

#[test]
fn composition_order_is_noncommutative() {
    let rx = Transform::<World, World>::try_from_rotation_translation(
        UnitQuat::try_from_components(1.0, 0.0, 0.0, 1.0).unwrap(),
        Vector3::new(0.0, 0.0, 0.0),
    )
    .unwrap();
    let rz = Transform::<World, World>::try_from_rotation_translation(
        UnitQuat::try_from_components(0.0, 0.0, 1.0, 1.0).unwrap(),
        Vector3::new(0.0, 0.0, 0.0),
    )
    .unwrap();
    let point = Point3::new(1.0, 0.0, 0.0);
    let first = rz.then(rx).unwrap().apply_point(point).unwrap();
    let second = rx.then(rz).unwrap().apply_point(point).unwrap();
    close(first.x, 0.0);
    close(first.y, 0.0);
    close(first.z, 1.0);
    close(second.y, 1.0);
    close(second.x, 0.0);
    close(second.z, 0.0);
}

#[test]
fn inverse_accepts_proper_half_turn() {
    let transform = Transform::<Sensor, World>::from_matrix([
        [-1.0, 0.0, 0.0, 1.0],
        [0.0, -1.0, 0.0, 2.0],
        [0.0, 0.0, 1.0, 3.0],
        [0.0, 0.0, 0.0, 1.0],
    ]);
    let point = Point3::new(2.0, 3.0, 4.0);
    assert_eq!(
        transform
            .try_inverse()
            .unwrap()
            .apply_point(transform.apply_point(point).unwrap())
            .unwrap(),
        point
    );
}

#[test]
fn raw_composition_ignores_both_bottom_rows() {
    let mut first = Transform::<Sensor, Aircraft>::from_translation(1.0, 2.0, 3.0);
    let mut next = Transform::<Aircraft, World>::from_matrix([
        [0.0, -1.0, 0.0, 10.0],
        [1.0, 0.0, 0.0, 20.0],
        [0.0, 0.0, 1.0, 30.0],
        [0.0, 0.0, 0.0, 1.0],
    ]);
    first.matrix[3] = [f64::NAN, f64::INFINITY, -7.0, 0.0];
    next.matrix[3] = [2.0, 3.0, 4.0, -5.0];
    let point = Point3::new(2.0, 3.0, 4.0);
    let sequential = next.apply_point(first.apply_point(point).unwrap()).unwrap();
    let composed = first.then(next).unwrap();
    assert_eq!(composed.matrix[3], [0.0, 0.0, 0.0, 1.0]);
    assert_eq!(composed.apply_point(point).unwrap(), sequential);
}

#[test]
fn inverse_rejects_non_rigid_raw_inputs() {
    for matrix in [
        [
            [2.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        [
            [1.0, 0.1, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        [
            [-1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.1, 1.0],
        ],
        [
            [f64::MAX, f64::MAX, 0.0, 0.0],
            [f64::MAX, -f64::MAX, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
    ] {
        assert!(matches!(
            Transform::<Sensor, World>::from_matrix(matrix).try_inverse(),
            Err(SpatialError::NonRigidTransform)
        ));
    }
}

#[test]
fn inverse_rejects_non_finite_input_in_every_entry() {
    for index in 0..16 {
        for invalid in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
            let mut transform = Transform::<Sensor, World>::identity();
            transform.matrix[index / 4][index % 4] = invalid;
            assert!(matches!(
                transform.try_inverse(),
                Err(SpatialError::NonFinite)
            ));
        }
    }
}

#[test]
fn inverse_translation_overflow_is_reported() {
    let transform = Transform::<Sensor, World>::try_from_rotation_translation(
        UnitQuat::try_from_components(0.0, 0.0, 1.0, 2.0).unwrap(),
        Vector3::new(f64::MAX, f64::MAX, 0.0),
    )
    .unwrap();
    assert!(matches!(
        transform.try_inverse(),
        Err(SpatialError::NonFinite)
    ));
}

#[test]
fn rigid_tolerance_is_explicit_and_canonicalized() {
    let mut near = Transform::<Sensor, World>::identity();
    near.matrix[0][0] += 1e-12;
    near.matrix[3][0] = 1e-12;
    assert_eq!(near.try_inverse().unwrap().matrix[3], [0.0, 0.0, 0.0, 1.0]);
    near.matrix[0][0] += 1e-8;
    assert!(matches!(
        near.try_inverse(),
        Err(SpatialError::NonRigidTransform)
    ));
}

#[test]
fn checked_construction_rejects_non_finite_translation() {
    for axis in 0..3 {
        for invalid in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
            let mut input = [0.0; 3];
            input[axis] = invalid;
            assert!(matches!(
                Transform::<Sensor, World>::try_from_rotation_translation(
                    UnitQuat::identity(),
                    Vector3::new(input[0], input[1], input[2])
                ),
                Err(SpatialError::NonFinite)
            ));
        }
    }
    let transform = Transform::<Sensor, World>::from_translation(f64::MAX, 0.0, 0.0);
    assert!(matches!(
        transform.apply_point(Point3::new(f64::MAX, 0.0, 0.0)),
        Err(SpatialError::NonFinite)
    ));
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(1024))]
    #[test]
    fn bounded_rigid_roundtrip_and_composition(
        components in prop::array::uniform4(-10.0_f64..10.0).prop_filter("nonzero quaternion", |values| values.iter().any(|&v| v != 0.0)),
        translation in prop::array::uniform3(-1000.0_f64..1000.0),
        point in prop::array::uniform3(-100.0_f64..100.0)
    ) {
        let rotation = UnitQuat::<Aircraft>::try_from_components(components[0], components[1], components[2], components[3]).unwrap();
        let transform = Transform::<Sensor, Aircraft>::try_from_rotation_translation(rotation, Vector3::new(translation[0], translation[1], translation[2])).unwrap();
        let next = Transform::<Aircraft, World>::try_from_rotation_translation(UnitQuat::try_from_components(0.0,1.0,0.0,1.0).unwrap(), Vector3::new(-3.0, 5.0, 7.0)).unwrap();
        let input = Point3::<Sensor>::new(point[0], point[1], point[2]);
        let combined = transform.then(next).unwrap();
        let output = combined.apply_point(input).unwrap();
        let sequential = next.apply_point(transform.apply_point(input).unwrap()).unwrap();
        let restored = combined.try_inverse().unwrap().apply_point(output).unwrap();
        // Bounded coordinates/translations keep roundoff well below 1e-9;
        // this does not promise that tolerance for unbounded raw inputs.
        for (actual, expected) in [(output.x,sequential.x),(output.y,sequential.y),(output.z,sequential.z),(restored.x,input.x),(restored.y,input.y),(restored.z,input.z)] {
            prop_assert!((actual-expected).abs() <= 1e-9);
        }
    }
}
