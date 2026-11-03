//! Translation compatibility helper, with deterministic and property tests.
//! This is not a configured cargo-fuzz target or continuous fuzzing setup.

use proptest::prelude::*;
use spatial_typestate::{Meters, Point3, Transform, spatial_frames};

spatial_frames! {
    World,
}

/// Entry-style function suitable for fuzzing.
///
/// A fuzz target can feed arbitrary point coordinates and translation offsets
/// into this function. Non-finite inputs and overflowing sums must return
/// NonFinite; successful calls match exact finite per-axis sums. Zero signs
/// may differ due to additions of matrix zeros.
pub fn fuzz_apply_point_with_translation(x: f64, y: f64, z: f64, tx: f64, ty: f64, tz: f64) {
    let result = Transform::<World, World, Meters>::from_translation(tx, ty, tz)
        .apply_point(Point3::<_, Meters>::new(x, y, z));
    if !x.is_finite()
        || !y.is_finite()
        || !z.is_finite()
        || !tx.is_finite()
        || !ty.is_finite()
        || !tz.is_finite()
    {
        assert!(matches!(
            result,
            Err(spatial_typestate::SpatialError::NonFinite)
        ));
        return;
    }
    let expected = [x + tx, y + ty, z + tz];
    if !expected.into_iter().all(f64::is_finite) {
        assert!(matches!(
            result,
            Err(spatial_typestate::SpatialError::NonFinite)
        ));
        return;
    }
    let q = result.expect("finite translation sums must succeed");
    // Independent per-axis sums retain exact numeric equality, with +0/-0
    // numerically equal. Overflow must be reported, not silently accepted.
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
fn finite_translation_overflow_is_reported() {
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
