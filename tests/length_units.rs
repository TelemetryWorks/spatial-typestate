//! Explicit length tags and checked conversions, independent of frame changes.
use proptest::prelude::*;
use spatial_typestate::{
    Dimensionless, Feet, Frame, LengthUnit, LinearLengthUnit, Meters, Point3, Quantity,
    SpatialError, Transform, Unit, UnitQuat, Vector3,
};

struct World;
impl Frame for World {}

struct Sensor;
impl Frame for Sensor {}
struct Aircraft;
impl Frame for Aircraft {}
struct Centimeters;
impl Unit for Centimeters {}
impl LengthUnit for Centimeters {}
impl LinearLengthUnit for Centimeters {
    const METERS_PER_UNIT: f64 = 0.01;
}
struct Velocity;
impl Unit for Velocity {}
struct OpaqueLength;
impl Unit for OpaqueLength {}
impl LengthUnit for OpaqueLength {}

// Const generics keep invalid/custom scales independent of the built-ins.
struct Scale<const BITS: u64>;
impl<const BITS: u64> Unit for Scale<BITS> {}
impl<const BITS: u64> LengthUnit for Scale<BITS> {}
impl<const BITS: u64> LinearLengthUnit for Scale<BITS> {
    const METERS_PER_UNIT: f64 = f64::from_bits(BITS);
}

fn close(actual: f64, expected: f64) {
    // A handful of bounded arithmetic steps: allow both zero-near absolute
    // error and relative error, not a universal unbounded roundtrip claim.
    assert!(
        (actual - expected).abs() <= 1e-11 + 32.0 * f64::EPSILON * expected.abs(),
        "{actual} != {expected}"
    );
}

#[test]
fn international_foot_has_analytic_meter_value() {
    let meters = Quantity::<Feet>::new(1.0).convert_to::<Meters>().unwrap();
    assert_eq!(meters.get().to_bits(), 0.3048_f64.to_bits());
    let point = Point3::<World, Feet>::new(1.0, -2.0, 0.0)
        .convert_to::<Meters>()
        .unwrap();
    assert_eq!(point.x.to_bits(), 0.3048_f64.to_bits());
    assert_eq!(point.y.to_bits(), (-0.6096_f64).to_bits());
    let map = Transform::<World, World, Feet>::identity()
        .convert_to::<Meters>()
        .unwrap();
    assert_eq!(map.apply_point(point).unwrap(), point);
}

#[test]
fn analytic_meter_and_foot_workflows_describe_same_point() {
    let first = Transform::<Sensor, Aircraft, Meters>::try_from_rotation_translation(
        UnitQuat::try_from_components(0.0, 0.0, 1.0, 1.0).unwrap(),
        Vector3::new(1.0, 2.0, 3.0),
    )
    .unwrap();
    let next = Transform::<Aircraft, World, Meters>::try_from_rotation_translation(
        UnitQuat::try_from_components(1.0, 0.0, 0.0, 1.0).unwrap(),
        Vector3::new(10.0, 20.0, 30.0),
    )
    .unwrap();
    let point = Point3::<Sensor, Meters>::new(2.0, 0.0, 1.0);
    let meter_map = first.then(next).unwrap();
    let foot_map = first
        .convert_to::<Feet>()
        .unwrap()
        .then(next.convert_to::<Feet>().unwrap())
        .unwrap();
    let foot_point = point.convert_to::<Feet>().unwrap();
    let result = foot_map
        .apply_point(foot_point)
        .unwrap()
        .convert_to::<Meters>()
        .unwrap();
    // Independent hand calculation: (2,0,1)->(1,4,4)->(11,16,34).
    for (actual, expected) in [result.x, result.y, result.z]
        .into_iter()
        .zip([11.0, 16.0, 34.0])
    {
        close(actual, expected);
    }
    let meter_result = meter_map.apply_point(point).unwrap();
    for (actual, expected) in [result.x, result.y, result.z].into_iter().zip([
        meter_result.x,
        meter_result.y,
        meter_result.z,
    ]) {
        close(actual, expected);
    }
    let inverse: Transform<World, Sensor, Feet> = foot_map.try_inverse().unwrap();
    let restored = inverse
        .apply_point(foot_map.apply_point(foot_point).unwrap())
        .unwrap();
    for (actual, expected) in [restored.x, restored.y, restored.z].into_iter().zip([
        foot_point.x,
        foot_point.y,
        foot_point.z,
    ]) {
        close(actual, expected);
    }
}

#[test]
fn rotation_preserves_opaque_vector_units_independent_of_translation() {
    let map = Transform::<Sensor, World, Feet>::try_from_rotation_translation(
        UnitQuat::try_from_components(0.0, 0.0, 1.0, 1.0).unwrap(),
        Vector3::new(100.0, 200.0, 300.0),
    )
    .unwrap();
    let direction: Vector3<World, Dimensionless> = map
        .apply_vector(Vector3::<Sensor, Dimensionless>::new(2.0, 3.0, 4.0))
        .unwrap();
    let velocity: Vector3<World, Velocity> = map
        .apply_vector(Vector3::<Sensor, Velocity>::new(2.0, 3.0, 4.0))
        .unwrap();
    for values in [
        [direction.x, direction.y, direction.z],
        [velocity.x, velocity.y, velocity.z],
    ] {
        for (actual, expected) in values.into_iter().zip([-3.0, 2.0, 4.0]) {
            close(actual, expected);
        }
    }
}

#[test]
fn custom_bare_unit_markers_need_no_value_traits_or_conversion_metadata() {
    fn traits<T: Copy + Clone + core::fmt::Debug + PartialEq>(value: T) {
        assert_eq!(value, value);
    }
    traits(Point3::<World, Centimeters>::new(1.0, 2.0, 3.0));
    traits(Vector3::<World, Velocity>::new(1.0, 2.0, 3.0));
    traits(Transform::<Sensor, World, OpaqueLength>::identity());
    traits(Quantity::<Centimeters>::new(1.0));
    let custom = Quantity::<Centimeters>::new(100.0)
        .convert_to::<Meters>()
        .unwrap();
    assert_eq!(custom.get().to_bits(), 1.0_f64.to_bits());
}

#[test]
fn transform_conversion_changes_only_translation_and_canonicalizes_bottom() {
    let matrix = [
        [-0.0, 2.0, -3.0, 1.0],
        [4.0, 5.0, 6.0, -2.0],
        [7.0, 8.0, 9.0, 3.0],
        [f64::NAN, f64::INFINITY, 4.0, 5.0],
    ];
    let source = Transform::<Sensor, World, Feet>::from_matrix(matrix);
    let result = source.convert_to::<Meters>().unwrap();
    for (row, source_row) in matrix.iter().take(3).enumerate() {
        for (column, source_entry) in source_row.iter().take(3).enumerate() {
            assert_eq!(result.matrix[row][column].to_bits(), source_entry.to_bits());
        }
        assert_eq!(
            result.matrix[row][3].to_bits(),
            (source_row[3] * 0.3048).to_bits()
        );
    }
    assert_eq!(
        result.matrix[3].map(f64::to_bits),
        [0.0_f64, 0.0, 0.0, 1.0].map(f64::to_bits)
    );
    for index in 0..12 {
        for invalid in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
            let mut map = source;
            map.matrix[index / 4][index % 4] = invalid;
            assert_eq!(map.convert_to::<Meters>(), Err(SpatialError::NonFinite));
        }
    }
}

#[test]
fn invalid_metadata_and_unrepresentable_factors_have_distinct_errors() {
    fn invalid<const B: u64>() {
        assert_eq!(
            Quantity::<Scale<B>>::new(1.0).convert_to::<Meters>(),
            Err(SpatialError::InvalidUnitScale)
        );
        assert_eq!(
            Quantity::<Meters>::new(1.0).convert_to::<Scale<B>>(),
            Err(SpatialError::InvalidUnitScale)
        );
    }
    invalid::<0>();
    invalid::<{ (-0.0_f64).to_bits() }>();
    invalid::<{ (-1.0_f64).to_bits() }>();
    invalid::<{ f64::NAN.to_bits() }>();
    invalid::<{ f64::INFINITY.to_bits() }>();
    invalid::<{ f64::NEG_INFINITY.to_bits() }>();
    type Invalid = Scale<0>;
    assert_eq!(
        Point3::<World, Invalid>::new(1.0, 2.0, 3.0).convert_to::<Meters>(),
        Err(SpatialError::InvalidUnitScale)
    );
    assert_eq!(
        Vector3::<World, Invalid>::new(1.0, 2.0, 3.0).convert_to::<Meters>(),
        Err(SpatialError::InvalidUnitScale)
    );
    assert_eq!(
        Transform::<Sensor, World, Invalid>::identity().convert_to::<Meters>(),
        Err(SpatialError::InvalidUnitScale)
    );
    // Metadata errors take precedence over non-finite values.
    assert_eq!(
        Quantity::<Invalid>::new(f64::NAN).convert_to::<Meters>(),
        Err(SpatialError::InvalidUnitScale)
    );
    type Tiny = Scale<1>;
    type Huge = Scale<{ f64::MAX.to_bits() }>;
    // Both scales are valid, but the factor under/overflows. Even a zero
    // value whose real conversion is zero does not bypass factor validation.
    assert_eq!(
        Quantity::<Tiny>::new(0.0).convert_to::<Huge>(),
        Err(SpatialError::UnrepresentableUnitConversion)
    );
    assert_eq!(
        Quantity::<Huge>::new(0.0).convert_to::<Tiny>(),
        Err(SpatialError::UnrepresentableUnitConversion)
    );
    // A rearranged computation could be finite; simple factor-first policy errs.
    assert_eq!(
        Quantity::<Huge>::new(f64::from_bits(1)).convert_to::<Tiny>(),
        Err(SpatialError::UnrepresentableUnitConversion)
    );
}

#[test]
fn nonfinite_components_and_overflow_are_rejected_but_underflow_is_allowed() {
    for invalid in [f64::NAN, f64::INFINITY, f64::NEG_INFINITY] {
        assert_eq!(
            Quantity::<Meters>::new(invalid).convert_to::<Meters>(),
            Err(SpatialError::NonFinite)
        );
        assert_eq!(
            Quantity::<Meters>::new(invalid).convert_to::<Feet>(),
            Err(SpatialError::NonFinite)
        );
        for axis in 0..3 {
            let mut values = [1.0; 3];
            values[axis] = invalid;
            assert_eq!(
                Point3::<World, Meters>::new(values[0], values[1], values[2]).convert_to::<Feet>(),
                Err(SpatialError::NonFinite)
            );
            assert_eq!(
                Vector3::<World, Meters>::new(values[0], values[1], values[2]).convert_to::<Feet>(),
                Err(SpatialError::NonFinite)
            );
        }
    }
    for extreme in [f64::MAX, -f64::MAX] {
        assert_eq!(
            Quantity::<Meters>::new(extreme).convert_to::<Feet>(),
            Err(SpatialError::NonFinite)
        );
        assert_eq!(
            Transform::<Sensor, World, Meters>::from_translation(extreme, 0.0, 0.0)
                .convert_to::<Feet>(),
            Err(SpatialError::NonFinite)
        );
    }
    assert_eq!(
        Quantity::<Feet>::new(f64::from_bits(1))
            .convert_to::<Meters>()
            .unwrap()
            .get()
            .to_bits(),
        0.0_f64.to_bits()
    );
    assert_eq!(
        Quantity::<Feet>::new(-f64::from_bits(1))
            .convert_to::<Meters>()
            .unwrap()
            .get()
            .to_bits(),
        (-0.0_f64).to_bits()
    );
}

#[test]
fn positive_subnormal_factor_is_allowed_and_conversion_errors_propagate() {
    type Tiny = Scale<1>;
    assert_eq!(
        Quantity::<Tiny>::new(1.0)
            .convert_to::<Meters>()
            .unwrap()
            .get()
            .to_bits(),
        1
    );
    fn convert() -> Result<(), Box<dyn std::error::Error>> {
        let _ = Quantity::<Meters>::new(f64::MAX).convert_to::<Feet>()?;
        Ok(())
    }
    assert_eq!(
        convert().unwrap_err().downcast_ref::<SpatialError>(),
        Some(&SpatialError::NonFinite)
    );
}

#[test]
fn finite_same_unit_conversion_preserves_extreme_and_zero_bits() {
    for value in [
        0.0,
        -0.0,
        f64::from_bits(1),
        -f64::from_bits(1),
        f64::MIN_POSITIVE,
        f64::MAX,
        -f64::MAX,
    ] {
        assert_same_unit_bits(value);
    }
}

fn assert_same_unit_bits(value: f64) {
    assert_eq!(
        Quantity::<Feet>::new(value)
            .convert_to::<Feet>()
            .unwrap()
            .get()
            .to_bits(),
        value.to_bits()
    );
    let point = Point3::<World, Feet>::new(value, value, value)
        .convert_to::<Feet>()
        .unwrap();
    let vector = Vector3::<World, Feet>::new(value, value, value)
        .convert_to::<Feet>()
        .unwrap();
    let map = Transform::<Sensor, World, Feet>::from_translation(value, value, value)
        .convert_to::<Feet>()
        .unwrap();
    for actual in [
        point.x,
        point.y,
        point.z,
        vector.x,
        vector.y,
        vector.z,
        map.matrix[0][3],
        map.matrix[1][3],
        map.matrix[2][3],
    ] {
        assert_eq!(actual.to_bits(), value.to_bits());
    }
}

proptest! {
    #![proptest_config(ProptestConfig::with_cases(1024))]
    #[test]
    fn same_unit_finite_bits_are_preserved(bits in any::<u64>()) {
        let value=f64::from_bits(bits);
        prop_assume!(value.is_finite());
        assert_same_unit_bits(value);
    }
    #[test]
    fn bounded_length_roundtrip(value in -1e6_f64..1e6) {
        let result=Quantity::<Meters>::new(value).convert_to::<Feet>().unwrap().convert_to::<Meters>().unwrap().get();
        close(result,value);
    }
    #[test]
    fn finite_foot_components_follow_factor_multiplication(bits in any::<u64>()) {
        let value=f64::from_bits(bits);
        prop_assume!(value.is_finite());
        // This is an evaluation/bit oracle; physical scale is independently
        // checked by the 1-foot analytic test and workflow above.
        let expected=(value*0.3048).to_bits();
        let point=Point3::<World,Feet>::new(value,value,value).convert_to::<Meters>().unwrap();
        let vector=Vector3::<World,Feet>::new(value,value,value).convert_to::<Meters>().unwrap();
        let quantity=Quantity::<Feet>::new(value).convert_to::<Meters>().unwrap();
        for actual in [point.x,point.y,point.z,vector.x,vector.y,vector.z,quantity.get()] {
            prop_assert_eq!(actual.to_bits(),expected);
        }
    }
}
