//! Translation compatibility helper, with deterministic and property tests.
//! This is not a configured cargo-fuzz target or continuous fuzzing setup.

use proptest::prelude::*;
use spatial_typestate::{Point3, Transform, spatial_frames};

spatial_frames! {
    World,
}

/// Entry-style function suitable for fuzzing.
///
/// A fuzz target can feed arbitrary point coordinates and translation offsets
/// into this function. Non-finite inputs are outside this helper's contract.
/// Finite inputs must produce the expected per-axis sums, including signed
/// infinity on overflow. Zero signs may differ due to additions of matrix zeros.
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

    // Identity coefficients only multiply finite inputs by zero or one; all
    // intermediate sums before translation are finite. The final finite+finite
    // addition can overflow, but cannot produce NaN. Equality checks the exact
    // finite sum or correct infinity sign, while treating +0 and -0 as equal.
    for (actual, expected) in [(q.x, x + tx), (q.y, y + ty), (q.z, z + tz)] {
        assert!(!actual.is_nan());
        assert_eq!(actual, expected);
    }
}

#[test]
fn fuzz_compat_smoke_test() {
    // Simple deterministic call to ensure the harness itself is wired correctly.
    fuzz_apply_point_with_translation(1.0, 2.0, 3.0, 10.0, -5.0, 0.5);
}

#[test]
fn finite_translation_can_overflow_without_nan() {
    fuzz_apply_point_with_translation(f64::MAX, -f64::MAX, f64::MAX, f64::MAX, -f64::MAX, f64::MAX);
}

#[test]
fn cancellation_and_large_finite_translations() {
    fuzz_apply_point_with_translation(
        f64::MAX,
        -f64::MAX,
        f64::MAX / 2.0,
        -f64::MAX,
        f64::MAX,
        f64::MAX / 2.0,
    );
    fuzz_apply_point_with_translation(
        -0.0,
        f64::from_bits(1),
        -f64::MIN_POSITIVE,
        0.0,
        -f64::from_bits(1),
        f64::MIN_POSITIVE,
    );
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(1024))]

    #[test]
    fn finite_bit_patterns_match_translation(
        input in any::<[u64; 6]>()
            .prop_map(|bits| bits.map(f64::from_bits))
            .prop_filter("finite coordinates and offsets", |values| values.iter().all(|value| value.is_finite()))
    ) {
        fuzz_apply_point_with_translation(input[0], input[1], input[2], input[3], input[4], input[5]);
    }
}
