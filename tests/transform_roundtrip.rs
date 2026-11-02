//! Tests for basic transform invariants.
//!
//! Focus here is on simple but meaningful properties rather than exhaustive
//! property-based tests (those can live in separate files).

use spatial_typestate::{Point3, Transform, spatial_frames};

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

#[test]
fn raw_matrix_uses_rows_and_last_column_translation() {
    let transform = Transform::<World, Body>::from_matrix([
        [0.0, -1.0, 0.0, 10.0],
        [1.0, 0.0, 0.0, 20.0],
        [0.0, 0.0, 1.0, 30.0],
        [0.0, 0.0, 0.0, 1.0],
    ]);
    let point = Point3::<World>::new(2.0, 3.0, 4.0);
    let result: Point3<Body> = transform.apply_point(point);
    assert!(approx_eq(result.x, 7.0, f64::EPSILON));
    assert!(approx_eq(result.y, 22.0, f64::EPSILON));
    assert!(approx_eq(result.z, 34.0, f64::EPSILON));

    // Raw inputs are not validated; apply_point ignores the bottom row and
    // performs no projective division, even when that row is not affine.
    let mut raw = transform.matrix;
    raw[3] = [f64::NAN, f64::INFINITY, -2.0, 0.0];
    let unchecked = Transform::<World, Body>::from_matrix(raw).apply_point(point);
    assert!(approx_eq(unchecked.x, result.x, f64::EPSILON));
    assert!(approx_eq(unchecked.y, result.y, f64::EPSILON));
    assert!(approx_eq(unchecked.z, result.z, f64::EPSILON));
}
