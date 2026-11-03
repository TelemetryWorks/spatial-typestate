//! Standard error reporting and caller-chosen boxed propagation.

use spatial_typestate::{SpatialError, UnitQuat, spatial_frames};

spatial_frames! { World }

#[test]
fn validation_errors_have_readable_messages() {
    assert_eq!(SpatialError::NonFinite.to_string(), "non-finite component");
    assert_eq!(
        SpatialError::ZeroNormQuaternion.to_string(),
        "all quaternion components are zero"
    );
    assert_eq!(
        SpatialError::NonRigidTransform.to_string(),
        "transform is not a proper rigid affine transform"
    );
    assert_eq!(
        SpatialError::InvalidUnitScale.to_string(),
        "unit scale must be positive and finite"
    );
    assert_eq!(
        SpatialError::UnrepresentableUnitConversion.to_string(),
        "unit conversion factor is not representable"
    );
}

#[test]
fn validation_errors_implement_core_error() {
    fn check_error(error: impl core::error::Error) {
        assert!(error.source().is_none());
    }
    check_error(SpatialError::NonFinite);
    check_error(SpatialError::ZeroNormQuaternion);
    check_error(SpatialError::NonRigidTransform);
    check_error(SpatialError::InvalidUnitScale);
    check_error(SpatialError::UnrepresentableUnitConversion);
}

#[test]
fn question_mark_propagates_into_caller_chosen_box() {
    fn normalize(components: [f64; 4]) -> Result<UnitQuat<World>, Box<dyn std::error::Error>> {
        Ok(UnitQuat::try_from_components(
            components[0],
            components[1],
            components[2],
            components[3],
        )?)
    }
    for (input, expected) in [
        ([f64::NAN, 0.0, 0.0, 1.0], SpatialError::NonFinite),
        ([0.0; 4], SpatialError::ZeroNormQuaternion),
    ] {
        let error = normalize(input).unwrap_err();
        assert_eq!(error.downcast_ref::<SpatialError>(), Some(&expected));
    }
    assert!(normalize([0.0, 0.0, 0.0, 2.0]).is_ok());
}
