use spatial_typestate::{Feet, Frame, Meters, Transform};
struct World;
impl Frame for World {}
fn main() {
    let first = Transform::<World, World, Meters>::identity();
    let next = Transform::<World, World, Feet>::identity();
    let _ = first.then(next);
}
