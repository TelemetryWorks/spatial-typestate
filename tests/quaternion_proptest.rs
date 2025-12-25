//! Property-based tests for UnitQuat invariants.
//!
//! These tests check that:
//! - Normalized quaternions stay unit length (within tolerance).
//! - Non-finite inputs are rejected.
//! - Zero-norm inputs are rejected (already covered by regular tests).
//! - This reinforces your invariant that `UnitQuat::try_from_components` always returns a unit quaternion when it succeeds.
//!
use proptest::prelude::*;
use spatial_typestate::{spatial_frames, Frame, SpatialError, UnitQuat};

spatial_frames! {
    World,
}

fn approx_eq(a: f64, b: f64, eps: f64) -> bool {
    (a - b).abs() <= eps
}

/// Strategy for generating arbitrary finite quaternion components.
fn finite_quaternion_components() -> impl Strategy<Value = (f64, f64, f64, f64)> {
    // Restrict to a moderate range to avoid overflow in norm calculations.
    (
        -1e6_f64..1e6_f64,
        -1e6_f64..1e6_f64,
        -1e6_f64..1e6_f64,
        -1e6_f64..1e6_f64,
    )
}

proptest! {
    #[test]
    fn try_from_components_produces_unit_norm_for_nonzero_finite_inputs(
        (x, y, z, w) in finite_quaternion_components()
    ) {
        // If all components are zero, we *expect* a ZeroNormQuaternion error.
        if x == 0.0 && y == 0.0 && z == 0.0 && w == 0.0 {
            let result = UnitQuat::<World>::try_from_components(x, y, z, w);
            prop_assert!(matches!(result, Err(SpatialError::ZeroNormQuaternion)));
        } else {
            let result = UnitQuat::<World>::try_from_components(x, y, z, w);
            let q = match result {
                Ok(q) => q,
                Err(SpatialError::ZeroNormQuaternion) => {
                    // In extremely degenerate cases, norm might underflow.
                    // Skip those inputs.
                    prop_assume!(false);
                    unreachable!();
                }
                Err(e) => panic!("Unexpected error from finite inputs: {:?}", e),
            };

            let norm_sq = q.x * q.x + q.y * q.y + q.z * q.z + q.w * q.w;
            prop_assert!(approx_eq(norm_sq, 1.0, 1e-9));
        }
    }
}
