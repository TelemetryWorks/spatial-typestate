//! Sensor -> aircraft -> world: two active quarter turns and target translations.
//! Run with default features or --no-default-features --features no_std.
use spatial_typestate::{
    Dimensionless, Feet, Frame, Meters, Point3, SpatialError, Transform, UnitQuat, Vector3,
};

struct Sensor;
struct Aircraft;
struct World;
impl Frame for Sensor {}
impl Frame for Aircraft {}
impl Frame for World {}

fn close(actual: f64, expected: f64) {
    assert!((actual - expected).abs() <= 1e-9);
}

fn main() -> Result<(), SpatialError> {
    // +90 degrees about z: (x,y,z) -> (-y,x,z), then aircraft-frame offset.
    let sensor_aircraft = Transform::<Sensor, Aircraft, Meters>::try_from_rotation_translation(
        UnitQuat::try_from_components(0.0, 0.0, 1.0, 1.0)?,
        Vector3::<_, Meters>::new(1.0, 2.0, 3.0),
    )?;
    // +90 degrees about x: (x,y,z) -> (x,-z,y), then world-frame offset.
    let aircraft_world = Transform::<Aircraft, World, Meters>::try_from_rotation_translation(
        UnitQuat::try_from_components(1.0, 0.0, 0.0, 1.0)?,
        Vector3::<_, Meters>::new(10.0, 20.0, 30.0),
    )?;
    // These frame relationships are supplied by the caller, not calibrated by
    // the library. Unit tags assert measurement units; physical axis meanings remain application choices.
    let sensor_point = Point3::<Sensor, Meters>::new(2.0, 0.0, 1.0);
    let aircraft_point = sensor_aircraft.apply_point(sensor_point)?;
    close(aircraft_point.x, 1.0);
    close(aircraft_point.y, 4.0);
    close(aircraft_point.z, 4.0);
    let sequential = aircraft_world.apply_point(aircraft_point)?;
    let sensor_world = sensor_aircraft.then(aircraft_world)?;
    let world_point = sensor_world.apply_point(sensor_point)?;
    for (actual, expected) in [
        (world_point.x, 11.0),
        (world_point.y, 16.0),
        (world_point.z, 34.0),
        (world_point.x, sequential.x),
        (world_point.y, sequential.y),
        (world_point.z, sequential.z),
    ] {
        close(actual, expected);
    }
    let restored = sensor_world.try_inverse()?.apply_point(world_point)?;
    close(restored.x, sensor_point.x);
    close(restored.y, sensor_point.y);
    close(restored.z, sensor_point.z);
    let direction =
        sensor_world.apply_vector(Vector3::<Sensor, Dimensionless>::new(2.0, 0.0, 1.0))?;
    close(direction.x, 0.0);
    close(direction.y, -1.0);
    close(direction.z, 2.0);
    let feet_map = sensor_world.convert_to::<Feet>()?;
    let feet_point = sensor_point.convert_to::<Feet>()?;
    let feet_world = feet_map.apply_point(feet_point)?.convert_to::<Meters>()?;
    for (actual, expected) in [
        (feet_world.x, 11.0),
        (feet_world.y, 16.0),
        (feet_world.z, 34.0),
    ] {
        close(actual, expected);
    }
    println!(
        "World point: ({:.3}, {:.3}, {:.3})",
        world_point.x, world_point.y, world_point.z
    );
    println!(
        "World vector: ({:.3}, {:.3}, {:.3})",
        direction.x, direction.y, direction.z
    );
    Ok(())
}
