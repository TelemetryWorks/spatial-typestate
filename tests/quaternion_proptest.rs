//! Property-based tests over finite f64 bit patterns, including subnormals.

use proptest::prelude::*;
use spatial_typestate::{SpatialError, UnitQuat, spatial_frames};

spatial_frames! { World }

fn finite_quaternion_components() -> impl Strategy<Value = [f64; 4]> {
    any::<[u64; 4]>()
        .prop_map(|bits| bits.map(f64::from_bits))
        .prop_filter("finite components", |components| {
            components.iter().all(|component| component.is_finite())
        })
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(1024))]

    #[test]
    fn all_finite_nonzero_bit_patterns_normalize(input in finite_quaternion_components()) {
        let result = UnitQuat::<World>::try_from_components(input[0], input[1], input[2], input[3]);
        if input.iter().all(|&component| component == 0.0) {
            prop_assert!(matches!(result, Err(SpatialError::ZeroNormQuaternion)));
        } else {
            // No underflow exceptions or skipped finite nonzero inputs.
            let quaternion = result.expect("finite nonzero inputs must normalize");
            let components = [quaternion.x(), quaternion.y(), quaternion.z(), quaternion.w()];
            prop_assert!(components.into_iter().all(f64::is_finite));
            let norm_sq: f64 = components.into_iter().map(|component| component * component).sum();
            // A small fixed number of rounded divisions, products, additions,
            // and a square root: 32 eps is a conservative rounding allowance,
            // far below a tolerance that could conceal a degenerate quaternion.
            prop_assert!((norm_sq - 1.0).abs() <= 32.0 * f64::EPSILON);
            for (original, normalized) in input.into_iter().zip(components) {
                prop_assert_eq!(original.is_sign_negative(), normalized.is_sign_negative());
            }
        }
    }
}
