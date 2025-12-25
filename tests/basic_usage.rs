//! Basic smoke tests for the spatial-typestate public API.
//!
//! These tests serve two purposes:
//! - Ensure the crate compiles and links as an external dependency.
//! - Exercise the core types: Frame, Point3, Vector3, Transform, Quantity.

use spatial_typestate::{
    spatial_frames, Frame, Meters, Point3, Quantity, Radians, Transform, Vector3,
};

spatial_frames! {
    World,
    Body,
    Sensor,
}

#[test]
fn point_and_vector_construction() {
    let p_world: Point3<World> = Point3::new(1.0, 2.0, 3.0);
    let v_body: Vector3<Body> = Vector3::new(0.0, 1.0, 0.0);

    assert_eq!(p_world.x, 1.0);
    assert_eq!(p_world.y, 2.0);
    assert_eq!(p_world.z, 3.0);

    assert_eq!(v_body.x, 0.0);
    assert_eq!(v_body.y, 1.0);
    assert_eq!(v_body.z, 0.0);
}

#[test]
fn identity_transform_preserves_point() {
    let p_body: Point3<Body> = Point3::new(1.0, 0.0, -2.0);
    let t_body_world: Transform<Body, World> = Transform::identity();

    let p_world = t_body_world.apply_point(p_body);

    // Identity should preserve coordinates exactly.
    assert_eq!(p_world.x, 1.0);
    assert_eq!(p_world.y, 0.0);
    assert_eq!(p_world.z, -2.0);
}

#[test]
fn quantities_add_and_subtract_with_same_unit() {
    let a: Quantity<Meters> = Quantity::new(100.0);
    let b: Quantity<Meters> = Quantity::new(50.0);

    let sum = a + b;
    let diff = a - b;

    assert_eq!(sum.get(), 150.0);
    assert_eq!(diff.get(), 50.0);

    let angle: Quantity<Radians> = Quantity::new(core::f64::consts::FRAC_PI_2);
    assert!(angle.get() > 0.0);
}
