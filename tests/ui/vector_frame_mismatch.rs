use spatial_typestate::{Transform, Vector3, spatial_frames};
spatial_frames! { Sensor, World }
fn main() {
    let transform = Transform::<Sensor, World>::identity();
    let wrong = Vector3::<World>::new(1.0, 0.0, 0.0);
    let _ = transform.apply_vector(wrong);
}
