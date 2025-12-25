//! Property-based tests for Quantity and basic unit behavior.

use proptest::prelude::*;
use spatial_typestate::{Meters, Quantity, Radians};

fn approx_eq(a: f64, b: f64, eps: f64) -> bool {
    (a - b).abs() <= eps
}

proptest! {
    #[test]
    fn quantity_add_then_subtract_is_identity_for_meters(a in -1e6_f64..1e6_f64,
                                                         b in -1e6_f64..1e6_f64) {
        let qa: Quantity<Meters> = Quantity::new(a);
        let qb: Quantity<Meters> = Quantity::new(b);

        let sum = qa + qb;
        let back = sum - qb;

        prop_assert!(approx_eq(back.get(), qa.get(), 1e-9));
    }

    #[test]
    fn quantity_zero_is_additive_identity_for_radians(x in -1e6_f64..1e6_f64) {
        let qx: Quantity<Radians> = Quantity::new(x);
        let zero: Quantity<Radians> = Quantity::new(0.0);

        let q_plus_zero = qx + zero;
        let zero_plus_q = zero + qx;

        prop_assert!(approx_eq(q_plus_zero.get(), x, 1e-9));
        prop_assert!(approx_eq(zero_plus_q.get(), x, 1e-9));
    }
}
