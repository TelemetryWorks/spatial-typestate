use spatial_typestate::{Meters, Transform, Vector3, spatial_frames};
spatial_frames! { Sensor, World }
fn main() {
    let transform = Transform::<Sensor, World, Meters>::identity();
    let wrong = Vector3::<World, Meters>::new(1.0, 0.0, 0.0);
    let _ = transform.apply_vector(wrong);
}
