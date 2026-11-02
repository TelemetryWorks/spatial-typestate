use spatial_typestate::{Transform, spatial_frames};
spatial_frames! { Sensor, Aircraft, World }
fn main() {
    let first = Transform::<Sensor, Aircraft>::identity();
    let wrong = Transform::<World, World>::identity();
    let _ = first.then(wrong);
}
