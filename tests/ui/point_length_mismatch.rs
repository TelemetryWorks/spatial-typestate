use spatial_typestate::{Feet, Frame, Meters, Point3, Transform};
struct World;
impl Frame for World {}
fn main() {
    let map = Transform::<World, World, Feet>::identity();
    let point = Point3::<World, Meters>::new(1.0, 2.0, 3.0);
    let _ = map.apply_point(point);
}
