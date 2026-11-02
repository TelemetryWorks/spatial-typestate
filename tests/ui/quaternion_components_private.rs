use spatial_typestate::{UnitQuat, spatial_frames};

spatial_frames! { World }

fn main() {
    let mut quaternion = UnitQuat::<World>::identity();
    quaternion.x = 2.0;
    quaternion.y = 2.0;
    quaternion.z = 2.0;
    quaternion.w = 2.0;
    std::hint::black_box(quaternion);
}
