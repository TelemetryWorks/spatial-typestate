//! Fuzz compatibility harness.
//!
//! This module defines a simple entry-style function that can be reused from a
//! fuzz target (e.g. `cargo-fuzz`) and a basic test that exercises it once.
//!
//! The idea is to keep the "what should never panic" logic centralized so
//! fuzzing and regular tests share behavior.

use spatial_typestate::{spatial_frames, Frame, Point3, Transform};

spatial_frames! {
    World,
}

/// Entry-style function suitable for fuzzing.
///
/// A fuzz target can feed arbitrary point coordinates and translation offsets
/// into this function and assert that it never panics or produces NaNs.
pub fn fuzz_apply_point_with_translation(x: f64, y: f64, z: f64, tx: f64, ty: f64, tz: f64) {
    // Reject obviously non-finite inputs early; fuzzers will still discover
    // more interesting edge cases near the finite boundary.
    if !x.is_finite()
        || !y.is_finite()
        || !z.is_finite()
        || !tx.is_finite()
        || !ty.is_finite()
        || !tz.is_finite()
    {
        return;
    }

    let p = Point3::<World>::new(x, y, z);
    let t = Transform::<World, World>::from_translation(tx, ty, tz);

    let q = t.apply_point(p);

    // Ensure we didn't produce NaNs from finite inputs.
    assert!(q.x.is_finite());
    assert!(q.y.is_finite());
    assert!(q.z.is_finite());
}

#[test]
fn fuzz_compat_smoke_test() {
    // Simple deterministic call to ensure the harness itself is wired correctly.
    fuzz_apply_point_with_translation(1.0, 2.0, 3.0, 10.0, -5.0, 0.5);
}
