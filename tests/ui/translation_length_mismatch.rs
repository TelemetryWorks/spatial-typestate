use spatial_typestate::{Feet, Frame, Meters, Transform, UnitQuat, Vector3};
struct World;
impl Frame for World {}
fn main() {
    let translation = Vector3::<World, Meters>::new(1.0, 2.0, 3.0);
    let _ = Transform::<World, World, Feet>::try_from_rotation_translation(
        UnitQuat::identity(), translation,
    );
}
