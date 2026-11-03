// This file is intentionally incorrect and should FAIL to compile.
// It is used by trybuild from `tests/type_safety_compile_fail.rs`.

use spatial_typestate::{Meters, spatial_frames, Point3, Transform};

spatial_frames! {
    World,
    Body,
}

fn main() {
    let p_body: Point3<Body, Meters> = Point3::<_, Meters>::new(1.0, 0.0, 0.0);
    let t_world_body: Transform<World, Body, Meters> = Transform::identity();

    // ❌ Intentional type mismatch:
    // `apply_point` expects a Point3<World, Meters> here, but we pass Point3<Body, Meters>.
    let _bad = t_world_body.apply_point(p_body);
    // The compiler should produce a type error, and trybuild asserts that.
}
