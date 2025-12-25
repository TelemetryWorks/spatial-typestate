//! Property-based tests for transform behavior using proptest.
//!
//! We focus on simple, composable properties that should always hold:
//! - Identity preserves any point.
//! - A pure translation adds its offset for any point.

use proptest::prelude::*;
use spatial_typestate::{spatial_frames, Frame, Point3, Transform};

spatial_frames! {
    World,
}

fn approx_eq(a: f64, b: f64, eps: f64) -> bool {
    (a - b).abs() <= eps
}

proptest! {
    #[test]
    fn identity_preserves_random_world_points(x in -1e6_f64..1e6_f64,
                                              y in -1e6_f64..1e6_f64,
                                              z in -1e6_f64..1e6_f64) {
        let p: Point3<World> = Point3::new(x, y, z);
        let id: Transform<World, World> = Transform::identity();
        let q = id.apply_point(p);

        prop_assert!(approx_eq(q.x, x, 1e-9));
        prop_assert!(approx_eq(q.y, y, 1e-9));
        prop_assert!(approx_eq(q.z, z, 1e-9));
    }

    #[test]
    fn translation_adds_offset_for_random_points(
        x in -1e3_f64..1e3_f64,
        y in -1e3_f64..1e3_f64,
        z in -1e3_f64..1e3_f64,
        tx in -1e3_f64..1e3_f64,
        ty in -1e3_f64..1e3_f64,
        tz in -1e3_f64..1e3_f64,
    ) {
        let p: Point3<World> = Point3::new(x, y, z);
        let t: Transform<World, World> = Transform::from_translation(tx, ty, tz);

        let q = t.apply_point(p);

        prop_assert!(approx_eq(q.x, x + tx, 1e-9));
        prop_assert!(approx_eq(q.y, y + ty, 1e-9));
        prop_assert!(approx_eq(q.z, z + tz, 1e-9));
    }
}
