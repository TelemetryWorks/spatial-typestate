//! Tests for UnitQuat invariants.

use spatial_typestate::{SpatialError, UnitQuat, spatial_frames};

spatial_frames! {
    World,
}

fn approx_eq(a: f64, b: f64, eps: f64) -> bool {
    (a - b).abs() <= eps
}

#[test]
fn identity_quaternion_is_unit_length() {
    const IDENTITY: UnitQuat<World> = UnitQuat::identity();
    const COMPONENTS: [f64; 4] = [IDENTITY.x(), IDENTITY.y(), IDENTITY.z(), IDENTITY.w()];
    let q = IDENTITY;
    assert!(approx_eq(COMPONENTS[0], 0.0, f64::EPSILON));
    assert!(approx_eq(COMPONENTS[1], 0.0, f64::EPSILON));
    assert!(approx_eq(COMPONENTS[2], 0.0, f64::EPSILON));
    assert!(approx_eq(COMPONENTS[3], 1.0, f64::EPSILON));

    let norm_sq = q.x() * q.x() + q.y() * q.y() + q.z() * q.z() + q.w() * q.w();
    assert!(approx_eq(norm_sq, 1.0, 1e-12));
}

#[test]
fn try_from_components_normalizes_quaternion() {
    // 2 * identity quaternion, not unit length yet.
    let q = UnitQuat::<World>::try_from_components(0.0, 0.0, 0.0, 2.0).unwrap();

    let norm_sq = q.x() * q.x() + q.y() * q.y() + q.z() * q.z() + q.w() * q.w();
    assert!(approx_eq(norm_sq, 1.0, 1e-12));
    assert!(approx_eq(q.w(), 1.0, 1e-12)); // normalized
}

#[test]
fn zero_norm_quaternion_is_rejected() {
    let result = UnitQuat::<World>::try_from_components(0.0, 0.0, 0.0, 0.0);
    assert!(matches!(result, Err(SpatialError::ZeroNormQuaternion)));
}

#[test]
fn non_finite_quaternion_is_rejected() {
    let result = UnitQuat::<World>::try_from_components(f64::NAN, 0.0, 0.0, 1.0);
    assert!(matches!(result, Err(SpatialError::NonFinite)));
}

#[test]
fn tiny_nonzero_components_are_not_rejected_as_zero() {
    for magnitude in [f64::MIN_POSITIVE, f64::from_bits(1)] {
        assert!(UnitQuat::<World>::try_from_components(0.0, magnitude, 0.0, 0.0).is_ok());
    }
}

#[test]
fn extreme_finite_components_normalize() {
    let smallest = f64::from_bits(1);
    for magnitude in [f64::MAX, f64::MIN_POSITIVE, smallest] {
        let q =
            UnitQuat::<World>::try_from_components(magnitude, -magnitude, magnitude, -magnitude)
                .expect("every finite nonzero quaternion must normalize");
        for (actual, expected) in [(q.x(), 0.5), (q.y(), -0.5), (q.z(), 0.5), (q.w(), -0.5)] {
            assert!(approx_eq(actual, expected, 32.0 * f64::EPSILON));
        }
    }
}

#[test]
fn each_axis_normalizes_across_the_finite_range() {
    for magnitude in [f64::MAX, f64::MIN_POSITIVE, f64::from_bits(1)] {
        for axis in 0..4 {
            let mut input = [0.0; 4];
            input[axis] = -magnitude;
            let q = UnitQuat::<World>::try_from_components(input[0], input[1], input[2], input[3])
                .unwrap();
            let output = [q.x(), q.y(), q.z(), q.w()];
            for (index, component) in output.into_iter().enumerate() {
                assert!(approx_eq(
                    component,
                    if index == axis { -1.0 } else { 0.0 },
                    f64::EPSILON
                ));
            }
        }
    }
}

#[test]
fn mixed_magnitudes_preserve_dominant_direction() {
    let q = UnitQuat::<World>::try_from_components(
        f64::MAX,
        -f64::MAX,
        f64::MIN_POSITIVE,
        -f64::from_bits(1),
    )
    .unwrap();
    assert!(approx_eq(
        q.x(),
        core::f64::consts::FRAC_1_SQRT_2,
        32.0 * f64::EPSILON
    ));
    assert!(approx_eq(
        q.y(),
        -core::f64::consts::FRAC_1_SQRT_2,
        32.0 * f64::EPSILON
    ));
    assert!([q.x(), q.y(), q.z(), q.w()].into_iter().all(f64::is_finite));
}

#[test]
fn signed_all_zero_inputs_are_rejected() {
    for signs in 0..16 {
        let input: [f64; 4] =
            core::array::from_fn(|axis| if signs & (1 << axis) == 0 { 0.0 } else { -0.0 });
        assert!(matches!(
            UnitQuat::<World>::try_from_components(input[0], input[1], input[2], input[3]),
            Err(SpatialError::ZeroNormQuaternion)
        ));
    }
}

#[test]
fn non_finite_components_in_any_position_are_rejected() {
    for non_finite in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        for axis in 0..4 {
            let mut input = [1.0; 4];
            input[axis] = non_finite;
            assert!(matches!(
                UnitQuat::<World>::try_from_components(input[0], input[1], input[2], input[3]),
                Err(SpatialError::NonFinite)
            ));
        }
    }
}
