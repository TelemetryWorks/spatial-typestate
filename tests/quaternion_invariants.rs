//! Tests for UnitQuat invariants.

use spatial_typestate::{spatial_frames, Frame, SpatialError, UnitQuat};

spatial_frames! {
    World,
}

fn approx_eq(a: f64, b: f64, eps: f64) -> bool {
    (a - b).abs() <= eps
}

#[test]
fn identity_quaternion_is_unit_length() {
    let q: UnitQuat<World> = UnitQuat::identity();

    let norm_sq = q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w;
    assert!(approx_eq(norm_sq, 1.0, 1e-12));
}

#[test]
fn try_from_components_normalizes_quaternion() {
    // 2 * identity quaternion, not unit length yet.
    let q = UnitQuat::<World>::try_from_components(0.0, 0.0, 0.0, 2.0).unwrap();

    let norm_sq = q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w;
    assert!(approx_eq(norm_sq, 1.0, 1e-12));
    assert!(approx_eq(q.w, 1.0, 1e-12)); // normalized
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
