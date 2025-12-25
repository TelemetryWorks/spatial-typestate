//! Tests for basic transform invariants.
//!
//! Focus here is on simple but meaningful properties rather than exhaustive
//! property-based tests (those can live in separate files).

use spatial_typestate::{spatial_frames, Frame, Point3, Transform};

spatial_frames! {
    World,
    Body,
}

fn approx_eq(a: f64, b: f64, eps: f64) -> bool {
    (a - b).abs() <= eps
}

#[test]
fn identity_is_left_and_right_neutral_for_points() {
    let p: Point3<World> = Point3::new(3.0, -1.0, 2.5);

    let id: Transform<World, World> = Transform::identity();
    let result = id.apply_point(p);

    assert!(approx_eq(result.x, p.x, 1e-12));
    assert!(approx_eq(result.y, p.y, 1e-12));
    assert!(approx_eq(result.z, p.z, 1e-12));
}

#[test]
fn simple_translation_on_point() {
    let t_translate: Transform<World, World> = Transform::from_translation(10.0, 0.0, 0.0);

    let p: Point3<World> = Point3::new(1.0, 2.0, 3.0);
    let q = t_translate.apply_point(p);

    assert!(approx_eq(q.x, 11.0, 1e-12));
    assert!(approx_eq(q.y, 2.0, 1e-12));
    assert!(approx_eq(q.z, 3.0, 1e-12));
}
