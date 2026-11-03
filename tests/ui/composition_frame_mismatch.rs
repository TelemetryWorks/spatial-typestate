use spatial_typestate::{Meters, Transform, spatial_frames};
spatial_frames! { Sensor, Aircraft, World }
fn main() {
    let first = Transform::<Sensor, Aircraft, Meters>::identity();
    let wrong = Transform::<World, World, Meters>::identity();
    let _ = first.then(wrong);
}
