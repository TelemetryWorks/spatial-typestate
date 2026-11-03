//! Frame markers need no value traits: they are labels, not stored values.
use spatial_typestate::{Frame, Meters, Point3, Transform, UnitQuat, Vector3};

struct Sensor;
struct World;
impl Frame for Sensor {}
impl Frame for World {}

fn assert_value_traits<T: Copy + Clone + core::fmt::Debug + PartialEq>(value: T) {
    let copied = value;
    assert_eq!(value, copied);
    assert!(!format!("{value:?}").is_empty());
}

#[test]
fn bare_markers_support_value_traits() {
    assert_value_traits(Point3::<Sensor, Meters>::new(1.0, 2.0, 3.0));
    assert_value_traits(Vector3::<Sensor, Meters>::new(1.0, 2.0, 3.0));
    assert_value_traits(Transform::<Sensor, World, Meters>::identity());
    assert_value_traits(UnitQuat::<World>::identity());
    assert!(format!("{:?}", Point3::<Sensor, Meters>::new(1.0, 2.0, 3.0)).contains("Sensor"));
    assert!(format!("{:?}", Transform::<Sensor, World, Meters>::identity()).contains("World"));
}

#[test]
fn quaternion_equality_is_component_equality() {
    let positive = UnitQuat::<World>::identity();
    let negative = UnitQuat::<World>::try_from_components(0.0, 0.0, 0.0, -1.0).unwrap();
    assert_ne!(positive, negative);
}
