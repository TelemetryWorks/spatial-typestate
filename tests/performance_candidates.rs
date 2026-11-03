//! Safety checks for isolated benchmark hypotheses, not library replacements.
#![deny(unsafe_code)]
#[path = "../benches/support/experiments.rs"]
mod experiments;
use proptest::prelude::*;
#[cfg(not(feature = "std"))]
use spatial_typestate::UnitQuat;
use spatial_typestate::{Frame, Meters, Point3, SpatialError, Transform};
struct World;
impl Frame for World {}

fn compare(map: Transform<World, World, Meters>, point: Point3<World, Meters>) {
    let reference = map.apply_point(point);
    let prepared = match experiments::Prepared::new(map) {
        Ok(prepared) => prepared.apply(point),
        Err(error) => Err(error),
    };
    for candidate in [
        prepared,
        experiments::point_local(&map, point),
        experiments::point_forced(&map, point),
        experiments::point_eager(&map, point),
        experiments::point_rows(&map, point),
    ] {
        match (reference, candidate) {
            (Ok(a), Ok(b)) => assert_eq!(
                [a.x, a.y, a.z].map(f64::to_bits),
                [b.x, b.y, b.z].map(f64::to_bits)
            ),
            (Err(a), Err(b)) => assert_eq!(a, b),
            _ => panic!("candidate changed success/error classification"),
        }
    }
}

#[test]
fn prepared_map_owns_its_validation_and_still_rejects_bad_points() {
    let mut original = Transform::<World, World, Meters>::identity();
    let prepared = experiments::Prepared::new(original).unwrap();
    original.matrix[0][0] = f64::NAN;
    assert!(original.apply_point(Point3::new(1.0, 2.0, 3.0)).is_err());
    assert_eq!(
        prepared
            .apply(Point3::new(1.0, 2.0, 3.0))
            .unwrap()
            .x
            .to_bits(),
        1.0_f64.to_bits()
    );
    assert!(matches!(
        prepared.apply(Point3::new(f64::NAN, 2.0, 3.0)),
        Err(SpatialError::NonFinite)
    ));
}

#[test]
fn adversarial_positions_and_ignored_bottom_match() {
    for invalid in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        for index in 0..16 {
            let mut map = Transform::identity();
            map.matrix[index / 4][index % 4] = invalid;
            compare(map, Point3::new(-0.0, f64::from_bits(1), f64::MAX));
        }
        for axis in 0..3 {
            let mut xyz = [1.0; 3];
            xyz[axis] = invalid;
            compare(Transform::identity(), Point3::new(xyz[0], xyz[1], xyz[2]));
        }
    }
    for value in [
        0.0,
        -0.0,
        f64::from_bits(1),
        -f64::from_bits(1),
        f64::MAX,
        -f64::MAX,
    ] {
        compare(
            Transform::from_translation(value, -value, value),
            Point3::new(value, value, -value),
        );
    }
}

fn check_norm(s: f64) {
    let native = s.sqrt();
    for candidate in [
        experiments::sqrt_steps::<6>(s),
        experiments::sqrt_steps::<8>(s),
    ] {
        assert!(candidate.is_finite());
        assert!((candidate - native).abs() <= 4.0 * f64::EPSILON * native);
        assert!((candidate * candidate - s).abs() <= 8.0 * f64::EPSILON * s);
    }
}

#[test]
fn replay_norms_meet_existing_sampled_bounds_not_a_bit_equivalence_proof() {
    let mut differences = 0;
    for i in 0..=100_000 {
        let s = 1.0 + 3.0 * f64::from(i) / 100_000.0;
        check_norm(s);
        differences += usize::from(
            experiments::sqrt_steps::<6>(s).to_bits() != experiments::sqrt_steps::<8>(s).to_bits(),
        );
    }
    for s in [1.0_f64, 2.0, 3.0, 4.0] {
        check_norm(s);
        if s > 1.0 {
            check_norm(f64::from_bits(s.to_bits() - 1));
        }
        if s < 4.0 {
            check_norm(f64::from_bits(s.to_bits() + 1));
        }
    }
    eprintln!("six/eight-step bit differences among 100001 dense values: {differences}");
}

#[test]
fn quaternion_replay_errors_and_extremes() {
    for components in [
        [f64::MAX, -f64::MAX, 0.0, 1.0],
        [
            f64::from_bits(1),
            -f64::from_bits(2),
            f64::from_bits(3),
            0.0,
        ],
    ] {
        for result in [
            experiments::normalize_steps::<6>(components),
            experiments::normalize_steps::<8>(components),
        ] {
            let q = result.unwrap();
            assert!(q.into_iter().all(f64::is_finite));
            assert!((q.into_iter().map(|v| v * v).sum::<f64>() - 1.0).abs() <= 32.0 * f64::EPSILON);
        }
    }
    for (components, error) in [
        ([0.0; 4], SpatialError::ZeroNormQuaternion),
        ([f64::NAN, 0.0, 0.0, 1.0], SpatialError::NonFinite),
    ] {
        assert_eq!(experiments::normalize_steps::<6>(components), Err(error));
        assert_eq!(experiments::normalize_steps::<8>(components), Err(error));
    }
}

proptest! {
    #![proptest_config(ProptestConfig {cases:4096, failure_persistence:Some(Box::new(proptest::test_runner::FileFailurePersistence::Direct("tests/performance_candidates.proptest-regressions"))), ..ProptestConfig::default()})]
    #[test]
    fn point_candidates_preserve_arbitrary_bits(matrix in any::<[[u64;4];4]>(),xyz in any::<[u64;3]>()) {
        let map=Transform::from_matrix(matrix.map(|row|row.map(f64::from_bits)));
        compare(map,Point3::new(f64::from_bits(xyz[0]),f64::from_bits(xyz[1]),f64::from_bits(xyz[2])));
    }
    #[test]
    fn norm_candidates_sample_interval_bits(offset in 0u64..=(4.0_f64.to_bits()-1.0_f64.to_bits())) {
        check_norm(f64::from_bits(1.0_f64.to_bits()+offset));
    }
    #[test]
    #[cfg(not(feature="std"))]
    fn replay8_matches_actual_no_std_library_bits(bits in any::<[u64;4]>()) {
        let [x,y,z,w]=bits.map(f64::from_bits);
        match (UnitQuat::<World>::try_from_components(x,y,z,w), experiments::normalize_steps::<8>([x,y,z,w])) {
            (Ok(q),Ok(replay))=>prop_assert_eq!([q.x(),q.y(),q.z(),q.w()].map(f64::to_bits),replay.map(f64::to_bits)),
            (Err(a),Err(b))=>prop_assert_eq!(a,b),
            _=>prop_assert!(false,"replay success/error changed"),
        }
    }
    #[test]
    fn replay_normalization_accepts_finite_nonzero_patterns(bits in any::<[u64;4]>()) {
        let components=bits.map(f64::from_bits);
        prop_assume!(components.into_iter().all(f64::is_finite));
        prop_assume!(components.into_iter().any(|v|v!=0.0));
        for result in [experiments::normalize_steps::<6>(components),experiments::normalize_steps::<8>(components)] {
            let q=result.unwrap();prop_assert!(q.into_iter().all(f64::is_finite));
            prop_assert!((q.into_iter().map(|v|v*v).sum::<f64>()-1.0).abs()<=32.0*f64::EPSILON);
        }
    }
}
